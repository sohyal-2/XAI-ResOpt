"""Critic Agent: Multi-dimensional quality evaluation node for proposed resume enhancements."""

from __future__ import annotations


from app.agents.optimization_models import CriticAgentOutput, CriticEvaluation, ProposedChange


class CriticAgent:
    """Critic Agent evaluating relevance, clarity, grammar, ATS safety, and factual risks."""

    def __init__(self) -> None:
        self.fluff_words = [
            "in order to",
            "various different",
            "responsible for the",
            "worked tirelessly",
            "go-getter",
            "synergized",
            "hardworking",
            "ninja",
            "rockstar",
        ]

    def evaluate(
        self,
        proposed_changes: list[ProposedChange],
        job_keywords: list[str] | None = None,
    ) -> CriticAgentOutput:
        """Evaluates each proposed resume modification across 8 quality dimensions."""
        evaluations: list[CriticEvaluation] = []
        approved_changes: list[ProposedChange] = []
        rejected_changes: list[ProposedChange] = []
        keywords = [k.lower() for k in (job_keywords or [])]

        for change in proposed_changes:
            eval_item = self._evaluate_single_change(change, keywords)
            evaluations.append(eval_item)

            if eval_item.verdict == "APPROVED":
                approved_changes.append(change)
            else:
                rejected_changes.append(change)

        avg_score = (
            sum(e.overall_critic_score for e in evaluations) / len(evaluations)
            if evaluations
            else 1.0
        )

        return CriticAgentOutput(
            status="completed",
            evaluations=evaluations,
            approved_changes=approved_changes,
            rejected_changes=rejected_changes,
            average_critic_score=round(avg_score, 4),
        )

    def _evaluate_single_change(
        self,
        change: ProposedChange,
        job_keywords: list[str],
    ) -> CriticEvaluation:
        text = change.after_text.strip()
        lower_text = text.lower()
        feedback: list[str] = []

        # 1. Relevance Score
        matched_kw = sum(1 for kw in job_keywords if kw in lower_text)
        relevance_score = min(1.0, 0.6 + (matched_kw * 0.1)) if job_keywords else 0.85
        if matched_kw > 0:
            feedback.append(f"Includes {matched_kw} target job keywords.")

        # 2. Clarity Score
        word_count = len(text.split())
        if 8 <= word_count <= 35:
            clarity_score = 0.95
        elif word_count < 5:
            clarity_score = 0.50
            feedback.append("Text is too brief for an impactful accomplishment bullet.")
        else:
            clarity_score = 0.70
            feedback.append("Text exceeds recommended length for standard ATS single-bullet display.")

        # 3. Grammar & Mechanics Score
        grammar_score = 1.0
        if not text[0].isupper():
            grammar_score -= 0.15
            feedback.append("Opening character should be capitalized.")
        if not text.endswith(".") and change.section != "skills":
            grammar_score -= 0.10
            feedback.append("Bullet should terminate with standard punctuation.")
        grammar_score = max(0.4, grammar_score)

        # 4. Conciseness Score
        conciseness_score = 1.0
        for fluff in self.fluff_words:
            if fluff in lower_text:
                conciseness_score -= 0.20
                feedback.append(f"Contains filler/cliche phrase '{fluff}'.")
        conciseness_score = max(0.4, conciseness_score)

        # 5. Keyword Quality Score
        keyword_quality_score = 0.90
        # Check for unnatural repetition / stuffing
        words = lower_text.split()
        if len(words) > 0 and len(set(words)) / len(words) < 0.65:
            keyword_quality_score = 0.60
            feedback.append("High word repetition detected; ensure natural syntax.")

        # 6. ATS Compatibility Score
        ats_score = 1.0
        special_chars = ["│", "┌", "┐", "└", "┘", "├", "┤", "❖", "➢", "★", "■"]
        if any(c in text for c in special_chars):
            ats_score = 0.40
            feedback.append("Contains non-standard graphical symbols that disrupt ATS parsers.")

        # 7. Professional Quality Score
        strong_starters = [
            "Architected", "Engineered", "Designed", "Implemented", "Spearheaded",
            "Optimized", "Scaled", "Deployed", "Developed", "Led", "Built", "Collaborated"
        ]
        first_word = text.split()[0] if text.split() else ""
        if any(first_word.startswith(verb) for verb in strong_starters):
            professional_score = 0.95
        else:
            professional_score = 0.75

        # 8. Factual Risk Score (Higher score = lower risk)
        # Check if text contains high risk unbacked buzzwords or ungrounded claims
        factual_risk_penalty = 0.0
        if change.risk_level == "high" or change.support_status == "UNSUPPORTED":
            factual_risk_penalty = 0.50
            feedback.append("Flagged for high factual risk or unverified claims.")
        elif not change.evidence_ids:
            factual_risk_penalty = 0.20
            feedback.append("No supporting candidate evidence IDs provided.")

        factual_safety_score = max(0.1, 1.0 - factual_risk_penalty)

        # Weighted Overall Critic Score
        overall_score = (
            relevance_score * 0.15
            + clarity_score * 0.15
            + grammar_score * 0.10
            + conciseness_score * 0.10
            + keyword_quality_score * 0.10
            + ats_score * 0.15
            + professional_score * 0.10
            + factual_safety_score * 0.15
        )

        # Determine Verdict
        if overall_score >= 0.75 and factual_safety_score >= 0.70:
            verdict = "APPROVED"
        elif overall_score >= 0.55:
            verdict = "NEEDS_REVISION"
        else:
            verdict = "REJECTED"

        return CriticEvaluation(
            change_id=change.change_id,
            relevance_score=round(relevance_score, 4),
            clarity_score=round(clarity_score, 4),
            grammar_score=round(grammar_score, 4),
            conciseness_score=round(conciseness_score, 4),
            keyword_quality_score=round(keyword_quality_score, 4),
            ats_compatibility_score=round(ats_score, 4),
            professional_quality_score=round(professional_score, 4),
            factual_risk_score=round(1.0 - factual_safety_score, 4),
            overall_critic_score=round(overall_score, 4),
            verdict=verdict,
            feedback=feedback,
        )
