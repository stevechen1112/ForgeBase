"""
Dynamic CTA Engine  (3.3.1)

Selects and personalizes the optimal CTA for a visitor based on:
- Intent stage (cold / warm / hot / sales_ready)
- Browsing history (products, applications viewed)
- Page context (current page type and entity)
- Available CTAs in the database

Selection logic:
  sales_ready → RFQ CTA (urgent)
  hot         → RFQ CTA (standard)
  warm        → Download / Comparison / Application CTA
  cold        → Contact / Catalog CTA
"""
from typing import Any

# ── Stage-to-action priority map ──────────────────────────────────────────────

STAGE_ACTION_PRIORITY: dict[str, list[str]] = {
    "sales_ready": ["rfq", "contact", "download", "comparison", "external_link"],
    "hot":         ["rfq", "contact", "download", "comparison", "external_link"],
    "warm":        ["download", "comparison", "rfq", "contact", "external_link"],
    "cold":        ["contact", "external_link", "download", "comparison", "rfq"],
}


def select_dynamic_cta(
    intent_stage: str,
    intent_score: int,
    available_ctas: list[dict[str, Any]],
    page_context: dict[str, Any] | None = None,
    top_products_viewed: list[str] | None = None,
) -> dict[str, Any]:
    """
    Select the best CTA for this visitor from the available CTA list.

    Args:
        intent_stage: "cold" | "warm" | "hot" | "sales_ready"
        intent_score: current rule-based intent score (0-100)
        available_ctas: list of CTA dicts from DB
        page_context: {page_type, entity_name, entity_id}
        top_products_viewed: list of product names recently viewed

    Returns:
        {
            cta: <selected CTA dict>,
            variant: "standard" | "urgent" | "soft",
            personalization: {headline_prefix, cta_label_override},
            fallback_used: bool
        }
    """
    stage = intent_stage if intent_stage in STAGE_ACTION_PRIORITY else "cold"
    action_priority = STAGE_ACTION_PRIORITY[stage]

    # Sort CTAs by stage preference
    def _priority(cta: dict) -> int:
        action_type = cta.get("action_type", "")
        try:
            return action_priority.index(action_type)
        except ValueError:
            return len(action_priority)

    sorted_ctas = sorted(available_ctas, key=_priority)
    selected = sorted_ctas[0] if sorted_ctas else None

    if selected is None:
        return {
            "cta": None,
            "variant": "standard",
            "personalization": {},
            "fallback_used": True,
        }

    # ── Determine variant and personalization ─────────────────────────────────
    variant = "standard"
    personalization: dict[str, Any] = {}

    if stage == "sales_ready":
        variant = "urgent"
        personalization["headline_prefix"] = "您已準備好詢價"
        personalization["cta_label_override"] = "立即送出詢價單"
    elif stage == "hot":
        variant = "standard"
        personalization["headline_prefix"] = "開始您的詢價"
        if top_products_viewed:
            personalization["product_hint"] = top_products_viewed[0]
    elif stage == "warm":
        variant = "soft"
        personalization["headline_prefix"] = "進一步了解"
        if page_context and page_context.get("entity_name"):
            personalization["entity_hint"] = page_context["entity_name"]
    else:
        variant = "soft"
        personalization["headline_prefix"] = "歡迎聯絡我們"

    return {
        "cta": selected,
        "variant": variant,
        "personalization": personalization,
        "fallback_used": False,
    }
