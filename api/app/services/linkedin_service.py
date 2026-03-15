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
# Helper
# ---------------------------------------------------------------------------

def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}",
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
) -> Optional[str]:
    """
    Create a new LinkedIn DMP segment and return its segment_id.
    audience_type: "EMAIL" | "COMPANY"
    """
    if not settings.LINKEDIN_ACCESS_TOKEN:
        logger.warning("LINKEDIN_ACCESS_TOKEN not configured — skipping create_dmp_segment")
        return None
    if not settings.LINKEDIN_AD_ACCOUNT_ID:
        logger.warning("LINKEDIN_AD_ACCOUNT_ID not configured — skipping create_dmp_segment")
        return None

    payload = {
        "name": name,
        "description": description,
        "type": "FILE",
        "account": f"urn:li:sponsoredAccount:{settings.LINKEDIN_AD_ACCOUNT_ID}",
        "destinations": [{"destination": "LINKEDIN"}],
        "userGeneratedAudience": {"format": audience_type},
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(LI_DMP_BASE, headers=_auth_headers(), json=payload)
            if res.status_code == 201:
                segment_id: str = res.json().get("id", "")
                logger.info("Created LinkedIn DMP segment %s id=%s", name, segment_id)
                return segment_id
            logger.error("LinkedIn create segment error %s: %s", res.status_code, res.text[:300])
    except Exception as exc:  # noqa: BLE001
        logger.error("LinkedIn create_dmp_segment exception: %s", exc)
    return None


async def upload_emails_to_segment(segment_id: str, emails: list[str]) -> bool:
    """
    Upload a list of email addresses (SHA-256 hashed) to a LinkedIn DMP segment.
    LinkedIn accepts up to 100k records per call; caller should batch.
    """
    if not settings.LINKEDIN_ACCESS_TOKEN:
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
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(url, headers=_auth_headers(), json=payload)
            if res.status_code in (200, 201, 204):
                logger.info("Uploaded %d emails to LinkedIn segment %s", len(hashed), segment_id)
                return True
            logger.error("LinkedIn upload emails error %s: %s", res.status_code, res.text[:300])
    except Exception as exc:  # noqa: BLE001
        logger.error("LinkedIn upload_emails_to_segment exception: %s", exc)
    return False


async def upload_companies_to_segment(segment_id: str, company_names: list[str]) -> bool:
    """
    Upload a list of company names to a LinkedIn DMP segment.
    LinkedIn uses company name matching internally.
    """
    if not settings.LINKEDIN_ACCESS_TOKEN:
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
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(url, headers=_auth_headers(), json=payload)
            if res.status_code in (200, 201, 204):
                logger.info("Uploaded %d companies to LinkedIn segment %s", len(names), segment_id)
                return True
            logger.error("LinkedIn upload companies error %s: %s", res.status_code, res.text[:300])
    except Exception as exc:  # noqa: BLE001
        logger.error("LinkedIn upload_companies_to_segment exception: %s", exc)
    return False


async def get_dmp_segment(segment_id: str) -> Optional[dict]:
    """Fetch a DMP segment record from LinkedIn API."""
    if not settings.LINKEDIN_ACCESS_TOKEN:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{LI_DMP_BASE}/{segment_id}",
                headers=_auth_headers(),
            )
            if res.status_code == 200:
                return res.json()
    except Exception as exc:  # noqa: BLE001
        logger.error("LinkedIn get_dmp_segment exception: %s", exc)
    return None
