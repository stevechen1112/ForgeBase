from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import RequireFeature, require_user_tenant_id
from app.core.locale import (
    SUPPORTED_CONTENT_LOCALES,
    locale_catalog_payload,
    to_content_locale,
)
from app.db.session import get_session
from app.models.user import User
from app.services.locale_support import default_buyer_locale, get_source_locale

router = APIRouter(tags=["Locale Quality"])

_ENTITIES = (
    ("products", "products", "slug"),
    ("categories", "product_categories", "slug"),
    ("applications", "applications", "slug"),
    ("pages", "pages", "slug"),
    ("faqs", "faq_items", "variant_key"),
    ("comparisons", "comparison_topics", "slug"),
    ("certifications", "certifications", "slug"),
    ("capabilities", "capabilities", "slug"),
)


@router.get("/locale-settings")
async def locale_settings(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(RequireFeature("multilingual")),
) -> dict[str, Any]:
    """Return the tenant source locale and the content/public locale boundary."""
    if current_user.role not in {"owner", "admin", "marketing_manager"}:
        raise HTTPException(status_code=403, detail="Content editor access required")
    tenant_id = require_user_tenant_id(current_user)
    source = await get_source_locale(db, tenant_id)
    return {
        "source_locale": source,
        "content_locales": locale_catalog_payload(),
        "public_shell_locales": [
            row["content_locale"]
            for row in locale_catalog_payload()
            if row["public_shell_ready"]
        ],
        "policy": (
            "All generated translations remain drafts until an editor publishes them. "
            "A content locale does not imply that the complete public-site interface pack is ready."
        ),
    }


@router.get("/locale-coverage")
async def locale_coverage(
    target_locale: str | None = Query(None),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(RequireFeature("multilingual")),
) -> dict[str, Any]:
    """Report missing, draft, and stale buyer-locale variants. Does not generate content."""
    if current_user.role not in {"owner", "admin", "marketing_manager"}:
        raise HTTPException(status_code=403, detail="Content editor access required")
    tenant_id = require_user_tenant_id(current_user)
    source = await get_source_locale(db, tenant_id)
    target = to_content_locale(target_locale or default_buyer_locale(source), default="")
    if target not in SUPPORTED_CONTENT_LOCALES or target == source:
        raise HTTPException(status_code=422, detail="target_locale must be a supported buyer locale")
    rows: list[dict[str, Any]] = []
    for entity, table, key in _ENTITIES:
        query = text(f"""
            SELECT
                COUNT(*) AS source_total,
                COUNT(*) FILTER (WHERE target.id IS NOT NULL) AS translated,
                COUNT(*) FILTER (
                    WHERE target.status IN ('published', 'active')
                ) AS published,
                COUNT(*) FILTER (WHERE target.status = 'draft') AS draft,
                COUNT(*) FILTER (
                    WHERE target.status IN ('published', 'active')
                      AND source.status IN ('published', 'active')
                      AND source.updated_at > COALESCE(target.updated_at, target.created_at)
                ) AS stale,
                ARRAY_REMOVE(ARRAY_AGG(source.{key}) FILTER (WHERE target.id IS NULL), NULL) AS missing_keys,
                ARRAY_REMOVE(ARRAY_AGG(source.id) FILTER (WHERE target.id IS NULL), NULL) AS missing_ids,
                ARRAY_REMOVE(ARRAY_AGG(source.{key}) FILTER (WHERE target.status = 'draft'), NULL) AS draft_keys,
                ARRAY_REMOVE(
                    ARRAY_AGG(source.{key}) FILTER (
                        WHERE target.status IN ('published', 'active')
                          AND source.status IN ('published', 'active')
                          AND source.updated_at > COALESCE(target.updated_at, target.created_at)
                    ),
                    NULL
                ) AS stale_keys
            FROM {table} source
            LEFT JOIN {table} target
              ON target.tenant_id = source.tenant_id
             AND target.{key} = source.{key}
             AND target.locale = :target
            WHERE source.tenant_id = :tenant_id
              AND source.locale = :source
        """)
        result = (await db.exec(
            query,
            params={"tenant_id": tenant_id, "target": target, "source": source},
        )).mappings().one()
        source_total = int(result["source_total"] or 0)
        translated = int(result["translated"] or 0)
        published = int(result["published"] or 0)
        draft = int(result["draft"] or 0)
        stale = int(result["stale"] or 0)
        rows.append({
            "entity": entity,
            "source_total": source_total,
            "translated": translated,
            "published": published,
            "draft": draft,
            "stale": stale,
            "coverage_pct": round(translated / source_total * 100, 1) if source_total else 100.0,
            "published_pct": round(published / source_total * 100, 1) if source_total else 100.0,
            "missing_count": max(source_total - translated, 0),
            "missing_keys": list(result["missing_keys"] or [])[:100],
            "missing_ids": [str(item) for item in list(result["missing_ids"] or [])[:100]],
            "draft_keys": list(result["draft_keys"] or [])[:100],
            "stale_keys": list(result["stale_keys"] or [])[:100],
        })
    total = sum(row["source_total"] for row in rows)
    translated = sum(row["translated"] for row in rows)
    missing = sum(row["missing_count"] for row in rows)
    draft = sum(row["draft"] for row in rows)
    stale = sum(row["stale"] for row in rows)
    return {
        "source_locale": source,
        "target_locale": target,
        "overall_coverage_pct": round(translated / total * 100, 1) if total else 100.0,
        "missing": missing,
        "draft": draft,
        "stale": stale,
        "entities": rows,
        "policy": "Buyer-locale drafts are unpublished until an editor publishes them. ForgeBase does not auto-publish translations.",
    }
