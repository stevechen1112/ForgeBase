from typing import Any

from app.services.chat_locale import fallback_reply
from app.services.chat_policy import build_response_plan
from app.services.chat_response_utils import (
    merge_reply_and_clarifying_question,
    normalize_question,
)


def finalize_generated_chat_response(
    *,
    user_question: str,
    context_entity_type: str,
    recent_messages: list[Any],
    payload: dict[str, Any],
    locale: str = "en",
) -> dict[str, Any]:
    plan = build_response_plan(
        user_question=user_question,
        context_entity_type=context_entity_type,
        recent_messages=recent_messages,
        model_suggested_action=payload.get("suggested_action") or "none",
        model_needs_clarification=bool(payload.get("needs_clarification")),
        model_clarifying_question=normalize_question(payload.get("clarifying_question")),
        locale=locale,
    )

    reply = payload.get("reply") or fallback_reply(locale)
    reply, needs_clarification, clarifying_question = merge_reply_and_clarifying_question(
        reply,
        plan.clarifying_question,
        locale=locale,
    )

    finalized_payload = dict(payload)
    finalized_payload["reply"] = reply
    finalized_payload["needs_clarification"] = needs_clarification
    finalized_payload["clarifying_question"] = clarifying_question
    finalized_payload["suggested_action"] = plan.suggested_action
    if plan.handoff_reason:
        finalized_payload["handoff_reason"] = plan.handoff_reason
    return finalized_payload
