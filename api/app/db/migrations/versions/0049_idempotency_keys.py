"""idempotency_keys table for CF publish idempotent POST

Revision ID: 0049_idempotency_keys
Revises: 0048_site_profile_ops_config
Create Date: 2026-08-03

CF→FB Publish Contract §6：支援 `Idempotency-Key` header，
重送時回傳首次結果，避免重複建頁。
"""
from alembic import op
import sqlalchemy as sa


revision = "0049_idempotency_keys"
down_revision = "0048_site_profile_ops_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("endpoint", sa.String(length=200), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="201"),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "endpoint", "key", name="uq_idempotency_tenant_endpoint_key"),
    )
    op.create_index("ix_idempotency_keys_tenant_id", "idempotency_keys", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_tenant_id", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
