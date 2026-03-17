from dataclasses import dataclass
from typing import Literal, Optional


ConversationStage = Literal["discovery", "qualification", "rfq_ready"]
IntentStrength = Literal["low", "medium", "high"]
ProgramType = Literal["unknown", "standard", "oem"]
PackagingScope = Literal["unknown", "logo_only", "custom_packaging"]
MarketRequirement = Literal["unknown", "named_market", "compliance_named"]
MissingSlot = Literal["program_type", "quantity", "packaging_scope", "market_requirement"]


@dataclass(frozen=True)
class CommercialSlotState:
    program_type: ProgramType
    quantity_known: bool
    packaging_scope: PackagingScope
    market_requirement: MarketRequirement


@dataclass(frozen=True)
class DialogueState:
    context_entity_type: str
    stage: ConversationStage
    buyer_intent: IntentStrength
    is_broad_discovery: bool
    asks_for_shortlist: bool
    asks_for_rfq: bool
    slots: CommercialSlotState
    missing_slot: Optional[MissingSlot]


@dataclass(frozen=True)
class ResponsePlan:
    stage: ConversationStage
    buyer_intent: IntentStrength
    suggested_action: Literal["none", "rfq", "contact"]
    needs_clarification: bool
    clarifying_question: Optional[str]
    handoff_reason: Optional[str]