"""Alembic migration 0013 — Download Gate field on content_assets (2.1.5)"""
from alembic import op
import sqlalchemy as sa

revision = "0013_phase2_download_gate"
down_revision = "0012_phase2_ab_test"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_assets",
        sa.Column("requires_gate", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("content_assets", "requires_gate")
