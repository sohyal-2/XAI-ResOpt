"""Pre-rendering validation layer ensuring zero defective or unapproved resumes are emitted."""

from __future__ import annotations

import re

from app.models.entities import ChangeDecision, ResumeChange
from app.schemas.rendering import DeterministicResumeDocument, ResumeValidationResult


def validate_resume_for_rendering(
    doc: DeterministicResumeDocument,
    rendered_text: str,
    changes: list[ResumeChange] | None = None,
) -> ResumeValidationResult:
    """Strictly validates all 5 pre-rendering safety invariants."""
    issues: list[str] = []
    warnings: list[str] = []
    checks_passed: dict[str, bool] = {
        "sections_present": True,
        "no_empty_sections": True,
        "contact_info_intact": True,
        "approved_changes_present": True,
        "rejected_changes_absent": True,
    }

    # 1. Verify sections are present
    if not doc.sections:
        issues.append("Zero sections found in structured resume representation.")
        checks_passed["sections_present"] = False

    # 2. Verify no accidental empty sections exist
    for sec in doc.sections:
        if not sec.items:
            issues.append(f"Section '{sec.heading}' ({sec.section_key}) has zero items.")
            checks_passed["no_empty_sections"] = False
        else:
            has_content = any(
                (item.raw_text and item.raw_text.strip()) or (item.bullets and len(item.bullets) > 0) or (item.title and item.title.strip())
                for item in sec.items
            )
            if not has_content:
                issues.append(f"Section '{sec.heading}' contains only empty placeholders.")
                checks_passed["no_empty_sections"] = False

    # 3. Verify contact information is intact
    if not doc.header.name or doc.header.name.strip() in ("", "Candidate Name", "Name"):
        issues.append("Candidate name is missing or placeholder.")
        checks_passed["contact_info_intact"] = False

    if not doc.header.email or not re.match(r"[^@]+@[^@]+\.[^@]+", doc.header.email.strip()):
        issues.append("Candidate email address is missing or malformed.")
        checks_passed["contact_info_intact"] = False

    if not doc.header.phone and not doc.header.location and not doc.header.linkedin and not doc.header.github:
        warnings.append("No secondary contact metadata (phone, location, or profile links) found.")

    # 4 & 5. Verify approved changes are present & rejected changes are absent
    if changes:
        clean_doc_text = rendered_text.lower()
        for ch in changes:
            # Approved / Edited modifications
            if ch.decision in (ChangeDecision.accepted, "accepted", ChangeDecision.edited, "edited"):
                expected_text = (ch.manual_text if ch.manual_text and ch.is_manual else ch.after_text).strip()
                if expected_text and expected_text.lower() not in clean_doc_text:
                    issues.append(
                        f"Approved change {ch.id} text was not found in final rendered resume text: '{expected_text[:40]}...'"
                    )
                    checks_passed["approved_changes_present"] = False

            # Rejected modifications
            elif ch.decision in (ChangeDecision.rejected, "rejected"):
                rejected_proposal = ch.after_text.strip()
                # Only check if rejected text is distinct from original text
                if rejected_proposal and rejected_proposal.lower() != ch.before_text.lower():
                    if rejected_proposal.lower() in clean_doc_text:
                        issues.append(
                            f"Rejected modification {ch.id} was unexpectedly present in final rendered resume: '{rejected_proposal[:40]}...'"
                        )
                        checks_passed["rejected_changes_absent"] = False

    is_valid = len(issues) == 0

    return ResumeValidationResult(
        is_valid=is_valid,
        issues=issues,
        warnings=warnings,
        checks_passed=checks_passed,
        details={
            "section_count": len(doc.sections),
            "contact_name": doc.header.name,
            "contact_email": doc.header.email,
        },
    )
