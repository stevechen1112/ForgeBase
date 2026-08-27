"""Alembic migration 0018 — growth site enhancement fields

- products: add is_featured (bool, default false), display_priority (int, default 0)
- rfq_requests: add first_response_at (timestamp), quote_sent_at (timestamp), lost_reason (varchar 500)
- ctas: add target_intent_stage (varchar 20, default 'any')
"""
import sqlalchemy as sa
from alembic import op

revision = "0018_growth_site_fields"
down_revision = "0017_add_brief_status_to_page_briefs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Products: featured product support ────────────────────────────────────
    op.add_column(
        "products",
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "products",
        sa.Column("display_priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_products_is_featured", "products", ["is_featured"])

    # ── RFQ Requests: sales follow-up fields ──────────────────────────────────
    op.add_column(
        "rfq_requests",
        sa.Column("first_response_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "rfq_requests",
        sa.Column("quote_sent_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "rfq_requests",
        sa.Column("lost_reason", sa.String(500), nullable=True),
    )

    # ── CTAs: intent stage targeting ──────────────────────────────────────────
    op.add_column(
        "ctas",
        sa.Column(
            "target_intent_stage",
            sa.String(20),
            nullable=False,
            server_default="any",
        ),
    )


def downgrade() -> None:
    op.drop_column("ctas", "target_intent_stage")
    op.drop_column("rfq_requests", "lost_reason")
    op.drop_column("rfq_requests", "quote_sent_at")
    op.drop_column("rfq_requests", "first_response_at")
    op.drop_index("ix_products_is_featured", table_name="products")
    op.drop_column("products", "display_priority")
    op.drop_column("products", "is_featured")
