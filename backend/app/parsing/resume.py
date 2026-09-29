import re
from collections import defaultdict

from app.parsing.models import ContactInformation, ExtractedItem, ResumeExtraction

SECTION_ALIASES = {
    "summary": {"summary", "profile", "professional summary", "objective"},
    "skills": {"skills", "technical skills", "core competencies", "technologies"},
    "experience": {"experience", "work experience", "professional experience", "employment"},
    "projects": {"projects", "selected projects", "project experience"},
    "education": {"education", "academic background"},
    "certifications": {"certifications", "certificates", "licenses"},
    "achievements": {"achievements", "awards", "honors"},
    "publications": {"publications", "papers"},
    "links": {"links", "profiles", "online"},
}
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d ()().-]{7,}\d)(?!\w)")
URL_RE = re.compile(r"https?://[^\s)>]+", re.IGNORECASE)


def parse_resume(text: str, source: str) -> ResumeExtraction:
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
        if current_section == "header" and len(first_content) < 2:
            first_content.append(line)
            continue
        item_type = _item_type(current_section)
        if item_type:
            sections[current_section].append(
                ExtractedItem(
                    type=item_type,
                    text=line.lstrip("-•* "),
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
    return ResumeExtraction(source=source, name=name, contact_information=contact, summary=summary, sections=dict(sections), items=items, raw_text=text)


def _section_name(line: str) -> str | None:
    normalized = re.sub(r"[^a-z ]", "", line.lower()).strip()
    for section, aliases in SECTION_ALIASES.items():
        if normalized in aliases:
            return section
    return None


def _item_type(section: str) -> str | None:
    return {"summary": "summary", "skills": "skill", "experience": "experience", "projects": "project", "education": "education", "certifications": "certification", "achievements": "achievement", "publications": "publication", "links": "link"}.get(section)


def _contact_information(text: str) -> ContactInformation:
    email = EMAIL_RE.search(text)
    phone = PHONE_RE.search(text)
    links = list(dict.fromkeys(URL_RE.findall(text)))
    return ContactInformation(email=email.group(0) if email else None, phone=phone.group(0) if phone else None, links=links)


def _find_name(first_content: list[str], contact: ContactInformation) -> str | None:
    for line in first_content:
        if contact.email and contact.email in line or contact.phone and contact.phone in line:
            continue
        if not URL_RE.search(line) and len(line.split()) <= 6:
            return line
    return None
