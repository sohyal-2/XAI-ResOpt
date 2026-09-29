"""Deterministic scoring engine for computing the XAI-ResOpt ATS Compatibility Score."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from app.agents.models import AnalysisState, ConsolidatedAnalysisOutput
from app.scoring.models import (
    CategoryScoreDetail,
    EvidenceTraceItem,
    RequirementTraceItem,
    RiskIndicator,
    ScorePenaltyDetail,
    ScoreReason,
    ScoringResult,
    ScoringWeights,
)


def _get_attr(item: Any, attr: str, default: Any = None) -> Any:
    """Safely extracts an attribute whether item is a Pydantic model or a dictionary."""
    if item is None:
        return default
    if isinstance(item, dict):
        return item.get(attr, default)
    return getattr(item, attr, default)


class ScoringEngine:
    """Deterministic, explainable XAI-ResOpt scoring engine.
    
    Computes category breakdown, penalties, reasons, supporting evidence,
    and a requirement-to-evidence traceability graph with zero LLM hallucinations.
    """

    def __init__(self, default_weights: ScoringWeights | None = None) -> None:
        self.weights = default_weights or ScoringWeights()

    def calculate_score(
        self,
        state: AnalysisState | ConsolidatedAnalysisOutput | dict[str, Any],
        custom_weights: ScoringWeights | None = None,
    ) -> ScoringResult:
        """Computes the deterministic XAI-ResOpt ATS Compatibility Score."""
        weights = custom_weights or self.weights
        norm_weights = weights.normalized_weights()

        # Extract sub-states safely
        resume = _get_attr(state, "resume_extraction", None)
        job = _get_attr(state, "job_extraction", None)
        grounded_contexts = _get_attr(state, "grounded_contexts", []) or []
        evidence_corpus = _get_attr(state, "evidence_corpus", []) or []
        
        ats_out = _get_attr(state, "ats_output", _get_attr(state, "ats_analysis", None))
        skill_out = _get_attr(state, "skill_output", _get_attr(state, "skill_analysis", None))
        evidence_out = _get_attr(state, "evidence_output", _get_attr(state, "evidence_analysis", None))

        # 1. Compute Category Scores
        cat_scores: dict[str, CategoryScoreDetail] = {}
        all_reasons: list[ScoreReason] = []
        matched_reqs: list[RequirementTraceItem] = []
        missing_reqs: list[RequirementTraceItem] = []
        risk_indicators: list[RiskIndicator] = []
        traceability_map: dict[str, list[str]] = {}
        supporting_evidence_items: list[EvidenceTraceItem] = []

        # Category 1: Keyword Coverage
        kw_score, kw_factors, kw_req_ids, kw_ev_ids = self._compute_keyword_coverage(
            resume, job, ats_out, grounded_contexts
        )
        cat_scores["keyword_coverage"] = CategoryScoreDetail(
            category="keyword_coverage",
            raw_score=round(kw_score, 4),
            percentage_score=round(kw_score * 100.0, 2),
            weight=round(norm_weights["keyword_coverage"], 4),
            weighted_contribution=round(kw_score * norm_weights["keyword_coverage"], 4),
            description="Coverage of exact job description keywords and domain terminology.",
            contributing_factors=kw_factors,
            requirement_ids=kw_req_ids,
            evidence_ids=kw_ev_ids,
        )

        # Category 2: Semantic Similarity
        sem_score, sem_factors, sem_req_ids, sem_ev_ids = self._compute_semantic_similarity(
            grounded_contexts
        )
        cat_scores["semantic_similarity"] = CategoryScoreDetail(
            category="semantic_similarity",
            raw_score=round(sem_score, 4),
            percentage_score=round(sem_score * 100.0, 2),
            weight=round(norm_weights["semantic_similarity"], 4),
            weighted_contribution=round(sem_score * norm_weights["semantic_similarity"], 4),
            description="Vector and conceptual semantic alignment with job requirements.",
            contributing_factors=sem_factors,
            requirement_ids=sem_req_ids,
            evidence_ids=sem_ev_ids,
        )

        # Category 3: Requirement Coverage
        req_score, req_factors, matched, missing, req_trace_map = self._compute_requirement_coverage(
            job, grounded_contexts, resume
        )
        matched_reqs.extend(matched)
        missing_reqs.extend(missing)
        for r_id_str, ev_list in req_trace_map.items():
            traceability_map.setdefault(r_id_str, []).extend(ev_list)

        cat_scores["requirement_coverage"] = CategoryScoreDetail(
            category="requirement_coverage",
            raw_score=round(req_score, 4),
            percentage_score=round(req_score * 100.0, 2),
            weight=round(norm_weights["requirement_coverage"], 4),
            weighted_contribution=round(req_score * norm_weights["requirement_coverage"], 4),
            description="Weighted fulfillment of mandatory, preferred, and nice-to-have requirements.",
            contributing_factors=req_factors,
            requirement_ids=[m.requirement_id for m in matched_reqs if m.requirement_id],
            evidence_ids=[ev for m in matched_reqs for ev in m.evidence_ids],
        )

        # Category 4: Evidence Confidence
        ev_score, ev_factors, ev_items = self._compute_evidence_confidence(
            evidence_out, grounded_contexts, evidence_corpus
        )
        supporting_evidence_items.extend(ev_items)
        cat_scores["evidence_confidence"] = CategoryScoreDetail(
            category="evidence_confidence",
            raw_score=round(ev_score, 4),
            percentage_score=round(ev_score * 100.0, 2),
            weight=round(norm_weights["evidence_confidence"], 4),
            weighted_contribution=round(ev_score * norm_weights["evidence_confidence"], 4),
            description="Confidence, verifiable metrics, and provenance backing candidate claims.",
            contributing_factors=ev_factors,
            evidence_ids=[item.evidence_id for item in ev_items if item.evidence_id],
        )

        # Category 5: Experience Alignment
        exp_score, exp_factors = self._compute_experience_alignment(resume, job, skill_out)
        cat_scores["experience_alignment"] = CategoryScoreDetail(
            category="experience_alignment",
            raw_score=round(exp_score, 4),
            percentage_score=round(exp_score * 100.0, 2),
            weight=round(norm_weights["experience_alignment"], 4),
            weighted_contribution=round(exp_score * norm_weights["experience_alignment"], 4),
            description="Seniority level, leadership scope, and years of experience alignment.",
            contributing_factors=exp_factors,
        )

        # Category 6: Section Completeness
        sec_score, sec_factors = self._compute_section_completeness(resume, ats_out)
        cat_scores["section_completeness"] = CategoryScoreDetail(
            category="section_completeness",
            raw_score=round(sec_score, 4),
            percentage_score=round(sec_score * 100.0, 2),
            weight=round(norm_weights["section_completeness"], 4),
            weighted_contribution=round(sec_score * norm_weights["section_completeness"], 4),
            description="Presence and standard naming of critical resume sections (Experience, Education, Skills, Contact).",
            contributing_factors=sec_factors,
        )

        # Category 7: Formatting & ATS Safety
        fmt_score, fmt_factors, fmt_risks = self._compute_formatting_safety(resume, ats_out)
        risk_indicators.extend(fmt_risks)
        cat_scores["formatting_safety"] = CategoryScoreDetail(
            category="formatting_safety",
            raw_score=round(fmt_score, 4),
            percentage_score=round(fmt_score * 100.0, 2),
            weight=round(norm_weights["formatting_safety"], 4),
            weighted_contribution=round(fmt_score * norm_weights["formatting_safety"], 4),
            description="ATS parsability score, layout readability, and absence of parsing blockers.",
            contributing_factors=fmt_factors,
        )

        # Category 8: Skill Match
        sk_score, sk_factors = self._compute_skill_match(skill_out, job)
        cat_scores["skill_match"] = CategoryScoreDetail(
            category="skill_match",
            raw_score=round(sk_score, 4),
            percentage_score=round(sk_score * 100.0, 2),
            weight=round(norm_weights["skill_match"], 4),
            weighted_contribution=round(sk_score * norm_weights["skill_match"], 4),
            description="Mandatory and preferred skill coverage with transferable capability boost.",
            contributing_factors=sk_factors,
        )

        # 2. Compute Penalties
        penalties, penalty_reasons = self._compute_penalties(
            evidence_out, missing_reqs, weights
        )
        all_reasons.extend(penalty_reasons)

        total_penalty = sum(p.deduction for p in penalties)
        raw_weighted_score = sum(c.weighted_contribution for c in cat_scores.values())

        # Net Score calculation
        net_score_normalized = max(0.0, min(1.0, raw_weighted_score - total_penalty))
        overall_score = round(net_score_normalized * 100.0, 2)

        # 3. Generate Positive & Constructive Reasons
        all_reasons.extend(self._generate_reasons(cat_scores, matched_reqs, missing_reqs))

        return ScoringResult(
            score_name="XAI-ResOpt ATS Compatibility Score",
            calculation_version="xai-resopt-v1.0-deterministic",
            overall_score=overall_score,
            overall_score_normalized=round(net_score_normalized, 4),
            raw_weighted_score=round(raw_weighted_score, 4),
            total_penalty=round(total_penalty, 4),
            category_scores=cat_scores,
            penalties=penalties,
            reasons=all_reasons,
            supporting_evidence=supporting_evidence_items,
            matched_requirements=matched_reqs,
            missing_requirements=missing_reqs,
            risk_indicators=risk_indicators,
            traceability_map=traceability_map,
            weights_applied=weights,
            calculation_metadata={
                "mandatory_requirements_count": len([m for m in matched_reqs + missing_reqs if m.kind == "mandatory"]),
                "preferred_requirements_count": len([m for m in matched_reqs + missing_reqs if m.kind == "preferred"]),
                "grounded_contexts_evaluated": len(grounded_contexts),
                "evidence_items_linked": len(supporting_evidence_items),
            },
        )

    # -------------------------------------------------------------------------
    # Dimension Calculators
    # -------------------------------------------------------------------------

    def _compute_keyword_coverage(
        self,
        resume: Any,
        job: Any,
        ats_out: Any,
        grounded_contexts: list[Any],
    ) -> tuple[float, list[str], list[UUID], list[UUID]]:
        pct = _get_attr(ats_out, "keyword_coverage_percent", None)
        if pct is not None:
            score = max(0.0, min(1.0, float(pct) / 100.0))
            factors = [f"ATS parser identified {pct:.1f}% keyword coverage."]
            req_ids: list[UUID] = []
            ev_ids: list[UUID] = []
            return score, factors, req_ids, ev_ids

        # Fallback deterministic calculation from requirements
        requirements = _get_attr(job, "requirements", []) or []
        if not requirements:
            return 1.0, ["No JD requirements specified."], [], []

        raw_resume = _get_attr(resume, "raw_text", "").lower() if resume else ""
        matched_count = 0
        total_count = len(requirements)
        factors = []
        req_ids = []
        ev_ids = []

        for req in requirements:
            req_text = _get_attr(req, "text", "").lower()
            original_terms = _get_attr(req, "original_terms", [])
            terms_to_check = [str(t).lower() for t in original_terms] if original_terms else [req_text]
            matched = any(term in raw_resume for term in terms_to_check)
            if matched:
                matched_count += 1
                req_id = _get_attr(req, "id", None)
                if req_id and isinstance(req_id, UUID):
                    req_ids.append(req_id)

        score = matched_count / total_count if total_count > 0 else 1.0
        factors.append(f"Matched {matched_count} of {total_count} required keyword groups ({score * 100:.1f}%).")
        return score, factors, req_ids, ev_ids

    def _compute_semantic_similarity(
        self,
        grounded_contexts: list[Any],
    ) -> tuple[float, list[str], list[UUID], list[UUID]]:
        if not grounded_contexts:
            return 0.5, ["No grounded requirement retrieval contexts available; assigned neutral baseline."], [], []

        sims: list[float] = []
        req_ids: list[UUID] = []
        ev_ids: list[UUID] = []

        for ctx in grounded_contexts:
            req_id = _get_attr(ctx, "requirement_id", None)
            if req_id and isinstance(req_id, UUID):
                req_ids.append(req_id)
            
            # Check matched_evidence or top_evidence
            matched_ev = _get_attr(ctx, "matched_evidence", _get_attr(ctx, "top_evidence", []))
            if matched_ev:
                for ev in matched_ev:
                    sem = float(_get_attr(ev, "semantic_score", _get_attr(ctx, "top_score", 0.0)))
                    sims.append(sem)
                    ev_id = _get_attr(ev, "evidence_id", None)
                    if ev_id and isinstance(ev_id, UUID):
                        ev_ids.append(ev_id)
            else:
                top_s = float(_get_attr(ctx, "top_score", 0.0))
                sims.append(top_s)

        avg_sim = sum(sims) / len(sims) if sims else 0.0
        score = max(0.0, min(1.0, avg_sim))
        factors = [f"Average semantic vector similarity across {len(grounded_contexts)} requirements is {score:.4f}."]
        return score, factors, req_ids, ev_ids

    def _compute_requirement_coverage(
        self,
        job: Any,
        grounded_contexts: list[Any],
        resume: Any,
    ) -> tuple[float, list[str], list[RequirementTraceItem], list[RequirementTraceItem], dict[str, list[str]]]:
        requirements = _get_attr(job, "requirements", []) or []
        if not requirements:
            return 1.0, ["No formal requirements listed."], [], [], {}

        # Build map of grounded contexts by requirement_id and by requirement_text
        ctx_map_by_id: dict[str, Any] = {}
        ctx_map_by_text: dict[str, Any] = {}
        for ctx in grounded_contexts:
            r_id = str(_get_attr(ctx, "requirement_id", ""))
            if r_id:
                ctx_map_by_id[r_id] = ctx
            r_txt = str(_get_attr(ctx, "requirement_text", "")).strip().lower()
            if r_txt:
                ctx_map_by_text[r_txt] = ctx

        raw_resume = _get_attr(resume, "raw_text", "").lower() if resume else ""
        weights_map = {"mandatory": 1.0, "preferred": 0.6, "nice_to_have": 0.3, "contextual": 0.2}
        total_possible_weight = 0.0
        earned_weight = 0.0

        matched_items: list[RequirementTraceItem] = []
        missing_items: list[RequirementTraceItem] = []
        trace_map: dict[str, list[str]] = {}
        factors: list[str] = []

        for req in requirements:
            r_id = _get_attr(req, "id", None)
            r_id_str = str(r_id) if r_id else ""
            r_kind = str(_get_attr(req, "kind", "mandatory")).lower()
            r_cat = str(_get_attr(req, "category", "technical_skill"))
            r_text = str(_get_attr(req, "text", ""))

            w = weights_map.get(r_kind, 0.5)
            total_possible_weight += w

            # Lookup context
            ctx = ctx_map_by_id.get(r_id_str) or ctx_map_by_text.get(r_text.strip().lower())
            support_status = str(_get_attr(ctx, "support_status", "NOT_FOUND")).upper()
            top_score = float(_get_attr(ctx, "top_score", _get_attr(ctx, "hybrid_score", 0.0)))

            ev_ids = []
            if ctx:
                matched_ev = _get_attr(ctx, "matched_evidence", _get_attr(ctx, "top_evidence", []))
                for ev in matched_ev:
                    e_id = _get_attr(ev, "evidence_id", None)
                    if e_id:
                        ev_ids.append(e_id)
                        key = r_id_str if r_id_str else r_text
                        trace_map.setdefault(key, []).append(str(e_id))

            # Also check direct terms match in resume text as additional confirmation
            orig_terms = [_get_attr(t, "original", str(t)) for t in _get_attr(req, "original_terms", [])]
            direct_term_match = any(t.lower() in raw_resume for t in orig_terms) if orig_terms else False

            is_supported = (support_status in ("SUPPORTED", "PARTIALLY_SUPPORTED") and (top_score > 0.35 or ev_ids)) or direct_term_match

            if is_supported:
                req_score = max(0.5, top_score if top_score > 0 else 0.85)
                earned_weight += w * req_score
                matched_items.append(
                    RequirementTraceItem(
                        requirement_id=r_id if isinstance(r_id, UUID) else None,
                        text=r_text,
                        kind=r_kind,
                        category=r_cat,
                        support_status=support_status if support_status != "NOT_FOUND" else "SUPPORTED",
                        score=round(req_score, 4),
                        matched_terms=orig_terms,
                        evidence_ids=[e for e in ev_ids if isinstance(e, UUID)],
                    )
                )
            else:
                missing_items.append(
                    RequirementTraceItem(
                        requirement_id=r_id if isinstance(r_id, UUID) else None,
                        text=r_text,
                        kind=r_kind,
                        category=r_cat,
                        support_status="MISSING",
                        score=0.0,
                        missing_terms=orig_terms,
                        evidence_ids=[],
                    )
                )

        score = earned_weight / total_possible_weight if total_possible_weight > 0 else 1.0
        factors.append(
            f"Fulfillment: {len(matched_items)}/{len(requirements)} requirements backed by evidence (Score: {score:.4f})."
        )
        return score, factors, matched_items, missing_items, trace_map

    def _compute_evidence_confidence(
        self,
        evidence_out: Any,
        grounded_contexts: list[Any],
        evidence_corpus: list[Any],
    ) -> tuple[float, list[str], list[EvidenceTraceItem]]:
        ev_items: list[EvidenceTraceItem] = []
        confidences: list[float] = []

        factual_score = _get_attr(evidence_out, "factual_support_score", None)
        if factual_score is not None:
            score = float(factual_score)
            factors = [f"Evidence Agent computed factual support score of {score:.4f}."]
            claims = _get_attr(evidence_out, "claim_evaluations", _get_attr(evidence_out, "claims_evaluation", []))
            for c in claims:
                c_id = _get_attr(c, "evidence_id", None)
                conf = float(_get_attr(c, "confidence", 0.8))
                confidences.append(conf)
                ev_items.append(
                    EvidenceTraceItem(
                        evidence_id=c_id if isinstance(c_id, UUID) else None,
                        source_type="resume",
                        source_location=_get_attr(c, "source_location", _get_attr(c, "source_provenance", None)),
                        text_snippet=str(_get_attr(c, "claim_text", "")),
                        confidence=round(conf, 4),
                        supported_requirement_ids=[_get_attr(c, "requirement_id")] if _get_attr(c, "requirement_id") else [],
                    )
                )
            return score, factors, ev_items

        # Fallback to grounded contexts
        for ctx in grounded_contexts:
            matched_ev = _get_attr(ctx, "matched_evidence", _get_attr(ctx, "top_evidence", []))
            for ev in matched_ev:
                e_id = _get_attr(ev, "evidence_id", None)
                conf = float(_get_attr(ev, "evidence_score", 0.85))
                confidences.append(conf)
                ev_items.append(
                    EvidenceTraceItem(
                        evidence_id=e_id if isinstance(e_id, UUID) else None,
                        source_type=str(_get_attr(ev, "source", "resume")),
                        source_location=_get_attr(ev, "location", None),
                        text_snippet=str(_get_attr(ev, "snippet", "")),
                        confidence=round(conf, 4),
                        supported_requirement_ids=[_get_attr(ctx, "requirement_id")] if _get_attr(ctx, "requirement_id") else [],
                    )
                )

        score = sum(confidences) / len(confidences) if confidences else 0.85
        factors = [f"Average confidence across {len(confidences)} grounded evidence items is {score:.4f}."]
        return score, factors, ev_items

    def _compute_experience_alignment(
        self,
        resume: Any,
        job: Any,
        skill_out: Any,
    ) -> tuple[float, list[str]]:
        seniority_score = _get_attr(skill_out, "seniority_alignment_score", None)
        if seniority_score is not None:
            score = float(seniority_score)
            factors = [f"Skill Agent computed seniority alignment score: {score:.4f}."]
            return score, factors

        job_exp = int(_get_attr(job, "years_of_experience", 0) or 0)
        factors = []
        if job_exp <= 0:
            return 1.0, ["No minimum years of experience required for this role."]

        # Estimate resume years
        raw_text = _get_attr(resume, "raw_text", "").lower() if resume else ""
        candidate_years = 0
        matches = re.findall(r"\b(\d+)\s*\+?\s*years?\b", raw_text)
        if matches:
            candidate_years = max(int(m) for m in matches)

        if candidate_years >= job_exp:
            score = 1.0
            factors.append(f"Candidate experience ({candidate_years}+ yrs) meets or exceeds required ({job_exp} yrs).")
        elif candidate_years > 0:
            score = max(0.4, candidate_years / job_exp)
            factors.append(f"Candidate experience ({candidate_years} yrs) partially meets required ({job_exp} yrs).")
        else:
            score = 0.7
            factors.append("Experience years not explicitly stated; estimated partial seniority alignment.")

        return score, factors

    def _compute_section_completeness(
        self,
        resume: Any,
        ats_out: Any,
    ) -> tuple[float, list[str]]:
        sec_dict = _get_attr(ats_out, "section_presence", None)
        if sec_dict is not None and isinstance(sec_dict, dict):
            core = ["experience", "education", "skills"]
            present = sum(1 for k in core if sec_dict.get(k, False))
            score = present / len(core) if core else 1.0
            factors = [f"Present sections: {present}/{len(core)} core sections found."]
            return score, factors

        if not resume:
            return 0.5, ["Resume sections not available."]

        sections = _get_attr(resume, "sections", {})
        core = ["experience", "education", "skills"]
        present = sum(1 for k in core if k in sections and sections[k])
        score = present / len(core) if core else 1.0
        factors = [f"Found {present} of {len(core)} primary resume sections."]
        return score, factors

    def _compute_formatting_safety(
        self,
        resume: Any,
        ats_out: Any,
    ) -> tuple[float, list[str], list[RiskIndicator]]:
        risks: list[RiskIndicator] = []
        factors: list[str] = []

        parsability = _get_attr(ats_out, "parsability_score", _get_attr(ats_out, "ats_parsability_score", None))
        formatting_risks = _get_attr(ats_out, "formatting_risks", []) or []

        for r in formatting_risks:
            risks.append(
                RiskIndicator(
                    risk_type=str(_get_attr(r, "risk_type", "formatting")),
                    severity=str(_get_attr(r, "severity", "Medium")),
                    description=str(_get_attr(r, "description", "")),
                    remediation_hint=str(_get_attr(r, "remediation", "Use plain bullet points and standard headers.")),
                )
            )

        if parsability is not None:
            score = float(parsability)
            factors.append(f"ATS parsability score: {score:.4f}.")
            return score, factors, risks

        # Fallback simple check
        raw_text = _get_attr(resume, "raw_text", "") if resume else ""
        has_table_chars = any(c in raw_text for c in ["│", "┌", "┐", "└", "┘", "├", "┤", "┬", "┴", "┼"])
        if has_table_chars:
            risks.append(
                RiskIndicator(
                    risk_type="table_layout",
                    severity="Medium",
                    description="Detected ASCII / Unicode table grid characters.",
                    remediation_hint="Convert multi-column tables to clean semantic bullet points.",
                )
            )
            return 0.75, ["Table structures detected in resume."], risks

        factors.append("Clean formatting detected without structural parser blockers.")
        return 0.95, factors, risks

    def _compute_skill_match(
        self,
        skill_out: Any,
        job: Any,
    ) -> tuple[float, list[str]]:
        mand_pct = _get_attr(skill_out, "mandatory_skill_coverage_percent", _get_attr(skill_out, "mandatory_skill_coverage_pct", None))
        if mand_pct is not None:
            mand_f = float(mand_pct)
            pref_f = float(_get_attr(skill_out, "preferred_skill_coverage_percent", _get_attr(skill_out, "preferred_skill_coverage_pct", 50.0)))
            transferable_boost = min(0.15, len(_get_attr(skill_out, "transferable_evidence", [])) * 0.05)
            
            raw_score = (mand_f * 0.7 + pref_f * 0.3) / 100.0 + transferable_boost
            score = max(0.0, min(1.0, raw_score))
            factors = [
                f"Mandatory skill coverage: {mand_f:.1f}%, Preferred: {pref_f:.1f}%, Transferable boost: +{transferable_boost * 100:.1f}%."
            ]
            return score, factors

        return 0.80, ["Standard skill matching baseline applied."]

    def _compute_penalties(
        self,
        evidence_out: Any,
        missing_reqs: list[RequirementTraceItem],
        weights: ScoringWeights,
    ) -> tuple[list[ScorePenaltyDetail], list[ScoreReason]]:
        penalties: list[ScorePenaltyDetail] = []
        reasons: list[ScoreReason] = []

        # 1. Unsupported Claim Penalty
        unsupported_claims: list[str] = []
        unsupported_raw = _get_attr(evidence_out, "unsupported_claims", []) or []
        for c in unsupported_raw:
            unsupported_claims.append(str(_get_attr(c, "claim_text", c)))
        
        if unsupported_claims:
            deduction = min(
                weights.max_unsupported_claim_penalty,
                len(unsupported_claims) * weights.unsupported_claim_penalty_factor,
            )
            penalties.append(
                ScorePenaltyDetail(
                    penalty_name="unsupported_claims_penalty",
                    deduction=round(deduction, 4),
                    reason=f"Detected {len(unsupported_claims)} unverified or unsupported resume claims.",
                    offending_items=unsupported_claims[:5],
                )
            )
            reasons.append(
                ScoreReason(
                    factor_name="Unsupported Claims",
                    impact="Negative",
                    description=f"Deducted {deduction * 100:.1f}% due to unverified statements lacking provenance in the evidence corpus.",
                    recommendation="Ensure all metric achievements and technical accomplishments reference verifiable projects or employers.",
                )
            )

        # 2. Contradictions Penalty
        contradictions: list[str] = []
        contradictions_raw = _get_attr(evidence_out, "contradictions", []) or []
        for c in contradictions_raw:
            contradictions.append(str(_get_attr(c, "description", c)))

        if contradictions:
            deduction = min(
                weights.max_contradiction_penalty,
                len(contradictions) * weights.contradiction_penalty_factor,
            )
            penalties.append(
                ScorePenaltyDetail(
                    penalty_name="contradictions_penalty",
                    deduction=round(deduction, 4),
                    reason=f"Detected {len(contradictions)} conflicting statements or dates.",
                    offending_items=contradictions[:3],
                )
            )
            reasons.append(
                ScoreReason(
                    factor_name="Factual Contradictions",
                    impact="Negative",
                    description=f"Deducted {deduction * 100:.1f}% due to conflicting timeline, role, or metric assertions.",
                    recommendation="Review overlapping dates and conflicting metrics in work history.",
                )
            )

        # 3. Missing Mandatory Requirements Penalty
        missing_mandatory = [m for m in missing_reqs if m.kind == "mandatory"]
        if missing_mandatory:
            deduction = min(
                weights.max_missing_mandatory_penalty,
                len(missing_mandatory) * weights.missing_mandatory_penalty_factor,
            )
            penalties.append(
                ScorePenaltyDetail(
                    penalty_name="missing_mandatory_requirements_penalty",
                    deduction=round(deduction, 4),
                    reason=f"Resume lacks evidence for {len(missing_mandatory)} mandatory job requirements.",
                    offending_items=[m.text for m in missing_mandatory[:5]],
                )
            )
            reasons.append(
                ScoreReason(
                    factor_name="Missing Mandatory Prerequisites",
                    impact="Negative",
                    description=f"Deducted {deduction * 100:.1f}% because {len(missing_mandatory)} core prerequisites have no supporting evidence.",
                    recommendation="Explicitly add relevant experience, projects, or transferable coursework addressing mandatory requirements.",
                )
            )

        return penalties, reasons

    def _generate_reasons(
        self,
        cat_scores: dict[str, CategoryScoreDetail],
        matched_reqs: list[RequirementTraceItem],
        missing_reqs: list[RequirementTraceItem],
    ) -> list[ScoreReason]:
        reasons: list[ScoreReason] = []

        # Strong positive factors
        for cat_name, detail in cat_scores.items():
            if detail.percentage_score >= 80.0:
                reasons.append(
                    ScoreReason(
                        factor_name=detail.category.replace("_", " ").title(),
                        impact="Positive",
                        description=f"High performance ({detail.percentage_score:.1f}%) contributing +{detail.weighted_contribution * 100:.1f} pts to compatibility.",
                    )
                )
            elif detail.percentage_score < 50.0:
                reasons.append(
                    ScoreReason(
                        factor_name=detail.category.replace("_", " ").title(),
                        impact="Negative",
                        description=f"Low performance ({detail.percentage_score:.1f}%) reducing potential compatibility score.",
                    )
                )

        return reasons
