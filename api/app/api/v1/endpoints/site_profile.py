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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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


# ── Ops Config（RFQ 自動回覆 / SLA）──────────────────────────────────────────
# 獨立於公開 GET /site-profile，避免 LINE token 等營運設定外洩。
# 實際生效的 key 見 app/services/rfq_auto_reply.py 與 app/services/sla.py。

_KNOWN_OPS_KEYS = {
    "auto_reply_enabled",
    "auto_reply_signature",
    "auto_reply_from_name",
    "sla_response_hours",
}


class OpsConfigUpdate(BaseModel):
    auto_reply_enabled: Optional[bool] = None
    auto_reply_signature: Optional[str] = Field(default=None, max_length=200)
    auto_reply_from_name: Optional[str] = Field(default=None, max_length=120)
    sla_response_hours: Optional[float] = Field(default=None, gt=0, le=168)


def _load_ops_dict(profile: SiteProfile) -> dict:
    import json

    if not profile.ops_config_json:
        return {}
    try:
        raw = json.loads(profile.ops_config_json)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


@router.get("/ops-config")
async def get_ops_config(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Admin-only — 回傳租戶營運設定（含未來擴充的未知 key）。"""
    profile = await _get_or_create_profile(db, current_user.tenant_id)
    return _load_ops_dict(profile)

@router.put("/ops-config")
async def update_ops_config(
    payload: OpsConfigUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Admin-only — 更新營運設定；僅覆寫有提供的 key，其餘保留。"""
    import json

    profile = await _get_or_create_profile(db, current_user.tenant_id)
    config = _load_ops_dict(profile)
    unknown = set(config) - _KNOWN_OPS_KEYS
    if unknown:
        # 保留未知 key，避免手動寫入的實驗性設定被 UI 清掉
        preserved = {k: config[k] for k in unknown}
    else:
        preserved = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None:
            config.pop(key, None)
        else:
            config[key] = value
    config.update(preserved)
    config = {**{k: v for k, v in config.items() if k in _KNOWN_OPS_KEYS}, **preserved}
    profile.ops_config_json = json.dumps(config, ensure_ascii=False)
    profile.updated_at = utcnow_naive()
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return _load_ops_dict(profile)
