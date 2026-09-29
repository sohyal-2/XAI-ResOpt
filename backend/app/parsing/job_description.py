"""Job Description Intelligence Subsystem.

Extracts structured job requirements:
- Mandatory skills
- Preferred skills
- Nice-to-have skills
- Years of experience
- Responsibilities
- Education
- Certifications
- Domain knowledge
- Tooling
- Soft skills
- Keywords
- Implied requirements
- Seniority indicators

Classifies requirements as: mandatory, preferred, nice_to_have, contextual.
Normalizes skills & keywords while preserving original terminology and synonym groups.
"""

from __future__ import annotations

import re
from collections import OrderedDict

from app.parsing.models import (
    JobDescriptionExtraction,
    JobRequirementExtraction,
    NormalizedTerm,
    RequirementCategory,
)
from app.parsing.taxonomy import (
    TECH_TAXONOMY,
)

HEADING_RULES: list[tuple[set[str], str, RequirementCategory | None]] = [
    (
        {
            "requirements",
            "required qualifications",
            "minimum qualifications",
            "basic qualifications",
            "must have",
            "mandatory requirements",
            "essential requirements",
            "what you need",
            "what you bring",
            "what youll bring",
            "what you will bring",
            "qualifications",
        },
        "mandatory",
        None,
    ),
    (
        {
            "preferred qualifications",
            "preferred requirements",
            "preferred skills",
            "desired qualifications",
            "desired skills",
            "bonus qualifications",
            "bonus points",
            "what gives you an edge",
            "additional qualifications",
            "preferred",
            "bonus",
        },
        "preferred",
        None,
    ),
    (
        {
            "nice to have",
            "nice to have skills",
            "nice to have",
            "optional qualifications",
            "optional skills",
            "great to have",
            "good to have",
        },
        "nice_to_have",
        None,
    ),
    (
        {
            "responsibilities",
            "what you will do",
            "what you ll do",
            "what youll do",
            "role responsibilities",
            "key responsibilities",
            "duties",
            "key duties",
            "the role",
            "about the role",
            "day to day",
        },
        "contextual",
        RequirementCategory.responsibility,
    ),
    (
        {
            "education",
            "educational requirements",
            "academic requirements",
            "degrees",
            "education requirements",
        },
        "mandatory",
        RequirementCategory.education,
    ),
    (
        {
            "certifications",
            "certificates",
            "licenses",
            "certifications and licenses",
            "credentials",
        },
        "preferred",
        RequirementCategory.certification,
    ),
    (
        {
            "tools",
            "tooling",
            "technology",
            "technologies",
            "tech stack",
            "technology stack",
            "tools technologies",
            "tools and technologies",
            "tooling technologies",
            "tooling and technologies",
        },
        "contextual",
        RequirementCategory.tooling,
    ),
    (
        {
            "soft skills",
            "professional skills",
            "interpersonal skills",
            "core competencies",
            "behavioral competencies",
        },
        "preferred",
        RequirementCategory.soft_skill,
    ),
    (
        {
            "domain knowledge",
            "industry knowledge",
            "industry experience",
            "domain expertise",
        },
        "preferred",
        RequirementCategory.domain_knowledge,
    ),
    (
        {
            "keywords",
            "key words",
            "tags",
            "skill tags",
        },
        "contextual",
        RequirementCategory.keyword,
    ),
    (
        {
            "implied requirements",
            "other requirements",
            "additional requirements",
        },
        "contextual",
        RequirementCategory.implied_requirement,
    ),
]

