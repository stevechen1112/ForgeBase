"""Approval-send policy, immutable delivery snapshot and message-linked events.

Revision ID: 0083_outreach_approval_send
Revises: 0082_journey_outreach_drafts
"""

import sqlalchemy as sa
from alembic import op

revision = "0083_outreach_approval_send"
down_revision = "0082_journey_outreach_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outreach_delivery_policies",
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("mode", sa.String(20), nullable=False, server_default="off"),
        sa.Column(
            "provider_name", sa.String(20), nullable=False, server_default="resend"
        ),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column(
            "quiet_hours_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "quiet_start_hour", sa.Integer(), nullable=False, server_default="20"
        ),
        sa.Column("quiet_end_hour", sa.Integer(), nullable=False, server_default="8"),
        sa.Column(
            "daily_send_quota", sa.Integer(), nullable=False, server_default="10"
        ),
        sa.Column(
            "frequency_cap_days", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column(
            "unsubscribe_scope", sa.String(20), nullable=False, server_default="tenant"
        ),
        sa.Column(
            "updated_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "mode IN ('off', 'approval_send')", name="ck_outreach_delivery_policy_mode"
        ),
        sa.CheckConstraint(
            "provider_name = 'resend'", name="ck_outreach_delivery_provider"
        ),
        sa.CheckConstraint(
            "quiet_start_hour >= 0 AND quiet_start_hour <= 23",
            name="ck_outreach_quiet_start",
        ),
        sa.CheckConstraint(
            "quiet_end_hour >= 0 AND quiet_end_hour <= 23", name="ck_outreach_quiet_end"
        ),
        sa.CheckConstraint(
            "daily_send_quota >= 0", name="ck_outreach_daily_send_quota"
        ),
        sa.CheckConstraint(
            "frequency_cap_days >= 1 AND frequency_cap_days <= 365",
            name="ck_outreach_frequency_days",
        ),
        sa.CheckConstraint(
            "unsubscribe_scope IN ('tenant', 'global')",
            name="ck_outreach_unsubscribe_scope",
        ),
    )
    op.create_index(
        "ix_outreach_delivery_policies_mode", "outreach_delivery_policies", ["mode"]
    )

    op.drop_constraint("ck_outreach_message_status", "outreach_messages", type_="check")
    op.create_check_constraint(
        "ck_outreach_message_status",
        "outreach_messages",
        "status IN ('draft', 'pending_review', 'approved', 'rejected', 'cancelled', "
        "'queued', 'sending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', "
        "'complained', 'unsubscribed', 'failed')",
    )
    columns = (
        sa.Column("send_idempotency_key", sa.String(200), nullable=True),
        sa.Column(
            "send_requested_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("send_requested_at", sa.DateTime(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(), nullable=True),
        sa.Column("send_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sending_at", sa.DateTime(), nullable=True),
        sa.Column("provider", sa.String(20), nullable=True),
        sa.Column("provider_message_id", sa.String(120), nullable=True),
        sa.Column("sent_subject_snapshot", sa.String(500), nullable=True),
        sa.Column("sent_from_name", sa.String(200), nullable=True),
        sa.Column("sent_from_email", sa.String(254), nullable=True),
        sa.Column("sent_html_snapshot", sa.Text(), nullable=True),
        sa.Column("sent_text_snapshot", sa.Text(), nullable=True),
        sa.Column(
            "sent_headers", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("unsubscribe_token_hash", sa.String(64), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("clicked_at", sa.DateTime(), nullable=True),
        sa.Column("bounced_at", sa.DateTime(), nullable=True),
        sa.Column("complained_at", sa.DateTime(), nullable=True),
        sa.Column("unsubscribed_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(2000), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    for column in columns:
        op.add_column("outreach_messages", column)
    op.execute(
        "UPDATE outreach_messages SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP)"
    )
    op.alter_column("outreach_messages", "updated_at", nullable=False)
    op.create_check_constraint(
        "ck_outreach_message_send_attempts", "outreach_messages", "send_attempts >= 0"
    )
    op.create_unique_constraint(
        "uq_outreach_messages_send_idempotency_key",
        "outreach_messages",
        ["send_idempotency_key"],
    )
    op.create_unique_constraint(
        "uq_outreach_provider_message",
        "outreach_messages",
        ["provider", "provider_message_id"],
    )
    for column in (
        "scheduled_for",
        "provider",
        "provider_message_id",
        "unsubscribe_token_hash",
        "sent_at",
        "updated_at",
    ):
        op.create_index(f"ix_outreach_messages_{column}", "outreach_messages", [column])

    op.drop_constraint(
        "ck_outreach_review_action", "outreach_message_reviews", type_="check"
    )
    op.create_check_constraint(
        "ck_outreach_review_action",
        "outreach_message_reviews",
        "action IN ('generated', 'revised', 'approved', 'rejected', 'send_queued', 'send_cancelled', 'send_retried')",
    )

    op.add_column(
        "email_delivery_events",
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "email_delivery_events",
        sa.Column(
            "outreach_message_id",
            sa.Uuid(),
            sa.ForeignKey("outreach_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "email_delivery_events", sa.Column("reason_code", sa.String(100), nullable=True)
    )
    op.add_column(
        "email_delivery_events",
        sa.Column("event_data_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "email_delivery_events",
        sa.Column(
            "is_unknown_message",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    for column in ("tenant_id", "outreach_message_id", "is_unknown_message"):
        op.create_index(
            f"ix_email_delivery_events_{column}", "email_delivery_events", [column]
        )

    op.add_column(
        "nurture_outbox",
        sa.Column(
            "outreach_message_id",
            sa.Uuid(),
            sa.ForeignKey("outreach_messages.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_nurture_outbox_outreach_message_id",
        "nurture_outbox",
        ["outreach_message_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_nurture_outbox_outreach_message_id", table_name="nurture_outbox")
    op.drop_column("nurture_outbox", "outreach_message_id")

    for column in ("is_unknown_message", "outreach_message_id", "tenant_id"):
        op.drop_index(
            f"ix_email_delivery_events_{column}", table_name="email_delivery_events"
        )
    for column in (
        "is_unknown_message",
        "event_data_json",
        "reason_code",
        "outreach_message_id",
        "tenant_id",
    ):
        op.drop_column("email_delivery_events", column)

    op.drop_constraint(
        "ck_outreach_review_action", "outreach_message_reviews", type_="check"
    )
    op.create_check_constraint(
        "ck_outreach_review_action",
        "outreach_message_reviews",
        "action IN ('generated', 'revised', 'approved', 'rejected')",
    )

    for column in (
        "updated_at",
        "sent_at",
        "unsubscribe_token_hash",
        "provider_message_id",
        "provider",
        "scheduled_for",
    ):
        op.drop_index(f"ix_outreach_messages_{column}", table_name="outreach_messages")
    op.drop_constraint(
        "uq_outreach_provider_message", "outreach_messages", type_="unique"
    )
    op.drop_constraint(
        "uq_outreach_messages_send_idempotency_key", "outreach_messages", type_="unique"
    )
    op.drop_constraint(
        "ck_outreach_message_send_attempts", "outreach_messages", type_="check"
    )
    for column in (
        "last_error",
        "updated_at",
        "unsubscribed_at",
        "complained_at",
        "bounced_at",
        "clicked_at",
        "opened_at",
        "delivered_at",
        "sent_at",
        "unsubscribe_token_hash",
        "sent_headers",
        "sent_text_snapshot",
        "sent_html_snapshot",
        "sent_from_email",
        "sent_from_name",
        "sent_subject_snapshot",
        "provider_message_id",
        "provider",
        "sending_at",
        "send_attempts",
        "scheduled_for",
        "send_requested_at",
        "send_requested_by",
        "send_idempotency_key",
    ):
        op.drop_column("outreach_messages", column)
    op.drop_constraint("ck_outreach_message_status", "outreach_messages", type_="check")
    op.create_check_constraint(
        "ck_outreach_message_status",
        "outreach_messages",
        "status IN ('draft', 'pending_review', 'approved', 'rejected', 'cancelled')",
    )
    op.drop_table("outreach_delivery_policies")
