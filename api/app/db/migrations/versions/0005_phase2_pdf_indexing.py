"""Phase 2.3.2: add is_indexable and seo_title to content_assets

Revision ID: 0005_phase2_pdf_indexing
Revises: 0004_phase1b_tracking_identity
Create Date: 2026-04-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_phase2_pdf_indexing"
down_revision: Union[str, None] = "0004_phase1b_tracking_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "content_assets",
        sa.Column("is_indexable", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "content_assets",
        sa.Column("seo_title", sa.String(length=200), nullable=True),
    )
    op.create_index(
        "ix_content_assets_is_indexable",
        "content_assets",
        ["is_indexable"],
    )


def downgrade() -> None:
    op.drop_index("ix_content_assets_is_indexable", table_name="content_assets")
    op.drop_column("content_assets", "seo_title")
    op.drop_column("content_assets", "is_indexable")
