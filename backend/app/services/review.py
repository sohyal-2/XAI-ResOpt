"""Human-in-the-Loop review service managing change inspection, audit trails, and version publication."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy import desc, select
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    Analysis,
    ApprovalHistory,
    ChangeDecision,
    Claim,
    EvidenceItem,
    OptimizationRun,
    Recommendation,
    ResumeChange,
    ResumeVersion,
)
from app.schemas.optimization import ClosedLoopOptimizationResponse, OptimizationRequest
from app.schemas.review import (
    ChangeReviewItem,
    EvidenceSummary,
    FinalizeReviewRequest,
    FinalizeReviewResponse,
    ReviewDecisionRequest,
    ReviewSessionResponse,
    TraceNode,
)
from app.services.optimization import run_closed_loop_optimization


async def get_review_session(
    db: AsyncSession,
    owner_id: UUID,
    analysis_id: UUID,
) -> ReviewSessionResponse:
    """Retrieves current change review session with 7-dimension inspection and full 5-tier traceability."""
    analysis_stmt = select(Analysis).where(Analysis.id == analysis_id, Analysis.owner_id == owner_id)
    analysis = (await db.scalars(analysis_stmt)).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    # Fetch latest OptimizationRun
    opt_stmt = (
        select(OptimizationRun)
        .where(OptimizationRun.analysis_id == analysis_id)
        .order_by(desc(OptimizationRun.iteration))
    )
    latest_opt_run = (await db.scalars(opt_stmt)).first()

    # Fetch existing ResumeChange records
    changes_stmt = (
        select(ResumeChange)
        .where(ResumeChange.optimization_run_id == latest_opt_run.id)
        .order_by(ResumeChange.created_at.asc())
        if latest_opt_run
        else select(ResumeChange).where(ResumeChange.resume_version_id == analysis.resume_version_id)
    )
    db_changes = list((await db.scalars(changes_stmt)).all())

    # Fetch all EvidenceItems for this owner
    ev_stmt = select(EvidenceItem).where(EvidenceItem.owner_id == owner_id)
    all_evidence = {e.id: e for e in (await db.scalars(ev_stmt)).all()}

    # Fetch all Claims for this owner
    claims_stmt = select(Claim).where(Claim.owner_id == owner_id)
    all_claims = list((await db.scalars(claims_stmt)).all())
    claims_by_ev = {}
    for c in all_claims:
        if c.evidence_item_id:
            claims_by_ev[c.evidence_item_id] = c

    # Fetch all Recommendations for this analysis
    rec_stmt = select(Recommendation).where(Recommendation.analysis_id == analysis_id)
    all_recs = list((await db.scalars(rec_stmt)).all())
    rec_map = {r.id: r for r in all_recs}

    # Fetch unresolved unsupported claims
    unresolved_claims = [
        {
            "id": str(c.id),
            "text": c.text,
            "status": c.support_status.value if hasattr(c.support_status, "value") else str(c.support_status),
            "confidence": c.confidence,
        }
        for c in all_claims
        if (hasattr(c.support_status, "value") and c.support_status.value in ("UNSUPPORTED", "CONTRADICTED"))
        or str(c.support_status) in ("UNSUPPORTED", "CONTRADICTED", "ClaimStatus.unsupported", "ClaimStatus.contradicted")
    ]

    review_items: list[ChangeReviewItem] = []
    for ch in db_changes:
        # Parse evidence UUIDs
        ev_uuids: list[UUID] = []
        raw_evs = ch.evidence_ids if isinstance(ch.evidence_ids, list) else []
        for raw_e in raw_evs:
            try:
                ev_uuids.append(UUID(str(raw_e)))
            except (ValueError, TypeError):
                continue

        ev_summaries: list[EvidenceSummary] = []
        linked_claim: Claim | None = None
        for eid in ev_uuids:
            if eid in all_evidence:
                item = all_evidence[eid]
                ev_summaries.append(
                    EvidenceSummary(
                        id=item.id,
                        text=item.text,
                        source_uri=item.source_uri,
                        location=item.source_location,
                        confidence=item.confidence,
                    )
                )
            if eid in claims_by_ev and not linked_claim:
                linked_claim = claims_by_ev[eid]

        # Trace Node: Recommendation -> Change -> Claim -> Evidence -> Original Source
        rec_text = rec_map.get(ch.recommendation_id).text if ch.recommendation_id and ch.recommendation_id in rec_map else None
        if not rec_text and all_recs:
            # Best match recommendation by keyword or section
            for r in all_recs:
                if ch.section.lower() in r.text.lower() or any(w in r.text.lower() for w in ch.before_text.lower().split()[:4]):
                    rec_text = r.text
                    break

        claim_text = linked_claim.text if linked_claim else "Extracted career experience claim"
        claim_status_str = (
            linked_claim.support_status.value if linked_claim and hasattr(linked_claim.support_status, "value")
            else (str(linked_claim.support_status) if linked_claim else ch.support_status)
        )
        primary_ev = ev_summaries[0] if ev_summaries else None

        trace = TraceNode(
            recommendation_text=rec_text or f"Optimize {ch.section} for ATS alignment and clarity",
            change_before=ch.before_text,
            change_after=ch.after_text,
            claim_text=claim_text,
            claim_status=claim_status_str,
            evidence_text=primary_ev.text if primary_ev else "Verified resume source text",
            original_source=primary_ev.source_uri if primary_ev else "Ingested Candidate Resume",
            source_location=primary_ev.location if primary_ev else f"Section: {ch.section}",
        )

        decision_val = ch.decision.value if hasattr(ch.decision, "value") else str(ch.decision)

        review_items.append(
            ChangeReviewItem(
                change_id=ch.id,
                section=ch.section,
                change_type=ch.change_type,
                before_text=ch.before_text,
                after_text=ch.after_text,
                why_changed=ch.reason or "Enhanced clarity, conciseness, and ATS keyword alignment.",
                evidence=ev_summaries,
                evidence_ids=ev_uuids,
                confidence=ch.confidence,
                risk=ch.risk_level,
                supported_status=ch.support_status,
                decision=decision_val,
                manual_text=ch.manual_text,
                is_manual=ch.is_manual,
                trace_chain=trace,
            )
        )

    accepted_cnt = sum(1 for item in review_items if item.decision == "accepted")
    rejected_cnt = sum(1 for item in review_items if item.decision == "rejected")
    edited_cnt = sum(1 for item in review_items if item.decision == "edited")
    pending_cnt = sum(1 for item in review_items if item.decision == "pending")

    can_finalize = len(unresolved_claims) == 0

    return ReviewSessionResponse(
        analysis_id=analysis_id,
        status="in_review",
        total_changes=len(review_items),
        accepted_count=accepted_cnt,
        rejected_count=rejected_cnt,
        edited_count=edited_cnt,
        pending_count=pending_cnt,
        unresolved_unsupported_claims=unresolved_claims,
        unsupported_claims_count=len(unresolved_claims),
        can_finalize=can_finalize,
        changes=review_items,
    )


async def apply_review_decisions(
    db: AsyncSession,
    owner_id: UUID,
    analysis_id: UUID,
    req: ReviewDecisionRequest,
) -> ReviewSessionResponse:
    """Applies granular decisions (Accept, Reject, Edit manually) to specified changes."""
    analysis_stmt = select(Analysis).where(Analysis.id == analysis_id, Analysis.owner_id == owner_id)
    analysis = (await db.scalars(analysis_stmt)).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    for dec in req.decisions:
        ch_stmt = select(ResumeChange).where(ResumeChange.id == dec.change_id)
        change = (await db.scalars(ch_stmt)).first()
        if not change:
            continue

        if dec.action == "accept":
            change.decision = ChangeDecision.accepted
            change.is_manual = False
        elif dec.action == "reject":
            change.decision = ChangeDecision.rejected
            change.is_manual = False
        elif dec.action == "edit":
            change.decision = ChangeDecision.edited
            change.manual_text = dec.manual_text
            change.is_manual = True

    await db.commit()
    return await get_review_session(db, owner_id, analysis_id)


async def accept_all_safe_changes(
    db: AsyncSession,
    owner_id: UUID,
    analysis_id: UUID,
) -> ReviewSessionResponse:
    """Bulk-accepts all proposed modifications that are low-risk and fully supported."""
    analysis_stmt = select(Analysis).where(Analysis.id == analysis_id, Analysis.owner_id == owner_id)
    analysis = (await db.scalars(analysis_stmt)).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    opt_stmt = (
        select(OptimizationRun)
        .where(OptimizationRun.analysis_id == analysis_id)
        .order_by(desc(OptimizationRun.iteration))
    )
    latest_opt_run = (await db.scalars(opt_stmt)).first()
    if not latest_opt_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No optimization run found for review")

    changes_stmt = select(ResumeChange).where(ResumeChange.optimization_run_id == latest_opt_run.id)
    changes = list((await db.scalars(changes_stmt)).all())

    for ch in changes:
        if ch.decision == ChangeDecision.edited or ch.is_manual:
            continue
        if ch.risk_level.lower() == "low" and ch.support_status.upper() in ("SUPPORTED", "CLAIMSTATUS.SUPPORTED"):
            ch.decision = ChangeDecision.accepted

    await db.commit()
    return await get_review_session(db, owner_id, analysis_id)


async def re_run_optimization_review(
    db: AsyncSession,
    owner_id: UUID,
    analysis_id: UUID,
) -> ClosedLoopOptimizationResponse:
    """Triggers another optimization cycle incorporating previous feedback."""
    return await run_closed_loop_optimization(
        db=db,
        owner_id=owner_id,
        analysis_id=analysis_id,
        req=OptimizationRequest(max_iterations=2),
    )


async def finalize_review(
    db: AsyncSession,
    owner_id: UUID,
    analysis_id: UUID,
    req: FinalizeReviewRequest,
) -> FinalizeReviewResponse:
    """Finalizes human review, checks safety guardrails against unresolved unsupported claims, and publishes a new ResumeVersion."""
    analysis_stmt = select(Analysis).where(Analysis.id == analysis_id, Analysis.owner_id == owner_id)
    analysis = (await db.scalars(analysis_stmt)).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    # Guardrail: Check for unresolved unsupported or contradicted claims
    claims_stmt = select(Claim).where(Claim.owner_id == owner_id)
    all_claims = list((await db.scalars(claims_stmt)).all())
    unsupported = [
        c for c in all_claims
        if (hasattr(c.support_status, "value") and c.support_status.value in ("UNSUPPORTED", "CONTRADICTED"))
        or str(c.support_status) in ("UNSUPPORTED", "CONTRADICTED", "ClaimStatus.unsupported", "ClaimStatus.contradicted")
    ]

    if unsupported and not req.force_unresolved_claims:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot finalize resume: unresolved unsupported claims exist. Review or explicitly acknowledge before finalization.",
        )

    # Fetch latest optimization run and changes
    opt_stmt = (
        select(OptimizationRun)
        .where(OptimizationRun.analysis_id == analysis_id)
        .order_by(desc(OptimizationRun.iteration))
    )
    latest_opt_run = (await db.scalars(opt_stmt)).first()
    if not latest_opt_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No optimization run found to finalize")

    changes_stmt = select(ResumeChange).where(ResumeChange.optimization_run_id == latest_opt_run.id)
    changes = list((await db.scalars(changes_stmt)).all())

    # Fetch initial resume text
    ver_stmt = select(ResumeVersion).where(ResumeVersion.id == analysis.resume_version_id)
    base_version = (await db.scalars(ver_stmt)).first()
    if not base_version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")

    finalized_text = base_version.content_text
    applied_count = 0
    manual_count = 0
    rejected_count = 0
    trace_summaries: list[dict[str, Any]] = []

    for ch in changes:
        if ch.decision in (ChangeDecision.accepted, "accepted"):
            if ch.before_text in finalized_text:
                finalized_text = finalized_text.replace(ch.before_text, ch.after_text, 1)
            applied_count += 1
            trace_summaries.append({
                "change_id": str(ch.id),
                "type": "AI_ACCEPTED",
                "before": ch.before_text,
                "after": ch.after_text,
                "is_manual": False,
            })
        elif ch.decision in (ChangeDecision.edited, "edited"):
            effective_replacement = ch.manual_text or ch.after_text
            if ch.before_text in finalized_text:
                finalized_text = finalized_text.replace(ch.before_text, effective_replacement, 1)
            applied_count += 1
            manual_count += 1
            trace_summaries.append({
                "change_id": str(ch.id),
                "type": "MANUAL_EDIT",
                "before": ch.before_text,
                "after": effective_replacement,
                "is_manual": True,
            })
        elif ch.decision in (ChangeDecision.rejected, "rejected"):
            rejected_count += 1
            trace_summaries.append({
                "change_id": str(ch.id),
                "type": "REJECTED",
                "before": ch.before_text,
                "is_manual": False,
            })

    # Create new published ResumeVersion
    max_ver_stmt = (
        select(ResumeVersion.version_number)
        .where(ResumeVersion.resume_id == base_version.resume_id)
        .order_by(desc(ResumeVersion.version_number))
    )
    latest_ver_num = await db.scalar(max_ver_stmt) or 1
    new_version_id = uuid4()
    new_version = ResumeVersion(
        id=new_version_id,
        resume_id=base_version.resume_id,
        version_number=latest_ver_num + 1,
        source_uri="human_approved_final",
        content_text=finalized_text,
        is_final=True,
    )
    db.add(new_version)

    # Record Approval History
    approval = ApprovalHistory(
        id=uuid4(),
        analysis_id=analysis_id,
        user_id=owner_id,
        decision=ChangeDecision.accepted,
        notes=req.notes or "Human-in-the-loop review finalized and approved.",
    )
    db.add(approval)

    await db.commit()

    return FinalizeReviewResponse(
        analysis_id=analysis_id,
        new_resume_version_id=new_version_id,
        version_number=latest_ver_num + 1,
        finalized_resume_text=finalized_text,
        changes_applied_count=applied_count,
        manual_edits_count=manual_count,
        rejected_count=rejected_count,
        trace_summary=trace_summaries,
    )
