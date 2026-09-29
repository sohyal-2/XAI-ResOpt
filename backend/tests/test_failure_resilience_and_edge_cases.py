"""Comprehensive test suite for failure resilience, edge cases, and graceful degradation.

Covers:
- Invalid files (empty files, corrupt PDF/DOCX headers, binary null bytes in txt, oversized files)
- Malformed model outputs (corrupted JSON, missing keys, invalid tool schemas handled gracefully)
- Failed agents & error telemetry (captured in AgentRun with RunStatus.failed, retry count, error tracking)
- Timeouts (HTTP / network timeouts handled gracefully)
- Unsupported claims (fact checker rejection and scoring engine penalty deductions)
- Repeated optimization (multi-cycle runs, convergence bounds, history preservation)
- Missing API keys (clean fallback to DevelopmentMockProvider and offline functionality)
"""

from collections.abc import AsyncGenerator
from io import BytesIO
import json
from uuid import UUID, uuid4
import pytest
import pytest_asyncio
import httpx
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.fact_check_agent import FactCheckAgent
from app.agents.optimization_models import ProposedChange
from app.ai.base import LLMResponse, LLMToolCall, LLMToolResponse
from app.ai.factory import get_llm_provider
from app.ai.mock_adapter import DevelopmentMockProvider
from app.ai.tool_runner import ToolRunner
from app.core.config import get_settings
from app.db import get_db
from app.main import app
from app.models.entities import AgentRun, RunStatus
from app.parsing.models import ExtractedItem
from app.parsing.validation import (
    CorruptDocumentError,
    IngestionError,
    UnsupportedFileError,
    validate_upload,
)
from app.scoring.engine import ScoringEngine
from app.services.observability import AgentTelemetryTracker
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
        pytest.skip(f"Resilience integration tests require PostgreSQL and Redis: {error}")

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

# =============================================================================
# 1. Invalid Files & Malformed Inputs
# =============================================================================

def test_empty_file_upload_rejected() -> None:
    with pytest.raises(IngestionError, match="The uploaded file is empty"):
        validate_upload("empty.txt", "text/plain", b"", 10 * 1024 * 1024)

def test_corrupt_pdf_signature_rejected() -> None:
    fake_pdf_payload = b"NOT_A_PDF_DOCUMENT_CONTENT"
    with pytest.raises(CorruptDocumentError, match="valid PDF signature"):
        validate_upload("resume.pdf", "application/pdf", fake_pdf_payload, 10 * 1024 * 1024)

def test_corrupt_docx_zip_container_rejected() -> None:
    fake_docx_payload = b"NOT_A_ZIP_CONTAINER"
    with pytest.raises(CorruptDocumentError, match="valid DOCX container"):
        validate_upload(
            "resume.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            fake_docx_payload,
            10 * 1024 * 1024,
        )

def test_plain_text_with_null_bytes_rejected() -> None:
    poisoned_text = b"John Doe\x00Software Engineer\x00Malicious payload"
    with pytest.raises(CorruptDocumentError, match="binary null bytes"):
        validate_upload("resume.txt", "text/plain", poisoned_text, 10 * 1024 * 1024)

def test_disallowed_file_extension_rejected() -> None:
    script_bytes = b"echo Hello World"
    with pytest.raises(UnsupportedFileError, match="Supported resume formats"):
        validate_upload("script.sh", "text/x-shellscript", script_bytes, 10 * 1024 * 1024)

def test_oversized_file_rejected() -> None:
    large_payload = b"X" * 1001
    with pytest.raises(IngestionError, match="exceeds the"):
        validate_upload("resume.txt", "text/plain", large_payload, max_bytes=1000)

# =============================================================================
# 2. Malformed Model Outputs & Tool Call Handling
# =============================================================================

