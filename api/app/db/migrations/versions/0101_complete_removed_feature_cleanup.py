"""Remove buyer scoring, retired external runtimes, and strategy-map storage.

Revision ID: 0101_removed_feature_cleanup
Revises: 0100_remove_copilot_ml_integrations
"""

import sqlalchemy as sa
from alembic import op

revision = "0101_removed_feature_cleanup"
down_revision = "0100_remove_copilot_ml_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM retirement_candidate_observations "
        "WHERE candidate_key = 'agentos_runtime'"
    )
    op.execute(
        "DELETE FROM operational_jobs "
        "WHERE job_type IN ('rfq_hubspot', 'rfq_agentos', 'rfq_webhook')"
    )
    op.execute(
        "UPDATE nurture_sequences SET trigger_type = 'manual', trigger_value = NULL "
        "WHERE trigger_type = 'intent_stage'"
    )
    op.execute(
        "UPDATE segments SET conditions = '[]' "
        "WHERE conditions LIKE '%\"intent_score\"%' "
        "OR conditions LIKE '%\"intent_stage\"%'"
    )

    op.drop_table("content_strategies")

    op.drop_index("ix_visitors_facet_product_interest", table_name="visitors")
    op.drop_index("ix_visitors_facet_trust_validation", table_name="visitors")
    op.drop_index("ix_visitors_facet_procurement_readiness", table_name="visitors")
    op.drop_index("ix_visitors_facet_urgency", table_name="visitors")
    op.drop_index("ix_visitors_intent_score", table_name="visitors")
    op.drop_index("ix_visitors_intent_stage", table_name="visitors")
    op.drop_constraint("ck_visitors_intent_stage", "visitors", type_="check")
    for column in (
        "intent_explanation",
        "facet_urgency",
        "facet_procurement_readiness",
        "facet_trust_validation",
        "facet_product_interest",
        "stage_alert_sent",
        "intent_stage",
        "intent_score",
    ):
        op.drop_column("visitors", column)

    op.drop_column("tracking_events", "score_delta")
    op.drop_column("contacts", "intent_score_at_creation")
    op.drop_column("contacts", "hubspot_contact_id")

    op.drop_index("ix_rfq_requests_agent_run_id", table_name="rfq_requests")
    for column in (
        "intent_score_at_submit",
        "intent_snapshot_json",
        "hubspot_deal_id",
        "agent_run_id",
        "agent_analysis_summary",
        "agent_draft_body",
    ):
        op.drop_column("rfq_requests", column)

    op.drop_column("ctas", "target_intent_stage")
    op.drop_column("site_profiles", "intent_scoring_config_json")
    op.drop_column("notification_preferences", "notify_hot_visitor")
    op.drop_column("notification_preferences", "notify_churn_risk")

    op.drop_constraint(
        "ck_growth_policy_min_intent_score",
        "growth_automation_policies",
        type_="check",
    )
    op.drop_column("growth_automation_policies", "min_intent_score")

    op.drop_constraint(
        "ck_journey_snapshot_intent_score", "journey_snapshots", type_="check"
    )
    op.drop_column("journey_snapshots", "intent_score")
    op.drop_column("journey_snapshots", "intent_stage")
    op.drop_column("journey_snapshots", "intent_facets")


def downgrade() -> None:
    op.add_column("journey_snapshots", sa.Column("intent_facets", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("journey_snapshots", sa.Column("intent_stage", sa.String(20), nullable=False, server_default="cold"))
    op.add_column("journey_snapshots", sa.Column("intent_score", sa.Integer(), nullable=False, server_default="0"))
    op.create_check_constraint("ck_journey_snapshot_intent_score", "journey_snapshots", "intent_score >= 0")
    op.add_column("growth_automation_policies", sa.Column("min_intent_score", sa.Integer(), nullable=False, server_default="40"))
    op.create_check_constraint("ck_growth_policy_min_intent_score", "growth_automation_policies", "min_intent_score >= 0")
    op.add_column("notification_preferences", sa.Column("notify_churn_risk", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("notification_preferences", sa.Column("notify_hot_visitor", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("site_profiles", sa.Column("intent_scoring_config_json", sa.Text(), nullable=True))
    op.add_column("ctas", sa.Column("target_intent_stage", sa.String(20), nullable=False, server_default="any"))
    op.add_column("rfq_requests", sa.Column("agent_draft_body", sa.Text(), nullable=True))
    op.add_column("rfq_requests", sa.Column("agent_analysis_summary", sa.String(2000), nullable=True))
    op.add_column("rfq_requests", sa.Column("agent_run_id", sa.String(100), nullable=True))
    op.create_index("ix_rfq_requests_agent_run_id", "rfq_requests", ["agent_run_id"])
    op.add_column("rfq_requests", sa.Column("hubspot_deal_id", sa.String(50), nullable=True))
    op.add_column("rfq_requests", sa.Column("intent_snapshot_json", sa.Text(), nullable=True))
    op.add_column("rfq_requests", sa.Column("intent_score_at_submit", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("contacts", sa.Column("hubspot_contact_id", sa.String(50), nullable=True))
    op.add_column("contacts", sa.Column("intent_score_at_creation", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("tracking_events", sa.Column("score_delta", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("visitors", sa.Column("intent_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("visitors", sa.Column("intent_stage", sa.String(20), nullable=False, server_default="cold"))
    op.add_column("visitors", sa.Column("stage_alert_sent", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("visitors", sa.Column("facet_product_interest", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("visitors", sa.Column("facet_trust_validation", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("visitors", sa.Column("facet_procurement_readiness", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("visitors", sa.Column("facet_urgency", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("visitors", sa.Column("intent_explanation", sa.Text(), nullable=True))
    op.create_check_constraint("ck_visitors_intent_stage", "visitors", "intent_stage IN ('cold','warm','hot','sales_ready')")
    op.create_index("ix_visitors_intent_score", "visitors", ["intent_score"])
    op.create_index("ix_visitors_intent_stage", "visitors", ["intent_stage"])
    op.create_index("ix_visitors_facet_product_interest", "visitors", ["facet_product_interest"])
    op.create_index("ix_visitors_facet_trust_validation", "visitors", ["facet_trust_validation"])
    op.create_index("ix_visitors_facet_procurement_readiness", "visitors", ["facet_procurement_readiness"])
    op.create_index("ix_visitors_facet_urgency", "visitors", ["facet_urgency"])

    op.create_table(
        "content_strategies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("page_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("locale", sa.String(5), nullable=False, server_default="en"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
