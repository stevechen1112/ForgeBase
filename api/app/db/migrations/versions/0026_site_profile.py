"""0026_site_profile

Create table for per-site brand / theme configuration.

Revision ID: 0026_site_profile
Revises: 0025_legacy_site_intake
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_site_profile"
down_revision = "0025_legacy_site_intake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_name", sa.String(120), nullable=False, server_default="NorthForge Tools"),
        sa.Column("logo_mark", sa.String(10), nullable=False, server_default="NF"),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("favicon_url", sa.String(500), nullable=True),
        sa.Column("theme_key", sa.String(30), nullable=False, server_default="cobalt"),
        sa.Column("contact_email", sa.String(200), nullable=False, server_default="sales@northforgetools.com"),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("site_url", sa.String(500), nullable=False, server_default="https://example.com"),
        sa.Column("default_locale", sa.String(5), nullable=False, server_default="en"),
        sa.Column("asset_base", sa.String(500), nullable=True),
        sa.Column("demo_company_folder", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("site_profiles")
