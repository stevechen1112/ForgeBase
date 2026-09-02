"""Realign RFQ lifecycle to website-to-human handoff.

Revision ID: 0102_realign_rfq_to_handoff_scope
Revises: 0101_removed_feature_cleanup

Removes CRM sales outcomes, revenue attribution, follow-up scheduling and buyer
scoring.  Historical sales values must be exported before production upgrade;
this migration deliberately does not retain a hidden runtime archive table.
"""

import sqlalchemy as sa
from alembic import op

revision = "0102_realign_rfq_to_handoff_scope"
down_revision = "0101_removed_feature_cleanup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "rfq_requests",
        "attribution_json",
        new_column_name="source_context_json",
    )
    op.add_column("rfq_requests", sa.Column("acknowledgement_sent_at", sa.DateTime(), nullable=True))
    op.add_column("rfq_requests", sa.Column("accepted_at", sa.DateTime(), nullable=True))
    op.add_column("rfq_requests", sa.Column("first_verified_response_at", sa.DateTime(), nullable=True))
    op.add_column("rfq_requests", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.add_column("rfq_requests", sa.Column("acceptance_due_at", sa.DateTime(), nullable=True))
    op.add_column(
        "rfq_requests",
        sa.Column(
            "acceptance_sla_breached",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index("ix_rfq_requests_accepted_at", "rfq_requests", ["accepted_at"])
    op.create_index("ix_rfq_requests_archived_at", "rfq_requests", ["archived_at"])
    op.create_index("ix_rfq_requests_acceptance_due_at", "rfq_requests", ["acceptance_due_at"])

    # Preserve only evidence that remains meaningful in the handoff product.
    op.execute(
        """
        UPDATE rfq_requests
        SET acceptance_due_at = sla_due_at,
            acceptance_sla_breached = sla_breached,
            accepted_at = CASE
                WHEN status IN ('in_progress', 'quoted', 'negotiation', 'won', 'lost', 'expired')
                THEN COALESCE(first_response_at, quote_sent_at, updated_at)
                ELSE NULL
            END,
            archived_at = CASE
                WHEN status IN ('quoted', 'negotiation', 'won', 'lost', 'expired')
                THEN COALESCE(closed_at, quote_sent_at, updated_at)
                ELSE NULL
            END
        """
    )
    op.execute(
        """
        UPDATE rfq_requests
        SET acceptance_sla_breached = TRUE
        WHERE acceptance_due_at IS NOT NULL
          AND (
            (accepted_at IS NOT NULL AND accepted_at > acceptance_due_at)
            OR (status = 'assigned' AND accepted_at IS NULL AND acceptance_due_at < NOW())
          )
        """
    )
    op.execute(
        """
        UPDATE rfq_requests AS r
        SET acknowledgement_sent_at = ack.first_ack
        FROM (
            SELECT rfq_id, MIN(created_at) AS first_ack
            FROM rfq_events
            WHERE event_type IN ('auto_reply_sent', 'acknowledgement_sent')
            GROUP BY rfq_id
        ) AS ack
        WHERE r.id = ack.rfq_id
        """
    )

    op.drop_constraint("ck_rfq_status", "rfq_requests", type_="check")
    op.execute(
        """
        UPDATE rfq_requests
        SET status = CASE
            WHEN status = 'new' THEN 'new'
            WHEN status = 'assigned' THEN 'assigned'
            WHEN status = 'in_progress' THEN 'accepted'
            ELSE 'archived'
        END
        """
    )
    op.create_check_constraint(
        "ck_rfq_status",
        "rfq_requests",
        "status IN ('new','assigned','accepted','archived')",
    )

    # An inbound-email handoff also stops at explicit human acceptance. Merely
    # opening an external mail client cannot prove that contact occurred.
    op.drop_constraint("ck_sales_handoff_status", "sales_handoffs", type_="check")
    op.execute(
        "UPDATE sales_handoffs SET status = 'accepted' WHERE status = 'in_progress'"
    )
    op.create_check_constraint(
        "ck_sales_handoff_status",
        "sales_handoffs",
        "status IN ('new','accepted','converted_to_rfq','closed')",
    )
    op.drop_constraint(
        "ck_sales_handoff_event_action", "sales_handoff_events", type_="check"
    )
    op.execute(
        "UPDATE sales_handoff_events SET action = 'accepted' "
        "WHERE action IN ('started', 'contacted')"
    )
    op.create_check_constraint(
        "ck_sales_handoff_event_action",
        "sales_handoff_events",
        "action IN ('created','accepted','assigned','linked_rfq','created_rfq',"
        "'marked_wrong_person','unsubscribed','closed')",
    )

    op.drop_index("ix_rfq_requests_quality_score", table_name="rfq_requests")
    op.drop_index("ix_rfq_requests_sla_due_at", table_name="rfq_requests")
    op.drop_index("ix_rfq_requests_next_follow_up_at", table_name="rfq_requests")

    for column in (
        "quality_reasons_json",
        "quality_score",
        "first_response_at",
        "quote_sent_at",
        "next_follow_up_at",
        "lost_reason",
        "won_reason",
        "deal_amount",
        "deal_currency",
        "sla_due_at",
        "sla_breached",
        "closed_at",
    ):
        op.drop_column("rfq_requests", column)

    # These tables implement outreach/RFQ/outcome attribution. First-party
    # traffic source remains in tracking events and rfq_requests.source_context_json.
    op.drop_table("attribution_events")
    op.drop_table("attribution_links")

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            UPDATE site_profiles
            SET ops_config_json = (
                (ops_config_json::jsonb - 'sla_response_hours') ||
                CASE
                    WHEN ops_config_json::jsonb ? 'sla_acceptance_hours' THEN '{}'::jsonb
                    ELSE jsonb_build_object(
                        'sla_acceptance_hours',
                        ops_config_json::jsonb -> 'sla_response_hours'
                    )
                END
            )::text
            WHERE ops_config_json IS NOT NULL
              AND ops_config_json::jsonb ? 'sla_response_hours'
            """
        )
        op.execute(
            """
            UPDATE tenants
            SET feature_overrides = (
                COALESCE(feature_overrides::jsonb, '{}'::jsonb)
                - 'outcomes_dashboard' - 'closed_loop_attribution'
            )::json
            WHERE COALESCE(feature_overrides::jsonb, '{}'::jsonb)
                ?| ARRAY['outcomes_dashboard', 'closed_loop_attribution']
            """
        )


def downgrade() -> None:
    raise RuntimeError(
        "0102 is an intentional destructive product-scope retirement. "
        "Restore the pre-deployment database backup instead of downgrading in place."
    )
