"""Add agent fields to page_briefs

Revision ID: 0044_add_page_brief_agent_fields
Revises: 0043_add_rfq_agent_draft_fields
Create Date: 2026-04-26

（2026-08-03 修正：原檔位於未掛載的 api/alembic/versions/，
revision/down_revision 使用短代號 "0044"/"0043" 導致斷鏈；
遷入正式目錄並對齊完整 revision id。）
"""
from alembic import op
import sqlalchemy as sa

revision = "0044_add_page_brief_agent_fields"
down_revision = "0043_add_rfq_agent_draft_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "page_briefs",
        sa.Column("agent_run_id", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_page_briefs_agent_run_id",
        "page_briefs",
        ["agent_run_id"],
    )
    op.add_column(
        "page_briefs",
        sa.Column("agent_approved_content_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_index("ix_page_briefs_agent_run_id", table_name="page_briefs")
    op.drop_column("page_briefs", "agent_run_id")
    op.drop_column("page_briefs", "agent_approved_content_json")
