"""Privacy governance and repeatable site provisioning.

Revision ID: 0063_privacy_and_site_provisioning
Revises: 0062_conversion_reliability
"""

import sqlalchemy as sa
from alembic import op

revision = "0063_privacy_and_site_provisioning"
down_revision = "0062_conversion_reliability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visitors", sa.Column("analytics_consent_status", sa.String(20), nullable=False, server_default="unknown"))
    op.add_column("visitors", sa.Column("consent_updated_at", sa.DateTime(), nullable=True))
    op.create_index("ix_visitors_analytics_consent_status", "visitors", ["analytics_consent_status"])

    op.create_table(
        "consent_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("visitor_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("source", sa.String(30), nullable=False, server_default="web"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for column in ("tenant_id", "visitor_hash", "status", "created_at"):
        op.create_index(f"ix_consent_records_{column}", "consent_records", [column])

    op.create_table(
        "site_builds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("template_key", sa.String(80), nullable=False, server_default="handtool-company"),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("primary_domain", sa.String(255), nullable=True),
        sa.Column("locales_json", sa.Text(), nullable=False, server_default='["en"]'),
        sa.Column("customization_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("cms_connected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("readiness_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_site_builds_tenant_id"),
    )
    for column in ("tenant_id", "template_key", "status"):
        op.create_index(f"ix_site_builds_{column}", "site_builds", [column])
    op.create_index(
        "ix_site_builds_primary_domain",
        "site_builds",
        ["primary_domain"],
        unique=True,
        postgresql_where=sa.text("primary_domain IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("site_builds")
    op.drop_table("consent_records")
    op.drop_index("ix_visitors_analytics_consent_status", table_name="visitors")
    op.drop_column("visitors", "consent_updated_at")
    op.drop_column("visitors", "analytics_consent_status")
