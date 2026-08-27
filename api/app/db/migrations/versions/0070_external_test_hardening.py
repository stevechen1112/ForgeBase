"""External-test email governance and synthetic-data classification.

Revision ID: 0070_external_test_hardening
Revises: 0069_rfq_sales_workspace
"""

import sqlalchemy as sa
from alembic import op

revision = "0070_external_test_hardening"
down_revision = "0069_rfq_sales_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_delivery_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(20), nullable=False, server_default="resend"),
        sa.Column("provider_event_id", sa.String(120), nullable=False),
        sa.Column("provider_message_id", sa.String(120), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("recipient_hash", sa.String(64), nullable=True),
        sa.Column("recipient_masked", sa.String(254), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("provider_event_id", name="uq_email_delivery_events_provider_event_id"),
    )
    for column in ("provider", "provider_event_id", "provider_message_id", "event_type", "recipient_hash", "occurred_at", "created_at"):
        op.create_index(f"ix_email_delivery_events_{column}", "email_delivery_events", [column])

    op.create_table(
        "email_suppressions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scope_key", sa.String(80), nullable=False, server_default="global"),
        sa.Column("email_hash", sa.String(64), nullable=False),
        sa.Column("email_masked", sa.String(254), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False, server_default="resend"),
        sa.Column("source_event_id", sa.String(120), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("scope_key", "email_hash", name="uq_email_suppression_scope_hash"),
    )
    for column in ("scope_key", "email_hash", "reason", "active"):
        op.create_index(f"ix_email_suppressions_{column}", "email_suppressions", [column])

    for table in ("rfq_requests", "visitors", "tracking_sessions", "tracking_events"):
        op.add_column(table, sa.Column("is_test_data", sa.Boolean(), nullable=False, server_default=sa.false()))
        op.add_column(table, sa.Column("test_run_id", sa.String(100), nullable=True))
        op.create_index(f"ix_{table}_is_test_data", table, ["is_test_data"])


def downgrade() -> None:
    for table in ("tracking_events", "tracking_sessions", "visitors", "rfq_requests"):
        op.drop_index(f"ix_{table}_is_test_data", table_name=table)
        op.drop_column(table, "test_run_id")
        op.drop_column(table, "is_test_data")
    op.drop_table("email_suppressions")
    op.drop_table("email_delivery_events")
