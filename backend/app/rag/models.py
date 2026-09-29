"""Data models and schemas for the XAI-ResOpt Retrieval Engine."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class RetrievalMethod(StrEnum):
    hybrid = "hybrid"
    lexical_only = "lexical_only"
    semantic_only = "semantic_only"


class RetrievalWeights(BaseModel):
    lexical_weight: float = Field(default=0.45, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.45, ge=0.0, le=1.0)
    evidence_weight: float = Field(default=0.10, ge=0.0, le=1.0)

    def normalized(self) -> RetrievalWeights:
        total = self.lexical_weight + self.semantic_weight + self.evidence_weight
        if total <= 0:
            return RetrievalWeights(lexical_weight=0.45, semantic_weight=0.45, evidence_weight=0.10)
        return RetrievalWeights(
            lexical_weight=self.lexical_weight / total,
            semantic_weight=self.semantic_weight / total,
            evidence_weight=self.evidence_weight / total,
        )


class LexicalScoreBreakdown(BaseModel):
    bm25_score: float = Field(ge=0.0, le=1.0)
    exact_match_score: float = Field(ge=0.0, le=1.0)
    normalized_keyword_score: float = Field(ge=0.0, le=1.0)
    ngram_score: float = Field(ge=0.0, le=1.0)
    total: float = Field(ge=0.0, le=1.0)


class SemanticScoreBreakdown(BaseModel):
    cosine_similarity: float = Field(ge=0.0, le=1.0)
    vector_distance: float | None = None
    total: float = Field(ge=0.0, le=1.0)


class RetrievedEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: UUID = Field(default_factory=uuid4)
    chunk_text: str = Field(min_length=1)
    normalized_text: str | None = None
    source_document: str
    source_location: str
    source_type: str = "resume"
    score_name: str = "XAI-ResOpt ATS Compatibility Score"
    hybrid_score: float = Field(ge=0.0, le=1.0)
    lexical_score: float = Field(ge=0.0, le=1.0)
    semantic_score: float = Field(ge=0.0, le=1.0)
    evidence_score: float = Field(ge=0.0, le=1.0)
    retrieval_method: RetrievalMethod = RetrievalMethod.hybrid
    matched_terms: list[str] = Field(default_factory=list)
    lexical_breakdown: LexicalScoreBreakdown | None = None
    semantic_breakdown: SemanticScoreBreakdown | None = None
    provenance: dict = Field(default_factory=dict)


class RequirementRetrievalQuery(BaseModel):
    requirement_id: UUID | None = None
    requirement_text: str = Field(min_length=1)
    category: str = "skill"
    kind: str = "mandatory"
    query_text: str = Field(min_length=1)
    target_terms: list[str] = Field(default_factory=list)
    normalized_terms: list[str] = Field(default_factory=list)
    synonym_terms: list[str] = Field(default_factory=list)


class RequirementRetrievalResult(BaseModel):
    requirement_text: str
    requirement_kind: str
    query: RequirementRetrievalQuery
    top_matches: list[RetrievedEvidence] = Field(default_factory=list)
    best_score: float = Field(default=0.0, ge=0.0, le=1.0)
    compatibility_score_name: str = "XAI-ResOpt ATS Compatibility Score"
