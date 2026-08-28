"""Preserve audit actor identity after ephemeral operator cleanup.

Revision ID: 0096_audit_actor_snapshot
Revises: 0095_retirement_governance_gate
"""

import sqlalchemy as sa
from alembic import op

revision = "0096_audit_actor_snapshot"
down_revision = "0095_retirement_governance_gate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "platform_audit_logs",
        sa.Column("actor_email", sa.String(length=255), nullable=True),
    )
    op.execute(
        """
        UPDATE platform_audit_logs pal
        SET actor_email = u.email
        FROM users u
        WHERE u.id = pal.actor_user_id
        """
    )
    op.drop_constraint(
        "platform_audit_logs_actor_user_id_fkey",
        "platform_audit_logs",
        type_="foreignkey",
    )
    op.alter_column("platform_audit_logs", "actor_user_id", nullable=True)
    op.create_foreign_key(
        "platform_audit_logs_actor_user_id_fkey",
        "platform_audit_logs",
        "users",
        ["actor_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    if op.get_bind().execute(
        sa.text("SELECT 1 FROM platform_audit_logs WHERE actor_user_id IS NULL LIMIT 1")
    ).first():
        raise RuntimeError("Cannot restore mandatory audit actors after operator removal")
    op.drop_constraint(
        "platform_audit_logs_actor_user_id_fkey",
        "platform_audit_logs",
        type_="foreignkey",
    )
    op.alter_column("platform_audit_logs", "actor_user_id", nullable=False)
    op.create_foreign_key(
        "platform_audit_logs_actor_user_id_fkey",
        "platform_audit_logs",
        "users",
        ["actor_user_id"],
        ["id"],
    )
    op.drop_column("platform_audit_logs", "actor_email")
