"""0040_copilot_run_log

Add copilot_run_logs table for AI engine observability:
tool hit rate, error rate, average latency per tenant.

Revision ID: 0040_copilot_run_log
Revises: 0039_intent_scoring_config
"""
import sqlalchemy as sa
from alembic import op

revision = "0040_copilot_run_log"
down_revision = "0039_intent_scoring_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "copilot_run_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("llm_calls", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tool_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_names", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("had_error", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_copilot_run_logs_tenant_id", "copilot_run_logs", ["tenant_id"])
    op.create_index("ix_copilot_run_logs_created_at", "copilot_run_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("copilot_run_logs")
