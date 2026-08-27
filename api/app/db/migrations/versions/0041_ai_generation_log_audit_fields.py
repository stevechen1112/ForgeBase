"""0041_ai_generation_log_audit_fields

Add missing audit fields to ai_generation_logs so the runtime model matches
the live database schema used by AI content generation.

Revision ID: 0041_ai_generation_log_audit_fields
Revises: 0040_copilot_run_log
"""
import sqlalchemy as sa
from alembic import op

revision = "0041_ai_generation_log_audit_fields"
down_revision = "0040_copilot_run_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_generation_logs", sa.Column("triggered_by", sa.UUID(), nullable=True))
    op.add_column("ai_generation_logs", sa.Column("input_summary", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_ai_generation_logs_triggered_by_users",
        "ai_generation_logs",
        "users",
        ["triggered_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_ai_generation_logs_triggered_by_users", "ai_generation_logs", type_="foreignkey")
    op.drop_column("ai_generation_logs", "input_summary")
    op.drop_column("ai_generation_logs", "triggered_by")