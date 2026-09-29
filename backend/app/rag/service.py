"""RAG Retrieval Service for database-backed evidence retrieval."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EvidenceItem, JobRequirement
from app.parsing.models import JobRequirementExtraction, RequirementCategory
from app.rag.hybrid import HybridRetrievalEngine
from app.rag.models import (
    RequirementRetrievalResult,
    RetrievalWeights,
)


class RetrievalService:
    """Service orchestrating database evidence retrieval with the hybrid engine."""

    def __init__(self, engine: HybridRetrievalEngine | None = None) -> None:
        self.engine = engine or HybridRetrievalEngine()

    async def get_owner_evidence(
        self,
        db: AsyncSession,
        owner_id: UUID,
    ) -> list[EvidenceItem]:
        """Fetch all evidence items belonging to the user/owner."""
        stmt = select(EvidenceItem).where(EvidenceItem.owner_id == owner_id)
        result = await db.scalars(stmt)
        return list(result.all())

    async def retrieve_for_requirement_db(
        self,
        db: AsyncSession,
        owner_id: UUID,
        requirement: JobRequirement | JobRequirementExtraction,
        weights: RetrievalWeights | None = None,
        limit: int = 5,
    ) -> RequirementRetrievalResult:
        """Retrieve evidence for a requirement against the owner's evidence in the database."""
        evidence_items = await self.get_owner_evidence(db, owner_id)

        if isinstance(requirement, JobRequirement):
            req_extraction = JobRequirementExtraction(
                text=requirement.text,
                kind=requirement.kind.value if hasattr(requirement.kind, "value") else str(requirement.kind),
                category=RequirementCategory(requirement.category) if requirement.category in RequirementCategory.__members__ else RequirementCategory.keyword,
                source_location=requirement.source_location or "Unknown",
                original_terms=requirement.original_terms or [],
                normalized_terms=requirement.normalized_terms or [],
                years_experience=requirement.years_experience,
                confidence=requirement.confidence,
            )
            req_id = requirement.id
        else:
            req_extraction = requirement
            req_id = None

        return self.engine.retrieve_for_requirement(
            requirement=req_extraction,
            evidence_items=evidence_items,
            weights=weights,
            requirement_id=req_id,
            limit=limit,
        )
