"""Data models and schemas for ATS, Skill, and Evidence analysis agents."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.parsing.models import JobDescriptionExtraction, ResumeExtraction
from app.rag.agentic_models import GroundedRequirementContext


class AgentRecommendation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_name: str
    category: str
    title: str
    description: str
    priority: str = "medium"  # "critical", "high", "medium", "low"
    requirement_id: UUID | None = None
    requirement_text: str | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)
    source_location: str | None = None
    suggested_action: str


class SectionNamingIssue(BaseModel):
    found_heading: str
    recommended_heading: str
    standard_section: str
    risk_level: str = "medium"


class FormattingRisk(BaseModel):
    risk_type: str
    description: str
    severity: str = "medium"
    location: str | None = None


class SkillGapItem(BaseModel):
    skill_name: str
    canonical: str
    kind: str  # mandatory, preferred, nice_to_have
    impact: str
    missing_evidence_types: list[str] = Field(default_factory=list)


class TransferableEvidenceItem(BaseModel):
    target_skill: str
    related_found_skill: str
    rationale: str
    evidence_id: UUID | None = None
    source_location: str | None = None
    transferability_confidence: float = Field(ge=0.0, le=1.0)


class ClaimEvaluation(BaseModel):
    claim_text: str
    support_status: str  # SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[UUID] = Field(default_factory=list)
    source_provenance: str | None = None
    rationale: str


class ContradictionItem(BaseModel):
    description: str
    conflicting_items: list[str] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    severity: str = "high"


class ATSAgentOutput(BaseModel):
    overall_ats_score: float = Field(ge=0.0, le=1.0)
    score_name: str = "XAI-ResOpt ATS Compatibility Score"
    keyword_coverage_percent: float = Field(ge=0.0, le=100.0)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    exact_matches: list[str] = Field(default_factory=list)
    synonym_matches: list[str] = Field(default_factory=list)
    section_presence: dict[str, bool] = Field(default_factory=dict)
    section_naming_issues: list[SectionNamingIssue] = Field(default_factory=list)
    formatting_risks: list[FormattingRisk] = Field(default_factory=list)
    formatting_risk_score: float = Field(ge=0.0, le=1.0)
    contact_info_completeness: dict[str, bool] = Field(default_factory=dict)
    readability_score: float = Field(ge=0.0, le=1.0)
    parsability_score: float = Field(ge=0.0, le=1.0)
    keyword_distribution: dict[str, int] = Field(default_factory=dict)
    requirement_coverage_percent: float = Field(ge=0.0, le=100.0)
    recommendations: list[AgentRecommendation] = Field(default_factory=list)


class SkillAgentOutput(BaseModel):
    semantic_skill_score: float = Field(ge=0.0, le=1.0)
    score_name: str = "XAI-ResOpt ATS Compatibility Score"
    mandatory_skill_coverage_percent: float = Field(ge=0.0, le=100.0)
    preferred_skill_coverage_percent: float = Field(ge=0.0, le=100.0)
    matched_mandatory_skills: list[str] = Field(default_factory=list)
    missing_mandatory_skills: list[str] = Field(default_factory=list)
    matched_preferred_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGapItem] = Field(default_factory=list)
    transferable_evidence: list[TransferableEvidenceItem] = Field(default_factory=list)
    seniority_alignment_score: float = Field(ge=0.0, le=1.0)
    seniority_gap: str | None = None
    experience_relevance_score: float = Field(ge=0.0, le=1.0)
    recommendations: list[AgentRecommendation] = Field(default_factory=list)


class EvidenceAgentOutput(BaseModel):
    factual_support_score: float = Field(ge=0.0, le=1.0)
    score_name: str = "XAI-ResOpt ATS Compatibility Score"
    total_claims_evaluated: int = 0
    supported_claims_count: int = 0
    partially_supported_count: int = 0
    unsupported_claims_count: int = 0
    claim_evaluations: list[ClaimEvaluation] = Field(default_factory=list)
    unsupported_claims: list[ClaimEvaluation] = Field(default_factory=list)
    contradictions: list[ContradictionItem] = Field(default_factory=list)
    evidence_sufficiency_score: float = Field(ge=0.0, le=1.0)
    insufficient_requirements: list[str] = Field(default_factory=list)
    recommendations: list[AgentRecommendation] = Field(default_factory=list)


class ConsolidatedAnalysisOutput(BaseModel):
    analysis_id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    resume_version_id: UUID | None = None
    job_description_id: UUID | None = None
    ats_analysis: ATSAgentOutput
    skill_analysis: SkillAgentOutput
    evidence_analysis: EvidenceAgentOutput
    consolidated_recommendations: list[AgentRecommendation] = Field(default_factory=list)
    score_name: str = "XAI-ResOpt ATS Compatibility Score"


class AnalysisState(BaseModel):
    """Shared state machine context for ATS, Skill, and Evidence analysis agents."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    analysis_id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    resume_version_id: UUID | None = None
    job_description_id: UUID | None = None

    # Input extractions and RAG context
    resume_extraction: ResumeExtraction | None = None
    job_extraction: JobDescriptionExtraction | None = None
    evidence_corpus: list[Any] = Field(default_factory=list)
    grounded_contexts: list[GroundedRequirementContext] = Field(default_factory=list)

    # Agent outputs
    ats_output: ATSAgentOutput | None = None
    skill_output: SkillAgentOutput | None = None
    evidence_output: EvidenceAgentOutput | None = None

    # Consolidated results
    consolidated_output: ConsolidatedAnalysisOutput | None = None
    agent_runs_log: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "idle"
    error: str | None = None
