"""RFQ: lead quality score + trade terms fields

Revision ID: 0046_rfq_quality_and_trade_terms
Revises: 0045_contacts_tenant_scoped_email
Create Date: 2026-08-03

T9: quality_score / quality_reasons_json（規則式 Lead Quality Score v1）
T10: incoterm / annual_volume / is_trial_order / required_certs_json /
     target_price（表單第二步貿易條件欄位，全選填）
"""
import sqlalchemy as sa
from alembic import op

revision = "0046_rfq_quality_and_trade_terms"
down_revision = "0045_contacts_tenant_scoped_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rfq_requests",
        sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_rfq_requests_quality_score", "rfq_requests", ["quality_score"])
    op.add_column("rfq_requests", sa.Column("quality_reasons_json", sa.Text(), nullable=True))
    op.add_column("rfq_requests", sa.Column("incoterm", sa.String(length=10), nullable=True))
    op.add_column("rfq_requests", sa.Column("annual_volume", sa.String(length=100), nullable=True))
    op.add_column("rfq_requests", sa.Column("is_trial_order", sa.Boolean(), nullable=True))
    op.add_column("rfq_requests", sa.Column("required_certs_json", sa.Text(), nullable=True))
    op.add_column("rfq_requests", sa.Column("target_price", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("rfq_requests", "target_price")
    op.drop_column("rfq_requests", "required_certs_json")
    op.drop_column("rfq_requests", "is_trial_order")
    op.drop_column("rfq_requests", "annual_volume")
    op.drop_column("rfq_requests", "incoterm")
    op.drop_column("rfq_requests", "quality_reasons_json")
    op.drop_index("ix_rfq_requests_quality_score", table_name="rfq_requests")
    op.drop_column("rfq_requests", "quality_score")
