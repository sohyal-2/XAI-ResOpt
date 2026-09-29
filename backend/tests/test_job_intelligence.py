from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import (
    JobRequirement,
    JobRequirementKind,
    User,
)
from app.parsing.job_description import parse_job_description
from app.parsing.models import (
    JobDescriptionExtraction,
    JobRequirementExtraction,
    RequirementCategory,
)
from app.parsing.taxonomy import get_synonyms_for_canonical, normalize_skill_name
from app.services.ingestion import store_job_description

settings = get_settings()

JOB_DESCRIPTION = """Senior Staff Full-Stack Engineer

About the Role
We are seeking an experienced Senior Staff Full-Stack Engineer to lead the architecture of our next-generation platform.

Must Have / Required Qualifications
- 5+ years of software engineering experience with Python and FastAPI
- Strong expertise with React.js and TypeScript
- Experience with PostgreSQL and relational database design
- Proven track record of building microservices and REST APIs
- BS or MS degree in Computer Science or related STEM field

Preferred Qualifications
- Experience with Next.js and GraphQL
- Hands-on experience with Apache Kafka and Redis caching
- Familiarity with fintech, banking, or payments systems
- AWS Certified Solutions Architect or equivalent certification

Nice to Have
- Knowledge of Kubernetes and Terraform for infrastructure
- Exposure to Large Language Models (LLM) and Agentic RAG systems

Responsibilities
- Architect, build, and maintain high-throughput distributed systems
- Lead cross-functional collaboration and mentor junior engineers
- Drive technical system design and code quality reviews

Tooling & Technologies
- Docker, Git, GitHub Actions, and Datadog

Soft Skills
- Excellent verbal and written communication skills
- Demonstrated problem-solving ability and team leadership

Implied Requirements
- Familiarity with fast-paced startup environments and willingness to learn new technologies
"""


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1),
        pool_pre_ping=True,
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as error:
        await engine.dispose()
        pytest.skip(f"PostgreSQL integration test requires active database: {error}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def test_extracts_all_structured_requirement_categories() -> None:
    extraction = parse_job_description(JOB_DESCRIPTION, "senior-staff-jd.txt")

    categories = {req.category for req in extraction.requirements}
    assert RequirementCategory.years_experience in categories
    assert RequirementCategory.skill in categories
    assert RequirementCategory.responsibility in categories
    assert RequirementCategory.education in categories
    assert RequirementCategory.certification in categories
    assert RequirementCategory.domain_knowledge in categories
    assert RequirementCategory.tooling in categories
    assert RequirementCategory.soft_skill in categories
    assert RequirementCategory.implied_requirement in categories

    # Seniority indicators
    assert "Senior" in extraction.seniority_indicators or "Staff" in extraction.seniority_indicators

    # Years of experience
    assert extraction.years_of_experience == 5
    years_req = next(r for r in extraction.requirements if r.category == RequirementCategory.years_experience)
    assert years_req.years_experience == 5
    assert years_req.kind == "mandatory"

    # Responsibilities
    assert len(extraction.responsibilities) >= 2
    assert any("Architect" in resp for resp in extraction.responsibilities)

    # Education
    assert len(extraction.education_requirements) >= 1
    assert any("Computer Science" in edu for edu in extraction.education_requirements)

    # Certifications
    assert len(extraction.certifications) >= 1
    assert any("AWS" in cert for cert in extraction.certifications)

    # Domain knowledge
    assert len(extraction.domain_knowledge) >= 1
    assert any("fintech" in dk.lower() for dk in extraction.domain_knowledge)

    # Soft skills
    assert len(extraction.soft_skills) >= 1
    assert any("communication" in s.lower() for s in extraction.soft_skills)

    # Implied requirements
    assert len(extraction.implied_requirements) >= 1
    assert any("startup" in imp.lower() or "familiarity" in imp.lower() for imp in extraction.implied_requirements)

    # Tooling
    tool_canonicals = {t.canonical for t in extraction.tooling}
    assert {"docker", "git", "github_actions", "datadog"} & tool_canonicals or len(extraction.tooling) > 0


def test_classifies_mandatory_preferred_nice_to_have_contextual() -> None:
    extraction = parse_job_description(JOB_DESCRIPTION, "senior-staff-jd.txt")

    # Mandatory checks
    mandatory_reqs = [r for r in extraction.requirements if r.kind == "mandatory"]
    assert any("5+ years" in r.text for r in mandatory_reqs)
    assert any("React" in r.text for r in mandatory_reqs)

    # Preferred checks
    preferred_reqs = [r for r in extraction.requirements if r.kind == "preferred"]
    assert any("Next.js" in r.text or "Kafka" in r.text or "fintech" in r.text for r in preferred_reqs)

    # Nice to have checks
    nice_to_have_reqs = [r for r in extraction.requirements if r.kind == "nice_to_have"]
    assert any("Kubernetes" in r.text or "LLM" in r.text or "Agentic RAG" in r.text for r in nice_to_have_reqs)

    # Contextual checks
    contextual_reqs = [r for r in extraction.requirements if r.kind == "contextual"]
    assert any("Architect, build, and maintain" in r.text for r in contextual_reqs)

    # Structured skill categorization
    mandatory_skill_canonicals = {t.canonical for t in extraction.mandatory_skills}
    assert "python" in mandatory_skill_canonicals
    assert "react" in mandatory_skill_canonicals
    assert "typescript" in mandatory_skill_canonicals

    preferred_skill_canonicals = {t.canonical for t in extraction.preferred_skills}
    assert "next.js" in preferred_skill_canonicals or "graphql" in preferred_skill_canonicals or "kafka" in preferred_skill_canonicals

    nice_to_have_skill_canonicals = {t.canonical for t in extraction.nice_to_have_skills}
    assert "kubernetes" in nice_to_have_skill_canonicals or "terraform" in nice_to_have_skill_canonicals or "rag" in nice_to_have_skill_canonicals


def test_normalizes_related_terms_without_losing_originals() -> None:
    sample = """Frontend Engineer
Requirements
- React
- React.js
- ReactJS
- Node.js
- NodeJS
- K8s
- Kubernetes
- PostgreSQL
- Postgres
- PGSQL
- AWS
- Amazon Web Services
- TypeScript
- TS
- C++
- CPP
- .NET
- DotNet
"""
    extraction = parse_job_description(sample, "normalization-test.txt")

    # React family
    react_reqs = [r for r in extraction.requirements if "react" in r.normalized_terms]
    assert len(react_reqs) >= 3
    assert {term.original for r in react_reqs for term in r.terms if term.canonical == "react"} == {"React", "React.js", "ReactJS"}
    assert all("ReactJS" in term.synonyms for r in react_reqs for term in r.terms if term.canonical == "react")

    # Node family
    node_reqs = [r for r in extraction.requirements if "node.js" in r.normalized_terms]
    assert len(node_reqs) >= 2
    assert {term.original for r in node_reqs for term in r.terms if term.canonical == "node.js"} == {"Node.js", "NodeJS"}

    # Kubernetes family
    k8s_reqs = [r for r in extraction.requirements if "kubernetes" in r.normalized_terms]
    assert len(k8s_reqs) >= 2
    assert {term.original for r in k8s_reqs for term in r.terms if term.canonical == "kubernetes"} == {"K8s", "Kubernetes"}

    # Postgres family
    pg_reqs = [r for r in extraction.requirements if "postgresql" in r.normalized_terms]
    assert len(pg_reqs) >= 3
    assert {term.original for r in pg_reqs for term in r.terms if term.canonical == "postgresql"} == {"PostgreSQL", "Postgres", "PGSQL"}

    # AWS family
    aws_reqs = [r for r in extraction.requirements if "aws" in r.normalized_terms]
    assert len(aws_reqs) >= 2
    assert {term.original for r in aws_reqs for term in r.terms if term.canonical == "aws"} == {"AWS", "Amazon Web Services"}


def test_taxonomy_helper_functions() -> None:
    assert normalize_skill_name("React.js") == "react"
    assert normalize_skill_name("ReactJS") == "react"
    assert normalize_skill_name("REACT") == "react"
    assert normalize_skill_name("PostgreSQL") == "postgresql"
    assert normalize_skill_name("k8s") == "kubernetes"
    assert normalize_skill_name("Amazon Web Services") == "aws"

    synonyms = get_synonyms_for_canonical("react")
    assert "React" in synonyms
    assert "React.js" in synonyms
    assert "ReactJS" in synonyms


def test_structured_data_validation() -> None:
    extraction = parse_job_description(JOB_DESCRIPTION, "sample-jd.txt")
    assert isinstance(extraction, JobDescriptionExtraction)
    assert extraction.source == "sample-jd.txt"
    assert extraction.raw_text == JOB_DESCRIPTION
    assert len(extraction.requirements) > 0

    for req in extraction.requirements:
        assert isinstance(req, JobRequirementExtraction)
        assert req.text
        assert req.kind in {"mandatory", "preferred", "nice_to_have", "contextual"}
        assert isinstance(req.category, RequirementCategory)
        assert 0.0 <= req.confidence <= 1.0
        assert req.source_location

    with pytest.raises(ValidationError):
        # Empty text should fail validation
        JobRequirementExtraction(text="", source_location="line 1", confidence=0.9)

    with pytest.raises(ValidationError):
        # Out-of-bounds confidence should fail validation
        JobRequirementExtraction(text="Valid", source_location="line 1", confidence=1.5)


@pytest.mark.asyncio
async def test_job_description_database_persistence(db_session: AsyncSession) -> None:
    user_id = uuid4()
    user = User(id=user_id, email=f"recruiter-{user_id}@example.com", full_name="Recruiter", password_hash="hash")
    db_session.add(user)
    await db_session.commit()

    try:
        extraction = parse_job_description(JOB_DESCRIPTION, "job-upload.pdf")
        job = await store_job_description(db_session, user_id, extraction)

        assert job.id is not None
        assert job.title == extraction.title
        assert job.source_uri == "job-upload.pdf"

        result = await db_session.scalars(select(JobRequirement).where(JobRequirement.job_description_id == job.id))
        persisted_reqs = list(result)
        assert len(persisted_reqs) == len(extraction.requirements)

        # Verify persisted fields
        kinds = {r.kind for r in persisted_reqs}
        assert JobRequirementKind.mandatory in kinds or "mandatory" in kinds
        assert any(r.years_experience == 5 for r in persisted_reqs)
        assert any("python" in r.normalized_terms for r in persisted_reqs)
        assert any(r.source_location is not None for r in persisted_reqs)
        assert any(len(r.synonym_groups) > 0 for r in persisted_reqs)
    finally:
        await db_session.execute(delete(User).where(User.id == user_id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_store_job_description_unit() -> None:
    from unittest.mock import AsyncMock, MagicMock

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    user_id = uuid4()
    extraction = parse_job_description(JOB_DESCRIPTION, "unit-test-job.txt")
    job = await store_job_description(mock_session, user_id, extraction)

    assert job.owner_id == user_id
    assert job.title == extraction.title
    assert mock_session.add.call_count == 1 + len(extraction.requirements)
    assert mock_session.commit.call_count == 1
    assert mock_session.refresh.call_count == 1

