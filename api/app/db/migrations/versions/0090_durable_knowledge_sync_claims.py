"""Add durable claims and retry policy to knowledge sync jobs.

Revision ID: 0090_durable_knowledge_sync_claims
Revises: 0089_retirement_timestamps_utc
"""

import sqlalchemy as sa
from alembic import op

revision = "0090_durable_knowledge_sync_claims"
down_revision = "0089_retirement_timestamps_utc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_sync_jobs",
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
    )
    op.add_column(
        "knowledge_sync_jobs",
        sa.Column("locked_at", sa.DateTime(), nullable=True),
    )
    op.execute(
        """
        UPDATE knowledge_sync_jobs
        SET locked_at = updated_at
        WHERE status = 'running' AND locked_at IS NULL
        """
    )
    op.create_check_constraint(
        "ck_knowledge_sync_jobs_attempts_nonnegative",
        "knowledge_sync_jobs",
        "attempts >= 0",
    )
    op.create_check_constraint(
        "ck_knowledge_sync_jobs_max_attempts_positive",
        "knowledge_sync_jobs",
        "max_attempts > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_knowledge_sync_jobs_max_attempts_positive",
        "knowledge_sync_jobs",
        type_="check",
    )
    op.drop_constraint(
        "ck_knowledge_sync_jobs_attempts_nonnegative",
        "knowledge_sync_jobs",
        type_="check",
    )
    op.drop_column("knowledge_sync_jobs", "locked_at")
    op.drop_column("knowledge_sync_jobs", "max_attempts")
