"""Deterministic reply classification; inbound text is never executed as a prompt."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReplyClassification:
    label: str
    confidence: float
    reasons: list[str]
    is_human: bool


def classify_reply(
    subject: str, body: str, headers: dict[str, str]
) -> ReplyClassification:
    combined = f"{subject}\n{body}".lower()
    auto_submitted = headers.get("auto-submitted", "").lower()
    precedence = headers.get("precedence", "").lower()
    if (
        (auto_submitted and auto_submitted != "no")
        or precedence in {"bulk", "junk", "list"}
        or headers.get("x-autoreply")
        or headers.get("x-autorespond")
        or any(
            term in combined
            for term in (
                "out of office",
                "automatic reply",
                "auto-reply",
                "不在辦公室",
                "自動回覆",
            )
        )
    ):
        return ReplyClassification(
            "auto_reply", 0.99, ["automatic-message header or phrase"], False
        )
    if any(
        term in combined
        for term in (
            "mailer-daemon",
            "delivery status notification",
            "undeliverable",
            "mail delivery failed",
        )
    ):
        return ReplyClassification("bounce", 0.98, ["delivery failure phrase"], False)
    if any(
        term in combined
        for term in (
            "unsubscribe",
            "remove me",
            "stop emailing",
            "取消訂閱",
            "不要再寄",
            "停止寄送",
        )
    ):
        return ReplyClassification(
            "unsubscribe", 0.99, ["explicit opt-out phrase"], True
        )
    if any(
        term in combined
        for term in (
            "wrong person",
            "not the right person",
            "no longer work",
            "找錯人",
            "不是負責人",
            "已離職",
        )
    ):
        return ReplyClassification("wrong_person", 0.95, ["wrong-person phrase"], True)
    if any(
        term in combined
        for term in (
            "not interested",
            "do not contact",
            "沒有興趣",
            "不感興趣",
            "別再聯絡",
        )
    ):
        return ReplyClassification("negative", 0.95, ["negative intent phrase"], True)
    if any(
        term in combined
        for term in (
            "not now",
            "later this year",
            "next quarter",
            "目前不需要",
            "之後再說",
            "下季",
        )
    ):
        return ReplyClassification("not_now", 0.9, ["defer phrase"], True)
    if any(
        term in combined
        for term in (
            "quotation",
            "quote",
            "rfq",
            "request for quote",
            "moq",
            "unit price",
            "quantity",
            "報價",
            "詢價",
            "最低訂購",
            "數量",
            "見積",
        )
    ):
        return ReplyClassification(
            "rfq", 0.92, ["quotation or procurement phrase"], True
        )
    if any(
        term in combined
        for term in (
            "interested",
            "let's discuss",
            "schedule a call",
            "sounds good",
            "有興趣",
            "想了解",
            "安排會議",
            "興味があります",
        )
    ):
        return ReplyClassification(
            "positive", 0.88, ["positive engagement phrase"], True
        )
    if (
        "?" in body
        or "？" in body
        or any(
            term in combined
            for term in ("could you", "can you", "請問", "想知道", "教えて")
        )
    ):
        return ReplyClassification("question", 0.8, ["question signal"], True)
    return ReplyClassification("unknown", 0.35, ["no deterministic rule matched"], True)
