"""Visitor intent facets（Intent Score 2.0, 實效計畫 §4.1）

Revision ID: 0050_visitor_intent_facets
Revises: 0049_idempotency_keys
Create Date: 2026-08-03

visitors 新增四個採購 facet 欄位（可排序／篩選）與「為何 Hot」解釋字串。
"""
import sqlalchemy as sa
from alembic import op

revision = "0050_visitor_intent_facets"
down_revision = "0049_idempotency_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "visitors",
        sa.Column("facet_product_interest", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "visitors",
        sa.Column("facet_trust_validation", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "visitors",
        sa.Column("facet_procurement_readiness", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "visitors",
        sa.Column("facet_urgency", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("visitors", sa.Column("intent_explanation", sa.Text(), nullable=True))
    op.create_index("ix_visitors_facet_product_interest", "visitors", ["facet_product_interest"])
    op.create_index("ix_visitors_facet_trust_validation", "visitors", ["facet_trust_validation"])
    op.create_index("ix_visitors_facet_procurement_readiness", "visitors", ["facet_procurement_readiness"])
    op.create_index("ix_visitors_facet_urgency", "visitors", ["facet_urgency"])


def downgrade() -> None:
    op.drop_index("ix_visitors_facet_urgency", table_name="visitors")
    op.drop_index("ix_visitors_facet_procurement_readiness", table_name="visitors")
    op.drop_index("ix_visitors_facet_trust_validation", table_name="visitors")
    op.drop_index("ix_visitors_facet_product_interest", table_name="visitors")
    op.drop_column("visitors", "intent_explanation")
    op.drop_column("visitors", "facet_urgency")
    op.drop_column("visitors", "facet_procurement_readiness")
    op.drop_column("visitors", "facet_trust_validation")
    op.drop_column("visitors", "facet_product_interest")
