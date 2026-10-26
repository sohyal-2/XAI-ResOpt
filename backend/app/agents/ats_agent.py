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
        diag = getattr(resume, "layout_diagnostics", None)

        # ---------------------------------------------------------------------
        # 1. Keyword coverage & Exact terminology (Job Description Matching)
        # ---------------------------------------------------------------------
        job_keywords = job.keywords if job else []
        matched_keywords: list[str] = []
        missing_keywords: list[str] = []
        exact_matches: list[str] = []
        synonym_matches: list[str] = []

        for kw in job_keywords:
            original = kw.original.lower()
            canonical = kw.canonical.lower()
            synonyms = [s.lower() for s in getattr(kw, "synonyms", [])]

            if re.search(rf"\b{re.escape(original)}\b", lowered_resume):
                matched_keywords.append(kw.original)
                exact_matches.append(kw.original)
            elif any(re.search(rf"\b{re.escape(syn)}\b", lowered_resume) for syn in [canonical] + synonyms):
                matched_keywords.append(kw.original)
                synonym_matches.append(kw.original)
            else:
                missing_keywords.append(kw.original)

        has_jd = bool(job_keywords)
        keyword_coverage = (
            (len(matched_keywords) / len(job_keywords)) * 100.0 if has_jd else 100.0
        )

        # ---------------------------------------------------------------------
        # 2. Section presence & Section naming (Resume Structure)
        # ---------------------------------------------------------------------
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

        # ---------------------------------------------------------------------
        # 3. Formatting & ATS Layout Risk Analysis (ATS Readability)
        # ---------------------------------------------------------------------
        formatting_risks: list[FormattingRisk] = []
        lines = [line.strip() for line in raw_resume_text.splitlines() if line.strip()]

        # Layout diagnostics from PDF/DOCX parser
        if diag:
            if getattr(diag, "has_multi_column", False):
                formatting_risks.append(
                    FormattingRisk(
                        risk_type="multi_column_layout",
                        description="Multi-column layout detected. ATS parsers typically parse text left-to-right across columns, jumbling contact info, dates, and titles.",
                        severity="high",
                        location="Document Layout",
                    )
                )
            if getattr(diag, "has_tables", False):
                formatting_risks.append(
                    FormattingRisk(
                        risk_type="complex_tables",
                        description=f"Document contains {getattr(diag, 'table_count', 1)} table(s). Standard ATS parsers frequently drop table cells or headers.",
                        severity="medium",
                        location="Document Tables",
                    )
                )
            if getattr(diag, "has_text_boxes", False):
                formatting_risks.append(
                    FormattingRisk(
                        risk_type="text_boxes",
                        description="Floating text boxes detected. Enterprise ATS systems (Workday, Taleo) often skip text box contents entirely.",
                        severity="high",
                        location="Document Text Boxes",
                    )
                )

        # Check for excessive line lengths
        long_lines = [line for line in lines if len(line) > 220]
        if long_lines:
            formatting_risks.append(
                FormattingRisk(
                    risk_type="excessive_line_length",
                    description=f"{len(long_lines)} lines exceed 220 characters without breaks, risking text truncation in legacy parsers.",
                    severity="low",
                    location=long_lines[0][:60] + "...",
                )
            )

        # Check for non-standard decorative characters or weird tables
        weird_chars = re.findall(r"[^\x00-\x7F\u2022\u2013\u2014\u00A0]", raw_resume_text)
        if len(weird_chars) > 20:
            formatting_risks.append(
                FormattingRisk(
                    risk_type="non_standard_encoding",
                    description=f"Detected {len(weird_chars)} non-standard or decorative characters that risk parser corruption.",
                    severity="medium",
                )
            )

        formatting_risk_score = round(max(0.2, 1.0 - (len(formatting_risks) * 0.15)), 4)

        # ---------------------------------------------------------------------
        # 4. Contact Information Completeness & Link Integrity
        # ---------------------------------------------------------------------
        contact = resume.contact_information if resume else None
        links = getattr(contact, "links", []) or []
        has_linkedin = any("linkedin.com" in l.lower() for l in links)
        has_github = any("github.com" in l.lower() for l in links)

        contact_completeness = {
            "email": bool(contact and contact.email),
            "phone": bool(contact and contact.phone),
            "location": bool(contact and getattr(contact, "location", None)),
            "links": bool(links),
            "linkedin": has_linkedin,
            "github": has_github,
        }

        contact_score = round(
            (0.40 if contact_completeness["email"] else 0.0)
            + (0.30 if contact_completeness["phone"] else 0.0)
            + (0.15 if contact_completeness["location"] else 0.05)
            + (0.15 if has_linkedin or has_github else 0.05),
            4,
        )

        # ---------------------------------------------------------------------
        # 5. Content Quality: Action Verbs, Measurable Outcomes, & Repetition
        # ---------------------------------------------------------------------
        bullet_items = [
            item.text
            for items in (resume.sections.values() if resume else [])
            for item in items
            if len(item.text.strip()) > 15
        ]

        # Strong action verbs
        strong_verbs_regex = r"\b(built|architected|developed|engineered|led|designed|implemented|optimized|scaled|managed|created|delivered|reduced|increased|spearheaded|streamlined|orchestrated|accelerated|automated|formulated)\b"
        action_verbs_matches = re.findall(strong_verbs_regex, lowered_resume)
        action_verb_density = min(1.0, len(action_verbs_matches) / (len(bullet_items) or 1))

        # Weak / passive verbs
        weak_verbs_regex = r"\b(assisted|helped|worked on|responsible for|participated in|involved in|handled|duties included|tasked with)\b"
        weak_verbs_found = list(dict.fromkeys(re.findall(weak_verbs_regex, lowered_resume)))

        # Quantifiable outcomes (numbers, percentages, currency, metrics)
        metric_regex = r"(?:\b\d+(?:\.\d+)?%|\$\d+(?:,\d+)*(?:\.\d+)?[kmb]?|\b\d+x\b|\b\d{1,3}(?:,\d{3})+\b|\b\d+\+?\s*(?:users|clients|records|queries|requests|endpoints|services|models|pipelines|features|data points)\b)"
        quantified_bullets = [
            b for b in bullet_items if re.search(metric_regex, b, re.IGNORECASE)
        ]
        quantified_ratio = len(quantified_bullets) / (len(bullet_items) or 1)

        # Repetitive opening words
        opening_words: dict[str, int] = {}
        for b in bullet_items:
            first_word = b.split()[0].lower() if b.split() else ""
            if len(first_word) > 3:
                opening_words[first_word] = opening_words.get(first_word, 0) + 1
        repetitive_verbs = [w for w, c in opening_words.items() if c >= 3]

        content_quality_score = round(
            max(0.3, min(1.0, 0.40 * action_verb_density + 0.40 * quantified_ratio + (0.20 if not weak_verbs_found else 0.05))),
            4,
        )

        readability_score = round(min(1.0, max(0.4, 0.5 + 0.5 * action_verb_density)), 4)

        # ---------------------------------------------------------------------
        # 6. ATS Parsability Score & Structure Score
        # ---------------------------------------------------------------------
        has_essential_sections = section_presence.get("experience", False) and section_presence.get("skills", False)
        structure_score = round(
            (0.35 if has_essential_sections else 0.15)
            + (0.25 if section_presence.get("education", False) else 0.10)
            + (0.20 if section_presence.get("summary", False) else 0.05)
            + (0.20 if not naming_issues else 0.10),
            4,
        )

        parsability_score = round(
            (0.4 if has_essential_sections else 0.2)
            + (0.3 if contact_completeness["email"] else 0.0)
            + 0.3 * formatting_risk_score,
            4,
        )

        # ---------------------------------------------------------------------
        # 7. Keyword Distribution across sections
        # ---------------------------------------------------------------------
        keyword_distribution: dict[str, int] = {}
        for sec_name, items in (resume.sections.items() if resume else {}):
            sec_text = " ".join(item.text.lower() for item in items)
            count = sum(1 for kw in job_keywords if getattr(kw, "canonical", "").lower() in sec_text or kw.original.lower() in sec_text)
            keyword_distribution[sec_name] = count

        # ---------------------------------------------------------------------
        # 8. Requirement coverage from RAG Grounded Contexts
        # ---------------------------------------------------------------------
        supported_reqs = sum(1 for c in contexts if c.support_status != "UNSUPPORTED")
        req_coverage_percent = (
            (supported_reqs / len(contexts)) * 100.0 if contexts else 100.0
        )

        # ---------------------------------------------------------------------
        # 9. Prioritized Recommendations with Exact Snippets
        # ---------------------------------------------------------------------
        recommendations: list[AgentRecommendation] = []

        # Critical / High: Multi-column or Text Boxes
        if diag and getattr(diag, "has_multi_column", False):
            recommendations.append(
                AgentRecommendation(
                    agent_name="ats_agent",
                    category="readability",
                    title="Remove Multi-Column Layout for Single-Column Flow",
                    description="Your resume uses multiple columns. ATS engines parse text left-to-right across the page, causing job titles, dates, and bullet points to merge incoherently.",
                    priority="critical",
                    suggested_action="Convert your resume layout to a clean, single-column linear hierarchy.",
                )
            )

        if not contact_completeness["email"]:
            recommendations.append(
                AgentRecommendation(
                    agent_name="ats_agent",
                    category="contact_info",
                    title="Add Verifiable Contact Email Address",
                    description="No valid contact email was detected in the header. ATS parsers reject candidate profiles lacking primary contact coordinates.",
                    priority="critical",
                    suggested_action="Place a professional email address at the very top of your resume header.",
                )
            )

        if missing_keywords:
            top_missing = missing_keywords[:5]
            recommendations.append(
                AgentRecommendation(
                    agent_name="ats_agent",
                    category="keyword_coverage",
                    title="Incorporate Target Job Keywords",
                    description=f"Add missing core keywords ({', '.join(top_missing)}) to skills and project bullets where you possess verified experience.",
                    priority="high",
                    suggested_action=f"Include verified experience with {', '.join(top_missing)} in the Work Experience or Skills section.",
                )
            )

        if weak_verbs_found:
            sample_weak = ", ".join(f'"{v}"' for v in weak_verbs_found[:3])
            recommendations.append(
                AgentRecommendation(
                    agent_name="ats_agent",
                    category="content_quality",
                    title="Replace Passive & Weak Action Verbs",
                    description=f"Detected passive expressions ({sample_weak}) that weaken recruiter impact. ATS algorithms and recruiters favor strong leadership verbs.",
                    priority="high",
                    suggested_action="Replace passive verbs with high-impact verbs such as 'Architected', 'Engineered', 'Optimized', or 'Spearheaded'.",
                )
            )

        if quantified_ratio < 0.35:
            recommendations.append(
                AgentRecommendation(
                    agent_name="ats_agent",
                    category="content_quality",
                    title="Add Quantifiable Metrics & Business Impact",
                    description=f"Only {int(quantified_ratio * 100)}% of your bullet points contain measurable metrics (numbers, %, $, scale). High-scoring ATS resumes demonstrate concrete outcomes.",
                    priority="high",
                    suggested_action="Apply the Google X-Y-Z formula ('Accomplished [X], measured by [Y], by doing [Z]') to add real scale and results.",
                )
            )

        if not section_presence.get("summary", False):
            recommendations.append(
                AgentRecommendation(
                    agent_name="ats_agent",
                    category="structure",
                    title="Add Professional Summary Section",
                    description="A structured professional summary elevates ATS keyword density and frames your core capability in the top third of the page.",
                    priority="recommended",
                    suggested_action="Add a 2-3 sentence executive summary highlighting core technologies, years of experience, and key strengths.",
                )
            )

        if repetitive_verbs:
            rep_list = ", ".join(f'"{v.title()}"' for v in repetitive_verbs[:2])
            recommendations.append(
                AgentRecommendation(
                    agent_name="ats_agent",
                    category="content_quality",
                    title="Vary Repetitive Opening Verbs",
                    description=f"Multiple bullets repeatedly start with {rep_list}. Varying verbs demonstrates broader technical and leadership scope.",
                    priority="recommended",
                    suggested_action="Diversify opening verbs across technical implementation, architectural design, and optimization.",
                )
            )

        if not contact_completeness.get("linkedin", False):
            recommendations.append(
                AgentRecommendation(
                    agent_name="ats_agent",
                    category="contact_info",
                    title="Add LinkedIn Profile URL",
                    description="Recruiters and automated sourcing tools verify professional presence via LinkedIn profile links.",
                    priority="optional",
                    suggested_action="Add your customized LinkedIn vanity URL to the header contact line.",
                )
            )

        # ---------------------------------------------------------------------
        # 10. Enhancv-Inspired 5 Category Pillars Structure
        # ---------------------------------------------------------------------
        category_pillars = {
            "readability": {
                "name": "ATS Readability",
                "score": round(formatting_risk_score * 100, 1),
                "status": "pass" if formatting_risk_score >= 0.85 else ("warn" if formatting_risk_score >= 0.70 else "fail"),
                "description": "Document layout, font readability, single-column flow, and absence of parsing traps.",
                "issues_count": len(formatting_risks),
            },
            "structure": {
                "name": "Resume Structure",
                "score": round(structure_score * 100, 1),
                "status": "pass" if structure_score >= 0.85 else ("warn" if structure_score >= 0.70 else "fail"),
                "description": "Standard section naming, logical ordering, and essential structural completeness.",
                "issues_count": len(naming_issues) + (0 if section_presence.get("summary") else 1),
            },
            "content": {
                "name": "Content Quality",
                "score": round(content_quality_score * 100, 1),
                "status": "pass" if content_quality_score >= 0.80 else ("warn" if content_quality_score >= 0.65 else "fail"),
                "description": "Active action verbs, absence of repetition, and quantifiable business outcomes.",
                "issues_count": len(weak_verbs_found) + (1 if quantified_ratio < 0.35 else 0),
            },
            "contact": {
                "name": "Contact Information",
                "score": round(contact_score * 100, 1),
                "status": "pass" if contact_score >= 0.85 else ("warn" if contact_score >= 0.70 else "fail"),
                "description": "Verifiable email, phone number, location, and professional profiles.",
                "issues_count": (0 if contact_completeness["email"] else 1) + (0 if contact_completeness["phone"] else 1),
            },
            "skills": {
                "name": "Skills & Experience",
                "score": round(min(100.0, 75.0 + len(bullet_items) * 2.0), 1),
                "status": "pass" if len(bullet_items) >= 6 else "warn",
                "description": "Breadth of technical capabilities and evidence-backed bullet points.",
                "issues_count": 0 if len(bullet_items) >= 6 else 1,
            },
        }

        if has_jd:
            category_pillars["job_match"] = {
                "name": "Job Description Match",
                "score": round(keyword_coverage, 1),
                "status": "pass" if keyword_coverage >= 80 else ("warn" if keyword_coverage >= 60 else "fail"),
                "description": "Alignment with target role keywords, mandatory qualifications, and domain terminology.",
                "issues_count": len(missing_keywords),
            }

        # ---------------------------------------------------------------------
        # 11. Overall ATS Score Synthesis
        # ---------------------------------------------------------------------
        if has_jd:
            overall_ats_score = round(
                0.35 * (keyword_coverage / 100.0)
                + 0.25 * (req_coverage_percent / 100.0)
                + 0.15 * parsability_score
                + 0.15 * content_quality_score
                + 0.10 * formatting_risk_score,
                4,
            )
        else:
            # Standalone Resume Quality Mode (No JD provided)
            overall_ats_score = round(
                0.25 * formatting_risk_score
                + 0.20 * structure_score
                + 0.25 * content_quality_score
                + 0.15 * contact_score
                + 0.15 * min(1.0, 0.6 + len(bullet_items) * 0.04),
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
            content_quality_score=content_quality_score,
            structure_score=structure_score,
            weak_verbs_found=weak_verbs_found,
            quantified_bullets_ratio=round(quantified_ratio, 2),
            category_pillars=category_pillars,
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
