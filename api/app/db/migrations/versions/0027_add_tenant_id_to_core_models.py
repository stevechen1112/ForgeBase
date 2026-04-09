"""0027_add_tenant_id_to_core_models

Add tenant_id FK + index to 7 core tables for multi-tenant data isolation:
products, product_categories, contacts, rfq_requests, visitors, tracking_events, chat_sessions.
Also add slug column to tenants for future domain mapping.

Revision ID: 0027_add_tenant_id_to_core_models
Revises: 0026_tenants_and_user_tenant_id
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0027_add_tenant_id_to_core_models"
down_revision = "0026_tenants_and_user_tenant_id"
branch_labels = None
depends_on = None

TABLES = [
    "products",
    "product_categories",
    "contacts",
    "rfq_requests",
    "visitors",
    "tracking_events",
    "chat_sessions",
]


def upgrade() -> None:
    # 1. Add slug to tenants
    op.add_column("tenants", sa.Column("slug", sa.String(100), nullable=True))

    # Backfill slug from name (lowercase, spaces→hyphens)
    op.execute(
        "UPDATE tenants SET slug = LOWER(REPLACE(name, ' ', '-'))"
    )
    op.alter_column("tenants", "slug", nullable=False)
    op.create_unique_constraint("uq_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    # 2. Add tenant_id to 7 core tables
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        )

    # 3. Backfill: assign all existing rows to the default tenant
    op.execute(
        """
        DO $$
        DECLARE
            _tid UUID;
        BEGIN
            SELECT id INTO _tid FROM tenants ORDER BY created_at LIMIT 1;
            IF _tid IS NOT NULL THEN
                UPDATE products            SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE product_categories  SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE contacts            SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE rfq_requests        SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE visitors            SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE tracking_events     SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE chat_sessions       SET tenant_id = _tid WHERE tenant_id IS NULL;
            END IF;
        END $$;
        """
    )

    # 4. Add FK + index
    for table in TABLES:
        op.create_foreign_key(
            f"fk_{table}_tenant_id",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")

    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_constraint("uq_tenants_slug", "tenants", type_="unique")
    op.drop_column("tenants", "slug")
