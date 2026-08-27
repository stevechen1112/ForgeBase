import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class SiteBuild(SQLModel, table=True):
    """Internal delivery workflow from template selection to controlled publish."""

    __tablename__ = "site_builds"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_site_builds_tenant_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    template_key: str = Field(default="handtool-company", max_length=80, index=True)
    status: str = Field(default="draft", max_length=30, index=True)
    primary_domain: str | None = Field(default=None, max_length=255, index=True, unique=True)
    locales_json: str = Field(default='["en"]')
    customization_json: str = Field(default="{}")
    cms_connected: bool = Field(default=False)
    readiness_json: str = Field(default="{}")
    # Delivery state is intentionally separate from the technical publish
    # state above.  A site can be technically ready while it is still waiting
    # for a customer review or formal handoff.
    delivery_stage: str = Field(default="intake", max_length=30, index=True)
    delivery_owner_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", index=True
    )
    target_launch_at: datetime | None = Field(default=None, index=True)
    handoff_at: datetime | None = Field(default=None)
    acceptance_status: str = Field(default="pending", max_length=30, index=True)
    internal_note: str | None = Field(default=None, max_length=4000)
    published_at: datetime | None = Field(default=None)
    last_error: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
