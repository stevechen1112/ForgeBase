"""Journey snapshots and review-only outreach drafts.

Revision ID: 0082_journey_outreach_drafts
Revises: 0081_contact_enrichment_review
"""

import sqlalchemy as sa
from alembic import op

revision = "0082_journey_outreach_drafts"
down_revision = "0081_contact_enrichment_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outreach_draft_policies",
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("mode", sa.String(20), nullable=False, server_default="off"),
        sa.Column("lookback_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("snapshot_retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("max_evidence_events", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("allowed_languages", sa.JSON(), nullable=False, server_default=sa.text("'[\"en\", \"zh-TW\"]'")),
        sa.Column("policy_version", sa.String(60), nullable=False, server_default="outreach-review-v1"),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("mode IN ('off', 'review_only')", name="ck_outreach_policy_mode"),
        sa.CheckConstraint("lookback_days >= 1 AND lookback_days <= 365", name="ck_outreach_policy_lookback"),
        sa.CheckConstraint("snapshot_retention_days >= 1 AND snapshot_retention_days <= 365", name="ck_outreach_policy_retention"),
        sa.CheckConstraint("max_evidence_events >= 1 AND max_evidence_events <= 500", name="ck_outreach_policy_max_events"),
    )
    op.create_index("ix_outreach_draft_policies_mode", "outreach_draft_policies", ["mode"])

    op.create_table(
        "journey_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("visitor_id", sa.Uuid(), sa.ForeignKey("visitors.visitor_id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_identification_id", sa.Uuid(), sa.ForeignKey("company_identifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_candidate_id", sa.Uuid(), sa.ForeignKey("contact_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation_key", sa.String(200), nullable=False),
        sa.Column("intent_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("intent_stage", sa.String(20), nullable=False, server_default="cold"),
        sa.Column("intent_facets", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("top_products", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("top_pages", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("downloads", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("comparisons", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("cta_signals", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("journey_signals", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_event_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("knowledge_references", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("policy_version", sa.String(60), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("intent_score >= 0", name="ck_journey_snapshot_intent_score"),
        sa.CheckConstraint("expires_at > generated_at", name="ck_journey_snapshot_expiry"),
        sa.UniqueConstraint("generation_key", name="uq_journey_snapshot_generation_key"),
    )
    for column in ("tenant_id", "visitor_id", "company_identification_id", "contact_candidate_id", "generation_key", "generated_at", "expires_at"):
        op.create_index(f"ix_journey_snapshots_{column}", "journey_snapshots", [column])

    op.create_table(
        "outreach_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("visitor_id", sa.Uuid(), sa.ForeignKey("visitors.visitor_id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_identification_id", sa.Uuid(), sa.ForeignKey("company_identifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_candidate_id", sa.Uuid(), sa.ForeignKey("contact_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.Uuid(), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("journey_snapshot_id", sa.Uuid(), sa.ForeignKey("journey_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nurture_sequence_id", sa.Uuid(), sa.ForeignKey("nurture_sequences.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nurture_step_id", sa.Uuid(), sa.ForeignKey("nurture_steps.id", ondelete="SET NULL"), nullable=True),
        sa.Column("revision_of_id", sa.Uuid(), sa.ForeignKey("outreach_messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("revision_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("purpose", sa.String(50), nullable=False, server_default="business_inquiry"),
        sa.Column("channel", sa.String(20), nullable=False, server_default="email"),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("to_email_ciphertext", sa.Text(), nullable=False),
        sa.Column("to_email_hash", sa.String(64), nullable=False),
        sa.Column("to_email_masked", sa.String(254), nullable=False),
        sa.Column("subject_snapshot", sa.String(500), nullable=False),
        sa.Column("html_snapshot", sa.Text(), nullable=False),
        sa.Column("text_snapshot", sa.Text(), nullable=False),
        sa.Column("personalization_evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("knowledge_version", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("generation_model", sa.String(100), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_review"),
        sa.Column("approved_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("review_note", sa.String(2000), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "contact_candidate_id", "revision_no", name="uq_outreach_candidate_revision"),
        sa.CheckConstraint("status IN ('draft', 'pending_review', 'approved', 'rejected', 'cancelled')", name="ck_outreach_message_status"),
        sa.CheckConstraint("revision_no >= 1", name="ck_outreach_message_revision"),
        sa.CheckConstraint("char_length(subject_snapshot) > 0", name="ck_outreach_subject_not_empty"),
        sa.CheckConstraint("char_length(text_snapshot) > 0", name="ck_outreach_text_not_empty"),
    )
    for column in ("tenant_id", "visitor_id", "company_identification_id", "contact_candidate_id", "contact_id", "journey_snapshot_id", "revision_of_id", "to_email_hash", "content_hash", "status", "created_at"):
        op.create_index(f"ix_outreach_messages_{column}", "outreach_messages", [column])

    op.create_table(
        "outreach_message_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outreach_message_id", sa.Uuid(), sa.ForeignKey("outreach_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason_code", sa.String(80), nullable=True),
        sa.Column("note", sa.String(2000), nullable=True),
        sa.Column("diff_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("action IN ('generated', 'revised', 'approved', 'rejected')", name="ck_outreach_review_action"),
    )
    for column in ("tenant_id", "outreach_message_id", "action", "created_at"):
        op.create_index(f"ix_outreach_message_reviews_{column}", "outreach_message_reviews", [column])


def downgrade() -> None:
    op.drop_table("outreach_message_reviews")
    op.drop_table("outreach_messages")
    op.drop_table("journey_snapshots")
    op.drop_table("outreach_draft_policies")
