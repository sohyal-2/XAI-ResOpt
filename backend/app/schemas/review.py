"""Pydantic schemas for Human-in-the-Loop review workflow, manual edits, and full provenance tracing."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvidenceSummary(BaseModel):
    """Summarized evidence item for direct UI display and provenance tracing."""
    id: UUID
    text: str
    source_uri: str | None = None
    location: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.95)


class TraceNode(BaseModel):
    """Complete 5-tier audit trace: Recommendation -> Change -> Claim -> Evidence -> Original Source."""
    recommendation_text: str | None = None
    change_before: str
    change_after: str
    claim_text: str | None = None
    claim_status: str | None = None
    evidence_text: str | None = None
    original_source: str | None = None
    source_location: str | None = None


class ChangeReviewItem(BaseModel):
    """Detailed change model containing all 7 required inspection dimensions and full provenance."""
    change_id: UUID
    section: str
    change_type: str
    before_text: str
    after_text: str
    why_changed: str
    evidence: list[EvidenceSummary] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.95)
    risk: str = Field(description="low, medium, or high")
    supported_status: str = Field(description="SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, CONTRADICTED")
    decision: str = Field(description="pending, accepted, rejected, or edited")
    manual_text: str | None = None
    is_manual: bool = False
    trace_chain: TraceNode | None = None


class ChangeDecisionItem(BaseModel):
    """Individual decision payload on a single proposed modification."""
    change_id: UUID
    action: str = Field(description="'accept', 'reject', or 'edit'")
    manual_text: str | None = Field(default=None, description="Custom content if action is 'edit'")

    model_config = ConfigDict(extra="forbid")


class ReviewDecisionRequest(BaseModel):
    """Batch payload of user actions on review items."""
    decisions: list[ChangeDecisionItem] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ReviewSessionResponse(BaseModel):
    """Current state of the Human-in-the-Loop review board."""
    analysis_id: UUID
    status: str = Field(description="'in_review', 'finalized', or 'pending'")
    total_changes: int
    accepted_count: int
    rejected_count: int
    edited_count: int
    pending_count: int
    unresolved_unsupported_claims: list[dict[str, Any]] = Field(default_factory=list)
    unsupported_claims_count: int
    can_finalize: bool = Field(description="False if unresolved unsupported claims block finalization")
    changes: list[ChangeReviewItem] = Field(default_factory=list)


class FinalizeReviewRequest(BaseModel):
    """Request to generate and finalize a new candidate ResumeVersion."""
    force_unresolved_claims: bool = Field(
        default=False,
        description="Explicit override if user chooses to proceed with known unverified claims",
    )
    notes: str | None = Field(default=None, description="Optional review approval notes")

    model_config = ConfigDict(extra="forbid")


class FinalizeReviewResponse(BaseModel):
    """Summary of finalized review and newly published ResumeVersion."""
    analysis_id: UUID
    new_resume_version_id: UUID
    version_number: int
    finalized_resume_text: str
    changes_applied_count: int
    manual_edits_count: int
    rejected_count: int
    trace_summary: list[dict[str, Any]] = Field(default_factory=list)
