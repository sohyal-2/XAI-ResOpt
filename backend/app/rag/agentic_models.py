"""Structured state, models, and outputs for the Agentic RAG Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.parsing.models import JobRequirementExtraction
from app.rag.models import (
    RequirementRetrievalQuery,
    RequirementRetrievalResult,
    RetrievalWeights,
    RetrievedEvidence,
)


class SupportStatus(StrEnum):
    supported = "SUPPORTED"
    partially_supported = "PARTIALLY_SUPPORTED"
    unsupported = "UNSUPPORTED"


class WorkflowStatus(StrEnum):
    idle = "idle"
    running = "running"
    completed = "completed"
    failed = "failed"


class AgenticRAGLogEntry(BaseModel):
    step: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    iteration: int = 0
    query: str | None = None
    retrieval_method: str | None = None
    retrieved_evidence_ids: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    retries: int = 0
    message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceSufficiencyItem(BaseModel):
    requirement_text: str
    requirement_kind: str
    is_sufficient: bool
    best_score: float
    matched_count: int
    missing_evidence_types: list[str] = Field(default_factory=list)
    rationale: str


class EvidenceSufficiencyReport(BaseModel):
    is_overall_sufficient: bool
    sufficient_count: int
    insufficient_count: int
    items: list[EvidenceSufficiencyItem] = Field(default_factory=list)
    requires_second_pass: bool = False


class GroundedRequirementContext(BaseModel):
    requirement_id: UUID | None = None
    requirement_text: str
    requirement_kind: str
    requirement_category: str
    support_status: SupportStatus
    confidence: float = Field(ge=0.0, le=1.0)
    top_score: float = Field(ge=0.0, le=1.0)
    compatibility_score_name: str = "XAI-ResOpt ATS Compatibility Score"
    matched_evidence: list[RetrievedEvidence] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    grounded_summary: str


class AgenticRAGOutput(BaseModel):
    task_id: str
    owner_id: UUID
    job_description_id: UUID | None = None
    resume_version_id: UUID | None = None
    status: WorkflowStatus
    total_requirements: int
    supported_count: int
    partially_supported_count: int
    unsupported_count: int
    overall_compatibility_score: float = Field(ge=0.0, le=1.0)
    compatibility_score_name: str = "XAI-ResOpt ATS Compatibility Score"
    grounded_contexts: list[GroundedRequirementContext] = Field(default_factory=list)
    sufficiency_report: EvidenceSufficiencyReport
    iteration_count: int = 0
    execution_logs: list[AgenticRAGLogEntry] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgenticRAGState(BaseModel):
    """Typed shared state for the LangGraph Agentic RAG State Machine."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    owner_id: UUID
    job_description_id: UUID | None = None
    resume_version_id: UUID | None = None

    # Input requirements and evidence
    requirements: list[JobRequirementExtraction] = Field(default_factory=list)
    raw_evidence_corpus: list[Any] = Field(default_factory=list)
    weights: RetrievalWeights = Field(default_factory=RetrievalWeights)

    # Workflow state tracking
    queries: list[RequirementRetrievalQuery] = Field(default_factory=list)
    evidence_needs: dict[str, list[str]] = Field(default_factory=dict)
    retrieval_results: dict[str, RequirementRetrievalResult] = Field(default_factory=dict)
    sufficiency_report: EvidenceSufficiencyReport | None = None

    # Iteration and retry control
    iteration: int = 0
    max_retries: int = 1

    # Output context and observability
    grounded_contexts: list[GroundedRequirementContext] = Field(default_factory=list)
    execution_logs: list[AgenticRAGLogEntry] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.idle
    error: str | None = None
