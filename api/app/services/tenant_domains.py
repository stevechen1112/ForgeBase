"""Tenant-domain normalization and legacy compatibility helpers."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.models.site_build import SiteBuild
from app.models.site_profile import SiteProfile
from app.models.tenant_domain import DOMAIN_TYPES, TenantDomain

_DOMAIN_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


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


def hostname_from_url(value: str | None) -> str | None:
    try:
        return normalize_hostname(urlparse(value or "").hostname)
    except ValueError:
        return None


async def hostname_owner(
    db: AsyncSession, hostname: str | None
) -> TenantDomain | None:
    normalized = normalize_hostname(hostname)
    if not normalized:
        return None
    return (
        await db.exec(select(TenantDomain).where(TenantDomain.hostname == normalized))
    ).first()


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
