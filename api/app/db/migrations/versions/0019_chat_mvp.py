"""Alembic migration 0019 — chat MVP tables

- add chat_sessions
- add chat_messages
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_chat_mvp"
down_revision = "0018_growth_site_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("visitor_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("context_page", sa.String(length=500), nullable=True),
        sa.Column("context_entity_type", sa.String(length=30), nullable=True),
        sa.Column("context_entity_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_sessions_visitor_id", "chat_sessions", ["visitor_id"])
    op.create_index("ix_chat_sessions_session_id", "chat_sessions", ["session_id"])
    op.create_index("ix_chat_sessions_context_entity_id", "chat_sessions", ["context_entity_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chat_session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["chat_session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_chat_session_id", "chat_messages", ["chat_session_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_chat_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_context_entity_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_session_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_visitor_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")