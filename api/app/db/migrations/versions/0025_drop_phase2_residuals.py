"""0025_drop_phase2_residuals

Drop all Phase 2 feature tables and residual columns that were removed
from the codebase: accounts, nurture_*, linkedin_audiences, crm_sync_logs,
ab_tests/ab_test_views, plus requires_gate / IP-resolution columns.

Revision ID: 0025_drop_phase2_residuals
Revises: 0024_redirects_table
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_drop_phase2_residuals"
down_revision = "0024_redirects_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Drop FK constraints first ---
    op.drop_constraint("fk_visitors_account_id", "visitors", type_="foreignkey")
    op.drop_constraint("nurture_steps_sequence_id_fkey", "nurture_steps", type_="foreignkey")
    op.drop_constraint("nurture_enrollments_sequence_id_fkey", "nurture_enrollments", type_="foreignkey")
    op.drop_constraint("nurture_enrollments_contact_id_fkey", "nurture_enrollments", type_="foreignkey")
    op.drop_constraint("ab_test_views_test_id_fkey", "ab_test_views", type_="foreignkey")

    # --- Drop child tables ---
    op.drop_table("ab_test_views")
    op.drop_table("nurture_steps")
    op.drop_table("nurture_enrollments")
    op.drop_table("crm_sync_logs")
    op.drop_table("linkedin_audiences")

    # --- Drop parent tables ---
    op.drop_table("ab_tests")
    op.drop_table("nurture_sequences")
    op.drop_table("accounts")

    # --- Drop residual columns ---
    op.drop_column("content_assets", "requires_gate")
    op.drop_column("visitors", "account_id")
    op.drop_column("visitors", "last_seen_ip")
    op.drop_column("visitors", "ip_resolved_at")


def downgrade() -> None:
    # Re-creating the full Phase 2 schema is not supported.
    # Restore from a database backup if needed.
    raise NotImplementedError("Downgrade not supported for Phase 2 removal migration")
