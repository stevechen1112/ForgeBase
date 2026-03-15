"""
2.3.4 SEO 診斷儀表板 API

GET /content/seo-audit/summary     — metrics overview
GET /content/seo-audit/pages       — per-page performance
GET /content/seo-audit/opportunities — ranking 6-20 high-potential pages
GET /content/seo-audit/cannibalization — keyword cannibalization detection
GET /content/seo-audit/on-page     — on-page SEO issues (missing meta, thin content, etc.)
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models.application import Application
from app.models.page import Page
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.user import User
from app.services.gsc_service import (
    detect_keyword_cannibalization,
    get_keyword_opportunities,
    get_page_performance,
)
from app.services.seo_workbench import audit_entity_payload, build_entity_path

router = APIRouter(prefix="/seo-audit", tags=["SEO Audit"])


class EvaluateSEORequest(BaseModel):
    entity_type: str
    data: dict[str, Any]


def _serialize_entity(entity_type: str, item: Any) -> dict[str, Any]:
    if entity_type == "product":
        category_slug = getattr(getattr(item, "category", None), "slug", None)
        return {
            "id": str(item.id),
            "product_name": item.product_name,
            "slug": item.slug,
            "model_number": item.model_number,
            "short_description": item.short_description,
            "full_description": item.full_description,
            "specifications": item.specifications,
            "seo_title": item.seo_title,
            "seo_description": item.seo_description,
            "locale": item.locale,
            "status": item.status,
            "category_slug": category_slug,
        }
    if entity_type == "category":
        return {
            "id": str(item.id),
            "category_name": item.category_name,
            "slug": item.slug,
            "description": item.description,
            "seo_title": item.seo_title,
            "seo_description": item.seo_description,
            "locale": item.locale,
            "status": item.status,
        }
    if entity_type == "application":
        return {
            "id": str(item.id),
            "application_name": item.application_name,
            "slug": item.slug,
            "industry": item.industry,
            "description": item.description,
            "challenge": item.challenge,
            "solution": item.solution,
            "seo_title": item.seo_title,
            "seo_description": item.seo_description,
            "locale": item.locale,
            "status": item.status,
        }
    return {
        "id": str(item.id),
        "title": item.title,
        "slug": item.slug,
        "subtitle": item.subtitle,
        "body": item.body,
        "seo_title": item.seo_title,
        "seo_description": item.seo_description,
        "canonical_url": item.canonical_url,
        "locale": item.locale,
        "status": item.status,
    }


def _task(title: str, description: str, count: int, impact: str, entity_types: list[str]) -> dict[str, Any]:
    return {
        "id": title.lower().replace(" ", "-"),
        "title": title,
        "description": description,
        "count": count,
        "impact": impact,
        "entity_types": entity_types,
    }


def _top_issue(audit: dict[str, Any]) -> str:
    for check in audit.get("checks", []):
        if check["status"] != "good":
            return check["message"]
    return "目前沒有高優先問題。"


@router.post("/evaluate")
async def evaluate_entity_seo(
    body: EvaluateSEORequest,
    _current_user: User = Depends(get_current_user),
):
    entity_type = body.entity_type.strip().lower()
    if entity_type not in {"page", "product", "category", "application"}:
        return {"detail": "Unsupported entity_type"}
    return audit_entity_payload(entity_type, body.data)


@router.get("/health")
async def seo_health(
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    pages = (await db.execute(select(Page).where(Page.status == "published"))).scalars().all()
    products = (await db.execute(select(Product).where(Product.status == "published"))).scalars().all()
    categories = (await db.execute(select(ProductCategory).where(ProductCategory.status == "published"))).scalars().all()
    applications = (await db.execute(select(Application).where(Application.status == "published"))).scalars().all()

    audits: list[dict[str, Any]] = []
    for item in pages:
        data = _serialize_entity("page", item)
        audit = audit_entity_payload("page", data)
        audits.append({
            "id": str(item.id),
            "entity_type": "page",
            "name": audit["entity_name"],
            "score": audit["score"],
            "status": audit["status"],
            "url": audit["search_preview"]["url"],
            "focus_keywords": audit["focus_keywords"],
            "top_issue": _top_issue(audit),
        })
    for item in products:
        data = _serialize_entity("product", item)
        audit = audit_entity_payload("product", data)
        audits.append({
            "id": str(item.id),
            "entity_type": "product",
            "name": audit["entity_name"],
            "score": audit["score"],
            "status": audit["status"],
            "url": audit["search_preview"]["url"],
            "focus_keywords": audit["focus_keywords"],
            "top_issue": _top_issue(audit),
        })
    for item in categories:
        data = _serialize_entity("category", item)
        audit = audit_entity_payload("category", data)
        audits.append({
            "id": str(item.id),
            "entity_type": "category",
            "name": audit["entity_name"],
            "score": audit["score"],
            "status": audit["status"],
            "url": audit["search_preview"]["url"],
            "focus_keywords": audit["focus_keywords"],
            "top_issue": _top_issue(audit),
        })
    for item in applications:
        data = _serialize_entity("application", item)
        audit = audit_entity_payload("application", data)
        audits.append({
            "id": str(item.id),
            "entity_type": "application",
            "name": audit["entity_name"],
            "score": audit["score"],
            "status": audit["status"],
            "url": audit["search_preview"]["url"],
            "focus_keywords": audit["focus_keywords"],
            "top_issue": _top_issue(audit),
        })

    total = len(audits)
    healthy = sum(1 for audit in audits if audit["status"] == "healthy")
    needs_work = sum(1 for audit in audits if audit["status"] == "needs-work")
    critical = sum(1 for audit in audits if audit["status"] == "critical")
    avg_score = round(sum(audit["score"] for audit in audits) / total, 1) if total else 0

    missing_descriptions = sum(1 for item in [*pages, *products, *categories, *applications] if not getattr(item, "seo_description", None))
    missing_titles = sum(1 for item in [*pages, *products, *categories, *applications] if not getattr(item, "seo_title", None))
    thin_content = 0
    for item in pages:
        if len(item.body or "") < 180:
            thin_content += 1
    for item in products:
        if len((item.short_description or "") + (item.full_description or "")) < 180:
            thin_content += 1
    for item in categories:
        if len(item.description or "") < 180:
            thin_content += 1
    for item in applications:
        if len((item.description or "") + (item.challenge or "") + (item.solution or "")) < 180:
            thin_content += 1

    tasks = [
        _task("補上搜尋摘要", "先補高優先頁面的搜尋摘要，提升搜尋結果點擊率。", missing_descriptions, "high", ["page", "product", "category", "application"]),
        _task("優化 Google 標題", "把過短或未設定的標題補齊，讓搜尋主題更清楚。", missing_titles, "high", ["page", "product", "category", "application"]),
        _task("補強內容深度", "增加規格、應用情境與 FAQ，避免頁面只有很薄的內容。", thin_content, "medium", ["page", "product", "category", "application"]),
    ]
    tasks = [task for task in tasks if task["count"] > 0]
    tasks.sort(key=lambda task: (-task["count"], task["title"]))

    audits.sort(key=lambda audit: (audit["score"], audit["entity_type"], audit["name"]))
    return {
        "summary": {
            "total_entities": total,
            "healthy": healthy,
            "needs_work": needs_work,
            "critical": critical,
            "avg_score": avg_score,
            "published_pages": len(pages),
            "published_products": len(products),
            "published_categories": len(categories),
            "published_applications": len(applications),
        },
        "tasks": tasks[:3],
        "entities": audits[:20],
    }


@router.get("/links")
async def seo_link_opportunities(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    suggestions: list[dict[str, Any]] = []

    category_product_rows = (await db.execute(
        text(
            """
            SELECT c.category_name, c.slug AS category_slug, p.product_name, p.slug AS product_slug, p.model_number
            FROM product_categories c
            JOIN products p ON p.category_id = c.id
            WHERE c.status = 'published' AND p.status = 'published'
            ORDER BY c.sort_order, p.display_priority DESC, p.product_name
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )).mappings().all()

    for row in category_product_rows:
        suggestions.append({
            "source_type": "category",
            "source_name": row["category_name"],
            "source_url": build_entity_path("category", {"slug": row["category_slug"]}),
            "target_type": "product",
            "target_name": f"{row['model_number']} {row['product_name']}",
            "target_url": build_entity_path("product", {"slug": row["product_slug"], "category_slug": row["category_slug"]}),
            "reason": "分類頁與產品頁主題高度相關，加入內鏈可幫助搜尋引擎與訪客向下探索。",
            "confidence": "high",
        })

    application_product_rows = (await db.execute(
        text(
            """
            SELECT a.application_name, a.slug AS application_slug, p.product_name, p.slug AS product_slug, p.model_number, c.slug AS category_slug
            FROM applications a
            JOIN product_application_links l ON l.application_id = a.id
            JOIN products p ON p.id = l.product_id
            LEFT JOIN product_categories c ON c.id = p.category_id
            WHERE a.status = 'published' AND p.status = 'published'
            ORDER BY a.sort_order, p.display_priority DESC, p.product_name
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )).mappings().all()

    for row in application_product_rows:
        suggestions.append({
            "source_type": "application",
            "source_name": row["application_name"],
            "source_url": build_entity_path("application", {"slug": row["application_slug"]}),
            "target_type": "product",
            "target_name": f"{row['model_number']} {row['product_name']}",
            "target_url": build_entity_path("product", {"slug": row["product_slug"], "category_slug": row["category_slug"]}),
            "reason": "應用場景頁已有相關產品資料，補上連結可縮短訪客前往詢價的路徑。",
            "confidence": "high",
        })

    return {
        "count": min(len(suggestions), limit),
        "suggestions": suggestions[:limit],
    }


@router.get("/revenue")
async def seo_revenue_insights(
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    query = text(
        """
        SELECT
            te.page_id::text AS page_id,
            te.page_type AS page_type,
            COALESCE(p.product_name, a.application_name, pg.title, te.page_url, 'Unknown') AS page_name,
            COUNT(*) AS page_views,
            COUNT(DISTINCT te.visitor_id) AS unique_visitors,
            COUNT(DISTINCT r.id) AS rfq_count,
            ROUND(AVG(COALESCE(v.intent_score, 0))::numeric, 1) AS avg_intent_score
        FROM tracking_events te
        LEFT JOIN visitors v ON v.visitor_id = te.visitor_id
        LEFT JOIN rfq_requests r ON r.visitor_id = te.visitor_id
        LEFT JOIN products p ON p.id = te.page_id AND te.page_type = 'product'
        LEFT JOIN applications a ON a.id = te.page_id AND te.page_type = 'application'
        LEFT JOIN pages pg ON pg.id = te.page_id AND te.page_type = 'page'
        WHERE te.timestamp >= NOW() - make_interval(days => :days)
          AND te.page_id IS NOT NULL
          AND te.page_type IN ('product', 'application', 'page')
        GROUP BY te.page_id, te.page_type, p.product_name, a.application_name, pg.title, te.page_url
        HAVING COUNT(*) > 0
        ORDER BY rfq_count DESC, page_views DESC
        """
    )
    rows = (await db.execute(query, {"days": days})).mappings().all()

    enriched: list[dict[str, Any]] = []
    for row in rows:
        page_views = int(row["page_views"] or 0)
        rfq_count = int(row["rfq_count"] or 0)
        conversion_rate = round((rfq_count / page_views) * 100, 2) if page_views else 0.0
        enriched.append({
            **dict(row),
            "conversion_rate": conversion_rate,
        })

    top_converters = sorted(
        [row for row in enriched if row["rfq_count"] > 0],
        key=lambda row: (-row["conversion_rate"], -row["rfq_count"], -row["page_views"]),
    )[:8]
    underperformers = sorted(
        [row for row in enriched if row["page_views"] >= 20 and row["rfq_count"] == 0],
        key=lambda row: (-row["page_views"], -row["avg_intent_score"]),
    )[:8]

    total_views = sum(row["page_views"] for row in enriched)
    total_rfq = sum(row["rfq_count"] for row in enriched)
    pages_with_rfq = sum(1 for row in enriched if row["rfq_count"] > 0)

    return {
        "summary": {
            "total_views": total_views,
            "total_rfq": total_rfq,
            "pages_with_rfq": pages_with_rfq,
            "avg_conversion_rate": round((total_rfq / total_views) * 100, 2) if total_views else 0.0,
        },
        "top_converters": top_converters,
        "underperformers": underperformers,
    }


# ── On-Page audit helpers ─────────────────────────────────────────────────────

def _audit_page(page: Page) -> dict:
    issues: list[str] = []

    # Meta title
    title = page.seo_title or page.title or ""
    if not title:
        issues.append("缺少 SEO 標題")
    elif len(title) < 20:
        issues.append(f"SEO 標題過短（{len(title)} 字元，建議 30-60）")
    elif len(title) > 65:
        issues.append(f"SEO 標題過長（{len(title)} 字元，上限 60）")

    # Meta description
    desc = page.seo_description or ""
    if not desc:
        issues.append("缺少 Meta Description")
    elif len(desc) < 50:
        issues.append(f"Meta Description 過短（{len(desc)} 字元，建議 120-160）")
    elif len(desc) > 165:
        issues.append(f"Meta Description 過長（{len(desc)} 字元，上限 160）")

    # Structured data
    if not page.structured_data:
        issues.append("缺少 JSON-LD Structured Data")

    # Canonical
    if not page.canonical_url:
        issues.append("未設定 Canonical URL")

    # Noindex
    if page.noindex:
        issues.append("⚠️ 頁面設定為 noindex（不會被索引）")

    # Thin content (body length)
    body_len = len(page.body or "")
    if body_len < 300 and page.page_type not in ("home", "contact"):
        issues.append(f"內容量偏少（{body_len} 字，建議 >300）")

    severity = "ok" if not issues else ("critical" if len(issues) >= 3 else "warning")

    return {
        "id": str(page.id),
        "slug": page.slug,
        "title": page.title,
        "page_type": page.page_type,
        "locale": page.locale,
        "status": page.status,
        "seo_title": page.seo_title,
        "seo_title_length": len(title),
        "seo_description": desc,
        "seo_description_length": len(desc),
        "has_structured_data": bool(page.structured_data),
        "has_canonical": bool(page.canonical_url),
        "noindex": page.noindex,
        "body_length": body_len,
        "issues": issues,
        "severity": severity,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/summary")
async def seo_audit_summary(
    days: int = Query(28, ge=7, le=90),
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    """
    Overview metrics:
    - On-page: pages with issues, structured data coverage
    - GSC: top-level clicks/impressions/avg position
    - Quick counts
    """
    pages = (await db.execute(
        select(Page).where(Page.status == "published")
    )).scalars().all()

    audits = [_audit_page(p) for p in pages]
    total = len(audits)
    ok_count = sum(1 for a in audits if a["severity"] == "ok")
    warning_count = sum(1 for a in audits if a["severity"] == "warning")
    critical_count = sum(1 for a in audits if a["severity"] == "critical")
    no_meta_desc = sum(1 for a in audits if not a["seo_description"])
    no_structured_data = sum(1 for a in audits if not a["has_structured_data"])
    has_canonical = sum(1 for a in audits if a["has_canonical"])

    # GSC overview
    gsc_rows = await get_page_performance(days=days)
    total_clicks = sum(r["clicks"] for r in gsc_rows)
    total_impressions = sum(r["impressions"] for r in gsc_rows)
    avg_ctr = round(total_clicks / total_impressions * 100, 2) if total_impressions else 0
    avg_position = (
        round(sum(r["avg_position"] for r in gsc_rows) / len(gsc_rows), 1)
        if gsc_rows else None
    )

    opportunities = [r for r in gsc_rows if 6 <= r["avg_position"] <= 20 and r["impressions"] >= 100]

    return {
        "on_page": {
            "total_published_pages": total,
            "ok": ok_count,
            "warning": warning_count,
            "critical": critical_count,
            "no_meta_description": no_meta_desc,
            "no_structured_data": no_structured_data,
            "has_canonical": has_canonical,
            "structured_data_coverage_pct": round(
                (total - no_structured_data) / total * 100, 1
            ) if total else 0,
        },
        "gsc": {
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "avg_ctr_pct": avg_ctr,
            "avg_position": avg_position,
            "opportunity_pages": len(opportunities),
            "days": days,
            "data_available": bool(gsc_rows),
        },
    }


@router.get("/pages")
async def seo_audit_pages(
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
    severity: Optional[str] = Query(None, description="Filter by severity: ok|warning|critical"),
    locale: Optional[str] = Query(None),
):
    """All published pages with on-page SEO audit results."""
    stmt = select(Page).where(Page.status == "published")
    if locale:
        stmt = stmt.where(Page.locale == locale)
    pages = (await db.execute(stmt)).scalars().all()

    audits = [_audit_page(p) for p in pages]
    if severity:
        audits = [a for a in audits if a["severity"] == severity]

    # Sort: critical first
    order = {"critical": 0, "warning": 1, "ok": 2}
    audits.sort(key=lambda a: order.get(a["severity"], 9))
    return audits


@router.get("/opportunities")
async def seo_opportunities(
    days: int = Query(28, ge=7, le=90),
    _current_user: User = Depends(get_current_user),
):
    """
    Pages ranking position 6-20 with >100 impressions — quick-win opportunities.
    Sorted by impressions desc.
    """
    rows = await get_keyword_opportunities(days=days)
    return {"days": days, "count": len(rows), "pages": rows}


@router.get("/cannibalization")
async def seo_cannibalization(
    days: int = Query(28, ge=7, le=90),
    _current_user: User = Depends(get_current_user),
):
    """
    Detect keyword cannibalization: same query ranking for multiple pages.
    Returns top 50 cannibalized queries sorted by affected page count.
    """
    results = await detect_keyword_cannibalization(days=days)
    return {"days": days, "count": len(results), "queries": results}


@router.get("/on-page")
async def seo_on_page_audit(
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
    severity: Optional[str] = Query(None),
    page_type: Optional[str] = Query(None),
    locale: Optional[str] = Query(None),
):
    """Detailed on-page SEO audit with issue list per page."""
    stmt = select(Page)
    if locale:
        stmt = stmt.where(Page.locale == locale)
    if page_type:
        stmt = stmt.where(Page.page_type == page_type)
    pages = (await db.execute(stmt)).scalars().all()

    audits = [_audit_page(p) for p in pages]
    if severity:
        audits = [a for a in audits if a["severity"] == severity]

    order = {"critical": 0, "warning": 1, "ok": 2}
    audits.sort(key=lambda a: order.get(a["severity"], 9))
    return {
        "total": len(audits),
        "pages": audits,
    }
