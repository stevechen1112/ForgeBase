"""Remove tier, phase, quota, and PayPal state from tenants.

Revision ID: 0088_single_product_tenant_access
Revises: 0087_canonical_visitor_contact_link
"""

import sqlalchemy as sa
from alembic import op

revision = "0088_single_product_tenant_access"
down_revision = "0087_canonical_visitor_contact_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("tenants", "paypal_payer_email")
    op.drop_column("tenants", "paypal_subscription_id")
    op.drop_column("tenants", "max_admins")
    op.drop_column("tenants", "max_products")
    op.drop_column("tenants", "product_stage")
    op.drop_column("tenants", "plan")


def downgrade() -> None:
    op.add_column("tenants", sa.Column("plan", sa.String(), nullable=True, server_default="starter"))
    op.add_column("tenants", sa.Column("product_stage", sa.String(length=30), nullable=False, server_default="phase1"))
    op.add_column("tenants", sa.Column("max_products", sa.Integer(), nullable=True, server_default="50"))
    op.add_column("tenants", sa.Column("max_admins", sa.Integer(), nullable=True, server_default="2"))
    op.add_column("tenants", sa.Column("paypal_subscription_id", sa.String(length=100), nullable=True))
    op.add_column("tenants", sa.Column("paypal_payer_email", sa.String(length=255), nullable=True))
