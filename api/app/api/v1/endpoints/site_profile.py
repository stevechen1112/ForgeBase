"""
Site Profile — read and update per-site branding / theme configuration.

Routes:
  GET  /api/v1/site-profile       — public: returns the site profile for the
                                    current tenant (resolved via X-Tenant-ID header)
  PUT  /api/v1/site-profile       — admin:  updates the tenant's site profile
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_admin, resolve_tenant_id
from app.db.session import get_session
from app.models.site_profile import SiteProfile
from app.models.user import User
from app.schemas.site_profile import SiteProfileRead, SiteProfileUpdate
from app.core.datetime import utcnow_naive

router = APIRouter(prefix="/site-profile", tags=["Site Profile"])


async def _get_or_create_profile(
    db: AsyncSession,
    tenant_id: Optional[uuid.UUID],
) -> SiteProfile:
    """Return the site profile row for a tenant, creating a default if none exists."""
    stmt = select(SiteProfile)
    if tenant_id:
        stmt = stmt.where(SiteProfile.tenant_id == tenant_id)
    else:
        stmt = stmt.where(SiteProfile.tenant_id.is_(None))
    result = await db.exec(stmt.limit(1))
    profile = result.first()
    if profile is None:
        profile = SiteProfile(tenant_id=tenant_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


@router.get("", response_model=SiteProfileRead)
async def get_site_profile(
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[uuid.UUID] = Depends(resolve_tenant_id),
):
    """Public endpoint — returns site branding and theme settings for the current tenant."""
    profile = await _get_or_create_profile(db, tenant_id)
    return profile


@router.put("", response_model=SiteProfileRead)
async def update_site_profile(
    payload: SiteProfileUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Admin-only — updates site branding and theme settings for the current user's tenant."""
    profile = await _get_or_create_profile(db, current_user.tenant_id)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
    profile.updated_at = utcnow_naive()
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
