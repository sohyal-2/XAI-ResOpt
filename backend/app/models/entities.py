import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClaimStatus(str, enum.Enum):
    supported = "SUPPORTED"
    partially_supported = "PARTIALLY_SUPPORTED"
    unsupported = "UNSUPPORTED"
    contradicted = "CONTRADICTED"


class JobRequirementKind(str, enum.Enum):
    mandatory = "mandatory"
    preferred = "preferred"
    nice_to_have = "nice_to_have"
    contextual = "contextual"


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ChangeDecision(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    edited = "edited"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resumes"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)


class ResumeVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resume_versions"
    resume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text)
    content_text: Mapped[str | None] = mapped_column(Text)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    __table_args__ = (UniqueConstraint("resume_id", "version_number", name="uq_resume_version_number"),)


class ResumeSection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resume_sections"
    resume_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True)
    section_type: Mapped[str] = mapped_column(String(80), nullable=False)
    heading: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class ExternalSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "external_sources"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    source_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    __table_args__ = (UniqueConstraint("owner_id", "uri", name="uq_external_source_owner_uri"),)


class EvidenceItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evidence_items"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    external_source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("external_sources.id", ondelete="SET NULL"), index=True)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), default="document", nullable=False)
    source_document: Mapped[str | None] = mapped_column(Text)
    source_location: Mapped[str | None] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    parser_version: Mapped[str | None] = mapped_column(String(50))
    normalized_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))


class Claim(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "claims"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    evidence_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="SET NULL"), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    support_status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus, name="support_status"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)


class ClaimEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "claim_evidence"
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    evidence_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence_items.id", ondelete="CASCADE"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(40), default="supports", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    support_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    __table_args__ = (UniqueConstraint("claim_id", "evidence_item_id", name="uq_claim_evidence_pair"),)


class KnowledgeEntity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_entities"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_evidence_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="SET NULL"), index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)


class KnowledgeRelationship(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_relationships"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_entities.id", ondelete="CASCADE"), index=True)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_entities.id", ondelete="CASCADE"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(60), nullable=False)
    evidence_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="SET NULL"), index=True)
    __table_args__ = (UniqueConstraint("source_entity_id", "target_entity_id", "relationship_type", name="uq_knowledge_relationship"),)


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skills"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(150), nullable=False)
    __table_args__ = (UniqueConstraint("owner_id", "normalized_name", name="uq_skill_owner_name"),)


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_evidence_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="SET NULL"), index=True)


class Experience(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "experiences"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    employer: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    started_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Certification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "certifications"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(200))
    issued_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobDescription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_descriptions"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    seniority_indicators: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    keywords: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)


class JobRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_requirements"
    job_description_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[JobRequirementKind] = mapped_column(Enum(JobRequirementKind, name="job_requirement_kind"), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="keyword")
    source_location: Mapped[str | None] = mapped_column(Text)
    original_terms: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    normalized_terms: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    synonym_groups: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    years_experience: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)


class Analysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analyses"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resume_versions.id", ondelete="RESTRICT"), index=True)
    job_description_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_descriptions.id", ondelete="RESTRICT"), index=True)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="run_status"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)


class AgentRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="run_status"), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    request_id: Mapped[str | None] = mapped_column(String(100), index=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retrieval_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_usage: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    recovery_status: Mapped[str | None] = mapped_column(String(50))
    final_score: Mapped[float | None] = mapped_column(Float)
    output: Mapped[dict | None] = mapped_column(JSONB)


class Score(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scores"
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    category_scores: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    penalties: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    reasons: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(50), nullable=False)


class Recommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"), index=True)
    evidence_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="SET NULL"), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    risk: Mapped[str] = mapped_column(String(30), nullable=False)


class OptimizationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "optimization_runs"
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    changes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    rejected_changes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    validation_issues: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    evidence_used: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    __table_args__ = (UniqueConstraint("analysis_id", "iteration", name="uq_optimization_iteration"),)


class ResumeChange(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resume_changes"
    optimization_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("optimization_runs.id", ondelete="CASCADE"), index=True)
    resume_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True)
    before_text: Mapped[str] = mapped_column(Text, nullable=False)
    after_text: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[ChangeDecision] = mapped_column(Enum(ChangeDecision, name="change_decision"), nullable=False, default=ChangeDecision.pending)
    supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    section: Mapped[str] = mapped_column(String(100), default="experience", nullable=False)
    change_type: Mapped[str] = mapped_column(String(50), default="bullet", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(30), default="low", nullable=False)
    support_status: Mapped[str] = mapped_column(String(30), default="SUPPORTED", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.95, nullable=False)
    evidence_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    manual_text: Mapped[str | None] = mapped_column(Text)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("recommendations.id", ondelete="SET NULL"), index=True)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"), index=True)


class ValidationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "validation_results"
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    resume_change_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resume_changes.id", ondelete="CASCADE"), index=True)
    validator: Mapped[str] = mapped_column(String(80), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    issues: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)


class ApprovalHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_history"
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    decision: Mapped[ChangeDecision] = mapped_column(Enum(ChangeDecision, name="approval_decision"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ChatSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)


class ChatMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_messages"
    chat_session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


Index("ix_claims_owner_support_status", Claim.owner_id, Claim.support_status)
Index("ix_job_requirements_kind", JobRequirement.kind)
Index("ix_agent_runs_analysis_status", AgentRun.analysis_id, AgentRun.status)
