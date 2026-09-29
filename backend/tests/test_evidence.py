from collections.abc import AsyncGenerator
from uuid import UUID

import httpx
import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db import get_db
from app.main import app
from app.models import User
from app.services.redis import get_redis

settings = get_settings()


@pytest_asyncio.fixture
async def resources() -> AsyncGenerator[tuple[async_sessionmaker[AsyncSession], Redis], None]:
    engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1), pool_pre_ping=True)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        await redis.ping()
    except Exception as error:
        await redis.aclose()
        await engine.dispose()
        pytest.skip(f"Evidence integration tests require PostgreSQL and Redis: {error}")
    yield async_sessionmaker(engine, expire_on_commit=False), redis
    await redis.flushdb()
    await redis.aclose()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(resources) -> AsyncGenerator[httpx.AsyncClient, None]:
    session_factory, redis = resources

    async def override_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    async def override_redis() -> AsyncGenerator[Redis, None]:
        yield redis

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = override_redis
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


async def remove_user(session_factory: async_sessionmaker[AsyncSession], user_id: UUID) -> None:
    async with session_factory() as session:
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def create_account(client: httpx.AsyncClient, email: str) -> dict:
    response = await client.post("/api/auth/signup", json={"email": email, "full_name": "Evidence Test", "password": "correct horse battery staple"})
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_claim_provenance_can_be_retrieved(client: httpx.AsyncClient, resources) -> None:
    session_factory, _ = resources
    account = await create_account(client, "provenance@example.com")
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    resume = await client.post("/api/ingestion/resumes", headers=headers, files={"file": ("resume.txt", "Ada Lovelace\n\nSkills\nPython", "text/plain")})
    assert resume.status_code == 201
    evidence_id = resume.json()["items"][0]["id"]

    claim = await client.post("/api/claims", headers=headers, json={"text": "Uses Python", "support_status": "SUPPORTED", "confidence": 0.96, "evidence": [{"evidence_id": evidence_id, "rationale": "The Skills section explicitly lists Python.", "support_confidence": 0.98}]})
    assert claim.status_code == 201
    provenance = await client.get(f"/api/claims/{claim.json()['id']}/provenance", headers=headers)
    assert provenance.status_code == 200
    assert provenance.json()[0]["evidence_item_id"] == evidence_id
    assert provenance.json()[0]["evidence"]["source_location"] == "Skills > line 4"
    assert provenance.json()[0]["rationale"] == "The Skills section explicitly lists Python."
    await remove_user(session_factory, UUID(account["user"]["id"]))


@pytest.mark.asyncio
async def test_unsupported_claim_is_explicit_and_owner_isolated(client: httpx.AsyncClient, resources) -> None:
    session_factory, _ = resources
    first = await create_account(client, "unsupported@example.com")
    second = await create_account(client, "other-owner@example.com")
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}
    claim = await client.post("/api/claims", headers=first_headers, json={"text": "Reduced cloud cost by 40%", "support_status": "UNSUPPORTED", "confidence": 0.0})
    assert claim.status_code == 201
    assert claim.json()["support_status"] == "UNSUPPORTED"
    hidden = await client.get(f"/api/claims/{claim.json()['id']}", headers=second_headers)
    assert hidden.status_code == 404
    await remove_user(session_factory, UUID(first["user"]["id"]))
    await remove_user(session_factory, UUID(second["user"]["id"]))


@pytest.mark.asyncio
async def test_knowledge_entities_and_relationships_are_evidence_backed(client: httpx.AsyncClient, resources) -> None:
    session_factory, _ = resources
    account = await create_account(client, "graph@example.com")
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    resume = await client.post("/api/ingestion/resumes", headers=headers, files={"file": ("resume.txt", "Ada Lovelace\n\nExperience\nBuilt analytical systems", "text/plain")})
    evidence_id = resume.json()["items"][0]["id"]
    person = await client.post("/api/knowledge/entities", headers=headers, json={"entity_type": "Person", "text": "Ada Lovelace", "confidence": 0.95})
    experience = await client.post("/api/knowledge/entities", headers=headers, json={"entity_type": "Experience", "text": "Built analytical systems", "source_evidence_id": evidence_id, "confidence": 0.95})
    relationship = await client.post("/api/knowledge/relationships", headers=headers, json={"source_entity_id": person.json()["id"], "target_entity_id": experience.json()["id"], "relationship_type": "has_experience", "evidence_item_id": evidence_id})
    assert relationship.status_code == 201
    assert relationship.json()["relationship_type"] == "has_experience"
    assert relationship.json()["evidence_item_id"] == evidence_id
    await remove_user(session_factory, UUID(account["user"]["id"]))
