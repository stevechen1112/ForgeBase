"""Company-identification provider contracts and built-in adapters."""

from app.core.config import settings
from app.services.company_identification.providers.base import (
    CompanyCandidate,
    CompanyIdentificationProvider,
    CompanyLookupContext,
    CompanyLookupResult,
    CompanyProviderError,
    CompanyProviderPermanentError,
    CompanyProviderRetryableError,
)
from app.services.company_identification.providers.mock import (
    MockCompanyIdentificationProvider,
)
from app.services.company_identification.providers.pdl import PeopleDataLabsIPProvider


class UnsupportedCompanyIdentificationProvider(ValueError):
    pass


def available_provider_names() -> tuple[str, ...]:
    providers = ["mock"]
    if (
        settings.PDL_DATA_USE_APPROVED
        and settings.PDL_API_KEY.strip()
        and settings.PDL_IP_ENRICH_ESTIMATED_COST > 0
    ):
        providers.append("pdl_ip")
    return tuple(providers)


def get_company_identification_provider(name: str) -> CompanyIdentificationProvider:
    normalized = name.strip().lower()
    if normalized == "mock":
        return MockCompanyIdentificationProvider()
    if normalized == "pdl_ip" and normalized in available_provider_names():
        return PeopleDataLabsIPProvider()
    raise UnsupportedCompanyIdentificationProvider(
        f"Company-identification provider '{name}' is not configured"
    )

__all__ = [
    "CompanyCandidate",
    "CompanyIdentificationProvider",
    "CompanyLookupContext",
    "CompanyLookupResult",
    "CompanyProviderError",
    "CompanyProviderPermanentError",
    "CompanyProviderRetryableError",
    "MockCompanyIdentificationProvider",
    "PeopleDataLabsIPProvider",
    "UnsupportedCompanyIdentificationProvider",
    "available_provider_names",
    "get_company_identification_provider",
]
