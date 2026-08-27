"""Add per-tenant frontend copy overrides.

Revision ID: 0067_site_profile_tenant_copy
Revises: 0066_asset_locale_content_repairs
"""
import sqlalchemy as sa
from alembic import op

revision = "0067_site_profile_tenant_copy"
down_revision = "0066_asset_locale_repairs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("site_profiles", sa.Column("site_copy_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("site_profiles", "site_copy_json")
