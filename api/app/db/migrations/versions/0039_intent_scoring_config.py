"""0039_intent_scoring_config

Add intent_scoring_config_json column to site_profiles for
per-tenant customizable scoring rules and stage thresholds.

Revision ID: 0039_intent_scoring_config
Revises: 0038_copilot_notifications
"""
from alembic import op
import sqlalchemy as sa

revision = "0039_intent_scoring_config"
down_revision = "0038_copilot_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site_profiles",
        sa.Column("intent_scoring_config_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("site_profiles", "intent_scoring_config_json")
