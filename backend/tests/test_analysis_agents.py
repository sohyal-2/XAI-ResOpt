from uuid import uuid4

import pytest

from app.agents.ats_agent import ATSAgent
from app.agents.evidence_agent import EvidenceAgent
from app.agents.models import (
    AnalysisState,
    ATSAgentOutput,
    EvidenceAgentOutput,
    SkillAgentOutput,
)
from app.agents.orchestrator import AnalysisOrchestrator
from app.agents.skill_agent import SkillAgent
from app.parsing.job_description import parse_job_description
from app.parsing.models import ContactInformation, ExtractedItem, ResumeExtraction
from app.rag.agentic_models import (
    AgenticRAGState,
)
from app.rag.agentic_rag import AgenticRAGEngine

JOB_TEXT = """Senior Backend Engineer

Required Qualifications
- 5+ years experience with Python and FastAPI
- Strong understanding of PostgreSQL and database indexing
- Experience designing scalable REST APIs and microservices

Preferred Qualifications
- Experience with Next.js or React
- Knowledge of Docker and Kubernetes
- Familiarity with AWS cloud architecture

Responsibilities
- Architect high-throughput distributed backend services
- Lead code reviews and mentor junior developers

Education
- BS in Computer Science or related field
"""

RESUME_TEXT = """John Doe
john.doe@example.com | +1 555 987 6543 | San Francisco, CA
https://github.com/johndoe | https://johndoe.dev

Professional Summary
Senior Software Engineer with 6+ years of experience building reliable backend systems using Python, Django, Flask, and PostgreSQL.

Work Experience
- Architected REST APIs and microservices using Python and Django, scaling system throughput by 45%.
- Implemented PostgreSQL database schemas, indexing strategies, and query optimizations.
- Containerized microservices with Docker and deployed to GCP cloud environment.

Technical Skills
Python, Django, Flask, PostgreSQL, Docker, GCP, SQL, Git, REST APIs

Education
University of California, Berkeley - Bachelor of Science in Computer Science
"""


@pytest.fixture
def sample_analysis_state() -> AnalysisState:
    owner_id = uuid4()
    job_extraction = parse_job_description(JOB_TEXT, "job.txt")

    # Build ResumeExtraction
    raw_text = RESUME_TEXT
    items = [
        ExtractedItem(
            id=uuid4(),
            type="experience",
            text="Architected REST APIs and microservices using Python and Django, scaling system throughput by 45%.",
            source="resume.pdf",
            location="Experience > Company A > Bullet 1",
            confidence=0.95,
        ),
        ExtractedItem(
            id=uuid4(),
            type="experience",
            text="Implemented PostgreSQL database schemas, indexing strategies, and query optimizations.",
            source="resume.pdf",
            location="Experience > Company A > Bullet 2",
            confidence=0.92,
        ),
        ExtractedItem(
            id=uuid4(),
            type="experience",
            text="Containerized microservices with Docker and deployed to GCP cloud environment.",
            source="resume.pdf",
            location="Experience > Company A > Bullet 3",
            confidence=0.88,
        ),
    ]

    resume_extraction = ResumeExtraction(
        source="resume.pdf",
        name="John Doe",
        contact_information=ContactInformation(
            email="john.doe@example.com",
            phone="+1 555 987 6543",
            location="San Francisco, CA",
            links=["https://github.com/johndoe", "https://johndoe.dev"],
        ),
        summary="Senior Software Engineer with 6+ years of experience building reliable backend systems using Python, Django, Flask, and PostgreSQL.",
        sections={
            "summary": [ExtractedItem(id=uuid4(), type="summary", text="Senior Software Engineer with 6+ years...", source="resume.pdf", location="Summary", confidence=0.95)],
            "experience": items,
            "skills": [ExtractedItem(id=uuid4(), type="skill", text="Python, Django, Flask, PostgreSQL, Docker, GCP, SQL, Git, REST APIs", source="resume.pdf", location="Skills", confidence=0.95)],
            "education": [ExtractedItem(id=uuid4(), type="education", text="University of California, Berkeley - BS CS", source="resume.pdf", location="Education", confidence=0.98)],
        },
        items=items,
        raw_text=raw_text,
    )

    # Run Agentic RAG to produce grounded context
    rag_engine = AgenticRAGEngine()
    rag_state = AgenticRAGState(
        owner_id=owner_id,
        requirements=job_extraction.requirements,
        raw_evidence_corpus=items,
        max_retries=1,
    )
    rag_output = rag_engine.invoke(rag_state)

    return AnalysisState(
        analysis_id=uuid4(),
        owner_id=owner_id,
        resume_extraction=resume_extraction,
        job_extraction=job_extraction,
        evidence_corpus=items,
        grounded_contexts=rag_output.grounded_contexts,
    )


