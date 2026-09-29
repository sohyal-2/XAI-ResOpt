"""Structured builder that deterministically parses resume text into a standard ATS document representation."""

from __future__ import annotations

import re
from uuid import UUID

from app.schemas.rendering import (
    DeterministicResumeDocument,
    ResumeContactBlock,
    ResumeItemBlock,
    ResumeRenderConfig,
    ResumeSectionBlock,
)

STANDARD_SECTION_MAP = {
    "summary": "Professional Summary",
    "professional summary": "Professional Summary",
    "profile": "Professional Summary",
    "experience": "Work Experience",
    "work experience": "Work Experience",
    "professional experience": "Work Experience",
    "employment": "Work Experience",
    "skills": "Technical Skills",
    "technical skills": "Technical Skills",
    "core competencies": "Technical Skills",
    "education": "Education",
    "academic background": "Education",
    "certifications": "Certifications",
    "licenses": "Certifications",
    "projects": "Projects",
    "key projects": "Projects",
}


def normalize_section_heading(raw_heading: str) -> tuple[str, str]:
    """Returns (section_key, standard_display_heading)."""
    cleaned = raw_heading.strip().lower()
    for key, display_name in STANDARD_SECTION_MAP.items():
        if key in cleaned:
            section_key = display_name.lower().replace(" ", "_")
            if "experience" in section_key:
                section_key = "experience"
            elif "skills" in section_key:
                section_key = "skills"
            elif "summary" in section_key:
                section_key = "summary"
            elif "education" in section_key:
                section_key = "education"
            elif "certification" in section_key:
                section_key = "certifications"
            elif "project" in section_key:
                section_key = "projects"
            return section_key, display_name
    # Fallback to Title Cased
    clean_title = raw_heading.strip().title()
    return clean_title.lower().replace(" ", "_"), clean_title


def extract_contact_block(lines: list[str]) -> tuple[ResumeContactBlock, list[str]]:
    """Extracts candidate contact details from the top lines of the resume."""
    name = "Candidate Name"
    email = "candidate@example.com"
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None

    header_lines: list[str] = []
    body_lines: list[str] = []
    found_section_header = False

    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue
        # If line matches section heading pattern, stop header extraction
        if any(sec in line_clean.lower() for sec in STANDARD_SECTION_MAP) and len(line_clean.split()) <= 4:
            found_section_header = True
            body_lines = lines[idx:]
            break
        header_lines.append(line_clean)
        if len(header_lines) >= 5 and not found_section_header:
            body_lines = lines[idx + 1:]
            break

    if not body_lines and not found_section_header:
        body_lines = lines[len(header_lines):]

    if header_lines:
        name = header_lines[0].strip()

    header_text = " | ".join(header_lines)

    # Extract Email
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", header_text)
    if email_match:
        email = email_match.group(0)

    # Extract Phone
    phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", header_text)
    if phone_match:
        phone = phone_match.group(0)

    # Extract Links & Location
    for part in re.split(r"[|•]", header_text):
        p = part.strip()
        if not p:
            continue
        if "linkedin.com" in p.lower():
            linkedin = p
        elif "github.com" in p.lower():
            github = p
        elif ("http://" in p.lower() or "https://" in p.lower()) and "linkedin" not in p.lower() and "github" not in p.lower():
            portfolio = p
        elif not location and not email_match or (location is None and "@" not in p and not re.search(r"\d{3}", p) and "http" not in p and p != name):
            if len(p) > 2 and len(p.split()) <= 4 and not any(k in p.lower() for k in ["http", "github", "linkedin", "engineer", "developer"]):
                location = p

    return (
        ResumeContactBlock(
            name=name,
            email=email,
            phone=phone,
            location=location,
            linkedin=linkedin,
            github=github,
            portfolio=portfolio,
        ),
        body_lines,
    )


def build_deterministic_document(
    content_text: str,
    version_id: UUID | None = None,
    config: ResumeRenderConfig | None = None,
) -> DeterministicResumeDocument:
    """Deterministically transforms approved text into a structured, validated document model."""
    effective_config = config or ResumeRenderConfig()
    raw_lines = content_text.splitlines()

    contact_block, body_lines = extract_contact_block(raw_lines)

    # Parse sections and bullet items
    raw_sections: dict[str, ResumeSectionBlock] = {}
    current_key: str | None = None
    current_heading: str | None = None
    current_item: ResumeItemBlock | None = None

    for raw_line in body_lines:
        line = raw_line.strip()
        if not line:
            continue

        # Check if line is a section heading
        is_heading = False
        lower_line = line.lower()
        if len(line.split()) <= 4:
            for sec_term, disp_name in STANDARD_SECTION_MAP.items():
                if sec_term == lower_line or lower_line.startswith(sec_term + ":") or lower_line == sec_term:
                    is_heading = True
                    sec_key, std_heading = normalize_section_heading(line)
                    current_key = sec_key
                    current_heading = std_heading
                    if current_key not in raw_sections:
                        raw_sections[current_key] = ResumeSectionBlock(
                            section_key=current_key,
                            heading=current_heading,
                            items=[],
                        )
                    current_item = None
                    break

        if is_heading:
            continue

        if not current_key:
            # Lines before first explicit section -> default to summary
            current_key = "summary"
            current_heading = "Professional Summary"
            raw_sections[current_key] = ResumeSectionBlock(
                section_key=current_key,
                heading=current_heading,
                items=[],
            )

        # Parse line content (bullets, titles, or paragraphs)
        section_obj = raw_sections[current_key]

        # Bullet point
        if line.startswith(("-", "*", "•", "–")):
            bullet_clean = re.sub(r"^[-*•–]\s*", "", line).strip()
            if not current_item:
                current_item = ResumeItemBlock(bullets=[bullet_clean])
                section_obj.items.append(current_item)
            else:
                current_item.bullets.append(bullet_clean)
        else:
            # Non-bullet line: could be role/company header or paragraph text
            if current_key == "experience" and (" at " in line or " - " in line or "," in line) and len(line.split()) <= 10:
                current_item = ResumeItemBlock(title=line, bullets=[])
                section_obj.items.append(current_item)
            elif current_key == "skills":
                # Skills block
                current_item = ResumeItemBlock(raw_text=line)
                section_obj.items.append(current_item)
            elif current_key == "summary":
                if not section_obj.items:
                    current_item = ResumeItemBlock(raw_text=line)
                    section_obj.items.append(current_item)
                else:
                    existing = section_obj.items[0].raw_text or ""
                    section_obj.items[0].raw_text = (existing + " " + line).strip()
            else:
                current_item = ResumeItemBlock(raw_text=line)
                section_obj.items.append(current_item)

    # Order sections according to config.section_order
    ordered_sections: list[ResumeSectionBlock] = []
    for key in effective_config.section_order:
        if key in raw_sections and raw_sections[key].items:
            ordered_sections.append(raw_sections[key])

    # Append any remaining non-empty sections not in standard order
    for key, sec in raw_sections.items():
        if key not in effective_config.section_order and sec.items:
            ordered_sections.append(sec)

    return DeterministicResumeDocument(
        resume_version_id=version_id,
        header=contact_block,
        sections=ordered_sections,
        config=effective_config,
    )
