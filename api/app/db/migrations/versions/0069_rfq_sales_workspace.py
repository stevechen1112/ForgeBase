"""RFQ sales workspace fields and internal notes.

Revision ID: 0069_rfq_sales_workspace
Revises: 0068_platform_tenant_operations
"""

import sqlalchemy as sa
from alembic import op

revision = "0069_rfq_sales_workspace"
down_revision = "0068_platform_tenant_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rfq_requests", sa.Column("next_follow_up_at", sa.DateTime(), nullable=True))
    op.add_column("rfq_requests", sa.Column("deal_amount", sa.Numeric(14, 2), nullable=True))
    op.add_column("rfq_requests", sa.Column("deal_currency", sa.String(3), nullable=False, server_default="USD"))
    op.add_column("rfq_requests", sa.Column("is_spam", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("rfq_requests", sa.Column("spam_reason", sa.String(500), nullable=True))
    op.add_column("rfq_requests", sa.Column("spam_marked_at", sa.DateTime(), nullable=True))
    op.add_column("rfq_requests", sa.Column("spam_marked_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("rfq_requests", sa.Column("merged_into_rfq_id", sa.Uuid(), sa.ForeignKey("rfq_requests.id"), nullable=True))
    op.add_column("rfq_requests", sa.Column("merged_at", sa.DateTime(), nullable=True))
    op.create_index("ix_rfq_requests_next_follow_up_at", "rfq_requests", ["next_follow_up_at"])
    op.create_index("ix_rfq_requests_is_spam", "rfq_requests", ["is_spam"])
    op.create_index("ix_rfq_requests_merged_into_rfq_id", "rfq_requests", ["merged_into_rfq_id"])

    op.create_table(
        "rfq_notes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("rfq_id", sa.Uuid(), sa.ForeignKey("rfq_requests.id"), nullable=False),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.String(4000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rfq_notes_tenant_id", "rfq_notes", ["tenant_id"])
    op.create_index("ix_rfq_notes_rfq_id", "rfq_notes", ["rfq_id"])
    op.create_index("ix_rfq_notes_author_id", "rfq_notes", ["author_id"])
    op.create_index("ix_rfq_notes_created_at", "rfq_notes", ["created_at"])


def downgrade() -> None:
    op.drop_table("rfq_notes")
    op.drop_index("ix_rfq_requests_merged_into_rfq_id", table_name="rfq_requests")
    op.drop_index("ix_rfq_requests_is_spam", table_name="rfq_requests")
    op.drop_index("ix_rfq_requests_next_follow_up_at", table_name="rfq_requests")
    op.drop_column("rfq_requests", "merged_at")
    op.drop_column("rfq_requests", "merged_into_rfq_id")
    op.drop_column("rfq_requests", "spam_marked_by")
    op.drop_column("rfq_requests", "spam_marked_at")
    op.drop_column("rfq_requests", "spam_reason")
    op.drop_column("rfq_requests", "is_spam")
    op.drop_column("rfq_requests", "deal_currency")
    op.drop_column("rfq_requests", "deal_amount")
    op.drop_column("rfq_requests", "next_follow_up_at")
