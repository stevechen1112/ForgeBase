from __future__ import annotations

import hashlib
from datetime import timedelta
from decimal import Decimal

from app.core.datetime import utcnow_naive
from app.services.contact_enrichment.providers.base import (
    ContactProviderCandidate,
    ContactSearchContext,
    ContactSearchResult,
    EmailVerificationResult,
)


class MockContactProvider:
    name = "mock"

    async def search(self, context: ContactSearchContext) -> ContactSearchResult:
        rows: list[ContactProviderCandidate] = []
        roles = (
            ("Procurement Contact", "procurement", "procurement", "manager"),
            ("Engineering Contact", "engineering", "engineering", "director"),
        )
        for name, local, department, seniority in roles[: context.limit]:
            rows.append(
                ContactProviderCandidate(
                    full_name=name,
                    business_email=f"{local}@{context.company_domain}",
                    job_title=f"{seniority.title()} of {department.title()}",
                    department=department,
                    seniority=seniority,
                    location=context.target_locations[0] if context.target_locations else None,
                    provider_person_id=f"mock:{local}:{context.company_domain}",
                    source_url=f"https://{context.company_domain}/",
                    source_freshness=utcnow_naive() - timedelta(days=1),
                    provider_confidence=0.90,
                )
            )
        return ContactSearchResult(
            provider=self.name,
            request_id=f"mock-contact:{context.company_identification_id}",
            candidates=tuple(rows),
        )

    async def healthcheck(self) -> bool:
        return True

    def estimate_cost(self) -> Decimal:
        return Decimal(0)


class MockEmailVerificationProvider:
    name = "mock"

    async def verify(self, email: str) -> EmailVerificationResult:
        normalized = email.strip().lower()
        local = normalized.partition("@")[0]
        status = "invalid" if local.startswith("invalid") else "verified"
        return EmailVerificationResult(
            provider=self.name,
            request_id=(
                f"mock-verify:{hashlib.sha256(normalized.encode()).hexdigest()[:16]}"
            ),
            status=status,
            score=100 if status == "verified" else 0,
            checked_at=utcnow_naive(),
        )

    async def healthcheck(self) -> bool:
        return True

    def estimate_cost(self) -> Decimal:
        return Decimal(0)
