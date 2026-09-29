from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.models import Claim, ClaimEvidence, EvidenceItem, User
from app.schemas.evidence import (
    ClaimCreate,
    ClaimEvidenceCreate,
    ClaimEvidenceResponse,
    ClaimResponse,
    EvidenceResponse,
    KnowledgeEntityCreate,
    KnowledgeEntityResponse,
    KnowledgeRelationshipCreate,
    KnowledgeRelationshipResponse,
)
from app.services.evidence import create_claim, create_knowledge_entity, create_knowledge_relationship, link_claim_evidence

router = APIRouter(prefix="/api", tags=["evidence"])


def evidence_response(row: EvidenceItem) -> EvidenceResponse:
    return EvidenceResponse(id=row.id, source_type=row.source_type, source_document=row.source_document, source_uri=row.source_uri, source_location=row.source_location, evidence_type=row.evidence_type, text=row.text, normalized_text=row.normalized_text, confidence=row.confidence, created_at=row.created_at)


def claim_response(row: Claim) -> ClaimResponse:
    return ClaimResponse(id=row.id, text=row.text, support_status=row.support_status.value, confidence=row.confidence, created_at=row.created_at)


@router.get("/evidence", response_model=list[EvidenceResponse])
async def list_evidence(limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[EvidenceResponse]:
    rows = (await db.scalars(select(EvidenceItem).where(EvidenceItem.owner_id == current_user.id).order_by(EvidenceItem.created_at.desc()).limit(limit))).all()
    return [evidence_response(row) for row in rows]


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(evidence_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> EvidenceResponse:
    row = await db.scalar(select(EvidenceItem).where(EvidenceItem.id == evidence_id, EvidenceItem.owner_id == current_user.id))
    if row is None:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return evidence_response(row)


@router.post("/claims", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def post_claim(payload: ClaimCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> ClaimResponse:
    try:
        return claim_response(await create_claim(db, current_user.id, payload))
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/claims/{claim_id}", response_model=ClaimResponse)
async def get_claim(claim_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> ClaimResponse:
    row = await db.scalar(select(Claim).where(Claim.id == claim_id, Claim.owner_id == current_user.id))
    if row is None:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return claim_response(row)


@router.post("/claims/{claim_id}/evidence", response_model=ClaimEvidenceResponse, status_code=status.HTTP_201_CREATED)
async def post_claim_evidence(claim_id: UUID, payload: ClaimEvidenceCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> ClaimEvidenceResponse:
    try:
        link = await link_claim_evidence(db, current_user.id, claim_id, payload.evidence_id, payload.relationship_type, payload.rationale, payload.support_confidence)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    evidence = await db.scalar(select(EvidenceItem).where(EvidenceItem.id == link.evidence_item_id))
    return ClaimEvidenceResponse(id=link.id, claim_id=link.claim_id, evidence_item_id=link.evidence_item_id, relationship_type=link.relationship_type, rationale=link.rationale, support_confidence=link.support_confidence, evidence=evidence_response(evidence))


@router.get("/claims/{claim_id}/provenance", response_model=list[ClaimEvidenceResponse])
async def get_claim_provenance(claim_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[ClaimEvidenceResponse]:
    claim = await db.scalar(select(Claim).where(Claim.id == claim_id, Claim.owner_id == current_user.id))
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found.")
    rows = (await db.execute(select(ClaimEvidence, EvidenceItem).join(EvidenceItem, EvidenceItem.id == ClaimEvidence.evidence_item_id).where(ClaimEvidence.claim_id == claim_id, EvidenceItem.owner_id == current_user.id))).all()
    return [ClaimEvidenceResponse(id=link.id, claim_id=link.claim_id, evidence_item_id=link.evidence_item_id, relationship_type=link.relationship_type, rationale=link.rationale, support_confidence=link.support_confidence, evidence=evidence_response(evidence)) for link, evidence in rows]


@router.post("/knowledge/entities", response_model=KnowledgeEntityResponse, status_code=status.HTTP_201_CREATED)
async def post_knowledge_entity(payload: KnowledgeEntityCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> KnowledgeEntityResponse:
    try:
        row = await create_knowledge_entity(db, current_user.id, payload)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return KnowledgeEntityResponse(id=row.id, entity_type=row.entity_type, text=row.text, normalized_text=row.normalized_text, source_evidence_id=row.source_evidence_id, confidence=row.confidence)


@router.post("/knowledge/relationships", response_model=KnowledgeRelationshipResponse, status_code=status.HTTP_201_CREATED)
async def post_knowledge_relationship(payload: KnowledgeRelationshipCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> KnowledgeRelationshipResponse:
    try:
        row = await create_knowledge_relationship(db, current_user.id, payload)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return KnowledgeRelationshipResponse(id=row.id, source_entity_id=row.source_entity_id, target_entity_id=row.target_entity_id, relationship_type=row.relationship_type, evidence_item_id=row.evidence_item_id)
