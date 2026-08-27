"""People Data Labs Person Search adapter for review-only contact candidates."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import settings
from app.services.contact_enrichment.providers.base import (
    ContactProviderCandidate,
    ContactProviderPermanentError,
    ContactProviderRetryableError,
    ContactSearchContext,
    ContactSearchResult,
)


def _retry_after(response: httpx.Response) -> int | None:
    try:
        return max(1, min(int(response.headers.get("retry-after", "")), 3600))
    except ValueError:
        return None


def _date(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc)
        return parsed.replace(tzinfo=None)
    except ValueError:
        return None


def _public_profile(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if not normalized.startswith(("https://", "http://")):
        normalized = f"https://{normalized.lstrip('/')}"
    return normalized[:1000]


def _search_query(context: ContactSearchContext) -> dict[str, Any]:
    persona = [
        {"match_phrase": {"job_title": value.strip().lower()}}
        for value in context.target_titles
        if value.strip()
    ]
    persona.extend(
        {"term": {"job_title_role": value.strip().lower()}}
        for value in context.target_departments
        if value.strip()
    )
    must: list[dict[str, Any]] = [
        {"term": {"job_company_website": context.company_domain.lower()}},
        {"exists": {"field": "work_email"}},
        {"bool": {"should": persona, "minimum_should_match": 1}},
    ]
    if context.target_seniorities:
        must.append(
            {
                "bool": {
                    "should": [
                        {"term": {"job_title_levels": value.strip().lower()}}
                        for value in context.target_seniorities
                        if value.strip()
                    ],
                    "minimum_should_match": 1,
                }
            }
        )
    return {"bool": {"must": must}}


class PeopleDataLabsContactProvider:
    name = "pdl_person"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        endpoint: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = (
            api_key if api_key is not None else settings.PDL_API_KEY
        ).strip()
        self._endpoint = endpoint or settings.PDL_PERSON_SEARCH_URL
        self._transport = transport
        self._cost = Decimal(str(settings.PDL_CONTACT_ESTIMATED_COST))

    async def search(self, context: ContactSearchContext) -> ContactSearchResult:
        if not self._api_key:
            raise ContactProviderPermanentError("PDL API key is not configured")
        payload = {
            "query": _search_query(context),
            "size": context.limit,
            "dataset": "all",
            "data_include": (
                "id,full_name,work_email,job_title,job_title_role,"
                "job_title_levels,location_name,linkedin_url,"
                "job_last_verified,job_last_changed,job_company_website"
            ),
        }
        try:
            async with httpx.AsyncClient(
                timeout=settings.CONTACT_PROVIDER_TIMEOUT_SECONDS,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    self._endpoint,
                    json=payload,
                    headers={
                        "X-Api-Key": self._api_key,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ContactProviderRetryableError("PDL Person Search failed") from exc
        request_id = response.headers.get("x-request-id") or (
            f"pdl-person:{context.company_identification_id}"
        )
        if response.status_code == 404:
            return ContactSearchResult(provider=self.name, request_id=request_id)
        if response.status_code == 429:
            raise ContactProviderRetryableError(
                "PDL Person Search rate limit reached",
                retry_after_seconds=_retry_after(response),
            )
        if response.status_code >= 500:
            raise ContactProviderRetryableError(
                f"PDL Person Search upstream error {response.status_code}"
            )
        if response.status_code in (401, 402, 403):
            raise ContactProviderPermanentError(
                "PDL credentials, credits or account access were rejected"
            )
        if response.status_code != 200:
            raise ContactProviderPermanentError(
                f"PDL Person Search rejected request with {response.status_code}"
            )
        try:
            rows = response.json().get("data", [])
        except (ValueError, AttributeError) as exc:
            raise ContactProviderRetryableError(
                "PDL Person Search response is malformed"
            ) from exc
        if not isinstance(rows, list):
            raise ContactProviderRetryableError(
                "PDL Person Search response schema is invalid"
            )

        candidates: list[ContactProviderCandidate] = []
        expected_domain = context.company_domain.lower()
        for row in rows[: context.limit]:
            if not isinstance(row, dict):
                continue
            email = str(row.get("work_email") or "").strip().lower()
            _, separator, email_domain = email.partition("@")
            company_domain = str(row.get("job_company_website") or "").strip().lower()
            if (
                not separator
                or email_domain != expected_domain
                or company_domain != expected_domain
            ):
                continue
            name = str(row.get("full_name") or "").strip()
            if not name:
                continue
            levels = row.get("job_title_levels")
            seniority = (
                str(levels[0]).strip()
                if isinstance(levels, list) and levels
                else None
            )
            candidates.append(
                ContactProviderCandidate(
                    full_name=name,
                    business_email=email,
                    job_title=str(row.get("job_title") or "").strip() or None,
                    department=str(row.get("job_title_role") or "").strip()
                    or None,
                    seniority=seniority,
                    location=str(row.get("location_name") or "").strip() or None,
                    provider_person_id=str(row.get("id") or "")[:200] or None,
                    source_url=_public_profile(row.get("linkedin_url")),
                    source_freshness=_date(
                        row.get("job_last_verified") or row.get("job_last_changed")
                    ),
                    # Person Search does not return a match likelihood. ForgeBase
                    # computes relevance separately and must not invent one.
                    provider_confidence=0.0,
                )
            )
        unique = {row.business_email: row for row in candidates}
        result_rows = tuple(list(unique.values())[: context.limit])
        return ContactSearchResult(
            provider=self.name,
            request_id=request_id,
            candidates=result_rows,
            units=len(rows),
            estimated_cost=self._cost * len(rows),
        )

    async def healthcheck(self) -> bool:
        return bool(self._api_key and self._cost > 0)

    def estimate_cost(self) -> Decimal:
        return self._cost
