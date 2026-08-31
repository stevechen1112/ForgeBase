"""
Intent Scoring Engine  (1b.3.1, 1b.3.2)

Centralized rule-based scoring.  Called whenever a new event is received.
Score rules sourced from spec 12.6.1.   Stage thresholds from spec 12.6.3.
"""
from typing import Optional

# ── Scoring rules (spec 12.6.1) ───────────────────────────────────────────────
# Exported so the admin rule API can read and present the defaults.

DEFAULT_BASE_SCORES: dict[str, int] = {
    "page_view": 1,
    "category_view": 2,
    "product_view": 3,
    "application_view": 4,
    "faq_expand": 6,
    "comparison_view": 6,
    "spec_download": 8,
    "certification_view": 3,
    "cta_click": 4,          # secondary default; primary handled below
    "cta_impression": 0,
    "form_start": 5,
    "form_submit": 8,
    "rfq_start": 15,
    "rfq_submit": 30,
    "return_visit": 6,
    "session_depth_reached": 5,
    "chat_start": 8,
    "chat_rfq_handoff": 20,
}

# Keep legacy alias so existing imports of _BASE_SCORES still work.
_BASE_SCORES = DEFAULT_BASE_SCORES

# ── Stage thresholds (spec 12.6.3) ────────────────────────────────────────────
# List of (min_score, stage_name) — checked from highest to lowest.

DEFAULT_STAGES: list[tuple[int, str]] = [
    (60, "sales_ready"),
    (30, "hot"),
    (10, "warm"),
    (0,  "cold"),
]

_STAGES = DEFAULT_STAGES


def calculate_score_delta(
    event_name: str,
    properties: Optional[dict] = None,
    custom_scores: Optional[dict[str, int]] = None,
) -> int:
    """
    Return the score delta for a single event.
    Applies weighted conditions from spec 12.6.1.
    Pass custom_scores to override the default per-event weights.
    """
    scores = custom_scores if custom_scores is not None else DEFAULT_BASE_SCORES
    props = properties or {}
    base = scores.get(event_name, 0)
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
        # Primary CTA: use custom score if present, else default +8
        primary_score = scores.get("cta_click_primary", 8)
        if props.get("cta_type") == "primary":
            return primary_score

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


def get_intent_stage(
    score: int,
    custom_stages: Optional[list[tuple[int, str]]] = None,
) -> str:
    """Map a cumulative score to an intent stage name."""
    stages = custom_stages if custom_stages is not None else DEFAULT_STAGES
    for threshold, stage in stages:
        if score >= threshold:
            return stage
    return "cold"


def should_alert(old_stage: str, new_stage: str) -> bool:
    """Return True if a stage transition warrants a sales alert."""
    severity = {"cold": 0, "warm": 1, "hot": 2, "sales_ready": 3}
    return severity.get(new_stage, 0) > severity.get(old_stage, 0)
