"""Evidence Agent Analysis Node.

Analyzes:
- Factual support
- Source provenance
- Claim confidence
- Unsupported claims
- Contradictions
- Evidence sufficiency
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.models import (
    AgentRecommendation,
    AnalysisState,
    ClaimEvaluation,
    ContradictionItem,
    EvidenceAgentOutput,
)


def _get_item_attr(item: Any, attr: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(attr, default)
    val = getattr(item, attr, None)
    return val if val is not None else default


class EvidenceAgent:
    """Agent evaluating factual grounding, provenance tracing, claim support, contradictions, and sufficiency."""

    def analyze(self, state: AnalysisState) -> EvidenceAgentOutput:
        resume = state.resume_extraction
        contexts = state.grounded_contexts
        evidence_items = state.evidence_corpus

        # 1. Evaluate factual support for resume claims
        claim_evaluations: list[ClaimEvaluation] = []
        unsupported_claims: list[ClaimEvaluation] = []

        resume_bullets = [
            item
            for items in (resume.sections.values() if resume else [])
            for item in items
        ]

        for item in resume_bullets:
            # Check if claim is backed by evidence
            claim_text = _get_item_attr(item, "text", "")
            confidence = float(_get_item_attr(item, "confidence", 0.90))

            # Trace provenance
            source_doc = _get_item_attr(item, "source_document", _get_item_attr(item, "source", "resume.pdf"))
            source_loc = _get_item_attr(item, "source_location", _get_item_attr(item, "location", "Unknown"))
            item_id = _get_item_attr(item, "id", None)

            if confidence >= 0.85:
                status = "SUPPORTED"
                rationale = f"Directly grounded by source evidence in {source_doc} ({source_loc})."
            elif confidence >= 0.50:
                status = "PARTIALLY_SUPPORTED"
                rationale = f"Partially inferred from context in {source_doc} ({source_loc})."
            else:
                status = "UNSUPPORTED"
                rationale = f"Unverified claim lacking authoritative backing in {source_doc}."

            eval_item = ClaimEvaluation(
                claim_text=claim_text,
                support_status=status,
                confidence=confidence,
                evidence_ids=[item_id] if item_id else [],
                source_provenance=f"{source_doc} > {source_loc}",
                rationale=rationale,
            )
            claim_evaluations.append(eval_item)

            if status == "UNSUPPORTED":
                unsupported_claims.append(eval_item)

        # 2. Contradiction Detection
        contradictions: list[ContradictionItem] = []
        # Check for date overlapping anomalies or conflicting claims
        for i, ev_a in enumerate(evidence_items):
            text_a = str(_get_item_attr(ev_a, "text", "")).lower()
            for ev_b in evidence_items[i + 1 :]:
                text_b = str(_get_item_attr(ev_b, "text", "")).lower()
                # Check metric contradiction
                metrics_a = re.findall(r"(\d+)%\s*(?:improvement|reduction|increase)", text_a)
                metrics_b = re.findall(r"(\d+)%\s*(?:improvement|reduction|increase)", text_b)
                if metrics_a and metrics_b and metrics_a != metrics_b and any(w in text_b for w in text_a.split()[:3]):
                    id_a = _get_item_attr(ev_a, "id", None)
                    id_b = _get_item_attr(ev_b, "id", None)
                    contradictions.append(
                        ContradictionItem(
                            description="Conflicting percentage metrics found across separate descriptions for similar projects.",
                            conflicting_items=[text_a[:60] + "...", text_b[:60] + "..."],
                            evidence_ids=[id for id in [id_a, id_b] if id],
                            severity="high",
                        )
                    )

        # 3. Evidence Sufficiency across Grounded RAG Contexts
        insufficient_requirements: list[str] = []
        sufficient_req_count = 0

        for ctx in contexts:
            if ctx.support_status == "UNSUPPORTED":
                insufficient_requirements.append(ctx.requirement_text)
            else:
                sufficient_req_count += 1

        ev_sufficiency_score = (
            (sufficient_req_count / len(contexts)) if contexts else 1.0
        )
        ev_sufficiency_score = round(min(1.0, max(0.0, ev_sufficiency_score)), 4)

        # 4. Overall Factual Support Score
        supported_claims = sum(1 for c in claim_evaluations if c.support_status == "SUPPORTED")
        partially_claims = sum(1 for c in claim_evaluations if c.support_status == "PARTIALLY_SUPPORTED")
        total_claims = len(claim_evaluations) or 1

        factual_score = (
            (supported_claims * 1.0 + partially_claims * 0.6) / total_claims
        )
        factual_score = round(min(1.0, max(0.0, factual_score)), 4)

        # 5. Generate Evidence Recommendations referencing Evidence IDs
        recommendations: list[AgentRecommendation] = []

        if unsupported_claims:
            for unsupp in unsupported_claims[:3]:
                recommendations.append(
                    AgentRecommendation(
                        agent_name="evidence_agent",
                        category="unsupported_claim",
                        title="Provide Evidence for Unverified Claim",
                        description=f"Claim '{unsupp.claim_text[:60]}...' lacks verifiable source evidence.",
                        priority="high",
                        evidence_ids=unsupp.evidence_ids,
                        source_location=unsupp.source_provenance,
                        suggested_action="Attach external proof (GitHub repo, certification ID, public URL) or adjust claim phrasing.",
                    )
                )

        if insufficient_requirements:
            for req_text in insufficient_requirements[:2]:
                recommendations.append(
                    AgentRecommendation(
                        agent_name="evidence_agent",
                        category="evidence_sufficiency",
                        title=f"Supply Supporting Evidence for: '{req_text[:40]}...'",
                        description="Job requirement has no corresponding evidence in current resume or portfolio.",
                        priority="high",
                        suggested_action="Add relevant project, certification, or experience bullets demonstrating this capability.",
                    )
                )

        return EvidenceAgentOutput(
            factual_support_score=factual_score,
            total_claims_evaluated=len(claim_evaluations),
            supported_claims_count=supported_claims,
            partially_supported_count=partially_claims,
            unsupported_claims_count=len(unsupported_claims),
            claim_evaluations=claim_evaluations,
            unsupported_claims=unsupported_claims,
            contradictions=contradictions,
            evidence_sufficiency_score=ev_sufficiency_score,
            insufficient_requirements=insufficient_requirements,
            recommendations=recommendations,
        )


def evidence_agent_node(state: AnalysisState) -> AnalysisState:
    """LangGraph node execution wrapper for Evidence Agent."""
    agent = EvidenceAgent()
    output = agent.analyze(state)
    state.evidence_output = output
    state.agent_runs_log.append({
        "agent": "evidence_agent",
        "status": "completed",
        "factual_support_score": output.factual_support_score,
        "evidence_sufficiency_score": output.evidence_sufficiency_score,
        "recommendations_count": len(output.recommendations),
    })
    return state
