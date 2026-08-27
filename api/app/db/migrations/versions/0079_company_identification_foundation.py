"""Company identification evidence, reviews, and provider usage.

Revision ID: 0079_company_identification_foundation
Revises: 0078_repair_public_footer_hrefs
"""

import sqlalchemy as sa
from alembic import op

revision = "0079_company_identification_foundation"
down_revision = "0078_repair_public_footer_hrefs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "network_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("visitor_id", sa.Uuid(), sa.ForeignKey("visitors.visitor_id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("tracking_sessions.session_id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_event_id", sa.Uuid(), sa.ForeignKey("tracking_events.event_id", ondelete="SET NULL"), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column("ip_masked", sa.String(64), nullable=False),
        sa.Column("ip_version", sa.Integer(), nullable=False),
        sa.Column("ip_source", sa.String(30), nullable=False, server_default="request"),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_vpn", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_proxy", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_hosting", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("eligibility_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("ineligible_reason", sa.String(100), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("asn", sa.String(30), nullable=True),
        sa.Column("asn_org", sa.String(300), nullable=True),
        sa.Column("consent_state", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("dedupe_key", sa.String(160), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "dedupe_key", name="uq_network_observation_tenant_dedupe"),
        sa.CheckConstraint("ip_version IN (4, 6)", name="ck_network_observation_ip_version"),
        sa.CheckConstraint(
            "eligibility_status IN ('pending', 'eligible', 'ineligible', 'expired')",
            name="ck_network_observation_eligibility_status",
        ),
        sa.CheckConstraint("expires_at > observed_at", name="ck_network_observation_expiry"),
    )
    for column in (
        "tenant_id",
        "visitor_id",
        "session_id",
        "source_event_id",
        "ip_hash",
        "eligibility_status",
        "consent_state",
        "observed_at",
        "expires_at",
    ):
        op.create_index(f"ix_network_observations_{column}", "network_observations", [column])

    op.create_table(
        "company_identifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("visitor_id", sa.Uuid(), sa.ForeignKey("visitors.visitor_id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "network_observation_id",
            sa.Uuid(),
            sa.ForeignKey("network_observations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(300), nullable=False),
        sa.Column("domain", sa.String(253), nullable=True),
        sa.Column("provider_company_id", sa.String(200), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("candidate_key", sa.String(300), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("confidence_band", sa.String(20), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("match_method", sa.String(50), nullable=False),
        sa.Column("source_freshness", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="shadow"),
        sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_note", sa.String(2000), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "network_observation_id",
            "provider",
            "candidate_key",
            name="uq_company_identification_provider_candidate",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_company_identification_confidence",
        ),
        sa.CheckConstraint(
            "confidence_band IN ('low', 'medium', 'high')",
            name="ck_company_identification_confidence_band",
        ),
        sa.CheckConstraint(
            "status IN ('shadow', 'candidate', 'confirmed', 'rejected', 'expired', 'conflict')",
            name="ck_company_identification_status",
        ),
    )
    for column in (
        "tenant_id",
        "visitor_id",
        "network_observation_id",
        "domain",
        "provider",
        "confidence_band",
        "status",
        "expires_at",
        "created_at",
    ):
        op.create_index(f"ix_company_identifications_{column}", "company_identifications", [column])

    op.create_table(
        "identification_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "company_identification_id",
            sa.Uuid(),
            sa.ForeignKey("company_identifications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("corrected_company_name", sa.String(300), nullable=True),
        sa.Column("corrected_domain", sa.String(253), nullable=True),
        sa.Column("reason_code", sa.String(80), nullable=True),
        sa.Column("note", sa.String(2000), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('confirm', 'reject', 'correct')",
            name="ck_identification_review_decision",
        ),
    )
    for column in (
        "tenant_id",
        "company_identification_id",
        "decision",
        "reviewed_by",
        "reviewed_at",
    ):
        op.create_index(f"ix_identification_reviews_{column}", "identification_reviews", [column])

    op.create_table(
        "provider_usage",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("operation", sa.String(50), nullable=False),
        sa.Column("request_key", sa.String(200), nullable=False),
        sa.Column("provider_request_id", sa.String(300), nullable=True),
        sa.Column("response_status", sa.String(40), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_class", sa.String(100), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_provider_usage_latency"),
        sa.CheckConstraint("units >= 0", name="ck_provider_usage_units"),
        sa.CheckConstraint("estimated_cost >= 0", name="ck_provider_usage_estimated_cost"),
        sa.CheckConstraint("retry_count >= 0", name="ck_provider_usage_retry_count"),
    )
    for column in (
        "tenant_id",
        "provider",
        "operation",
        "request_key",
        "response_status",
        "cache_hit",
        "created_at",
    ):
        op.create_index(f"ix_provider_usage_{column}", "provider_usage", [column])


def downgrade() -> None:
    op.drop_table("provider_usage")
    op.drop_table("identification_reviews")
    op.drop_table("company_identifications")
    op.drop_table("network_observations")
