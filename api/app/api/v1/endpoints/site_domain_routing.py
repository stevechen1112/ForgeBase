"""Public exact-host canonical routing metadata for the shared frontend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import request_routing_hosts
from app.db.session import get_session
from app.models.tenant import Tenant
from app.models.tenant_domain import TenantDomain

router = APIRouter(prefix="/site-domain-routing", tags=["Site Domain Routing"])


@router.get("")
async def get_site_domain_routing(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    _, _, hostname = request_routing_hosts(request)
    if not hostname:
        raise HTTPException(status_code=404, detail="Tenant hostname not found")
    current = (
        await session.exec(
            select(TenantDomain)
            .join(Tenant, Tenant.id == TenantDomain.tenant_id)
            .where(
                TenantDomain.hostname == hostname,
                TenantDomain.status == "active",
                Tenant.is_active.is_(True),
            )
        )
    ).first()
    if not current:
        raise HTTPException(status_code=404, detail="Tenant hostname not found")
    canonical = (
        await session.exec(
            select(TenantDomain).where(
                TenantDomain.tenant_id == current.tenant_id,
                TenantDomain.status == "active",
                TenantDomain.is_canonical.is_(True),
            )
        )
    ).first()
    if not canonical:
        raise HTTPException(status_code=503, detail="Canonical hostname unavailable")
    return {
        "hostname": current.hostname,
        "canonical_hostname": canonical.hostname,
        "redirect_required": bool(
            current.redirect_to_canonical and current.id != canonical.id
        ),
    }
