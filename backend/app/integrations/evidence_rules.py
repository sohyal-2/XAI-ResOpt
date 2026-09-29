"""Invariant enforcement: External data must NEVER automatically prove a skill. It is supporting evidence only."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from app.integrations.policy import PrivacyScrubber
from app.models import ClaimEvidence, EvidenceItem

# Core Constants
SUPPORTING_EVIDENCE_TYPE = "external_supporting"
MAX_SUPPORTING_CONFIDENCE = 0.70  # External evidence cannot exceed 0.70 confidence on its own
SUPPORTING_RELATIONSHIP_TYPE = "supports"


class SupportingEvidenceRecord(BaseModel):
    """Encapsulates supporting evidence with strict provenance and confidence cap."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    source_type: str  # "github" | "portfolio"
    source_document: str  # e.g. "GitHub Profile", "GitHub Repository: octocat/hello-world"
    source_uri: str
    source_location: str  # e.g. "github:octocat/hello-world#readme"
    evidence_type: str = SUPPORTING_EVIDENCE_TYPE
    text: str
    confidence: float = MAX_SUPPORTING_CONFIDENCE
    is_supporting_only: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillSupportStatus(BaseModel):
    """Result of evaluating whether an external record corroborates or attempts to falsely prove a skill."""

    skill_name: str
    is_proven: bool
    status: str  # "corroborated", "unsupported_in_resume", "unverified"
    rationale: str
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)


def build_supporting_evidence_item(
    owner_id: UUID,
    source_type: str,
    source_uri: str,
    source_document: str,
    source_location: str,
    raw_text: str,
    confidence: float = MAX_SUPPORTING_CONFIDENCE,
    external_source_id: UUID | None = None,
) -> EvidenceItem:
    """Builds an EvidenceItem that enforces supporting-evidence bounds and scrubs private data."""
    scrubbed = PrivacyScrubber.scrub(raw_text.strip())
    capped_confidence = min(max(confidence, 0.1), MAX_SUPPORTING_CONFIDENCE)

    return EvidenceItem(
        id=uuid4(),
        owner_id=owner_id,
        external_source_id=external_source_id,
        source_type=source_type,
        source_document=source_document,
        source_uri=source_uri,
        source_location=source_location,
        evidence_type=SUPPORTING_EVIDENCE_TYPE,
        text=scrubbed,
        confidence=capped_confidence,
        normalized_text=scrubbed.casefold(),
    )


def create_supporting_claim_link(
    claim_id: UUID,
    evidence_item_id: UUID,
    rationale: str,
    confidence: float = MAX_SUPPORTING_CONFIDENCE,
) -> ClaimEvidence:
    """Creates a ClaimEvidence record strictly bound to 'supports' relationship."""
    return ClaimEvidence(
        claim_id=claim_id,
        evidence_item_id=evidence_item_id,
        relationship_type=SUPPORTING_RELATIONSHIP_TYPE,
        rationale=f"[Supporting Evidence Only] {rationale}",
        support_confidence=min(confidence, MAX_SUPPORTING_CONFIDENCE),
    )


def evaluate_skill_provenance(
    skill_name: str,
    has_resume_mention: bool,
    supporting_items: list[EvidenceItem] | None = None,
) -> SkillSupportStatus:
    """Evaluates whether an external data point can prove or merely support a skill.

    Invariant: External repositories and portfolio pages NEVER automatically prove a skill.
    If the resume itself does not claim the skill, it remains unproven.
    """
    items = supporting_items or []
    item_ids = [item.id for item in items]

    if not has_resume_mention:
        return SkillSupportStatus(
            skill_name=skill_name,
            is_proven=False,
            status="unsupported_in_resume",
            rationale=(
                f"External evidence references '{skill_name}', but the skill is not documented in the resume. "
                "Per XAI-ResOpt safety guidelines, external data cannot automatically prove a skill without candidate claim."
            ),
            supporting_evidence_ids=item_ids,
        )

    if items:
        return SkillSupportStatus(
            skill_name=skill_name,
            is_proven=True,
            status="corroborated",
            rationale=(
                f"Skill '{skill_name}' is stated in the resume and successfully corroborated by {len(items)} "
                "external supporting evidence records."
            ),
            supporting_evidence_ids=item_ids,
        )

    return SkillSupportStatus(
        skill_name=skill_name,
        is_proven=True,
        status="resume_only",
        rationale=f"Skill '{skill_name}' is verified directly from resume content.",
        supporting_evidence_ids=[],
    )
