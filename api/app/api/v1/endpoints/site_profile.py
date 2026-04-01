"""
Site Profile — read and update per-site branding / theme configuration.

Routes:
  GET  /api/v1/site-profile       — public: returns the current site profile
  PUT  /api/v1/site-profile       — admin:  updates the site profile
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models.site_profile import SiteProfile
from app.models.user import User
from app.schemas.site_profile import SiteProfileRead, SiteProfileUpdate
from app.core.datetime import utcnow_naive

router = APIRouter(prefix="/site-profile", tags=["Site Profile"])


async def _get_or_create_profile(db: AsyncSession) -> SiteProfile:
    """Return the single site profile row, creating a default if none exists."""
    result = await db.exec(select(SiteProfile).limit(1))
    profile = result.first()
    if profile is None:
        profile = SiteProfile()
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


@router.get("", response_model=SiteProfileRead)
async def get_site_profile(db: AsyncSession = Depends(get_session)):
    """Public endpoint — returns current site branding and theme settings."""
    profile = await _get_or_create_profile(db)
    return profile


@router.put("", response_model=SiteProfileRead)
async def update_site_profile(
    payload: SiteProfileUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Admin-only — updates site branding and theme settings."""
    profile = await _get_or_create_profile(db)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
    profile.updated_at = utcnow_naive()
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
