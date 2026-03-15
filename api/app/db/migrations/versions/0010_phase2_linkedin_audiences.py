"""0010_phase2_linkedin_audiences

Phase 2.1.6 — LinkedIn Audience Sync:
  - linkedin_audiences table

Revision ID: 0010_phase2_linkedin_audiences
Revises: 0009_phase2_nurture_engine
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_phase2_linkedin_audiences"
down_revision = "0009_phase2_nurture_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "linkedin_audiences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("linkedin_segment_id", sa.String(), nullable=True),
        sa.Column("audience_type", sa.String(), nullable=False, server_default="EMAIL"),
        sa.Column("source_type", sa.String(), nullable=False, server_default="segment"),
        sa.Column("source_segment_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_linkedin_audiences_name", "linkedin_audiences", ["name"])
    op.create_index("ix_linkedin_audiences_linkedin_segment_id", "linkedin_audiences", ["linkedin_segment_id"])


def downgrade() -> None:
    op.drop_index("ix_linkedin_audiences_linkedin_segment_id")
    op.drop_index("ix_linkedin_audiences_name")
    op.drop_table("linkedin_audiences")
