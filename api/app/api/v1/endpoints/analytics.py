"""
2.5.x Analytics API
===================
GET /tracking/analytics/pages          — 2.5.1 Page-level performance
GET /tracking/analytics/products       — 2.5.2 Product-level performance
GET /tracking/analytics/applications   — 2.5.2 Application-level performance
GET /tracking/analytics/strategy-map   — 2.5.3 Content strategy map overlay
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models.user import User

router = APIRouter(prefix="/tracking/analytics", tags=["Analytics"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ── 2.5.1  Page-level analytics ───────────────────────────────────────────────

@router.get("/pages")
async def page_analytics(
    days: int = Query(30, ge=1, le=365, description="Look-back window in days"),
    page_type: str | None = Query(None, description="Filter by page_type (product/application/page/category)"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Per-page aggregated metrics over the last N days.
    Joins tracking_events + visitors (for avg intent score) + rfq_requests (for RFQ count).
    """
    page_type_filter = "AND te.page_type = :page_type" if page_type else ""
    sql = text(f"""
        SELECT
            te.page_id::text                                              AS page_id,
            te.page_type                                                  AS page_type,
            -- try to surface a label from products / applications tables
            COALESCE(p.product_name, app.application_name, pg.title, te.page_type) AS page_name,
            COUNT(*)                                                      AS page_views,
            COUNT(DISTINCT te.visitor_id)                                 AS unique_visitors,
            SUM(CASE WHEN te.event_name = 'spec_download' THEN 1 ELSE 0 END) AS spec_downloads,
            SUM(CASE WHEN te.event_name = 'rfq_submit'    THEN 1 ELSE 0 END) AS rfq_events,
            COUNT(DISTINCT r.id)                                          AS rfq_count,
            ROUND(AVG(v.intent_score)::numeric, 1)                       AS avg_intent_score
        FROM tracking_events te
        LEFT JOIN visitors v ON v.visitor_id = te.visitor_id
        LEFT JOIN rfq_requests r ON r.visitor_id = te.visitor_id
        LEFT JOIN products p ON p.id = te.page_id AND te.page_type = 'product'
        LEFT JOIN applications app ON app.id = te.page_id AND te.page_type = 'application'
        LEFT JOIN pages pg ON pg.id = te.page_id AND te.page_type = 'page'
        WHERE te.page_id IS NOT NULL
          AND te.timestamp >= NOW() - make_interval(days => :days)
          {page_type_filter}
        GROUP BY te.page_id, te.page_type, p.product_name, app.application_name, pg.title
        ORDER BY page_views DESC
        LIMIT :limit
    """)

    params: dict[str, Any] = {"days": days, "limit": limit}
    if page_type:
        params["page_type"] = page_type

    result = await session.execute(sql, params)
    rows = result.mappings().all()

    # Summary totals
    totals_sql = text(f"""
        SELECT
            COUNT(*)                  AS total_events,
            COUNT(DISTINCT te.page_id) AS total_pages,
            COUNT(DISTINCT te.visitor_id) AS total_unique_visitors
        FROM tracking_events te
        WHERE te.page_id IS NOT NULL
          AND te.timestamp >= NOW() - make_interval(days => :days)
          {page_type_filter}
    """)
    totals_row = (await session.execute(totals_sql, params)).mappings().one()

    return {
        "period_days": days,
        "generated_at": _iso(datetime.now(timezone.utc)),
        "summary": dict(totals_row),
        "pages": [dict(r) for r in rows],
    }


# ── 2.5.2  Product-level analytics ────────────────────────────────────────────

