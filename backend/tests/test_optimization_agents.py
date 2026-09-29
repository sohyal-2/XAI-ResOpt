"""Unit tests for Optimizer Agent, Critic Agent, and Fact-Check Agent with anti-hallucination validation."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agents.critic_agent import CriticAgent
from app.agents.fact_check_agent import FactCheckAgent
from app.agents.models import AnalysisState
from app.agents.optimization_models import ProposedChange
from app.agents.optimizer_agent import OptimizerAgent
from app.parsing.job_description import parse_job_description
from app.parsing.models import ContactInformation, ExtractedItem, ResumeExtraction


JOB_TEXT = """Senior Backend Engineer

Required Qualifications
- 5+ years experience with Python and FastAPI microservices
- Production experience with PostgreSQL and relational databases

Preferred Qualifications
- Experience with Docker containerization
"""

RESUME_TEXT = """John Doe
john.doe@example.com | +1 555 123 4567 | San Francisco, CA

Professional Summary
Senior Software Engineer with 6+ years experience building backend APIs using Python, Django, and PostgreSQL.

Work Experience
Senior Backend Engineer at TechCorp
- Built REST APIs and microservices using Python and Django, scaling transaction throughput by 40%.
- Designed PostgreSQL database schemas and indexing strategies.
- Worked on Docker container deployment for backend services.

