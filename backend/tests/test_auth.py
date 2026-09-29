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


def database_url() -> str:
    return settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)


@pytest_asyncio.fixture
async def integration_resources() -> AsyncGenerator[tuple[async_sessionmaker[AsyncSession], Redis], None]:
    engine = create_async_engine(database_url(), pool_pre_ping=True)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        await redis.ping()
    except Exception as error:
        await redis.aclose()
        await engine.dispose()
        pytest.skip(f"Authentication integration tests require PostgreSQL and Redis: {error}")

    yield async_sessionmaker(engine, expire_on_commit=False), redis
    await redis.flushdb()
    await redis.aclose()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(integration_resources: tuple[async_sessionmaker[AsyncSession], Redis]) -> AsyncGenerator[httpx.AsyncClient, None]:
    session_factory, redis = integration_resources

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


async def delete_user(session_factory: async_sessionmaker[AsyncSession], user_id: UUID) -> None:
    async with session_factory() as session:
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


@pytest.mark.asyncio
async def test_registration_login_and_logout(client: httpx.AsyncClient, integration_resources) -> None:
    session_factory, _ = integration_resources
    email = "auth-test@example.com"
    signup = await client.post("/api/auth/signup", json={"email": email, "full_name": "Auth Test", "password": "correct horse battery staple"})
    assert signup.status_code == 201
    token = signup.json()["access_token"]
    user = signup.json()["user"]

    me = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email

    logout = await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 204
    revoked = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert revoked.status_code == 401
    await delete_user(session_factory, UUID(user["id"]))


@pytest.mark.asyncio
async def test_login_rejects_invalid_password(client: httpx.AsyncClient, integration_resources) -> None:
    session_factory, _ = integration_resources
    email = "invalid-password@example.com"
    signup = await client.post("/api/auth/signup", json={"email": email, "full_name": "Login Test", "password": "correct horse battery staple"})
    assert signup.status_code == 201
    login = await client.post("/api/auth/login", json={"email": email, "password": "wrong password"})
    assert login.status_code == 401
    await delete_user(session_factory, UUID(signup.json()["user"]["id"]))


@pytest.mark.asyncio
async def test_duplicate_email_is_rejected(client: httpx.AsyncClient, integration_resources) -> None:
    session_factory, _ = integration_resources
    payload = {"email": "duplicate@example.com", "full_name": "Duplicate Test", "password": "correct horse battery staple"}
    first = await client.post("/api/auth/signup", json=payload)
    second = await client.post("/api/auth/signup", json=payload)
    assert first.status_code == 201
    assert second.status_code == 409
    await delete_user(session_factory, UUID(first.json()["user"]["id"]))


@pytest.mark.asyncio
async def test_authorization_and_ownership_isolation(client: httpx.AsyncClient, integration_resources) -> None:
    session_factory, _ = integration_resources
    first = await client.post("/api/auth/signup", json={"email": "owner-a@example.com", "full_name": "Owner A", "password": "correct horse battery staple"})
    second = await client.post("/api/auth/signup", json={"email": "owner-b@example.com", "full_name": "Owner B", "password": "correct horse battery staple"})
    token_a = first.json()["access_token"]
    user_b = second.json()["user"]

    missing_auth = await client.get(f"/api/users/{user_b['id']}")
    forbidden = await client.get(f"/api/users/{user_b['id']}", headers={"Authorization": f"Bearer {token_a}"})
    assert missing_auth.status_code == 401
    assert forbidden.status_code == 404

    await delete_user(session_factory, UUID(first.json()["user"]["id"]))
    await delete_user(session_factory, UUID(user_b["id"]))
