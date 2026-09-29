"""Add structured job intelligence fields.

Revision ID: 003_job_intelligence
Revises: 002_evidence_knowledge_model
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_job_intelligence"
down_revision = "002_evidence_knowledge_model"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not column_exists("job_requirements", "category"):
        op.add_column("job_requirements", sa.Column("category", sa.String(length=40), server_default="keyword", nullable=False))
    if not column_exists("job_requirements", "source_location"):
        op.add_column("job_requirements", sa.Column("source_location", sa.Text(), nullable=True))
    if not column_exists("job_requirements", "original_terms"):
        op.add_column("job_requirements", sa.Column("original_terms", postgresql.JSONB(), server_default="[]", nullable=False))
    if not column_exists("job_requirements", "synonym_groups"):
        op.add_column("job_requirements", sa.Column("synonym_groups", postgresql.JSONB(), server_default="[]", nullable=False))
    if not column_exists("job_requirements", "years_experience"):
        op.add_column("job_requirements", sa.Column("years_experience", sa.Integer(), nullable=True))
    if not column_exists("job_requirements", "confidence"):
        op.add_column("job_requirements", sa.Column("confidence", sa.Float(), server_default="0.85", nullable=False))


def downgrade() -> None:
    op.drop_column("job_requirements", "confidence")
    op.drop_column("job_requirements", "years_experience")
    op.drop_column("job_requirements", "synonym_groups")
    op.drop_column("job_requirements", "original_terms")
    op.drop_column("job_requirements", "source_location")
    op.drop_column("job_requirements", "category")
