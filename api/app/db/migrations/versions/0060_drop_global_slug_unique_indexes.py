"""0060_drop_global_slug_unique_indexes

Drop leftover UNIQUE indexes on slug / model_number that conflict with
per-locale rows (same slug across en + zh-tw). Composite constraints
(slug, locale, tenant_id) remain the canonical uniqueness boundary.

Revision ID: 0060_drop_global_slug_unique_indexes
Revises: 0059_locale_sync_v1
"""
from alembic import op

revision = "0060_drop_global_slug_unique_indexes"
down_revision = "0059_locale_sync_v1"
branch_labels = None
depends_on = None

# (unique_index_to_drop, table, columns_for_nonunique_replacement)
_INDEXES = [
    ("ix_products_slug", "products", ["slug"]),
    ("ix_products_model_number", "products", ["model_number"]),
    ("ix_applications_slug", "applications", ["slug"]),
    ("ix_comparison_topics_slug", "comparison_topics", ["slug"]),
    ("ix_capabilities_slug", "capabilities", ["slug"]),
    ("ix_pages_slug", "pages", ["slug"]),
    ("ix_certifications_slug", "certifications", ["slug"]),
]


def upgrade() -> None:
    for name, table, cols in _INDEXES:
        op.execute(f'DROP INDEX IF EXISTS "{name}"')
        # Keep a non-unique index for list/filter performance
        col_list = ", ".join(cols)
        op.execute(
            f'CREATE INDEX IF NOT EXISTS "{name}" ON {table} ({col_list})'
        )


def downgrade() -> None:
    # NOTE: 同步跑過後同 slug 會有多語列，重建 UNIQUE 索引會失敗；
    # 需先移除目標語系列再回滾。
    for name, table, cols in _INDEXES:
        op.execute(f'DROP INDEX IF EXISTS "{name}"')
        col_list = ", ".join(cols)
        op.execute(
            f'CREATE UNIQUE INDEX IF NOT EXISTS "{name}" ON {table} ({col_list})'
        )
