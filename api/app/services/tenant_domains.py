"""Tenant-domain normalization and legacy compatibility helpers."""

from __future__ import annotations

import ipaddress
import re
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.models.site_build import SiteBuild
from app.models.site_profile import SiteProfile
from app.models.tenant_domain import DOMAIN_TYPES, TenantDomain

_DOMAIN_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
RESERVED_TENANT_SUBDOMAINS = {
    "admin",
    "api",
    "app",
    "edge",
    "mail",
    "replies",
    "status",
    "support",
    "www",
}


class DomainConflictError(ValueError):
    """The normalized hostname is already assigned to another tenant."""


def normalize_hostname(value: str | None) -> str | None:
    normalized = (value or "").strip().lower().rstrip(".")
    if not normalized:
        return None
    try:
        return normalized.encode("idna").decode("ascii")
    except UnicodeError:
        return None


def valid_hostname(value: str | None) -> bool:
    normalized = normalize_hostname(value)
    if not normalized or len(normalized) > 253 or "." not in normalized:
        return False
    try:
        ipaddress.ip_address(normalized)
        return False
    except ValueError:
        pass
    return all(_DOMAIN_LABEL.fullmatch(label) for label in normalized.split("."))


async def hostname_owner(
    db: AsyncSession, hostname: str | None
) -> TenantDomain | None:
    normalized = normalize_hostname(hostname)
    if not normalized:
        return None
    return (
        await db.exec(select(TenantDomain).where(TenantDomain.hostname == normalized))
    ).first()


def forgebase_hostname_for_slug(slug: str, base_domain: str) -> str:
    """Return the platform-provided hostname for a tenant slug."""
    normalized_slug = (slug or "").strip().lower()
    normalized_base = normalize_hostname(base_domain)
    if (
        not _DOMAIN_LABEL.fullmatch(normalized_slug)
        or normalized_slug in RESERVED_TENANT_SUBDOMAINS
        or not valid_hostname(normalized_base)
    ):
        raise ValueError("Tenant slug cannot be used as a ForgeBase subdomain")
    hostname = f"{normalized_slug}.{normalized_base}"
    if not valid_hostname(hostname):
        raise ValueError("Generated ForgeBase hostname is invalid")
    return hostname


async def ensure_forgebase_subdomain(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    slug: str,
    base_domain: str,
    dns_target: str,
    created_by_user_id: UUID | None = None,
) -> TenantDomain:
    """Create the always-available managed hostname for one tenant."""
    hostname = forgebase_hostname_for_slug(slug, base_domain)
    normalized_target = normalize_hostname(dns_target)
    if not valid_hostname(normalized_target):
        raise ValueError("Invalid tenant CNAME target")

    existing = await hostname_owner(db, hostname)
    if existing:
        if existing.tenant_id != tenant_id:
            raise DomainConflictError("ForgeBase subdomain is already assigned")
        return existing

    current_domains = (
        await db.exec(select(TenantDomain).where(TenantDomain.tenant_id == tenant_id))
    ).all()
    make_canonical = not any(item.is_canonical for item in current_domains)
    now = utcnow_naive()
    domain = TenantDomain(
        tenant_id=tenant_id,
        hostname=hostname,
        domain_type="forgebase_subdomain",
        status="active",
        is_canonical=make_canonical,
        verification_method="platform_managed",
        dns_target=normalized_target,
        dns_verified_at=now,
        tls_status="pending",
        activated_at=now,
        redirect_to_canonical=not make_canonical,
        created_by_user_id=created_by_user_id,
    )
    db.add(domain)
    return domain


async def set_legacy_canonical_domain(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    hostname: str | None,
    created_by_user_id: UUID | None = None,
    domain_type: str = "custom",
    sync_profile_url: bool = True,
    verification_method: str = "legacy_controlled",
) -> TenantDomain | None:
    """Mirror a legacy primary-domain write into the new source-of-truth table.

    This helper deliberately records the domain as an already-active legacy
    assignment. New custom-domain flows must use DNS verification instead.
    """
    supplied = (hostname or "").strip()
    normalized = normalize_hostname(hostname)
    if supplied and (not normalized or not valid_hostname(normalized)):
        raise ValueError("Invalid hostname")
    if domain_type not in DOMAIN_TYPES:
        raise ValueError("Invalid domain type")

    current_domains = (
        await db.exec(select(TenantDomain).where(TenantDomain.tenant_id == tenant_id))
    ).all()
    if not normalized:
        for item in current_domains:
            if item.is_canonical:
                item.is_canonical = False
                item.updated_at = utcnow_naive()
                db.add(item)
        build = (
            await db.exec(select(SiteBuild).where(SiteBuild.tenant_id == tenant_id))
        ).first()
        if build:
            build.primary_domain = None
            build.updated_at = utcnow_naive()
            db.add(build)
        return None

    existing = await hostname_owner(db, normalized)
    if existing and existing.tenant_id != tenant_id:
        raise DomainConflictError("Hostname is already assigned")

    now = utcnow_naive()
    canonical_changed = False
    for item in current_domains:
        if item.is_canonical and item.hostname != normalized:
            item.is_canonical = False
            item.redirect_to_canonical = True
            item.updated_at = now
            db.add(item)
            canonical_changed = True

    # The partial unique index permits only one canonical row per tenant.
    # Persist demotions before promoting or inserting the replacement.
    if canonical_changed:
        await db.flush()

    domain = existing or TenantDomain(
        tenant_id=tenant_id,
        hostname=normalized,
        domain_type=domain_type,
        created_by_user_id=created_by_user_id,
        verification_method=verification_method,
    )
    domain.domain_type = domain_type
    domain.status = "active"
    domain.is_canonical = True
    domain.redirect_to_canonical = False
    domain.activated_at = domain.activated_at or now
    domain.updated_at = now
    db.add(domain)

    build = (
        await db.exec(select(SiteBuild).where(SiteBuild.tenant_id == tenant_id))
    ).first()
    if build:
        build.primary_domain = normalized
        build.updated_at = now
        db.add(build)
    if sync_profile_url:
        profile = (
            await db.exec(select(SiteProfile).where(SiteProfile.tenant_id == tenant_id))
        ).first()
        if profile:
            profile.site_url = f"https://{normalized}"
            profile.updated_at = now
            db.add(profile)
    return domain
