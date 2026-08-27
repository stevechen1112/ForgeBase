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

Facet overrides（實效計畫 §4.2，訊號強時覆寫 stage 優先序）：
  產品興趣高＋信任驗證低 → 先補信任：certification/download CTA
  採購準備高             → RFQ／規格交換
  產品興趣高（重複瀏覽） → 比較頁／應用頁
"""
from typing import Any

from app.services.intent_facets import (
    FACET_PROCUREMENT_READINESS,
    FACET_PRODUCT_INTEREST,
    FACET_TRUST_VALIDATION,
)

# facet 訊號強度門檻（對應規則式 score_delta 累積量級）
_FACET_STRONG = 15

# ── Stage-to-action priority map ──────────────────────────────────────────────

STAGE_ACTION_PRIORITY: dict[str, list[str]] = {
    "sales_ready": ["rfq", "contact", "download", "comparison", "external_link"],
    "hot":         ["rfq", "contact", "download", "comparison", "external_link"],
    "warm":        ["download", "comparison", "rfq", "contact", "external_link"],
    "cold":        ["contact", "external_link", "download", "comparison", "rfq"],
}


def _localized(locale: str, english: str, traditional_chinese: str) -> str:
    return traditional_chinese if locale.lower().replace("_", "-").startswith("zh") else english


def _facet_action_override(facets: dict[str, int] | None, locale: str) -> tuple[list[str] | None, dict[str, str]]:
    """依 facet 組合回傳覆寫的 action 優先序與個人化提示（§4.2）。

    回傳 (None, {}) 表示無強訊號，沿用 stage 優先序。
    """
    if not facets:
        return None, {}
    product = facets.get(FACET_PRODUCT_INTEREST, 0)
    trust = facets.get(FACET_TRUST_VALIDATION, 0)
    procurement = facets.get(FACET_PROCUREMENT_READINESS, 0)

    # 採購準備高 → 短版 RFQ／規格交換
    if procurement >= _FACET_STRONG:
        return (
            ["rfq", "download", "contact", "comparison", "external_link"],
            {"facet_reason": "procurement_ready", "headline_prefix": _localized(locale, "Specifications ready — continue to RFQ", "規格已備，直接取得報價")},
        )
    # 產品興趣高但信任驗證不足 → 先補信任內容
    if product >= _FACET_STRONG and trust < _FACET_STRONG:
        return (
            ["download", "comparison", "contact", "rfq", "external_link"],
            {"facet_reason": "trust_gap", "headline_prefix": _localized(locale, "Review quality evidence first", "先驗證品質與製程證據")},
        )
    # 產品興趣高且已有信任 → 比較頁／應用頁深化
    if product >= _FACET_STRONG:
        return (
            ["comparison", "download", "rfq", "contact", "external_link"],
            {"facet_reason": "deepen_product", "headline_prefix": _localized(locale, "Compare specifications before enquiring", "比較規格，再進一步詢問")},
        )
    return None, {}


def select_dynamic_cta(
    intent_stage: str,
    intent_score: int,
    available_ctas: list[dict[str, Any]],
    page_context: dict[str, Any] | None = None,
    top_products_viewed: list[str] | None = None,
    facets: dict[str, int] | None = None,
    locale: str = "en",
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
    facet_priority, facet_personalization = _facet_action_override(facets, locale)
    action_priority = facet_priority or STAGE_ACTION_PRIORITY[stage]

    # Filter CTAs by target_intent_stage: keep "any" + matching stage
    filtered_ctas = [
        cta for cta in available_ctas
        if cta.get("target_intent_stage", "any") in ("any", stage)
    ]
    # Fall back to all CTAs if filtering removes everything
    if not filtered_ctas:
        filtered_ctas = available_ctas

    # Sort CTAs by stage preference
    def _priority(cta: dict) -> int:
        action_type = cta.get("action_type", "")
        try:
            return action_priority.index(action_type)
        except ValueError:
            return len(action_priority)

    sorted_ctas = sorted(filtered_ctas, key=_priority)
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
        personalization["headline_prefix"] = _localized(locale, "Your requirement is ready for RFQ", "您的需求已可進入詢價")
        personalization["cta_label_override"] = _localized(locale, "Continue to RFQ", "繼續詢價")
    elif stage == "hot":
        variant = "standard"
        personalization["headline_prefix"] = _localized(locale, "Continue with your enquiry", "開始您的詢價")
        if top_products_viewed:
            personalization["product_hint"] = top_products_viewed[0]
    elif stage == "warm":
        variant = "soft"
        personalization["headline_prefix"] = _localized(locale, "Review the next detail", "進一步了解")
        if page_context and page_context.get("entity_name"):
            personalization["entity_hint"] = page_context["entity_name"]
    else:
        variant = "soft"
        personalization["headline_prefix"] = _localized(locale, "Ready when you have a requirement", "有需求時，歡迎進一步聯絡")

    # facet 訊號的個人化優先於 stage 預設（§4.2：像銷售助理的下一步）
    if facet_priority is not None:
        personalization.update(facet_personalization)

    return {
        "cta": selected,
        "variant": variant,
        "personalization": personalization,
        "fallback_used": False,
    }
