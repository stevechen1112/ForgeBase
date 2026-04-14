"""add tenant_id to pages

Revision ID: 0033_page_tenant_id
Revises: 0032_tracking_session_tenant
Create Date: 2026-04-12
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0033_page_tenant_id"
down_revision = "0032_tracking_session_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pages",
        sa.Column("tenant_id", sa.UUID(), nullable=True),
    )
    op.create_index("ix_pages_tenant_id", "pages", ["tenant_id"])
    op.create_foreign_key(
        "fk_pages_tenant_id",
        "pages",
        "tenants",
        ["tenant_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_pages_tenant_id", "pages", type_="foreignkey")
    op.drop_index("ix_pages_tenant_id", "pages")
    op.drop_column("pages", "tenant_id")
