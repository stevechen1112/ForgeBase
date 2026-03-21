"""
2.1.6 LinkedIn Audience 同步
LinkedIn Marketing API v2 — Matched Audiences (DMP Segments)

Supports:
  - Company name list upload  (userGeneratedAudience type: COMPANY)
  - Email list upload          (userGeneratedAudience type: EMAIL)

References:
  https://learn.microsoft.com/en-us/linkedin/marketing/integrations/matched-audiences/
"""
from __future__ import annotations

import hashlib
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

LI_API_BASE = "https://api.linkedin.com/v2"
LI_DMP_BASE = "https://api.linkedin.com/v2/dmpSegments"


# ---------------------------------------------------------------------------
# Credential resolution: DB first, env-var fallback
# ---------------------------------------------------------------------------

async def _resolve_credential(key: str, env_value: str,
                               tenant_id: Optional[str] = None) -> str:
    """Look up a LinkedIn credential from DB; fallback to env var."""
    try:
        from app.db.session import get_session_ctx
        from app.core.encryption import decrypt
        from app.models.integration_credential import IntegrationCredential
        from sqlmodel import select

        async with get_session_ctx() as db:
            stmt = select(IntegrationCredential).where(
                IntegrationCredential.service == "linkedin",
                IntegrationCredential.credential_key == key,
                IntegrationCredential.tenant_id == tenant_id,
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row:
                return decrypt(row.encrypted_value)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not resolve credential '%s' from DB: %s", key, exc)
    return env_value


async def get_access_token(tenant_id: Optional[str] = None) -> str:
    return await _resolve_credential("access_token", settings.LINKEDIN_ACCESS_TOKEN, tenant_id)


async def get_ad_account_id(tenant_id: Optional[str] = None) -> str:
    return await _resolve_credential("ad_account_id", settings.LINKEDIN_AD_ACCOUNT_ID, tenant_id)


async def is_configured(tenant_id: Optional[str] = None) -> bool:
    """Return True if both LinkedIn credentials are available (DB or env)."""
    token = await get_access_token(tenant_id)
    account_id = await get_ad_account_id(tenant_id)
    return bool(token and account_id)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _auth_headers(tenant_id: Optional[str] = None) -> dict:
    token = await get_access_token(tenant_id)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202401",
    }


def _sha256_email(email: str) -> str:
    """Normalise and SHA-256 hash an email address (LinkedIn requirement)."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


# ---------------------------------------------------------------------------
# DMP Segment management
# ---------------------------------------------------------------------------

async def create_dmp_segment(
    name: str,
    audience_type: str = "EMAIL",
    description: str = "",
    tenant_id: Optional[str] = None,
) -> Optional[str]:
    """
    Create a new LinkedIn DMP segment and return its segment_id.
    audience_type: "EMAIL" | "COMPANY"
    """
    token = await get_access_token(tenant_id)
    account_id = await get_ad_account_id(tenant_id)

    if not token:
        logger.warning("LINKEDIN_ACCESS_TOKEN not configured — skipping create_dmp_segment")
        return None
    if not account_id:
        logger.warning("LINKEDIN_AD_ACCOUNT_ID not configured — skipping create_dmp_segment")
        return None

    payload = {
        "name": name,
        "description": description,
        "type": "FILE",
        "account": f"urn:li:sponsoredAccount:{account_id}",
        "destinations": [{"destination": "LINKEDIN"}],
        "userGeneratedAudience": {"format": audience_type},
    }

    try:
        headers = await _auth_headers(tenant_id)
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(LI_DMP_BASE, headers=headers, json=payload)
            if res.status_code == 201:
                segment_id: str = res.json().get("id", "")
                logger.info("Created LinkedIn DMP segment %s id=%s", name, segment_id)
                return segment_id
            logger.error("LinkedIn create segment error %s: %s", res.status_code, res.text[:300])
    except Exception as exc:  # noqa: BLE001
        logger.error("LinkedIn create_dmp_segment exception: %s", exc)
    return None


async def upload_emails_to_segment(segment_id: str, emails: list[str],
                                   tenant_id: Optional[str] = None) -> bool:
    """
    Upload a list of email addresses (SHA-256 hashed) to a LinkedIn DMP segment.
    LinkedIn accepts up to 100k records per call; caller should batch.
    """
    token = await get_access_token(tenant_id)
    if not token:
        logger.warning("LINKEDIN_ACCESS_TOKEN not configured — skipping upload_emails_to_segment")
        return False

    hashed = [_sha256_email(e) for e in emails if e]
    if not hashed:
        return True  # nothing to do

    payload = {
        "elements": [
            {"userIds": [{"idType": "SHA256_EMAIL", "idValue": h}]}
            for h in hashed
        ]
    }
    url = f"{LI_DMP_BASE}/{segment_id}/users"

    try:
        headers = await _auth_headers(tenant_id)
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code in (200, 201, 204):
                logger.info("Uploaded %d emails to LinkedIn segment %s", len(hashed), segment_id)
                return True
            logger.error("LinkedIn upload emails error %s: %s", res.status_code, res.text[:300])
    except Exception as exc:  # noqa: BLE001
        logger.error("LinkedIn upload_emails_to_segment exception: %s", exc)
    return False


async def upload_companies_to_segment(segment_id: str, company_names: list[str],
                                      tenant_id: Optional[str] = None) -> bool:
    """
    Upload a list of company names to a LinkedIn DMP segment.
    LinkedIn uses company name matching internally.
    """
    token = await get_access_token(tenant_id)
    if not token:
        logger.warning("LINKEDIN_ACCESS_TOKEN not configured — skipping upload_companies_to_segment")
        return False

    names = [c for c in company_names if c]
    if not names:
        return True

    payload = {
        "elements": [
            {"userIds": [{"idType": "COMPANY_NAME", "idValue": n}]}
            for n in names
        ]
    }
    url = f"{LI_DMP_BASE}/{segment_id}/users"

    try:
        headers = await _auth_headers(tenant_id)
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code in (200, 201, 204):
                logger.info("Uploaded %d companies to LinkedIn segment %s", len(names), segment_id)
                return True
            logger.error("LinkedIn upload companies error %s: %s", res.status_code, res.text[:300])
    except Exception as exc:  # noqa: BLE001
        logger.error("LinkedIn upload_companies_to_segment exception: %s", exc)
    return False


async def get_dmp_segment(segment_id: str, tenant_id: Optional[str] = None) -> Optional[dict]:
    """Fetch a DMP segment record from LinkedIn API."""
    token = await get_access_token(tenant_id)
    if not token:
        return None
    try:
        headers = await _auth_headers(tenant_id)
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(f"{LI_DMP_BASE}/{segment_id}", headers=headers)
            if res.status_code == 200:
                return res.json()
    except Exception as exc:  # noqa: BLE001
        logger.error("LinkedIn get_dmp_segment exception: %s", exc)
    return None
