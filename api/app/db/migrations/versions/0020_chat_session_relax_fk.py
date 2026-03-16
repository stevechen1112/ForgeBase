"""Alembic migration 0020 — relax chat session tracking foreign key

- drop chat_sessions.session_id foreign key to tracking_sessions
"""
from alembic import op

revision = "0020_chat_session_relax_fk"
down_revision = "0019_chat_mvp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("chat_sessions_session_id_fkey", "chat_sessions", type_="foreignkey")


def downgrade() -> None:
    op.create_foreign_key(
        "chat_sessions_session_id_fkey",
        "chat_sessions",
        "tracking_sessions",
        ["session_id"],
        ["session_id"],
    )