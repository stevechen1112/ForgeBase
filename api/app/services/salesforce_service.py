"""
2.4.1 Salesforce CRM 整合 — Salesforce REST API Service

OAuth 2.0 Username-Password flow (server-to-server).
Supports:
  - Create / Upsert Contact
  - Create / Upsert Opportunity (linked to Contact via Account)
  - Query records (SOQL)

Required env vars:
  SF_CLIENT_ID
  SF_CLIENT_SECRET
  SF_USERNAME
  SF_PASSWORD
  SF_SECURITY_TOKEN  (appended to password for login)
  SF_INSTANCE_URL    (e.g. "https://yourorg.my.salesforce.com")
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SF_LOGIN_URL = "https://login.salesforce.com/services/oauth2/token"
# For sandbox: "https://test.salesforce.com/services/oauth2/token"


# ---------------------------------------------------------------------------
# Token management (simple in-memory cache, refreshes on 401)
# ---------------------------------------------------------------------------

_cached_token: Optional[str] = None
_cached_instance: Optional[str] = None


async def _get_token() -> tuple[str, str]:
    """Return (access_token, instance_url). Raises RuntimeError if login fails."""
    global _cached_token, _cached_instance
    if _cached_token and _cached_instance:
        return _cached_token, _cached_instance

    token, instance = await _login()
    _cached_token = token
    _cached_instance = instance
    return token, instance


async def _login() -> tuple[str, str]:
    if not settings.SF_CLIENT_ID:
        raise RuntimeError("SF_CLIENT_ID not configured")

    payload = {
        "grant_type": "password",
        "client_id": settings.SF_CLIENT_ID,
        "client_secret": settings.SF_CLIENT_SECRET,
        "username": settings.SF_USERNAME,
        "password": settings.SF_PASSWORD + settings.SF_SECURITY_TOKEN,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(SF_LOGIN_URL, data=payload)
        if res.status_code not in (200, 201):
            raise RuntimeError(f"Salesforce login failed {res.status_code}: {res.text[:200]}")
        data = res.json()
        return data["access_token"], data["instance_url"]


def _clear_token() -> None:
    global _cached_token, _cached_instance
    _cached_token = None
    _cached_instance = None


async def _sf_request(
    method: str,
    path: str,
    *,
    json_body: Optional[dict] = None,
    params: Optional[dict] = None,
    retry: bool = True,
) -> dict:
    """Low-level SF REST call. Auto-refreshes token on 401."""
    try:
        token, instance = await _get_token()
    except RuntimeError as exc:
        logger.error("Salesforce auth failed: %s", exc)
        return {"error": str(exc)}

    url = f"{instance}/services/data/v60.0{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.request(method, url, headers=headers, json=json_body, params=params)
            if res.status_code == 401 and retry:
                _clear_token()
                return await _sf_request(method, path, json_body=json_body, params=params, retry=False)
            if res.status_code in (200, 201, 204):
                return res.json() if res.content else {"success": True}
            logger.error("Salesforce %s %s → %s: %s", method, path, res.status_code, res.text[:300])
            return {"error": res.text[:300], "status": res.status_code}
    except Exception as exc:  # noqa: BLE001
        logger.error("Salesforce request exception: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Contact operations
# ---------------------------------------------------------------------------

async def upsert_contact(
    email: str,
    first_name: str = "",
    last_name: str = "",
    company: str = "",
    phone: str = "",
    extra_fields: Optional[dict] = None,
) -> dict:
    """
    Upsert (create or update) a Salesforce Contact by email.
    Uses PATCH /sobjects/Contact/Email/{email} (external ID or composite upsert).

    Returns Salesforce response dict.
    """
    body: dict[str, Any] = {
        "Email": email,
        "FirstName": first_name,
        "LastName": last_name or email.split("@")[0],
        "Company": company,  # Note: Account name; Salesforce Contact field is AccountId
    }
    if phone:
        body["Phone"] = phone
    if extra_fields:
        body.update(extra_fields)

    # Upsert by Email as external ID
    path = f"/sobjects/Contact/Email/{email}"
    return await _sf_request("PATCH", path, json_body=body)


async def create_opportunity(
    name: str,
    stage: str = "Qualification",
    close_date: str = "2099-12-31",
    contact_id: Optional[str] = None,
    account_id: Optional[str] = None,
    amount: Optional[float] = None,
    description: str = "",
    extra_fields: Optional[dict] = None,
) -> dict:
    """
    Create a new Salesforce Opportunity.
    Returns created record including 'id'.
    """
    body: dict[str, Any] = {
        "Name": name,
        "StageName": stage,
        "CloseDate": close_date,
        "Description": description,
    }
    if amount is not None:
        body["Amount"] = amount
    if account_id:
        body["AccountId"] = account_id
    if extra_fields:
        body.update(extra_fields)

    result = await _sf_request("POST", "/sobjects/Opportunity", json_body=body)

    # Link to Contact via OpportunityContactRole
    if contact_id and result.get("id"):
        role_body = {
            "OpportunityId": result["id"],
            "ContactId": contact_id,
            "Role": "Economic Buyer",
            "IsPrimary": True,
        }
        await _sf_request("POST", "/sobjects/OpportunityContactRole", json_body=role_body)

    return result


async def query_records(soql: str) -> list[dict]:
    """Run a SOQL query and return records list."""
    result = await _sf_request("GET", "/query", params={"q": soql})
    return result.get("records", [])


async def get_contact_by_email(email: str) -> Optional[dict]:
    """Query a Contact by email address."""
    records = await query_records(
        f"SELECT Id, FirstName, LastName, Email, AccountId, OwnerId FROM Contact "
        f"WHERE Email = '{email}' LIMIT 1"
    )
    return records[0] if records else None


async def update_opportunity_stage(opportunity_id: str, stage: str) -> dict:
    """Update the StageName of an Opportunity (used in 2.4.2 reverse sync)."""
    return await _sf_request(
        "PATCH",
        f"/sobjects/Opportunity/{opportunity_id}",
        json_body={"StageName": stage},
    )
