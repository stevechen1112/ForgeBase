"""Phase 2.1.1: add segments table for advanced audience segmentation

Revision ID: 0006_phase2_audience_segments
Revises: 0005_phase2_pdf_indexing
Create Date: 2026-04-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_phase2_audience_segments"
down_revision: Union[str, None] = "0005_phase2_pdf_indexing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "segments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("conditions", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("combinator", sa.String(length=3), nullable=False, server_default="AND"),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_segments_name", "segments", ["name"])


def downgrade() -> None:
    op.drop_index("ix_segments_name", table_name="segments")
    op.drop_table("segments")
