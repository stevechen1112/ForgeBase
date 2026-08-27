import re
from typing import Any, Optional

from app.services.chat_response_utils import (
    contains_any,
    has_quantity_signal,
    normalize_question,
)
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
    "推薦",
    "適合",
    "怎麼選",
    "哪一款",
    "組合",
    "おすすめ",
    "どれ",
    "選び",
    "適した",
    "welch",
    "empfehl",
]
OEM_TERMS = [
    "oem",
    "private label",
    "private-label",
    "branding",
    "logo",
    "custom",
    "packaging",
    "代工",
    "貼牌",
    "自有品牌",
    "客製",
    "包裝",
    "プライベートブランド",
    "自社ブランド",
    "カスタム",
    "包装",
    "eigenmarke",
    "kundenspezifisch",
    "verpackung",
]
STANDARD_TERMS = [
    "standard supply",
    "standard range",
    "standard assortment",
    "stock program",
    "neutral package",
]
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
    "詢價",
    "報價",
    "價格",
    "交期",
    "樣品",
    "試單",
    "見積",
    "価格",
    "納期",
    "サンプル",
    "最低発注数量",
    "angebot",
    "preis",
    "lieferzeit",
    "mindestbestellmenge",
    "muster",
    "견적",
    "가격",
    "납기",
    "샘플",
    "최소 주문 수량",
]
MARKET_TERMS = [
    "europe",
    "european",
    "eu",
    "germany",
    "german",
    "us",
    "usa",
    "japan",
    "middle east",
    "uk",
    "歐洲",
    "德國",
    "美國",
    "日本",
    "中東",
    "英國",
    "欧州",
    "ドイツ",
    "米国",
    "europa",
    "deutschland",
]
COMPLIANCE_TERMS = [
    "ce",
    "reach",
    "rohs",
    "ul",
    "compliance",
    "certification",
    "iso",
    "法規",
    "認證",
    "合規",
    "法規",
    "認証",
    "適合",
    "zertifizierung",
    "konformität",
    "인증",
    "규정",
]
USE_CASE_TERMS = [
    "used for",
    "use case",
    "application",
    "for our",
    "for automotive",
    "for construction",
    "for assembly",
    "production line",
    "assembly line",
    "repair",
    "maintenance",
    "diy",
    "professional use",
    "industry",
    "用途",
    "應用",
    "產線",
    "維修",
    "製造",
    "組裝",
    "用途",
    "使用",
    "生産ライン",
    "保守",
    "製造",
    "組立",
    "anwendung",
    "produktionslinie",
    "wartung",
    "montage",
    "용도",
    "생산 라인",
    "유지보수",
    "조립",
]
SPEC_TERMS = [
    "material",
    "cr-v",
    "cr-mo",
    "chrome vanadium",
    "stainless",
    "hardness",
    "hrc",
    "torque",
    "dimension",
    "size",
    "length",
    "din",
    "ansi",
    "spec",
    "drawing",
    "材質",
    "硬度",
    "扭力",
    "尺寸",
    "規格",
    "圖面",
    "公差",
    "材質",
    "硬度",
    "トルク",
    "寸法",
    "仕様",
    "図面",
    "公差",
    "werkstoff",
    "härte",
    "drehmoment",
    "abmessung",
    "spezifikation",
    "zeichnung",
    "toleranz",
    "재질",
    "경도",
    "토크",
    "치수",
    "사양",
    "도면",
    "공차",
    "tolerance",
]
LEAD_TIME_TERMS = [
    "lead time",
    "delivery",
    "deliver",
    "ship by",
    "shipment",
    "deadline",
    "urgent",
    "by q1",
    "by q2",
    "by q3",
    "by q4",
    "weeks",
    "days",
    "交期",
    "出貨",
    "到貨",
    "急件",
    "週",
    "天",
    "納期",
    "出荷",
    "到着",
    "至急",
    "週間",
    "日",
    "lieferzeit",
    "versand",
    "ankunft",
    "dringend",
    "wochen",
    "tage",
    "납기",
    "출하",
    "도착",
    "긴급",
    "주",
    "일",
]


def _message_role(message: Any) -> str:
    return str(getattr(message, "role", "") or "").lower()


def _message_content(message: Any) -> str:
    return str(getattr(message, "content", "") or "")


def _build_user_conversation_text(
    user_question: str, recent_messages: list[Any]
) -> str:
    user_lines = [
        _message_content(message).strip()
        for message in recent_messages
        if _message_role(message) == "user"
    ]
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


