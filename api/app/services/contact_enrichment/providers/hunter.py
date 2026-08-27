"""Hunter Domain Search and email-verifier POC adapters."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from math import ceil
from typing import Any

import httpx

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.services.contact_enrichment.providers.base import (
    ContactProviderCandidate,
    ContactProviderPermanentError,
    ContactProviderRetryableError,
    ContactSearchContext,
    ContactSearchResult,
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

_HUNTER_DEPARTMENTS = {
    "executive",
    "it",
    "finance",
    "management",
    "sales",
    "legal",
    "support",
    "hr",
    "marketing",
    "communication",
    "education",
    "design",
    "health",
    "operations",
    "product",
    "research",
    "consulting",
    "administrative",
    "procurement",
}
_HUNTER_SENIORITIES = {"junior", "senior", "executive"}


def _source_freshness(row: dict[str, Any]) -> datetime | None:
    values = []
    verification = row.get("verification")
    if isinstance(verification, dict):
        values.append(verification.get("date"))
    sources = row.get("sources")
    if isinstance(sources, list):
        values.extend(
            source.get("last_seen_on")
            for source in sources
            if isinstance(source, dict)
        )
    parsed = []
    for value in values:
        if not isinstance(value, str):
            continue
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if result.tzinfo is not None:
                result = result.astimezone(timezone.utc)
            parsed.append(result.replace(tzinfo=None))
        except ValueError:
            continue
    return max(parsed) if parsed else None


def _source_url(row: dict[str, Any]) -> str | None:
    linkedin = str(row.get("linkedin") or "").strip()
    if linkedin:
        if not linkedin.startswith(("https://", "http://")):
            linkedin = f"https://{linkedin.lstrip('/')}"
        return linkedin[:1000]
    sources = row.get("sources")
    if isinstance(sources, list):
        for source in sources:
            if isinstance(source, dict) and source.get("uri"):
                return str(source["uri"])[:1000]
    return None


class HunterDomainSearchContactProvider:
    name = "hunter_domain"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = (
            api_key if api_key is not None else settings.HUNTER_API_KEY
        ).strip()
        self._transport = transport
        self._cost = Decimal(str(settings.HUNTER_CONTACT_ESTIMATED_COST))

    async def search(self, context: ContactSearchContext) -> ContactSearchResult:
        if not self._api_key:
            raise ContactProviderPermanentError("Hunter API key is not configured")
        params: dict[str, str | int] = {
            "domain": context.company_domain.lower(),
            "limit": min(context.limit, 10),
            "offset": 0,
            "type": "personal",
            "required_field": "full_name,position",
            "verification_status": "valid,accept_all,unknown",
        }
        departments = [
            value.strip().lower()
            for value in context.target_departments
            if value.strip().lower() in _HUNTER_DEPARTMENTS
        ]
        seniorities = [
            value.strip().lower()
            for value in context.target_seniorities
            if value.strip().lower() in _HUNTER_SENIORITIES
        ]
        if departments:
            params["department"] = ",".join(departments)
        if context.target_titles:
            params["job_titles"] = ",".join(
                value.strip() for value in context.target_titles if value.strip()
            )
        if seniorities:
            params["seniority"] = ",".join(seniorities)
        try:
            async with httpx.AsyncClient(
                timeout=settings.CONTACT_PROVIDER_TIMEOUT_SECONDS,
                transport=self._transport,
            ) as client:
                response = await client.get(
                    settings.HUNTER_DOMAIN_SEARCH_URL,
                    params=params,
                    headers={
                        "X-API-KEY": self._api_key,
                        "Accept": "application/json",
                    },
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ContactProviderRetryableError("Hunter Domain Search failed") from exc
        request_id = response.headers.get("x-request-id") or (
            f"hunter-domain:{context.company_identification_id}"
        )
        if response.status_code == 404:
            return ContactSearchResult(provider=self.name, request_id=request_id)
        if response.status_code == 429 or response.status_code >= 500:
            raise ContactProviderRetryableError(
                f"Hunter Domain Search upstream error {response.status_code}"
            )
        if response.status_code in (401, 402, 403):
            raise ContactProviderPermanentError(
                "Hunter credentials, credits or account access were rejected"
            )
        if response.status_code != 200:
            raise ContactProviderPermanentError(
                f"Hunter Domain Search rejected request with {response.status_code}"
            )
        try:
            data = response.json().get("data") or {}
            rows = data.get("emails", [])
        except (ValueError, AttributeError) as exc:
            raise ContactProviderRetryableError(
                "Hunter Domain Search response is malformed"
            ) from exc
        if not isinstance(rows, list):
            raise ContactProviderRetryableError(
                "Hunter Domain Search response schema is invalid"
            )

        expected_domain = context.company_domain.lower()
        candidates: list[ContactProviderCandidate] = []
        for row in rows[: context.limit]:
            if not isinstance(row, dict) or row.get("type") != "personal":
                continue
            email = str(row.get("value") or "").strip().lower()
            _, separator, email_domain = email.partition("@")
            first_name = str(row.get("first_name") or "").strip()
            last_name = str(row.get("last_name") or "").strip()
            name = " ".join(value for value in (first_name, last_name) if value)
            if not separator or email_domain != expected_domain or not name:
                continue
            confidence = row.get("confidence")
            candidates.append(
                ContactProviderCandidate(
                    full_name=name,
                    business_email=email,
                    job_title=str(row.get("position") or "").strip() or None,
                    department=str(row.get("department") or "").strip() or None,
                    seniority=str(row.get("seniority") or "").strip() or None,
                    provider_person_id=None,
                    source_url=_source_url(row),
                    source_freshness=_source_freshness(row),
                    provider_confidence=(
                        max(0.0, min(float(confidence) / 100, 1.0))
                        if isinstance(confidence, (int, float))
                        else 0.0
                    ),
                )
            )
        unique = {row.business_email: row for row in candidates}
        result_rows = tuple(list(unique.values())[: context.limit])
        units = ceil(len(rows) / 10) if rows else 0
        return ContactSearchResult(
            provider=self.name,
            request_id=request_id,
            candidates=result_rows,
            units=units,
            estimated_cost=self._cost * units,
        )

    async def healthcheck(self) -> bool:
        return bool(self._api_key and self._cost > 0)

    def estimate_cost(self) -> Decimal:
        return self._cost


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
