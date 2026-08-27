"""Provider-neutral contracts for contact search and email verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContactSearchContext:
    tenant_id: UUID
    company_identification_id: UUID
    company_name: str
    company_domain: str
    target_departments: tuple[str, ...]
    target_titles: tuple[str, ...]
    target_seniorities: tuple[str, ...]
    target_locations: tuple[str, ...]
    limit: int

    def __post_init__(self) -> None:
        if not self.company_name.strip() or not self.company_domain.strip():
            raise ValueError("company name and domain are required")
        if not 1 <= self.limit <= 25:
            raise ValueError("contact search limit must be 1-25")
        if not (self.target_departments or self.target_titles):
            raise ValueError("at least one target department or title is required")


@dataclass(frozen=True, slots=True)
class ContactProviderCandidate:
    full_name: str
    business_email: str = field(repr=False)
    job_title: str | None = None
    department: str | None = None
    seniority: str | None = None
    location: str | None = None
    provider_person_id: str | None = None
    source_url: str | None = None
    source_freshness: datetime | None = None
    provider_confidence: float = 0.0

    def __post_init__(self) -> None:
        if not self.full_name.strip() or len(self.full_name) > 200:
            raise ValueError("candidate full_name must be 1-200 characters")
        address = self.business_email.strip().lower()
        if len(address) > 254 or address.count("@") != 1:
            raise ValueError("candidate business email is invalid")
        if not 0 <= self.provider_confidence <= 1:
            raise ValueError("provider confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ContactSearchResult:
    provider: str
    request_id: str
    candidates: tuple[ContactProviderCandidate, ...] = ()
    units: int = 0
    estimated_cost: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.request_id.strip() or len(self.request_id) > 300:
            raise ValueError("provider and request_id are required")
        if len(self.candidates) > 25 or self.units < 0 or self.estimated_cost < 0:
            raise ValueError("invalid provider result accounting")
        emails = [row.business_email.strip().lower() for row in self.candidates]
        if len(emails) != len(set(emails)):
            raise ValueError("provider candidate emails must be unique")


@dataclass(frozen=True, slots=True)
class EmailVerificationResult:
    provider: str
    request_id: str
    status: str
    score: int | None = None
    checked_at: datetime | None = None
    units: int = 0
    estimated_cost: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if self.status not in {"verified", "risky", "catch_all", "unknown", "invalid"}:
            raise ValueError("invalid normalized verification status")
        if self.score is not None and not 0 <= self.score <= 100:
            raise ValueError("verification score must be between 0 and 100")
        if self.units < 0 or self.estimated_cost < 0:
            raise ValueError("invalid verification accounting")


class ContactProvider(Protocol):
    name: str

    async def search(self, context: ContactSearchContext) -> ContactSearchResult: ...
    async def healthcheck(self) -> bool: ...
    def estimate_cost(self) -> Decimal: ...


class EmailVerificationProvider(Protocol):
    name: str

    async def verify(self, email: str) -> EmailVerificationResult: ...
    async def healthcheck(self) -> bool: ...
    def estimate_cost(self) -> Decimal: ...


class ContactProviderError(RuntimeError):
    pass


class ContactProviderRetryableError(ContactProviderError):
    def __init__(self, message: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ContactProviderPermanentError(ContactProviderError):
    pass
