"""Complete End-to-End User Flow Test.

Tests the full 16-step user journey from onboarding to export:
Sign up
-> Login
-> Upload Resume
-> Add Job Description
-> Analyze (Baseline)
-> View Baseline Report
-> Inspect Evidence Trace
-> Optimize (Closed Loop)
-> Verify Agent Execution Telemetry (Intake, Parser, JD, ATS, Skill, Evidence, Explainability, Optimizer, Critic, Fact-Check, Re-Evaluator)
-> Re-Score & Compare (Baseline vs Optimized)
-> Review Changes
-> Approve Decisions (Accept safe modifications)
-> Finalize Review & Publish Version
-> Validate Pre-rendering Invariants
-> Download ATS-Safe PDF
-> Download ATS-Safe Word DOCX
"""

from collections.abc import AsyncGenerator
from io import BytesIO
from uuid import UUID, uuid4
import pytest
import pytest_asyncio
import httpx
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db import get_db
from app.main import app
from app.services.redis import get_redis
from app.services.observability import EXPECTED_AGENTS

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
        pytest.skip(f"E2E tests require PostgreSQL and Redis: {error}")

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


@pytest.mark.asyncio
async def test_complete_end_to_end_journey(client: httpx.AsyncClient) -> None:
    # -------------------------------------------------------------------------
    # Step 1: Sign up
    # -------------------------------------------------------------------------
    user_email = f"e2e_engineer_{uuid4().hex[:6]}@example.com"
    user_password = "StrongPassword123!#"
    user_name = "Jane Candidate"

    signup_res = await client.post(
        "/api/auth/signup",
        json={"email": user_email, "full_name": user_name, "password": user_password},
    )
    assert signup_res.status_code == 201, f"Signup failed: {signup_res.text}"
    user_data = signup_res.json()["user"]
    assert user_data["email"] == user_email
    assert user_data["full_name"] == user_name

    # -------------------------------------------------------------------------
    # Step 2: Login
    # -------------------------------------------------------------------------
    login_res = await client.post(
        "/api/auth/login",
        json={"email": user_email, "password": user_password},
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    assert token and len(token) > 20
    auth_headers = {"Authorization": f"Bearer {token}"}

    # -------------------------------------------------------------------------
    # Step 3: Upload Resume
    # -------------------------------------------------------------------------
    resume_body = (
        "Jane Candidate\n"
        "jane@example.com | 555-0199 | San Francisco, CA | linkedin.com/in/janecandidate\n\n"
        "Summary\n"
        "Staff Software Engineer with 8 years of experience designing scalable distributed systems "
        "and high-performance microservices in Python, Go, and PostgreSQL.\n\n"
        "Experience\n"
        "Senior Backend Engineer | CloudScale Inc | 2021 - Present\n"
        "- Built asynchronous data ingestion pipeline handling 50k events/sec using FastAPI and Kafka.\n"
        "- Reduced database query latency by 45% by restructuring indexes and caching frequently accessed reads in Redis.\n"
        "- Containerized applications using Docker and deployed to Kubernetes clusters via GitHub Actions CI/CD.\n\n"
        "Software Engineer | DataCorp | 2018 - 2021\n"
        "- Developed RESTful APIs and background worker tasks using Python, Celery, and PostgreSQL.\n"
        "- Collaborated with cross-functional product and infrastructure teams.\n\n"
        "Skills\n"
        "Languages: Python, Go, SQL\n"
        "Frameworks & Tools: FastAPI, Docker, Kubernetes, Redis, PostgreSQL, AWS, Git\n\n"
        "Education\n"
        "B.S. in Computer Science | State University | 2018\n"
    ).encode("utf-8")

    upload_res = await client.post(
        "/api/ingestion/resumes",
        headers=auth_headers,
        files={"file": ("Jane_Candidate_Resume.txt", BytesIO(resume_body), "text/plain")},
    )
    assert upload_res.status_code == 201, f"Resume upload failed: {upload_res.text}"
    resume_id = upload_res.json()["id"]
    assert resume_id is not None

    # -------------------------------------------------------------------------
    # Step 4: Add Job Description
    # -------------------------------------------------------------------------
    jd_body = (
        "Role: Staff Backend Engineer\n"
        "Company: Apex Technologies\n\n"
        "Responsibilities:\n"
        "- Architect high-throughput distributed systems in Python and FastAPI.\n"
        "- Design performant database schemas in PostgreSQL with Redis caching.\n"
        "- Oversee container orchestration using Kubernetes and Docker on AWS cloud.\n"
        "- Champion automated testing, CI/CD pipelines, and observability.\n\n"
        "Requirements:\n"
        "- 5+ years of production experience with Python and FastAPI (Mandatory).\n"
        "- Strong proficiency in PostgreSQL and Redis distributed caching (Mandatory).\n"
        "- Experience with Docker, Kubernetes, and AWS infrastructure (Mandatory).\n"
        "- Experience with Kafka event streaming and Go microservices (Preferred).\n"
    )

    jd_res = await client.post(
        "/api/ingestion/job-descriptions",
        headers=auth_headers,
        data={"text": jd_body, "title": "Staff Backend Engineer"},
    )
    assert jd_res.status_code == 201, f"JD ingestion failed: {jd_res.text}"
    job_id = jd_res.json()["id"]
    assert job_id is not None

    # -------------------------------------------------------------------------
    # Step 5: Trigger Baseline Analysis
    # -------------------------------------------------------------------------
    baseline_run_res = await client.post(
        "/api/analysis/baseline",
        headers=auth_headers,
        json={"resume_id": resume_id, "job_description_id": job_id},
    )
    assert baseline_run_res.status_code == 201, f"Baseline analysis failed: {baseline_run_res.text}"
    baseline_run_data = baseline_run_res.json()
    analysis_id = baseline_run_data["analysis_id"]
    assert analysis_id is not None
    baseline_score = baseline_run_data["overall_score"]
    assert 0.0 <= baseline_score <= 100.0

    # -------------------------------------------------------------------------
    # Step 6: View Baseline Report
    # -------------------------------------------------------------------------
    report_res = await client.get(f"/api/analysis/{analysis_id}/baseline", headers=auth_headers)
    assert report_res.status_code == 200
    report = report_res.json()
    assert report["analysis_id"] == analysis_id
    assert report["score_name"] == "XAI-ResOpt ATS Compatibility Score"
    assert "category_scores" in report
    assert len(report["strengths"]) > 0

    # -------------------------------------------------------------------------
    # Step 7: Inspect Evidence Trace
    # -------------------------------------------------------------------------
    evidence_res = await client.get(f"/api/analysis/{analysis_id}/evidence", headers=auth_headers)
    assert evidence_res.status_code == 200
    evidence_data = evidence_res.json()
    assert evidence_data["analysis_id"] == analysis_id
    assert evidence_data["total_evidence_items"] >= 1

    # -------------------------------------------------------------------------
    # Step 8: Trigger Closed-Loop Optimization
    # -------------------------------------------------------------------------
    opt_res = await client.post(
        "/api/analysis/{analysis_id}/optimize".format(analysis_id=analysis_id),
        headers=auth_headers,
        json={"max_iterations": 2},
    )
    assert opt_res.status_code == 200, f"Optimization failed: {opt_res.text}"
    opt_data = opt_res.json()
    assert opt_data["analysis_id"] == analysis_id
    assert opt_data["total_iterations"] >= 1
    print("OPT DATA:", opt_data)
    assert "final_score" in opt_data

    # -------------------------------------------------------------------------
    # Step 9: Verify Real Agent Execution Telemetry (All 11 Agents)
    # -------------------------------------------------------------------------
    agent_runs_res = await client.get(f"/api/analysis/{analysis_id}/agent-runs", headers=auth_headers)
    assert agent_runs_res.status_code == 200
    agent_runs_data = agent_runs_res.json()
    assert agent_runs_data["total_runs"] >= 11
    agent_names_recorded = {r["agent_name"] for r in agent_runs_data["agent_runs"]}

    for expected in EXPECTED_AGENTS:
        assert expected in agent_names_recorded, f"Expected agent '{expected}' not recorded in telemetry!"

    # -------------------------------------------------------------------------
    # Step 10: Re-Score & Compare (Baseline vs Optimized)
    # -------------------------------------------------------------------------
    score_res = await client.get(f"/api/analysis/{analysis_id}/score", headers=auth_headers)
    assert score_res.status_code == 200
    score_data = score_res.json()
    assert "overall_score" in score_data

    latest_opt_res = await client.get(f"/api/analysis/{analysis_id}/optimizations/latest", headers=auth_headers)
    assert latest_opt_res.status_code == 200
    latest_opt = latest_opt_res.json()
    assert latest_opt["score_delta"] >= 0.0

    # -------------------------------------------------------------------------
    # Step 11: Review Proposed Changes
    # -------------------------------------------------------------------------
    review_res = await client.get(f"/api/analysis/{analysis_id}/review", headers=auth_headers)
    assert review_res.status_code == 200
    review_data = review_res.json()
    assert review_data["analysis_id"] == analysis_id
    assert review_data["total_changes"] >= 1

    # -------------------------------------------------------------------------
    # Step 12: Decide / Approve Proposed Changes
    # -------------------------------------------------------------------------
    bulk_accept_res = await client.post(
        f"/api/analysis/{analysis_id}/review/accept-all-safe",
        headers=auth_headers,
    )
    assert bulk_accept_res.status_code == 200
    bulk_data = bulk_accept_res.json()
    assert bulk_data["accepted_count"] >= 1

    # -------------------------------------------------------------------------
    # Step 13: Finalize Human Review & Publish Resume Version
    # -------------------------------------------------------------------------
    finalize_res = await client.post(
        f"/api/analysis/{analysis_id}/review/finalize",
        headers=auth_headers,
        json={"force_unresolved_claims": False, "notes": "Approved for release"},
    )
    assert finalize_res.status_code == 200, f"Finalize failed: {finalize_res.text}"
    finalize_data = finalize_res.json()
    final_version_id = finalize_data["new_resume_version_id"]
    assert final_version_id is not None
    assert finalize_data["version_number"] >= 2

    # -------------------------------------------------------------------------
    # Step 14: Validate Pre-rendering Invariants & Preview
    # -------------------------------------------------------------------------
    val_res = await client.get(f"/api/resumes/versions/{final_version_id}/validate", headers=auth_headers)
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is True
    assert "checks_passed" in val_data
    assert val_data["checks_passed"]["sections_present"] is True
    assert val_data["checks_passed"]["contact_info_intact"] is True

    preview_res = await client.get(f"/api/resumes/versions/{final_version_id}/preview", headers=auth_headers)
    assert preview_res.status_code == 200
    preview_doc = preview_res.json()
    assert preview_doc["header"]["name"] == "Jane Candidate"

    # -------------------------------------------------------------------------
    # Step 15: Download & Validate PDF
    # -------------------------------------------------------------------------
    pdf_res = await client.get(f"/api/resumes/versions/{final_version_id}/export/pdf", headers=auth_headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")
    assert len(pdf_res.content) > 500

    # -------------------------------------------------------------------------
    # Step 16: Download & Validate Word DOCX
    # -------------------------------------------------------------------------
    docx_res = await client.get(f"/api/resumes/versions/{final_version_id}/export/docx", headers=auth_headers)
    assert docx_res.status_code == 200
    assert "openxmlformats-officedocument.wordprocessingml.document" in docx_res.headers["content-type"]
    assert docx_res.content.startswith(b"PK\x03\x04")
    assert len(docx_res.content) > 500
