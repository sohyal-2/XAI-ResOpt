from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.core.security import get_current_user
from app.db import get_db
from app.models import EvidenceItem, User
from app.parsing.documents import extract_document_text, extract_document_text_with_diagnostics
from app.parsing.job_description import parse_job_description
from app.parsing.resume import parse_resume
from app.parsing.url_safety import UnsafeUrlError, fetch_public_url
from app.parsing.validation import IngestionError, validate_upload
from app.schemas.ingestion import ExternalSourceResponse, IngestionResponse, JobDescriptionResponse
from app.services.ingestion import store_external_source, store_job_description, store_resume

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])

resume_limiter = RateLimiter(times=30, seconds=60, key_prefix="ingest:resume")
job_limiter = RateLimiter(times=30, seconds=60, key_prefix="ingest:job")
external_limiter = RateLimiter(times=20, seconds=60, key_prefix="ingest:external")


@router.post("/resumes", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(resume_limiter)])
async def ingest_resume(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> IngestionResponse:
    try:
        upload = validate_upload(file.filename or "", file.content_type, await file.read(), get_settings().max_upload_size_bytes)
        raw_text, diag = extract_document_text_with_diagnostics(upload)
        extraction = parse_resume(raw_text, upload.filename, diagnostics=diag)
        resume = await store_resume(db, current_user.id, extraction)
        return IngestionResponse(id=resume.id, source=extraction.source, item_count=len(extraction.items), items=extraction.items)
    except IngestionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/job-descriptions", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(job_limiter)])
async def ingest_job_description(
    text: str | None = Form(None),
    title: str | None = Form(None),
    url: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobDescriptionResponse:
    try:
        if url:
            fetched = await fetch_public_url(url, get_settings().url_fetch_timeout_seconds)
            content, source = fetched.text, url
        elif file is not None:
            upload = validate_upload(file.filename or "", file.content_type, await file.read(), get_settings().max_upload_size_bytes)
            content, source = extract_document_text(upload), upload.filename
        elif text and text.strip():
            content, source = text.strip(), "pasted job description"
        else:
            raise IngestionError("Provide pasted text, an uploaded document, or a public URL.")
        extraction = parse_job_description(content, source)
        if title:
            extraction.title = title.strip()
        job = await store_job_description(db, current_user.id, extraction)
        requirements = [item.model_dump(mode="json") for item in extraction.requirements]
        keywords = [item.model_dump(mode="json") for item in extraction.keywords]
        return JobDescriptionResponse(
            id=job.id,
            title=job.title,
            source=source,
            requirement_count=len(requirements),
            seniority_indicators=extraction.seniority_indicators,
            keywords=keywords,
            requirements=requirements,
            years_of_experience=extraction.years_of_experience,
            mandatory_skills=[item.model_dump(mode="json") for item in extraction.mandatory_skills],
            preferred_skills=[item.model_dump(mode="json") for item in extraction.preferred_skills],
            nice_to_have_skills=[item.model_dump(mode="json") for item in extraction.nice_to_have_skills],
            responsibilities=extraction.responsibilities,
            education_requirements=extraction.education_requirements,
            certifications=extraction.certifications,
            domain_knowledge=extraction.domain_knowledge,
            tooling=[item.model_dump(mode="json") for item in extraction.tooling],
            soft_skills=extraction.soft_skills,
            implied_requirements=extraction.implied_requirements,
        )
    except (IngestionError, UnsafeUrlError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


from app.integrations.github import extract_github_evidence
from app.integrations.policy import PolicyViolationError, RateLimitExceededError
from app.integrations.portfolio import extract_portfolio_evidence


@router.post("/external", response_model=ExternalSourceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(external_limiter)])
async def ingest_external_url(
    url: str = Form(...),
    source_type: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExternalSourceResponse:
    if source_type not in {"github", "portfolio"}:
        raise HTTPException(status_code=422, detail="source_type must be github or portfolio.")
    try:
        timeout = get_settings().url_fetch_timeout_seconds
        structured_metadata = None
        evidence_items = None
        projects = None

        if source_type == "github":
            try:
                meta, ev_items = await extract_github_evidence(url, current_user.id)
                structured_metadata = meta.model_dump(mode="json")
                evidence_items = ev_items
                projects = [
                    {"name": r.name, "description": r.description}
                    for r in meta.repositories
                ]
                extraction = ExternalContentExtraction(
                    source=meta.url,
                    title=f"GitHub: @{meta.username}",
                    text=f"GitHub user @{meta.username} with {len(meta.repositories)} public repositories.",
                    items=[],
                )
            except RateLimitExceededError:
                raise
            except Exception:
                # Fallback to standard URL fetching if direct API fails or rate limited
                extraction = await fetch_public_url(url, timeout)
        elif source_type == "portfolio":
            try:
                p_result, ev_items = await extract_portfolio_evidence(url, current_user.id, timeout_seconds=timeout)
                structured_metadata = p_result.model_dump(mode="json")
                evidence_items = ev_items
                projects = [
                    {"name": p.title, "description": p.description}
                    for p in p_result.projects
                ]
                extraction = ExternalContentExtraction(
                    source=p_result.url,
                    title=p_result.title or "Portfolio",
                    text=p_result.raw_text[:2000],
                    items=[],
                )
            except (PolicyViolationError, RateLimitExceededError, UnsafeUrlError):
                raise
            except Exception:
                extraction = await fetch_public_url(url, timeout)
        else:
            extraction = await fetch_public_url(url, timeout)

        source = await store_external_source(
            db,
            current_user.id,
            source_type,
            extraction,
            structured_metadata=structured_metadata,
            evidence_items=evidence_items,
            projects=projects,
        )
        count = await db.scalar(select(func.count(EvidenceItem.id)).where(EvidenceItem.external_source_id == source.id))
        return ExternalSourceResponse(id=source.id, source_type=source.source_type, uri=source.uri, item_count=count or 0)
    except RateLimitExceededError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except PolicyViolationError as error:
        raise HTTPException(status_code=422, detail=f"Policy violation: {error}") from error
    except (IngestionError, UnsafeUrlError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
