"""Product gallery order for tenant content maintenance.

Revision ID: 0077_tenant_content_maintenance
Revises: 0076_knowledge_index_and_rate_limit
"""

import sqlalchemy as sa
from alembic import op

revision = "0077_tenant_content_maintenance"
down_revision = "0076_knowledge_index_and_rate_limit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_assets",
        sa.Column("display_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("content_assets", "display_order")
