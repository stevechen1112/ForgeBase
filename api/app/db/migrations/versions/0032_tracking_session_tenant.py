"""add tenant_id to tracking_sessions

Revision ID: 0032_tracking_session_tenant
Revises: 0031_tenant_isolation_phase2
Create Date: 2026-04-12
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0032_tracking_session_tenant"
down_revision = "0031_tenant_isolation_phase2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tracking_sessions",
        sa.Column("tenant_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_tracking_sessions_tenant_id",
        "tracking_sessions",
        ["tenant_id"],
    )
    op.create_foreign_key(
        "fk_tracking_sessions_tenant_id",
        "tracking_sessions",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Backfill: assign existing sessions to the tenant via their visitor's tenant_id
    op.execute("""
        UPDATE tracking_sessions ts
        SET tenant_id = v.tenant_id
        FROM visitors v
        WHERE ts.visitor_id = v.visitor_id
          AND v.tenant_id IS NOT NULL
          AND ts.tenant_id IS NULL
    """)


def downgrade() -> None:
    op.drop_constraint("fk_tracking_sessions_tenant_id", "tracking_sessions", type_="foreignkey")
    op.drop_index("ix_tracking_sessions_tenant_id", table_name="tracking_sessions")
    op.drop_column("tracking_sessions", "tenant_id")
