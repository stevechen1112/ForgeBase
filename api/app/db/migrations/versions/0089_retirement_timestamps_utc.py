"""Normalize retirement-observation timestamps to UTC.

Revision ID: 0089_retirement_timestamps_utc
Revises: 0088_single_product_tenant_access
"""

import sqlalchemy as sa
from alembic import op

revision = "0089_retirement_timestamps_utc"
down_revision = "0088_single_product_tenant_access"
branch_labels = None
depends_on = None


_UTC_NOW = sa.text("TIMEZONE('utc', NOW())")


def upgrade() -> None:
    # Older installs could seed the observation start in the database session's
    # local timezone even though application events use naive UTC. Only repair
    # impossible future values so legitimate observation history is preserved.
    op.execute(
        """
        UPDATE retirement_candidate_observations
        SET started_at = TIMEZONE('utc', NOW()),
            updated_at = TIMEZONE('utc', NOW())
        WHERE started_at > TIMEZONE('utc', NOW())
        """
    )
    op.alter_column(
        "retirement_candidate_observations",
        "started_at",
        existing_type=sa.DateTime(),
        server_default=_UTC_NOW,
    )
    op.alter_column(
        "retirement_candidate_observations",
        "updated_at",
        existing_type=sa.DateTime(),
        server_default=_UTC_NOW,
    )
    op.alter_column(
        "retirement_usage_events",
        "occurred_at",
        existing_type=sa.DateTime(),
        server_default=_UTC_NOW,
    )


def downgrade() -> None:
    local_now = sa.text("NOW()")
    op.alter_column(
        "retirement_usage_events",
        "occurred_at",
        existing_type=sa.DateTime(),
        server_default=local_now,
    )
    op.alter_column(
        "retirement_candidate_observations",
        "updated_at",
        existing_type=sa.DateTime(),
        server_default=local_now,
    )
    op.alter_column(
        "retirement_candidate_observations",
        "started_at",
        existing_type=sa.DateTime(),
        server_default=local_now,
    )
