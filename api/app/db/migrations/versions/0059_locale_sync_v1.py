"""0059_locale_sync_v1

- products.model_number unique per (model_number, locale, tenant_id)
- faq_items.variant_key for cross-locale pairing + backfill
- content_field_locks for silent manual-edit protection

Revision ID: 0059_locale_sync_v1
Revises: 0058_normalize_locale_case
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0059_locale_sync_v1"
down_revision = "0058_normalize_locale_case"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Product model_number uniqueness includes locale ─────────────────────
    op.drop_constraint("uq_products_model_number_tenant", "products", type_="unique")
    op.create_unique_constraint(
        "uq_products_model_number_locale_tenant",
        "products",
        ["model_number", "locale", "tenant_id"],
    )

    # ── FAQ variant_key ─────────────────────────────────────────────────────
    op.add_column(
        "faq_items",
        sa.Column("variant_key", sa.String(length=80), nullable=True),
    )
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM faq_items WHERE variant_key IS NULL")).fetchall()
    # Pair by (tenant_id, lower(question), coalesce(category_tag,''), sort_order) sharing one key
    # Simpler backfill: each row gets its own key first; EN/zh pairs with same question later share via sync.
    for (row_id,) in rows:
        conn.execute(
            sa.text("UPDATE faq_items SET variant_key = :k WHERE id = :id"),
            {"k": f"faq-{uuid.uuid4().hex[:16]}", "id": row_id},
        )
    # Merge keys for same tenant+question+category across locales (best-effort)
    conn.execute(
        sa.text(
            """
            WITH ranked AS (
              SELECT id, tenant_id, lower(question) AS q, coalesce(category_tag, '') AS tag, locale,
                     FIRST_VALUE(variant_key) OVER (
                       PARTITION BY tenant_id, lower(question), coalesce(category_tag, '')
                       ORDER BY CASE WHEN locale = 'en' THEN 0 ELSE 1 END, created_at
                     ) AS shared_key
              FROM faq_items
            )
            UPDATE faq_items f
            SET variant_key = ranked.shared_key
            FROM ranked
            WHERE f.id = ranked.id AND f.variant_key IS DISTINCT FROM ranked.shared_key
            """
        )
    )
    op.alter_column("faq_items", "variant_key", nullable=False)
    op.create_index("ix_faq_items_variant_key", "faq_items", ["variant_key"])
    op.create_unique_constraint(
        "uq_faq_items_variant_key_locale_tenant",
        "faq_items",
        ["variant_key", "locale", "tenant_id"],
    )

    # ── Manual field locks ──────────────────────────────────────────────────
    op.create_table(
        "content_field_locks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "entity_type", "entity_id", "field_name",
            name="uq_content_field_locks_entity_field",
        ),
    )
    op.create_index(
        "ix_content_field_locks_entity",
        "content_field_locks",
        ["entity_type", "entity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_content_field_locks_entity", table_name="content_field_locks")
    op.drop_table("content_field_locks")

    op.drop_constraint("uq_faq_items_variant_key_locale_tenant", "faq_items", type_="unique")
    op.drop_index("ix_faq_items_variant_key", table_name="faq_items")
    op.drop_column("faq_items", "variant_key")

    op.drop_constraint("uq_products_model_number_locale_tenant", "products", type_="unique")
    # 同步跑過後 en/zh-tw 可合法共用 model_number；直接重建舊約束會失敗。
    # 明確報錯勝過靜默刪資料：先人工移除目標語系列再回滾。
    conn = op.get_bind()
    dupes = conn.execute(
        sa.text(
            "SELECT model_number FROM products "
            "GROUP BY model_number, tenant_id HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).fetchone()
    if dupes:
        raise RuntimeError(
            "Cannot downgrade 0059: duplicate model_number across locales exist "
            "(locale sync has run). Remove non-'en' product rows first."
        )
    op.create_unique_constraint(
        "uq_products_model_number_tenant",
        "products",
        ["model_number", "tenant_id"],
    )