YEARS_RE = re.compile(
    r"\b(?:(?:minimum|at\s+least)\s+)?(\d+)(?:\s*(?:-|to|\+)\s*(\d+))?\s*\+?\s*years?(?:\s+of)?(?:\s+(?:professional|relevant|software|hands-on|industry)?\s+experience)?\b",
    re.IGNORECASE,
)
SENIORITY_RE = re.compile(
    r"\b(intern|internship|entry[- ]level|associate|junior|mid[- ]level|senior|staff|principal|lead|architect|manager|director|vp|vice[- ]president|head\s+of)\b",
    re.IGNORECASE,
)
EDUCATION_RE = re.compile(
    r"\b(bachelor'?s?|master'?s?|ph\.?d\.?|doctorate|associate'?s?|b\.?s\.?|m\.?s\.?|b\.?a\.?|degree\s+in|computer\s+science|software\s+engineering|information\s+technology|stem|electrical\s+engineering)\b",
    re.IGNORECASE,
)
CERTIFICATION_RE = re.compile(
    r"\b(certif\w*|license|licensed|credential|cka|ckad|pmp|cissp|csm|scrum\s+master|aws\s+certified|google\s+cloud\s+certified|microsoft\s+certified)\b",
    re.IGNORECASE,
)
RESPONSIBILITY_VERBS_RE = re.compile(
    r"\b(build|design|develop|architect|maintain|scale|optimize|lead|deliver|implement|collaborate|participate|oversee|drive|mentor|create|manage|deploy|ensure|troubleshoot|review|coordinate)\b",
    re.IGNORECASE,
)
IMPLIED_RE = re.compile(
    r"\b(familiarity\s+with|exposure\s+to|understanding\s+of|knowledge\s+of|working\s+knowledge|demonstrated\s+ability|ability\s+to\s+learn|passion\s+for|willingness\s+to|thrive\s+in)\b",
    re.IGNORECASE,
)
SOFT_SKILL_RE = re.compile(
    r"\b(communication|collaboration|collaborat\w*|leadership|mentoring|mentorship|teamwork|problem[- ]solving|critical\s+thinking|interpersonal|adaptability|ownership|self[- ]starter)\b",
    re.IGNORECASE,
)
DOMAIN_RE = re.compile(
    r"\b(fintech|healthcare|healthtech|ecommerce|e-commerce|saas|adtech|edtech|banking|payments|cybersecurity|infosec|telecom|gaming|supply\s+chain|insurtech|blockchain|web3)\b",
    re.IGNORECASE,
)


