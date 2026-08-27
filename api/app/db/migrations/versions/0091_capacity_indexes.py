"""Add hot-path indexes for public reads and durable queue claims.

Revision ID: 0091_capacity_indexes
Revises: 0090_durable_knowledge_sync_claims
"""

from alembic import op

revision = "0091_capacity_indexes"
down_revision = "0090_durable_knowledge_sync_claims"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX ix_products_public_listing
        ON products (
            tenant_id,
            locale,
            status,
            display_priority DESC,
            product_name ASC
        )
        """
    )
    op.create_index(
        "ix_content_assets_product_gallery",
        "content_assets",
        ["tenant_id", "product_id", "asset_type", "display_order", "created_at"],
    )
    op.execute(
        """
        CREATE INDEX ix_operational_jobs_ready_claim
        ON operational_jobs (available_at)
        WHERE status IN ('pending', 'retry')
        """
    )
    op.execute(
        """
        CREATE INDEX ix_operational_jobs_stale_claim
        ON operational_jobs (locked_at)
        WHERE status = 'processing'
        """
    )
    op.execute(
        """
        CREATE INDEX ix_knowledge_sync_jobs_ready_claim
        ON knowledge_sync_jobs (available_at)
        WHERE status = 'queued'
        """
    )
    op.execute(
        """
        CREATE INDEX ix_knowledge_sync_jobs_stale_claim
        ON knowledge_sync_jobs (locked_at)
        WHERE status = 'running'
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_sync_jobs_stale_claim", table_name="knowledge_sync_jobs"
    )
    op.drop_index(
        "ix_knowledge_sync_jobs_ready_claim", table_name="knowledge_sync_jobs"
    )
    op.drop_index("ix_operational_jobs_stale_claim", table_name="operational_jobs")
    op.drop_index("ix_operational_jobs_ready_claim", table_name="operational_jobs")
    op.drop_index(
        "ix_content_assets_product_gallery", table_name="content_assets"
    )
    op.drop_index("ix_products_public_listing", table_name="products")
