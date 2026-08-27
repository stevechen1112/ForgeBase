"""Add rfq_events audit log table

Revision ID: 0030_rfq_events
Revises: 0029_chat_admin_fields
Create Date: 2026-04-11
"""
import sqlalchemy as sa
from alembic import op

revision = "0030_rfq_events"
down_revision = "0029_chat_admin_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rfq_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rfq_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfq_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rfq_events_rfq_id", "rfq_events", ["rfq_id"])
    op.create_index("ix_rfq_events_event_type", "rfq_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_rfq_events_event_type", table_name="rfq_events")
    op.drop_index("ix_rfq_events_rfq_id", table_name="rfq_events")
    op.drop_table("rfq_events")
