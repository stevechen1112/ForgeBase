"""Validation and replay-safe helpers for atomic tenant delivery."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.locale import PUBLIC_SITE_LOCALES
from app.models.site_build import SiteBuild
from app.models.tenant import Tenant
from app.models.tenant_domain import TenantDomain
from app.models.user import User
from app.services.site_provisioning import SITE_TEMPLATES
from app.services.tenant_domains import normalize_hostname, valid_hostname


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
    site_url: str,
    primary_domain: str | None,
    default_locale: str,
    locales: list[str],
) -> dict[str, Any]:
    normalized_domain = normalize_domain(primary_domain)
    try:
        parsed_site_url = urlparse(site_url)
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
    if normalized_domain:
        existing_domain = (
            await db.exec(select(TenantDomain.id).where(TenantDomain.hostname == normalized_domain))
        ).first() or (
            await db.exec(
                select(SiteBuild.id).where(SiteBuild.primary_domain == normalized_domain)
            )
        ).first()

    checks = {
        "tenant_slug_available": existing_tenant is None,
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
        "primary_domain_valid": valid_hostname(normalized_domain),
        "primary_domain_available": existing_domain is None,
        "domain_matches_site_url": bool(
            normalized_domain and site_hostname == normalized_domain
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
            "site_url": site_url.rstrip("/"),
            "owner_email": owner_email.lower(),
        },
    }
