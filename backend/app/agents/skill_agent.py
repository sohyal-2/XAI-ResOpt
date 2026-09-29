"""Skill Agent Analysis Node.

Analyzes:
- Semantic skill matching
- Mandatory skill coverage
- Preferred skill coverage
- Skill gaps
- Transferable evidence
- Seniority alignment
- Experience relevance
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.models import (
    AgentRecommendation,
    AnalysisState,
    SkillAgentOutput,
    SkillGapItem,
    TransferableEvidenceItem,
)

TRANSFERABLE_SKILL_MAP: dict[str, list[tuple[str, str, float]]] = {
    "fastapi": [("flask", "Flask backend development experience transfers directly to FastAPI ASGI architecture.", 0.85),
                ("django", "Django REST framework experience provides strong foundation for API design and ORM patterns in FastAPI.", 0.80)],
    "react": [("vue", "Vue.js component-based architecture and reactive state concepts transfer readily to React.", 0.78),
              ("angular", "Angular component architecture and TypeScript mastery translate to modern React development.", 0.75)],
    "next.js": [("react", "Strong React proficiency provides core foundational knowledge for Next.js SSR and App Router.", 0.88)],
    "kubernetes": [("docker", "Docker containerization and compose proficiency transfer to Kubernetes Pod and deployment orchestration.", 0.80)],
    "aws": [("gcp", "Google Cloud Platform infrastructure experience maps directly to equivalent AWS cloud services (ECS/EC2, S3, IAM).", 0.85),
            ("azure", "Microsoft Azure enterprise cloud architecture maps directly to AWS services.", 0.85)],
    "postgresql": [("mysql", "MySQL relational schema design, indexing, and SQL optimization apply directly to PostgreSQL.", 0.85)],
    "typescript": [("javascript", "Deep JavaScript mastery provides direct syntax and runtime foundation for TypeScript type safety.", 0.88)],
}


def _get_item_attr(item: Any, attr: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(attr, default)
    val = getattr(item, attr, None)
    return val if val is not None else default


class SkillAgent:
    """Agent analyzing technical skills, mandatory/preferred coverage, gaps, transferability, and seniority."""

    def analyze(self, state: AnalysisState) -> SkillAgentOutput:
        resume = state.resume_extraction
        job = state.job_extraction
        contexts = state.grounded_contexts

        raw_resume_text = resume.raw_text.lower() if resume else ""

        # Extract resume skills
        resume_skill_items = (
            resume.sections.get("skills", []) + resume.sections.get("experience", [])
            if resume
            else []
        )
        resume_skill_text = " ".join(item.text.lower() for item in resume_skill_items)

        # 1. Mandatory & Preferred Skill Coverage
        mandatory_skills = job.mandatory_skills if job else []
        preferred_skills = job.preferred_skills if job else []

        matched_mandatory: list[str] = []
        missing_mandatory: list[str] = []
        for term in mandatory_skills:
            canonical = term.canonical
            if canonical in resume_skill_text or term.original.lower() in raw_resume_text:
                matched_mandatory.append(term.original)
            else:
                missing_mandatory.append(term.original)

        matched_preferred: list[str] = []
        missing_preferred: list[str] = []
        for term in preferred_skills:
            canonical = term.canonical
            if canonical in resume_skill_text or term.original.lower() in raw_resume_text:
                matched_preferred.append(term.original)
            else:
                missing_preferred.append(term.original)

        mand_cov_pct = (
            (len(matched_mandatory) / len(mandatory_skills)) * 100.0 if mandatory_skills else 100.0
        )
        pref_cov_pct = (
            (len(matched_preferred) / len(preferred_skills)) * 100.0 if preferred_skills else 100.0
        )

        # 2. Skill Gaps Identification
        skill_gaps: list[SkillGapItem] = []
        for term in mandatory_skills:
            if term.original in missing_mandatory:
                skill_gaps.append(
                    SkillGapItem(
                        skill_name=term.original,
                        canonical=term.canonical,
                        kind="mandatory",
                        impact="High - Mandatory requirement for the role.",
                        missing_evidence_types=["experience", "project"],
                    )
                )

        for term in preferred_skills:
            if term.original in missing_preferred:
                skill_gaps.append(
                    SkillGapItem(
                        skill_name=term.original,
                        canonical=term.canonical,
                        kind="preferred",
                        impact="Medium - Preferred capability that improves competitive standing.",
                        missing_evidence_types=["project", "certification"],
                    )
                )

        # 3. Transferable Evidence Discovery
        transferable_evidence: list[TransferableEvidenceItem] = []
        evidence_items = state.evidence_corpus

        for gap in skill_gaps:
            canonical_gap = gap.canonical
            if canonical_gap in TRANSFERABLE_SKILL_MAP:
                for related_skill, rationale, conf in TRANSFERABLE_SKILL_MAP[canonical_gap]:
                    # Search if related skill exists in evidence items
                    for ev in evidence_items:
                        ev_text = str(_get_item_attr(ev, "text", "")).lower()
                        if related_skill in ev_text:
                            ev_id = _get_item_attr(ev, "id", None)
                            ev_loc = _get_item_attr(ev, "source_location", _get_item_attr(ev, "location", None))
                            transferable_evidence.append(
                                TransferableEvidenceItem(
                                    target_skill=gap.skill_name,
                                    related_found_skill=related_skill.title(),
                                    rationale=rationale,
                                    evidence_id=ev_id,
                                    source_location=ev_loc,
                                    transferability_confidence=conf,
                                )
                            )
                            break

        # 4. Seniority Alignment Score
        job_years = job.years_of_experience if job else 0

        # Estimate resume years from raw text and grounded contexts
        resume_years = 0
        years_matches = re.findall(r"\b(\d+)\s*\+?\s*years?\b", raw_resume_text)
        if years_matches:
            resume_years = max(int(y) for y in years_matches)
        for ctx in contexts:
            if ctx.requirement_category == "years_experience" and ctx.support_status == "SUPPORTED":
                resume_years = max(resume_years, 5)

        seniority_gap = None
        if job_years and resume_years < job_years:
            seniority_gap = f"Target role requests {job_years}+ years; resume demonstrates approx {resume_years} years."
            seniority_score = max(0.4, resume_years / job_years)
        else:
            seniority_score = 0.95

        # 5. Experience Relevance & Semantic Skill Score from Grounded RAG Contexts
        supported_count = sum(1 for c in contexts if c.support_status == "SUPPORTED")
        partially_count = sum(1 for c in contexts if c.support_status == "PARTIALLY_SUPPORTED")

        exp_relevance = (
            (supported_count * 1.0 + partially_count * 0.5) / len(contexts)
            if contexts
            else 0.85
        )
        exp_relevance_score = round(min(1.0, max(0.0, exp_relevance)), 4)

        semantic_skill_score = round(
            0.40 * (mand_cov_pct / 100.0)
            + 0.25 * (pref_cov_pct / 100.0)
            + 0.20 * exp_relevance_score
            + 0.15 * seniority_score,
            4,
        )

        # 6. Generate Recommendations referencing Evidence IDs
        recommendations: list[AgentRecommendation] = []

        for trans in transferable_evidence[:3]:
            recommendations.append(
                AgentRecommendation(
                    agent_name="skill_agent",
                    category="transferable_skill",
                    title=f"Leverage Transferable {trans.related_found_skill} Experience for {trans.target_skill}",
                    description=trans.rationale,
                    priority="high",
                    evidence_ids=[trans.evidence_id] if trans.evidence_id else [],
                    source_location=trans.source_location,
                    suggested_action=f"Highlight architecture similarities between {trans.related_found_skill} and {trans.target_skill} in experience descriptions.",
                )
            )

        for gap in skill_gaps[:2]:
            if not any(t.target_skill == gap.skill_name for t in transferable_evidence):
                recommendations.append(
                    AgentRecommendation(
                        agent_name="skill_agent",
                        category="skill_gap",
                        title=f"Address Missing Skill: {gap.skill_name}",
                        description=f"{gap.skill_name} is a {gap.kind} requirement. Consider adding side projects or coursework evidence.",
                        priority="high" if gap.kind == "mandatory" else "medium",
                        suggested_action=f"Provide verified repository or portfolio evidence demonstrating hands-on work with {gap.skill_name}.",
                    )
                )

        return SkillAgentOutput(
            semantic_skill_score=semantic_skill_score,
            mandatory_skill_coverage_percent=round(mand_cov_pct, 2),
            preferred_skill_coverage_percent=round(pref_cov_pct, 2),
            matched_mandatory_skills=matched_mandatory,
            missing_mandatory_skills=missing_mandatory,
            matched_preferred_skills=matched_preferred,
            missing_preferred_skills=missing_preferred,
            skill_gaps=skill_gaps,
            transferable_evidence=transferable_evidence,
            seniority_alignment_score=round(seniority_score, 4),
            seniority_gap=seniority_gap,
            experience_relevance_score=exp_relevance_score,
            recommendations=recommendations,
        )


def skill_agent_node(state: AnalysisState) -> AnalysisState:
    """LangGraph node execution wrapper for Skill Agent."""
    agent = SkillAgent()
    output = agent.analyze(state)
    state.skill_output = output
    state.agent_runs_log.append({
        "agent": "skill_agent",
        "status": "completed",
        "semantic_skill_score": output.semantic_skill_score,
        "recommendations_count": len(output.recommendations),
    })
    return state
