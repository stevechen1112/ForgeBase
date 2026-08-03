"""
Intent Score 2.0 — 採購 Facets（實效計畫 §4.1）

在既有 intent_scoring 總分之外，把訊號拆成四個可解釋面向，
讓顧問與客戶能回答「為何 Hot」、並依 facet 篩名單：

- product_interest     產品興趣：產品頁、系列頁、應用頁
- trust_validation     信任驗證：認證頁、FAQ、產能／品管內容
- procurement_readiness 採購準備：規格下載、比較頁、表單行為
- urgency              急迫性：回訪、RFQ start、chat 轉詢價

Facet 分數以事件實際 score_delta 累積（沿用租戶自訂權重）。
"""
from datetime import datetime, timedelta
from typing import Iterable, Optional

FACET_PRODUCT_INTEREST = "product_interest"
FACET_TRUST_VALIDATION = "trust_validation"
FACET_PROCUREMENT_READINESS = "procurement_readiness"
FACET_URGENCY = "urgency"

FACETS = (
    FACET_PRODUCT_INTEREST,
    FACET_TRUST_VALIDATION,
    FACET_PROCUREMENT_READINESS,
    FACET_URGENCY,
)

VISITOR_FACET_COLUMN = {
    FACET_PRODUCT_INTEREST: "facet_product_interest",
    FACET_TRUST_VALIDATION: "facet_trust_validation",
    FACET_PROCUREMENT_READINESS: "facet_procurement_readiness",
    FACET_URGENCY: "facet_urgency",
}

_FACET_BY_EVENT: dict[str, str] = {
    "product_view": FACET_PRODUCT_INTEREST,
    "category_view": FACET_PRODUCT_INTEREST,
    "application_view": FACET_PRODUCT_INTEREST,
    "certification_view": FACET_TRUST_VALIDATION,
    "faq_expand": FACET_TRUST_VALIDATION,
    "spec_download": FACET_PROCUREMENT_READINESS,
    "comparison_view": FACET_PROCUREMENT_READINESS,
    "cta_click": FACET_PROCUREMENT_READINESS,
    "form_start": FACET_PROCUREMENT_READINESS,
    "form_submit": FACET_PROCUREMENT_READINESS,
    "rfq_submit": FACET_PROCUREMENT_READINESS,
    "return_visit": FACET_URGENCY,
    "rfq_start": FACET_URGENCY,
    "chat_start": FACET_URGENCY,
    "chat_rfq_handoff": FACET_URGENCY,
    "session_depth_reached": FACET_URGENCY,
}

# page_view 依 page_type 歸屬（無法歸類則不計 facet）
_FACET_BY_PAGE_TYPE: dict[str, str] = {
    "product": FACET_PRODUCT_INTEREST,
    "category": FACET_PRODUCT_INTEREST,
    "application": FACET_PRODUCT_INTEREST,
    "certification": FACET_TRUST_VALIDATION,
    "capability": FACET_TRUST_VALIDATION,
    "comparison": FACET_PROCUREMENT_READINESS,
    "pricing": FACET_PROCUREMENT_READINESS,
}


def facet_for_event(
    event_name: str,
    page_type: Optional[str] = None,
) -> Optional[str]:
    if event_name == "page_view":
        return _FACET_BY_PAGE_TYPE.get(page_type or "")
    return _FACET_BY_EVENT.get(event_name)


def apply_event_to_visitor(visitor, event_name: str, score_delta: int, page_type: Optional[str] = None) -> None:
    """把單一事件的 facet 分數累進 visitor 的 facet 欄位。"""
    facet = facet_for_event(event_name, page_type)
    if not facet or score_delta <= 0:
        return
    column = VISITOR_FACET_COLUMN[facet]
    setattr(visitor, column, max(0, getattr(visitor, column, 0) + score_delta))


def recompute_facets(events: Iterable) -> dict[str, int]:
    """從事件序列重算 facets（backfill／對帳用）。events 需有 event_name/page_type/score_delta。"""
    totals = {f: 0 for f in FACETS}
    for ev in events:
        facet = facet_for_event(ev.event_name, getattr(ev, "page_type", None))
        if facet:
            delta = getattr(ev, "score_delta", 0) or 0
            if delta > 0:
                totals[facet] += delta
    return totals


# ── 「為何 Hot」解釋字串 ────────────────────────────────────────────────────

def build_intent_explanation(
    events: list,
    now: Optional[datetime] = None,
    *,
    has_rfq_record: bool = False,
) -> str:
    """從近期事件產生顧問可讀的熱度原因，例如：

    「48h 內 3 次認證頁 + 下載規格表 + 進 RFQ 未送出」

    events：近期的 TrackingEvent（建議 ≤50 筆，含 event_name/page_type/created_at）。
    has_rfq_record：是否已有 rfq_requests 列（表單建立不一定寫入 rfq_submit 事件）。
    """
    now = now or datetime.utcnow()
    window_48h = now - timedelta(hours=48)

    def _ts(e) -> datetime:
        # TrackingEvent 用 timestamp；測試／手動附加的物件用 created_at
        ts = getattr(e, "created_at", None) or getattr(e, "timestamp", None) or now
        return ts.replace(tzinfo=None) if ts.tzinfo is not None else ts

    recent_48h = [e for e in events if _ts(e) >= window_48h]

    def _count(event_list, name=None, page_types=None):
        n = 0
        for e in event_list:
            if name and e.event_name != name:
                continue
            if page_types and getattr(e, "page_type", None) not in page_types:
                continue
            n += 1
        return n

    phrases: list[str] = []

    cert_views_48h = _count(recent_48h, "certification_view") + _count(
        recent_48h, "page_view", {"certification", "capability"}
    )
    if cert_views_48h:
        phrases.append(f"48h 內 {cert_views_48h} 次認證／產能頁")

    product_views_48h = _count(recent_48h, "product_view") + _count(recent_48h, "page_view", {"product"})
    if product_views_48h >= 2:
        phrases.append(f"48h 內 {product_views_48h} 次產品頁")

    if _count(events, "spec_download"):
        phrases.append("下載規格表")
    if _count(events, "comparison_view"):
        phrases.append("研究比較頁")

    return_visits = _count(recent_48h, "return_visit")
    if return_visits:
        phrases.append(f"48h 內回訪 {return_visits} 次")

    rfq_start = _count(events, "rfq_start")
    rfq_submit = _count(events, "rfq_submit")
    if has_rfq_record or rfq_submit:
        phrases.append("已送出 RFQ")
    elif rfq_start > rfq_submit:
        phrases.append("進 RFQ 未送出")

    if _count(events, "chat_rfq_handoff"):
        phrases.append("AI 顧問轉詢價")

    return " + ".join(phrases)
