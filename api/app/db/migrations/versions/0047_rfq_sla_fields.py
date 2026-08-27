"""RFQ: timezone-aware first-response SLA fields

Revision ID: 0047_rfq_sla_fields
Revises: 0046_rfq_quality_and_trade_terms
Create Date: 2026-08-03

T7: buyer_timezone / sla_due_at / sla_breached。
SLA 以買家時區工作時間計時（先回覆者紅利）。
"""
import sqlalchemy as sa
from alembic import op

revision = "0047_rfq_sla_fields"
down_revision = "0046_rfq_quality_and_trade_terms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rfq_requests", sa.Column("buyer_timezone", sa.String(length=50), nullable=True))
    op.add_column("rfq_requests", sa.Column("sla_due_at", sa.DateTime(), nullable=True))
    op.create_index("ix_rfq_requests_sla_due_at", "rfq_requests", ["sla_due_at"])
    op.add_column(
        "rfq_requests",
        sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("rfq_requests", "sla_breached")
    op.drop_index("ix_rfq_requests_sla_due_at", table_name="rfq_requests")
    op.drop_column("rfq_requests", "sla_due_at")
    op.drop_column("rfq_requests", "buyer_timezone")
