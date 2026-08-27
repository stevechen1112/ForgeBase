"""Add tenant ownership to content assets and backfill tenant credentials.

Revision ID: 0061_content_asset_tenant_scope
Revises: 0060_drop_global_slug_unique_indexes
"""
import sqlalchemy as sa
from alembic import op

revision = "0061_content_asset_tenant_scope"
down_revision = "0060_drop_global_slug_unique_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("locale", sa.String(length=10), nullable=True))
    op.execute("UPDATE chat_sessions SET locale = 'en' WHERE locale IS NULL")
    op.alter_column("chat_sessions", "locale", nullable=False, server_default="en")
    op.add_column(
        "content_assets",
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_content_assets_tenant_id",
        "content_assets",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_content_assets_tenant_id",
        "content_assets",
        ["tenant_id"],
    )

    # Existing assets inherit the uploader's tenant. Refuse to leave ambiguous
    # global assets behind: an operator must repair such rows before migrating.
    op.execute(
        """
        UPDATE content_assets AS asset
        SET tenant_id = users.tenant_id
        FROM users
        WHERE asset.uploaded_by = users.id
          AND asset.tenant_id IS NULL
        """
    )
    connection = op.get_bind()
    orphan_count = connection.execute(
        sa.text("SELECT count(*) FROM content_assets WHERE tenant_id IS NULL")
    ).scalar_one()
    if orphan_count:
        raise RuntimeError(
            f"Cannot tenant-scope {orphan_count} content asset(s); repair uploaded_by ownership first"
        )
    op.alter_column("content_assets", "tenant_id", nullable=False)

    # The credential table historically allowed global rows. When exactly one
    # tenant exists, safely assign those rows to it. Multi-tenant installations
    # must explicitly migrate global credentials instead of sharing secrets.
    tenant_count = connection.execute(sa.text("SELECT count(*) FROM tenants")).scalar_one()
    global_credential_count = connection.execute(
        sa.text("SELECT count(*) FROM integration_credentials WHERE tenant_id IS NULL")
    ).scalar_one()
    if global_credential_count and tenant_count != 1:
        raise RuntimeError(
            "Global integration credentials require explicit tenant assignment"
        )
    if global_credential_count:
        op.execute(
            """
            UPDATE integration_credentials
            SET tenant_id = (SELECT id::text FROM tenants LIMIT 1)
            WHERE tenant_id IS NULL
            """
        )


def downgrade() -> None:
    op.drop_index("ix_content_assets_tenant_id", table_name="content_assets")
    op.drop_constraint(
        "fk_content_assets_tenant_id",
        "content_assets",
        type_="foreignkey",
    )
    op.drop_column("content_assets", "tenant_id")
    op.drop_column("chat_sessions", "locale")
