from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceResponse(BaseModel):
    id: UUID
    source_type: str
    source_document: str | None
    source_uri: str
    source_location: str | None
    evidence_type: str
    text: str
    normalized_text: str | None
    confidence: float
    created_at: datetime


class ClaimCreate(BaseModel):
    text: str = Field(min_length=1)
    support_status: str = "UNSUPPORTED"
    confidence: float = Field(ge=0, le=1)
    evidence: list["ClaimEvidenceCreate"] = Field(default_factory=list)


class ClaimEvidenceCreate(BaseModel):
    evidence_id: UUID
    relationship_type: str = "supports"
    rationale: str = Field(min_length=1)
    support_confidence: float = Field(ge=0, le=1)


class ClaimResponse(BaseModel):
    id: UUID
    text: str
    support_status: str
    confidence: float
    created_at: datetime


class ClaimEvidenceResponse(BaseModel):
    id: UUID
    claim_id: UUID
    evidence_item_id: UUID
    relationship_type: str
    rationale: str
    support_confidence: float
    evidence: EvidenceResponse


class KnowledgeEntityCreate(BaseModel):
    entity_type: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=1)
    normalized_text: str | None = None
    source_evidence_id: UUID | None = None
    confidence: float = Field(ge=0, le=1)


class KnowledgeEntityResponse(BaseModel):
    id: UUID
    entity_type: str
    text: str
    normalized_text: str
    source_evidence_id: UUID | None
    confidence: float


class KnowledgeRelationshipCreate(BaseModel):
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str = Field(min_length=1, max_length=60)
    evidence_item_id: UUID | None = None


class KnowledgeRelationshipResponse(BaseModel):
    id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str
    evidence_item_id: UUID | None
