"""People Data Labs IP Enrichment POC adapter.

Only normalized company fields and network-risk booleans leave this adapter.
The raw provider payload, requested IP, person object, and location/address data
are deliberately never returned to the persistence layer.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.services.company_identification.providers.base import (
    CompanyCandidate,
    CompanyLookupContext,
    CompanyLookupResult,
    CompanyProviderPermanentError,
    CompanyProviderRetryableError,
)

_CONFIDENCE = {
    "very high": 0.95,
    "high": 0.85,
    "moderate": 0.65,
    "low": 0.40,
    "very low": 0.20,
}


def _retry_after(response: httpx.Response) -> int | None:
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(1, min(int(raw), 3600))
    except ValueError:
        return None


def _domain(value: Any) -> str | None:
    raw = str(value or "").strip().lower().rstrip("/")
    if not raw:
        return None
    parsed = urlsplit(raw if "://" in raw else f"//{raw}")
    if not parsed.hostname:
        return None
    domain = parsed.hostname.lower().rstrip(".")
    if (
        len(domain) > 253
        or "." not in domain
        or any(not label or len(label) > 63 for label in domain.split("."))
    ):
        return None
    return domain


class PeopleDataLabsIPProvider:
    name = "pdl_ip"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        endpoint: str | None = None,
        estimated_cost: Decimal | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = (api_key if api_key is not None else settings.PDL_API_KEY).strip()
        self._endpoint = endpoint or settings.PDL_IP_ENRICH_URL
        self._estimated_cost = estimated_cost if estimated_cost is not None else Decimal(
            str(settings.PDL_IP_ENRICH_ESTIMATED_COST)
        )
        self._transport = transport

    async def identify_company(self, context: CompanyLookupContext) -> CompanyLookupResult:
        if not self._api_key:
            raise CompanyProviderPermanentError("PDL API key is not configured")
        try:
            async with httpx.AsyncClient(
                timeout=settings.COMPANY_PROVIDER_TIMEOUT_SECONDS,
                transport=self._transport,
            ) as client:
                response = await client.get(
                    self._endpoint,
                    headers={"X-Api-Key": self._api_key, "Accept": "application/json"},
                    params={
                        "ip": context.ip_address,
                        "return_ip_metadata": "true",
                        "return_ip_location": "false",
                        "return_person": "false",
                    },
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise CompanyProviderRetryableError("PDL request timed out or failed") from exc

        if response.status_code == 404:
            return CompanyLookupResult(
                provider=self.name,
                request_id=response.headers.get("x-request-id") or f"pdl:{context.observation_id}",
                units=0,
            )
        if response.status_code == 429:
            raise CompanyProviderRetryableError(
                "PDL rate limit reached",
                retry_after_seconds=_retry_after(response),
            )
        if response.status_code >= 500:
            raise CompanyProviderRetryableError(f"PDL upstream error {response.status_code}")
        if response.status_code in (401, 403):
            raise CompanyProviderPermanentError("PDL credentials or account access were rejected")

        try:
            payload = response.json()
        except ValueError as exc:
            raise CompanyProviderRetryableError("PDL returned malformed JSON") from exc

        # PDL documents 400 for hosting/proxy/Tor/relay/service IPs. Treat it
        # as an audit-safe network rejection, not as a company candidate.
        if response.status_code == 400:
            return CompanyLookupResult(
                provider=self.name,
                request_id=response.headers.get("x-request-id") or f"pdl:{context.observation_id}",
                units=0,
                metadata={"provider_network_rejected": True},
            )
        if response.status_code != 200:
            raise CompanyProviderPermanentError(f"PDL rejected request with {response.status_code}")
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
            raise CompanyProviderRetryableError("PDL response schema is invalid")

        data = payload["data"]
        ip_data = data.get("ip") if isinstance(data.get("ip"), dict) else {}
        metadata = ip_data.get("metadata") if isinstance(ip_data.get("metadata"), dict) else {}
        risk = {
            "is_vpn": bool(metadata.get("vpn")),
            "is_proxy": bool(metadata.get("proxy") or metadata.get("tor") or metadata.get("relay")),
            "is_hosting": bool(metadata.get("hosting") or metadata.get("service")),
        }
        company = data.get("company") if isinstance(data.get("company"), dict) else None
        candidates: tuple[CompanyCandidate, ...] = ()
        if company and not any(risk.values()):
            name = str(company.get("display_name") or company.get("name") or "").strip()
            domain = _domain(company.get("website"))
            provider_id = str(company.get("id") or "").strip() or None
            confidence_label = str(company.get("confidence") or "").strip().lower()
            if name and (domain or provider_id):
                candidate_key = provider_id or domain
                candidates = (
                    CompanyCandidate(
                        company_name=name,
                        candidate_key=candidate_key,
                        confidence=_CONFIDENCE.get(confidence_label, 0.20),
                        match_method="pdl_ip_observed",
                        domain=domain,
                        provider_company_id=provider_id,
                        source_freshness=utcnow_naive(),
                        evidence={
                            "confidence_label": confidence_label or "unknown",
                            "dataset_version": str(data.get("dataset_version") or "")[:100],
                            "asn_domain_match": bool(metadata.get("asn_domain")),
                        },
                    ),
                )
        return CompanyLookupResult(
            provider=self.name,
            request_id=response.headers.get("x-request-id") or f"pdl:{context.observation_id}",
            candidates=candidates,
            units=1 if candidates else 0,
            estimated_cost=self._estimated_cost if candidates else Decimal(0),
            metadata=risk,
        )

    async def healthcheck(self) -> bool:
        return bool(self._api_key and self._estimated_cost > 0)

    def estimate_cost(self) -> Decimal:
        return self._estimated_cost
