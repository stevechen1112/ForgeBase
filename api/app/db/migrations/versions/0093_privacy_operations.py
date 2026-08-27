"""Add privacy operations audit ledger.

Revision ID: 0093_privacy_operations
Revises: 0092_tenant_delivery_factory
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0093_privacy_operations"
down_revision = "0092_tenant_delivery_factory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "privacy_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("operation_type", sa.String(length=30), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject_hash", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "operation_type IN ('retention_run', 'visitor_export', 'visitor_erasure')",
            name="ck_privacy_operation_type",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')", name="ck_privacy_operation_status"
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_privacy_operations_key"),
    )
    for column in (
        "idempotency_key",
        "operation_type",
        "tenant_id",
        "actor_user_id",
        "subject_hash",
        "status",
        "created_at",
    ):
        op.create_index(f"ix_privacy_operations_{column}", "privacy_operations", [column])


def downgrade() -> None:
    for column in reversed(
        (
            "idempotency_key",
            "operation_type",
            "tenant_id",
            "actor_user_id",
            "subject_hash",
            "status",
            "created_at",
        )
    ):
        op.drop_index(f"ix_privacy_operations_{column}", table_name="privacy_operations")
    op.drop_table("privacy_operations")
