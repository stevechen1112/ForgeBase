"""0036_site_profile_flexible_shell

Add flexible site-shell and asset-manifest fields to site_profiles.

Revision ID: 0036_site_profile_flexible_shell
Revises: 0035_drop_global_slug_indexes
"""
from alembic import op
import sqlalchemy as sa

revision = "0036_site_profile_flexible_shell"
down_revision = "0035_drop_global_slug_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("site_profiles", sa.Column("header_nav_json", sa.Text(), nullable=True))
    op.add_column("site_profiles", sa.Column("header_actions_json", sa.Text(), nullable=True))
    op.add_column("site_profiles", sa.Column("footer_sections_json", sa.Text(), nullable=True))
    op.add_column("site_profiles", sa.Column("footer_badges_json", sa.Text(), nullable=True))
    op.add_column("site_profiles", sa.Column("social_links_json", sa.Text(), nullable=True))
    op.add_column("site_profiles", sa.Column("footer_cta_title", sa.String(length=200), nullable=True))
    op.add_column("site_profiles", sa.Column("footer_cta_description", sa.Text(), nullable=True))
    op.add_column("site_profiles", sa.Column("footer_cta_label", sa.String(length=120), nullable=True))
    op.add_column("site_profiles", sa.Column("footer_cta_href", sa.String(length=500), nullable=True))
    op.add_column("site_profiles", sa.Column("asset_manifest_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("site_profiles", "asset_manifest_json")
    op.drop_column("site_profiles", "footer_cta_href")
    op.drop_column("site_profiles", "footer_cta_label")
    op.drop_column("site_profiles", "footer_cta_description")
    op.drop_column("site_profiles", "footer_cta_title")
    op.drop_column("site_profiles", "social_links_json")
    op.drop_column("site_profiles", "footer_badges_json")
    op.drop_column("site_profiles", "footer_sections_json")
    op.drop_column("site_profiles", "header_actions_json")
    op.drop_column("site_profiles", "header_nav_json")
