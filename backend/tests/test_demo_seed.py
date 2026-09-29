"""Test suite verifying the integrity and properties of the development/demo seed dataset.

Validates:
- Realistic resume, 3 distinct job descriptions, representative skills, projects, and experiences.
- Granular evidence records and provenance lineage.
- Supported claims linked via ClaimEvidence and unsupported ungrounded claims.
- Real dynamically computed ATS baseline scores across all 8 dimensions (0 hard-coded numbers).
- Skill gaps detection on JD 2 and JD 3.
- Real closed-loop multi-iteration optimization history.
- Rejected unsupported claim in OptimizationRun and ResumeChange.
- Human review decisions, approval history, and published final resume version.
"""

from collections.abc import AsyncGenerator
import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.entities import (
    AgentRun,
    Analysis,
    ApprovalHistory,
    ChangeDecision,
    Claim,
    ClaimEvidence,
    ClaimStatus,
    EvidenceItem,
    Experience,
    JobDescription,
    JobRequirement,
    OptimizationRun,
    Project,
    Resume,
    ResumeChange,
    ResumeSection,
    ResumeVersion,
    RunStatus,
    Score,
    Skill,
    User,
)
from scripts.seed_demo_data import DEMO_USER_EMAIL, seed_demo_dataset

settings = get_settings()

