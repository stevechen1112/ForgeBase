"""
HubSpot CRM Integration — 1b.5.2

Sync contacts and deals to HubSpot via REST API v3 on RFQ submission.

Env vars:
  HUBSPOT_API_KEY  — Private App token (Bearer), required to enable sync
  HUBSPOT_PORTAL_ID — optional, for direct portal links in logs

Functions:
  sync_contact_to_hubspot(contact_id) — create/update HubSpot Contact
  sync_rfq_to_hubspot(rfq_id)         — create HubSpot Deal linked to contact
"""
import logging
import os
import uuid

import httpx

from app.db.session import get_session_ctx
from app.models.contact import Contact
from app.models.rfq_request import RFQRequest

logger = logging.getLogger(__name__)

HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY", "")
_BASE = "https://api.hubapi.com"
_CONTACTS_URL = f"{_BASE}/crm/v3/objects/contacts"
_DEALS_URL = f"{_BASE}/crm/v3/objects/deals"
_ASSOC_URL = f"{_BASE}/crm/v4/objects/deals/{{deal_id}}/associations/contacts/{{contact_id}}"

_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {HUBSPOT_API_KEY}",
}


def _enabled() -> bool:
    return bool(HUBSPOT_API_KEY)


# ── Contact sync ──────────────────────────────────────────────────────────────

async def sync_contact_to_hubspot(contact_id: uuid.UUID) -> str | None:
    """
    Upsert a Contact to HubSpot by email.
    Returns the HubSpot contact ID string, or None on failure/disabled.
    Stores hubspot_contact_id back on the Contact model.
    """
    if not _enabled():
        return None
    try:
        async with get_session_ctx() as db:
            contact = await db.get(Contact, contact_id)
            if not contact:
                return None

            # Upsert via email (idempotent)
            payload = {
                "properties": {
                    "email": contact.email,
                    "firstname": (contact.full_name or "").split()[0] if contact.full_name else "",
                    "lastname": " ".join((contact.full_name or "").split()[1:]) or "",
                    "company": contact.company_name or "",
                    "phone": contact.phone or "",
                    "jobtitle": contact.job_title or "",
                    "country": contact.country or "",
                    "hs_lead_status": "NEW",
                },
                "id": contact.hubspot_contact_id or None,
            }

            async with httpx.AsyncClient(timeout=15) as client:
                if contact.hubspot_contact_id:
                    # Update existing
                    resp = await client.patch(
                        f"{_CONTACTS_URL}/{contact.hubspot_contact_id}",
                        json={"properties": payload["properties"]},
                        headers=_HEADERS,
                    )
                    hs_id = contact.hubspot_contact_id
                else:
                    # Create via upsert-by-email
                    resp = await client.post(
                        f"{_CONTACTS_URL}",
                        json=payload,
                        headers=_HEADERS,
                    )
                    if resp.status_code == 409:
                        # Already exists — extract existing ID from error
                        data = resp.json()
                        hs_id = data.get("message", "").split(":")[-1].strip()
                    else:
                        resp.raise_for_status()
                        hs_id = resp.json().get("id")

            if hs_id:
                contact.hubspot_contact_id = str(hs_id)
                db.add(contact)
                await db.commit()
                logger.info("HubSpot contact synced: contact=%s hs_id=%s", contact_id, hs_id)
                return str(hs_id)
    except httpx.RequestError:
        logger.exception("sync_contact_to_hubspot request failed contact_id=%s", contact_id)
    except Exception:
        logger.exception("sync_contact_to_hubspot unexpected error contact_id=%s", contact_id)
    return None


# ── Deal sync ─────────────────────────────────────────────────────────────────

async def sync_rfq_to_hubspot(rfq_id: uuid.UUID) -> str | None:
    """
    Create a HubSpot Deal for an RFQ and associate it with the contact.
    Returns the HubSpot deal ID string, or None on failure/disabled.
    Stores hubspot_deal_id back on the RFQRequest model.
    """
    if not _enabled():
        return None
    try:
        async with get_session_ctx() as db:
            rfq = await db.get(RFQRequest, rfq_id)
            if not rfq:
                return None

            # Ensure contact is synced first
            hs_contact_id: str | None = None
            if rfq.contact_id:
                contact = await db.get(Contact, rfq.contact_id)
                if contact:
                    hs_contact_id = contact.hubspot_contact_id
                    if not hs_contact_id:
                        hs_contact_id = await sync_contact_to_hubspot(rfq.contact_id)

            # Map priority → HubSpot deal priority
            pipeline_stage = {
                "urgent": "appointmentscheduled",
                "high": "qualifiedtobuy",
                "normal": "presentationscheduled",
            }.get(rfq.priority, "presentationscheduled")

            deal_payload = {
                "properties": {
                    "dealname": rfq.rfq_number,
                    "pipeline": "default",
                    "dealstage": pipeline_stage,
                    "amount": "",
                    "description": f"ForgeBase RFQ {rfq.rfq_number} | Intent score: {rfq.intent_score_at_submit}",
                    "forgebase_rfq_id": str(rfq.id),
                    "forgebase_rfq_status": rfq.status,
                },
            }

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    _DEALS_URL,
                    json=deal_payload,
                    headers=_HEADERS,
                )
                resp.raise_for_status()
                deal_data = resp.json()
                hs_deal_id = deal_data.get("id")

                # Associate deal with contact
                if hs_deal_id and hs_contact_id:
                    assoc_url = _ASSOC_URL.format(
                        deal_id=hs_deal_id, contact_id=hs_contact_id
                    )
                    assoc_payload = [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}]
                    await client.put(assoc_url, json=assoc_payload, headers=_HEADERS)

            if hs_deal_id:
                rfq.hubspot_deal_id = str(hs_deal_id)
                db.add(rfq)
                await db.commit()
                logger.info("HubSpot deal synced: rfq=%s hs_deal_id=%s", rfq_id, hs_deal_id)
                return str(hs_deal_id)
    except httpx.RequestError:
        logger.exception("sync_rfq_to_hubspot request failed rfq_id=%s", rfq_id)
    except Exception:
        logger.exception("sync_rfq_to_hubspot unexpected error rfq_id=%s", rfq_id)
    return None
