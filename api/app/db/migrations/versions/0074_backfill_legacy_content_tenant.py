"""Assign pre-multitenant website content to the original default tenant.

Revision ID: 0074_backfill_legacy_content_tenant
Revises: 0073_backfill_published_delivery_stage
"""

from alembic import op

revision = "0074_backfill_legacy_content_tenant"
down_revision = "0073_backfill_published_delivery_stage"
branch_labels = None
depends_on = None


_CONTENT_TABLES = (
    "applications",
    "faq_items",
    "comparison_topics",
    "certifications",
    "capabilities",
    "ctas",
    "pages",
    "products",
    "product_categories",
)


def upgrade() -> None:
    # Content created before tenant support belonged to the original
    # NorthForge/default website.  Keeping it tenant-less would make the same
    # rows appear in every authenticated tenant console.
    for table in _CONTENT_TABLES:
        op.execute(
            f"""
            UPDATE {table}
            SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default-tenant' LIMIT 1)
            WHERE tenant_id IS NULL
              AND EXISTS (SELECT 1 FROM tenants WHERE slug = 'default-tenant')
            """
        )


def downgrade() -> None:
    # Tenant ownership is a security boundary and must not be erased by a
    # code rollback.
    pass