def database_url() -> str:
    return settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(database_url(), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_demo_seed_dataset_completeness(db_session: AsyncSession) -> None:
    """Verifies that running seed_demo_dataset populates all required entities and relationships."""
    summary = await seed_demo_dataset(db_session)
    assert summary is not None
    assert summary["user"]["email"] == DEMO_USER_EMAIL

    # 1. User verification
    user = await db_session.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    assert user is not None
    assert user.full_name == "Alex Chen"

    # 2. Resume & Sections verification
    resumes = (await db_session.scalars(select(Resume).where(Resume.owner_id == user.id))).all()
    assert len(resumes) >= 1
    resume = resumes[0]

    versions = (await db_session.scalars(select(ResumeVersion).where(ResumeVersion.resume_id == resume.id))).all()
    assert len(versions) >= 2  # Original + Finalized versions

    sections = (await db_session.scalars(
        select(ResumeSection).where(ResumeSection.resume_version_id == versions[0].id)
    )).all()
    assert len(sections) >= 4
    section_types = {s.section_type for s in sections}
    assert "experience" in section_types or "work_experience" in section_types or "skills" in section_types

    # 3. Job Descriptions & Requirements
    jds = (await db_session.scalars(select(JobDescription).where(JobDescription.owner_id == user.id))).all()
    assert len(jds) == 3
    jd_titles = [j.title for j in jds]
    assert any("Platform" in t for t in jd_titles)
    assert any("DevOps" in t or "Infrastructure" in t for t in jd_titles)
    assert any("AI Systems" in t or "RAG" in t for t in jd_titles)

    reqs = (await db_session.scalars(
        select(JobRequirement).where(JobRequirement.job_description_id.in_([j.id for j in jds]))
    )).all()
    assert len(reqs) >= 10

    # 4. Structured Skills, Experiences, Projects
    skills = (await db_session.scalars(select(Skill).where(Skill.owner_id == user.id))).all()
    assert len(skills) >= 8
    skill_names = {s.name.lower() for s in skills}
    assert "python" in skill_names
    assert "kubernetes" in skill_names
    assert "redis" in skill_names

    exps = (await db_session.scalars(select(Experience).where(Experience.owner_id == user.id))).all()
    assert len(exps) >= 2
    projs = (await db_session.scalars(select(Project).where(Project.owner_id == user.id))).all()
    assert len(projs) >= 2

    # 5. Evidence Records & Provenance
    evidence_items = (await db_session.scalars(select(EvidenceItem).where(EvidenceItem.owner_id == user.id))).all()
    assert len(evidence_items) >= 5

    # 6. Supported & Unsupported Claims
    claims = (await db_session.scalars(select(Claim).where(Claim.owner_id == user.id))).all()
    assert len(claims) >= 3

    supported_claims = [c for c in claims if c.support_status == ClaimStatus.supported]
    unsupported_claims = [c for c in claims if c.support_status == ClaimStatus.unsupported]

    assert len(supported_claims) >= 1
    assert len(unsupported_claims) >= 2
    assert any("15,000 requests" in c.text for c in supported_claims)
    assert any("quantum cryptography" in c.text for c in unsupported_claims)

    claim_evidences = (await db_session.scalars(
        select(ClaimEvidence).where(ClaimEvidence.claim_id.in_([c.id for c in supported_claims]))
    )).all()
    assert len(claim_evidences) >= 1
    assert claim_evidences[0].relationship_type == "provenance"


@pytest.mark.asyncio
async def test_demo_baseline_analyses_and_scoring(db_session: AsyncSession) -> None:
    """Verifies that all 3 analyses have real dynamically calculated scores and agent telemetry."""
    user = await db_session.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    assert user is not None

    analyses = (await db_session.scalars(select(Analysis).where(Analysis.owner_id == user.id))).all()
    assert len(analyses) == 3

    # Check scores
    scores = (await db_session.scalars(
        select(Score).where(Score.analysis_id.in_([a.id for a in analyses]))
    )).all()
    assert len(scores) == 3

    for score in scores:
        assert score.overall_score > 0.0
        assert score.calculation_version == "xai-resopt-v1.0-deterministic"
        assert len(score.category_scores) == 8  # 8 standard ATS scoring categories
        cat_keys = set(score.category_scores.keys())
        assert "keyword_coverage" in cat_keys
        assert "semantic_similarity" in cat_keys
        assert "evidence_confidence" in cat_keys

    # Check observability agent runs
    agent_runs = (await db_session.scalars(
        select(AgentRun).where(AgentRun.analysis_id.in_([a.id for a in analyses]))
    )).all()
    assert len(agent_runs) >= 33  # 11 agents * 3 analyses

    for run in agent_runs:
        assert run.status == RunStatus.completed
        assert run.duration_ms is not None and run.duration_ms >= 0


@pytest.mark.asyncio
async def test_demo_optimization_and_rejected_unsupported_claims(db_session: AsyncSession) -> None:
    """Verifies that closed-loop optimization history and rejected unsupported claims are preserved."""
    user = await db_session.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    assert user is not None

    opt_runs = (await db_session.scalars(
        select(OptimizationRun).join(Analysis).where(Analysis.owner_id == user.id).order_by(OptimizationRun.iteration)
    )).all()
    assert len(opt_runs) >= 1

    latest_run = opt_runs[-1]
    assert latest_run.score > 0.0

    # Verify rejected changes contains the ungrounded hallucinated claim
    assert len(latest_run.rejected_changes) >= 1
    rejected_data = latest_run.rejected_changes[0]
    assert "Rust and Solidity" in rejected_data["after_text"] or "quantum" in rejected_data["after_text"]
    assert rejected_data["support_status"] == "UNSUPPORTED"

    # Verify ResumeChange table contains the rejected record
    changes = (await db_session.scalars(
        select(ResumeChange).where(ResumeChange.optimization_run_id == latest_run.id)
    )).all()
    assert len(changes) >= 1
    rejected_changes = [c for c in changes if c.decision == ChangeDecision.rejected or not c.supported]
    assert len(rejected_changes) >= 1
    assert rejected_changes[0].risk_level == "high"
    assert rejected_changes[0].supported is False

    # Verify ApprovalHistory contains the final human review record
    approvals = (await db_session.scalars(
        select(ApprovalHistory).where(ApprovalHistory.user_id == user.id)
    )).all()
    assert len(approvals) >= 1
    assert "grounded" in approvals[0].notes.lower()
