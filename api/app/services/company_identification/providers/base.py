"""Stable contract between ForgeBase and replaceable company-data vendors."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CompanyLookupContext:
    """Transient provider input; ``ip_address`` must never be persisted by adapters."""

    tenant_id: UUID
    observation_id: UUID
    ip_address: str = field(repr=False)
    country: str | None = None
    asn: str | None = None


@dataclass(frozen=True, slots=True)
class CompanyCandidate:
    company_name: str
    candidate_key: str
    confidence: float
    match_method: str
    domain: str | None = None
    provider_company_id: str | None = None
    source_freshness: datetime | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        company_name = self.company_name.strip()
        candidate_key = self.candidate_key.strip()
        if not company_name:
            raise ValueError("company_name must not be blank")
        if len(company_name) > 300:
            raise ValueError("company_name must not exceed 300 characters")
        if not candidate_key:
            raise ValueError("candidate_key must not be blank")
        if len(candidate_key) > 300:
            raise ValueError("candidate_key must not exceed 300 characters")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.domain:
            domain = self.domain.strip().lower().rstrip(".")
            parsed = urlsplit(f"//{domain}")
            if (
                len(domain) > 253
                or not parsed.hostname
                or parsed.hostname != domain
                or "." not in domain
                or any(not label or len(label) > 63 for label in domain.split("."))
            ):
                raise ValueError("domain must be a valid hostname")
        if not self.match_method.strip() or len(self.match_method) > 50:
            raise ValueError("match_method must be 1-50 characters")
        if self.provider_company_id and len(self.provider_company_id) > 200:
            raise ValueError("provider_company_id must not exceed 200 characters")


@dataclass(frozen=True, slots=True)
class CompanyLookupResult:
    provider: str
    request_id: str
    candidates: tuple[CompanyCandidate, ...] = ()
    units: int = 0
    estimated_cost: Decimal = Decimal(0)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must not be blank")
        if not self.request_id.strip() or len(self.request_id) > 300:
            raise ValueError("request_id must be 1-300 characters")
        if len(self.candidates) > 20:
            raise ValueError("provider result must not exceed 20 candidates")
        if self.units < 0:
            raise ValueError("units must not be negative")
        if self.estimated_cost < 0:
            raise ValueError("estimated_cost must not be negative")
        candidate_keys = [candidate.candidate_key.strip() for candidate in self.candidates]
        if len(candidate_keys) != len(set(candidate_keys)):
            raise ValueError("provider candidates must have unique candidate_key values")


class CompanyIdentificationProvider(Protocol):
    """Adapter interface implemented by mock, POC and production providers."""

    name: str

    async def identify_company(self, context: CompanyLookupContext) -> CompanyLookupResult:
        """Return zero or more company candidates without persisting raw input."""
        ...

    async def healthcheck(self) -> bool:
        """Report whether the provider can currently accept lookups."""
        ...

    def estimate_cost(self) -> Decimal:
        """Return the configured upper-bound cost for one lookup."""
        ...


class CompanyProviderError(RuntimeError):
    """Base error safe to expose to the operational retry policy."""


class CompanyProviderRetryableError(CompanyProviderError):
    def __init__(self, message: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class CompanyProviderPermanentError(CompanyProviderError):
    """Configuration or authentication failure that retries cannot repair."""
