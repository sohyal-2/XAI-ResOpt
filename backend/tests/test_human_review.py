"""Integration and unit tests for the Human-in-the-Loop review workflow, manual edits, and audit trail."""

from collections.abc import AsyncGenerator
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db import get_db
from app.main import app
from app.models.entities import ApprovalHistory, Claim, ClaimStatus, ResumeVersion
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
        pytest.skip(f"Human review integration tests require PostgreSQL and Redis: {error}")

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


SAMPLE_RESUME_TEXT = """Morgan Smith
morgan.smith@example.com | +1 206 555 0123 | Seattle, WA
https://github.com/morgansmith

Summary
Backend engineer specializing in distributed systems and cloud backends in Python and PostgreSQL.

Experience
Backend Engineer at CloudCorp
- Maintained REST APIs and microservices using Python and PostgreSQL.
- Handled CI/CD container deployments using Docker.

Skills
Python, PostgreSQL, Docker, Git, REST APIs

Education
University of Washington - BS Computer Science
"""

SAMPLE_JOB_TEXT = """Senior Backend Engineer
Requirements
- 4+ years Python, FastAPI, and PostgreSQL experience
- Strong experience with Docker and REST APIs
"""


@pytest.mark.asyncio
async def test_complete_human_review_workflow(client: httpx.AsyncClient, integration_resources: tuple[async_sessionmaker[AsyncSession], Redis]) -> None:
    session_factory, _ = integration_resources

    # 1. Register and login
    user_email = f"reviewer_{uuid4()}@example.com"
    reg_response = await client.post(
        "/api/auth/signup",
        json={"email": user_email, "password": "Password123!", "full_name": "Reviewer Tester"},
    )
    assert reg_response.status_code == 201
    auth_token = reg_response.json()["access_token"]
    user_id = reg_response.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {auth_token}"}

    # 2. Ingest Resume & Job Description
    files = {"file": ("morgan_resume.txt", SAMPLE_RESUME_TEXT.encode("utf-8"), "text/plain")}
    resume_resp = await client.post("/api/ingestion/resumes", files=files, headers=headers)
    assert resume_resp.status_code == 201
    resume_id = resume_resp.json()["id"]

    job_resp = await client.post(
        "/api/ingestion/job-descriptions",
        data={"text": SAMPLE_JOB_TEXT, "title": "Senior Backend Engineer JD"},
        headers=headers,
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    # 3. Trigger Baseline Analysis & Optimization
    baseline_resp = await client.post(
        "/api/analysis/baseline",
        headers=headers,
        json={"resume_id": resume_id, "job_description_id": job_id},
    )
    assert baseline_resp.status_code == 201
    analysis_id = baseline_resp.json()["analysis_id"]

    optim_resp = await client.post(
        f"/api/analysis/{analysis_id}/optimize",
        headers=headers,
        json={"max_iterations": 2},
    )
    assert optim_resp.status_code == 200

    # 4. Retrieve Review Session & Verify 7 Dimensions + Trace Graph
    review_resp = await client.get(f"/api/analysis/{analysis_id}/review", headers=headers)
    assert review_resp.status_code == 200
    review_data = review_resp.json()

    assert review_data["analysis_id"] == analysis_id
    assert review_data["total_changes"] >= 1
    assert isinstance(review_data["changes"], list)

    for item in review_data["changes"]:
        # Verify 7 required dimensions
        assert "before_text" in item and len(item["before_text"]) > 0
        assert "after_text" in item and len(item["after_text"]) > 0
        assert "why_changed" in item and len(item["why_changed"]) > 0
        assert "evidence" in item
        assert "confidence" in item and 0.0 <= item["confidence"] <= 1.0
        assert "risk" in item
        assert "supported_status" in item

        # Verify 5-tier audit trace: Recommendation -> Change -> Claim -> Evidence -> Original Source
        trace = item["trace_chain"]
        assert trace is not None
        assert "recommendation_text" in trace
        assert trace["change_before"] == item["before_text"]
        assert trace["change_after"] == item["after_text"]
        assert "claim_text" in trace
        assert "evidence_text" in trace
        assert "original_source" in trace

    # 5. Test Accept, Reject, and Manual Edit Separation
    first_change = review_data["changes"][0]
    second_change = review_data["changes"][1] if len(review_data["changes"]) > 1 else first_change

    custom_manual_text = "Custom manually authored summary highlighting Python and PostgreSQL architecture."
    decisions_payload = {
        "decisions": [
            {"change_id": first_change["change_id"], "action": "accept"},
            {"change_id": second_change["change_id"], "action": "edit", "manual_text": custom_manual_text},
        ]
    }
    dec_resp = await client.post(
        f"/api/analysis/{analysis_id}/review/decisions",
        headers=headers,
        json=decisions_payload,
    )
    assert dec_resp.status_code == 200
    updated_review = dec_resp.json()
    assert updated_review["accepted_count"] >= 1
    assert updated_review["edited_count"] >= 1

    # Verify manual edit is recorded separately from AI change
    edited_items = [ch for ch in updated_review["changes"] if ch["change_id"] == second_change["change_id"]]
    assert len(edited_items) == 1
    assert edited_items[0]["is_manual"] is True
    assert edited_items[0]["manual_text"] == custom_manual_text

    # 6. Test Accept All Safe Changes
    safe_resp = await client.post(
        f"/api/analysis/{analysis_id}/review/accept-all-safe",
        headers=headers,
    )
    assert safe_resp.status_code == 200
    safe_data = safe_resp.json()
    assert safe_data["accepted_count"] >= 1

    # 7. Test Safety Guardrail: Finalization Rejects Unresolved Unsupported Claims
    # Insert an unsupported claim
    from uuid import UUID
    async with session_factory() as session:
        unsupported_claim = Claim(
            id=uuid4(),
            owner_id=UUID(user_id),
            text="Led team of 50 engineers at Google",
            support_status=ClaimStatus.unsupported,
            confidence=0.1,
        )
        session.add(unsupported_claim)
        await session.commit()

    # Attempt to finalize without acknowledging/forcing -> MUST be rejected with 400
    blocked_final = await client.post(
        f"/api/analysis/{analysis_id}/review/finalize",
        headers=headers,
        json={"force_unresolved_claims": False},
    )
    assert blocked_final.status_code == 400
    assert "unresolved unsupported claims" in blocked_final.json()["detail"].lower()

    # 8. Finalize with explicit acknowledgment / force
    final_resp = await client.post(
        f"/api/analysis/{analysis_id}/review/finalize",
        headers=headers,
        json={"force_unresolved_claims": True, "notes": "Approved with manual overrides."},
    )
    assert final_resp.status_code == 200
    final_data = final_resp.json()

    assert final_data["analysis_id"] == analysis_id
    assert "new_resume_version_id" in final_data
    assert final_data["version_number"] >= 2
    assert final_data["changes_applied_count"] >= 1
    assert final_data["manual_edits_count"] >= 1
    assert custom_manual_text in final_data["finalized_resume_text"]

    # Verify new ResumeVersion and ApprovalHistory are persisted in PostgreSQL
    async with session_factory() as session:
        v_stmt = select(ResumeVersion).where(ResumeVersion.id == UUID(final_data["new_resume_version_id"]))
        persisted_ver = (await session.scalars(v_stmt)).first()
        assert persisted_ver is not None
        assert persisted_ver.is_final is True

        app_stmt = select(ApprovalHistory).where(ApprovalHistory.analysis_id == UUID(analysis_id))
        persisted_app = (await session.scalars(app_stmt)).first()
        assert persisted_app is not None
        assert "Approved with manual overrides." in (persisted_app.notes or "")


@pytest.mark.asyncio
async def test_re_run_optimization_action_and_isolation(client: httpx.AsyncClient) -> None:
    """Tests re-running optimization loop from review interface and tenant authorization boundaries."""
    user_email = f"reopt_user_{uuid4()}@example.com"
    reg_response = await client.post(
        "/api/auth/signup",
        json={"email": user_email, "password": "Password123!", "full_name": "Reopt User"},
    )
    auth_token = reg_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Ingest
    files = {"file": ("morgan_resume.txt", SAMPLE_RESUME_TEXT.encode("utf-8"), "text/plain")}
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

    # First optimize pass
    opt_resp = await client.post(f"/api/analysis/{analysis_id}/optimize", headers=headers, json={"max_iterations": 1})
    assert opt_resp.status_code == 200

    # Re-run optimization via review endpoint
    reopt_resp = await client.post(f"/api/analysis/{analysis_id}/review/re-optimize", headers=headers)
    assert reopt_resp.status_code == 200
    reopt_data = reopt_resp.json()
    assert reopt_data["analysis_id"] == analysis_id
    assert reopt_data["total_iterations"] >= 1

    # Tenant Isolation: Other user cannot review or finalize this analysis
    other_email = f"attacker_{uuid4()}@example.com"
    other_reg = await client.post(
        "/api/auth/signup",
        json={"email": other_email, "password": "Password123!", "full_name": "Attacker"},
    )
    other_token = other_reg.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    other_rev = await client.get(f"/api/analysis/{analysis_id}/review", headers=other_headers)
    assert other_rev.status_code == 404

    other_fin = await client.post(f"/api/analysis/{analysis_id}/review/finalize", headers=other_headers, json={})
    assert other_fin.status_code == 404

