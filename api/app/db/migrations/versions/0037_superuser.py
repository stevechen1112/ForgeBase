"""0037_superuser

Add is_superuser flag to users table for platform admin access.

Revision ID: 0037_superuser
Revises: 0036_site_profile_flexible_shell
"""
import sqlalchemy as sa
from alembic import op

revision = "0037_superuser"
down_revision = "0036_site_profile_flexible_shell"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "is_superuser")
