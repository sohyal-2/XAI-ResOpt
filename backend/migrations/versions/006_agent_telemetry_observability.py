"""Add real agent observability telemetry columns to agent_runs table.

Revision ID: 006_agent_telemetry_observability
Revises: 005_human_review_schema
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "006_agent_telemetry_observability"
down_revision = "005_human_review_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE agent_runs
        ADD COLUMN IF NOT EXISTS request_id VARCHAR(100),
        ADD COLUMN IF NOT EXISTS start_time TIMESTAMP WITH TIME ZONE,
        ADD COLUMN IF NOT EXISTS end_time TIMESTAMP WITH TIME ZONE,
        ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0 NOT NULL,
        ADD COLUMN IF NOT EXISTS retrieval_count INTEGER DEFAULT 0 NOT NULL,
        ADD COLUMN IF NOT EXISTS model_calls INTEGER DEFAULT 0 NOT NULL,
        ADD COLUMN IF NOT EXISTS token_usage JSONB,
        ADD COLUMN IF NOT EXISTS error TEXT,
        ADD COLUMN IF NOT EXISTS recovery_status VARCHAR(50),
        ADD COLUMN IF NOT EXISTS final_score FLOAT;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE agent_runs
        DROP COLUMN IF EXISTS request_id,
        DROP COLUMN IF EXISTS start_time,
        DROP COLUMN IF EXISTS end_time,
        DROP COLUMN IF EXISTS retry_count,
        DROP COLUMN IF EXISTS retrieval_count,
        DROP COLUMN IF EXISTS model_calls,
        DROP COLUMN IF EXISTS token_usage,
        DROP COLUMN IF EXISTS error,
        DROP COLUMN IF EXISTS recovery_status,
        DROP COLUMN IF EXISTS final_score;
    """)
