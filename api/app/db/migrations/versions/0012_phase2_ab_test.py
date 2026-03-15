"""Alembic migration 0012 — A/B Test tables (2.5.4)"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

revision = "0012_phase2_ab_test"
down_revision = "0011_phase2_crm_sync_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ab_tests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("page_id", sa.Uuid(), nullable=True),
        sa.Column("test_element", sa.String(), nullable=False, server_default="cta"),
        sa.Column("variant_a", sa.Text(), nullable=False, server_default=""),
        sa.Column("variant_b", sa.Text(), nullable=False, server_default=""),
        sa.Column("split_ratio", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("views_a", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("views_b", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversions_a", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversions_b", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ab_tests_name", "ab_tests", ["name"])
    op.create_index("ix_ab_tests_page_id", "ab_tests", ["page_id"])
    op.create_index("ix_ab_tests_is_active", "ab_tests", ["is_active"])

    op.create_table(
        "ab_test_views",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("test_id", sa.Uuid(), nullable=False),
        sa.Column("visitor_id", sa.String(), nullable=True),
        sa.Column("variant", sa.String(), nullable=False, server_default="a"),
        sa.Column("converted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["test_id"], ["ab_tests.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ab_test_views_test_id", "ab_test_views", ["test_id"])
    op.create_index("ix_ab_test_views_visitor_id", "ab_test_views", ["visitor_id"])


def downgrade() -> None:
    op.drop_table("ab_test_views")
    op.drop_table("ab_tests")
