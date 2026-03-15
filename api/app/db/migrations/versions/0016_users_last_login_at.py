"""Alembic migration 0016 — add last_login_at to users

- users: add last_login_at (nullable timestamp with timezone)
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_users_last_login_at"
down_revision = "0015_certification_slug"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
