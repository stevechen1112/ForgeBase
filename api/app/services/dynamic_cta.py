"""Contextual CTA selection based only on the current page and explicit content."""

from typing import Any


PAGE_ACTION_PRIORITY: dict[str, list[str]] = {
    "product": ["rfq", "download", "contact", "comparison", "external_link"],
    "application": ["contact", "rfq", "download", "comparison", "external_link"],
    "comparison": ["rfq", "contact", "download", "external_link"],
    "default": ["contact", "rfq", "download", "comparison", "external_link"],
}


def _localized(locale: str, english: str, traditional_chinese: str) -> str:
    return traditional_chinese if locale.lower().replace("_", "-").startswith("zh") else english


def select_dynamic_cta(
    available_ctas: list[dict[str, Any]],
    page_context: dict[str, Any] | None = None,
    top_products_viewed: list[str] | None = None,
    locale: str = "en",
) -> dict[str, Any]:
    """Select a CTA without inferring or scoring the visitor."""
    page_type = str((page_context or {}).get("page_type") or "default")
    priorities = PAGE_ACTION_PRIORITY.get(page_type, PAGE_ACTION_PRIORITY["default"])

    def priority(cta: dict[str, Any]) -> int:
        try:
            return priorities.index(str(cta.get("action_type", "")))
        except ValueError:
            return len(priorities)

    selected = sorted(available_ctas, key=priority)[0] if available_ctas else None
    if selected is None:
        return {"cta": None, "variant": "standard", "personalization": {}, "fallback_used": True}

    personalization: dict[str, Any] = {
        "headline_prefix": _localized(locale, "Choose the next step", "選擇下一步")
    }
    if page_context and page_context.get("entity_name"):
        personalization["entity_hint"] = page_context["entity_name"]
    elif top_products_viewed:
        personalization["product_hint"] = top_products_viewed[0]

    return {
        "cta": selected,
        "variant": "contextual",
        "personalization": personalization,
        "fallback_used": False,
    }
