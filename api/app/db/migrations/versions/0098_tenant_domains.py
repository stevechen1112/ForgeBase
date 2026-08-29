"""Add multi-hostname tenant domain lifecycle records.

Revision ID: 0098_tenant_domains
Revises: 0097_disable_unused_notification_channels
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0098_tenant_domains"
down_revision = "0097_disable_unused_notification_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_domains",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hostname", sa.String(length=253), nullable=False),
        sa.Column("domain_type", sa.String(length=32), nullable=False, server_default="custom"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("is_canonical", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_method", sa.String(length=40), nullable=True),
        sa.Column("verification_token", sa.String(length=255), nullable=True),
        sa.Column("dns_target", sa.String(length=253), nullable=True),
        sa.Column("dns_observed_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("dns_verified_at", sa.DateTime(), nullable=True),
        sa.Column("tls_status", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("tls_issued_at", sa.DateTime(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sa.String(length=1000), nullable=True),
        sa.Column("redirect_to_canonical", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "domain_type IN ('forgebase_subdomain', 'custom')",
            name="ck_tenant_domains_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'verifying', 'verified', 'active', 'failed', 'suspended')",
            name="ck_tenant_domains_status",
        ),
        sa.CheckConstraint(
            "tls_status IN ('unknown', 'pending', 'issuing', 'active', 'failed')",
            name="ck_tenant_domains_tls_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hostname", name="uq_tenant_domains_hostname"),
    )
    for column in (
        "tenant_id",
        "domain_type",
        "status",
        "tls_status",
        "last_checked_at",
        "created_by_user_id",
    ):
        op.create_index(f"ix_tenant_domains_{column}", "tenant_domains", [column])
    op.create_index(
        "uq_tenant_domains_canonical_per_tenant",
        "tenant_domains",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_canonical"),
    )

    # Preserve every currently assigned live hostname without claiming that a
    # historical deployment completed the new DNS ownership workflow.
    op.execute(
        """
        INSERT INTO tenant_domains (
            id, tenant_id, hostname, domain_type, status, is_canonical,
            verification_method, tls_status, activated_at,
            redirect_to_canonical, created_at, updated_at
        )
        SELECT
            gen_random_uuid(), sb.tenant_id,
            LOWER(TRIM(TRAILING '.' FROM TRIM(sb.primary_domain))),
            'custom', 'active', TRUE, 'legacy_migration', 'unknown',
            COALESCE(sb.published_at, sb.updated_at), FALSE, sb.created_at, sb.updated_at
        FROM site_builds sb
        WHERE sb.primary_domain IS NOT NULL
          AND TRIM(sb.primary_domain) <> ''
        ON CONFLICT (hostname) DO NOTHING
        """
    )


def downgrade() -> None:
    if op.get_bind().execute(
        sa.text(
            """
            SELECT 1
            FROM tenant_domains
            WHERE verification_method IS DISTINCT FROM 'legacy_migration'
            LIMIT 1
            """
        )
    ).first():
        raise RuntimeError("Cannot drop tenant_domains after managed-domain records exist")
    op.drop_index("uq_tenant_domains_canonical_per_tenant", table_name="tenant_domains")
    op.drop_table("tenant_domains")
