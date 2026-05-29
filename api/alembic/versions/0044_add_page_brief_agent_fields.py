"""add agent fields to page_briefs

Revision ID: 0044
Revises: 0043
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0044"
down_revision = "0043"
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
