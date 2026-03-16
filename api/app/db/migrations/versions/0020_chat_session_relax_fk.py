"""Alembic migration 0020 — relax chat session tracking foreign key

- drop chat_sessions.session_id foreign key to tracking_sessions
"""
from alembic import op

revision = "0020_chat_session_relax_fk"
down_revision = "0019_chat_mvp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'chat_sessions_session_id_fkey'
            ) THEN
                ALTER TABLE chat_sessions DROP CONSTRAINT chat_sessions_session_id_fkey;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.create_foreign_key(
        "chat_sessions_session_id_fkey",
        "chat_sessions",
        "tracking_sessions",
        ["session_id"],
        ["session_id"],
    )