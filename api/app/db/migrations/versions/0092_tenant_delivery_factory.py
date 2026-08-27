"""Add replay ledger for atomic tenant delivery factory runs.

Revision ID: 0092_tenant_delivery_factory
Revises: 0091_capacity_indexes
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0092_tenant_delivery_factory"
down_revision = "0091_capacity_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_provisioning_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="201"),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_tenant_provisioning_runs_key"
        ),
    )
    op.create_index(
        "ix_tenant_provisioning_runs_idempotency_key",
        "tenant_provisioning_runs",
        ["idempotency_key"],
    )
    op.create_index(
        "ix_tenant_provisioning_runs_actor_user_id",
        "tenant_provisioning_runs",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_tenant_provisioning_runs_tenant_id",
        "tenant_provisioning_runs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_tenant_provisioning_runs_created_at",
        "tenant_provisioning_runs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tenant_provisioning_runs_created_at",
        table_name="tenant_provisioning_runs",
    )
    op.drop_index(
        "ix_tenant_provisioning_runs_tenant_id",
        table_name="tenant_provisioning_runs",
    )
    op.drop_index(
        "ix_tenant_provisioning_runs_actor_user_id",
        table_name="tenant_provisioning_runs",
    )
    op.drop_index(
        "ix_tenant_provisioning_runs_idempotency_key",
        table_name="tenant_provisioning_runs",
    )
    op.drop_table("tenant_provisioning_runs")

