"""0029_chat_admin_fields

Add quality_rating and admin_notes columns to chat_sessions table
for admin quality review.
"""

import sqlalchemy as sa
from alembic import op

revision = "0029_chat_admin_fields"
down_revision = "0028_merge_site_profile_and_multitenant_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("quality_rating", sa.Integer(), nullable=True),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("admin_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "admin_notes")
    op.drop_column("chat_sessions", "quality_rating")
