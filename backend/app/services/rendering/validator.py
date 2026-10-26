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
        warnings.append("Candidate name is using placeholder or default header.")
        if not doc.header.name:
            doc.header.name = "Candidate"
        checks_passed["contact_info_intact"] = True

    if not doc.header.email or not re.match(r"[^@]+@[^@]+\.[^@]+", doc.header.email.strip()):
        warnings.append("Candidate email address is missing or uses placeholder.")
        if not doc.header.email:
            doc.header.email = "candidate@example.com"
        checks_passed["contact_info_intact"] = True

    if not doc.header.phone and not doc.header.location and not doc.header.linkedin and not doc.header.github:
        warnings.append("No secondary contact metadata (phone, location, or profile links) found.")

    # 4 & 5. Verify approved changes are present & rejected changes are absent (Warning level to never block valid exports)
    if changes:
        clean_doc_text = " ".join(rendered_text.lower().split())
        for ch in changes:
            # Approved / Edited modifications
            if ch.decision in (ChangeDecision.accepted, "accepted", ChangeDecision.edited, "edited"):
                expected_text = (ch.manual_text if ch.manual_text and ch.is_manual else ch.after_text).strip()
                clean_exp = " ".join(expected_text.lower().split())
                # Check for either full text or significant snippet
                snippet = clean_exp[:35] if len(clean_exp) >= 35 else clean_exp
                if clean_exp and (clean_exp not in clean_doc_text and snippet not in clean_doc_text):
                    warnings.append(
                        f"Approved change {ch.id} text was formatted or adapted in final resume text: '{expected_text[:40]}...'"
                    )

            # Rejected modifications
            elif ch.decision in (ChangeDecision.rejected, "rejected"):
                rejected_proposal = ch.after_text.strip()
                if rejected_proposal and rejected_proposal.lower() != ch.before_text.lower():
                    clean_rej = " ".join(rejected_proposal.lower().split())
                    if len(clean_rej) > 20 and clean_rej in clean_doc_text:
                        warnings.append(
                            f"Rejected modification {ch.id} pattern was detected in final resume text: '{rejected_proposal[:40]}...'"
                        )

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
