"""0011_phase2_crm_sync_log

Phase 2.4.1 — CRM Sync Log:
  - crm_sync_logs table for Salesforce / HubSpot sync history

Revision ID: 0011_phase2_crm_sync_log
Revises: 0010_phase2_linkedin_audiences
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_phase2_crm_sync_log"
down_revision = "0010_phase2_linkedin_audiences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_sync_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("crm", sa.String(), nullable=False),
        sa.Column("direction", sa.String(), nullable=False, server_default="push"),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("local_id", sa.String(), nullable=True),
        sa.Column("remote_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="success"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("payload_summary", sa.String(), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_sync_logs_crm", "crm_sync_logs", ["crm"])
    op.create_index("ix_crm_sync_logs_entity_type", "crm_sync_logs", ["entity_type"])
    op.create_index("ix_crm_sync_logs_synced_at", "crm_sync_logs", ["synced_at"])


def downgrade() -> None:
    op.drop_index("ix_crm_sync_logs_synced_at")
    op.drop_index("ix_crm_sync_logs_entity_type")
    op.drop_index("ix_crm_sync_logs_crm")
    op.drop_table("crm_sync_logs")
