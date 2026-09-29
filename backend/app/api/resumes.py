"""REST API router for deterministic resume preview, validation, and ATS-safe PDF/DOCX exports."""

from __future__ import annotations

import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime

from pydantic import BaseModel

from app.core.security import get_current_user
from app.db import get_db
from app.models.entities import Resume, ResumeChange, ResumeVersion, User
from app.schemas.rendering import (
    DeterministicResumeDocument,
    ResumeRenderConfig,
    ResumeValidationResult,
)
from app.services.rendering import (
    ATSDocxRenderer,
    ATSPdfRenderer,
    build_deterministic_document,
    validate_resume_for_rendering,
)

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


class ResumeSummaryItem(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    versions_count: int
    latest_version_id: UUID | None = None
    latest_version_number: int | None = None
    is_final: bool = False


class ResumeVersionSummaryItem(BaseModel):
    id: UUID
    resume_id: UUID
    version_number: int
    is_final: bool
    source_uri: str | None = None
    created_at: datetime
    content_preview: str | None = None


@router.get("", response_model=list[ResumeSummaryItem])
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ResumeSummaryItem]:
    """Lists all resumes uploaded or generated for current user."""
    res_stmt = (
        select(Resume)
        .where(Resume.owner_id == current_user.id)
        .order_by(Resume.created_at.desc())
    )
    resumes = list((await db.scalars(res_stmt)).all())

    summaries: list[ResumeSummaryItem] = []
    for r in resumes:
        v_stmt = (
            select(ResumeVersion)
            .where(ResumeVersion.resume_id == r.id)
            .order_by(ResumeVersion.version_number.desc())
        )
        versions = list((await db.scalars(v_stmt)).all())
        latest = versions[0] if versions else None

        summaries.append(
            ResumeSummaryItem(
                id=r.id,
                title=r.title,
                created_at=r.created_at,
                versions_count=len(versions),
                latest_version_id=latest.id if latest else None,
                latest_version_number=latest.version_number if latest else None,
                is_final=any(v.is_final for v in versions),
            )
        )
    return summaries


@router.get("/{resume_id}/versions", response_model=list[ResumeVersionSummaryItem])
async def list_resume_versions(
    resume_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ResumeVersionSummaryItem]:
    """Lists all versions for a specific resume belonging to the user."""
    r = await db.scalar(select(Resume).where(Resume.id == resume_id, Resume.owner_id == current_user.id))
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    v_stmt = select(ResumeVersion).where(ResumeVersion.resume_id == resume_id).order_by(ResumeVersion.version_number.asc())
    versions = list((await db.scalars(v_stmt)).all())

    return [
        ResumeVersionSummaryItem(
            id=v.id,
            resume_id=v.resume_id,
            version_number=v.version_number,
            is_final=v.is_final,
            source_uri=v.source_uri,
            created_at=v.created_at,
            content_preview=v.content_text[:200] if v.content_text else None,
        )
        for v in versions
    ]



async def _get_validated_resume_document(
    db: AsyncSession,
    owner_id: UUID,
    version_id: UUID,
    config: ResumeRenderConfig | None = None,
) -> tuple[ResumeVersion, DeterministicResumeDocument, list[ResumeChange]]:
    """Helper to verify ownership, fetch changes, build document, and validate."""
    v_stmt = (
        select(ResumeVersion, Resume)
        .join(Resume, Resume.id == ResumeVersion.resume_id)
        .where(ResumeVersion.id == version_id, Resume.owner_id == owner_id)
    )
    res = (await db.execute(v_stmt)).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")

    resume_version, _ = res

    # Fetch associated resume changes
    changes_stmt = select(ResumeChange).where(ResumeChange.resume_version_id == resume_version.id)
    changes = list((await db.scalars(changes_stmt)).all())

    doc = build_deterministic_document(resume_version.content_text, version_id=version_id, config=config)
    return resume_version, doc, changes


@router.get("/versions/{version_id}/validate", response_model=ResumeValidationResult)
async def validate_resume_version(
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeValidationResult:
    """Runs strict pre-rendering validation across all 5 mandatory ATS and review invariants."""
    resume_ver, doc, changes = await _get_validated_resume_document(db, current_user.id, version_id)
    return validate_resume_for_rendering(doc, resume_ver.content_text, changes)


@router.get("/versions/{version_id}/preview", response_model=DeterministicResumeDocument)
async def preview_deterministic_resume(
    version_id: UUID,
    font_family: str = Query(default="Helvetica"),
    margins_inch: float = Query(default=0.6),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeterministicResumeDocument:
    """Returns the structured, deterministic document model for in-browser rendering."""
    config = ResumeRenderConfig(font_family=font_family, margins_inch=margins_inch)
    _, doc, _ = await _get_validated_resume_document(db, current_user.id, version_id, config=config)
    return doc


@router.get("/versions/{version_id}/export/pdf")
async def export_resume_pdf(
    version_id: UUID,
    font_family: str = Query(default="Helvetica"),
    margins_inch: float = Query(default=0.6),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Renders and streams a single-column, ATS-safe PDF document."""
    config = ResumeRenderConfig(font_family=font_family, margins_inch=margins_inch)
    resume_ver, doc, changes = await _get_validated_resume_document(db, current_user.id, version_id, config=config)

    # Validate before rendering
    val_res = validate_resume_for_rendering(doc, resume_ver.content_text, changes)
    if not val_res.is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Resume failed pre-rendering validation: {'; '.join(val_res.issues)}",
        )

    renderer = ATSPdfRenderer(doc)
    pdf_bytes = renderer.render_pdf_bytes()

    clean_name = doc.header.name.replace(" ", "_")
    filename = f"{clean_name}_Resume.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/versions/{version_id}/export/docx")
async def export_resume_docx(
    version_id: UUID,
    font_family: str = Query(default="Helvetica"),
    margins_inch: float = Query(default=0.6),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Renders and streams a clean, semantic single-column Word DOCX document."""
    config = ResumeRenderConfig(font_family=font_family, margins_inch=margins_inch)
    resume_ver, doc, changes = await _get_validated_resume_document(db, current_user.id, version_id, config=config)

    # Validate before rendering
    val_res = validate_resume_for_rendering(doc, resume_ver.content_text, changes)
    if not val_res.is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Resume failed pre-rendering validation: {'; '.join(val_res.issues)}",
        )

    renderer = ATSDocxRenderer(doc)
    docx_bytes = renderer.render_docx_bytes()

    clean_name = doc.header.name.replace(" ", "_")
    filename = f"{clean_name}_Resume.docx"

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
