"""Deterministic no-network adapter for contract and shadow-pipeline tests."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from app.services.company_identification.providers.base import (
    CompanyCandidate,
    CompanyLookupContext,
    CompanyLookupResult,
)


class MockCompanyIdentificationProvider:
    name = "mock"

    def __init__(self, matches: Mapping[str, tuple[CompanyCandidate, ...]] | None = None) -> None:
        self._matches = dict(matches or {})

    async def identify_company(self, context: CompanyLookupContext) -> CompanyLookupResult:
        return CompanyLookupResult(
            provider=self.name,
            request_id=f"mock-{context.observation_id}",
            candidates=self._matches.get(context.ip_address, ()),
            units=0,
            metadata={"mock": True},
        )

    async def healthcheck(self) -> bool:
        return True

    def estimate_cost(self) -> Decimal:
        return Decimal(0)
