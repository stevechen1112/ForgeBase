"""0057_products_image_url

Add image_url to products. The column exists in the Product model (and is
used by admin forms + public product pages) but was never created by any
migration — every products query would 500 on a fresh DB.

Revision ID: 0057_products_image_url
Revises: 0056_translation_glossary
"""
from alembic import op
import sqlalchemy as sa


revision = "0057_products_image_url"
down_revision = "0056_translation_glossary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dev DBs created via SQLModel create_all already have this column;
    # production DBs driven by alembic do not. Skip if present.
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("products")]
    if "image_url" not in columns:
        op.add_column(
            "products",
            sa.Column("image_url", sa.String(length=500), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("products")]
    if "image_url" in columns:
        op.drop_column("products", "image_url")
