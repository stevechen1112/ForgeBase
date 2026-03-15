"""add entity context to page_briefs; add entity/brief/noindex to pages

Revision ID: 0003_page_brief_entity_page_fields
Revises: 0002_content_strategies
Create Date: 2026-03-14 00:00:00.000000

Changes:
  - page_briefs: add related_entity_type (varchar 40), related_entity_id (uuid)
  - pages: add entity_type (varchar 40), entity_id (uuid), brief_id (uuid FK → page_briefs.id), noindex (bool)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_page_brief_entity_page_fields"
down_revision: Union[str, None] = "0002_content_strategies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # alembic_version.version_num defaults to varchar(32); some revision IDs in
    # this project exceed that limit. Expand to varchar(64) first so Alembic can
    # record the current (35-char) revision ID successfully.
    op.execute(
        "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(64)"
    )

    # ── page_briefs: entity context for AI generation (1a.3.6) ─────────────────
    op.add_column(
        "page_briefs",
        sa.Column("related_entity_type", sa.String(40), nullable=True),
    )
    op.add_column(
        "page_briefs",
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # ── pages: entity binding, brief source, noindex flag (spec 12.2.9) ─────────
    op.add_column(
        "pages",
        sa.Column("entity_type", sa.String(40), nullable=True),
    )
    op.add_column(
        "pages",
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "pages",
        sa.Column(
            "brief_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("page_briefs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "pages",
        sa.Column("noindex", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_pages_brief_id", "pages", ["brief_id"])
    op.create_index("ix_page_briefs_related_entity_id", "page_briefs", ["related_entity_id"])


def downgrade() -> None:
    op.drop_index("ix_page_briefs_related_entity_id", table_name="page_briefs")
    op.drop_index("ix_pages_brief_id", table_name="pages")
    op.drop_column("pages", "noindex")
    op.drop_column("pages", "brief_id")
    op.drop_column("pages", "entity_id")
    op.drop_column("pages", "entity_type")
    op.drop_column("page_briefs", "related_entity_id")
    op.drop_column("page_briefs", "related_entity_type")
