"""0038_copilot_notifications

Add 3 tables for AI Marketing Copilot:
  - notification_preferences
  - copilot_conversations
  - notification_log

Revision ID: 0038_copilot_notifications
Revises: 0037_superuser
"""
from alembic import op
import sqlalchemy as sa

revision = "0038_copilot_notifications"
down_revision = "0037_superuser"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── notification_preferences ──────────────────────────────────────
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("channel_config", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_new_rfq", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_hot_visitor", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_daily_summary", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_churn_risk", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notify_chat_handoff", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_content_suggestion", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quiet_hours_start", sa.String(5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(5), nullable=True),
        sa.Column("binding_code", sa.String(10), nullable=True),
        sa.Column("binding_code_expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"])
    op.create_index("ix_notification_preferences_tenant_id", "notification_preferences", ["tenant_id"])
    op.create_index("ix_notification_preferences_binding_code", "notification_preferences", ["binding_code"])

    # ── copilot_conversations ─────────────────────────────────────────
    op.create_table(
        "copilot_conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("channel_user_id", sa.String(200), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_copilot_conversations_user_id", "copilot_conversations", ["user_id"])
    op.create_index("ix_copilot_conversations_channel_user_id", "copilot_conversations", ["channel_user_id"])

    # ── notification_log ──────────────────────────────────────────────
    op.create_table(
        "notification_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_ref_id", sa.UUID(), nullable=True),
        sa.Column("message_preview", sa.String(500), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="sent"),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_log_tenant_id", "notification_log", ["tenant_id"])
    op.create_index("ix_notification_log_user_id", "notification_log", ["user_id"])
    op.create_index("ix_notification_log_event_type", "notification_log", ["event_type"])
    op.create_index("ix_notification_log_event_ref_id", "notification_log", ["event_ref_id"])


def downgrade() -> None:
    op.drop_table("notification_log")
    op.drop_table("copilot_conversations")
    op.drop_table("notification_preferences")
