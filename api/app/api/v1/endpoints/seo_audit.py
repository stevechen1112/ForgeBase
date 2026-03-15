"""
2.3.4 SEO 診斷儀表板 API

GET /content/seo-audit/summary     — metrics overview
GET /content/seo-audit/pages       — per-page performance
GET /content/seo-audit/opportunities — ranking 6-20 high-potential pages
GET /content/seo-audit/cannibalization — keyword cannibalization detection
GET /content/seo-audit/on-page     — on-page SEO issues (missing meta, thin content, etc.)
"""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models.page import Page
from app.models.user import User
from app.services.gsc_service import (
    detect_keyword_cannibalization,
    get_keyword_opportunities,
    get_page_performance,
)

router = APIRouter(prefix="/seo-audit", tags=["SEO Audit"])


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
