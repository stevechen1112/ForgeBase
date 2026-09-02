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

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import (
    clear_tenant_host_cache,
    optional_current_user,
    require_admin,
    require_content_editor,
    resolve_tenant_id,
)
from app.core.datetime import utcnow_naive
from app.core.locale import LOCALE_CATALOG, to_content_locale, to_route_locale
from app.db.session import get_session
from app.models.site_profile import SiteProfile
from app.models.user import User
from app.schemas.site_profile import SiteProfileRead, SiteProfileUpdate

router = APIRouter(prefix="/site-profile", tags=["Site Profile"])

_TENANT_EDITABLE_PROFILE_FIELDS = {
    "brand_name",
    "logo_mark",
    "logo_url",
    "contact_email",
    "contact_phone",
    "default_locale",
    "translation_glossary_json",
}


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
    current_user: User | None = Depends(optional_current_user),
):
    """Return branding for the authenticated tenant or the resolved public host."""
    resolved_tenant_id = current_user.tenant_id if current_user and current_user.tenant_id else tenant_id
    profile = await _get_or_create_profile(db, resolved_tenant_id)
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
    if "default_locale" in update_data and update_data["default_locale"] is not None:
        locale = to_content_locale(str(update_data["default_locale"]), default="")
        if locale not in LOCALE_CATALOG:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported default_locale")
        update_data["default_locale"] = to_route_locale(locale)
    restricted_fields = sorted(set(update_data) - _TENANT_EDITABLE_PROFILE_FIELDS)
    if restricted_fields:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "These delivery settings can only be changed by ForgeBase support.",
                "fields": restricted_fields,
            },
        )
    for key, value in update_data.items():
        setattr(profile, key, value)
    profile.updated_at = utcnow_naive()
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    clear_tenant_host_cache()
    return profile


# ── Ops Config（RFQ 收件確認 / 接手 SLA）────────────────────────────────────
# 獨立於公開 GET /site-profile，避免 LINE token 等營運設定外洩。
# 實際生效的 key 見 app/services/rfq_auto_reply.py 與 app/services/sla.py。

_KNOWN_OPS_KEYS = {
    "auto_reply_enabled",
    "auto_reply_signature",
    "auto_reply_from_name",
    "sla_acceptance_hours",
}


class OpsConfigUpdate(BaseModel):
    auto_reply_enabled: Optional[bool] = None
    auto_reply_signature: Optional[str] = Field(default=None, max_length=200)
    auto_reply_from_name: Optional[str] = Field(default=None, max_length=120)
    sla_acceptance_hours: Optional[float] = Field(default=None, gt=0, le=168)


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


class TenantCopyUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    locale: str = "en"
    copy_payload: dict = Field(default_factory=dict, alias="copy")
    assets: dict | None = None
    hidden_blocks: dict | None = None
    logo_url: str | None = None


@router.get("/tenant-copy")
async def get_tenant_copy(
    locale: str = Query("en"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    from app.services import tenant_copy as tenant_copy_service

    if not current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")
    profile = await _get_or_create_profile(db, current_user.tenant_id)
    site_copy = tenant_copy_service.parse_json_object(profile.site_copy_json)
    manifest = tenant_copy_service.parse_json_object(profile.asset_manifest_json)
    resolved = tenant_copy_service.locale_key(locale)
    overlay = tenant_copy_service.extract_locale_overlay(site_copy, resolved)
    return {
        "locale": resolved,
        "copy": tenant_copy_service.serialize_overlay(overlay),
        "assets": tenant_copy_service.read_assets(manifest),
        "hidden_blocks": tenant_copy_service.read_hidden_blocks(site_copy),
        "logo_url": profile.logo_url or "",
    }


@router.put("/tenant-copy")
async def update_tenant_copy(
    payload: TenantCopyUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    from app.services import tenant_copy as tenant_copy_service
    from app.services.revalidate import revalidate_tenant_copy

    if not current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")
    profile = await _get_or_create_profile(db, current_user.tenant_id)
    site_copy = tenant_copy_service.parse_json_object(profile.site_copy_json)
    manifest = tenant_copy_service.parse_json_object(profile.asset_manifest_json)
    resolved = tenant_copy_service.locale_key(payload.locale)
    try:
        site_copy = tenant_copy_service.apply_copy_overlay(site_copy, resolved, payload.copy_payload)
        site_copy = tenant_copy_service.apply_hidden_blocks(site_copy, payload.hidden_blocks)
        manifest = tenant_copy_service.apply_assets(manifest, payload.assets)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    profile.site_copy_json = tenant_copy_service.dump_json(site_copy)
    profile.asset_manifest_json = tenant_copy_service.dump_json(manifest)
    if "logo_url" in payload.model_fields_set:
        cleaned_logo = (payload.logo_url or "").strip()
        profile.logo_url = cleaned_logo[:500] or None
    profile.updated_at = utcnow_naive()
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    clear_tenant_host_cache()
    await revalidate_tenant_copy()
    overlay = tenant_copy_service.extract_locale_overlay(site_copy, resolved)
    return {
        "locale": resolved,
        "copy": tenant_copy_service.serialize_overlay(overlay),
        "assets": tenant_copy_service.read_assets(manifest),
        "hidden_blocks": tenant_copy_service.read_hidden_blocks(site_copy),
        "logo_url": profile.logo_url or "",
    }
