import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class ServiceLevelSnapshot(SQLModel, table=True):
    """Durable point-in-time SLO evaluation; not an external uptime claim."""

    __tablename__ = "service_level_snapshots"
    __table_args__ = (
        CheckConstraint(
            "status IN ('healthy', 'at_risk', 'breached')",
            name="ck_service_level_snapshot_status",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: str = Field(max_length=20, index=True)
    metrics: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    sampled_at: datetime = Field(default_factory=utcnow_naive, index=True)


class OperationalIncident(SQLModel, table=True):
    """Persistent incident lifecycle replacing process-local alert dedupe."""

    __tablename__ = "operational_incidents"
    __table_args__ = (
        UniqueConstraint("incident_key", name="uq_operational_incidents_key"),
        CheckConstraint(
            "severity IN ('warning', 'critical')",
            name="ck_operational_incident_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved')",
            name="ck_operational_incident_status",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    incident_key: str = Field(max_length=100, index=True)
    incident_type: str = Field(max_length=60, index=True)
    severity: str = Field(max_length=20, index=True)
    status: str = Field(default="open", max_length=20, index=True)
    title: str = Field(max_length=200)
    summary: str = Field(max_length=1000)
    metrics: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict)
    )
    occurrence_count: int = Field(default=1, ge=1)
    first_seen_at: datetime = Field(default_factory=utcnow_naive, index=True)
    last_seen_at: datetime = Field(default_factory=utcnow_naive, index=True)
    acknowledged_at: datetime | None = Field(default=None)
    acknowledged_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    resolved_at: datetime | None = Field(default=None)
    resolved_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    last_notified_at: datetime | None = Field(default=None)
    notification_error: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class OperationalIncidentEvent(SQLModel, table=True):
    """Append-only incident decisions and automated state transitions."""

    __tablename__ = "operational_incident_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('opened', 'observed', 'reopened', 'acknowledged', 'resolved', "
            "'notification_sent', 'notification_failed')",
            name="ck_operational_incident_event_action",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    incident_id: uuid.UUID = Field(
        foreign_key="operational_incidents.id", ondelete="CASCADE", index=True
    )
    actor_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    action: str = Field(max_length=30, index=True)
    note: str | None = Field(default=None, max_length=1000)
    detail: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict)
    )
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
