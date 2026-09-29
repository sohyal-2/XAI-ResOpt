"""Integration tests for the complete End-to-End Baseline Analysis Workflow and APIs."""

from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db import get_db
from app.main import app
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
        pytest.skip(f"Baseline integration tests require PostgreSQL and Redis: {error}")

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


SAMPLE_RESUME_TEXT = """Jane Doe
jane.doe@example.com | +1 555 123 4567 | San Francisco, CA
https://github.com/janedoe | https://janedoe.dev

Professional Summary
Senior Backend Engineer with 6+ years of experience designing and scaling distributed APIs using Python, FastAPI, Docker, and PostgreSQL.

Work Experience
Senior Backend Engineer at TechCorp
- Architected high-throughput REST APIs using Python and FastAPI, increasing transaction processing by 40%.
- Designed and optimized PostgreSQL schemas, indexes, and connection pools.
- Built containerized CI/CD microservices with Docker.

Technical Skills
Python, FastAPI, PostgreSQL, Docker, Redis, SQL, Git, REST APIs

Education
University of California, Berkeley - Bachelor of Science in Computer Science
"""

SAMPLE_JOB_TEXT = """Senior Backend Engineer

Required Qualifications
- 5+ years experience with Python and FastAPI microservices
- Production experience with PostgreSQL and relational databases

Preferred Qualifications
- Experience with AWS cloud deployment
- Experience with Docker containerization
"""


@pytest.mark.asyncio
async def test_complete_baseline_analysis_workflow_and_apis(client: httpx.AsyncClient) -> None:
    from uuid import uuid4

    # 1. Register and login Primary User
    alice_email = f"alice_{uuid4()}@example.com"
    reg_response = await client.post(
        "/api/auth/signup",
        json={"email": alice_email, "password": "SecurePassword123!", "full_name": "Alice Baseline"},
    )
    assert reg_response.status_code == 201
    token = reg_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ingest Resume
    files = {"file": ("resume.txt", SAMPLE_RESUME_TEXT.encode("utf-8"), "text/plain")}
    resume_resp = await client.post("/api/ingestion/resumes", files=files, headers=headers)
    assert resume_resp.status_code == 201
    resume_id = resume_resp.json()["id"]

    # 3. Ingest Job Description
    job_resp = await client.post(
        "/api/ingestion/job-descriptions",
        data={"text": SAMPLE_JOB_TEXT, "title": "Senior Backend Engineer"},
        headers=headers,
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    # 4. Trigger Full Baseline Analysis Pipeline
    analysis_resp = await client.post(
        "/api/analysis/baseline",
        json={"resume_id": resume_id, "job_description_id": job_id},
        headers=headers,
    )
    assert analysis_resp.status_code == 201
    report = analysis_resp.json()

    # Validate Core Baseline Report Schema & Deterministic Metrics
    assert "analysis_id" in report
    analysis_id = report["analysis_id"]
    assert report["score_name"] == "XAI-ResOpt ATS Compatibility Score"
    assert report["calculation_version"] == "xai-resopt-v1.0-deterministic"
    assert 0.0 <= report["overall_score"] <= 100.0
    assert 0.0 <= report["overall_score_normalized"] <= 1.0

    # Validate Category Scores (8 dimensions)
    cat_scores = report["category_scores"]
    assert "keyword_coverage" in cat_scores
    assert "semantic_similarity" in cat_scores
    assert "requirement_coverage" in cat_scores
    assert "evidence_confidence" in cat_scores
    assert "experience_alignment" in cat_scores
    assert "section_completeness" in cat_scores
    assert "formatting_safety" in cat_scores
    assert "skill_match" in cat_scores

    # Validate Qualitative Insights
    assert len(report["strengths"]) > 0
    assert isinstance(report["weaknesses"], list)
    assert isinstance(report["mandatory_skill_gaps"], list)
    assert isinstance(report["preferred_skill_gaps"], list)
    assert isinstance(report["ats_risks"], list)
    assert isinstance(report["recommendations"], list)
    assert len(report["recommendations"]) > 0
    assert isinstance(report["evidence_references"], list)
    assert isinstance(report["requirement_coverage"], list)

    # 5. Retrieve via GET /api/analysis/{id}/baseline
    get_report_resp = await client.get(f"/api/analysis/{analysis_id}/baseline", headers=headers)
    assert get_report_resp.status_code == 200
    retrieved_report = get_report_resp.json()
    assert retrieved_report["analysis_id"] == analysis_id
    assert retrieved_report["overall_score"] == report["overall_score"]

    # 6. Retrieve via GET /api/analysis/{id}/score
    score_resp = await client.get(f"/api/analysis/{analysis_id}/score", headers=headers)
    assert score_resp.status_code == 200
    score_data = score_resp.json()
    assert score_data["overall_score"] == report["overall_score"]
    assert len(score_data["category_scores"]) == 8

    # 7. Retrieve via GET /api/analysis/{id}/agent-runs
    runs_resp = await client.get(f"/api/analysis/{analysis_id}/agent-runs", headers=headers)
    assert runs_resp.status_code == 200
    runs_data = runs_resp.json()
    assert runs_data["total_runs"] >= 5
    agent_names = [r["agent_name"] for r in runs_data["agent_runs"]]
    assert "agentic_rag" in agent_names
    assert "ats_agent" in agent_names
    assert "skill_agent" in agent_names
    assert "evidence_agent" in agent_names
    assert "scoring_engine" in agent_names

    # 8. Retrieve via GET /api/analysis/{id}/recommendations
    recs_resp = await client.get(f"/api/analysis/{analysis_id}/recommendations", headers=headers)
    assert recs_resp.status_code == 200
    recs_data = recs_resp.json()
    assert recs_data["total_recommendations"] > 0

    # 9. Retrieve via GET /api/analysis/{id}/requirements
    reqs_resp = await client.get(f"/api/analysis/{analysis_id}/requirements", headers=headers)
    assert reqs_resp.status_code == 200
    reqs_data = reqs_resp.json()
    assert reqs_data["total_requirements"] > 0

    # 10. Retrieve via GET /api/analysis/{id}/evidence
    ev_resp = await client.get(f"/api/analysis/{analysis_id}/evidence", headers=headers)
    assert ev_resp.status_code == 200
    ev_data = ev_resp.json()
    assert ev_data["total_evidence_items"] >= 0

    # 11. Verify User Ownership Isolation
    # Register a second user
    bob_email = f"bob_{uuid4()}@example.com"
    other_user_resp = await client.post(
        "/api/auth/signup",
        json={"email": bob_email, "password": "SecurePassword123!", "full_name": "Bob Attacker"},
    )
    assert other_user_resp.status_code == 201
    other_token = other_user_resp.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Bob attempts to access Alice's analysis -> Expect 404 (or 403)
    unauthorized_resp = await client.get(f"/api/analysis/{analysis_id}/baseline", headers=other_headers)
    assert unauthorized_resp.status_code == 404
