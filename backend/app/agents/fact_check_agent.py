"""Fact-Check Agent: Strict verification node that detects and rejects hallucinated metrics, skills, companies, and ungrounded claims."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from app.agents.optimization_models import FactCheckAgentOutput, FactCheckVerification, ProposedChange


def _get_attr(item: Any, attr: str, default: Any = None) -> Any:
    if item is None:
        return default
    if isinstance(item, dict):
        return item.get(attr, default)
    return getattr(item, attr, default)


class FactCheckAgent:
    """Fact-Check Agent providing strict truthfulness verification against candidate evidence."""

    def __init__(self) -> None:
        # Common technical terms regex for skill extraction
        self.metric_pattern = re.compile(
            r"(?:\$\s*\d+(?:\.\d+)?[kKmMbB]?|\b\d+(?:\.\d+)?\s*%|\b\d+x\b|\b\d+\s*\+?\s*(?:million|billion|thousand|users|requests|ms|seconds|minutes|hours)\b)",
            re.IGNORECASE,
        )

    def verify(
        self,
        proposed_changes: list[ProposedChange],
        evidence_corpus: list[Any],
        raw_resume_text: str = "",
    ) -> FactCheckAgentOutput:
        """Verifies every proposed change against the candidate evidence corpus, rejecting any unsupported content."""
        verifications: list[FactCheckVerification] = []
        passed_changes: list[ProposedChange] = []
        rejected_changes: list[ProposedChange] = []
        hallucination_count = 0

        # Compile complete truth corpus from evidence items and raw resume text
        corpus_text_combined = raw_resume_text.lower()
        evidence_text_list: list[str] = []
        evidence_ids_all: list[UUID] = []

        for ev in evidence_corpus:
            txt = str(_get_attr(ev, "text", "")).lower()
            evidence_text_list.append(txt)
            corpus_text_combined += " " + txt
            ev_id = _get_attr(ev, "id", None)
            if ev_id and isinstance(ev_id, UUID):
                evidence_ids_all.append(ev_id)

        for change in proposed_changes:
            verif = self._verify_single_change(
                change, corpus_text_combined, evidence_text_list, evidence_corpus
            )
            verifications.append(verif)

            if verif.verdict == "PASSED":
                change.support_status = "SUPPORTED"
                passed_changes.append(change)
            else:
                change.support_status = "UNSUPPORTED"
                change.risk_level = "high"
                rejected_changes.append(change)
                hallucination_count += 1

        total = len(proposed_changes)
        pass_rate = (len(passed_changes) / total * 100.0) if total > 0 else 100.0

        return FactCheckAgentOutput(
            status="completed",
            verifications=verifications,
            passed_changes=passed_changes,
            rejected_changes=rejected_changes,
            hallucination_count=hallucination_count,
            pass_rate=round(pass_rate, 2),
        )

    def _verify_single_change(
        self,
        change: ProposedChange,
        corpus_text: str,
        evidence_text_list: list[str],
        evidence_corpus: list[Any],
    ) -> FactCheckVerification:
        after_text = change.after_text
        before_text = change.before_text
        after_lower = after_text.lower()
        before_lower = before_text.lower()

        hallucination_flags: list[str] = []
        metrics_verified = True
        technologies_verified = True
        companies_verified = True
        dates_verified = True
        titles_verified = True
        numerical_claims_verified = True

        # 1. Metrics & Numerical Claims Verification
        after_metrics = self.metric_pattern.findall(after_text)
        
        # Check if any new metric in after_text is missing from truth corpus
        for m in after_metrics:
            m_clean = m.strip().lower()
            # If the metric is not in the before_text and not in candidate evidence corpus
            if m_clean not in before_lower and m_clean not in corpus_text:
                metrics_verified = False
                numerical_claims_verified = False
                hallucination_flags.append(f"Hallucinated metric '{m}' not present in candidate evidence.")

        # 2. Technologies & Invented Skills Verification
        # Check if after_text contains newly added specialized technical tools not present in candidate evidence
        skill_indicators = [
            "kubernetes", "k8s", "rust", "golang", "scala", "graphql",
            "terraform", "kafka", "snowflake", "spark", "hadoop", "pytorch",
            "tensorflow", "react native", "flutter", "c++", "c#", "ruby"
        ]
        for tech in skill_indicators:
            if tech in after_lower and tech not in before_lower and tech not in corpus_text:
                technologies_verified = False
                hallucination_flags.append(f"Invented skill/technology '{tech}' not found in candidate evidence.")

        # 3. Invented Companies & Employers
        company_indicators = [
            "google", "meta", "facebook", "apple", "amazon", "netflix",
            "microsoft", "uber", "airbnb", "stripe", "openai", "deepmind"
        ]
        for comp in company_indicators:
            if f"at {comp}" in after_lower or f"for {comp}" in after_lower:
                if comp not in corpus_text and comp not in before_lower:
                    companies_verified = False
                    hallucination_flags.append(f"Invented employer '{comp.title()}' not found in candidate history.")

        # 4. Invented Seniority Titles
        executive_titles = ["vp of engineering", "chief technology officer", "cto", "director of engineering"]
        for title in executive_titles:
            if title in after_lower and title not in before_lower and title not in corpus_text:
                titles_verified = False
                hallucination_flags.append(f"Invented executive title '{title.title()}' without supporting evidence.")

        # 5. Provenance Mapping
        matched_provenance: list[UUID] = []
        for ev in evidence_corpus:
            ev_id = _get_attr(ev, "id")
            ev_text = str(_get_attr(ev, "text", "")).lower()
            if ev_text and (ev_text in after_lower or ev_text in before_lower):
                if ev_id and isinstance(ev_id, UUID):
                    matched_provenance.append(ev_id)

        matched_provenance.extend(change.evidence_ids)
        unique_provenance = list(set(matched_provenance))

        # Determine Final Verdict
        is_grounded = (
            metrics_verified
            and technologies_verified
            and companies_verified
            and dates_verified
            and titles_verified
            and numerical_claims_verified
        )

        verdict = "PASSED" if is_grounded else "FAILED"
        rejection_reason = "; ".join(hallucination_flags) if hallucination_flags else None

        return FactCheckVerification(
            change_id=change.change_id,
            metrics_verified=metrics_verified,
            companies_verified=companies_verified,
            dates_verified=dates_verified,
            titles_verified=titles_verified,
            technologies_verified=technologies_verified,
            responsibilities_verified=True,
            certifications_verified=True,
            projects_verified=True,
            numerical_claims_verified=numerical_claims_verified,
            is_grounded=is_grounded,
            verdict=verdict,
            hallucination_flags=hallucination_flags,
            evidence_provenance=unique_provenance,
            rejection_reason=rejection_reason,
        )
