"""Deterministic safety boundary around model-generated product-advisor replies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.services.chat_locale import policy_reply

_INJECTION_PATTERNS = (
    r"ignore (all |the )?(previous|above|system) instructions",
    r"reveal (the )?(system prompt|developer message|hidden instructions)",
    r"act as (a |an )?(system|developer)",
    r"忽略.{0,8}(指令|規則|提示)",
    r"顯示.{0,8}(系統提示|隱藏指令)",
    r"(以前|上記|システム).{0,10}(指示|命令).{0,8}(無視|忘れ)",
    r"(zeige|enthülle).{0,12}(system|intern).{0,12}(anweisung|prompt)",
)
_PRICE_TERMS = (
    "price",
    "pricing",
    "cost",
    "lead time",
    "delivery date",
    "價格",
    "報價",
    "交期",
    "価格",
    "見積",
    "納期",
    "preis",
    "angebot",
    "lieferzeit",
    "가격",
    "견적",
    "납기",
)
_COMPLIANCE_TERMS = (
    "certified",
    "compliant",
    "guarantee",
    "warranty",
    "認證",
    "合規",
    "保證",
    "保固",
    "認証",
    "適合",
    "保証",
    "zertifiziert",
    "konform",
    "garantie",
    "인증",
    "규정 준수",
    "보증",
)
_TRUSTED_TYPES = {
    "product",
    "category",
    "application",
    "faq",
    "certification",
    "capability",
    "page",
    "asset",
}
_NUMBER_RE = re.compile(
    r"(?<![\w./-])(\d+(?:[.,]\d+)?)(?:\s*(mm|cm|m|kg|g|lb|hrc|mpa|nm|v|w|%))?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GroundedReply:
    reply: str
    sources: list[dict[str, str]]
    status: str
    warnings: list[str]
    blocked: bool = False


def normalize_source(source: dict[str, Any]) -> dict[str, str] | None:
    if (
        source.get("type") not in _TRUSTED_TYPES
        or not source.get("id")
        or not source.get("name")
    ):
        return None
    payload = {key: str(source.get(key) or "") for key in ("type", "id", "name", "url")}
    if source.get("filename"):
        payload["filename"] = str(source["filename"])
    if source.get("page_number"):
        payload["page_number"] = str(source["page_number"])
    return payload


def buyer_facing_sources(sources: list[dict[str, str]]) -> list[dict[str, str]]:
    """Visitors see a name and a link they can open — never a forced page number."""
    visible: list[dict[str, str]] = []
    for source in sources:
        url = (source.get("url") or "").strip()
        if not url:
            continue
        visible.append(
            {
                "type": source["type"],
                "id": source["id"],
                "name": source["name"],
                "url": url,
            }
        )
    return visible


def unsupported_numeric_claims(reply: str, evidence_texts: list[str]) -> list[str]:
    corpus = " ".join(evidence_texts).lower().replace(",", "").replace(" ", "")
    unverified: list[str] = []
    for match in _NUMBER_RE.finditer(reply or ""):
        number = match.group(1).replace(",", "")
        if number.isdigit() and (len(number) == 4 or int(number) <= 2):
            continue
        compact = match.group(0).lower().replace(" ", "").replace(",", "")
        if number not in corpus and compact not in corpus:
            unverified.append(match.group(0).strip())
    return unverified


def apply_grounding_policy(
    *,
    question: str,
    reply: str,
    sources: list[dict[str, Any]],
    locale: str,
    evidence_texts: list[str] | None = None,
) -> GroundedReply:
    """Allow only repository-built source objects and fail safely on risky claims."""
    trusted_sources = [
        normalized for source in sources if (normalized := normalize_source(source))
    ]
    lowered_question = question.lower()
    if any(
        re.search(pattern, lowered_question, re.IGNORECASE)
        for pattern in _INJECTION_PATTERNS
    ):
        return GroundedReply(
            reply=policy_reply("prompt_injection", locale),
            sources=[],
            status="blocked",
            warnings=["prompt_injection_blocked"],
            blocked=True,
        )

    combined = f"{question} {reply}".lower()
    warnings: list[str] = []
    if any(term in combined for term in _PRICE_TERMS):
        warnings.append("commercial_terms_require_sales_confirmation")
    if any(term in combined for term in _COMPLIANCE_TERMS):
        warnings.append("compliance_claim_requires_documented_source")

    relevant_compliance_source = any(
        source["type"] == "certification" for source in trusted_sources
    )
    asks_compliance = any(term in lowered_question for term in _COMPLIANCE_TERMS)
    if asks_compliance and not relevant_compliance_source:
        return GroundedReply(
            reply=policy_reply("insufficient_compliance", locale),
            sources=[],
            status="limited",
            warnings=["insufficient_compliance_evidence"],
        )

    if not trusted_sources:
        return GroundedReply(
            reply=policy_reply("no_published_source", locale),
            sources=[],
            status="limited",
            warnings=["no_published_source"],
        )

    invented = unsupported_numeric_claims(reply, evidence_texts or [])
    if invented:
        return GroundedReply(
            reply=policy_reply("unsupported_numeric", locale),
            sources=trusted_sources,
            status="limited",
            warnings=warnings + ["unsupported_numeric_claim"],
        )

    return GroundedReply(
        reply=reply,
        sources=trusted_sources,
        status="grounded",
        warnings=warnings,
    )
