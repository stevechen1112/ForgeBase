"""Backfill delivery workflow for sites published before the control centre.

Revision ID: 0073_backfill_published_delivery_stage
Revises: 0072_platform_delivery_control_center
"""

from alembic import op

revision = "0073_backfill_published_delivery_stage"
down_revision = "0072_platform_delivery_control_center"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0072 introduced a non-null default of ``intake``.  Existing sites that
    # were already technically published must not appear as a new intake.
    # Only populate the new workflow fields; never alter publication state.
    op.execute(
        """
        UPDATE site_builds
        SET delivery_stage = 'live',
            acceptance_status = CASE
                WHEN acceptance_status = 'pending' THEN 'waived'
                ELSE acceptance_status
            END,
            handoff_at = COALESCE(handoff_at, published_at)
        WHERE status = 'published' AND delivery_stage = 'intake'
        """
    )


def downgrade() -> None:
    # Historical delivery stage is operational data.  It is intentionally
    # retained if a code rollback is required.
    pass
