"""Tests for real agent observability, structured logging, and telemetry persistence."""

import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db import get_db
from app.main import app
from app.models.entities import AgentRun, RunStatus
from app.services.observability import (
    AGENT_DISPLAY_NAMES,
    EXPECTED_AGENTS,
    AgentTelemetryTracker,
    StructuredJsonFormatter,
    init_analysis_pipeline_runs,
    log_agent_event,
)
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
        pytest.skip(f"Integration tests require PostgreSQL and Redis: {error}")

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


def test_structured_json_logging() -> None:
    """Verifies that the structured JSON formatter creates machine-readable logs with correlation metadata."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="xai_resopt.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test agent execution turn",
        args=(),
        exc_info=None,
    )
    analysis_uuid = uuid4()
    record.request_id = "req-12345"
    record.analysis_id = analysis_uuid
    record.agent_name = "ats_agent"
    record.status = "completed"
    record.duration_ms = 450
    record.retry_count = 1
    record.retrieval_count = 5
    record.model_calls = 1
    record.token_usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    record.final_score = 88.5

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test agent execution turn"
    assert parsed["request_id"] == "req-12345"
    assert parsed["analysis_id"] == str(analysis_uuid)
    assert parsed["agent_name"] == "ats_agent"
    assert parsed["status"] == "completed"
    assert parsed["duration_ms"] == 450
    assert parsed["retry_count"] == 1
    assert parsed["retrieval_count"] == 5
    assert parsed["model_calls"] == 1
    assert parsed["token_usage"]["total_tokens"] == 150
    assert parsed["final_score"] == 88.5


@pytest.mark.asyncio
async def test_agent_telemetry_tracker_success_and_failure(
    client: httpx.AsyncClient,
    integration_resources: tuple[async_sessionmaker[AsyncSession], Redis],
) -> None:
    """Verifies that AgentTelemetryTracker accurately persists execution metrics, errors, and recovery status."""
    session_factory, _ = integration_resources

    # Ingest baseline
    user_email = f"telemetry_unit_{uuid4()}@example.com"
    reg = await client.post(
        "/api/auth/signup",
        json={"email": user_email, "password": "Password123!", "full_name": "Unit Tester"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res_resp = await client.post(
        "/api/ingestion/resumes",
        files={"file": ("resume.txt", b"Jane Doe\njane@example.com\nPython Developer", "text/plain")},
        headers=headers,
    )
    resume_id = res_resp.json()["id"]

    jd_resp = await client.post(
        "/api/ingestion/job-descriptions",
        data={"text": "Python Developer required with 3+ years experience.", "title": "Python Dev"},
        headers=headers,
    )
    jd_id = jd_resp.json()["id"]

    ana_resp = await client.post(
        "/api/analysis/baseline",
        json={"resume_id": resume_id, "job_description_id": jd_id},
        headers=headers,
    )
    assert ana_resp.status_code == 201
    analysis_id = UUID(ana_resp.json()["analysis_id"])

    # 1. Successful execution check
    async with session_factory() as db:
        stmt = select(AgentRun).where(
            AgentRun.analysis_id == analysis_id, AgentRun.agent_name == "intake_agent"
        )
        saved = await db.scalar(stmt)
        assert saved is not None
        assert saved.status == RunStatus.completed
        assert saved.retrieval_count == 2
        assert saved.start_time is not None
        assert saved.end_time is not None
        assert saved.duration_ms is not None and saved.duration_ms >= 0
        assert saved.error is None
        assert saved.output is not None

    # 2. Failed execution of an agent with recovery tracking
    request_id = f"req-fail-{uuid4()}"
    async with session_factory() as db:
        try:
            async with AgentTelemetryTracker(
                db, analysis_id, request_id, "critic_agent", retry_count=2
            ) as tracker:
                tracker.recovery_status = "unrecovered"
                raise ValueError("Model validation timeout exceeded")
        except ValueError:
            pass
        await db.commit()

    async with session_factory() as db:
        stmt = select(AgentRun).where(
            AgentRun.analysis_id == analysis_id, AgentRun.request_id == request_id
        )
        saved_critic = await db.scalar(stmt)
        assert saved_critic is not None
        assert saved_critic.status == RunStatus.failed
        assert saved_critic.retry_count == 2
        assert "Model validation timeout exceeded" in (saved_critic.error or "")
        assert saved_critic.recovery_status == "unrecovered"


@pytest.mark.asyncio
async def test_all_11_agents_exposed_via_api(client: httpx.AsyncClient) -> None:
    """Verifies that running a baseline analysis records and exposes all 11 required agents via GET /api/analysis/{id}/agent-runs."""
    SAMPLE_RESUME = """Alice Observability
alice@observability.dev | +1 555 999 8888 | New York, NY
https://github.com/alice-obs

Summary
Staff Infrastructure and AI Systems Engineer with 8+ years experience building observable agent pipelines.

Experience
Senior AI Engineer at Apex Systems
- Built distributed multi-agent systems with real telemetry and structured event logging.
- Deployed PostgreSQL and Redis infrastructure supporting high throughput workloads.

Skills
Python, FastAPI, Docker, PostgreSQL, Agent Observability, Redis, OpenRouter
"""

    SAMPLE_JD = """Staff AI Systems Engineer

Requirements
- 7+ years of experience with Python, FastAPI, and PostgreSQL
- Production knowledge of LLM agent architectures and real observability
- Experience with Docker and Redis
"""

    user_email = f"telemetry_{uuid4()}@example.com"
    reg = await client.post(
        "/api/auth/signup",
        json={"email": user_email, "password": "Password123!", "full_name": "Telemetry Tester"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res_resp = await client.post(
        "/api/ingestion/resumes",
        files={"file": ("resume.txt", SAMPLE_RESUME.encode("utf-8"), "text/plain")},
        headers=headers,
    )
    assert res_resp.status_code == 201
    resume_id = res_resp.json()["id"]

    jd_resp = await client.post(
        "/api/ingestion/job-descriptions",
        data={"text": SAMPLE_JD, "title": "Staff AI Engineer"},
        headers=headers,
    )
    assert jd_resp.status_code == 201
    jd_id = jd_resp.json()["id"]

    # Trigger Baseline Analysis
    ana_resp = await client.post(
        "/api/analysis/baseline",
        json={"resume_id": resume_id, "job_description_id": jd_id},
        headers=headers,
    )
    assert ana_resp.status_code == 201
    analysis_id = ana_resp.json()["analysis_id"]

    # Query Agent Runs Telemetry Endpoint
    runs_resp = await client.get(f"/api/analysis/{analysis_id}/agent-runs", headers=headers)
    assert runs_resp.status_code == 200
    runs_data = runs_resp.json()

    agent_names = {r["agent_name"] for r in runs_data["agent_runs"]}

    # Verify every single one of the 11 user-specified agents is present
    for agent_key in EXPECTED_AGENTS:
        assert agent_key in agent_names, f"Missing required agent: {agent_key}"

    # Verify telemetry properties for each record
    for r in runs_data["agent_runs"]:
        assert "id" in r
        assert "analysis_id" in r
        assert "agent_name" in r
        assert "status" in r
        assert r["status"] in ["queued", "running", "completed", "failed", "cancelled"]
        assert "retry_count" in r
        assert "retrieval_count" in r
        assert "model_calls" in r
        assert "created_at" in r
