"""
IntegrationCredential — per-tenant encrypted credential store.

One row per (tenant_id, service, credential_key).
Values are AES-encrypted via app.core.encryption.

tenant_id = NULL  →  single-tenant / global (current mode)
tenant_id = str   →  future SaaS multi-tenant (org UUID as string)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class IntegrationCredential(SQLModel, table=True):
    __tablename__ = "integration_credentials"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # NULL means global / single-tenant; set to org UUID string for SaaS
    tenant_id: Optional[str] = Field(default=None, index=True)

    # e.g. "linkedin" | "hubspot" | "sendgrid" | "resend" | …
    service: str = Field(index=True)

    # e.g. "access_token" | "ad_account_id" | "api_key" | …
    credential_key: str

    # Fernet-encrypted plaintext value
    encrypted_value: str

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
