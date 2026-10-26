import re
from collections import defaultdict

from app.parsing.models import ContactInformation, ExtractedItem, ResumeExtraction, ResumeLayoutDiagnostics

SECTION_ALIASES = {
    "summary": {
        "summary", "profile", "professional summary", "objective", "career summary",
        "executive summary", "about me", "professional profile", "summary of qualifications",
        "career objective", "personal statement"
    },
    "skills": {
        "skills", "technical skills", "core competencies", "technologies", "key skills",
        "technical proficiencies", "technical stack", "tools and technologies", "competencies",
        "areas of expertise", "skills & abilities", "tech stack"
    },
    "experience": {
        "experience", "work experience", "professional experience", "employment",
        "work history", "employment history", "professional background", "relevant experience",
        "career history", "internships", "practical experience"
    },
    "projects": {
        "projects", "selected projects", "project experience", "technical projects",
        "academic projects", "key projects", "notable projects", "open source projects",
        "personal projects"
    },
    "education": {
        "education", "academic background", "academic credentials", "degrees",
        "education and training", "academic history", "qualifications"
    },
    "certifications": {
        "certifications", "certificates", "licenses", "professional certifications",
        "licenses and certifications", "credentials"
    },
    "achievements": {
        "achievements", "awards", "honors", "key achievements", "awards & honors",
        "accomplishments"
    },
    "publications": {"publications", "papers", "research", "patents"},
    "links": {"links", "profiles", "online", "portfolio", "social"},
}

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\w)|(?<!\w)(?:\+?\d[\d ()().-]{7,}\d)(?!\w)")
URL_RE = re.compile(r"https?://[^\s)>]+", re.IGNORECASE)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+", re.IGNORECASE)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+", re.IGNORECASE)
LOCATION_RE = re.compile(r"\b([A-Z][a-zA-Z\s]+,\s*[A-Z]{2}\b|\b[A-Z][a-zA-Z\s]+,\s*(?:United States|USA|Canada|UK|India|Germany|Australia))\b")


def parse_resume(
    text: str,
    source: str,
    diagnostics: ResumeLayoutDiagnostics | None = None,
) -> ResumeExtraction:
    lines = [line.strip() for line in text.splitlines()]
    lines_with_numbers = [(index + 1, line) for index, line in enumerate(lines) if line]
    sections: dict[str, list[ExtractedItem]] = defaultdict(list)
    current_section = "header"
    first_content: list[str] = []

    for number, line in lines_with_numbers:
        section_name = _section_name(line)
        if section_name:
            current_section = section_name
            continue
        if current_section == "header" and len(first_content) < 3:
            first_content.append(line)
            continue
        item_type = _item_type(current_section)
        if item_type:
            sections[current_section].append(
                ExtractedItem(
                    type=item_type,
                    text=line.lstrip("-•*▪▫◦►–— "),
                    source=source,
                    location=f"{current_section.title()} > line {number}",
                    confidence=0.95,
                )
            )

    contact = _contact_information(text)
    name = _find_name(first_content, contact)
    summary = " ".join(item.text for item in sections.get("summary", [])) or None
    items = [item for values in sections.values() for item in values]

    if name:
        items.append(ExtractedItem(type="person", text=name, source=source, location="Header > line 1", confidence=0.85))
    for value in contact.links:
        items.append(ExtractedItem(type="link", text=value, source=source, location="Contact information", confidence=0.99))

    layout_diag = diagnostics or ResumeLayoutDiagnostics()

    return ResumeExtraction(
        source=source,
        name=name,
        contact_information=contact,
        summary=summary,
        sections=dict(sections),
        items=items,
        raw_text=text,
        layout_diagnostics=layout_diag,
    )


def _section_name(line: str) -> str | None:
    # Remove colons, dashes, and special formatting
    normalized = re.sub(r"[^a-z\s]", "", line.lower()).strip()
    if not normalized or len(normalized) > 50:
        return None
    for section, aliases in SECTION_ALIASES.items():
        if normalized in aliases:
            return section
    return None


def _item_type(section: str) -> str | None:
    return {
        "summary": "summary",
        "skills": "skill",
        "experience": "experience",
        "projects": "project",
        "education": "education",
        "certifications": "certification",
        "achievements": "achievement",
        "publications": "publication",
        "links": "link",
    }.get(section)


def _contact_information(text: str) -> ContactInformation:
    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)
    location_match = LOCATION_RE.search(text)

    # Classify all URLs
    raw_links = list(dict.fromkeys(URL_RE.findall(text)))
    
    # Also find handles if not formatted with http
    linkedin_match = LINKEDIN_RE.search(text)
    github_match = GITHUB_RE.search(text)
    if linkedin_match and not any("linkedin.com" in l.lower() for l in raw_links):
        raw_links.append(f"https://{linkedin_match.group(0).lstrip('http://').lstrip('https://')}")
    if github_match and not any("github.com" in l.lower() for l in raw_links):
        raw_links.append(f"https://{github_match.group(0).lstrip('http://').lstrip('https://')}")

    return ContactInformation(
        email=email_match.group(0) if email_match else None,
        phone=phone_match.group(0) if phone_match else None,
        location=location_match.group(0) if location_match else None,
        links=raw_links,
    )


def _find_name(first_content: list[str], contact: ContactInformation) -> str | None:
    for line in first_content:
        if contact.email and contact.email in line:
            continue
        if contact.phone and contact.phone in line:
            continue
        if URL_RE.search(line):
            continue
        cleaned = re.sub(r"[^a-zA-Z\s.-]", "", line).strip()
        words = cleaned.split()
        if 2 <= len(words) <= 5 and not any(w.lower() in {"resume", "curriculum", "vitae", "cv"} for w in words):
            return cleaned
    return None

