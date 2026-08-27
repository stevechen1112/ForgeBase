import re
from typing import Optional

from app.services.chat_locale import clarification_prefix


def contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def has_quantity_signal(text: str) -> bool:
    lowered = text.lower()
    quantity_terms = [
        "qty",
        "quantity",
        "moq",
        "pcs",
        "pieces",
        "units",
        "containers",
        "trial order",
        "pilot order",
        "starter order",
        "數量",
        "最低訂購量",
        "試單",
        "件",
        "組",
        "個",
        "最低発注数量",
        "数量",
        "ロット",
        "개",
        "수량",
        "최소 주문 수량",
        "menge",
        "mindestbestellmenge",
    ]
    return contains_any(lowered, quantity_terms) or bool(
        re.search(r"\d+[kKmM萬千]?", lowered)
    )


def normalize_question(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    question = value.strip()
    if not question:
        return None
    if question[-1] not in {"?", ".", "!", "？", "。", "！"}:
        question += "?"
    return question


def merge_reply_and_clarifying_question(
    reply: str,
    clarifying_question: Optional[str],
    locale: str = "en",
) -> tuple[str, bool, Optional[str]]:
    normalized_question = normalize_question(clarifying_question)
    if not normalized_question:
        return reply, False, None

    if normalized_question.lower() in reply.lower():
        return reply, True, normalized_question

    prefix = clarification_prefix(locale)
    merged_reply = f"{reply.rstrip()}\n\n{prefix} {normalized_question}"
    return merged_reply, True, normalized_question
