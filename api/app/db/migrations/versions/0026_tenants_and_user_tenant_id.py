"""0026_tenants_and_user_tenant_id

Create tenants table for multi-tenant SaaS support and add tenant_id FK to users.

Revision ID: 0026_tenants_and_user_tenant_id
Revises: 0025_drop_phase2_residuals
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

revision = "0026_tenants_and_user_tenant_id"
down_revision = "0025_drop_phase2_residuals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("plan", sa.String(), nullable=False, server_default="starter"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_products", sa.Integer(), nullable=True, server_default="50"),
        sa.Column("max_admins", sa.Integer(), nullable=True, server_default="2"),
        sa.Column("paypal_subscription_id", sa.String(100), nullable=True),
        sa.Column("paypal_payer_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 2. Add tenant_id column to users (nullable for backward compat)
    op.add_column(
        "users",
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_tenant_id",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
    )

    # 3. Create a default tenant and assign all existing users to it
    default_tenant_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    op.execute(
        sa.text(
            "INSERT INTO tenants (id, name, plan, is_active, max_products, max_admins, created_at, updated_at) "
            "VALUES (:id, :name, :plan, true, NULL, NULL, :now, :now)"
        ).bindparams(
            id=default_tenant_id,
            name="Default Tenant",
            plan="professional",
            now=now,
        )
    )
    op.execute(
        sa.text("UPDATE users SET tenant_id = :tid").bindparams(tid=default_tenant_id)
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_column("users", "tenant_id")
    op.drop_table("tenants")
