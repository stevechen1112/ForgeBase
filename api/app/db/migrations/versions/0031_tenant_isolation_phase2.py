"""0031_tenant_isolation_phase2

Add tenant_id to the 4 tables that were missing multi-tenant scoping:
  - intake_projects
  - site_profiles
  - redirects
  - page_briefs

Also fixes the redirects.from_path uniqueness:
  - Drop global unique constraint on from_path
  - Add composite unique constraint on (from_path, tenant_id)

Revision ID: 0031_tenant_isolation_phase2
Revises: 0030_rfq_events
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0031_tenant_isolation_phase2"
down_revision = "0030_rfq_events"
branch_labels = None
depends_on = None

# Tables that get a plain nullable tenant_id FK + index
_SIMPLE_TABLES = [
    "intake_projects",
    "site_profiles",
    "page_briefs",
]


def upgrade() -> None:
    # ── 1. Add tenant_id to simple tables ────────────────────────────────────
    for table in _SIMPLE_TABLES:
        op.add_column(
            table,
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        )

    # ── 2. redirects: drop global unique, add tenant_id, add composite unique ─
    op.drop_index("ix_redirects_from_path", table_name="redirects", if_exists=True)
    # The original unique=True on from_path creates a named constraint; drop it
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'redirects_from_path_key'
                  AND conrelid = 'redirects'::regclass
            ) THEN
                ALTER TABLE redirects DROP CONSTRAINT redirects_from_path_key;
            END IF;
        END $$;
        """
    )
    op.add_column(
        "redirects",
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
    )

    # ── 3. Backfill all tables: assign rows to the first/oldest tenant ────────
    op.execute(
        """
        DO $$
        DECLARE
            _tid UUID;
        BEGIN
            SELECT id INTO _tid FROM tenants ORDER BY created_at LIMIT 1;
            IF _tid IS NOT NULL THEN
                UPDATE intake_projects  SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE site_profiles    SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE page_briefs      SET tenant_id = _tid WHERE tenant_id IS NULL;
                UPDATE redirects        SET tenant_id = _tid WHERE tenant_id IS NULL;
            END IF;
        END $$;
        """
    )

    # ── 4. Add FK + index for simple tables ──────────────────────────────────
    for table in _SIMPLE_TABLES:
        op.create_foreign_key(
            f"fk_{table}_tenant_id",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    # ── 5. redirects: FK + index + composite unique ───────────────────────────
    op.create_foreign_key(
        "fk_redirects_tenant_id",
        "redirects",
        "tenants",
        ["tenant_id"],
        ["id"],
    )
    op.create_index("ix_redirects_tenant_id", "redirects", ["tenant_id"])
    op.create_index("ix_redirects_from_path", "redirects", ["from_path"])
    op.create_unique_constraint(
        "uq_redirects_from_path_tenant",
        "redirects",
        ["from_path", "tenant_id"],
    )


def downgrade() -> None:
    # redirects
    op.drop_constraint("uq_redirects_from_path_tenant", "redirects", type_="unique")
    op.drop_index("ix_redirects_from_path", table_name="redirects")
    op.drop_index("ix_redirects_tenant_id", table_name="redirects")
    op.drop_constraint("fk_redirects_tenant_id", "redirects", type_="foreignkey")
    op.drop_column("redirects", "tenant_id")
    # Restore original global unique on from_path
    op.create_unique_constraint("redirects_from_path_key", "redirects", ["from_path"])

    # simple tables
    for table in reversed(_SIMPLE_TABLES):
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
