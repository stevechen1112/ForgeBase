"""Persist chat grounding review data and normalize CTA publishing status.

Revision ID: 0064_chat_grounding_and_cta_status
Revises: 0063_privacy_and_site_provisioning
"""

import sqlalchemy as sa
from alembic import op

revision = "0064_chat_grounding_and_cta_status"
down_revision = "0063_privacy_and_site_provisioning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("grounding_status", sa.String(20), nullable=True))
    op.add_column("chat_messages", sa.Column("claim_warnings", sa.Text(), nullable=True))
    op.execute("UPDATE ctas SET status = 'published' WHERE status = 'active'")


def downgrade() -> None:
    # CTA values stay published because an older published row cannot be
    # distinguished safely from one normalized from the legacy active value.
    op.drop_column("chat_messages", "claim_warnings")
    op.drop_column("chat_messages", "grounding_status")
