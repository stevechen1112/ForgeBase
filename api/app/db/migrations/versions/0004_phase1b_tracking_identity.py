"""Phase 1b: add tracking, identity, and RFQ tables

Revision ID: 0004_phase1b_tracking_identity
Revises: 0003_page_brief_entity_page_fields
Create Date: 2026-03-14 00:00:00.000000

New tables:
  - contacts
  - visitors (FK → contacts, nullable)
  - tracking_sessions (FK → visitors)
  - tracking_events (FK → visitors, tracking_sessions)
  - rfq_requests (FK → contacts, visitors, applications, users)
  - rfq_product_links (FK → rfq_requests, products)
  - audience_tags
  - visitor_tag_links (FK → visitors, audience_tags)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_phase1b_tracking_identity"
down_revision: Union[str, None] = "0003_page_brief_entity_page_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── contacts ────────────────────────────────────────────────────────────────
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(100), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("company_name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("country", sa.String(50), nullable=True),
        sa.Column("job_title", sa.String(80), nullable=True),
        sa.Column("visitor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("intent_score_at_creation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hubspot_contact_id", sa.String(50), nullable=True),
        sa.Column("source_page", sa.String(500), nullable=True),
        sa.Column("how_did_you_find_us", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("email", name="uq_contacts_email"),
    )
    op.create_index("ix_contacts_email", "contacts", ["email"])

    # ── visitors ─────────────────────────────────────────────────────────────────
    op.create_table(
        "visitors",
        sa.Column("visitor_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("total_visits", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_page_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("intent_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("intent_stage", sa.String(20), nullable=False, server_default="'cold'"),
        sa.Column("device_type", sa.String(20), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stage_alert_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], name="fk_visitors_contact_id", ondelete="SET NULL"),
        sa.CheckConstraint("intent_stage IN ('cold','warm','hot','sales_ready')", name="ck_visitors_intent_stage"),
    )
    op.create_index("ix_visitors_intent_stage", "visitors", ["intent_stage"])
    op.create_index("ix_visitors_intent_score", "visitors", ["intent_score"])
    op.create_index("ix_visitors_contact_id", "visitors", ["contact_id"])

    # Add FK from contacts.visitor_id → visitors (deferred to avoid circular)
    op.create_foreign_key(
        "fk_contacts_visitor_id",
        "contacts", "visitors",
        ["visitor_id"], ["visitor_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_contacts_visitor_id", "contacts", ["visitor_id"])

    # ── tracking_sessions ────────────────────────────────────────────────────────
    op.create_table(
        "tracking_sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("visitor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("entry_page", sa.String(500), nullable=True),
        sa.Column("exit_page", sa.String(500), nullable=True),
        sa.Column("traffic_source", sa.String(30), nullable=True),
        sa.Column("referrer", sa.String(500), nullable=True),
        sa.Column("utm_source", sa.String(100), nullable=True),
        sa.Column("utm_medium", sa.String(100), nullable=True),
        sa.Column("utm_campaign", sa.String(100), nullable=True),
        sa.Column("utm_term", sa.String(100), nullable=True),
        sa.Column("utm_content", sa.String(100), nullable=True),
        sa.Column("device_type", sa.String(20), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"], name="fk_sessions_visitor_id", ondelete="CASCADE"),
    )
    op.create_index("ix_tracking_sessions_visitor_id", "tracking_sessions", ["visitor_id"])
    op.create_index("ix_tracking_sessions_start_time", "tracking_sessions", ["start_time"])

    # ── tracking_events ──────────────────────────────────────────────────────────
    op.create_table(
        "tracking_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_name", sa.String(50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("visitor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("page_url", sa.String(500), nullable=True),
        sa.Column("page_type", sa.String(40), nullable=True),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("locale", sa.String(5), nullable=True, server_default="'en'"),
        sa.Column("referrer", sa.String(500), nullable=True),
        sa.Column("traffic_source", sa.String(30), nullable=True),
        sa.Column("campaign_id", sa.String(200), nullable=True),
        sa.Column("user_agent", sa.String(300), nullable=True),
        sa.Column("device_type", sa.String(20), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("properties", sa.Text(), nullable=True),
        sa.Column("score_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["session_id"], ["tracking_sessions.session_id"], name="fk_events_session_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"], name="fk_events_visitor_id", ondelete="SET NULL"),
    )
    op.create_index("ix_tracking_events_event_name", "tracking_events", ["event_name"])
    op.create_index("ix_tracking_events_visitor_id", "tracking_events", ["visitor_id"])
    op.create_index("ix_tracking_events_session_id", "tracking_events", ["session_id"])
    op.create_index("ix_tracking_events_timestamp", "tracking_events", ["timestamp"])

    # ── rfq_requests ─────────────────────────────────────────────────────────────
    op.create_table(
        "rfq_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rfq_number", sa.String(30), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("visitor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("form_data", sa.Text(), nullable=True),
        sa.Column("intent_score_at_submit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'new'"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("priority", sa.String(10), nullable=False, server_default="'normal'"),
        sa.Column("source_page", sa.String(500), nullable=True),
        sa.Column("hubspot_deal_id", sa.String(50), nullable=True),
        sa.Column("assigned_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_24h_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalation_48h_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("rfq_number", name="uq_rfq_number"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], name="fk_rfq_contact_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"], name="fk_rfq_visitor_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name="fk_rfq_application_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], name="fk_rfq_assigned_to", ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('new','assigned','in_progress','quoted','won','lost','expired')",
            name="ck_rfq_status",
        ),
        sa.CheckConstraint("priority IN ('normal','high','urgent')", name="ck_rfq_priority"),
    )
    op.create_index("ix_rfq_requests_status", "rfq_requests", ["status"])
    op.create_index("ix_rfq_requests_rfq_number", "rfq_requests", ["rfq_number"])
    op.create_index("ix_rfq_requests_contact_id", "rfq_requests", ["contact_id"])
    op.create_index("ix_rfq_requests_assigned_to", "rfq_requests", ["assigned_to"])

    # ── rfq_product_links ────────────────────────────────────────────────────────
    op.create_table(
        "rfq_product_links",
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfq_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
    )

    # ── audience_tags ────────────────────────────────────────────────────────────
    op.create_table(
        "audience_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(200), nullable=False, server_default="''"),
        sa.Column("rule_type", sa.String(20), nullable=False, server_default="'manual'"),
        sa.Column("rule_config", sa.Text(), nullable=False, server_default="'{}'"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("name", name="uq_audience_tags_name"),
    )

    # ── visitor_tag_links ────────────────────────────────────────────────────────
    op.create_table(
        "visitor_tag_links",
        sa.Column("visitor_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tagged_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("tagged_by", sa.String(20), nullable=False, server_default="'manual'"),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["audience_tags.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("visitor_tag_links")
    op.drop_table("audience_tags")
    op.drop_table("rfq_product_links")
    op.drop_table("rfq_requests")
    op.drop_table("tracking_events")
    op.drop_table("tracking_sessions")
    op.drop_index("ix_contacts_visitor_id", table_name="contacts")
    op.drop_constraint("fk_contacts_visitor_id", "contacts", type_="foreignkey")
    op.drop_index("ix_visitors_contact_id", table_name="visitors")
    op.drop_index("ix_visitors_intent_score", table_name="visitors")
    op.drop_index("ix_visitors_intent_stage", table_name="visitors")
    op.drop_table("visitors")
    op.drop_index("ix_contacts_email", table_name="contacts")
    op.drop_table("contacts")
