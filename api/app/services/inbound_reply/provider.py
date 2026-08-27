"""Bounded Resend Receiving API adapter."""

from __future__ import annotations

import json

import httpx

from app.core.config import settings

RECEIVING_URL = "https://api.resend.com/emails/receiving"


class InboundProviderRetryable(RuntimeError):
    retry_after_seconds = 120


class InboundProviderPermanent(RuntimeError):
    pass


async def fetch_received_email(provider_email_id: str) -> dict:
    if not settings.RESEND_API_KEY.strip():
        raise InboundProviderPermanent("Resend API key is not configured")
    if not provider_email_id or len(provider_email_id) > 120:
        raise InboundProviderPermanent("Invalid provider email id")
    try:
        async with (
            httpx.AsyncClient(timeout=15.0) as client,
            client.stream(
                "GET",
                f"{RECEIVING_URL}/{provider_email_id}",
                params={"html_format": "cid"},
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Accept": "application/json",
                    "User-Agent": "ForgeBase/1.0",
                },
            ) as response,
        ):
            if response.status_code == 429 or response.status_code >= 500:
                retry_after = response.headers.get("retry-after")
                error = InboundProviderRetryable(
                    f"Resend receiving HTTP {response.status_code}"
                )
                if retry_after and retry_after.isdigit():
                    error.retry_after_seconds = min(max(int(retry_after), 1), 3600)
                raise error
            if response.status_code in {401, 403, 404}:
                raise InboundProviderPermanent(
                    f"Resend receiving HTTP {response.status_code}"
                )
            if response.status_code != 200:
                raise InboundProviderPermanent(
                    f"Unexpected Resend receiving HTTP {response.status_code}"
                )
            declared_length = response.headers.get("content-length")
            if (
                declared_length
                and declared_length.isdigit()
                and int(declared_length) > settings.INBOUND_REPLY_MAX_FETCH_BYTES
            ):
                raise InboundProviderPermanent(
                    "Received email payload exceeds configured limit"
                )
            chunks: list[bytes] = []
            received_bytes = 0
            async for chunk in response.aiter_bytes():
                received_bytes += len(chunk)
                if received_bytes > settings.INBOUND_REPLY_MAX_FETCH_BYTES:
                    raise InboundProviderPermanent(
                        "Received email payload exceeds configured limit"
                    )
                chunks.append(chunk)
    except httpx.RequestError as exc:
        raise InboundProviderRetryable("Resend receiving request failed") from exc
    try:
        payload = json.loads(b"".join(chunks))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InboundProviderPermanent("Received email payload is not JSON") from exc
    if (
        not isinstance(payload, dict)
        or str(payload.get("id") or "") != provider_email_id
    ):
        raise InboundProviderPermanent("Received email payload identity mismatch")
    return payload
