"""Apollo people-search POC adapter, locked behind a reseller/data-use gate."""

from __future__ import annotations

from decimal import Decimal
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
)


def _retry_after(response: httpx.Response) -> int | None:
    try:
        return max(1, min(int(response.headers.get("retry-after", "")), 3600))
    except ValueError:
        return None


class ApolloContactProvider:
    name = "apollo"

    def __init__(self, *, api_key: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._api_key = (api_key if api_key is not None else settings.APOLLO_API_KEY).strip()
        self._transport = transport
        self._cost = Decimal(str(settings.APOLLO_CONTACT_ESTIMATED_COST))

    async def _request(self, client: httpx.AsyncClient, url: str, *, params: dict[str, Any]) -> httpx.Response:
        try:
            response = await client.post(url, params=params, headers={"x-api-key": self._api_key, "accept": "application/json"})
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ContactProviderRetryableError("Apollo request failed") from exc
        if response.status_code == 429:
            raise ContactProviderRetryableError("Apollo rate limit reached", retry_after_seconds=_retry_after(response))
        if response.status_code >= 500:
            raise ContactProviderRetryableError(f"Apollo upstream error {response.status_code}")
        if response.status_code in (401, 403):
            raise ContactProviderPermanentError("Apollo credentials or reseller access rejected")
        if response.status_code == 422:
            raise ContactProviderPermanentError("Apollo rejected the configured search filters")
        if response.status_code != 200:
            raise ContactProviderPermanentError(f"Apollo rejected request with {response.status_code}")
        return response

    async def search(self, context: ContactSearchContext) -> ContactSearchResult:
        if not self._api_key:
            raise ContactProviderPermanentError("Apollo API key is not configured")
        async with httpx.AsyncClient(timeout=settings.CONTACT_PROVIDER_TIMEOUT_SECONDS, transport=self._transport) as client:
            search = await self._request(
                client,
                settings.APOLLO_PEOPLE_SEARCH_URL,
                params={
                    "q_organization_domains_list[]": context.company_domain,
                    "person_titles[]": list(context.target_titles),
                    "person_seniorities[]": list(context.target_seniorities),
                    "person_locations[]": list(context.target_locations),
                    "include_similar_titles": "false",
                    "page": 1,
                    "per_page": context.limit,
                },
            )
            try:
                people = search.json().get("people", [])
            except (ValueError, AttributeError) as exc:
                raise ContactProviderRetryableError("Apollo search response is malformed") from exc
            if not isinstance(people, list):
                raise ContactProviderRetryableError("Apollo search schema is invalid")

            candidates: list[ContactProviderCandidate] = []
            for person in people[: context.limit]:
                if not isinstance(person, dict) or not person.get("id"):
                    continue
                match = await self._request(
                    client,
                    settings.APOLLO_PEOPLE_MATCH_URL,
                    params={
                        "id": str(person["id"]),
                        "domain": context.company_domain,
                        "reveal_personal_emails": "false",
                        "reveal_phone_number": "false",
                    },
                )
                try:
                    row = match.json().get("person") or {}
                except (ValueError, AttributeError) as exc:
                    raise ContactProviderRetryableError("Apollo enrichment response is malformed") from exc
                email = str(row.get("email") or "").strip().lower()
                _, separator, email_domain = email.partition("@")
                # Business addresses must match the confirmed company domain;
                # personal-email reveal is never requested.
                if not separator or email_domain != context.company_domain.lower():
                    continue
                location = ", ".join(
                    str(row.get(key)).strip() for key in ("city", "state", "country") if row.get(key)
                ) or None
                name = str(row.get("name") or "").strip()
                if not name:
                    continue
                candidates.append(
                    ContactProviderCandidate(
                        full_name=name,
                        business_email=email,
                        job_title=str(row.get("title") or "").strip() or None,
                        department=str(row.get("departments", [""])[0] if isinstance(row.get("departments"), list) and row.get("departments") else "").strip() or None,
                        seniority=str(row.get("seniority") or "").strip() or None,
                        location=location,
                        provider_person_id=str(row.get("id") or person["id"])[:200],
                        source_url=str(row.get("linkedin_url") or "")[:1000] or None,
                        source_freshness=utcnow_naive(),
                        provider_confidence=0.85 if row.get("email_status") == "verified" else 0.65,
                    )
                )
        unique = {row.business_email: row for row in candidates}
        result_rows = tuple(list(unique.values())[: context.limit])
        return ContactSearchResult(
            provider=self.name,
            request_id=search.headers.get("x-request-id") or f"apollo:{context.company_identification_id}",
            candidates=result_rows,
            units=len(result_rows),
            estimated_cost=self._cost * len(result_rows),
        )

    async def healthcheck(self) -> bool:
        return bool(self._api_key and self._cost > 0)

    def estimate_cost(self) -> Decimal:
        return self._cost
