"""
Integration Credentials API

GET    /api/v1/admin/integrations/status            — env-var status of all integrations
GET    /api/v1/admin/integrations/{service}         — list credential keys stored in DB for a service
PUT    /api/v1/admin/integrations/{service}/{key}   — create or update an encrypted credential
DELETE /api/v1/admin/integrations/{service}/{key}   — remove a credential from DB

Credentials are AES-encrypted (Fernet) before being stored in integration_credentials table.
Values are NEVER returned in plaintext — GET endpoints return only key names + masked preview.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_admin, require_content_editor
from app.core.encryption import decrypt, encrypt
from app.db.session import get_session
from app.models.integration_credential import IntegrationCredential
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/integrations/status")
async def get_integrations_status(
    _: User = Depends(require_content_editor),
):
    """
    Returns which integrations are configured (env vars present).
    Does not expose secret values — only whether they are set.
    """

    def _configured(*keys: str) -> bool:
        return all(bool(os.getenv(k)) for k in keys)

    def _masked(val: str, keep: int = 8) -> str | None:
        if not val:
            return None
        return val[:keep] + "..." if len(val) > keep else val

    measurement_id = os.getenv("NEXT_PUBLIC_GA_MEASUREMENT_ID", "")
    pixel_id       = os.getenv("META_PIXEL_ID", "")
    customer_id    = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
    webhook_urls   = [
        u.strip()
        for u in os.getenv("WEBHOOK_ENDPOINT_URLS", "").split(",")
        if u.strip()
    ]

    return {
        "ga4": {
            "configured":    bool(measurement_id),
            "measurement_id": _masked(measurement_id, 4),
        },
        "hubspot": {
            "configured": _configured("HUBSPOT_API_KEY"),
        },
        "google_ads": {
            "configured": _configured(
                "GOOGLE_ADS_DEVELOPER_TOKEN",
                "GOOGLE_ADS_CUSTOMER_ID",
                "GOOGLE_ADS_CLIENT_ID",
                "GOOGLE_ADS_CLIENT_SECRET",
                "GOOGLE_ADS_REFRESH_TOKEN",
                "GOOGLE_ADS_CUSTOMER_LIST_ID",
            ),
            "customer_id": customer_id or None,
        },
        "meta": {
            "configured": _configured("META_PIXEL_ID", "META_ACCESS_TOKEN"),
            "pixel_id":   pixel_id or None,
        },
        "webhook": {
            "configured":     bool(webhook_urls),
            "endpoint_count": len(webhook_urls),
            "endpoints": [
                (u[:40] + "...") if len(u) > 40 else u
                for u in webhook_urls
            ],
            "signing_enabled": _configured("WEBHOOK_SECRET"),
        },
        "smtp": {
            "configured": _configured("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"),
            "host":       os.getenv("SMTP_HOST") or None,
        },
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_credential(db: AsyncSession, service: str, key: str,
                          tenant_id: Optional[str] = None) -> Optional[IntegrationCredential]:
    stmt = select(IntegrationCredential).where(
        IntegrationCredential.service == service,
        IntegrationCredential.credential_key == key,
        IntegrationCredential.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _masked(value: str, keep: int = 6) -> str:
    return value[:keep] + "••••••" if len(value) > keep else "••••••"


# ── Schemas ───────────────────────────────────────────────────────────────────

class CredentialUpsert(BaseModel):
    value: str
    tenant_id: Optional[str] = None  # None = global / single-tenant


# ── Credential CRUD ───────────────────────────────────────────────────────────

@router.get("/integrations/{service}")
async def list_service_credentials(
    service: str,
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    """
    Return which credential keys are configured for a service.
    Values are masked — never returned in plaintext.
    """
    stmt = select(IntegrationCredential).where(
        IntegrationCredential.service == service,
        IntegrationCredential.tenant_id == tenant_id,
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "key": row.credential_key,
            "configured": True,
            "preview": _masked(decrypt(row.encrypted_value)),
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


@router.put("/integrations/{service}/{key}", status_code=status.HTTP_200_OK)
async def upsert_credential(
    service: str,
    key: str,
    body: CredentialUpsert,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Create or update an encrypted credential."""
    if not body.value.strip():
        raise HTTPException(status_code=422, detail="value must not be empty")

    encrypted = encrypt(body.value.strip())
    row = await _get_credential(db, service, key, body.tenant_id)

    from app.core.datetime import utcnow_naive
    if row:
        row.encrypted_value = encrypted
        row.updated_at = utcnow_naive()
    else:
        row = IntegrationCredential(
            service=service,
            credential_key=key,
            encrypted_value=encrypted,
            tenant_id=body.tenant_id,
        )

    db.add(row)
    await db.commit()
    return {"service": service, "key": key, "configured": True}


@router.delete("/integrations/{service}/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    service: str,
    key: str,
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Remove a credential from the DB. The env-var fallback still applies."""
    row = await _get_credential(db, service, key, tenant_id)
    if not row:
        raise HTTPException(status_code=404, detail="Credential not found")
    await db.delete(row)
    await db.commit()

