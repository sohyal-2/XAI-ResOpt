from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.evidence_rules import (
    MAX_SUPPORTING_CONFIDENCE,
    SUPPORTING_EVIDENCE_TYPE,
)
from app.models import (
    EvidenceItem,
    ExternalSource,
    JobDescription,
    JobRequirement,
    Project,
    Resume,
    ResumeSection,
    ResumeVersion,
)
from app.parsing.models import ExternalContentExtraction, JobDescriptionExtraction, ResumeExtraction


async def store_resume(db: AsyncSession, owner_id: UUID, extraction: ResumeExtraction) -> Resume:
    resume = Resume(owner_id=owner_id, title=extraction.name or "Imported resume")
    db.add(resume)
    await db.flush()
    version = ResumeVersion(resume_id=resume.id, version_number=1, source_uri=extraction.source, content_text=extraction.raw_text)
    db.add(version)
    await db.flush()
    for position, (section_type, items) in enumerate(extraction.sections.items()):
        db.add(ResumeSection(resume_version_id=version.id, section_type=section_type, heading=section_type.title(), content="\n".join(item.text for item in items), position=position))
    for item in extraction.items:
        db.add(EvidenceItem(id=item.id, owner_id=owner_id, source_type="resume", source_document=item.source, source_uri=item.source, source_location=item.location, evidence_type=item.type, text=item.text, confidence=item.confidence, normalized_text=item.text.casefold()))
    await db.commit()
    await db.refresh(resume)
    return resume


async def store_job_description(db: AsyncSession, owner_id: UUID, extraction: JobDescriptionExtraction) -> JobDescription:
    job = JobDescription(owner_id=owner_id, title=extraction.title or "Imported job description", source_uri=extraction.source, content_text=extraction.raw_text, seniority_indicators=extraction.seniority_indicators, keywords=[term.model_dump(mode="json") for term in extraction.keywords])
    db.add(job)
    await db.flush()
    for requirement in extraction.requirements:
        db.add(JobRequirement(job_description_id=job.id, text=requirement.text, kind=requirement.kind, category=requirement.category.value, source_location=requirement.source_location, original_terms=requirement.original_terms, normalized_terms=requirement.normalized_terms, synonym_groups=[term.synonyms for term in requirement.terms], years_experience=requirement.years_experience, confidence=requirement.confidence))
    await db.commit()
    await db.refresh(job)
    return job


async def store_external_source(
    db: AsyncSession,
    owner_id: UUID,
    source_type: str,
    extraction: ExternalContentExtraction,
    structured_metadata: dict[str, Any] | None = None,
    evidence_items: list[EvidenceItem] | None = None,
    projects: list[dict[str, Any]] | None = None,
) -> ExternalSource:
    """Stores an external source record, ensuring external data is supporting evidence only."""
    uri = str(extraction.source)
    existing = await db.scalar(select(ExternalSource).where(ExternalSource.owner_id == owner_id, ExternalSource.uri == uri))

    meta = structured_metadata or {"title": extraction.title}
    source = existing or ExternalSource(owner_id=owner_id, source_type=source_type, uri=uri, source_metadata=meta)
    if existing is None:
        db.add(source)
        await db.flush()
    else:
        source.source_metadata = meta
        await db.flush()

    # If explicit supporting evidence items were provided (from GitHub/Portfolio extractors)
    if evidence_items:
        for item in evidence_items:
            item.external_source_id = source.id
            db.add(item)
    else:
        # Fallback to extraction items
        for item in extraction.items:
            db.add(
                EvidenceItem(
                    id=item.id,
                    owner_id=owner_id,
                    external_source_id=source.id,
                    source_type=source_type,
                    source_document=item.source,
                    source_uri=item.source,
                    source_location=item.location,
                    evidence_type=SUPPORTING_EVIDENCE_TYPE,
                    text=item.text,
                    confidence=min(item.confidence, MAX_SUPPORTING_CONFIDENCE),
                    normalized_text=item.text.casefold(),
                )
            )

    # If structured projects were extracted, link to Project entities
    if projects:
        for proj in projects:
            p_name = proj.get("name") or proj.get("title") or "Unnamed Project"
            p_desc = proj.get("description")
            p_evidence_id = proj.get("evidence_id")
            db.add(
                Project(
                    owner_id=owner_id,
                    name=p_name[:200],
                    description=p_desc,
                    source_evidence_id=p_evidence_id,
                )
            )

    await db.commit()
    await db.refresh(source)
    return source
