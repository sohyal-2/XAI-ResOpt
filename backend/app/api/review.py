"""REST API router for Human-in-the-Loop review actions and resume finalization."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.models.entities import User
from app.schemas.optimization import ClosedLoopOptimizationResponse
from app.schemas.review import (
    FinalizeReviewRequest,
    FinalizeReviewResponse,
    ReviewDecisionRequest,
    ReviewSessionResponse,
)
from app.services.review import (
    accept_all_safe_changes,
    apply_review_decisions,
    finalize_review,
    get_review_session,
    re_run_optimization_review,
)

router = APIRouter(prefix="/api/analysis", tags=["review"])


@router.get("/{analysis_id}/review", response_model=ReviewSessionResponse)
async def retrieve_review_session(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewSessionResponse:
    """Retrieves all proposed changes with 7-dimension inspection and full 5-tier traceability."""
    return await get_review_session(db, current_user.id, analysis_id)


@router.post("/{analysis_id}/review/decisions", response_model=ReviewSessionResponse)
async def submit_review_decisions(
    analysis_id: UUID,
    req: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewSessionResponse:
    """Applies user decisions (Accept, Reject, Edit manually) to individual proposed modifications."""
    return await apply_review_decisions(db, current_user.id, analysis_id, req)


@router.post("/{analysis_id}/review/accept-all-safe", response_model=ReviewSessionResponse)
async def bulk_accept_safe_changes(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewSessionResponse:
    """Bulk-accepts all proposed modifications that are low-risk and factually supported."""
    return await accept_all_safe_changes(db, current_user.id, analysis_id)


@router.post("/{analysis_id}/review/re-optimize", response_model=ClosedLoopOptimizationResponse)
async def trigger_re_optimization(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClosedLoopOptimizationResponse:
    """Re-runs the optimization agent loop taking existing human feedback into account."""
    return await re_run_optimization_review(db, current_user.id, analysis_id)


@router.post("/{analysis_id}/review/finalize", response_model=FinalizeReviewResponse, status_code=status.HTTP_200_OK)
async def finalize_human_review(
    analysis_id: UUID,
    req: FinalizeReviewRequest = Body(default_factory=FinalizeReviewRequest),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinalizeReviewResponse:
    """Finalizes human review, checks safety guardrails against unresolved unsupported claims, and publishes a new ResumeVersion."""
    return await finalize_review(db, current_user.id, analysis_id, req)