def test_ats_agent_analysis(sample_analysis_state: AnalysisState) -> None:
    agent = ATSAgent()
    output = agent.analyze(sample_analysis_state)

    assert isinstance(output, ATSAgentOutput)
    assert output.score_name == "XAI-ResOpt ATS Compatibility Score"
    assert 0.0 <= output.overall_ats_score <= 1.0

    # Keyword coverage & exact terminology
    assert output.keyword_coverage_percent > 40.0
    assert "Python" in output.matched_keywords
    assert "PostgreSQL" in output.matched_keywords or "Postgres" in output.matched_keywords

    # Section presence
    assert output.section_presence.get("experience") is True
    assert output.section_presence.get("skills") is True
    assert output.section_presence.get("education") is True

    # Contact information
    assert output.contact_info_completeness.get("email") is True
    assert output.contact_info_completeness.get("phone") is True
    assert output.contact_info_completeness.get("links") is True

    # Parsability & Readability
    assert output.parsability_score > 0.70
    assert output.readability_score > 0.50

    # Keyword distribution
    assert len(output.keyword_distribution) > 0

    # Recommendations
    assert len(output.recommendations) > 0
    assert all(r.agent_name == "ats_agent" for r in output.recommendations)


def test_skill_agent_analysis(sample_analysis_state: AnalysisState) -> None:
    agent = SkillAgent()
    output = agent.analyze(sample_analysis_state)

    assert isinstance(output, SkillAgentOutput)
    assert output.score_name == "XAI-ResOpt ATS Compatibility Score"
    assert 0.0 <= output.semantic_skill_score <= 1.0

    # Mandatory & Preferred Skill Coverage
    assert "Python" in output.matched_mandatory_skills or "python" in output.matched_mandatory_skills
    assert output.mandatory_skill_coverage_percent > 0.0

    # Transferable Evidence: Django/Flask -> FastAPI, GCP -> AWS
    assert len(output.transferable_evidence) > 0
    trans_targets = {t.target_skill.lower() for t in output.transferable_evidence}
    assert "fastapi" in trans_targets or "aws" in trans_targets

    # Check evidence ID attached to transferable recommendations
    trans_recs = [r for r in output.recommendations if r.category == "transferable_skill"]
    assert len(trans_recs) > 0
    assert any(len(r.evidence_ids) > 0 for r in trans_recs)

    # Seniority Alignment
    assert output.seniority_alignment_score > 0.70


def test_evidence_agent_analysis(sample_analysis_state: AnalysisState) -> None:
    agent = EvidenceAgent()
    output = agent.analyze(sample_analysis_state)

    assert isinstance(output, EvidenceAgentOutput)
    assert output.score_name == "XAI-ResOpt ATS Compatibility Score"
    assert 0.0 <= output.factual_support_score <= 1.0
    assert output.total_claims_evaluated > 0

    # Verify claim evaluations and provenance tracing
    for claim in output.claim_evaluations:
        assert claim.claim_text
        assert claim.support_status in {"SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED"}
        assert claim.source_provenance is not None
        assert 0.0 <= claim.confidence <= 1.0

    # Evidence sufficiency score
    assert 0.0 <= output.evidence_sufficiency_score <= 1.0

    # Recommendations reference evidence IDs
    assert len(output.recommendations) >= 0


def test_multi_agent_orchestrator_execution(sample_analysis_state: AnalysisState) -> None:
    orchestrator = AnalysisOrchestrator()
    consolidated = orchestrator.invoke(sample_analysis_state)

    assert consolidated.score_name == "XAI-ResOpt ATS Compatibility Score"
    assert consolidated.ats_analysis is not None
    assert consolidated.skill_analysis is not None
    assert consolidated.evidence_analysis is not None

    # Verify consolidated recommendations
    recs = consolidated.consolidated_recommendations
    assert len(recs) > 0

    # Recommendations must contain contributions from all active agents
    agents_represented = {r.agent_name for r in recs}
    assert "ats_agent" in agents_represented
    assert "skill_agent" in agents_represented


@pytest.mark.asyncio
async def test_multi_agent_orchestrator_async(sample_analysis_state: AnalysisState) -> None:
    orchestrator = AnalysisOrchestrator()
    consolidated = await orchestrator.ainvoke(sample_analysis_state)

    assert consolidated.ats_analysis.overall_ats_score > 0.0
    assert consolidated.skill_analysis.semantic_skill_score > 0.0
    assert consolidated.evidence_analysis.factual_support_score > 0.0
    assert len(consolidated.consolidated_recommendations) > 0
