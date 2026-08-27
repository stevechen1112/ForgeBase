"""Tenant product-stage presets and feature overrides.

Revision ID: 0075_tenant_feature_entitlements
Revises: 0074_backfill_legacy_content_tenant
"""

import sqlalchemy as sa
from alembic import op

revision = "0075_tenant_feature_entitlements"
down_revision = "0074_backfill_legacy_content_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("product_stage", sa.String(30), nullable=False, server_default="phase1"),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "feature_overrides",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "feature_overrides")
    op.drop_column("tenants", "product_stage")
