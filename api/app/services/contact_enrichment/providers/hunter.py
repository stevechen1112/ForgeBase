"""Hunter email-verifier POC adapter."""

from __future__ import annotations

from decimal import Decimal

import httpx

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.services.contact_enrichment.providers.base import (
    ContactProviderPermanentError,
    ContactProviderRetryableError,
    EmailVerificationResult,
)

_STATUS = {
    "valid": "verified",
    "accept_all": "catch_all",
    "accept-all": "catch_all",
    "webmail": "risky",
    "disposable": "risky",
    "invalid": "invalid",
    "blocked": "invalid",
    "unknown": "unknown",
}


class HunterEmailVerificationProvider:
    name = "hunter"

    def __init__(self, *, api_key: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._api_key = (api_key if api_key is not None else settings.HUNTER_API_KEY).strip()
        self._transport = transport
        self._cost = Decimal(str(settings.HUNTER_VERIFY_ESTIMATED_COST))

    async def verify(self, email: str) -> EmailVerificationResult:
        if not self._api_key:
            raise ContactProviderPermanentError("Hunter API key is not configured")
        try:
            async with httpx.AsyncClient(timeout=settings.CONTACT_PROVIDER_TIMEOUT_SECONDS, transport=self._transport) as client:
                response = await client.get(
                    settings.HUNTER_EMAIL_VERIFIER_URL,
                    params={"email": email},
                    headers={"X-API-KEY": self._api_key, "Accept": "application/json"},
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ContactProviderRetryableError("Hunter request failed") from exc
        if response.status_code in (202, 429) or response.status_code >= 500:
            retry_after = 3600 if response.status_code == 202 else None
            try:
                retry_after = max(1, min(int(response.headers.get("retry-after", "")), 43200))
            except ValueError:
                pass
            raise ContactProviderRetryableError("Hunter verification is pending", retry_after_seconds=retry_after)
        if response.status_code in (401, 403):
            raise ContactProviderPermanentError("Hunter credentials or account access rejected")
        if response.status_code != 200:
            raise ContactProviderPermanentError(f"Hunter rejected request with {response.status_code}")
        try:
            data = response.json().get("data") or {}
        except (ValueError, AttributeError) as exc:
            raise ContactProviderRetryableError("Hunter response is malformed") from exc
        raw_status = str(data.get("status") or "unknown").lower().replace(" ", "_")
        status = _STATUS.get(raw_status, "unknown")
        if data.get("disposable") or data.get("webmail") or data.get("block"):
            status = "risky" if status != "invalid" else status
        if data.get("accept_all"):
            status = "catch_all"
        score = data.get("score")
        return EmailVerificationResult(
            provider=self.name,
            request_id=response.headers.get("x-request-id") or f"hunter:{email.partition('@')[1]}",
            status=status,
            score=int(score) if isinstance(score, (int, float)) else None,
            checked_at=utcnow_naive(),
            units=1,
            estimated_cost=self._cost,
        )

    async def healthcheck(self) -> bool:
        return bool(self._api_key and self._cost > 0)

    def estimate_cost(self) -> Decimal:
        return self._cost
