from typing import Any, Optional

from app.services.chat_response_utils import contains_any, has_quantity_signal, normalize_question
from app.services.chat_state import CommercialSlotState, DialogueState, ResponsePlan


ASSORTMENT_TERMS = [
    "which",
    "best",
    "recommend",
    "shortlist",
    "start with",
    "starter",
    "assortment",
    "bundle",
    "fit",
]
OEM_TERMS = ["oem", "private label", "private-label", "branding", "logo", "custom", "packaging"]
STANDARD_TERMS = ["standard supply", "standard range", "standard assortment", "stock program", "neutral package"]
CUSTOM_PACKAGING_TERMS = [
    "custom packaging",
    "private-label packaging",
    "private label packaging",
    "retail box",
    "printed carton",
    "custom box",
]
LOGO_ONLY_TERMS = ["logo marking", "logo only", "logo engraving", "laser logo"]
RFQ_TERMS = [
    "rfq",
    "quote",
    "quotation",
    "price",
    "pricing",
    "lead time",
    "sample",
    "trial order",
]
MARKET_TERMS = ["europe", "european", "eu", "germany", "german", "us", "usa", "japan", "middle east", "uk"]
COMPLIANCE_TERMS = ["ce", "reach", "rohs", "ul", "compliance", "certification", "iso"]


def _message_role(message: Any) -> str:
    return str(getattr(message, "role", "") or "").lower()


def _message_content(message: Any) -> str:
    return str(getattr(message, "content", "") or "")


def _build_user_conversation_text(user_question: str, recent_messages: list[Any]) -> str:
    user_lines = [_message_content(message).strip() for message in recent_messages if _message_role(message) == "user"]
    normalized_current = user_question.strip().lower()
    if not user_lines or user_lines[-1].strip().lower() != normalized_current:
        user_lines.append(user_question.strip())
    return "\n".join(line for line in user_lines if line)


def _detect_program_type(text: str) -> str:
    if contains_any(text, OEM_TERMS):
        return "oem"
    if contains_any(text, STANDARD_TERMS):
        return "standard"
    return "unknown"


def _detect_packaging_scope(text: str) -> str:
    if contains_any(text, CUSTOM_PACKAGING_TERMS):
        return "custom_packaging"
    if contains_any(text, LOGO_ONLY_TERMS):
        return "logo_only"
    return "unknown"


def _detect_market_requirement(text: str) -> str:
    if contains_any(text, COMPLIANCE_TERMS):
        return "compliance_named"
    if contains_any(text, MARKET_TERMS):
        return "named_market"
    return "unknown"


def _clarifying_question_for_slot(missing_slot: Optional[str]) -> Optional[str]:
    if missing_slot == "program_type":
        return "Are you evaluating a standard supply range, or an OEM/private-label program"
    if missing_slot == "quantity":
        return "What estimated quantity or MOQ target should I use for the first RFQ round"
    if missing_slot == "packaging_scope":
        return "For the private-label scope, do you need logo marking only, or custom packaging as well"
    if missing_slot == "market_requirement":
        return "Which target market or compliance requirement should I account for in the shortlist"
    return None


def resolve_dialogue_state(
    *,
    user_question: str,
    context_entity_type: str,
    recent_messages: list[Any],
    model_suggested_action: str = "none",
) -> DialogueState:
    full_user_text = _build_user_conversation_text(user_question, recent_messages)
    lowered_question = user_question.lower()
    lowered_full_text = full_user_text.lower()
    broad_context = context_entity_type in {"category", "application", "home"}
    asks_for_shortlist = broad_context and contains_any(lowered_question, ASSORTMENT_TERMS)
    asks_for_rfq = contains_any(lowered_question, RFQ_TERMS)

    slots = CommercialSlotState(
        program_type=_detect_program_type(lowered_full_text),
        quantity_known=has_quantity_signal(lowered_full_text),
        packaging_scope=_detect_packaging_scope(lowered_full_text),
        market_requirement=_detect_market_requirement(lowered_full_text),
    )

    if asks_for_rfq or slots.program_type == "oem" or slots.quantity_known or model_suggested_action == "rfq":
        buyer_intent = "high"
    elif asks_for_shortlist:
        buyer_intent = "medium"
    else:
        buyer_intent = "low"

    missing_slot = None
    if broad_context and asks_for_shortlist and slots.program_type == "unknown":
        missing_slot = "program_type"
    elif buyer_intent == "high" and not slots.quantity_known:
        missing_slot = "quantity"
    elif slots.program_type == "oem" and slots.packaging_scope == "unknown" and contains_any(lowered_question, OEM_TERMS):
        missing_slot = "packaging_scope"
    elif contains_any(lowered_question, ["compliance", "certification", "market"]) and slots.market_requirement == "unknown":
        missing_slot = "market_requirement"

    if buyer_intent == "high" and (slots.quantity_known or asks_for_rfq):
        stage = "rfq_ready"
    elif buyer_intent in {"medium", "high"}:
        stage = "qualification"
    else:
        stage = "discovery"

    return DialogueState(
        context_entity_type=context_entity_type,
        stage=stage,
        buyer_intent=buyer_intent,
        is_broad_discovery=broad_context,
        asks_for_shortlist=asks_for_shortlist,
        asks_for_rfq=asks_for_rfq,
        slots=slots,
        missing_slot=missing_slot,
    )


def infer_clarifying_question(
    user_question: str,
    context_entity_type: str,
    suggested_action: str,
    recent_messages: Optional[list[Any]] = None,
) -> Optional[str]:
    state = resolve_dialogue_state(
        user_question=user_question,
        context_entity_type=context_entity_type,
        recent_messages=recent_messages or [],
        model_suggested_action=suggested_action,
    )
    return _clarifying_question_for_slot(state.missing_slot)


def build_response_plan(
    *,
    user_question: str,
    context_entity_type: str,
    recent_messages: list[Any],
    model_suggested_action: str,
    model_needs_clarification: bool,
    model_clarifying_question: Optional[str],
) -> ResponsePlan:
    state = resolve_dialogue_state(
        user_question=user_question,
        context_entity_type=context_entity_type,
        recent_messages=recent_messages,
        model_suggested_action=model_suggested_action,
    )
    policy_question = _clarifying_question_for_slot(state.missing_slot)
    clarifying_question = normalize_question(policy_question or model_clarifying_question)
    needs_clarification = bool(clarifying_question) and (
        model_needs_clarification or state.missing_slot is not None or state.stage == "qualification"
    )

    suggested_action = model_suggested_action if model_suggested_action in {"none", "rfq", "contact"} else "none"
    if state.buyer_intent == "high":
        suggested_action = "rfq"
    elif suggested_action == "contact" and state.buyer_intent != "low":
        suggested_action = "none"

    handoff_reason = None
    if suggested_action == "rfq":
        handoff_reason = state.missing_slot or state.stage

    return ResponsePlan(
        stage=state.stage,
        buyer_intent=state.buyer_intent,
        suggested_action=suggested_action,
        needs_clarification=needs_clarification,
        clarifying_question=clarifying_question if needs_clarification else None,
        handoff_reason=handoff_reason,
    )