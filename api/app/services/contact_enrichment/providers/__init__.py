from app.core.config import settings
from app.services.contact_enrichment.providers.apollo import ApolloContactProvider
from app.services.contact_enrichment.providers.base import (
    ContactProvider,
    ContactProviderCandidate,
    ContactProviderError,
    ContactProviderPermanentError,
    ContactProviderRetryableError,
    ContactSearchContext,
    ContactSearchResult,
    EmailVerificationProvider,
    EmailVerificationResult,
)
from app.services.contact_enrichment.providers.hunter import (
    HunterDomainSearchContactProvider,
    HunterEmailVerificationProvider,
)
from app.services.contact_enrichment.providers.mock import (
    MockContactProvider,
    MockEmailVerificationProvider,
)
from app.services.contact_enrichment.providers.pdl import (
    PeopleDataLabsContactProvider,
)


def available_contact_provider_names() -> tuple[str, ...]:
    values = [] if settings.is_production else ["mock"]
    if settings.PDL_CONTACT_DATA_USE_APPROVED and settings.PDL_API_KEY.strip() and settings.PDL_CONTACT_ESTIMATED_COST > 0:
        values.append("pdl_person")
    if settings.HUNTER_DATA_USE_APPROVED and settings.HUNTER_API_KEY.strip() and settings.HUNTER_CONTACT_ESTIMATED_COST > 0:
        values.append("hunter_domain")
    if settings.APOLLO_DATA_USE_APPROVED and settings.APOLLO_API_KEY.strip() and settings.APOLLO_CONTACT_ESTIMATED_COST > 0:
        values.append("apollo")
    return tuple(values)


def available_verification_provider_names() -> tuple[str, ...]:
    values = [] if settings.is_production else ["mock"]
    if settings.HUNTER_DATA_USE_APPROVED and settings.HUNTER_API_KEY.strip() and settings.HUNTER_VERIFY_ESTIMATED_COST > 0:
        values.append("hunter")
    return tuple(values)


def get_contact_provider(name: str) -> ContactProvider:
    normalized = name.strip().lower()
    if normalized == "mock" and not settings.is_production:
        return MockContactProvider()
    if normalized == "pdl_person" and normalized in available_contact_provider_names():
        return PeopleDataLabsContactProvider()
    if normalized == "hunter_domain" and normalized in available_contact_provider_names():
        return HunterDomainSearchContactProvider()
    if normalized == "apollo" and normalized in available_contact_provider_names():
        return ApolloContactProvider()
    raise ContactProviderPermanentError(f"Contact provider '{name}' is not configured")


def get_verification_provider(name: str) -> EmailVerificationProvider:
    normalized = name.strip().lower()
    if normalized == "mock" and not settings.is_production:
        return MockEmailVerificationProvider()
    if normalized == "hunter" and normalized in available_verification_provider_names():
        return HunterEmailVerificationProvider()
    raise ContactProviderPermanentError(
        f"Email verification provider '{name}' is not configured"
    )


__all__ = [
    "ContactProvider", "ContactProviderCandidate", "ContactProviderError",
    "ContactProviderPermanentError", "ContactProviderRetryableError",
    "ContactSearchContext", "ContactSearchResult", "EmailVerificationProvider",
    "EmailVerificationResult", "HunterDomainSearchContactProvider",
    "PeopleDataLabsContactProvider", "available_contact_provider_names",
    "available_verification_provider_names", "get_contact_provider",
    "get_verification_provider",
]
