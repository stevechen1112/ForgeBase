"""Tenant capability access for the single ForgeBase product."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models.tenant import Tenant
from app.models.user import User
from app.services.capability_access import resolve_tenant_features

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


class CapabilityAccess(BaseModel):
    product: str = "forgebase"
    features: dict[str, bool]


@router.get("/access", response_model=CapabilityAccess)
async def current_capability_access(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CapabilityAccess:
    if not current_user.tenant_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User has no tenant")
    tenant = await session.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return CapabilityAccess(features=resolve_tenant_features(tenant))
