"""Give every existing tenant a platform-managed ForgeBase hostname.

Revision ID: 0099_managed_tenant_subdomains
Revises: 0098_tenant_domains
"""

import sqlalchemy as sa
from alembic import op

revision = "0099_managed_tenant_subdomains"
down_revision = "0098_tenant_domains"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO tenant_domains (
            id, tenant_id, hostname, domain_type, status, is_canonical,
            verification_method, dns_target, dns_verified_at, tls_status,
            activated_at, redirect_to_canonical, created_at, updated_at
        )
        SELECT
            gen_random_uuid(), t.id, LOWER(t.slug) || '.forgebase.com',
            'forgebase_subdomain', 'active',
            NOT EXISTS (
                SELECT 1 FROM tenant_domains current
                WHERE current.tenant_id = t.id AND current.is_canonical
            ),
            'platform_managed_migration', 'edge.forgebase.com', NOW(),
            'pending', NOW(),
            EXISTS (
                SELECT 1 FROM tenant_domains current
                WHERE current.tenant_id = t.id AND current.is_canonical
            ),
            NOW(), NOW()
        FROM tenants t
        WHERE LOWER(t.slug) NOT IN (
            'admin', 'api', 'app', 'edge', 'mail', 'replies', 'status',
            'support', 'www'
        )
        ON CONFLICT (hostname) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE site_builds sb
        SET primary_domain = td.hostname, updated_at = NOW()
        FROM tenant_domains td
        WHERE td.tenant_id = sb.tenant_id
          AND td.verification_method = 'platform_managed_migration'
          AND td.is_canonical
          AND (sb.primary_domain IS NULL OR TRIM(sb.primary_domain) = '')
        """
    )
    op.execute(
        """
        UPDATE site_profiles sp
        SET site_url = 'https://' || td.hostname, updated_at = NOW()
        FROM tenant_domains td
        WHERE td.tenant_id = sp.tenant_id
          AND td.verification_method = 'platform_managed_migration'
          AND td.is_canonical
          AND (sp.site_url IS NULL OR sp.site_url IN ('', 'https://example.com'))
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE site_builds sb
        SET primary_domain = NULL, updated_at = NOW()
        FROM tenant_domains td
        WHERE td.tenant_id = sb.tenant_id
          AND td.verification_method = 'platform_managed_migration'
          AND sb.primary_domain = td.hostname
        """
    )
    op.execute(
        """
        UPDATE site_profiles sp
        SET site_url = 'https://example.com', updated_at = NOW()
        FROM tenant_domains td
        WHERE td.tenant_id = sp.tenant_id
          AND td.verification_method = 'platform_managed_migration'
          AND sp.site_url = 'https://' || td.hostname
        """
    )
    op.execute(
        sa.text(
            """
            DELETE FROM tenant_domains
            WHERE verification_method = 'platform_managed_migration'
            """
        )
    )