def _clarifying_question_for_slot(
    missing_slot: Optional[str], locale: str = "en"
) -> Optional[str]:
    language = locale.lower().split("-", 1)[0]
    questions = {
        "zh": {
            "program_type": "您要找的是標準品供應，還是 OEM／自有品牌方案",
            "quantity": "第一輪詢價預估需要多少數量，或希望的 MOQ 是多少",
            "use_case": "這項產品預計用在哪個應用或生產情境",
            "spec_detail": "需要優先確認哪些規格，例如材質、尺寸或適用標準",
            "lead_time": "希望的交貨時間或最晚出貨日是什麼時候",
            "packaging_scope": "自有品牌需求是只要標示 Logo，還是也需要客製包裝",
            "market_requirement": "產品預計銷售到哪個市場，需要符合哪些認證或法規",
        },
        "en": {
            "program_type": "Are you evaluating a standard supply range, or an OEM/private-label program",
            "quantity": "What estimated quantity or MOQ target should I use for the first RFQ round",
            "use_case": "What will the product be used for — which application or production scenario",
            "spec_detail": "Which key specifications should I confirm — material, dimensions, or applicable standard",
            "lead_time": "What is your target delivery timeframe or required ship date",
            "packaging_scope": "For the private-label scope, do you need logo marking only, or custom packaging as well",
            "market_requirement": "Which target market or compliance requirement should I account for in the shortlist",
        },
        "ja": {
            "program_type": "標準品の供給と、OEM／プライベートブランドのどちらをご検討ですか",
            "quantity": "最初の見積依頼では、想定数量または目標MOQをいくつとして検討すればよいですか",
            "use_case": "この製品はどのような用途または生産環境で使用する予定ですか",
            "spec_detail": "材質、寸法、適用規格など、優先して確認すべき仕様は何ですか",
            "lead_time": "希望する納期または出荷期限はいつですか",
            "packaging_scope": "プライベートブランドでは、ロゴ表示のみですか、それともカスタム包装も必要ですか",
            "market_requirement": "対象市場と、必要な認証または法規要件を教えてください",
        },
        "fr": {
            "program_type": "Évaluez-vous une gamme standard ou un programme OEM / marque privée",
            "quantity": "Quelle quantité estimée ou quelle MOQ dois-je utiliser pour la première RFQ",
            "use_case": "Dans quelle application ou quel environnement de production ce produit sera-t-il utilisé",
            "spec_detail": "Quelles spécifications faut-il confirmer en priorité, par exemple le matériau, les dimensions ou la norme applicable",
            "lead_time": "Quel est votre délai de livraison cible ou la date d’expédition requise",
            "packaging_scope": "Pour la marque privée, avez-vous besoin du marquage du logo uniquement ou également d’un emballage personnalisé",
            "market_requirement": "Quel est le marché cible et quelles certifications ou exigences réglementaires faut-il prendre en compte",
        },
        "ru": {
            "program_type": "Вы рассматриваете стандартный ассортимент или программу OEM / частной торговой марки",
            "quantity": "Какой предполагаемый объём или целевую MOQ указать для первого RFQ",
            "use_case": "Для какого применения или производственного процесса предназначен продукт",
            "spec_detail": "Какие характеристики нужно подтвердить в первую очередь: материал, размеры или применимый стандарт",
            "lead_time": "Какой срок поставки или крайняя дата отгрузки вам требуется",
            "packaging_scope": "Для частной торговой марки нужен только логотип или также индивидуальная упаковка",
            "market_requirement": "Каков целевой рынок и какие сертификаты или нормативные требования нужно учесть",
        },
        "de": {
            "program_type": "Prüfen Sie ein Standardsortiment oder ein OEM-/Eigenmarkenprogramm",
            "quantity": "Welche geschätzte Menge oder welches MOQ soll ich für die erste Angebotsrunde ansetzen",
            "use_case": "Für welche Anwendung oder Produktionsumgebung ist das Produkt vorgesehen",
            "spec_detail": "Welche Spezifikationen soll ich zuerst prüfen, etwa Werkstoff, Abmessungen oder Normen",
            "lead_time": "Welchen Lieferzeitraum oder Versandtermin benötigen Sie",
            "packaging_scope": "Benötigen Sie für die Eigenmarke nur eine Logokennzeichnung oder auch eine individuelle Verpackung",
            "market_requirement": "Für welchen Zielmarkt und welche Zertifizierungs- oder Konformitätsanforderungen soll ich planen",
        },
        "ko": {
            "program_type": "표준 제품 공급과 OEM/자체 브랜드 프로그램 중 어느 쪽을 검토하고 계신가요",
            "quantity": "첫 견적 단계에서 예상 수량 또는 목표 MOQ를 얼마로 적용하면 될까요",
            "use_case": "이 제품은 어떤 용도 또는 생산 환경에서 사용할 예정인가요",
            "spec_detail": "재질, 치수, 적용 표준 중 어떤 사양을 우선 확인해야 하나요",
            "lead_time": "희망 납기 또는 출하 기한은 언제인가요",
            "packaging_scope": "자체 브랜드 범위가 로고 표시만 필요한가요, 아니면 맞춤 포장도 필요한가요",
            "market_requirement": "대상 시장과 필요한 인증 또는 규정 요건은 무엇인가요",
        },
    }
    locale_questions = questions.get(language)
    return locale_questions.get(missing_slot) if locale_questions else None


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
    asks_for_shortlist = broad_context and contains_any(
        lowered_question, ASSORTMENT_TERMS
    )
    asks_for_rfq = contains_any(lowered_question, RFQ_TERMS)

    slots = CommercialSlotState(
        program_type=_detect_program_type(lowered_full_text),
        quantity_known=has_quantity_signal(lowered_full_text),
        packaging_scope=_detect_packaging_scope(lowered_full_text),
        market_requirement=_detect_market_requirement(lowered_full_text),
        use_case_known=contains_any(lowered_full_text, USE_CASE_TERMS),
        spec_known=contains_any(lowered_full_text, SPEC_TERMS),
        lead_time_known=contains_any(lowered_full_text, LEAD_TIME_TERMS),
    )

    if (
        asks_for_rfq
        or slots.program_type == "oem"
        or slots.quantity_known
        or model_suggested_action == "rfq"
    ):
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
    elif buyer_intent == "high" and not slots.use_case_known:
        missing_slot = "use_case"
    elif buyer_intent == "high" and not slots.spec_known:
        missing_slot = "spec_detail"
    elif buyer_intent == "high" and not slots.lead_time_known:
        missing_slot = "lead_time"
    elif (
        slots.program_type == "oem"
        and slots.packaging_scope == "unknown"
        and contains_any(lowered_question, OEM_TERMS)
    ):
        missing_slot = "packaging_scope"
    elif (
        contains_any(lowered_question, ["compliance", "certification", "market"])
        and slots.market_requirement == "unknown"
    ):
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