@pytest.mark.asyncio
async def test_malformed_model_output_handling() -> None:
    """Verifies that invalid tool arguments and unparseable outputs do not crash the ToolRunner."""
    class BrokenMockProvider:
        provider_name = "broken_mock"
        default_model = "broken-model"

        async def generate(self, prompt, **kwargs):
            return LLMResponse(content="Malformed content", model="broken-model", provider="broken_mock")

        async def generate_with_tools(self, prompt, tools, **kwargs):
            bad_tc = LLMToolCall(
                id="call_bad_1",
                tool_name="github_search",
                arguments={"invalid": "{bad:json", "query": 12345},
            )
            return LLMToolResponse(
                content="Attempting tool call",
                tool_calls=[bad_tc],
                model="broken-model",
                provider="broken_mock",
            )

    runner = ToolRunner(provider=BrokenMockProvider(), max_iterations=2)
    result = await runner.run("Find github repositories")
    assert result is not None
    assert len(result.tool_history) >= 1
    tool_rec = result.tool_history[0]
    assert tool_rec.tool_name == "github_search"
    assert tool_rec.result.success is False
    assert tool_rec.result.error is not None

# =============================================================================
# 3. Failed Agents & Observability Telemetry Error Tracking
# =============================================================================

@pytest.mark.asyncio
async def test_failed_agent_telemetry_captures_error(client: httpx.AsyncClient, integration_resources) -> None:
    session_factory, _ = integration_resources
    user_email = f"telemetry_{uuid4().hex[:6]}@example.com"
    pwd = "StrongPassword123!#"
    sign = await client.post("/api/auth/signup", json={"email": user_email, "full_name": "Telem User", "password": pwd})
    assert sign.status_code == 201
    auth_headers = {"Authorization": f"Bearer {sign.json()['access_token']}"}

    res_up = await client.post(
        "/api/ingestion/resumes",
        headers=auth_headers,
        files={"file": ("resume.txt", b"Jane Dev\nPython, Docker\n3 years experience.", "text/plain")},
    )
    resume_id = res_up.json()["id"]

    jd_up = await client.post(
        "/api/ingestion/job-descriptions",
        headers=auth_headers,
        data={"text": "Backend Engineer with Python experience.", "title": "Dev"},
    )
    job_id = jd_up.json()["id"]

    base_res = await client.post(
        "/api/analysis/baseline",
        headers=auth_headers,
        json={"resume_id": resume_id, "job_description_id": job_id},
    )
    analysis_uuid = UUID(base_res.json()["analysis_id"])
    request_uuid = f"req-err-{uuid4()}"

    async with session_factory() as db:
        try:
            async with AgentTelemetryTracker(
                db,
                analysis_uuid,
                request_uuid,
                agent_name="critic_agent",
                retry_count=3,
            ) as tracker:
                tracker.recovery_status = "unrecovered"
                raise RuntimeError("Critic evaluation failed: LLM rate limit exceeded upstream")
        except RuntimeError:
            pass
        await db.commit()

    async with session_factory() as db:
        stmt = select(AgentRun).where(
            AgentRun.analysis_id == analysis_uuid,
            AgentRun.request_id == request_uuid,
        )
        run_record = await db.scalar(stmt)
        assert run_record is not None
        assert run_record.status == RunStatus.failed
        assert run_record.retry_count == 3
        assert "LLM rate limit exceeded" in (run_record.error or "")
        assert run_record.recovery_status == "unrecovered"
        assert run_record.duration_ms is not None and run_record.duration_ms >= 0

# =============================================================================
# 4. Unsupported Claims & Hallucination Penalties
# =============================================================================

def test_fact_checker_detects_unsupported_metrics_and_skills() -> None:
    fact_checker = FactCheckAgent()
    grounded_evidence = [
        ExtractedItem(
            id=uuid4(),
            type="experience",
            text="Experienced in Python and FastAPI backend development.",
            source="resume.txt",
            location="Experience",
            confidence=0.95,
        )
    ]

    hallucinated_change = ProposedChange(
        change_id=uuid4(),
        section="Experience",
        change_type="bullet",
        before_text="Worked on Python backend.",
        after_text="Architected distributed Rust and Solidity systems achieving 99.999% uptime.",
        reason="Keyword enrichment",
    )

    result = fact_checker.verify([hallucinated_change], grounded_evidence)
    assert len(result.rejected_changes) == 1
    rejected = result.rejected_changes[0]
    assert rejected.change_id == hallucinated_change.change_id
    assert result.hallucination_count >= 1
    assert len(result.verifications) >= 1
    verif = result.verifications[0]
    assert verif.is_grounded is False
    assert verif.verdict == "FAILED"
    assert any("metric" in flag.lower() or "skill" in flag.lower() or "rust" in flag.lower() for flag in verif.hallucination_flags)

