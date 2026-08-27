"""Hard content rules shared by generated and human-revised drafts."""

from __future__ import annotations

import re


class OutreachContentError(ValueError):
    pass


class OutreachDraftBlocked(RuntimeError):
    """A permanent policy/evidence failure; retrying cannot repair the draft."""


_FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "tracking_disclosure",
        re.compile(
            r"\b(we|i)\s+(saw|noticed|tracked)\s+(you|your)|瀏覽紀錄|追蹤到|看到您(?:瀏覽|下載|點擊)|我們發現您",
            re.IGNORECASE,
        ),
    ),
    (
        "invented_relationship",
        re.compile(
            r"\b(as discussed|our previous conversation|valued customer|existing customer)\b|如同(?:先前|上次)討論|既有客戶|長期合作",
            re.IGNORECASE,
        ),
    ),
    (
        "invented_price",
        re.compile(
            r"(?:[$€£¥]|NT\$|USD|EUR|JPY)\s*\d|\b(price|pricing|discount)\s+(?:is|of|at)\b|售價(?:為|是)|折扣(?:為|是)",
            re.IGNORECASE,
        ),
    ),
    (
        "invented_lead_time",
        re.compile(
            r"\b(?:ship|deliver|lead time)\s+(?:in|within|is)\s+\d|\d+\s*(?:business\s*)?days?\s+(?:delivery|lead time)|\d+\s*(?:天|日)(?:內)?(?:出貨|交貨)",
            re.IGNORECASE,
        ),
    ),
    (
        "unsupported_guarantee",
        re.compile(
            r"\b(?:guaranteed|100%|best in class|number one|#1)\b|保證(?:適用|交貨|成功)|業界第一|百分之百",
            re.IGNORECASE,
        ),
    ),
    (
        "invented_specification",
        re.compile(
            r"\b\d+(?:\.\d+)?\s*(?:mm|cm|m|kg|g|mpa|bar|psi|kw|w|v|a|rpm|°c|%)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "invented_certification",
        re.compile(
            r"\b(?:certified|complies with|meets (?:the )?requirements of)\b|通過認證|符合\s*(?:ISO|EN|DIN|JIS)",
            re.IGNORECASE,
        ),
    ),
    (
        "sensitive_identity",
        re.compile(
            r"\b(visitor id|ip address|session id|device fingerprint)\b|訪客編號|IP 位址|工作階段編號",
            re.IGNORECASE,
        ),
    ),
)

_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
_EXTRA_CTA_RE = re.compile(
    r"\b(?:reply|contact us|call us|book (?:a )?(?:call|meeting)|schedule (?:a )?(?:call|meeting)|click here)\b|"
    r"(?:請|歡迎)(?:直接)?(?:回覆|聯絡|來電|預約|點擊)|お問い合わせ|ご返信|ご連絡",
    re.IGNORECASE,
)


def validate_content(*, subject: str, body_without_cta: str) -> None:
    subject = subject.strip()
    body_without_cta = body_without_cta.strip()
    if not subject or not body_without_cta:
        raise OutreachContentError("Subject and body are required")
    if len(subject) > 200 or len(body_without_cta) > 5000:
        raise OutreachContentError("Draft content exceeds the review-only limits")
    combined = f"{subject}\n{body_without_cta}"
    if _URL_RE.search(combined):
        raise OutreachContentError("Drafts cannot add unverified links")
    if _EXTRA_CTA_RE.search(body_without_cta):
        raise OutreachContentError("The system appends the only allowed CTA")
    for code, pattern in _FORBIDDEN_PATTERNS:
        if pattern.search(combined):
            raise OutreachContentError(f"Content policy violation: {code}")


def canonical_cta(language: str) -> str:
    if language.lower().startswith("zh"):
        return "若這與貴公司的需求相關，請直接回覆此信，我們會安排業務協助確認。"
    if language.lower().startswith("ja"):
        return "ご関心がございましたら、このメールにご返信ください。担当者よりご案内します。"
    return "If this is relevant to your team, please reply to this email and our sales team will help."
