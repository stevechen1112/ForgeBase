"""0025_drop_phase2_residuals

Drop all Phase 2 feature tables and residual columns that were removed
from the codebase: accounts, nurture_*, linkedin_audiences, crm_sync_logs,
ab_tests/ab_test_views, plus requires_gate / IP-resolution columns.

Revision ID: 0025_drop_phase2_residuals
Revises: 0024_redirects_table
"""
from alembic import op

revision = "0025_drop_phase2_residuals"
down_revision = "0024_redirects_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Phase 2 migrations (0006-0013) were converted to no-ops before this
    # migration was written; the tables/columns may never have been created.
    # All drops are therefore guarded with IF EXISTS.

    # --- Drop FK constraints (safe even if never created) ---
    op.execute("ALTER TABLE IF EXISTS visitors DROP CONSTRAINT IF EXISTS fk_visitors_account_id;")
    op.execute("ALTER TABLE IF EXISTS nurture_steps DROP CONSTRAINT IF EXISTS nurture_steps_sequence_id_fkey;")
    op.execute("ALTER TABLE IF EXISTS nurture_enrollments DROP CONSTRAINT IF EXISTS nurture_enrollments_sequence_id_fkey;")
    op.execute("ALTER TABLE IF EXISTS nurture_enrollments DROP CONSTRAINT IF EXISTS nurture_enrollments_contact_id_fkey;")
    op.execute("ALTER TABLE IF EXISTS ab_test_views DROP CONSTRAINT IF EXISTS ab_test_views_test_id_fkey;")

    # --- Drop child tables ---
    op.execute("DROP TABLE IF EXISTS ab_test_views;")
    op.execute("DROP TABLE IF EXISTS nurture_steps;")
    op.execute("DROP TABLE IF EXISTS nurture_enrollments;")
    op.execute("DROP TABLE IF EXISTS crm_sync_logs;")
    op.execute("DROP TABLE IF EXISTS linkedin_audiences;")

    # --- Drop parent tables ---
    op.execute("DROP TABLE IF EXISTS ab_tests;")
    op.execute("DROP TABLE IF EXISTS nurture_sequences;")
    op.execute("DROP TABLE IF EXISTS accounts;")

    # --- Drop residual columns ---
    op.execute("ALTER TABLE IF EXISTS content_assets DROP COLUMN IF EXISTS requires_gate;")
    op.execute("ALTER TABLE IF EXISTS visitors DROP COLUMN IF EXISTS account_id;")
    op.execute("ALTER TABLE IF EXISTS visitors DROP COLUMN IF EXISTS last_seen_ip;")
    op.execute("ALTER TABLE IF EXISTS visitors DROP COLUMN IF EXISTS ip_resolved_at;")


def downgrade() -> None:
    # Re-creating the full Phase 2 schema is not supported.
    # Restore from a database backup if needed.
    raise NotImplementedError("Downgrade not supported for Phase 2 removal migration")
