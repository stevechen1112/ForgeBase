import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class Visitor(SQLModel, table=True):
    """
    Anonymous visitor identified by first-party cookie visitor_id.
    One record per unique visitor. Stores first-party activity facts only.
    """
    __tablename__ = "visitors"

    visitor_id: uuid.UUID = Field(primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    # visitor_id is generated client-side and stored in first-party cookie

    first_seen: datetime = Field(default_factory=utcnow_naive)
    last_seen: datetime = Field(default_factory=utcnow_naive)
    last_activity_at: datetime = Field(default_factory=utcnow_naive)

    total_visits: int = Field(default=1)
    total_page_views: int = Field(default=0)

    # Device & location (server-side enrichment)
    device_type: Optional[str] = Field(default=None, max_length=20)
    # "desktop" | "mobile" | "tablet"
    country: Optional[str] = Field(default=None, max_length=2)
    # ISO 3166-1 alpha-2

    # Identity: linked contact after form submission
    contact_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="contacts.id",
        ondelete="SET NULL",
        index=True,
    )

    # Analytics consent lifecycle. Detailed audit uses a keyed hash rather
    # than retaining the raw anonymous browser identifier.
    analytics_consent_status: str = Field(default="unknown", max_length=20, index=True)
    consent_updated_at: Optional[datetime] = Field(default=None)

    is_test_data: bool = Field(default=False, index=True)
    test_run_id: Optional[str] = Field(default=None, max_length=100)

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