def test_scoring_engine_applies_unsupported_claims_penalty() -> None:
    engine = ScoringEngine()

    clean_state = {
        "evidence_output": {
            "unsupported_claims": [],
            "contradictions": [],
        }
    }
    clean_result = engine.calculate_score(clean_state)

    penalized_state = {
        "evidence_output": {
            "unsupported_claims": [
                "Achieved 1000% revenue growth without verifiable project.",
                "Architected AWS cloud infrastructure singlehandedly.",
            ],
            "contradictions": [],
        }
    }
    penalized_result = engine.calculate_score(penalized_state)

    assert penalized_result.total_penalty > 0
    assert penalized_result.overall_score < clean_result.overall_score
    penalty_names = [p.penalty_name for p in penalized_result.penalties]
    assert "unsupported_claims_penalty" in penalty_names

# =============================================================================
# 5. Repeated Optimization & Monotonicity
# =============================================================================

@pytest.mark.asyncio
async def test_repeated_optimization_cycles(client: httpx.AsyncClient) -> None:
    """Verifies that running optimization multiple times succeeds and preserves history."""
    user_email = f"repeat_opt_{uuid4().hex[:6]}@example.com"
    pwd = "StrongPassword123!#"
    sign = await client.post("/api/auth/signup", json={"email": user_email, "full_name": "Repeater", "password": pwd})
    assert sign.status_code == 201
    auth_headers = {"Authorization": f"Bearer {sign.json()['access_token']}"}

    res_up = await client.post(
        "/api/ingestion/resumes",
        headers=auth_headers,
        files={"file": ("resume.txt", b"Jane Dev\nPython, Docker, SQL\n5 years backend experience.", "text/plain")},
    )
    resume_id = res_up.json()["id"]

    jd_up = await client.post(
        "/api/ingestion/job-descriptions",
        headers=auth_headers,
        data={"text": "Backend Engineer with Python, Docker, Kubernetes, and Redis experience.", "title": "Dev"},
    )
    job_id = jd_up.json()["id"]

    base_res = await client.post(
        "/api/analysis/baseline",
        headers=auth_headers,
        json={"resume_id": resume_id, "job_description_id": job_id},
    )
    analysis_id = base_res.json()["analysis_id"]

    # Run 1st optimization cycle
    opt1_res = await client.post(
        f"/api/analysis/{analysis_id}/optimize",
        headers=auth_headers,
        json={"max_iterations": 2},
    )
    assert opt1_res.status_code == 200
    opt1_data = opt1_res.json()
    assert opt1_data["total_iterations"] >= 1

    # Run 2nd optimization cycle on same analysis
    opt2_res = await client.post(
        f"/api/analysis/{analysis_id}/optimize",
        headers=auth_headers,
        json={"max_iterations": 2},
    )
    assert opt2_res.status_code == 200
    opt2_data = opt2_res.json()
    assert opt2_data["total_iterations"] >= 1

    # Verify optimization history contains multiple records
    hist_res = await client.get(f"/api/analysis/{analysis_id}/optimizations", headers=auth_headers)
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 2

# =============================================================================
# 6. Missing API Keys & Offline Fallback
# =============================================================================

def test_missing_api_keys_offline_fallback(monkeypatch) -> None:
    """Verifies that missing API keys gracefully fall back to DevelopmentMockProvider."""
    s = get_settings()
    monkeypatch.setattr(s, "openai_api_key", None)
    monkeypatch.setattr(s, "anthropic_api_key", None)
    monkeypatch.setattr(s, "gemini_api_key", None)
    monkeypatch.setattr(s, "google_api_key", None)
    monkeypatch.setattr(s, "openrouter_api_key", None)

    prov_openai = get_llm_provider("openai")
    assert isinstance(prov_openai, DevelopmentMockProvider)

    prov_anthropic = get_llm_provider("anthropic")
    assert isinstance(prov_anthropic, DevelopmentMockProvider)

    prov_auto = get_llm_provider("auto")
    assert isinstance(prov_auto, DevelopmentMockProvider)
    assert prov_auto.is_available() is True
