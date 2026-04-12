import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field


class TrackingSession(SQLModel, table=True):
    """
    A browsing session for one visitor. Session ends after 30 min inactivity
    (managed client-side). One visitor can have many sessions.
    Spec: 1b.2.2
    """
    __tablename__ = "tracking_sessions"

    session_id: uuid.UUID = Field(primary_key=True)
    # session_id is generated client-side per session (sessionStorage)

    visitor_id: uuid.UUID = Field(
        foreign_key="visitors.visitor_id", index=True
    )

    tenant_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="tenants.id", index=True
    )

    start_time: datetime = Field(default_factory=utcnow_naive)
    end_time: Optional[datetime] = Field(default=None)
    # last event time in session; updated on each event

    page_count: int = Field(default=0)
    entry_page: Optional[str] = Field(default=None, max_length=500)
    exit_page: Optional[str] = Field(default=None, max_length=500)

    # Traffic attribution
    traffic_source: Optional[str] = Field(default=None, max_length=30)
    # "organic" | "paid" | "direct" | "referral" | "social"
    referrer: Optional[str] = Field(default=None, max_length=500)
    utm_source: Optional[str] = Field(default=None, max_length=100)
    utm_medium: Optional[str] = Field(default=None, max_length=100)
    utm_campaign: Optional[str] = Field(default=None, max_length=100)
    utm_term: Optional[str] = Field(default=None, max_length=100)
    utm_content: Optional[str] = Field(default=None, max_length=100)

    device_type: Optional[str] = Field(default=None, max_length=20)
    country: Optional[str] = Field(default=None, max_length=2)

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
