"""Schemas and data models for closed-loop resume optimization workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.agents.optimization_models import ProposedChange


class OptimizationRequest(BaseModel):
    """Payload to trigger the bounded closed-loop optimization workflow."""
    max_iterations: int = Field(default=3, ge=1, le=5, description="Maximum optimization iterations allowed")
    target_score: float | None = Field(default=None, ge=0.0, le=100.0, description="Target score threshold to halt early")
    strict_mode: bool = Field(default=True, description="Enforce strict rejection of hallucinated facts")

    model_config = ConfigDict(extra="forbid")


class OptimizationIterationRecord(BaseModel):
    """Execution telemetry and results for an individual optimization cycle."""
    iteration_number: int
    score: float = Field(ge=0.0, le=100.0)
    score_delta: float = Field(description="Score change relative to previous iteration")
    changes: list[ProposedChange] = Field(default_factory=list)
    accepted_changes: list[ProposedChange] = Field(default_factory=list)
    rejected_changes: list[ProposedChange] = Field(default_factory=list)
    validation_issues: list[str] = Field(default_factory=list)
    evidence_used: list[UUID] = Field(default_factory=list)
    agent_runs: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ClosedLoopOptimizationResponse(BaseModel):
    """Comprehensive output of the closed-loop optimization pipeline."""
    analysis_id: UUID
    total_iterations: int
    baseline_score: float = Field(ge=0.0, le=100.0)
    final_score: float = Field(ge=0.0, le=100.0)
    score: float = Field(default=0.0, description="Final optimized ATS score")
    overall_delta: float = Field(description="Net score improvement from baseline")
    score_delta: float = Field(default=0.0, description="Net score change")
    improved: bool = Field(description="True if final score is strictly greater than baseline score")
    before_score: float
    after_score: float
    delta: float
    remaining_gaps: list[str] = Field(default_factory=list)
    new_risks: list[str] = Field(default_factory=list)
    optimized_resume_text: str
    optimized_version_id: UUID | None = None
    iterations: list[OptimizationIterationRecord] = Field(default_factory=list)
    status: str = Field(description="ready_for_approval, completed, or max_iterations_reached")

