"""0035_drop_global_slug_indexes

Drop global (non-tenant-scoped) unique slug indexes that conflict with
multi-tenant design.  The composite unique constraints (slug + locale +
tenant_id) added in earlier migrations are the canonical uniqueness
boundaries; global slug uniqueness would prevent two separate tenants
from using the same slug, which contradicts the white-label model.

Revision ID: 0035_drop_global_slug_indexes
Revises: 0034_multitenant_content_phase3
"""
from alembic import op

revision = "0035_drop_global_slug_indexes"
down_revision = "0034_multitenant_content_phase3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # product_categories: global slug uniqueness replaced by
    # uq_product_categories_slug_locale_tenant (added in 0034)
    op.execute(
        "DROP INDEX IF EXISTS ix_product_categories_slug"
    )


def downgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_product_categories_slug "
        "ON product_categories (slug)"
    )
