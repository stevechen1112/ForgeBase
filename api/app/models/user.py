import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class UserRole(str, Enum):
    admin = "admin"
    owner = "owner"
    marketing_manager = "marketing_manager"
    sales = "sales"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str
    full_name: Optional[str] = Field(default=None, max_length=100)
    role: str = Field(default="marketing_manager", sa_type=String)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    tenant_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=utcnow_naive,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow_naive,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_login_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
