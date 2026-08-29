"""Platform-operated lifecycle for managed and customer tenant domains."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import clear_tenant_host_cache, require_superuser
from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.platform_audit_log import PlatformAuditLog
from app.models.tenant import Tenant
from app.models.tenant_domain import TenantDomain
from app.models.user import User
from app.services.domain_verification import (
    DNSLookupError,
    inspect_custom_domain_dns,
    verification_hostname,
    verification_txt_value,
)
from app.services.tenant_domains import (
    DomainConflictError,
    DomainLifecycleError,
    activate_verified_custom_domain,
    register_custom_domain,
    suspend_custom_domain,
)

router = APIRouter(prefix="/admin/tenants", tags=["Platform Tenant Domains"])


class CustomDomainCreate(BaseModel):
    hostname: str = Field(min_length=4, max_length=253)


def _payload(domain: TenantDomain) -> dict[str, Any]:
    token = domain.verification_token
    try:
        dns_observed = json.loads(domain.dns_observed_json or "{}")
    except (TypeError, json.JSONDecodeError):
        dns_observed = {}
    return {
        "id": str(domain.id),
        "tenant_id": str(domain.tenant_id),
        "hostname": domain.hostname,
        "domain_type": domain.domain_type,
        "status": domain.status,
        "is_canonical": domain.is_canonical,
        "redirect_to_canonical": domain.redirect_to_canonical,
        "verification_method": domain.verification_method,
        "verification": (
            {
                "record_type": "TXT",
                "record_name": verification_hostname(domain.hostname),
                "record_value": verification_txt_value(token),
            }
            if domain.domain_type == "custom" and token
            else None
        ),
        "routing": {
            "record_type": "CNAME",
            "supported_record_types": ["CNAME", "ALIAS", "ANAME"],
            "record_name": domain.hostname,
            "record_value": domain.dns_target,
        },
        "dns_observed": dns_observed,
        "dns_verified_at": domain.dns_verified_at,
        "tls_status": domain.tls_status,
        "tls_issued_at": domain.tls_issued_at,
        "activated_at": domain.activated_at,
        "last_checked_at": domain.last_checked_at,
        "failure_reason": domain.failure_reason,
        "created_at": domain.created_at,
        "updated_at": domain.updated_at,
    }


def _audit(
    session: AsyncSession,
    actor: User,
    domain: TenantDomain,
    *,
    action: str,
    changes: dict[str, Any],
) -> None:
    session.add(
        PlatformAuditLog(
            actor_user_id=actor.id,
            actor_email=actor.email,
            tenant_id=domain.tenant_id,
            action=action,
            target_type="tenant_domain",
            target_id=str(domain.id),
            changes_json=json.dumps(changes, default=str, ensure_ascii=False),
        )
    )


async def _get_custom_domain(
    session: AsyncSession, tenant_id: UUID, domain_id: UUID
) -> TenantDomain:
    domain = await session.get(TenantDomain, domain_id)
    if not domain or domain.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Tenant domain not found")
    if domain.domain_type != "custom":
        raise HTTPException(
            status_code=409, detail="This operation is only for customer domains"
        )
    return domain


async def _lock_tenant(session: AsyncSession, tenant_id: UUID) -> Tenant:
    tenant = (
        await session.exec(
            select(Tenant).where(Tenant.id == tenant_id).with_for_update()
        )
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


async def _inspect_and_store(domain: TenantDomain) -> dict[str, Any]:
    if not domain.verification_token or not domain.dns_target:
        raise DomainLifecycleError("Domain verification configuration is incomplete")
    observation = await inspect_custom_domain_dns(
        domain.hostname,
        domain.verification_token,
        domain.dns_target,
    )
    now = utcnow_naive()
    observed = observation.payload()
    domain.dns_observed_json = json.dumps(observed, sort_keys=True)
    domain.last_checked_at = now
    domain.updated_at = now
    was_active = domain.status == "active"
    if observation.ready:
        domain.status = "active" if was_active else "verified"
        domain.dns_verified_at = now
        domain.failure_reason = None
    else:
        domain.status = "active" if was_active else "verifying"
        if not was_active:
            domain.dns_verified_at = None
        missing = []
        if not observation.ownership_verified:
            missing.append("ownership_txt")
        if not observation.routing_verified:
            missing.append("forgebase_routing")
        domain.failure_reason = f"DNS verification incomplete: {', '.join(missing)}"
    return observed


@router.get("/{tenant_id}/domains")
async def list_tenant_domains(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> list[dict[str, Any]]:
    if not await session.get(Tenant, tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    domains = (
        await session.exec(
            select(TenantDomain)
            .where(TenantDomain.tenant_id == tenant_id)
            .order_by(TenantDomain.is_canonical.desc(), TenantDomain.created_at)
        )
    ).all()
    return [_payload(domain) for domain in domains]


@router.post("/{tenant_id}/domains", status_code=status.HTTP_201_CREATED)
async def create_custom_domain(
    tenant_id: UUID,
    body: CustomDomainCreate,
    session: AsyncSession = Depends(get_session),
    actor: User = Depends(require_superuser),
) -> dict[str, Any]:
    await _lock_tenant(session, tenant_id)
    fallback = (
        await session.exec(
            select(TenantDomain.id).where(
                TenantDomain.tenant_id == tenant_id,
                TenantDomain.domain_type == "forgebase_subdomain",
                TenantDomain.status == "active",
            )
        )
    ).first()
    if not fallback:
        raise HTTPException(
            status_code=409,
            detail="An active ForgeBase fallback hostname is required first",
        )
    try:
        domain = await register_custom_domain(
            session,
            tenant_id=tenant_id,
            hostname=body.hostname,
            base_domain=settings.TENANT_BASE_DOMAIN,
            dns_target=settings.TENANT_CNAME_TARGET,
            created_by_user_id=actor.id,
        )
        await session.flush()
        _audit(
            session,
            actor,
            domain,
            action="tenant_domain.registered",
            changes={"hostname": domain.hostname, "status": domain.status},
        )
        await session.commit()
        await session.refresh(domain)
    except DomainConflictError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Hostname is already assigned") from exc
    return _payload(domain)


@router.post("/{tenant_id}/domains/{domain_id}/verify")
async def verify_custom_domain(
    tenant_id: UUID,
    domain_id: UUID,
    session: AsyncSession = Depends(get_session),
    actor: User = Depends(require_superuser),
) -> dict[str, Any]:
    await _lock_tenant(session, tenant_id)
    domain = await _get_custom_domain(session, tenant_id, domain_id)
    try:
        observed = await _inspect_and_store(domain)
    except DNSLookupError as exc:
        if domain.status != "active":
            domain.status = "verifying"
        domain.last_checked_at = utcnow_naive()
        domain.failure_reason = "DNS resolver temporarily unavailable"
        domain.updated_at = domain.last_checked_at
        session.add(domain)
        _audit(
            session,
            actor,
            domain,
            action="tenant_domain.verification_unavailable",
            changes={"hostname": domain.hostname},
        )
        await session.commit()
        raise HTTPException(
            status_code=503, detail="DNS verification is temporarily unavailable"
        ) from exc
    session.add(domain)
    _audit(
        session,
        actor,
        domain,
        action="tenant_domain.verified" if observed["ready"] else "tenant_domain.verification_pending",
        changes={
            "hostname": domain.hostname,
            "ownership_verified": observed["ownership_verified"],
            "routing_verified": observed["routing_verified"],
        },
    )
    await session.commit()
    await session.refresh(domain)
    return _payload(domain)


@router.post("/{tenant_id}/domains/{domain_id}/activate")
async def activate_custom_domain(
    tenant_id: UUID,
    domain_id: UUID,
    session: AsyncSession = Depends(get_session),
    actor: User = Depends(require_superuser),
) -> dict[str, Any]:
    await _lock_tenant(session, tenant_id)
    domain = await _get_custom_domain(session, tenant_id, domain_id)
    try:
        observed = await _inspect_and_store(domain)
        if not observed["ready"]:
            session.add(domain)
            _audit(
                session,
                actor,
                domain,
                action="tenant_domain.activation_blocked",
                changes={
                    "hostname": domain.hostname,
                    "ownership_verified": observed["ownership_verified"],
                    "routing_verified": observed["routing_verified"],
                },
            )
            await session.commit()
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "domain_dns_not_ready",
                    "ownership_verified": observed["ownership_verified"],
                    "routing_verified": observed["routing_verified"],
                },
            )
        if not (domain.status == "active" and domain.is_canonical):
            await activate_verified_custom_domain(session, domain=domain)
        _audit(
            session,
            actor,
            domain,
            action="tenant_domain.activated",
            changes={"hostname": domain.hostname, "canonical": True},
        )
        await session.commit()
        await session.refresh(domain)
    except DNSLookupError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=503, detail="DNS verification is temporarily unavailable"
        ) from exc
    except DomainLifecycleError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    clear_tenant_host_cache()
    return _payload(domain)


@router.post("/{tenant_id}/domains/{domain_id}/suspend")
async def suspend_tenant_domain(
    tenant_id: UUID,
    domain_id: UUID,
    session: AsyncSession = Depends(get_session),
    actor: User = Depends(require_superuser),
) -> dict[str, Any]:
    await _lock_tenant(session, tenant_id)
    domain = await _get_custom_domain(session, tenant_id, domain_id)
    try:
        await suspend_custom_domain(session, domain=domain)
        _audit(
            session,
            actor,
            domain,
            action="tenant_domain.suspended",
            changes={"hostname": domain.hostname, "fallback_restored": True},
        )
        await session.commit()
        await session.refresh(domain)
    except DomainLifecycleError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    clear_tenant_host_cache()
    return _payload(domain)
