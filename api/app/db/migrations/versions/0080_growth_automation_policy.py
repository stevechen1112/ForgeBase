"""Platform-controlled staged growth automation policy.

Revision ID: 0080_growth_automation_policy
Revises: 0079_company_identification_foundation
"""

import sqlalchemy as sa
from alembic import op

revision = "0080_growth_automation_policy"
down_revision = "0079_company_identification_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "growth_automation_policies",
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "company_identification_mode",
            sa.String(30),
            nullable=False,
            server_default="off",
        ),
        sa.Column("provider_name", sa.String(50), nullable=False, server_default="mock"),
        sa.Column("min_intent_score", sa.Integer(), nullable=False, server_default="40"),
        sa.Column("observation_retention_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("daily_lookup_quota", sa.Integer(), nullable=False, server_default="100"),
        sa.Column(
            "daily_provider_cost_limit",
            sa.Numeric(14, 6),
            nullable=False,
            server_default="10",
        ),
        sa.Column(
            "medium_confidence_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.7",
        ),
        sa.Column(
            "high_confidence_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.9",
        ),
        sa.Column("allowed_countries", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "company_identification_mode IN "
            "('off', 'shadow', 'review_only', 'approval_send', 'controlled_auto')",
            name="ck_growth_policy_company_identification_mode",
        ),
        sa.CheckConstraint("min_intent_score >= 0", name="ck_growth_policy_min_intent_score"),
        sa.CheckConstraint(
            "observation_retention_days >= 1 AND observation_retention_days <= 365",
            name="ck_growth_policy_observation_retention",
        ),
        sa.CheckConstraint("daily_lookup_quota >= 0", name="ck_growth_policy_daily_lookup_quota"),
        sa.CheckConstraint(
            "daily_provider_cost_limit >= 0",
            name="ck_growth_policy_daily_provider_cost_limit",
        ),
        sa.CheckConstraint(
            "medium_confidence_threshold >= 0 AND medium_confidence_threshold <= 1",
            name="ck_growth_policy_medium_confidence",
        ),
        sa.CheckConstraint(
            "high_confidence_threshold >= 0 AND high_confidence_threshold <= 1",
            name="ck_growth_policy_high_confidence",
        ),
        sa.CheckConstraint(
            "high_confidence_threshold >= medium_confidence_threshold",
            name="ck_growth_policy_confidence_order",
        ),
    )
    op.create_index(
        "ix_growth_automation_policies_company_identification_mode",
        "growth_automation_policies",
        ["company_identification_mode"],
    )


def downgrade() -> None:
    op.drop_table("growth_automation_policies")
