"""Review-only company contact candidates.

Revision ID: 0081_contact_enrichment_review
Revises: 0080_growth_automation_policy
"""

import sqlalchemy as sa
from alembic import op

revision = "0081_contact_enrichment_review"
down_revision = "0080_growth_automation_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("contacts", "email", type_=sa.String(254), existing_type=sa.String(100))
    op.alter_column("contacts", "full_name", type_=sa.String(200), existing_type=sa.String(100))
    op.add_column("contacts", sa.Column("source_type", sa.String(40), nullable=True))
    op.add_column("contacts", sa.Column("source_reference_id", sa.Uuid(), nullable=True))
    op.create_index("ix_contacts_source_type", "contacts", ["source_type"])
    op.create_index("ix_contacts_source_reference_id", "contacts", ["source_reference_id"])

    op.create_table(
        "contact_persona_policies",
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("mode", sa.String(20), nullable=False, server_default="off"),
        sa.Column("contact_provider_name", sa.String(50), nullable=False, server_default="mock"),
        sa.Column("verification_provider_name", sa.String(50), nullable=False, server_default="mock"),
        sa.Column("target_departments", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("target_titles", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("target_seniorities", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("target_locations", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("excluded_title_terms", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("min_relevance_score", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("candidate_retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("max_candidates_per_company", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("daily_lookup_quota", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("daily_provider_cost_limit", sa.Numeric(14, 6), nullable=False, server_default="5"),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("mode IN ('off', 'review_only')", name="ck_contact_persona_mode"),
        sa.CheckConstraint("min_relevance_score >= 0 AND min_relevance_score <= 100", name="ck_contact_persona_min_relevance"),
        sa.CheckConstraint("candidate_retention_days >= 1 AND candidate_retention_days <= 365", name="ck_contact_persona_retention"),
        sa.CheckConstraint("max_candidates_per_company >= 1 AND max_candidates_per_company <= 25", name="ck_contact_persona_max_candidates"),
        sa.CheckConstraint("daily_lookup_quota >= 0", name="ck_contact_persona_daily_quota"),
        sa.CheckConstraint("daily_provider_cost_limit >= 0", name="ck_contact_persona_daily_cost"),
    )
    op.create_index("ix_contact_persona_policies_mode", "contact_persona_policies", ["mode"])

    op.create_table(
        "contact_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_identification_id", sa.Uuid(), sa.ForeignKey("company_identifications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_company_name", sa.String(300), nullable=False),
        sa.Column("source_company_domain", sa.String(253), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("job_title", sa.String(200), nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("seniority", sa.String(80), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("email_ciphertext", sa.Text(), nullable=False),
        sa.Column("email_hash", sa.String(64), nullable=False),
        sa.Column("email_masked", sa.String(254), nullable=False),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("verification_provider", sa.String(50), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("source_provider", sa.String(50), nullable=False),
        sa.Column("source_person_id", sa.String(200), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("source_freshness", sa.DateTime(), nullable=True),
        sa.Column("relevance_score", sa.Integer(), nullable=False),
        sa.Column("relevance_reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="candidate"),
        sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_reason_code", sa.String(80), nullable=True),
        sa.Column("review_note", sa.String(2000), nullable=True),
        sa.Column("converted_contact_id", sa.Uuid(), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "company_identification_id", "email_hash", name="uq_contact_candidate_company_email"),
        sa.CheckConstraint("verification_status IN ('verified', 'risky', 'catch_all', 'unknown', 'invalid')", name="ck_contact_candidate_verification"),
        sa.CheckConstraint("status IN ('candidate', 'approved', 'rejected', 'converted', 'expired', 'do_not_contact')", name="ck_contact_candidate_status"),
        sa.CheckConstraint("relevance_score >= 0 AND relevance_score <= 100", name="ck_contact_candidate_relevance"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_contact_candidate_confidence"),
        sa.CheckConstraint("expires_at > created_at", name="ck_contact_candidate_expiry"),
    )
    for column in (
        "tenant_id", "company_identification_id", "email_hash", "verification_status",
        "source_provider", "relevance_score", "status", "converted_contact_id", "created_at", "expires_at",
    ):
        op.create_index(f"ix_contact_candidates_{column}", "contact_candidates", [column])

    op.create_table(
        "contact_candidate_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_candidate_id", sa.Uuid(), sa.ForeignKey("contact_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("reason_code", sa.String(80), nullable=True),
        sa.Column("note", sa.String(2000), nullable=True),
        sa.Column("reviewer_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resulting_contact_id", sa.Uuid(), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("decision IN ('approve', 'reject', 'convert', 'do_not_contact')", name="ck_contact_candidate_review_decision"),
    )
    for column in ("tenant_id", "contact_candidate_id", "decision", "created_at"):
        op.create_index(f"ix_contact_candidate_reviews_{column}", "contact_candidate_reviews", [column])


def downgrade() -> None:
    op.drop_table("contact_candidate_reviews")
    op.drop_table("contact_candidates")
    op.drop_table("contact_persona_policies")
    op.drop_index("ix_contacts_source_reference_id", table_name="contacts")
    op.drop_index("ix_contacts_source_type", table_name="contacts")
    op.drop_column("contacts", "source_reference_id")
    op.drop_column("contacts", "source_type")
    op.alter_column("contacts", "full_name", type_=sa.String(100), existing_type=sa.String(200))
    op.alter_column("contacts", "email", type_=sa.String(100), existing_type=sa.String(254))
