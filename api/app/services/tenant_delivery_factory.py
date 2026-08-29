"""Validation and replay-safe helpers for atomic tenant delivery."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.locale import PUBLIC_SITE_LOCALES
from app.models.site_build import SiteBuild
from app.models.tenant import Tenant
from app.models.tenant_domain import TenantDomain
from app.models.user import User
from app.services.site_provisioning import SITE_TEMPLATES
from app.services.tenant_domains import (
    forgebase_hostname_for_slug,
    normalize_hostname,
    validate_custom_hostname,
    valid_hostname,
)


def normalize_domain(value: str | None) -> str | None:
    return normalize_hostname(value)


def request_fingerprint(payload: dict[str, Any]) -> str:
    """Fingerprint the durable spec while excluding its write-only credential."""
    durable_spec = {key: value for key, value in payload.items() if key != "temporary_password"}
    canonical = json.dumps(
        durable_spec, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(
        b"forgebase-tenant-provision-v1\0" + canonical.encode("utf-8")
    ).hexdigest()


async def evaluate_provisioning_preflight(
    db: AsyncSession,
    *,
    slug: str,
    owner_email: str,
    template_key: str,
    site_url: str | None,
    primary_domain: str | None,
    default_locale: str,
    locales: list[str],
) -> dict[str, Any]:
    try:
        managed_hostname = forgebase_hostname_for_slug(slug, settings.TENANT_BASE_DOMAIN)
    except ValueError:
        managed_hostname = None
    requested_custom_domain = normalize_domain(primary_domain)
    if requested_custom_domain == managed_hostname:
        requested_custom_domain = None
    custom_domain_valid = True
    if requested_custom_domain:
        try:
            validate_custom_hostname(
                requested_custom_domain, settings.TENANT_BASE_DOMAIN
            )
        except ValueError:
            custom_domain_valid = False
    normalized_domain = managed_hostname
    normalized_site_url = (
        f"https://{managed_hostname}" if managed_hostname else ""
    )
    supplied_site_url = (
        site_url or (f"https://{requested_custom_domain or managed_hostname}" if managed_hostname else "")
    ).rstrip("/")
    try:
        parsed_site_url = urlparse(supplied_site_url)
        site_hostname = normalize_domain(parsed_site_url.hostname)
        site_port = parsed_site_url.port
    except ValueError:
        parsed_site_url = None
        site_hostname = None
        site_port = -1
    template = SITE_TEMPLATES.get(template_key)

    existing_tenant = (
        await db.exec(select(Tenant.id).where(Tenant.slug == slug))
    ).first()
    existing_owner = (
        await db.exec(select(User.id).where(func.lower(User.email) == owner_email.lower()))
    ).first()
    existing_domain = None
    availability_hostname = requested_custom_domain or normalized_domain
    if availability_hostname:
        existing_domain = (
            await db.exec(select(TenantDomain.id).where(TenantDomain.hostname == availability_hostname))
        ).first() or (
            await db.exec(
                select(SiteBuild.id).where(SiteBuild.primary_domain == availability_hostname)
            )
        ).first()
    existing_managed_domain = None
    if managed_hostname:
        existing_managed_domain = (
            await db.exec(
                select(TenantDomain.id).where(TenantDomain.hostname == managed_hostname)
            )
        ).first()

    checks = {
        "tenant_slug_available": existing_tenant is None,
        "forgebase_subdomain_valid": managed_hostname is not None,
        "forgebase_subdomain_available": existing_managed_domain is None,
        "owner_email_available": existing_owner is None,
        "template_publishable": bool(template and template.get("cms_connected")),
        "https_site_url": bool(
            parsed_site_url
            and parsed_site_url.scheme == "https"
            and site_hostname
        ),
        "site_url_has_no_credentials": bool(
            parsed_site_url
            and not parsed_site_url.username
            and not parsed_site_url.password
        ),
        "site_url_has_no_query_or_fragment": bool(
            parsed_site_url
            and not parsed_site_url.query
            and not parsed_site_url.fragment
        ),
        "site_url_uses_standard_port": site_port in {None, 443},
        "primary_domain_valid": bool(
            valid_hostname(availability_hostname) and custom_domain_valid
        ),
        "primary_domain_available": existing_domain is None,
        "domain_matches_site_url": bool(
            availability_hostname and site_hostname == availability_hostname
        ),
        "locale_set_supported": bool(locales)
        and len(locales) == len(set(locales))
        and all(locale in PUBLIC_SITE_LOCALES for locale in locales),
        "default_locale_enabled": default_locale in locales,
    }
    blockers = [name for name, passed in checks.items() if not passed]
    return {
        "ready": not blockers,
        "checks": checks,
        "blockers": blockers,
        "normalized": {
            "primary_domain": normalized_domain,
            "requested_custom_domain": requested_custom_domain,
            "forgebase_hostname": managed_hostname,
            "site_url": normalized_site_url,
            "owner_email": owner_email.lower(),
        },
    }
