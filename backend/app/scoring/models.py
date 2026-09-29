"""Data models and schemas for the deterministic XAI-ResOpt scoring engine."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScoringWeights(BaseModel):
    """Configurable weights and penalty factors for the XAI-ResOpt scoring engine.
    
    Weights are automatically normalized to sum to 1.0 during score calculation.
    """
    keyword_coverage_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    semantic_similarity_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    requirement_coverage_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    evidence_confidence_weight: float = Field(default=0.12, ge=0.0, le=1.0)
    experience_alignment_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    section_completeness_weight: float = Field(default=0.08, ge=0.0, le=1.0)
    formatting_safety_weight: float = Field(default=0.08, ge=0.0, le=1.0)
    skill_match_weight: float = Field(default=0.12, ge=0.0, le=1.0)

    # Penalty factors
    unsupported_claim_penalty_factor: float = Field(default=0.05, ge=0.0, le=0.5)
    max_unsupported_claim_penalty: float = Field(default=0.25, ge=0.0, le=0.5)
    contradiction_penalty_factor: float = Field(default=0.08, ge=0.0, le=0.5)
    max_contradiction_penalty: float = Field(default=0.25, ge=0.0, le=0.5)
    missing_mandatory_penalty_factor: float = Field(default=0.06, ge=0.0, le=0.5)
    max_missing_mandatory_penalty: float = Field(default=0.30, ge=0.0, le=0.5)

    model_config = ConfigDict(extra="forbid")

    def normalized_weights(self) -> dict[str, float]:
        """Returns the dictionary of category weights normalized to sum to 1.0."""
        raw = {
            "keyword_coverage": self.keyword_coverage_weight,
            "semantic_similarity": self.semantic_similarity_weight,
            "requirement_coverage": self.requirement_coverage_weight,
            "evidence_confidence": self.evidence_confidence_weight,
            "experience_alignment": self.experience_alignment_weight,
            "section_completeness": self.section_completeness_weight,
            "formatting_safety": self.formatting_safety_weight,
            "skill_match": self.skill_match_weight,
        }
        total = sum(raw.values())
        if total <= 0:
            count = len(raw)
            return {k: 1.0 / count for k in raw}
        return {k: v / total for k, v in raw.items()}


class CategoryScoreDetail(BaseModel):
    """Detailed calculation and explanation for an individual score category."""
    category: str
    raw_score: float = Field(ge=0.0, le=1.0, description="Score in range 0.0 to 1.0")
    percentage_score: float = Field(ge=0.0, le=100.0, description="Score in percentage (0 to 100)")
    weight: float = Field(ge=0.0, le=1.0, description="Normalized weight assigned to category")
    weighted_contribution: float = Field(description="Contribution to raw weighted score")
    description: str
    contributing_factors: list[str] = Field(default_factory=list)
    requirement_ids: list[UUID] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)


class ScorePenaltyDetail(BaseModel):
    """Explicit penalty deduction applied to the raw score."""
    penalty_name: str
    deduction: float = Field(ge=0.0, le=1.0, description="Amount deducted from overall score")
    reason: str
    offending_items: list[str] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)


class ScoreReason(BaseModel):
    """Explainable reason for a score award, factor, or deduction."""
    factor_name: str
    impact: str = Field(description="Positive, Neutral, or Negative impact")
    description: str
    requirement_id: UUID | None = None
    evidence_id: UUID | None = None
    recommendation: str | None = None


class EvidenceTraceItem(BaseModel):
    """Traceable evidence item supporting one or more requirements."""
    evidence_id: UUID | None = None
    source_type: str = "resume"
    source_location: str | None = None
    text_snippet: str
    confidence: float = Field(ge=0.0, le=1.0)
    supported_requirement_ids: list[UUID] = Field(default_factory=list)
    supported_skills: list[str] = Field(default_factory=list)


class RequirementTraceItem(BaseModel):
    """Traceable status for an individual job requirement."""
    requirement_id: UUID | None = None
    text: str
    kind: str = "mandatory"
    category: str = "technical_skill"
    support_status: str = "SUPPORTED"
    score: float = Field(ge=0.0, le=1.0)
    matched_terms: list[str] = Field(default_factory=list)
    missing_terms: list[str] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)


class RiskIndicator(BaseModel):
    """Risk item identified during scoring."""
    risk_type: str
    severity: str = Field(description="Low, Medium, or High")
    description: str
    remediation_hint: str
    evidence_ids: list[UUID] = Field(default_factory=list)


class ScoringResult(BaseModel):
    """Comprehensive, fully explainable output of the deterministic XAI-ResOpt scoring engine."""
    score_name: str = "XAI-ResOpt ATS Compatibility Score"
    calculation_version: str = "xai-resopt-v1.0-deterministic"
    overall_score: float = Field(ge=0.0, le=100.0, description="Overall compatibility score 0-100")
    overall_score_normalized: float = Field(ge=0.0, le=1.0, description="Overall score normalized to 0.0-1.0")
    raw_weighted_score: float = Field(ge=0.0, le=1.0, description="Pre-penalty weighted sum")
    total_penalty: float = Field(ge=0.0, le=1.0, description="Sum of all applied penalties")
    
    category_scores: dict[str, CategoryScoreDetail] = Field(
        default_factory=dict,
        description="Dictionary of individual category score breakdowns"
    )
    penalties: list[ScorePenaltyDetail] = Field(default_factory=list)
    reasons: list[ScoreReason] = Field(default_factory=list)
    supporting_evidence: list[EvidenceTraceItem] = Field(default_factory=list)
    matched_requirements: list[RequirementTraceItem] = Field(default_factory=list)
    missing_requirements: list[RequirementTraceItem] = Field(default_factory=list)
    risk_indicators: list[RiskIndicator] = Field(default_factory=list)
    
    # Traceability graph mapping: requirement_id -> list of evidence_ids
    traceability_map: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Graph mapping requirement UUID strings to matching evidence item UUID strings"
    )
    weights_applied: ScoringWeights = Field(default_factory=ScoringWeights)
    calculation_metadata: dict[str, Any] = Field(default_factory=dict)