Technical Skills
Python, Django, FastAPI, PostgreSQL, Docker, Redis, SQL, Git
"""


@pytest.fixture
def sample_analysis_state() -> AnalysisState:
    ev_id_1 = uuid4()
    ev_id_2 = uuid4()
    ev_id_3 = uuid4()

    items = [
        ExtractedItem(
            id=ev_id_1,
            type="experience",
            text="Built REST APIs and microservices using Python and Django, scaling transaction throughput by 40%.",
            source="resume.txt",
            location="Experience: Line 8",
            confidence=0.95,
        ),
        ExtractedItem(
            id=ev_id_2,
            type="experience",
            text="Designed PostgreSQL database schemas and indexing strategies.",
            source="resume.txt",
            location="Experience: Line 9",
            confidence=0.92,
        ),
        ExtractedItem(
            id=ev_id_3,
            type="experience",
            text="Worked on Docker container deployment for backend services.",
            source="resume.txt",
            location="Experience: Line 10",
            confidence=0.90,
        ),
    ]

    resume = ResumeExtraction(
        source="resume.txt",
        raw_text=RESUME_TEXT,
        contact_information=ContactInformation(email="john.doe@example.com", phone="+1 555 123 4567"),
        sections={
            "experience": items,
            "skills": [ExtractedItem(id=uuid4(), type="skill", text="Python, Django, FastAPI, PostgreSQL, Docker, Redis", source="resume.txt", location="Skills", confidence=0.98)],
        },
        items=items,
    )

    job = parse_job_description(JOB_TEXT, "job.txt")

    return AnalysisState(
        analysis_id=uuid4(),
        owner_id=uuid4(),
        resume_extraction=resume,
        job_extraction=job,
        evidence_corpus=items,
    )


def test_optimizer_agent_grounded_rewriting(sample_analysis_state: AnalysisState) -> None:
    """Verify Optimizer Agent proposes active, grounded rewrites with valid evidence references."""
    optimizer = OptimizerAgent()
    output = optimizer.optimize(sample_analysis_state)

    assert output.status == "completed"
    assert output.total_changes_proposed >= 2
    assert output.grounded_evidence_count > 0

    # Ensure passive verb "Worked on" was upgraded to an active impact verb
    rewritten_bullets = [c.after_text for c in output.proposed_changes if c.section == "experience"]
    assert any("Engineered and deployed" in b or "Architected" in b for b in rewritten_bullets)

    # Ensure all proposed changes carry evidence IDs
    for change in output.proposed_changes:
        assert isinstance(change.evidence_ids, list)
        assert len(change.before_text) > 0
        assert len(change.after_text) > 0
        assert len(change.reason) > 0


def test_critic_agent_multi_dimensional_evaluation(sample_analysis_state: AnalysisState) -> None:
    """Verify Critic Agent evaluates quality dimensions and assigns appropriate verdicts."""
    optimizer = OptimizerAgent()
    opt_output = optimizer.optimize(sample_analysis_state)

    critic = CriticAgent()
    critic_output = critic.evaluate(opt_output.proposed_changes, job_keywords=["Python", "FastAPI", "PostgreSQL"])

    assert critic_output.status == "completed"
    assert len(critic_output.evaluations) == len(opt_output.proposed_changes)
    assert 0.0 <= critic_output.average_critic_score <= 1.0

    for eval_item in critic_output.evaluations:
        assert 0.0 <= eval_item.relevance_score <= 1.0
        assert 0.0 <= eval_item.clarity_score <= 1.0
        assert 0.0 <= eval_item.grammar_score <= 1.0
        assert 0.0 <= eval_item.ats_compatibility_score <= 1.0
        assert eval_item.verdict in ("APPROVED", "NEEDS_REVISION", "REJECTED")


def test_fact_check_detects_hallucinated_metrics(sample_analysis_state: AnalysisState) -> None:
    """Verify Fact-Check Agent detects and rejects unbacked numerical/percentage claims."""
    hallucinated_change = ProposedChange(
        change_id=uuid4(),
        section="experience",
        before_text="Designed PostgreSQL database schemas and indexing strategies.",
        after_text="Designed PostgreSQL database schemas, reducing query latency by 99.5% and saving $5M annually.",
        reason="Added impact metric",
        evidence_ids=[],
    )

    fact_checker = FactCheckAgent()
    output = fact_checker.verify(
        [hallucinated_change],
        sample_analysis_state.evidence_corpus,
        sample_analysis_state.resume_extraction.raw_text,
    )

    assert output.hallucination_count == 1
    assert len(output.rejected_changes) == 1
    assert len(output.passed_changes) == 0

    verif = output.verifications[0]
    assert verif.verdict == "FAILED"
    assert verif.metrics_verified is False
    assert any("Hallucinated metric" in flag for flag in verif.hallucination_flags)


def test_fact_check_detects_invented_skills(sample_analysis_state: AnalysisState) -> None:
    """Verify Fact-Check Agent detects and rejects newly invented technical skills not in candidate evidence."""
    invented_skill_change = ProposedChange(
        change_id=uuid4(),
        section="experience",
        before_text="Built REST APIs and microservices using Python and Django.",
        after_text="Architected distributed microservices in Rust and Kubernetes clusters with PyTorch.",
        reason="Aligned with tech stack",
        evidence_ids=[],
    )

    fact_checker = FactCheckAgent()
    output = fact_checker.verify(
        [invented_skill_change],
        sample_analysis_state.evidence_corpus,
        sample_analysis_state.resume_extraction.raw_text,
    )

    assert output.hallucination_count == 1
    assert len(output.rejected_changes) == 1

    verif = output.verifications[0]
    assert verif.verdict == "FAILED"
    assert verif.technologies_verified is False
    assert any("Invented skill/technology" in flag for flag in verif.hallucination_flags)


def test_fact_check_detects_invented_experience_and_employers(sample_analysis_state: AnalysisState) -> None:
    """Verify Fact-Check Agent rejects ungrounded company names and executive titles."""
    invented_company_change = ProposedChange(
        change_id=uuid4(),
        section="experience",
        before_text="Senior Backend Engineer at TechCorp",
        after_text="VP of Engineering at Google: Led engineering department across 5 global teams.",
        reason="Elevated impact",
        evidence_ids=[],
    )

    fact_checker = FactCheckAgent()
    output = fact_checker.verify(
        [invented_company_change],
        sample_analysis_state.evidence_corpus,
        sample_analysis_state.resume_extraction.raw_text,
    )

    assert output.hallucination_count == 1
    assert len(output.rejected_changes) == 1

    verif = output.verifications[0]
    assert verif.verdict == "FAILED"
    assert verif.companies_verified is False or verif.titles_verified is False


def test_fact_check_passes_fully_grounded_changes(sample_analysis_state: AnalysisState) -> None:
    """Verify Fact-Check Agent approves truthful, evidence-backed improvements."""
    ev_id = sample_analysis_state.evidence_corpus[0].id
    grounded_change = ProposedChange(
        change_id=uuid4(),
        section="experience",
        before_text="Built REST APIs and microservices using Python and Django, scaling transaction throughput by 40%.",
        after_text="Architected and implemented high-throughput REST APIs and microservices using Python and Django, scaling transaction throughput by 40%.",
        reason="Enhanced action verbs while preserving verified 40% throughput metric.",
        evidence_ids=[ev_id],
    )

    fact_checker = FactCheckAgent()
    output = fact_checker.verify(
        [grounded_change],
        sample_analysis_state.evidence_corpus,
        sample_analysis_state.resume_extraction.raw_text,
    )

    assert output.hallucination_count == 0
    assert len(output.passed_changes) == 1
    assert len(output.rejected_changes) == 0

    verif = output.verifications[0]
    assert verif.verdict == "PASSED"
    assert verif.is_grounded is True
    assert verif.metrics_verified is True
    assert verif.technologies_verified is True
    assert verif.companies_verified is True
