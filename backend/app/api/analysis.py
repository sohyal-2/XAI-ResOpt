"""REST API router for Baseline Analysis workflow and explainable reports."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.models.entities import User
from app.schemas.analysis import (
    AgentRunsResponse,
    AnalysisSummaryItem,
    BaselineAnalysisRequest,
    BaselineReportResponse,
    CopilotChatRequest,
    CopilotChatResponse,
    EvidenceTraceResponse,
    RecommendationsResponse,
    RequirementsCoverageResponse,
    ScoreBreakdownResponse,
)
from app.schemas.optimization import (
    ClosedLoopOptimizationResponse,
    OptimizationIterationRecord,
    OptimizationRequest,
)
from app.services.analysis import (
    copilot_chat,
    delete_user_analysis,
    get_agent_runs,
    get_analysis_summary,
    get_baseline_report,
    get_evidence_trace,
    get_recommendations,
    get_requirements_coverage,
    get_score_breakdown,
    list_user_analyses,
    run_baseline_analysis,
)
from app.services.optimization import (
    get_latest_optimization,
    get_optimization_history,
    run_closed_loop_optimization,
)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("", response_model=list[AnalysisSummaryItem])
async def list_analyses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AnalysisSummaryItem]:
    """Retrieves all analyses belonging to the current user."""
    return await list_user_analyses(db, current_user.id)


@router.get("/{analysis_id}/summary", response_model=AnalysisSummaryItem)
async def retrieve_analysis_summary(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisSummaryItem:
    """Retrieves metadata summary for an analysis."""
    return await get_analysis_summary(db, current_user.id, analysis_id)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def remove_analysis(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Deletes an analysis record and associated runs for the user."""
    await delete_user_analysis(db, current_user.id, analysis_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.post("/{analysis_id}/chat", response_model=CopilotChatResponse)
async def chat_with_copilot(
    analysis_id: UUID,
    req: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CopilotChatResponse:
    """Answers user queries grounded strictly in active analysis evidence and scores."""
    return await copilot_chat(db, current_user.id, analysis_id, req.message)



@router.post("/baseline", response_model=BaselineReportResponse, status_code=status.HTTP_201_CREATED)
async def trigger_baseline_analysis(
    req: BaselineAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BaselineReportResponse:
    """Executes the full Intake -> Parse -> Evidence -> RAG -> Agents -> Scoring workflow."""
    return await run_baseline_analysis(db, current_user.id, req)


@router.get("/{analysis_id}/baseline", response_model=BaselineReportResponse)
async def retrieve_baseline_report(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BaselineReportResponse:
    """Retrieves the complete, explainable baseline report for an analysis."""
    return await get_baseline_report(db, current_user.id, analysis_id)


@router.get("/{analysis_id}/score", response_model=ScoreBreakdownResponse)
async def retrieve_score_breakdown(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreBreakdownResponse:
    """Retrieves the deterministic score breakdown, category scores, and penalties."""
    return await get_score_breakdown(db, current_user.id, analysis_id)


@router.get("/{analysis_id}/agent-runs", response_model=AgentRunsResponse)
async def retrieve_agent_runs(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentRunsResponse:
    """Retrieves agent execution history and telemetry logs."""
    return await get_agent_runs(db, current_user.id, analysis_id)


@router.get("/{analysis_id}/recommendations", response_model=RecommendationsResponse)
async def retrieve_recommendations(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationsResponse:
    """Retrieves all generated recommendations linked to evidence references."""
    return await get_recommendations(db, current_user.id, analysis_id)


@router.get("/{analysis_id}/requirements", response_model=RequirementsCoverageResponse)
async def retrieve_requirements_coverage(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequirementsCoverageResponse:
    """Retrieves requirement fulfillment status, matched terms, and gaps."""
    return await get_requirements_coverage(db, current_user.id, analysis_id)


@router.get("/{analysis_id}/evidence", response_model=EvidenceTraceResponse)
async def retrieve_evidence_trace(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceTraceResponse:
    """Retrieves grounded evidence items and unsupported claim traces."""
    return await get_evidence_trace(db, current_user.id, analysis_id)


@router.post("/{analysis_id}/optimize", response_model=ClosedLoopOptimizationResponse, status_code=status.HTTP_200_OK)
async def trigger_closed_loop_optimization(
    analysis_id: UUID,
    req: OptimizationRequest = Body(default_factory=OptimizationRequest),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClosedLoopOptimizationResponse:
    """Executes closed-loop optimization cycles with Critic, Fact-Check, and deterministic ATS re-scoring."""
    return await run_closed_loop_optimization(db, current_user.id, analysis_id, req)


@router.get("/{analysis_id}/optimizations", response_model=list[OptimizationIterationRecord])
async def retrieve_optimization_history(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OptimizationIterationRecord]:
    """Retrieves all optimization iterations for an analysis with changes, scores, and validation issues."""
    return await get_optimization_history(db, current_user.id, analysis_id)


@router.get("/{analysis_id}/optimizations/latest", response_model=ClosedLoopOptimizationResponse)
async def retrieve_latest_optimization(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClosedLoopOptimizationResponse:
    """Retrieves the most recent optimization iteration and overall comparison for an analysis."""
    return await get_latest_optimization(db, current_user.id, analysis_id)
