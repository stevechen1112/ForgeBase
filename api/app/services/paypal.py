"""
PayPal Subscriptions API integration.

Supports:
- Creating subscription checkout URLs (subscriber redirected to PayPal)
- Verifying webhook notifications (subscription activated / cancelled / payment failed)
- Fetching subscription details

Env vars required:
  PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_WEBHOOK_ID
  PAYPAL_STARTER_PLAN_ID, PAYPAL_PROFESSIONAL_PLAN_ID
  PAYPAL_MODE  ("sandbox" | "live", default "sandbox")

Plans must be pre-created in PayPal dashboard with matching plan IDs.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

PAYPAL_MODE = getattr(settings, "PAYPAL_MODE", "sandbox")
PAYPAL_BASE = (
    "https://api-m.paypal.com"
    if PAYPAL_MODE == "live"
    else "https://api-m.sandbox.paypal.com"
)
PAYPAL_CLIENT_ID = getattr(settings, "PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = getattr(settings, "PAYPAL_CLIENT_SECRET", "")
PAYPAL_WEBHOOK_ID = getattr(settings, "PAYPAL_WEBHOOK_ID", "")

PLAN_ID_MAP: Dict[str, str] = {
    "starter": getattr(settings, "PAYPAL_STARTER_PLAN_ID", ""),
    "professional": getattr(settings, "PAYPAL_PROFESSIONAL_PLAN_ID", ""),
}


# ── Auth ──────────────────────────────────────────────────────────────────────

async def _get_access_token() -> str:
    """Obtain an OAuth2 access token from PayPal."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_BASE}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


# ── Create Subscription ──────────────────────────────────────────────────────

async def create_subscription(
    plan_name: str,
    tenant_id: str,
    return_url: str,
    cancel_url: str,
) -> Dict[str, Any]:
    """
    Create a PayPal subscription and return the approval URL.

    Returns: {"subscription_id": "...", "approve_url": "..."}
    """
    paypal_plan_id = PLAN_ID_MAP.get(plan_name)
    if not paypal_plan_id:
        raise ValueError(f"No PayPal plan ID configured for: {plan_name}")

    token = await _get_access_token()
    payload = {
        "plan_id": paypal_plan_id,
        "custom_id": tenant_id,  # Our tenant ID for webhook correlation
        "application_context": {
            "brand_name": "ForgeBase",
            "locale": "en-US",
            "shipping_preference": "NO_SHIPPING",
            "user_action": "SUBSCRIBE_NOW",
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_BASE}/v1/billing/subscriptions",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    approve_url = ""
    for link in data.get("links", []):
        if link["rel"] == "approve":
            approve_url = link["href"]
            break

    return {
        "subscription_id": data["id"],
        "approve_url": approve_url,
    }


# ── Get Subscription Details ──────────────────────────────────────────────────

async def get_subscription(subscription_id: str) -> Dict[str, Any]:
    """Fetch subscription details from PayPal."""
    token = await _get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PAYPAL_BASE}/v1/billing/subscriptions/{subscription_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()


# ── Cancel Subscription ──────────────────────────────────────────────────────

async def cancel_subscription(subscription_id: str, reason: str = "Customer request") -> bool:
    """Cancel a PayPal subscription."""
    token = await _get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_BASE}/v1/billing/subscriptions/{subscription_id}/cancel",
            json={"reason": reason},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        return resp.status_code == 204


# ── Webhook Verification ─────────────────────────────────────────────────────

async def verify_webhook_signature(
    headers: Dict[str, str],
    body: bytes,
) -> bool:
    """
    Verify PayPal webhook signature using the PayPal API.
    Returns True if the webhook is authentic.
    """
    if not PAYPAL_WEBHOOK_ID:
        from app.core.config import settings
        if settings.is_production:
            logger.error("PAYPAL_WEBHOOK_ID not set in production — rejecting webhook to prevent bypass")
            return False
        logger.warning("PAYPAL_WEBHOOK_ID not set — skipping webhook verification (dev mode only)")
        return True  # Allow in dev mode only

    token = await _get_access_token()
    verification_body = {
        "auth_algo": headers.get("paypal-auth-algo", ""),
        "cert_url": headers.get("paypal-cert-url", ""),
        "transmission_id": headers.get("paypal-transmission-id", ""),
        "transmission_sig": headers.get("paypal-transmission-sig", ""),
        "transmission_time": headers.get("paypal-transmission-time", ""),
        "webhook_id": PAYPAL_WEBHOOK_ID,
        "webhook_event": __import__("json").loads(body),
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_BASE}/v1/notifications/verify-webhook-signature",
            json=verification_body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code != 200:
            logger.error("PayPal webhook verification failed: %s", resp.text)
            return False
        return resp.json().get("verification_status") == "SUCCESS"
