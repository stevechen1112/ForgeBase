"""Inbound reply receipt, safe classification and human sales handoff.

Revision ID: 0084_inbound_reply_sales_handoff
Revises: 0083_outreach_approval_send
"""

import sqlalchemy as sa
from alembic import op

revision = "0084_inbound_reply_sales_handoff"
down_revision = "0083_outreach_approval_send"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inbound_reply_policies",
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("mode", sa.String(20), nullable=False, server_default="off"),
        sa.Column(
            "handoff_sla_hours", sa.Integer(), nullable=False, server_default="4"
        ),
        sa.Column(
            "content_retention_days", sa.Integer(), nullable=False, server_default="90"
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
            "mode IN ('off', 'review_only')", name="ck_inbound_reply_policy_mode"
        ),
        sa.CheckConstraint(
            "handoff_sla_hours >= 1 AND handoff_sla_hours <= 168",
            name="ck_inbound_reply_handoff_sla",
        ),
        sa.CheckConstraint(
            "content_retention_days >= 1 AND content_retention_days <= 365",
            name="ck_inbound_reply_retention",
        ),
    )
    op.create_index(
        "ix_inbound_reply_policies_mode", "inbound_reply_policies", ["mode"]
    )

    op.add_column(
        "outreach_messages",
        sa.Column("sent_reply_to", sa.String(320), nullable=True),
    )
    op.add_column(
        "outreach_messages",
        sa.Column("reply_route_token_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_outreach_messages_reply_route_token_hash",
        "outreach_messages",
        ["reply_route_token_hash"],
        unique=True,
    )
    op.drop_constraint("ck_outreach_message_status", "outreach_messages", type_="check")
    op.create_check_constraint(
        "ck_outreach_message_status",
        "outreach_messages",
        "status IN ('draft', 'pending_review', 'approved', 'rejected', 'cancelled', "
        "'queued', 'sending', 'sent', 'delivered', 'opened', 'clicked', 'replied', "
        "'bounced', 'complained', 'unsubscribed', 'failed')",
    )

    op.create_table(
        "inbound_replies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "outreach_message_id",
            sa.Uuid(),
            sa.ForeignKey("outreach_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "parent_reply_id",
            sa.Uuid(),
            sa.ForeignKey("inbound_replies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(20), nullable=False, server_default="resend"),
        sa.Column("provider_event_id", sa.String(120), nullable=False),
        sa.Column("provider_email_id", sa.String(120), nullable=False),
        sa.Column("rfc_message_id", sa.String(500), nullable=True),
        sa.Column("in_reply_to", sa.String(500), nullable=True),
        sa.Column(
            "references", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("sender_email_ciphertext", sa.Text(), nullable=False),
        sa.Column("sender_email_hash", sa.String(64), nullable=False),
        sa.Column("sender_email_masked", sa.String(254), nullable=False),
        sa.Column("route_address_hash", sa.String(64), nullable=True),
        sa.Column("subject_ciphertext", sa.Text(), nullable=False),
        sa.Column("body_text_ciphertext", sa.Text(), nullable=True),
        sa.Column("body_sha256", sa.String(64), nullable=True),
        sa.Column("body_char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "attachment_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("attachment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "attachment_total_bytes",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "attachments_quarantined",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "classification", sa.String(30), nullable=False, server_default="unknown"
        ),
        sa.Column(
            "classification_confidence", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column(
            "classification_reasons",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="fetch_pending"
        ),
        sa.Column(
            "stops_automation", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "needs_human_review", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("processing_error", sa.String(2000), nullable=True),
        sa.Column("raw_payload_sha256", sa.String(64), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.Column("classified_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("content_redacted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "provider", "provider_event_id", name="uq_inbound_reply_provider_event"
        ),
        sa.UniqueConstraint(
            "provider", "provider_email_id", name="uq_inbound_reply_provider_email"
        ),
        sa.CheckConstraint(
            "status IN ('fetch_pending', 'processing', 'classified', 'needs_review', "
            "'handed_off', 'ignored', 'failed')",
            name="ck_inbound_reply_status",
        ),
        sa.CheckConstraint(
            "classification IN ('unknown', 'positive', 'question', 'rfq', 'not_now', "
            "'wrong_person', 'unsubscribe', 'negative', 'auto_reply', 'bounce')",
            name="ck_inbound_reply_classification",
        ),
        sa.CheckConstraint(
            "classification_confidence >= 0 AND classification_confidence <= 1",
            name="ck_inbound_reply_confidence",
        ),
        sa.CheckConstraint(
            "body_char_count >= 0 AND attachment_count >= 0 AND attachment_total_bytes >= 0",
            name="ck_inbound_reply_nonnegative_counts",
        ),
    )
    for column in (
        "tenant_id",
        "outreach_message_id",
        "parent_reply_id",
        "provider",
        "provider_event_id",
        "provider_email_id",
        "rfc_message_id",
        "in_reply_to",
        "sender_email_hash",
        "route_address_hash",
        "attachments_quarantined",
        "classification",
        "status",
        "stops_automation",
        "needs_human_review",
        "received_at",
        "expires_at",
        "content_redacted_at",
        "created_at",
        "updated_at",
    ):
        op.create_index(f"ix_inbound_replies_{column}", "inbound_replies", [column])

    op.create_table(
        "sales_handoffs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "inbound_reply_id",
            sa.Uuid(),
            sa.ForeignKey("inbound_replies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "outreach_message_id",
            sa.Uuid(),
            sa.ForeignKey("outreach_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rfq_id",
            sa.Uuid(),
            sa.ForeignKey("rfq_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="new"),
        sa.Column("priority", sa.String(10), nullable=False, server_default="normal"),
        sa.Column("classification", sa.String(30), nullable=False),
        sa.Column("summary", sa.String(1000), nullable=False),
        sa.Column("sla_due_at", sa.DateTime(), nullable=False),
        sa.Column(
            "sla_breached", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("inbound_reply_id", name="uq_sales_handoff_inbound_reply"),
        sa.CheckConstraint(
            "status IN ('new', 'accepted', 'in_progress', 'converted_to_rfq', 'closed')",
            name="ck_sales_handoff_status",
        ),
        sa.CheckConstraint(
            "priority IN ('normal', 'high', 'urgent')",
            name="ck_sales_handoff_priority",
        ),
    )
    for column in (
        "tenant_id",
        "inbound_reply_id",
        "outreach_message_id",
        "rfq_id",
        "owner_id",
        "status",
        "priority",
        "classification",
        "sla_due_at",
        "sla_breached",
        "created_at",
        "updated_at",
    ):
        op.create_index(f"ix_sales_handoffs_{column}", "sales_handoffs", [column])

    op.create_table(
        "sales_handoff_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sales_handoff_id",
            sa.Uuid(),
            sa.ForeignKey("sales_handoffs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("note", sa.String(2000), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "action IN ('created', 'accepted', 'assigned', 'started', 'linked_rfq', "
            "'created_rfq', 'contacted', 'marked_wrong_person', 'unsubscribed', 'closed')",
            name="ck_sales_handoff_event_action",
        ),
    )
    for column in (
        "tenant_id",
        "sales_handoff_id",
        "actor_user_id",
        "action",
        "created_at",
    ):
        op.create_index(
            f"ix_sales_handoff_events_{column}", "sales_handoff_events", [column]
        )


def downgrade() -> None:
    op.drop_table("sales_handoff_events")
    op.drop_table("sales_handoffs")
    op.drop_table("inbound_replies")

    op.drop_constraint("ck_outreach_message_status", "outreach_messages", type_="check")
    op.create_check_constraint(
        "ck_outreach_message_status",
        "outreach_messages",
        "status IN ('draft', 'pending_review', 'approved', 'rejected', 'cancelled', "
        "'queued', 'sending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', "
        "'complained', 'unsubscribed', 'failed')",
    )
    op.drop_index(
        "ix_outreach_messages_reply_route_token_hash", table_name="outreach_messages"
    )
    op.drop_column("outreach_messages", "reply_route_token_hash")
    op.drop_column("outreach_messages", "sent_reply_to")
    op.drop_table("inbound_reply_policies")
