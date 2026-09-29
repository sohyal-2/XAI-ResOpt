"""ATS Agent Analysis Node.

Analyzes:
- Keyword coverage
- Exact terminology
- Section presence
- Section naming
- Formatting risk
- Contact information
- Readability
- ATS parsability
- Keyword distribution
- Requirement coverage
"""

from __future__ import annotations

import re

from app.agents.models import (
    AgentRecommendation,
    AnalysisState,
    ATSAgentOutput,
    FormattingRisk,
    SectionNamingIssue,
)

STANDARD_SECTIONS = {
    "summary": ["summary", "professional summary", "about me", "profile"],
    "experience": ["experience", "work experience", "employment history", "professional experience"],
    "skills": ["skills", "technical skills", "core competencies", "technologies"],
    "education": ["education", "academic background", "degrees"],
    "projects": ["projects", "key projects", "personal projects"],
    "certifications": ["certifications", "certificates", "licenses"],
}


class ATSAgent:
    """Agent evaluating ATS compatibility, terminology, parsability, and formatting risk."""

    def analyze(self, state: AnalysisState) -> ATSAgentOutput:
        resume = state.resume_extraction
        job = state.job_extraction
        contexts = state.grounded_contexts

        raw_resume_text = resume.raw_text if resume else ""
        lowered_resume = raw_resume_text.lower()

        # 1. Keyword coverage & Exact terminology
        job_keywords = job.keywords if job else []
        matched_keywords: list[str] = []
        missing_keywords: list[str] = []
        exact_matches: list[str] = []
        synonym_matches: list[str] = []

        for kw in job_keywords:
            original = kw.original.lower()
            canonical = kw.canonical.lower()
            synonyms = [s.lower() for s in kw.synonyms]

            # Check exact match
            if re.search(rf"\b{re.escape(original)}\b", lowered_resume):
                matched_keywords.append(kw.original)
                exact_matches.append(kw.original)
            # Check canonical or synonyms match
            elif any(re.search(rf"\b{re.escape(syn)}\b", lowered_resume) for syn in [canonical] + synonyms):
                matched_keywords.append(kw.original)
                synonym_matches.append(kw.original)
            else:
                missing_keywords.append(kw.original)

        keyword_coverage = (
            (len(matched_keywords) / len(job_keywords)) * 100.0 if job_keywords else 100.0
        )

        # 2. Section presence & Section naming
        sections_found = resume.sections if resume else {}
        section_presence = {sec: (sec in sections_found) for sec in STANDARD_SECTIONS}

        naming_issues: list[SectionNamingIssue] = []
        for sec_name in sections_found.keys():
            matched_standard = False
            for std_key, aliases in STANDARD_SECTIONS.items():
                if sec_name.lower() in aliases:
                    matched_standard = True
                    break
            if not matched_standard:
                naming_issues.append(
                    SectionNamingIssue(
                        found_heading=sec_name,
                        recommended_heading=sec_name.title(),
                        standard_section="custom",
                        risk_level="medium",
                    )
                )

        # 3. Formatting risk analysis
        formatting_risks: list[FormattingRisk] = []
        lines = [line.strip() for line in raw_resume_text.splitlines() if line.strip()]

        # Check for excessive line lengths (hard to parse)
        long_lines = [line for line in lines if len(line) > 200]
        if long_lines:
            formatting_risks.append(
                FormattingRisk(
                    risk_type="excessive_line_length",
                    description=f"{len(long_lines)} lines exceed 200 characters, which may clip in legacy ATS parsers.",
                    severity="low",
                    location=long_lines[0][:50] + "...",
                )
            )

        # Check for non-standard decorative characters or weird tables
        weird_chars = re.findall(r"[^\x00-\x7F\u2022\u2013\u2014]", raw_resume_text)
        if len(weird_chars) > 20:
            formatting_risks.append(
                FormattingRisk(
                    risk_type="non_standard_encoding",
                    description=f"Detected {len(weird_chars)} non-ASCII or decorative characters that risk parser corruption.",
                    severity="medium",
                )
            )

        formatting_risk_score = round(max(0.0, 1.0 - (len(formatting_risks) * 0.15)), 4)

        # 4. Contact Information completeness
        contact = resume.contact_information if resume else None
        contact_completeness = {
            "email": bool(contact and contact.email),
            "phone": bool(contact and contact.phone),
            "location": bool(contact and contact.location),
            "links": bool(contact and len(contact.links) > 0),
        }

        # 5. Readability & Action Verb Analysis
        bullet_items = [
            item.text
            for items in (resume.sections.values() if resume else [])
            for item in items
        ]
        action_verbs = re.findall(
            r"\b(built|architected|developed|engineered|led|designed|implemented|optimized|scaled|managed|created|delivered|reduced|increased)\b",
            lowered_resume,
        )
        action_verb_density = min(1.0, len(action_verbs) / (len(bullet_items) or 1))
        readability_score = round(min(1.0, max(0.4, 0.5 + 0.5 * action_verb_density)), 4)

        # 6. ATS Parsability Score
        has_essential_sections = section_presence.get("experience", False) and section_presence.get("skills", False)
        parsability_score = round(
            (0.4 if has_essential_sections else 0.2)
            + (0.3 if contact_completeness["email"] else 0.0)
            + 0.3 * formatting_risk_score,
            4,
        )

        # 7. Keyword Distribution across sections
        keyword_distribution: dict[str, int] = {}
        for sec_name, items in (resume.sections.items() if resume else {}):
            sec_text = " ".join(item.text.lower() for item in items)
            count = sum(1 for kw in job_keywords if kw.canonical in sec_text or kw.original.lower() in sec_text)
            keyword_distribution[sec_name] = count

        # 8. Requirement coverage from RAG Grounded Contexts
        supported_reqs = sum(1 for c in contexts if c.support_status != "UNSUPPORTED")
        req_coverage_percent = (
            (supported_reqs / len(contexts)) * 100.0 if contexts else 100.0
        )

        # 9. Generate Actionable Recommendations with Evidence IDs
        recommendations: list[AgentRecommendation] = []

        if missing_keywords:
            top_missing = missing_keywords[:5]
            recommendations.append(
                AgentRecommendation(
                    agent_name="ats_agent",
                    category="keyword_coverage",
                    title="Incorporate Missing Core Keywords",
                    description=f"Add missing target terms ({', '.join(top_missing)}) to skills and work experience bullets.",
                    priority="high",
                    suggested_action=f"Include verified experience with {', '.join(top_missing)} in the Work Experience section.",
                )
            )

        if not section_presence.get("summary", False):
            recommendations.append(
                AgentRecommendation(
                    agent_name="ats_agent",
                    category="section_presence",
                    title="Add Professional Summary Section",
                    description="A structured professional summary enhances ATS keyword density and recruiter engagement.",
                    priority="medium",
                    suggested_action="Add a 3-sentence summary highlighting core technologies and senior impact.",
                )
            )

        if not contact_completeness.get("links", False):
            recommendations.append(
                AgentRecommendation(
                    agent_name="ats_agent",
                    category="contact_info",
                    title="Add GitHub / Portfolio Profile Links",
                    description="Technical roles benefit from direct links to GitHub repositories or public portfolio code.",
                    priority="medium",
                    suggested_action="Include GitHub or portfolio URL in the resume header.",
                )
            )

        # Overall ATS score synthesis
        overall_ats_score = round(
            0.35 * (keyword_coverage / 100.0)
            + 0.25 * (req_coverage_percent / 100.0)
            + 0.20 * parsability_score
            + 0.10 * readability_score
            + 0.10 * formatting_risk_score,
            4,
        )

        return ATSAgentOutput(
            overall_ats_score=overall_ats_score,
            keyword_coverage_percent=round(keyword_coverage, 2),
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            exact_matches=exact_matches,
            synonym_matches=synonym_matches,
            section_presence=section_presence,
            section_naming_issues=naming_issues,
            formatting_risks=formatting_risks,
            formatting_risk_score=formatting_risk_score,
            contact_info_completeness=contact_completeness,
            readability_score=readability_score,
            parsability_score=parsability_score,
            keyword_distribution=keyword_distribution,
            requirement_coverage_percent=round(req_coverage_percent, 2),
            recommendations=recommendations,
        )


def ats_agent_node(state: AnalysisState) -> AnalysisState:
    """LangGraph node execution wrapper for ATS Agent."""
    agent = ATSAgent()
    output = agent.analyze(state)
    state.ats_output = output
    state.agent_runs_log.append({
        "agent": "ats_agent",
        "status": "completed",
        "overall_score": output.overall_ats_score,
        "recommendations_count": len(output.recommendations),
    })
    return state
