"""Alembic migration 0017 — add brief_status to page_briefs

- page_briefs: add brief_status (varchar 30, default 'draft')
"""
import sqlalchemy as sa
from alembic import op

revision = "0017_add_brief_status_to_page_briefs"
down_revision = "0016_users_last_login_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "page_briefs",
        sa.Column(
            "brief_status",
            sa.String(30),
            nullable=False,
            server_default="draft",
        ),
    )


def downgrade() -> None:
    op.drop_column("page_briefs", "brief_status")
