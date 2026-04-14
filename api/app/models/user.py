import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import String, Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from enum import Enum


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
    full_name: str = Field(max_length=100)
    role: str = Field(default="marketing_manager", sa_type=String)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    tenant_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=utcnow_naive,
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=utcnow_naive,
        sa_column=Column(DateTime(timezone=True)),
    )
    last_login_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
