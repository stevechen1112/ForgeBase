"""Closed-loop North Star attribution lineage.

Revision ID: 0085_closed_loop_attribution
Revises: 0084_inbound_reply_sales_handoff
"""

import sqlalchemy as sa
from alembic import op

revision = "0085_closed_loop_attribution"
down_revision = "0084_inbound_reply_sales_handoff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "outreach_delivery_policies",
        sa.Column("controlled_auto_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "outreach_delivery_policies",
        sa.Column("controlled_auto_legal_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    for column in (
        "controlled_auto_allowed_regions",
        "controlled_auto_allowed_personas",
        "controlled_auto_allowed_templates",
    ):
        op.add_column(
            "outreach_delivery_policies",
            sa.Column(column, sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        )
    op.add_column(
        "outreach_delivery_policies",
        sa.Column("controlled_auto_review_sample_pct", sa.Integer(), nullable=False, server_default="100"),
    )
    op.add_column(
        "outreach_delivery_policies",
        sa.Column("controlled_auto_reviewed_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "outreach_delivery_policies",
        sa.Column("controlled_auto_reviewed_at", sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        "fk_outreach_delivery_auto_reviewer",
        "outreach_delivery_policies",
        "users",
        ["controlled_auto_reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_outreach_auto_review_sample",
        "outreach_delivery_policies",
        "controlled_auto_review_sample_pct >= 1 AND controlled_auto_review_sample_pct <= 100",
    )

    op.create_table(
        "attribution_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("rfq_request_id", sa.Uuid(), nullable=False),
        sa.Column("visitor_id", sa.Uuid(), nullable=True),
        sa.Column("company_identification_id", sa.Uuid(), nullable=True),
        sa.Column("contact_candidate_id", sa.Uuid(), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("journey_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("outreach_message_id", sa.Uuid(), nullable=True),
        sa.Column("inbound_reply_id", sa.Uuid(), nullable=True),
        sa.Column("sales_handoff_id", sa.Uuid(), nullable=True),
        sa.Column("attribution_type", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("derivation_version", sa.String(length=80), nullable=False, server_default="north-star-attribution-v1"),
        sa.Column("manually_overridden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("override_reason", sa.String(length=2000), nullable=True),
        sa.Column("overridden_by", sa.Uuid(), nullable=True),
        sa.Column("overridden_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rfq_request_id"], ["rfq_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_identification_id"], ["company_identifications.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contact_candidate_id"], ["contact_candidates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["journey_snapshot_id"], ["journey_snapshots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["outreach_message_id"], ["outreach_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inbound_reply_id"], ["inbound_replies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sales_handoff_id"], ["sales_handoffs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["overridden_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rfq_request_id", name="uq_attribution_link_rfq"),
        sa.CheckConstraint("attribution_type IN ('direct', 'assisted', 'unknown', 'manual')", name="ck_attribution_link_type"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_attribution_link_confidence"),
    )
    for column in (
        "tenant_id", "rfq_request_id", "visitor_id", "company_identification_id",
        "contact_candidate_id", "contact_id", "journey_snapshot_id", "outreach_message_id",
        "inbound_reply_id", "sales_handoff_id", "attribution_type", "manually_overridden",
        "overridden_by", "created_at", "updated_at",
    ):
        op.create_index(f"ix_attribution_links_{column}", "attribution_links", [column])

    op.create_table(
        "attribution_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("attribution_link_id", sa.Uuid(), nullable=False),
        sa.Column("rfq_request_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("previous_type", sa.String(length=20), nullable=True),
        sa.Column("attribution_type", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(length=2000), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attribution_link_id"], ["attribution_links.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rfq_request_id"], ["rfq_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("action IN ('derived', 'recalculated', 'manual_override', 'outcome_changed')", name="ck_attribution_event_action"),
        sa.CheckConstraint("previous_type IS NULL OR previous_type IN ('direct', 'assisted', 'unknown', 'manual')", name="ck_attribution_event_previous_type"),
        sa.CheckConstraint("attribution_type IN ('direct', 'assisted', 'unknown', 'manual')", name="ck_attribution_event_type"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_attribution_event_confidence"),
    )
    for column in (
        "tenant_id", "attribution_link_id", "rfq_request_id", "actor_user_id",
        "action", "attribution_type", "created_at",
    ):
        op.create_index(f"ix_attribution_events_{column}", "attribution_events", [column])


def downgrade() -> None:
    op.drop_table("attribution_events")
    op.drop_table("attribution_links")
    op.drop_constraint(
        "ck_outreach_auto_review_sample",
        "outreach_delivery_policies",
        type_="check",
    )
    op.drop_constraint(
        "fk_outreach_delivery_auto_reviewer",
        "outreach_delivery_policies",
        type_="foreignkey",
    )
    for column in (
        "controlled_auto_reviewed_at",
        "controlled_auto_reviewed_by",
        "controlled_auto_review_sample_pct",
        "controlled_auto_allowed_templates",
        "controlled_auto_allowed_personas",
        "controlled_auto_allowed_regions",
        "controlled_auto_legal_approved",
        "controlled_auto_opt_in",
    ):
        op.drop_column("outreach_delivery_policies", column)