def parse_job_description(text: str, source: str) -> JobDescriptionExtraction:
    """Parse raw job description text into structured, categorized, normalized requirements."""
    raw_lines = text.splitlines()
    lines: list[tuple[int, str]] = [
        (index + 1, line.strip(" -•*#\t"))
        for index, line in enumerate(raw_lines)
        if line.strip(" -•*#\t")
    ]

    title = _extract_title([line for _, line in lines])
    seniority_indicators = _extract_seniority(text)

    requirements: list[JobRequirementExtraction] = []
    active_kind: str = "contextual"
    active_category: RequirementCategory | None = None

    overall_years: int | None = None

    for line_number, line in lines:
        heading = _heading_rule(line)
        if heading:
            active_kind, active_category = heading
            continue

        # Skip if the line is solely the title header
        if line == title and line_number <= 3:
            continue

        terms = _extract_terms(line)
        years_match = YEARS_RE.search(line)
        years_val = int(years_match.group(1)) if years_match else None

        if years_val and overall_years is None:
            overall_years = years_val

        category = _classify_category(line, active_category, terms, years_match)
        kind = _classify_kind(line, active_kind)

        # Filter out short noise lines without terms or context
        if len(line) < 4 and not terms and not years_match and not active_category:
            continue

        if not (
            terms
            or years_match
            or active_category
            or category
            in {
                RequirementCategory.education,
                RequirementCategory.certification,
                RequirementCategory.responsibility,
                RequirementCategory.implied_requirement,
                RequirementCategory.soft_skill,
                RequirementCategory.domain_knowledge,
                RequirementCategory.tooling,
            }
        ):
            continue

        # Calculate confidence based on extraction fidelity
        confidence = 0.95 if (terms and years_match) else (0.90 if terms or years_match else 0.85)

        location_name = category.value.replace("_", " ").title()
        source_location = f"{location_name} > line {line_number}"

        req = JobRequirementExtraction(
            text=line,
            kind=kind,
            category=category,
            source_location=source_location,
            original_terms=[t.original for t in terms],
            normalized_terms=[t.canonical for t in terms],
            terms=terms,
            years_experience=years_val,
            confidence=confidence,
        )
        requirements.append(req)

    # Aggregate categorized views
    all_keywords = _unique_terms(requirements)

    mandatory_skills: OrderedDict[str, NormalizedTerm] = OrderedDict()
    preferred_skills: OrderedDict[str, NormalizedTerm] = OrderedDict()
    nice_to_have_skills: OrderedDict[str, NormalizedTerm] = OrderedDict()
    tooling_skills: OrderedDict[str, NormalizedTerm] = OrderedDict()

    responsibilities: list[str] = []
    education_reqs: list[str] = []
    certifications: list[str] = []
    domain_knowledge: list[str] = []
    soft_skills: list[str] = []
    implied_requirements: list[str] = []

    for req in requirements:
        if req.category == RequirementCategory.responsibility:
            responsibilities.append(req.text)
        elif req.category == RequirementCategory.education:
            education_reqs.append(req.text)
        elif req.category == RequirementCategory.certification:
            certifications.append(req.text)
        elif req.category == RequirementCategory.domain_knowledge:
            domain_knowledge.append(req.text)
        elif req.category == RequirementCategory.soft_skill:
            soft_skills.append(req.text)
        elif req.category == RequirementCategory.implied_requirement:
            implied_requirements.append(req.text)
        elif req.category == RequirementCategory.tooling:
            for term in req.terms:
                tooling_skills.setdefault(term.canonical, term)

        # Classify skill terms by requirement kind
        for term in req.terms:
            if req.kind == "mandatory":
                mandatory_skills.setdefault(term.canonical, term)
            elif req.kind == "preferred":
                preferred_skills.setdefault(term.canonical, term)
            elif req.kind == "nice_to_have":
                nice_to_have_skills.setdefault(term.canonical, term)

    return JobDescriptionExtraction(
        source=source,
        title=title,
        seniority_indicators=seniority_indicators,
        years_of_experience=overall_years,
        mandatory_skills=list(mandatory_skills.values()),
        preferred_skills=list(preferred_skills.values()),
        nice_to_have_skills=list(nice_to_have_skills.values()),
        responsibilities=responsibilities,
        education_requirements=education_reqs,
        certifications=certifications,
        domain_knowledge=domain_knowledge,
        tooling=list(tooling_skills.values()),
        soft_skills=soft_skills,
        keywords=all_keywords,
        implied_requirements=implied_requirements,
        raw_text=text,
        requirements=requirements,
    )


def _heading_rule(line: str) -> tuple[str, RequirementCategory | None] | None:
    cleaned = re.sub(r"[^a-z0-9 ]", " ", line.lower())
    normalized = re.sub(r"\s+", " ", cleaned).strip()

    # Check both full line and sub-parts split by delimiters
    parts = [normalized] + [
        re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", p.lower())).strip()
        for p in re.split(r"[/|&–—\-:]+", line)
        if p.strip()
    ]

    for part in parts:
        for aliases, kind, category in HEADING_RULES:
            if part in aliases:
                return kind, category
    return None


def _extract_title(lines: list[str]) -> str | None:
    for line in lines[:5]:
        if re.search(
            r"\b(engineer|developer|designer|manager|analyst|scientist|specialist|intern|architect|consultant|lead|administrator)\b",
            line,
            re.IGNORECASE,
        ):
            return line
    return lines[0] if lines else None


def _extract_seniority(text: str) -> list[str]:
    matches: OrderedDict[str, str] = OrderedDict()
    for match in SENIORITY_RE.finditer(text):
        word = match.group(0).strip().title()
        matches.setdefault(word.casefold(), word)
    return list(matches.values())


