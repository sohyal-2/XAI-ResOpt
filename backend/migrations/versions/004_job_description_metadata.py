"""Persist job description keywords and seniority indicators.

Revision ID: 004_job_description_metadata
Revises: 003_job_intelligence
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_job_description_metadata"
down_revision = "003_job_intelligence"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not column_exists("job_descriptions", "seniority_indicators"):
        op.add_column("job_descriptions", sa.Column("seniority_indicators", postgresql.JSONB(), server_default="[]", nullable=False))
    if not column_exists("job_descriptions", "keywords"):
        op.add_column("job_descriptions", sa.Column("keywords", postgresql.JSONB(), server_default="[]", nullable=False))


def downgrade() -> None:
    op.drop_column("job_descriptions", "keywords")
    op.drop_column("job_descriptions", "seniority_indicators")