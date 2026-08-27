"""Platform tenant operations audit trail.

Revision ID: 0068_platform_tenant_operations
Revises: 0067_site_profile_tenant_copy
"""

import sqlalchemy as sa
from alembic import op

revision = "0068_platform_tenant_operations"
down_revision = "0067_site_profile_tenant_copy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=True),
        sa.Column("changes_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_platform_audit_logs_actor_user_id", "platform_audit_logs", ["actor_user_id"])
    op.create_index("ix_platform_audit_logs_tenant_id", "platform_audit_logs", ["tenant_id"])
    op.create_index("ix_platform_audit_logs_action", "platform_audit_logs", ["action"])
    op.create_index("ix_platform_audit_logs_created_at", "platform_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("platform_audit_logs")