def summarize_quotable_needs(user_text: str) -> dict[str, Any]:
    """從買家對話文字萃取「可詢價需求」摘要（實效計畫 §4.3）。

    輸出可寫入 RFQ 草稿或 Copilot 工單，讓業務拿到的是結構化需求，
    而不是一整段對話紀錄。
    """
    lowered = user_text.lower()
    program_type = _detect_program_type(lowered)
    packaging_scope = _detect_packaging_scope(lowered)
    market_requirement = _detect_market_requirement(lowered)
    quantity_known = has_quantity_signal(lowered)
    use_case_known = contains_any(lowered, USE_CASE_TERMS)
    spec_known = contains_any(lowered, SPEC_TERMS)
    lead_time_known = contains_any(lowered, LEAD_TIME_TERMS)

    quantity_match = re.search(
        r"\b(\d[\d,]*\s?(?:pcs|pieces|units|sets|containers|k))\b", lowered
    )
    quantity_hint = quantity_match.group(1) if quantity_match else None

    missing = []
    if not quantity_known:
        missing.append("quantity")
    if not use_case_known:
        missing.append("use_case")
    if not spec_known:
        missing.append("spec_detail")
    if not lead_time_known:
        missing.append("lead_time")

    parts: list[str] = []
    parts.append(
        {"oem": "OEM/private-label program", "standard": "standard supply range"}.get(
            program_type, "program type TBD"
        )
    )
    if quantity_hint:
        parts.append(f"quantity ~{quantity_hint}")
    elif quantity_known:
        parts.append("quantity discussed")
    if use_case_known:
        parts.append("use case described")
    if spec_known:
        parts.append("specs mentioned")
    if lead_time_known:
        parts.append("lead time specified")
    if market_requirement != "unknown":
        parts.append("market/compliance named")
    if packaging_scope != "unknown":
        parts.append(packaging_scope.replace("_", " "))
    if missing:
        parts.append("missing: " + ", ".join(missing))

    return {
        "program_type": program_type,
        "quantity_known": quantity_known,
        "quantity_hint": quantity_hint,
        "use_case_known": use_case_known,
        "spec_known": spec_known,
        "lead_time_known": lead_time_known,
        "packaging_scope": packaging_scope,
        "market_requirement": market_requirement,
        "missing": missing,
        "summary_text": "; ".join(parts),
    }


def infer_clarifying_question(
    user_question: str,
    context_entity_type: str,
    suggested_action: str,
    recent_messages: Optional[list[Any]] = None,
    locale: str = "en",
) -> Optional[str]:
    state = resolve_dialogue_state(
        user_question=user_question,
        context_entity_type=context_entity_type,
        recent_messages=recent_messages or [],
        model_suggested_action=suggested_action,
    )
    return _clarifying_question_for_slot(state.missing_slot, locale)


def build_response_plan(
    *,
    user_question: str,
    context_entity_type: str,
    recent_messages: list[Any],
    model_suggested_action: str,
    model_needs_clarification: bool,
    model_clarifying_question: Optional[str],
    locale: str = "en",
) -> ResponsePlan:
    state = resolve_dialogue_state(
        user_question=user_question,
        context_entity_type=context_entity_type,
        recent_messages=recent_messages,
        model_suggested_action=model_suggested_action,
    )
    policy_question = _clarifying_question_for_slot(state.missing_slot, locale)
    clarifying_question = normalize_question(
        policy_question or model_clarifying_question
    )
    needs_clarification = bool(clarifying_question) and (
        model_needs_clarification
        or state.missing_slot is not None
        or state.stage == "qualification"
    )

    suggested_action = (
        model_suggested_action
        if model_suggested_action in {"none", "rfq", "contact"}
        else "none"
    )
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
