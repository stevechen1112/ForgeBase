"""
AI CTA & Workflow Recommender  (3.1.4)

Recommends a contextual CTA from explicit first-party activity and page context.
"""
import json
import logging
from typing import Any

from app.core.config import settings
from app.core.tracing import chat_completion_kwargs, get_openai_client

logger = logging.getLogger(__name__)
client = get_openai_client()

RECOMMEND_SYSTEM = """You are a B2B conversion optimization expert.
Given factual first-party activity, recommend the most relevant CTA.
Do not infer a buyer score, stage, personality, or hidden intent.
Output valid JSON only."""


async def recommend_cta_for_visitor(
    visitor_profile: dict[str, Any],
    available_ctas: list[dict[str, Any]],
    current_page_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Recommend the best CTA for a visitor based on their behavioral profile.

    Args:
        visitor_profile: {
            total_page_views, total_visits, top_products_viewed, top_applications_viewed,
            has_downloaded_spec, has_submitted_rfq, country, device_type,
            recent_events (list of last N event names)
        }
        available_ctas: list of CTA dicts {id, name, action_type, label, description}
        current_page_context: {page_type, entity_name} if available

    Returns:
        {
            recommended_cta_id, recommended_cta_name, confidence, reason,
            alternative_cta_id, personalization_hint,
            recommended_workflow_type, workflow_rationale
        }
    """
    ctas_ctx = json.dumps(
        [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "action_type": c.get("action_type"),
                "label": c.get("label"),
            }
            for c in available_ctas[:10]
        ],
        ensure_ascii=False,
    )

    prompt = f"""
Recommend the best CTA and nurture workflow for this visitor.

── Visitor Profile ──
Total Visits: {visitor_profile.get("total_visits", 0)} | Page Views: {visitor_profile.get("total_page_views", 0)}
Products Viewed: {visitor_profile.get("top_products_viewed", [])}
Applications Viewed: {visitor_profile.get("top_applications_viewed", [])}
Downloaded Spec Sheet: {visitor_profile.get("has_downloaded_spec", False)}
Submitted RFQ: {visitor_profile.get("has_submitted_rfq", False)}
Country: {visitor_profile.get("country", "unknown")}
Recent Events: {visitor_profile.get("recent_events", [])[-10:]}

── Current Page ──
{json.dumps(current_page_context or {}, ensure_ascii=False)}

── Available CTAs ──
{ctas_ctx}

Return JSON:
{{
  "recommended_cta_id": "<uuid or null>",
  "recommended_cta_name": "<name>",
  "confidence": <integer 0-100>,
  "reason": "<why this CTA is best for this visitor>",
  "alternative_cta_id": "<uuid or null; second best option>",
  "personalization_hint": "<short text to personalize the CTA, e.g. mention specific product>",
  "recommended_workflow_type": "<discovery|nurture|re-engagement|sales-handoff>",
  "workflow_rationale": "<why this workflow type fits this visitor>"
}}"""

    try:
        resp = await client.chat.completions.create(
            model=settings.AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": RECOMMEND_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            **chat_completion_kwargs(temperature=0.3, max_output_tokens=600),
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        logger.error(f"CTA recommender failed: {e}")
        # Deterministic fallback based on current page context only.
        action = "rfq" if (current_page_context or {}).get("page_type") == "product" else "contact"
        fallback_cta = next(
            (c for c in available_ctas if c.get("action_type") == action),
            available_ctas[0] if available_ctas else None,
        )
        return {
            "recommended_cta_id": fallback_cta.get("id") if fallback_cta else None,
            "recommended_cta_name": fallback_cta.get("name", "Contact Us") if fallback_cta else "Contact Us",
            "confidence": 50,
            "reason": "Contextual fallback based on the current page",
            "alternative_cta_id": None,
            "personalization_hint": None,
            "recommended_workflow_type": "discovery",
            "workflow_rationale": "Fallback rule applied — AI unavailable",
        }
