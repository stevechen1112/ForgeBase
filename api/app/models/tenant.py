import uuid
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlmodel import SQLModel, Field
from sqlalchemy import String, Column, DateTime

from app.core.datetime import utcnow_naive


class PlanTier(str, Enum):
    starter = "starter"
    professional = "professional"


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=200)
    slug: str = Field(max_length=100, unique=True, index=True)
    plan: str = Field(default="starter", sa_type=String)
    is_active: bool = Field(default=True)

    # Quota fields (values synced from PLAN_MATRIX on plan change)
    max_products: Optional[int] = Field(default=50)
    max_admins: Optional[int] = Field(default=2)

    # PayPal billing
    paypal_subscription_id: Optional[str] = Field(default=None, max_length=100)
    paypal_payer_email: Optional[str] = Field(default=None, max_length=255)

    created_at: datetime = Field(
        default_factory=utcnow_naive,
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=utcnow_naive,
        sa_column=Column(DateTime(timezone=True)),
    )
