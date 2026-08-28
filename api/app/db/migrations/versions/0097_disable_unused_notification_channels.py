"""Disable unused LINE and Telegram channels and start observation.

Revision ID: 0097_disable_unused_notification_channels
Revises: 0096_audit_actor_snapshot
"""

import sqlalchemy as sa
from alembic import op

revision = "0097_disable_unused_notification_channels"
down_revision = "0096_audit_actor_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_preferences",
        sa.Column("retirement_disabled_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "notification_preferences",
        sa.Column("retirement_previous_enabled", sa.Boolean(), nullable=True),
    )
    op.create_index(
        "ix_notification_preferences_retirement_disabled_at",
        "notification_preferences",
        ["retirement_disabled_at"],
    )
    op.execute(
        """
        UPDATE notification_preferences
        SET retirement_previous_enabled = enabled,
            enabled = FALSE,
            binding_code = NULL,
            binding_code_expires_at = NULL,
            retirement_disabled_at = TIMEZONE('utc', NOW()),
            updated_at = TIMEZONE('utc', NOW())
        WHERE channel IN ('telegram', 'line')
          AND retirement_disabled_at IS NULL
        """
    )
    op.execute(
        """
        UPDATE retirement_candidate_observations
        SET code_state = 'disabled',
            started_at = CASE
                WHEN status = 'observing' THEN TIMEZONE('utc', NOW())
                ELSE started_at
            END,
            updated_at = TIMEZONE('utc', NOW())
        WHERE candidate_key IN ('notification_telegram', 'notification_line')
          AND code_state = 'active'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE notification_preferences
        SET enabled = retirement_previous_enabled,
            updated_at = TIMEZONE('utc', NOW())
        WHERE channel IN ('telegram', 'line')
          AND retirement_disabled_at IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE retirement_candidate_observations
        SET code_state = 'active',
            status = 'observing',
            updated_at = TIMEZONE('utc', NOW())
        WHERE candidate_key IN ('notification_telegram', 'notification_line')
          AND code_state = 'disabled'
        """
    )
    op.drop_index(
        "ix_notification_preferences_retirement_disabled_at",
        table_name="notification_preferences",
    )
    op.drop_column("notification_preferences", "retirement_previous_enabled")
    op.drop_column("notification_preferences", "retirement_disabled_at")
