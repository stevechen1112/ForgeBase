"""
2.5.x Analytics API
===================
GET /tracking/analytics/pages          — 2.5.1 Page-level performance
GET /tracking/analytics/products       — 2.5.2 Product-level performance
GET /tracking/analytics/applications   — 2.5.2 Application-level performance
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import RequireFeature, get_current_user
from app.db.session import get_session
from app.models.user import User

router = APIRouter(prefix="/tracking/analytics", tags=["Analytics"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _build_filter_sql(
    tenant_id: uuid.UUID | None = None,
    page_type: str | None = None,
    tenant_column: str = "te.tenant_id",
) -> tuple[str, dict[str, Any]]:
    clauses: list[str] = ["AND te.is_test_data = FALSE"]
    params: dict[str, Any] = {}

    if page_type:
        clauses.append("AND te.page_type = :page_type")
        params["page_type"] = page_type
    if tenant_id:
        clauses.append("AND te.tenant_id = :tenant_id")
        params["tenant_id"] = str(tenant_id)

    if not clauses:
        return "", params

    return "\n          " + "\n          ".join(clauses), params


def _build_visitor_filter_sql(tenant_id: uuid.UUID | None = None) -> tuple[str, dict[str, Any]]:
    if not tenant_id:
        return "\n          AND is_test_data = FALSE", {}
    return "\n          AND is_test_data = FALSE\n          AND tenant_id = :tenant_id", {"tenant_id": str(tenant_id)}


# ── 2.5.1  Page-level analytics ───────────────────────────────────────────────

@router.get("/pages")
async def page_analytics(
    days: int = Query(30, ge=1, le=365, description="Look-back window in days"),
    page_type: str | None = Query(None, description="Filter by page_type (product/application/page/category)"),
    limit: int = Query(50, ge=1, le=200),
    _feature: User = Depends(RequireFeature("full_tracking")),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Per-page aggregated metrics over the last N days.
    Joins first-party tracking events with RFQs for direct website performance.
    """
    filter_sql, filter_params = _build_filter_sql(_.tenant_id, page_type)
    sql = text(
        """
        SELECT
            te.page_id::text                                              AS page_id,
            te.page_type                                                  AS page_type,
            -- try to surface a label from products / applications tables
            COALESCE(p.product_name, app.application_name, pg.title, te.page_type) AS page_name,
            COUNT(*)                                                      AS page_views,
            COUNT(DISTINCT te.visitor_id)                                 AS unique_visitors,
            SUM(CASE WHEN te.event_name = 'spec_download' THEN 1 ELSE 0 END) AS spec_downloads,
            SUM(CASE WHEN te.event_name = 'rfq_submit'    THEN 1 ELSE 0 END) AS rfq_events,
            COUNT(DISTINCT r.id)                                          AS rfq_count
        FROM tracking_events te
        LEFT JOIN rfq_requests r ON r.visitor_id = te.visitor_id AND r.is_test_data = FALSE
        LEFT JOIN products p ON p.id = te.page_id AND te.page_type = 'product'
        LEFT JOIN applications app ON app.id = te.page_id AND te.page_type = 'application'
        LEFT JOIN pages pg ON pg.id = te.page_id AND te.page_type = 'page'
        WHERE te.page_id IS NOT NULL
          AND te.timestamp >= NOW() - make_interval(days => :days)
                    __FILTERS__
        GROUP BY te.page_id, te.page_type, p.product_name, app.application_name, pg.title
        ORDER BY page_views DESC
        LIMIT :limit
                """.replace("__FILTERS__", filter_sql)
        )

    params: dict[str, Any] = {"days": days, "limit": limit} | filter_params

    result = await session.exec(sql, params=params)
    rows = result.mappings().all()

    # Summary totals
    totals_sql = text("""
        SELECT
            COUNT(*)                  AS total_events,
            COUNT(DISTINCT te.page_id) AS total_pages,
            COUNT(DISTINCT te.visitor_id) AS total_unique_visitors
        FROM tracking_events te
        WHERE te.page_id IS NOT NULL
          AND te.timestamp >= NOW() - make_interval(days => :days)
          """ + filter_sql + """
    """)
    totals_row = (await session.exec(totals_sql, params=params)).mappings().one()

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
    _feature: User = Depends(RequireFeature("full_tracking")),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Per-product: page views, unique visitors, spec downloads and RFQ count."""
    filter_sql, filter_params = _build_filter_sql(_.tenant_id)
    sql = text(
        """
        SELECT
            te.page_id::text                                 AS product_id,
            p.product_name,
            p.model_number,
            c.slug                                           AS category_slug,
            COUNT(*)                                         AS page_views,
            COUNT(DISTINCT te.visitor_id)                    AS unique_visitors,
            SUM(CASE WHEN te.event_name = 'spec_download' THEN 1 ELSE 0 END) AS spec_downloads,
            COUNT(DISTINCT r.id)                             AS rfq_count
        FROM tracking_events te
        JOIN products p ON p.id = te.page_id
        LEFT JOIN product_categories c ON c.id = p.category_id
        LEFT JOIN rfq_requests r ON r.visitor_id = te.visitor_id
        WHERE te.page_type = 'product'
          AND te.timestamp >= NOW() - make_interval(days => :days)
          __FILTERS__
        GROUP BY te.page_id, p.product_name, p.model_number, c.slug
        ORDER BY page_views DESC
        LIMIT :limit
        """.replace("__FILTERS__", filter_sql)
    )
    params: dict[str, Any] = {"days": days, "limit": limit} | filter_params
    result = await session.exec(sql, params=params)
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
    _feature: User = Depends(RequireFeature("full_tracking")),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Per-application: page views, unique visitors and RFQ count."""
    filter_sql, filter_params = _build_filter_sql(_.tenant_id)
    sql = text(
        """
        SELECT
            te.page_id::text                                 AS application_id,
            app.application_name,
            app.industry,
            COUNT(*)                                         AS page_views,
            COUNT(DISTINCT te.visitor_id)                    AS unique_visitors,
            COUNT(DISTINCT r.id)                             AS rfq_count
        FROM tracking_events te
        JOIN applications app ON app.id = te.page_id
        LEFT JOIN rfq_requests r ON r.visitor_id = te.visitor_id
        WHERE te.page_type = 'application'
          AND te.timestamp >= NOW() - make_interval(days => :days)
          __FILTERS__
        GROUP BY te.page_id, app.application_name, app.industry
        ORDER BY page_views DESC
        LIMIT :limit
        """.replace("__FILTERS__", filter_sql)
    )
    result = await session.exec(
        sql, params={"days": days, "limit": limit} | filter_params
    )
    rows = result.mappings().all()

    return {
        "period_days": days,
        "generated_at": _iso(datetime.now(timezone.utc)),
        "applications": [dict(r) for r in rows],
    }
