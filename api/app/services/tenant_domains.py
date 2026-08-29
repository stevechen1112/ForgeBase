"""Tenant-domain normalization and legacy compatibility helpers."""

from __future__ import annotations

import ipaddress
import re
import secrets
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.models.site_build import SiteBuild
from app.models.site_profile import SiteProfile
from app.models.tenant_domain import TenantDomain

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


class DomainLifecycleError(ValueError):
    """A domain cannot perform the requested lifecycle transition."""


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


def validate_custom_hostname(hostname: str | None, base_domain: str) -> str:
    normalized = normalize_hostname(hostname)
    normalized_base = normalize_hostname(base_domain)
    if not valid_hostname(normalized):
        raise ValueError("Invalid custom hostname")
    if normalized_base and (
        normalized == normalized_base or normalized.endswith(f".{normalized_base}")
    ):
        raise ValueError("ForgeBase-managed hostnames cannot be customer domains")
    return normalized


async def register_custom_domain(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    hostname: str,
    base_domain: str,
    dns_target: str,
    created_by_user_id: UUID | None,
) -> TenantDomain:
    """Register a customer hostname without making it reachable or canonical."""
    normalized = validate_custom_hostname(hostname, base_domain)
    normalized_target = normalize_hostname(dns_target)
    if not valid_hostname(normalized_target):
        raise ValueError("Invalid tenant CNAME target")
    existing = await hostname_owner(db, normalized)
    if existing:
        raise DomainConflictError("Hostname is already registered")

    now = utcnow_naive()
    domain = TenantDomain(
        tenant_id=tenant_id,
        hostname=normalized,
        domain_type="custom",
        status="pending",
        is_canonical=False,
        verification_method="dns_txt_and_route",
        verification_token=secrets.token_urlsafe(32),
        dns_target=normalized_target,
        tls_status="unknown",
        redirect_to_canonical=True,
        created_by_user_id=created_by_user_id,
        updated_at=now,
    )
    db.add(domain)
    return domain


async def sync_canonical_domain_projections(
    db: AsyncSession, *, tenant_id: UUID, hostname: str
) -> None:
    """Keep legacy URL columns as read-only projections of TenantDomain."""
    now = utcnow_naive()
    build = (
        await db.exec(select(SiteBuild).where(SiteBuild.tenant_id == tenant_id))
    ).first()
    if build:
        build.primary_domain = hostname
        build.updated_at = now
        db.add(build)
    profile = (
        await db.exec(select(SiteProfile).where(SiteProfile.tenant_id == tenant_id))
    ).first()
    if profile:
        profile.site_url = f"https://{hostname}"
        profile.updated_at = now
        db.add(profile)


async def activate_verified_custom_domain(
    db: AsyncSession, *, domain: TenantDomain
) -> TenantDomain:
    if domain.domain_type != "custom":
        raise DomainLifecycleError("Only customer domains use this activation flow")
    if domain.status not in {"verified", "active"} or not domain.dns_verified_at:
        raise DomainLifecycleError("Domain must pass DNS verification before activation")

    domains = (
        await db.exec(
            select(TenantDomain).where(TenantDomain.tenant_id == domain.tenant_id)
        )
    ).all()
    now = utcnow_naive()
    demoted = False
    for item in domains:
        if item.id != domain.id and item.is_canonical:
            item.is_canonical = False
            item.redirect_to_canonical = True
            item.updated_at = now
            db.add(item)
            demoted = True
    if demoted:
        await db.flush()

    domain.status = "active"
    domain.is_canonical = True
    domain.redirect_to_canonical = False
    domain.tls_status = "pending"
    domain.activated_at = now
    domain.failure_reason = None
    domain.updated_at = now
    db.add(domain)
    await sync_canonical_domain_projections(
        db, tenant_id=domain.tenant_id, hostname=domain.hostname
    )
    return domain


async def suspend_custom_domain(
    db: AsyncSession, *, domain: TenantDomain
) -> TenantDomain:
    """Suspend a custom host and atomically fall back to the free hostname."""
    if domain.domain_type != "custom":
        raise DomainLifecycleError("The ForgeBase hostname cannot be suspended")
    now = utcnow_naive()
    was_canonical = domain.is_canonical
    domain.status = "suspended"
    domain.is_canonical = False
    domain.redirect_to_canonical = False
    domain.updated_at = now
    db.add(domain)
    if not was_canonical:
        return domain
    await db.flush()

    managed = (
        await db.exec(
            select(TenantDomain).where(
                TenantDomain.tenant_id == domain.tenant_id,
                TenantDomain.domain_type == "forgebase_subdomain",
                TenantDomain.status == "active",
            )
        )
    ).first()
    if not managed:
        raise DomainLifecycleError("No active ForgeBase fallback hostname exists")
    managed.is_canonical = True
    managed.redirect_to_canonical = False
    managed.updated_at = now
    db.add(managed)
    await sync_canonical_domain_projections(
        db, tenant_id=domain.tenant_id, hostname=managed.hostname
    )
    return domain
