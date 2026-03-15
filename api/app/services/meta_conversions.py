"""
Meta Conversions API — 1b.5.5

Server-side event forwarding to Meta (Facebook) Pixel via CAPI.
Runs alongside client-side Pixel for server-side deduplication.

Event mapping (spec 12.8.3):
  product_view  → ViewContent      (content_type=product)
  rfq_start     → InitiateCheckout
  rfq_submit    → Lead
  spec_download → AddToCart        (content_type=document)

Deduplication: pass event_id matching the client-side Pixel event_id.

Required env vars:
  META_PIXEL_ID       — numeric Meta Pixel ID (e.g. 123456789012345)
  META_ACCESS_TOKEN   — system user access token
"""
import hashlib
import logging
import os
import time
import uuid
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_PIXEL_ID     = os.getenv("META_PIXEL_ID", "")
_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
_API_VERSION  = "v18.0"

# Spec 12.8.3: ForgeBase event → Meta standard event name
_EVENT_MAP: dict[str, str] = {
    "product_view":  "ViewContent",
    "rfq_start":     "InitiateCheckout",
    "rfq_submit":    "Lead",
    "spec_download": "AddToCart",
}


def _enabled() -> bool:
    return bool(_PIXEL_ID and _ACCESS_TOKEN)


def _sha256(value: str) -> str:
    """Normalize and SHA-256 hash a PII value as required by Meta."""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


async def fire_meta_event(
    event_name: str,
    visitor_id: Optional[str] = None,
    email: Optional[str] = None,
    page_url: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    content_ids: Optional[list[str]] = None,
    event_id: Optional[str] = None,
) -> None:
    """
    Forward a single tracked event to Meta Conversions API.
    Silently returns for unmapped event names or if CAPI is not configured.
    """
    meta_event = _EVENT_MAP.get(event_name)
    if not meta_event or not _enabled():
        return

    event_id = event_id or str(uuid.uuid4())

    user_data: dict = {}
    if email:
        user_data["em"] = [_sha256(email)]
    if ip_address:
        user_data["client_ip_address"] = ip_address
    if user_agent:
        user_data["client_user_agent"] = user_agent
    if visitor_id:
        user_data["extern_id"] = visitor_id

    custom_data: dict = {
        "content_type": "document" if event_name == "spec_download" else "product"
    }
    if content_ids:
        custom_data["content_ids"] = content_ids

    payload = {
        "data": [{
            "event_name":       meta_event,
            "event_time":       int(time.time()),
            "event_id":         event_id,
            "event_source_url": page_url or "",
            "action_source":    "website",
            "user_data":        user_data,
            "custom_data":      custom_data,
        }],
        "access_token": _ACCESS_TOKEN,
    }

    url = f"https://graph.facebook.com/{_API_VERSION}/{_PIXEL_ID}/events"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code >= 400:
            logger.warning(
                "meta_capi.error event=%s status=%d body=%s",
                meta_event, resp.status_code, resp.text[:200],
            )
        else:
            logger.info(
                "meta_capi.sent event=%s pixel=%s", meta_event, _PIXEL_ID
            )
    except Exception as exc:
        logger.warning(
            "meta_capi.exception event=%s error=%s", meta_event, exc
        )
