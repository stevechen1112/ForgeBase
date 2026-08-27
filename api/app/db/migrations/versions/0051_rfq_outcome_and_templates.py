"""RFQ won_reason + reply_templates（Phase 4，實效計畫 §5.4／§6.3）

Revision ID: 0051_rfq_outcome_and_templates
Revises: 0050_visitor_intent_facets
Create Date: 2026-08-03

- rfq_requests.won_reason：成交原因（§6.3 成交／流失原因必填，供日後回寫 intent 權重）
- reply_templates：回覆範本庫（§5.4，依產品線／國家／語系維護）
"""
import sqlalchemy as sa
from alembic import op

revision = "0051_rfq_outcome_and_templates"
down_revision = "0050_visitor_intent_facets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ck_rfq_status 檢查約束加入 negotiation（0004 建立的列舉延伸，§6.3 漏斗）
    op.drop_constraint("ck_rfq_status", "rfq_requests", type_="check")
    op.create_check_constraint(
        "ck_rfq_status", "rfq_requests",
        "status IN ('new','assigned','in_progress','quoted','negotiation','won','lost','expired')",
    )

    op.add_column("rfq_requests", sa.Column("won_reason", sa.String(length=500), nullable=True))

    op.create_table(
        "reply_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("product_line", sa.String(length=80), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("locale", sa.String(length=5), nullable=False, server_default="en"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reply_templates_tenant_id", "reply_templates", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_reply_templates_tenant_id", table_name="reply_templates")
    op.drop_table("reply_templates")
    op.drop_column("rfq_requests", "won_reason")

    op.drop_constraint("ck_rfq_status", "rfq_requests", type_="check")
    op.create_check_constraint(
        "ck_rfq_status", "rfq_requests",
        "status IN ('new','assigned','in_progress','quoted','won','lost','expired')",
    )
