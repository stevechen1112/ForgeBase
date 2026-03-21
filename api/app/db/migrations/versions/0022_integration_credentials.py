"""0022_integration_credentials

Add integration_credentials table for encrypted per-tenant API key storage.

Revision ID: 0022_integration_credentials
Revises: 0021_certifications_multilingual_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_integration_credentials"
down_revision = "0021_certifications_multilingual_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column("credential_key", sa.String(), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "service", "credential_key",
                            name="uq_integration_credential"),
    )
    op.create_index("ix_integration_credentials_tenant_id",
                    "integration_credentials", ["tenant_id"])
    op.create_index("ix_integration_credentials_service",
                    "integration_credentials", ["service"])


def downgrade() -> None:
    op.drop_index("ix_integration_credentials_service",
                  table_name="integration_credentials")
    op.drop_index("ix_integration_credentials_tenant_id",
                  table_name="integration_credentials")
    op.drop_table("integration_credentials")
