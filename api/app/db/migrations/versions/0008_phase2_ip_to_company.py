"""phase2 IP-to-company account model

Revision ID: 0008_phase2_ip_to_company
Revises: 0007_phase2_multilingual_schema
Create Date: 2025-01-01 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_phase2_ip_to_company"
down_revision = "0007_phase2_multilingual_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create accounts table ─────────────────────────────────────────────────
    op.create_table(
        "accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(200), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("employee_count_range", sa.String(30), nullable=True),
        sa.Column("annual_revenue_range", sa.String(30), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enrichment_source", sa.String(50), nullable=True),
        sa.Column("enrichment_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("last_enriched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_visitors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_page_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_intent_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounts_company_name", "accounts", ["company_name"])
    op.create_index("ix_accounts_domain", "accounts", ["domain"])

    # ── Add account_id + IP tracking columns to visitors ──────────────────────
    op.add_column(
        "visitors",
        sa.Column("account_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "visitors",
        sa.Column("last_seen_ip", sa.String(45), nullable=True),
    )
    op.add_column(
        "visitors",
        sa.Column("ip_resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_visitors_account_id",
        "visitors",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_visitors_account_id", "visitors", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_visitors_account_id", "visitors")
    op.drop_constraint("fk_visitors_account_id", "visitors", type_="foreignkey")
    op.drop_column("visitors", "ip_resolved_at")
    op.drop_column("visitors", "last_seen_ip")
    op.drop_column("visitors", "account_id")

    op.drop_index("ix_accounts_domain", "accounts")
    op.drop_index("ix_accounts_company_name", "accounts")
    op.drop_table("accounts")
