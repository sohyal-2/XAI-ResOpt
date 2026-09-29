"""Unit tests for the deterministic XAI-ResOpt ATS Compatibility Scoring Engine."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agents.ats_agent import ATSAgent
from app.agents.evidence_agent import EvidenceAgent
from app.agents.models import (
    AnalysisState,
    ClaimEvaluation,
    FormattingRisk,
)
from app.agents.skill_agent import SkillAgent
from app.parsing.job_description import parse_job_description
from app.parsing.models import ContactInformation, ExtractedItem, ResumeExtraction
from app.rag.agentic_models import AgenticRAGState
from app.rag.agentic_rag import AgenticRAGEngine
from app.scoring import ScoringEngine, ScoringWeights

JOB_TEXT = """Senior Backend Engineer

Required Qualifications
- 5+ years experience with Python and FastAPI microservices
- Production experience with PostgreSQL and relational databases

Preferred Qualifications
- Experience with AWS cloud deployment
- Experience with Docker containerization
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
        raw_text=RESUME_TEXT,
    )

    rag_engine = AgenticRAGEngine()
    rag_state = AgenticRAGState(
        owner_id=owner_id,
        requirements=job_extraction.requirements,
        raw_evidence_corpus=items,
        max_retries=1,
    )
    rag_output = rag_engine.invoke(rag_state)

    state = AnalysisState(
        analysis_id=uuid4(),
        owner_id=owner_id,
        resume_extraction=resume_extraction,
        job_extraction=job_extraction,
        evidence_corpus=items,
        grounded_contexts=rag_output.grounded_contexts,
    )

    # Run agents to populate state
    state.ats_output = ATSAgent().analyze(state)
    state.skill_output = SkillAgent().analyze(state)
    state.evidence_output = EvidenceAgent().analyze(state)

    return state


def test_deterministic_scoring_reproducibility(sample_analysis_state: AnalysisState) -> None:
    """Verify that multiple runs with the exact same input produce 100% deterministic output."""
    engine = ScoringEngine()
    
    result_1 = engine.calculate_score(sample_analysis_state)
    result_2 = engine.calculate_score(sample_analysis_state)
    result_3 = engine.calculate_score(sample_analysis_state)

    assert result_1.score_name == "XAI-ResOpt ATS Compatibility Score"
    assert result_1.calculation_version == "xai-resopt-v1.0-deterministic"
    assert result_1.overall_score == result_2.overall_score == result_3.overall_score
    assert result_1.raw_weighted_score == result_2.raw_weighted_score == result_3.raw_weighted_score
    assert result_1.total_penalty == result_2.total_penalty == result_3.total_penalty
    
    for cat in result_1.category_scores:
        assert result_1.category_scores[cat].raw_score == result_2.category_scores[cat].raw_score
        assert result_1.category_scores[cat].weighted_contribution == result_3.category_scores[cat].weighted_contribution


def test_custom_weights_and_normalization(sample_analysis_state: AnalysisState) -> None:
    """Verify configurable weights and automatic normalization."""
    engine = ScoringEngine()
    
    custom_weights = ScoringWeights(
        keyword_coverage_weight=0.40,
        semantic_similarity_weight=0.40,
        requirement_coverage_weight=0.10,
        evidence_confidence_weight=0.05,
        experience_alignment_weight=0.05,
        section_completeness_weight=0.0,
        formatting_safety_weight=0.0,
        skill_match_weight=0.0,
    )
    
    result = engine.calculate_score(sample_analysis_state, custom_weights=custom_weights)
    norm = custom_weights.normalized_weights()
    
    assert sum(norm.values()) == pytest.approx(1.0, rel=1e-5)
    assert result.category_scores["keyword_coverage"].weight == round(norm["keyword_coverage"], 4)
    assert 0.0 <= result.overall_score <= 100.0


def test_unsupported_claim_penalty_deduction(sample_analysis_state: AnalysisState) -> None:
    """Verify that unsupported claims cause explicit penalties and explainable reasons."""
    sample_analysis_state.evidence_output.unsupported_claims = [
        ClaimEvaluation(
            claim_text="Led a 50-person engineering department across 4 timezones",
            support_status="UNSUPPORTED",
            confidence=0.1,
            rationale="No supporting evidence found in work history.",
        ),
        ClaimEvaluation(
            claim_text="Generated $10M in ARR within first quarter",
            support_status="UNSUPPORTED",
            confidence=0.1,
            rationale="No revenue metrics found in projects or experience.",
        ),
    ]

    engine = ScoringEngine()
    result = engine.calculate_score(sample_analysis_state)

    assert result.total_penalty > 0.0
    penalty_names = [p.penalty_name for p in result.penalties]
    assert "unsupported_claims_penalty" in penalty_names

    unsupported_p = next(p for p in result.penalties if p.penalty_name == "unsupported_claims_penalty")
    assert unsupported_p.deduction == pytest.approx(0.10, rel=1e-3)
    assert len(unsupported_p.offending_items) == 2


def test_requirement_to_evidence_traceability_graph(sample_analysis_state: AnalysisState) -> None:
    """Verify the trace graph links requirements directly to evidence IDs."""
    engine = ScoringEngine()
    result = engine.calculate_score(sample_analysis_state)

    assert len(result.matched_requirements) > 0
    assert len(result.category_scores) == 8

    # Ensure reasons explain why score factors were awarded
    positive_reasons = [r for r in result.reasons if r.impact == "Positive"]
    assert len(positive_reasons) > 0


def test_formatting_risk_detection(sample_analysis_state: AnalysisState) -> None:
    """Verify formatting risks are surfaced in risk indicators."""
    sample_analysis_state.ats_output.formatting_risks = [
        FormattingRisk(
            risk_type="complex_bullet",
            severity="Medium",
            description="Detected wingding bullet '❖'",
            location="Experience",
        )
    ]

    engine = ScoringEngine()
    result = engine.calculate_score(sample_analysis_state)

    assert len(result.risk_indicators) > 0
    assert result.risk_indicators[0].risk_type == "complex_bullet"
