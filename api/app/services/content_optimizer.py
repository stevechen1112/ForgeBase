"""
AI-powered Content Performance Optimizer  (3.1.3)

Analyzes page performance data (real traffic + intent signals) and
generates holistic content improvement suggestions that go beyond
SEO keyword optimization.

This differs from seo_optimize.py (which relies on GSC keyword gaps).
This service combines:
- Actual user behavior (pageviews, spec_downloads, rfq conversions)
- Intent signal patterns
- Content quality assessment
"""
import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

OPTIMIZER_SYSTEM = """You are an expert B2B industrial content strategist.
You analyze page performance data and actual user behavior to suggest content improvements.
Focus on improving visitor engagement, intent capture, and conversion to RFQ.
Output valid JSON only. Be specific and actionable."""


async def optimize_content(
    page_info: dict[str, Any],
    analytics: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate AI content improvement suggestions based on real performance data.

    Args:
        page_info: dict with keys: page_type, title, seo_title, description,
                   full_description (optional), slug, entity_name
        analytics: dict with keys: page_views, unique_visitors, spec_downloads,
                   rfq_count, avg_intent_score, period_days

    Returns dict with:
        overall_score, issues, suggestions, priority_actions, revised_title,
        revised_description, content_gaps
    """
    views = analytics.get("page_views", 0)
    visitors = analytics.get("unique_visitors", 0)
    downloads = analytics.get("spec_downloads", 0)
    rfqs = analytics.get("rfq_count", 0)
    avg_intent = analytics.get("avg_intent_score", 0)
    days = analytics.get("period_days", 30)

    # Derived signals
    dl_rate = round(downloads / visitors * 100, 1) if visitors > 0 else 0
    rfq_rate = round(rfqs / visitors * 100, 2) if visitors > 0 else 0
    intent_level = "low" if avg_intent < 10 else "medium" if avg_intent < 25 else "high"

    prompt = f"""
Analyze this B2B manufacturer page and suggest improvements.

── Page Info ──
Type: {page_info.get("page_type", "product")}
Entity: {page_info.get("entity_name", "N/A")}
Title: {page_info.get("title", "N/A")}
SEO Title: {page_info.get("seo_title", "N/A")}
Meta Description: {page_info.get("description", "N/A")}
Content Preview: {(page_info.get("full_description") or "")[:500]}

── Performance Data (last {days} days) ──
Page Views: {views} | Unique Visitors: {visitors}
Spec Downloads: {downloads} ({dl_rate}% download rate)
RFQ Conversions: {rfqs} ({rfq_rate}% RFQ rate)
Avg Intent Score: {avg_intent:.1f} ({intent_level} intent)

── Industry Benchmarks (B2B industrial) ──
Good spec download rate: > 5% | Good RFQ rate: > 0.5%
Target intent score: > 20

Analyze the gaps and return JSON:
{{
  "overall_score": <integer 0-100, content health score>,
  "performance_diagnosis": "<2-sentence diagnosis of why this page is performing this way>",
  "issues": [
    {{"severity": "high|medium|low", "category": "title|description|content|cta|structure", "issue": "<what's wrong>"}}
  ],
  "suggestions": [
    {{"priority": 1-5, "category": "title|description|content|cta|structure|faq", "action": "<specific action>", "expected_impact": "high|medium|low"}}
  ],
  "priority_actions": [<top 3 immediate actions as strings>],
  "revised_title": "<suggested improved title (max 60 chars)>",
  "revised_description": "<suggested improved meta description (max 160 chars)>",
  "content_gaps": [<topics/sections this page is missing, max 4>]
}}"""

    try:
        resp = await client.chat.completions.create(
            model=settings.AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": OPTIMIZER_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1200,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        logger.error(f"Content optimizer failed: {e}")
        return {
            "overall_score": 0,
            "performance_diagnosis": "AI analysis unavailable.",
            "issues": [],
            "suggestions": [],
            "priority_actions": ["Retry AI analysis after checking API connectivity"],
            "revised_title": None,
            "revised_description": None,
            "content_gaps": [],
        }
