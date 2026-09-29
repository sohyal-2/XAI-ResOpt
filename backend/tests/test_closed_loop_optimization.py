"""Integration and end-to-end tests for the Closed-Loop Optimization Workflow and APIs."""

from collections.abc import AsyncGenerator
from uuid import uuid4

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
        pytest.skip(f"Optimization integration tests require PostgreSQL and Redis: {error}")

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


SAMPLE_RESUME_TEXT = """Alex Mercer
alex.mercer@example.com | +1 415 555 0199 | San Francisco, CA
https://github.com/alexmercer | https://alexmercer.dev

Summary
Software engineer with experience building web backends in Python and working with relational databases.

Experience
Software Engineer at CloudScale Inc
- Worked on backend APIs using Python and PostgreSQL.
- Handled microservice deployments and container workflows.
- Improved database query performance and reliability.

Skills
Python, PostgreSQL, Git, Linux, Docker

Education
BS in Computer Science, Stanford University
"""

SAMPLE_JOB_TEXT = """Senior Backend Software Engineer

Requirements
- 4+ years of experience with Python, FastAPI, and PostgreSQL
- Strong experience with Docker containerization and CI/CD pipelines
- Proven record designing high-performance REST APIs

Preferred
- Redis caching experience
- Kubernetes cluster management
"""


@pytest.mark.asyncio
async def test_complete_closed_loop_optimization_workflow_and_apis(client: httpx.AsyncClient) -> None:
    # 1. Register and login Primary User
    user_email = f"optim_user_{uuid4()}@example.com"
    reg_response = await client.post(
        "/api/auth/signup",
        json={"email": user_email, "password": "Password123!", "full_name": "Optimization Tester"},
    )
    assert reg_response.status_code == 201
    auth_token = reg_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}

    # 2. Ingest Resume
    files = {"file": ("alex_resume.txt", SAMPLE_RESUME_TEXT.encode("utf-8"), "text/plain")}
    resume_resp = await client.post("/api/ingestion/resumes", files=files, headers=headers)
    assert resume_resp.status_code == 201
    resume_id = resume_resp.json()["id"]

    # 3. Ingest Job Description
    job_resp = await client.post(
        "/api/ingestion/job-descriptions",
        data={"text": SAMPLE_JOB_TEXT, "title": "Senior Backend Engineer JD"},
        headers=headers,
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    # 4. Trigger Baseline Analysis
    baseline_resp = await client.post(
        "/api/analysis/baseline",
        headers=headers,
        json={"resume_id": resume_id, "job_description_id": job_id},
    )
    assert baseline_resp.status_code == 201
    baseline_data = baseline_resp.json()
    analysis_id = baseline_data["analysis_id"]
    initial_score = baseline_data["overall_score"]
    assert initial_score > 0

    # 5. Trigger Closed-Loop Optimization
    optim_resp = await client.post(
        f"/api/analysis/{analysis_id}/optimize",
        headers=headers,
        json={"max_iterations": 2, "target_score": 90.0, "strict_mode": True},
    )
    assert optim_resp.status_code == 200, f"Error {optim_resp.status_code}: {optim_resp.text}"
    optim_data = optim_resp.json()

    assert optim_data["analysis_id"] == analysis_id
    assert optim_data["before_score"] == pytest.approx(initial_score, rel=1e-2)
    assert optim_data["total_iterations"] >= 1
    assert optim_data["total_iterations"] <= 2
    assert isinstance(optim_data["iterations"], list)
    assert len(optim_data["iterations"]) == optim_data["total_iterations"]

    # Check iteration record fields
    first_iter = optim_data["iterations"][0]
    assert first_iter["iteration_number"] == 1
    assert "score" in first_iter
    assert "score_delta" in first_iter
    assert isinstance(first_iter["changes"], list)
    assert isinstance(first_iter["accepted_changes"], list)
    assert isinstance(first_iter["rejected_changes"], list)
    assert isinstance(first_iter["validation_issues"], list)
    assert isinstance(first_iter["agent_runs"], list)

    # Check that accepted changes have grounding and evidence IDs
    for change in first_iter["accepted_changes"]:
        assert "change_id" in change
        assert "before_text" in change
        assert "after_text" in change
        assert "reason" in change
        assert "evidence_ids" in change

    # 6. Query Optimization History API
    history_resp = await client.get(
        f"/api/analysis/{analysis_id}/optimizations",
        headers=headers,
    )
    assert history_resp.status_code == 200
    history_data = history_resp.json()
    assert len(history_data) == optim_data["total_iterations"]
    assert history_data[0]["iteration_number"] == 1

    # 7. Query Latest Optimization API
    latest_resp = await client.get(
        f"/api/analysis/{analysis_id}/optimizations/latest",
        headers=headers,
    )
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["total_iterations"] == optim_data["total_iterations"]
    assert latest_data["after_score"] == optim_data["after_score"]

    # 8. Tenant Isolation Check: Another user cannot access or optimize this analysis
    other_email = f"other_{uuid4()}@example.com"
    other_reg = await client.post(
        "/api/auth/signup",
        json={"email": other_email, "password": "Password123!", "full_name": "Other User"},
    )
    other_token = other_reg.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Other user optimize attempt -> 404
    other_opt = await client.post(
        f"/api/analysis/{analysis_id}/optimize",
        headers=other_headers,
        json={"max_iterations": 2},
    )
    assert other_opt.status_code == 404

    # Other user get history attempt -> 404
    other_hist = await client.get(
        f"/api/analysis/{analysis_id}/optimizations",
        headers=other_headers,
    )
    assert other_hist.status_code == 404


@pytest.mark.asyncio
async def test_closed_loop_optimization_early_termination_and_bounds(client: httpx.AsyncClient) -> None:
    """Proves that closed-loop optimization terminates early if target score is met and strictly respects max_iterations."""
    user_email = f"bounds_user_{uuid4()}@example.com"
    reg_response = await client.post(
        "/api/auth/signup",
        json={"email": user_email, "password": "Password123!", "full_name": "Bounds Tester"},
    )
    auth_token = reg_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Ingest
    files = {"file": ("alex_resume.txt", SAMPLE_RESUME_TEXT.encode("utf-8"), "text/plain")}
    resume_resp = await client.post("/api/ingestion/resumes", files=files, headers=headers)
    resume_id = resume_resp.json()["id"]

    job_resp = await client.post(
        "/api/ingestion/job-descriptions",
        data={"text": SAMPLE_JOB_TEXT, "title": "Senior Backend Engineer JD"},
        headers=headers,
    )
    job_id = job_resp.json()["id"]

    # Baseline Analysis
    baseline_resp = await client.post(
        "/api/analysis/baseline",
        headers=headers,
        json={"resume_id": resume_id, "job_description_id": job_id},
    )
    analysis_id = baseline_resp.json()["analysis_id"]

    # Test with target_score=40.0 (low threshold) -> should terminate on iteration 1
    early_resp = await client.post(
        f"/api/analysis/{analysis_id}/optimize",
        headers=headers,
        json={"max_iterations": 3, "target_score": 40.0},
    )
    assert early_resp.status_code == 200
    early_data = early_resp.json()
    assert early_data["total_iterations"] == 1
    assert early_data["final_score"] >= 40.0

