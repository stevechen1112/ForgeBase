"""Private reverse-proxy control endpoints.

These routes are intentionally mounted outside /api and are reachable only on
the Docker network. The public Caddy routes never proxy /internal/*.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.models.tenant import Tenant
from app.models.tenant_domain import TenantDomain
from app.services.tenant_domains import normalize_hostname, valid_hostname

router = APIRouter(prefix="/internal", include_in_schema=False)


@router.get("/tls/authorize", status_code=status.HTTP_204_NO_CONTENT)
async def authorize_on_demand_tls(
    domain: str = Query(min_length=1, max_length=253),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Allow Caddy certificate issuance only for an active tenant hostname."""
    hostname = normalize_hostname(domain)
    if not valid_hostname(hostname):
        raise HTTPException(status_code=404, detail="Unknown tenant hostname")
    tenant_id = (
        await session.exec(
            select(TenantDomain.tenant_id)
            .join(Tenant, Tenant.id == TenantDomain.tenant_id)
            .where(
                TenantDomain.hostname == hostname,
                TenantDomain.status == "active",
                Tenant.is_active.is_(True),
            )
        )
    ).first()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Unknown tenant hostname")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
