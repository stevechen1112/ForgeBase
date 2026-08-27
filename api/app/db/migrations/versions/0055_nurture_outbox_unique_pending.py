"""0055_nurture_outbox_unique_pending

Prevent duplicate pending outbox rows for the same enrollment+step
(race between concurrent scheduler workers).

Revision ID: 0055_nurture_outbox_unique_pending
Revises: 0054_nurture_outbox
"""
from alembic import op

revision = "0055_nurture_outbox_unique_pending"
down_revision = "0054_nurture_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Partial unique index: at most one pending outbox per enrollment+step
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_nurture_outbox_pending_enrollment_step
        ON nurture_outbox (enrollment_id, step_id)
        WHERE status = 'pending'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_nurture_outbox_pending_enrollment_step")
