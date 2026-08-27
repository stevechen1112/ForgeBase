"""Add durable SLO snapshots and incident lifecycle.

Revision ID: 0094_slo_incident_console
Revises: 0093_privacy_operations
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0094_slo_incident_console"
down_revision = "0093_privacy_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_level_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sampled_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('healthy', 'at_risk', 'breached')",
            name="ck_service_level_snapshot_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "operational_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_key", sa.String(length=100), nullable=False),
        sa.Column("incident_type", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_notified_at", sa.DateTime(), nullable=True),
        sa.Column("notification_error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "severity IN ('warning', 'critical')",
            name="ck_operational_incident_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved')",
            name="ck_operational_incident_status",
        ),
        sa.CheckConstraint("occurrence_count >= 1", name="ck_incident_occurrences"),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_key", name="uq_operational_incidents_key"),
    )
    op.create_table(
        "operational_incident_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "action IN ('opened', 'observed', 'reopened', 'acknowledged', 'resolved', "
            "'notification_sent', 'notification_failed')",
            name="ck_operational_incident_event_action",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["incident_id"], ["operational_incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for table, columns in {
        "service_level_snapshots": ("status", "sampled_at"),
        "operational_incidents": (
            "incident_key",
            "incident_type",
            "severity",
            "status",
            "first_seen_at",
            "last_seen_at",
        ),
        "operational_incident_events": ("incident_id", "action", "created_at"),
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table, columns in reversed(
        list(
            {
                "service_level_snapshots": ("status", "sampled_at"),
                "operational_incidents": (
                    "incident_key",
                    "incident_type",
                    "severity",
                    "status",
                    "first_seen_at",
                    "last_seen_at",
                ),
                "operational_incident_events": ("incident_id", "action", "created_at"),
            }.items()
        )
    ):
        for column in reversed(columns):
            op.drop_index(f"ix_{table}_{column}", table_name=table)
    op.drop_table("operational_incident_events")
    op.drop_table("operational_incidents")
    op.drop_table("service_level_snapshots")