def _extract_terms(line: str) -> list[NormalizedTerm]:
    candidates: list[tuple[int, int, NormalizedTerm]] = []

    for entry in TECH_TAXONOMY:
        pattern = rf"(?<![\w+#])(?:{entry.pattern})(?![\w+#])"
        for match in re.finditer(pattern, line, re.IGNORECASE):
            candidates.append(
                (
                    match.start(),
                    match.end(),
                    NormalizedTerm(
                        original=match.group(0),
                        canonical=entry.canonical,
                        synonyms=list(entry.synonyms),
                    ),
                )
            )

    # Sort candidates by longest span first, then earlier index
    candidates.sort(key=lambda c: (-(c[1] - c[0]), c[0]))

    selected: list[tuple[int, int, NormalizedTerm]] = []
    for start, end, term in candidates:
        if not any(max(start, s) < min(end, e) for s, e, _ in selected):
            selected.append((start, end, term))

    selected.sort(key=lambda c: c[0])
    return [term for _, _, term in selected]


def _classify_category(
    line: str,
    active_category: RequirementCategory | None,
    terms: list[NormalizedTerm],
    years_match: re.Match | None,
) -> RequirementCategory:
    lowered = line.lower()

    if years_match and (
        "year" in lowered and ("experience" in lowered or "background" in lowered or not active_category)
    ):
        return RequirementCategory.years_experience

    if active_category is not None:
        return active_category

    if EDUCATION_RE.search(line):
        return RequirementCategory.education

    if CERTIFICATION_RE.search(line):
        return RequirementCategory.certification

    if RESPONSIBILITY_VERBS_RE.search(line) and re.match(
        r"^(build|design|develop|architect|maintain|scale|lead|deliver|implement|collaborate|mentor|oversee|ensure|troubleshoot)\b",
        lowered.strip(),
    ):
        return RequirementCategory.responsibility

    if terms:
        # Check taxonomy category for the matched term
        first_term = terms[0]
        for entry in TECH_TAXONOMY:
            if entry.canonical == first_term.canonical:
                if entry.category == "tooling":
                    return RequirementCategory.tooling
                if entry.category == "domain_knowledge":
                    return RequirementCategory.domain_knowledge
                if entry.category == "soft_skill":
                    return RequirementCategory.soft_skill
                if entry.category == "certification":
                    return RequirementCategory.certification
                if entry.category == "keyword":
                    return RequirementCategory.keyword
                return RequirementCategory.skill
        return RequirementCategory.skill

    if SOFT_SKILL_RE.search(line):
        return RequirementCategory.soft_skill

    if DOMAIN_RE.search(line):
        return RequirementCategory.domain_knowledge

    if IMPLIED_RE.search(line):
        return RequirementCategory.implied_requirement

    return RequirementCategory.keyword


def _classify_kind(line: str, active_kind: str) -> str:
    lowered = line.lower()
    if re.search(
        r"\b(required|must\s+have|must\s+be|mandatory|essential|minimum(?:\s+of)?|at\s+least|is\s+a\s+must)\b",
        lowered,
    ):
        return "mandatory"
    if re.search(
        r"\b(preferred|preference(?:\s+for)?|plus|advantageous|advantage|desired|desirable|a\s+plus)\b",
        lowered,
    ):
        return "preferred"
    if re.search(
        r"\b(nice[- ]to[- ]have|bonus|optional|great\s+to\s+have|good\s+to\s+have)\b",
        lowered,
    ):
        return "nice_to_have"
    return active_kind


def _unique_terms(requirements: list[JobRequirementExtraction]) -> list[NormalizedTerm]:
    result: OrderedDict[str, NormalizedTerm] = OrderedDict()
    for requirement in requirements:
        for term in requirement.terms:
            result.setdefault(term.canonical, term)
    return list(result.values())
