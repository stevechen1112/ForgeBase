"""0024_redirects_table

Create redirects table for SEO 301/302 slug-change management.

Revision ID: 0024_redirects_table
Revises: 0023_seo_og_image_alt_fields
"""
import sqlalchemy as sa
from alembic import op

revision = "0024_redirects_table"
down_revision = "0023_seo_og_image_alt_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "redirects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("from_path", sa.String(500), nullable=False),
        sa.Column("to_path", sa.String(500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="301"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_path", name="uq_redirects_from_path"),
    )
    op.create_index("ix_redirects_from_path", "redirects", ["from_path"])
    op.create_index("ix_redirects_is_active", "redirects", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_redirects_is_active", table_name="redirects")
    op.drop_index("ix_redirects_from_path", table_name="redirects")
    op.drop_table("redirects")
