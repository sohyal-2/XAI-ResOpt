from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Claim, ClaimEvidence, ClaimStatus, EvidenceItem, KnowledgeEntity, KnowledgeRelationship
from app.schemas.evidence import ClaimCreate, KnowledgeEntityCreate, KnowledgeRelationshipCreate


async def create_claim(db: AsyncSession, owner_id: UUID, payload: ClaimCreate) -> Claim:
    try:
        status = ClaimStatus(payload.support_status)
    except ValueError as error:
        raise ValueError("support_status must be SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, or CONTRADICTED.") from error
    evidence_ids = [item.evidence_id for item in payload.evidence]
    evidence_rows = []
    if evidence_ids:
        evidence_rows = list((await db.scalars(select(EvidenceItem).where(EvidenceItem.id.in_(evidence_ids), EvidenceItem.owner_id == owner_id))).all())
        if len(evidence_rows) != len(set(evidence_ids)):
            raise LookupError("One or more evidence records were not found for this user.")
    claim = Claim(owner_id=owner_id, text=payload.text, support_status=status, confidence=payload.confidence)
    db.add(claim)
    await db.flush()
    for link in payload.evidence:
        db.add(ClaimEvidence(claim_id=claim.id, evidence_item_id=link.evidence_id, relationship_type=link.relationship_type, rationale=link.rationale, support_confidence=link.support_confidence))
    await db.commit()
    await db.refresh(claim)
    return claim


async def link_claim_evidence(db: AsyncSession, owner_id: UUID, claim_id: UUID, evidence_id: UUID, relationship_type: str, rationale: str, support_confidence: float) -> ClaimEvidence:
    claim = await db.scalar(select(Claim).where(Claim.id == claim_id, Claim.owner_id == owner_id))
    evidence = await db.scalar(select(EvidenceItem).where(EvidenceItem.id == evidence_id, EvidenceItem.owner_id == owner_id))
    if claim is None or evidence is None:
        raise LookupError("Claim or evidence record was not found for this user.")
    link = ClaimEvidence(claim_id=claim_id, evidence_item_id=evidence_id, relationship_type=relationship_type, rationale=rationale, support_confidence=support_confidence)
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def create_knowledge_entity(db: AsyncSession, owner_id: UUID, payload: KnowledgeEntityCreate) -> KnowledgeEntity:
    evidence = None
    if payload.source_evidence_id is not None:
        evidence = await db.scalar(select(EvidenceItem).where(EvidenceItem.id == payload.source_evidence_id, EvidenceItem.owner_id == owner_id))
        if evidence is None:
            raise LookupError("Source evidence was not found for this user.")
    entity = KnowledgeEntity(owner_id=owner_id, entity_type=payload.entity_type, text=payload.text, normalized_text=payload.normalized_text or payload.text.casefold(), source_evidence_id=payload.source_evidence_id, confidence=payload.confidence)
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


async def create_knowledge_relationship(db: AsyncSession, owner_id: UUID, payload: KnowledgeRelationshipCreate) -> KnowledgeRelationship:
    entities = list((await db.scalars(select(KnowledgeEntity).where(KnowledgeEntity.id.in_([payload.source_entity_id, payload.target_entity_id]), KnowledgeEntity.owner_id == owner_id))).all())
    if len(entities) != 2 or payload.source_entity_id == payload.target_entity_id:
        raise LookupError("Both knowledge entities must belong to this user and be distinct.")
    if payload.evidence_item_id is not None:
        evidence = await db.scalar(select(EvidenceItem).where(EvidenceItem.id == payload.evidence_item_id, EvidenceItem.owner_id == owner_id))
        if evidence is None:
            raise LookupError("Relationship evidence was not found for this user.")
    relationship = KnowledgeRelationship(owner_id=owner_id, source_entity_id=payload.source_entity_id, target_entity_id=payload.target_entity_id, relationship_type=payload.relationship_type, evidence_item_id=payload.evidence_item_id)
    db.add(relationship)
    await db.commit()
    await db.refresh(relationship)
    return relationship
