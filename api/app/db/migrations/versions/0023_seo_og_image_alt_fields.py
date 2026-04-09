"""0023_seo_og_image_alt_fields

Add og_image_url to products, product_categories, applications;
add image_alt to products.

Revision ID: 0023_seo_og_image_alt_fields
Revises: 0022_integration_credentials
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_seo_og_image_alt_fields"
down_revision = "0022_integration_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # products
    op.add_column("products", sa.Column("og_image_url", sa.String(500), nullable=True))
    op.add_column("products", sa.Column("image_alt", sa.String(200), nullable=True))

    # product_categories
    op.add_column("product_categories", sa.Column("og_image_url", sa.String(500), nullable=True))

    # applications
    op.add_column("applications", sa.Column("og_image_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("applications", "og_image_url")
    op.drop_column("product_categories", "og_image_url")
    op.drop_column("products", "image_alt")
    op.drop_column("products", "og_image_url")
