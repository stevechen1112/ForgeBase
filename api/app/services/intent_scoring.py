"""
Intent Scoring Engine  (1b.3.1, 1b.3.2)

Centralized rule-based scoring.  Called whenever a new event is received.
Score rules sourced from spec 12.6.1.   Stage thresholds from spec 12.6.3.
"""
from typing import Optional

# ── Scoring rules (spec 12.6.1) ───────────────────────────────────────────────

_BASE_SCORES: dict[str, int] = {
    "page_view": 1,
    "category_view": 2,
    "product_view": 3,
    "application_view": 4,
    "faq_expand": 6,
    "comparison_view": 6,
    "spec_download": 8,
    "certification_view": 3,
    "cta_click": 4,          # secondary default; primary handled below
    "form_start": 5,
    "form_submit": 8,
    "rfq_start": 15,
    "rfq_submit": 30,
    "return_visit": 6,
    "session_depth_reached": 5,
    "chat_start": 8,
    "chat_rfq_handoff": 20,
}

# ── Stage thresholds (spec 12.6.3) ────────────────────────────────────────────

_STAGES: list[tuple[int, str]] = [
    (60, "sales_ready"),
    (30, "hot"),
    (10, "warm"),
    (0,  "cold"),
]


def calculate_score_delta(
    event_name: str,
    properties: Optional[dict] = None,
) -> int:
    """
    Return the score delta for a single event.
    Applies weighted conditions from spec 12.6.1.
    """
    props = properties or {}
    base = _BASE_SCORES.get(event_name, 0)
    extra = 0

    if event_name == "product_view":
        # Spec: repeat view of same product +2
        if props.get("repeat_view"):
            extra += 2

    elif event_name == "faq_expand":
        # Spec: expand ≥ 3 FAQs +4
        if props.get("session_faq_count", 0) >= 3:
            extra += 4

    elif event_name == "cta_click":
        # Primary CTA +8 (overrides base +4)
        if props.get("cta_type") == "primary":
            return 8

    elif event_name == "return_visit":
        # 7 days within last visit +4
        days = props.get("days_since_last", 999)
        if days <= 7:
            extra += 4

    elif event_name == "session_depth_reached":
        # depth ≥ 8 +3
        if props.get("depth", 0) >= 8:
            extra += 3

    return base + extra


def get_intent_stage(score: int) -> str:
    """Map a cumulative score to an intent stage name."""
    for threshold, stage in _STAGES:
        if score >= threshold:
            return stage
    return "cold"


def should_alert(old_stage: str, new_stage: str) -> bool:
    """Return True if a stage transition warrants a sales alert."""
    severity = {"cold": 0, "warm": 1, "hot": 2, "sales_ready": 3}
    return severity.get(new_stage, 0) > severity.get(old_stage, 0)
