"""Add claim provenance and knowledge graph relationships.

Revision ID: 002_evidence_knowledge_model
Revises: 001_initial_schema
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_evidence_knowledge_model"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table_name in insp.get_table_names()


def upgrade() -> None:
    op.execute("ALTER TYPE support_status ADD VALUE IF NOT EXISTS 'PARTIALLY_SUPPORTED'")
    op.execute("ALTER TYPE support_status ADD VALUE IF NOT EXISTS 'CONTRADICTED'")

    if not column_exists("evidence_items", "source_type"):
        op.add_column("evidence_items", sa.Column("source_type", sa.String(length=40), server_default="document", nullable=False))
    if not column_exists("evidence_items", "source_document"):
        op.add_column("evidence_items", sa.Column("source_document", sa.Text(), nullable=True))

    if not table_exists("claim_evidence"):
        op.create_table(
            "claim_evidence",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
            sa.Column("evidence_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("relationship_type", sa.String(length=40), nullable=False),
            sa.Column("rationale", sa.Text(), nullable=False),
            sa.Column("support_confidence", sa.Float(), nullable=False),
            sa.UniqueConstraint("claim_id", "evidence_item_id", name="uq_claim_evidence_pair"),
        )
        op.create_index("ix_claim_evidence_claim_id", "claim_evidence", ["claim_id"])
        op.create_index("ix_claim_evidence_evidence_item_id", "claim_evidence", ["evidence_item_id"])

    if not table_exists("knowledge_entities"):
        op.create_table(
            "knowledge_entities",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("entity_type", sa.String(length=40), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("normalized_text", sa.Text(), nullable=False),
            sa.Column("source_evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False),
        )
        op.create_index("ix_knowledge_entities_owner_id", "knowledge_entities", ["owner_id"])
        op.create_index("ix_knowledge_entities_source_evidence_id", "knowledge_entities", ["source_evidence_id"])

    if not table_exists("knowledge_relationships"):
        op.create_table(
            "knowledge_relationships",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False),
            sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False),
            sa.Column("relationship_type", sa.String(length=60), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("provenance_evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_knowledge_relationships_owner_id", "knowledge_relationships", ["owner_id"])
        op.create_index("ix_knowledge_relationships_provenance_evidence_id", "knowledge_relationships", ["provenance_evidence_id"])
        op.create_index("ix_knowledge_relationships_source_entity_id", "knowledge_relationships", ["source_entity_id"])
        op.create_index("ix_knowledge_relationships_target_entity_id", "knowledge_relationships", ["target_entity_id"])


def downgrade() -> None:
    op.drop_table("knowledge_relationships")
    op.drop_table("knowledge_entities")
    op.drop_table("claim_evidence")
    op.drop_column("evidence_items", "source_document")
    op.drop_column("evidence_items", "source_type")
