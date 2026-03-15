"""
Google Ads Customer Match Sync — 1b.5.4

Daily batch job: collects emails of hot/sales_ready visitors and uploads them
to a Google Ads Customer Match user list (spec 12.8.3).

Required env vars:
  GOOGLE_ADS_DEVELOPER_TOKEN   — Google Ads API developer token
  GOOGLE_ADS_CUSTOMER_ID       — 10-digit customer ID (no dashes)
  GOOGLE_ADS_CLIENT_ID         — OAuth2 client ID
  GOOGLE_ADS_CLIENT_SECRET     — OAuth2 client secret
  GOOGLE_ADS_REFRESH_TOKEN     — offline OAuth2 refresh token
  GOOGLE_ADS_CUSTOMER_LIST_ID  — numeric user list ID to populate

API used: Google Ads REST API v17 (offlineUserDataJobs).
"""
import hashlib
import logging
import os

import httpx
from sqlmodel import select

from app.db.session import get_session_ctx
from app.models.contact import Contact
from app.models.visitor import Visitor

logger = logging.getLogger(__name__)

_DEV_TOKEN     = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
_CUSTOMER_ID   = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
_CLIENT_ID     = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
_REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
_LIST_ID       = os.getenv("GOOGLE_ADS_CUSTOMER_LIST_ID", "")

_ADS_API_VERSION = "v17"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_ADS_BASE  = "https://googleads.googleapis.com"


def _enabled() -> bool:
    return all([
        _DEV_TOKEN, _CUSTOMER_ID, _CLIENT_ID,
        _CLIENT_SECRET, _REFRESH_TOKEN, _LIST_ID,
    ])


def _sha256_hash(value: str) -> str:
    """Normalize (strip + lowercase) and SHA-256 hash for Customer Match."""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


async def _get_access_token() -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(_TOKEN_URL, data={
            "client_id":     _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
            "refresh_token": _REFRESH_TOKEN,
            "grant_type":    "refresh_token",
        })
        resp.raise_for_status()
        return resp.json()["access_token"]


async def sync_high_intent_to_customer_match() -> dict:
    """
    Collect hashed emails of hot/sales_ready visitors and upload to Google Ads.
    Triggered daily by APScheduler at 03:00 UTC.
    Returns a stats dict.
    """
    if not _enabled():
        logger.debug("google_ads: not configured — skipping customer match sync")
        return {"skipped": True}

    # 1. Collect hashed emails from high-intent visitors
    hashed_emails: list[str] = []
    async with get_session_ctx() as db:
        result = await db.exec(
            select(Visitor, Contact)
            .join(Contact, Visitor.contact_id == Contact.id)  # type: ignore
            .where(Visitor.intent_stage.in_(["hot", "sales_ready"]))  # type: ignore
        )
        for _visitor, contact in result.all():
            if contact.email:
                hashed_emails.append(_sha256_hash(contact.email))

    if not hashed_emails:
        logger.info("google_ads: no eligible emails for customer match")
        return {"uploaded": 0}

    # 2. Obtain OAuth2 access token
    try:
        access_token = await _get_access_token()
    except Exception as exc:
        logger.error("google_ads: failed to get access token: %s", exc)
        return {"error": str(exc)}

    hdrs = {
        "Authorization":  f"Bearer {access_token}",
        "developer-token": _DEV_TOKEN,
        "Content-Type":   "application/json",
    }

    # 3. Create an offline user data job
    create_url = (
        f"{_ADS_BASE}/{_ADS_API_VERSION}"
        f"/customers/{_CUSTOMER_ID}/offlineUserDataJobs"
    )
    job_body = {
        "job": {
            "type": "CUSTOMER_MATCH_USER_LIST",
            "customerMatchUserListMetadata": {
                "userList": f"customers/{_CUSTOMER_ID}/userLists/{_LIST_ID}",
            },
        }
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(create_url, json=job_body, headers=hdrs)
        if r.status_code >= 400:
            logger.error(
                "google_ads: create job failed %d %s", r.status_code, r.text[:300]
            )
            return {"error": r.text[:200]}
        job_name = r.json().get("resourceName", "")

    # 4. Add hashed email operations
    add_url = f"{_ADS_BASE}/{_ADS_API_VERSION}/{job_name}:addOperations"
    operations = [
        {"create": {"userIdentifiers": [{"hashedEmail": h}]}}
        for h in hashed_emails
    ]
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            add_url,
            json={"operations": operations, "enablePartialFailure": True},
            headers=hdrs,
        )
        if r.status_code >= 400:
            logger.error(
                "google_ads: add operations failed %d %s",
                r.status_code, r.text[:300],
            )
            return {"error": r.text[:200]}

    # 5. Run the job (async on Google's side)
    run_url = f"{_ADS_BASE}/{_ADS_API_VERSION}/{job_name}:run"
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(run_url, json={}, headers=hdrs)

    logger.info(
        "google_ads: customer match uploaded %d emails", len(hashed_emails)
    )
    return {"uploaded": len(hashed_emails)}
