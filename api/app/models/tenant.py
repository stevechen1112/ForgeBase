import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"
    __table_args__ = (UniqueConstraint("slug", name="uq_tenants_slug"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=200)
    slug: str = Field(max_length=100, unique=True, index=True)
    # Operational capability controls, independent from commercial packaging.
    feature_overrides: dict[str, bool] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=utcnow_naive,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow_naive,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
