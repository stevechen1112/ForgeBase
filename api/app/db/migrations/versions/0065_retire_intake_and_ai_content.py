"""Retire Legacy Site Intake and AI content-generation persistence.

Revision ID: 0065_retire_intake_ai_content
Revises: 0064_chat_grounding_and_cta_status

This migration intentionally removes product capabilities that are no longer
part of ForgeBase. Back up any legacy intake or AI-generation audit data before
running it in an environment where that historical data must be retained.
"""

from alembic import op

revision = "0065_retire_intake_ai_content"
down_revision = "0064_chat_grounding_and_cta_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep the content planning matrix, but remove its dependency on AI briefs
    # and normalize old workflow-only status values to the supported lifecycle.
    op.execute(
        """
        UPDATE content_strategies
        SET status = CASE
            WHEN status IN ('brief_created', 'ai_generated') THEN 'planned'
            WHEN status = 'in_review' THEN 'in_progress'
            ELSE status
        END
        """
    )
    op.execute(
        "ALTER TABLE IF EXISTS content_strategies "
        "DROP CONSTRAINT IF EXISTS ck_strategies_status"
    )
    op.execute(
        "ALTER TABLE IF EXISTS content_strategies "
        "DROP CONSTRAINT IF EXISTS fk_strategies_brief_id"
    )
    op.execute(
        "ALTER TABLE IF EXISTS content_strategies "
        "DROP COLUMN IF EXISTS brief_id"
    )
    op.execute(
        "ALTER TABLE IF EXISTS content_strategies "
        "ADD CONSTRAINT ck_strategies_status "
        "CHECK (status IN ('unplanned','planned','in_progress','published'))"
    )

    op.execute("DROP INDEX IF EXISTS ix_pages_brief_id")
    op.execute("ALTER TABLE IF EXISTS pages DROP COLUMN IF EXISTS brief_id")

    op.execute("DROP TABLE IF EXISTS ai_generation_logs")

    # Drop child intake tables before their parents to respect foreign keys.
    op.execute("DROP TABLE IF EXISTS intake_brief_candidates")
    op.execute("DROP TABLE IF EXISTS intake_redirect_candidates")
    op.execute("DROP TABLE IF EXISTS intake_entity_candidates")
    op.execute("DROP TABLE IF EXISTS intake_url_candidates")
    op.execute("DROP TABLE IF EXISTS intake_projects")

    op.execute("DROP TABLE IF EXISTS page_briefs")


def downgrade() -> None:
    raise NotImplementedError(
        "Retired intake and AI-content data cannot be reconstructed automatically; "
        "restore a database backup if rollback is required."
    )
