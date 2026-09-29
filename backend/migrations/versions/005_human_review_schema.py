"""Add columns for Human-in-the-Loop review and traceability to resume_changes.

Revision ID: 005_human_review_schema
Revises: 004_job_description_metadata
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "005_human_review_schema"
down_revision = "004_job_description_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE resume_changes
        ADD COLUMN IF NOT EXISTS section VARCHAR(100) DEFAULT 'experience' NOT NULL,
        ADD COLUMN IF NOT EXISTS change_type VARCHAR(50) DEFAULT 'bullet' NOT NULL,
        ADD COLUMN IF NOT EXISTS reason TEXT DEFAULT '' NOT NULL,
        ADD COLUMN IF NOT EXISTS risk_level VARCHAR(30) DEFAULT 'low' NOT NULL,
        ADD COLUMN IF NOT EXISTS support_status VARCHAR(30) DEFAULT 'SUPPORTED' NOT NULL,
        ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 0.95 NOT NULL,
        ADD COLUMN IF NOT EXISTS evidence_ids JSONB DEFAULT '[]'::jsonb NOT NULL,
        ADD COLUMN IF NOT EXISTS manual_text TEXT,
        ADD COLUMN IF NOT EXISTS is_manual BOOLEAN DEFAULT FALSE NOT NULL,
        ADD COLUMN IF NOT EXISTS recommendation_id UUID REFERENCES recommendations(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS claim_id UUID REFERENCES claims(id) ON DELETE SET NULL;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE resume_changes
        DROP COLUMN IF EXISTS section,
        DROP COLUMN IF EXISTS change_type,
        DROP COLUMN IF EXISTS reason,
        DROP COLUMN IF EXISTS risk_level,
        DROP COLUMN IF EXISTS support_status,
        DROP COLUMN IF EXISTS confidence,
        DROP COLUMN IF EXISTS evidence_ids,
        DROP COLUMN IF EXISTS manual_text,
        DROP COLUMN IF EXISTS is_manual,
        DROP COLUMN IF EXISTS recommendation_id,
        DROP COLUMN IF EXISTS claim_id;
    """)
