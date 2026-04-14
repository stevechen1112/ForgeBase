"""0034_multitenant_content_phase3

Add tenant_id to the remaining content tables, backfill tenant ownership,
add tenant-aware unique constraints, and introduce site_profiles.layout_key.

Revision ID: 0034_multitenant_content_phase3
Revises: 0033_page_tenant_id
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0034_multitenant_content_phase3"
down_revision = "0033_page_tenant_id"
branch_labels = None
depends_on = None


_ADD_TENANT_ID_TABLES = [
    "applications",
    "faq_items",
    "comparison_topics",
    "capabilities",
    "certifications",
    "ctas",
    "ai_generation_logs",
]

_BACKFILL_TABLES = [
    "applications",
    "faq_items",
    "comparison_topics",
    "capabilities",
    "certifications",
    "ctas",
    "ai_generation_logs",
    "products",
    "product_categories",
    "pages",
    "site_profiles",
]


def _drop_constraint_if_exists(table: str, constraint: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{constraint}'
                  AND conrelid = '{table}'::regclass
            ) THEN
                ALTER TABLE {table} DROP CONSTRAINT {constraint};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    for table in _ADD_TENANT_ID_TABLES:
        op.add_column(table, sa.Column("tenant_id", UUID(as_uuid=True), nullable=True))

    op.add_column(
        "site_profiles",
        sa.Column("layout_key", sa.String(length=30), nullable=False, server_default="classic"),
    )

    op.execute(
        """
        DO $$
        DECLARE
            _tid UUID;
        BEGIN
            SELECT id INTO _tid FROM tenants ORDER BY created_at LIMIT 1;
            IF _tid IS NOT NULL THEN
                UPDATE applications      SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE faq_items         SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE comparison_topics SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE capabilities      SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE certifications    SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE ctas              SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE ai_generation_logs SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE products          SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE product_categories SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE pages             SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE site_profiles     SET tenant_id = _tid WHERE tenant_id IS NULL;
            END IF;

            UPDATE site_profiles
            SET layout_key = CASE
                WHEN theme_key = 'industrial' THEN 'industrial'
                ELSE 'classic'
            END
            WHERE layout_key IS NULL OR layout_key = 'classic';
        END $$;
        """
    )

    op.alter_column("site_profiles", "layout_key", server_default=None)

    for table in _ADD_TENANT_ID_TABLES:
        op.create_foreign_key(
            f"fk_{table}_tenant_id",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    _drop_constraint_if_exists("applications", "uq_applications_slug_locale")
    _drop_constraint_if_exists("certifications", "uq_certifications_slug_locale")
    _drop_constraint_if_exists("products", "uq_products_slug_locale")
    _drop_constraint_if_exists("product_categories", "product_categories_slug_key")
    _drop_constraint_if_exists("pages", "pages_slug_key")
    _drop_constraint_if_exists("comparison_topics", "comparison_topics_slug_key")
    _drop_constraint_if_exists("capabilities", "capabilities_slug_key")
    _drop_constraint_if_exists("ctas", "ctas_cta_key_key")
    _drop_constraint_if_exists("products", "products_model_number_key")

    op.create_unique_constraint(
        "uq_applications_slug_locale_tenant",
        "applications",
        ["slug", "locale", "tenant_id"],
    )
    op.create_unique_constraint(
        "uq_certifications_slug_locale_tenant",
        "certifications",
        ["slug", "locale", "tenant_id"],
    )
    op.create_unique_constraint(
        "uq_products_slug_locale_tenant",
        "products",
        ["slug", "locale", "tenant_id"],
    )
    op.create_unique_constraint(
        "uq_products_model_number_tenant",
        "products",
        ["model_number", "tenant_id"],
    )
    op.create_unique_constraint(
        "uq_product_categories_slug_locale_tenant",
        "product_categories",
        ["slug", "locale", "tenant_id"],
    )
    op.create_unique_constraint(
        "uq_pages_slug_locale_tenant",
        "pages",
        ["slug", "locale", "tenant_id"],
    )
    op.create_unique_constraint(
        "uq_comparison_topics_slug_locale_tenant",
        "comparison_topics",
        ["slug", "locale", "tenant_id"],
    )
    op.create_unique_constraint(
        "uq_capabilities_slug_locale_tenant",
        "capabilities",
        ["slug", "locale", "tenant_id"],
    )
    op.create_unique_constraint(
        "uq_ctas_key_locale_tenant",
        "ctas",
        ["cta_key", "locale", "tenant_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_ctas_key_locale_tenant", "ctas", type_="unique")
    op.drop_constraint("uq_capabilities_slug_locale_tenant", "capabilities", type_="unique")
    op.drop_constraint("uq_comparison_topics_slug_locale_tenant", "comparison_topics", type_="unique")
    op.drop_constraint("uq_pages_slug_locale_tenant", "pages", type_="unique")
    op.drop_constraint("uq_product_categories_slug_locale_tenant", "product_categories", type_="unique")
    op.drop_constraint("uq_products_model_number_tenant", "products", type_="unique")
    op.drop_constraint("uq_products_slug_locale_tenant", "products", type_="unique")
    op.drop_constraint("uq_certifications_slug_locale_tenant", "certifications", type_="unique")
    op.drop_constraint("uq_applications_slug_locale_tenant", "applications", type_="unique")

    op.create_unique_constraint("uq_applications_slug_locale", "applications", ["slug", "locale"])
    op.create_unique_constraint("uq_certifications_slug_locale", "certifications", ["slug", "locale"])
    op.create_unique_constraint("uq_products_slug_locale", "products", ["slug", "locale"])
    op.create_unique_constraint("products_model_number_key", "products", ["model_number"])
    op.create_unique_constraint("product_categories_slug_key", "product_categories", ["slug"])
    op.create_unique_constraint("pages_slug_key", "pages", ["slug"])
    op.create_unique_constraint("comparison_topics_slug_key", "comparison_topics", ["slug"])
    op.create_unique_constraint("capabilities_slug_key", "capabilities", ["slug"])
    op.create_unique_constraint("ctas_cta_key_key", "ctas", ["cta_key"])

    op.drop_column("site_profiles", "layout_key")

    for table in reversed(_ADD_TENANT_ID_TABLES):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")