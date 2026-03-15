"""add content_strategies and ai_generation_logs

Revision ID: 0002_content_strategies
Revises: 0001_initial
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_content_strategies"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── content_strategies ──────────────────────────────────────────────────────
    op.create_table(
        "content_strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("page_type", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("brief_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="unplanned",
        ),
        sa.Column("locale", sa.String(16), nullable=False, server_default="zh-TW"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["brief_id"],
            ["page_briefs.id"],
            name="fk_strategies_brief_id",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "status IN ('unplanned','brief_created','ai_generated','in_review','published')",
            name="ck_strategies_status",
        ),
    )

    op.create_index("ix_content_strategies_page_type", "content_strategies", ["page_type"])
    op.create_index("ix_content_strategies_status", "content_strategies", ["status"])
    op.create_index("ix_content_strategies_entity", "content_strategies", ["entity_type", "entity_id"])

    # ── ai_generation_logs ───────────────────────────────────────────────────────
    op.create_table(
        "ai_generation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("brief_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("page_type", sa.String(64), nullable=True),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["brief_id"],
            ["page_briefs.id"],
            name="fk_ai_logs_brief_id",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "status IN ('pending','processing','done','error')",
            name="ck_ai_logs_status",
        ),
    )

    op.create_index("ix_ai_generation_logs_brief_id", "ai_generation_logs", ["brief_id"])
    op.create_index("ix_ai_generation_logs_status", "ai_generation_logs", ["status"])
    op.create_index("ix_ai_generation_logs_created_at", "ai_generation_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_generation_logs")
    op.drop_table("content_strategies")