@router.get("/products")
async def product_analytics(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Per-product: page views, unique visitors, spec downloads, RFQ count, avg intent score."""
    sql = text("""
        SELECT
            te.page_id::text                                 AS product_id,
            p.product_name,
            p.model_number,
            c.slug                                           AS category_slug,
            COUNT(*)                                         AS page_views,
            COUNT(DISTINCT te.visitor_id)                    AS unique_visitors,
            SUM(CASE WHEN te.event_name = 'spec_download' THEN 1 ELSE 0 END) AS spec_downloads,
            COUNT(DISTINCT r.id)                             AS rfq_count,
            ROUND(AVG(v.intent_score)::numeric, 1)           AS avg_intent_score
        FROM tracking_events te
        JOIN products p ON p.id = te.page_id
        LEFT JOIN product_categories c ON c.id = p.category_id
        LEFT JOIN visitors v ON v.visitor_id = te.visitor_id
        LEFT JOIN rfq_requests r ON r.visitor_id = te.visitor_id
        WHERE te.page_type = 'product'
          AND te.timestamp >= NOW() - make_interval(days => :days)
        GROUP BY te.page_id, p.product_name, p.model_number, c.slug
        ORDER BY page_views DESC
        LIMIT :limit
    """)
    result = await session.execute(sql, {"days": days, "limit": limit})
    rows = result.mappings().all()

    return {
        "period_days": days,
        "generated_at": _iso(datetime.now(timezone.utc)),
        "products": [dict(r) for r in rows],
    }


# ── 2.5.2  Application-level analytics ────────────────────────────────────────

@router.get("/applications")
async def application_analytics(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Per-application: page views, unique visitors, RFQ count, avg intent score."""
    sql = text("""
        SELECT
            te.page_id::text                                 AS application_id,
            app.application_name,
            app.industry,
            COUNT(*)                                         AS page_views,
            COUNT(DISTINCT te.visitor_id)                    AS unique_visitors,
            COUNT(DISTINCT r.id)                             AS rfq_count,
            ROUND(AVG(v.intent_score)::numeric, 1)           AS avg_intent_score
        FROM tracking_events te
        JOIN applications app ON app.id = te.page_id
        LEFT JOIN visitors v ON v.visitor_id = te.visitor_id
        LEFT JOIN rfq_requests r ON r.visitor_id = te.visitor_id
        WHERE te.page_type = 'application'
          AND te.timestamp >= NOW() - make_interval(days => :days)
        GROUP BY te.page_id, app.application_name, app.industry
        ORDER BY page_views DESC
        LIMIT :limit
    """)
    result = await session.execute(sql, {"days": days, "limit": limit})
    rows = result.mappings().all()

    return {
        "period_days": days,
        "generated_at": _iso(datetime.now(timezone.utc)),
        "applications": [dict(r) for r in rows],
    }


# ── 2.5.3  Strategy map performance overlay ───────────────────────────────────

@router.get("/strategy-map")
async def strategy_map_analytics(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Per-strategy-page overlay: page views + RFQ count + performance tier.
    Performance tier:
      - 'strong'   : rfq_count > 0 AND page_views >= 10
      - 'engaged'  : page_views >= 10 (traffic but no RFQ)
      - 'weak'     : page_views > 0 AND page_views < 10
      - 'dark'     : page_views = 0 (no traffic)
    """
    # Fetch all strategy entries with linked page metrics
    sql = text("""
        WITH page_metrics AS (
            SELECT
                te.page_id                                       AS page_id,
                COUNT(*)                                         AS page_views,
                COUNT(DISTINCT te.visitor_id)                    AS unique_visitors,
                COUNT(DISTINCT r.id)                             AS rfq_count,
                SUM(CASE WHEN te.event_name = 'spec_download' THEN 1 ELSE 0 END) AS spec_downloads,
                ROUND(AVG(v.intent_score)::numeric, 1)           AS avg_intent_score
            FROM tracking_events te
            LEFT JOIN visitors v ON v.visitor_id = te.visitor_id
            LEFT JOIN rfq_requests r ON r.visitor_id = te.visitor_id
            WHERE te.page_id IS NOT NULL
              AND te.timestamp >= NOW() - make_interval(days => :days)
            GROUP BY te.page_id
        )
        SELECT
            cs.id::text                                          AS strategy_id,
            cs.funnel_stage,
            cs.status,
            cs.buying_role,
            cs.target_keyword,
            cs.primary_message,
            p.id::text                                           AS page_id,
            p.title                                              AS page_title,
            p.slug                                               AS page_slug,
            COALESCE(pm.page_views,       0)                    AS page_views,
            COALESCE(pm.unique_visitors,  0)                    AS unique_visitors,
            COALESCE(pm.rfq_count,        0)                    AS rfq_count,
            COALESCE(pm.spec_downloads,   0)                    AS spec_downloads,
            COALESCE(pm.avg_intent_score, 0)                    AS avg_intent_score,
            CASE
                WHEN COALESCE(pm.rfq_count, 0) > 0 AND COALESCE(pm.page_views, 0) >= 10 THEN 'strong'
                WHEN COALESCE(pm.page_views, 0) >= 10 THEN 'engaged'
                WHEN COALESCE(pm.page_views, 0) > 0  THEN 'weak'
                ELSE 'dark'
            END                                                  AS performance_tier
        FROM content_strategies cs
        LEFT JOIN pages p ON p.id = cs.page_id
        LEFT JOIN page_metrics pm ON pm.page_id = cs.page_id
        ORDER BY
            CASE cs.funnel_stage
                WHEN 'awareness' THEN 1
                WHEN 'consideration' THEN 2
                WHEN 'decision' THEN 3
                ELSE 4
            END,
            COALESCE(pm.page_views, 0) DESC
    """)

    result = await session.execute(sql, {"days": days})
    rows = result.mappings().all()

    # Aggregate tier counts
    tiers: dict[str, int] = {"strong": 0, "engaged": 0, "weak": 0, "dark": 0}
    for row in rows:
        tier = row.get("performance_tier", "dark")
        if tier in tiers:
            tiers[tier] += 1

    return {
        "period_days": days,
        "generated_at": _iso(datetime.now(timezone.utc)),
        "tier_summary": tiers,
        "strategies": [dict(r) for r in rows],
    }
