"""Per-tenant ops config loader (SiteProfile.ops_config_json).

承載 T6/T7 等營運開關，key 見 migration 0048 說明。
"""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def load_ops_config(tenant_id, db) -> dict[str, Any]:
    """回傳 tenant 的 ops config dict；無設定或解析失敗回 {}。"""
    if not tenant_id:
        return {}
    try:
        from sqlmodel import select

        from app.models.site_profile import SiteProfile

        profile = (
            await db.exec(
                select(SiteProfile)
                .where(SiteProfile.tenant_id == tenant_id)
                .limit(1)
            )
        ).first()
        if profile and profile.ops_config_json:
            raw = json.loads(profile.ops_config_json)
            return raw if isinstance(raw, dict) else {}
    except Exception:
        logger.debug("ops config unavailable for tenant %s", tenant_id, exc_info=True)
    return {}
