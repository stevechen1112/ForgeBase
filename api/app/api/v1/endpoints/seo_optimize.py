"""
2.3.5 內容優化建議引擎

POST /content/seo-audit/optimize   — AI generates actionable improvement suggestions
                                     given a page's on-page audit result
"""
from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.db.session import get_session
from app.models.page import Page
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/seo-audit", tags=["SEO Audit"])


# ── AI helper ────────────────────────────────────────────────────────────────

async def _call_openai(prompt: str) -> str:
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model=settings.AI_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert B2B technical SEO consultant specialising in "
                        "industrial manufacturing websites. Respond in Traditional Chinese (繁體中文). "
                        "Be concise, actionable, and specific. Provide improvements as a "
                        "JSON object with keys: seo_title, meta_description, content_suggestions, "
                        "structured_data_recommendation, priority (high|medium|low), "
                        "estimated_impact (brief sentence)."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or "{}"
    except Exception as exc:  # noqa: BLE001
        logger.error("SEO optimization AI call failed: %s", exc)
        raise RuntimeError(f"AI service error: {exc}") from exc


# ── Schema ────────────────────────────────────────────────────────────────────

class OptimizeRequest(BaseModel):
    page_id: uuid.UUID
    # Optional GSC context (clicks, impressions, avg_position) from frontend
    gsc_clicks: int = 0
    gsc_impressions: int = 0
    gsc_avg_position: float = 0.0
    gsc_ctr: float = 0.0


# ── On-page audit (inline, same logic as seo_audit.py) ───────────────────────

def _audit_issues(page: Page) -> list[str]:
    issues: list[str] = []
    title = page.seo_title or page.title or ""
    if not title:
        issues.append("缺少 SEO 標題")
    elif len(title) < 20:
        issues.append(f"SEO 標題過短（{len(title)} 字元）")
    elif len(title) > 65:
        issues.append(f"SEO 標題過長（{len(title)} 字元）")
    desc = page.seo_description or ""
    if not desc:
        issues.append("缺少 Meta Description")
    elif len(desc) < 50:
        issues.append(f"Meta Description 過短（{len(desc)} 字元）")
    elif len(desc) > 165:
        issues.append(f"Meta Description 過長（{len(desc)} 字元）")
    if not page.structured_data:
        issues.append("缺少 JSON-LD Structured Data")
    if not page.canonical_url:
        issues.append("未設定 Canonical URL")
    if page.noindex:
        issues.append("頁面設定為 noindex")
    body_len = len(page.body or "")
    if body_len < 300 and page.page_type not in ("home", "contact"):
        issues.append(f"內容量偏少（{body_len} 字）")
    return issues


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/optimize")
async def generate_seo_suggestions(
    body: OptimizeRequest,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    """
    Given a page ID (+ optional GSC data), return AI-generated SEO improvement suggestions.
    """
    page = await db.get(Page, body.page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    issues = _audit_issues(page)

    # Build context prompt
    body_preview = (page.body or "")[:800]  # first 800 chars to keep token count down
    gsc_context = ""
    if body.gsc_impressions > 0:
        gsc_context = (
            f"\nGoogle Search Console data (last 28 days):\n"
            f"  clicks={body.gsc_clicks}, impressions={body.gsc_impressions}, "
            f"  avg_position={body.gsc_avg_position:.1f}, CTR={body.gsc_ctr:.2f}%"
        )

    prompt = f"""Analyse this industrial B2B page and provide specific SEO improvements.

Page details:
  - slug: {page.slug}
  - page_type: {page.page_type}
  - locale: {page.locale}
  - title: {page.title!r}
  - current_seo_title: {page.seo_title!r}
  - current_meta_description: {page.seo_description!r}
  - body_length: {len(page.body or '')} chars
  - body_preview: {body_preview!r}
  - has_structured_data: {bool(page.structured_data)}
  - has_canonical: {bool(page.canonical_url)}
  - noindex: {page.noindex}
{gsc_context}

Detected issues:
{chr(10).join(f'  - {i}' for i in issues) if issues else '  (none detected)'}

Return a JSON object with these keys:
  seo_title (string, optimal 40-60 chars),
  meta_description (string, optimal 120-155 chars),
  content_suggestions (array of strings, max 5 actionable items),
  structured_data_recommendation (string — which schema type to use and why),
  priority ("high"|"medium"|"low"),
  estimated_impact (one-sentence description of expected SEO benefit)
"""

    ai_response_raw = await _call_openai(prompt)

    try:
        suggestions = json.loads(ai_response_raw)
    except json.JSONDecodeError:
        suggestions = {"raw": ai_response_raw}

    return {
        "page_id": str(page.id),
        "slug": page.slug,
        "title": page.title,
        "on_page_issues": issues,
        "suggestions": suggestions,
    }
