from typing import Optional

from app.core.locale import chat_language

_FALLBACK_REPLIES = {
    "en": "I don't have confirmed information for that yet. The fastest next step is to submit an RFQ or contact request.",
    "zh": "目前沒有足夠且已確認的資料可以直接回答。最快的下一步是送出詢價，讓業務依您的需求確認。",
    "ja": "現時点では、確認済みの情報が不足しているため、直接お答えできません。最も早い次のステップは、RFQ（見積依頼）を送信し、担当者に要件の確認を依頼することです。",
    "de": "Dazu liegen derzeit nicht genügend bestätigte Informationen vor. Am schnellsten ist es, eine Anfrage zu senden, damit unser Vertrieb Ihre Anforderungen prüfen kann.",
    "ko": "현재 확인된 정보만으로는 바로 답변드리기 어렵습니다. 견적 요청을 보내 주시면 담당자가 요구 사항을 확인하는 것이 가장 빠릅니다.",
    "es": "Aún no hay suficiente información confirmada para responder con fiabilidad. El siguiente paso más rápido es enviar una solicitud de cotización para que el equipo comercial revise sus requisitos.",
    "fr": "Les informations confirmées disponibles ne suffisent pas encore pour répondre de façon fiable. Le plus rapide est d’envoyer une demande de devis afin que l’équipe commerciale vérifie vos besoins.",
    "ru": "Опубликованных подтверждённых данных пока недостаточно для надёжного ответа. Отправьте запрос на коммерческое предложение, чтобы отдел продаж проверил ваши требования.",
}

_POLICY_REPLIES = {
    "commercial_terms": {
        "en": "Pricing and guaranteed lead time are not confirmed by the published website material. Please submit an RFQ with the product, quantity, specifications, and required date so sales can provide a formal response.",
        "zh": "公開網站資料無法確認價格或保證交期。請在詢價中提供產品、數量、規格與需求日期，由業務正式回覆。",
        "ja": "公開されているウェブサイト資料では、価格や納期保証を確認できません。製品、数量、仕様、希望日を見積依頼に記載し、担当者から正式な回答を受けてください。",
        "de": "Preise und garantierte Lieferzeiten sind durch die veröffentlichten Website-Inhalte nicht bestätigt. Bitte senden Sie eine Anfrage mit Produkt, Menge, Spezifikationen und Wunschtermin.",
        "ko": "공개된 웹사이트 자료만으로는 가격이나 보장된 납기를 확인할 수 없습니다. 제품, 수량, 사양 및 희망 일자를 포함하여 견적을 요청해 주세요.",
        "fr": "Les prix et les délais garantis ne sont pas confirmés par les informations publiées sur le site. Envoyez une RFQ avec le produit, la quantité, les spécifications et la date requise afin d’obtenir une réponse formelle.",
        "ru": "Цены и гарантированные сроки поставки не подтверждаются опубликованными материалами сайта. Отправьте RFQ с указанием продукта, количества, характеристик и требуемой даты для официального ответа.",
    },
    "prompt_injection": {
        "en": "I cannot change system rules or reveal internal instructions. Please ask about a product, specification, certification, or RFQ requirement.",
        "zh": "我無法變更系統規則或顯示內部指令。請直接告訴我您要查詢的產品、規格、認證或詢價需求。",
        "ja": "システムのルールを変更したり、内部指示を開示したりすることはできません。製品、仕様、認証、または見積要件についてご質問ください。",
        "de": "Ich kann Systemregeln nicht ändern oder interne Anweisungen offenlegen. Bitte fragen Sie nach einem Produkt, einer Spezifikation, einer Zertifizierung oder einer Angebotsanforderung.",
        "ko": "시스템 규칙을 변경하거나 내부 지침을 공개할 수 없습니다. 제품, 사양, 인증 또는 견적 요청에 관해 질문해 주세요.",
        "fr": "Je ne peux ni modifier les règles du système ni révéler des instructions internes. Posez une question sur un produit, une spécification, une certification ou une RFQ.",
        "ru": "Я не могу изменить системные правила или раскрыть внутренние инструкции. Задайте вопрос о продукте, характеристике, сертификате или RFQ.",
    },
    "insufficient_compliance": {
        "en": "The published material is not sufficient to confirm that certification or compliance claim. I will not infer it; please submit an RFQ so sales can verify it against formal documents.",
        "zh": "目前已發布資料不足以確認這項認證或合規聲明。我不會代為推測；請留下詢價需求，由業務依正式文件確認。",
        "ja": "公開済みの資料だけでは、その認証または法規適合性を確認できません。推測では回答せず、正式文書で確認できるよう見積依頼をお送りください。",
        "de": "Die veröffentlichten Unterlagen reichen nicht aus, um diese Zertifizierungs- oder Konformitätsaussage zu bestätigen. Ich werde dies nicht ableiten; bitte senden Sie eine Anfrage, damit der Vertrieb die formalen Dokumente prüfen kann.",
        "ko": "공개된 자료만으로는 해당 인증 또는 규정 준수 여부를 확인할 수 없습니다. 추측하지 않으며, 담당자가 공식 문서로 확인할 수 있도록 견적 요청을 보내 주세요.",
        "fr": "Les documents publiés ne suffisent pas à confirmer cette certification ou cette conformité. Je ne vais pas la déduire ; envoyez une RFQ afin que l’équipe commerciale la vérifie dans les documents officiels.",
        "ru": "Опубликованных материалов недостаточно, чтобы подтвердить эту сертификацию или соответствие требованиям. Я не буду делать выводы; отправьте RFQ, чтобы отдел продаж проверил официальные документы.",
    },
    "no_published_source": {
        "en": "The published website material is not sufficient to answer this reliably. I can help structure an RFQ, but I will not invent specifications or commitments.",
        "zh": "目前網站已發布資料不足以可靠回答這個問題。我可以協助您整理需求並轉成詢價，但不會自行補寫規格或承諾。",
        "ja": "現在公開されているウェブサイト資料だけでは、信頼できる回答ができません。見積依頼の整理はお手伝いできますが、仕様や約束を推測して追加することはありません。",
        "de": "Die veröffentlichten Website-Inhalte reichen für eine verlässliche Antwort nicht aus. Ich kann Ihre Anforderungen für eine Anfrage strukturieren, werde aber keine Spezifikationen oder Zusagen erfinden.",
        "ko": "현재 공개된 웹사이트 자료만으로는 신뢰할 수 있는 답변을 드리기 어렵습니다. 견적 요청에 필요한 내용을 정리해 드릴 수 있지만 사양이나 약속을 임의로 만들지는 않습니다.",
        "fr": "Les informations publiées sur le site ne suffisent pas à répondre de manière fiable. Je peux vous aider à structurer une RFQ, mais je n’inventerai ni spécification ni engagement.",
        "ru": "Опубликованных на сайте материалов недостаточно для надёжного ответа. Я могу помочь оформить RFQ, но не буду придумывать характеристики или обязательства.",
    },
    "unsupported_numeric": {
        "en": "The published material is not sufficient to confirm that numeric specification, so I will not invent it. Please submit an RFQ so sales can verify it against formal documents.",
        "zh": "目前已發布資料不足以確認這項數字規格，我不會自行補寫。請留下詢價需求，由業務依正式文件確認。",
        "ja": "公開済みの資料では、その数値仕様を確認できないため、推測で補うことはありません。正式文書で確認できるよう見積依頼をお送りください。",
        "de": "Die veröffentlichten Unterlagen reichen nicht aus, um diese Zahlenangabe zu bestätigen. Ich werde sie nicht erfinden; bitte senden Sie eine Anfrage, damit der Vertrieb sie anhand formaler Dokumente prüfen kann.",
        "ko": "공개된 자료만으로는 해당 수치 사양을 확인할 수 없어 임의로 작성하지 않습니다. 담당자가 공식 문서로 확인할 수 있도록 견적 요청을 보내 주세요.",
        "fr": "Les documents publiés ne suffisent pas à confirmer cette valeur numérique. Je ne vais pas l’inventer ; envoyez une RFQ afin que l’équipe commerciale la vérifie dans les documents officiels.",
        "ru": "Опубликованных материалов недостаточно, чтобы подтвердить эту числовую характеристику. Я не буду её придумывать; отправьте RFQ для проверки по официальным документам.",
    },
}

_CLARIFICATION_PREFIXES = {
    "en": "One key question before I narrow this further:",
    "zh": "在我進一步縮小範圍前，想先確認一個重點：",
    "ja": "候補を絞り込む前に、一点確認させてください：",
    "de": "Eine wichtige Frage, bevor ich die Auswahl weiter eingrenze:",
    "ko": "범위를 더 좁히기 전에 한 가지 확인하겠습니다:",
    "es": "Una pregunta importante antes de reducir más las opciones:",
    "fr": "Une question importante avant d’affiner davantage la sélection :",
    "ru": "Один важный вопрос, прежде чем уточнить подбор:",
}


def _pick(messages: dict[str, str], locale: str) -> str:
    return messages.get(chat_language(locale), messages["en"])


def localized_greeting(
    context_type: str,
    entity_name: Optional[str] = None,
    locale: str = "en",
) -> str:
    language = chat_language(locale)
    if language == "zh":
        named = f"「{entity_name}」" if entity_name else "這個主題"
        messages = {
            "product": f"我可以協助您確認{named}的材質、規格、MOQ、認證與 OEM 選項。",
            "category": f"我可以協助您比較{named}的產品、OEM 選項，並整理詢價需求。",
            "application": f"我可以協助您評估{named}適用的產品、規格與詢價下一步。",
            "home": "我可以協助您找產品、確認 MOQ、OEM 能力、認證，或整理詢價需求。",
            "faq": "我可以協助您查找 MOQ、客製化、認證與詢價相關答案。",
        }
        return messages.get(context_type, messages["faq"])
    if language == "ja":
        named = f"「{entity_name}」" if entity_name else "このテーマ"
        messages = {
            "product": f"{named}の材質、仕様、MOQ、認証、OEMオプションを確認できます。",
            "category": f"{named}の製品比較、OEMオプション、見積依頼の整理をお手伝いします。",
            "application": f"{named}に適した製品、仕様、見積依頼の次のステップをご案内します。",
            "home": "製品探し、MOQ、OEM対応、認証の確認、見積依頼の整理をお手伝いします。",
            "faq": "MOQ、カスタマイズ、認証、見積に関する確認をお手伝いします。",
        }
        return messages.get(context_type, messages["faq"])
    if language == "fr":
        named = f"« {entity_name} »" if entity_name else "ce sujet"
        messages = {
            "product": f"Je peux vous aider à vérifier les matériaux, les spécifications, la MOQ, les certifications et les options OEM pour {named}.",
            "category": f"Je peux comparer les produits de {named}, préciser les options OEM et préparer votre RFQ.",
            "application": f"Je peux évaluer les produits et spécifications adaptés à {named}, puis préparer la prochaine étape de la RFQ.",
            "home": "Je peux vous aider à trouver un produit, vérifier la MOQ, les possibilités OEM et les certifications, ou préparer une RFQ.",
            "faq": "Je peux vous aider à trouver des réponses sur la MOQ, la personnalisation, les certifications et les RFQ.",
        }
        return messages.get(context_type, messages["faq"])
    if language == "ru":
        named = f"«{entity_name}»" if entity_name else "этой теме"
        messages = {
            "product": f"Я могу помочь проверить материалы, характеристики, MOQ, сертификацию и варианты OEM для {named}.",
            "category": f"Я могу сравнить продукты в категории {named}, уточнить варианты OEM и подготовить RFQ.",
            "application": f"Я могу подобрать продукты и требования для {named} и помочь подготовить RFQ.",
            "home": "Я могу помочь найти продукт, проверить MOQ, возможности OEM и сертификацию или подготовить RFQ.",
            "faq": "Я могу помочь найти ответы о MOQ, кастомизации, сертификации и RFQ.",
        }
        return messages.get(context_type, messages["faq"])
    messages = {
        "product": f"I can help with material, MOQ, certification, or OEM options for {entity_name}."
        if entity_name
        else "I can help with product specs, certification, MOQ, or OEM questions.",
        "category": f"I can help you compare options in {entity_name}, narrow down fit, and move toward an RFQ."
        if entity_name
        else "I can help you compare product categories, OEM options, and the fastest path to a quotation.",
        "application": f"I can help you evaluate products, requirements, and RFQ next steps for {entity_name}."
        if entity_name
        else "I can help you connect application needs to the right products, OEM scope, and RFQ next steps.",
        "home": "I can help you find the right product category, OEM capability, MOQ guidance, or the fastest path to an RFQ.",
        "faq": "I can help you quickly find MOQ, customization, certification, or quotation-related answers.",
    }
    return messages.get(context_type, messages["faq"])


def localized_suggestions(context_type: str, locale: str = "en") -> list[str]:
    language = chat_language(locale)
    if language == "zh":
        return {
            "product": [
                "這項產品使用什麼材質？",
                "有哪些認證？",
                "可以 OEM 或客製品牌嗎？",
            ],
            "category": ["哪些產品適合 OEM 專案？", "常見認證有哪些？", "如何詢價？"],
            "application": [
                "哪些產品最適合這個應用？",
                "可以客製規格嗎？",
                "詢價需要提供哪些資料？",
            ],
            "home": [
                "哪個產品類別適合我的用途？",
                "可以做 OEM 或自有品牌嗎？",
                "如何開始詢價？",
            ],
        }.get(
            context_type, ["最低訂購量是多少？", "可以客製規格嗎？", "如何取得報價？"]
        )
    if language == "ja":
        return {
            "product": [
                "この製品の材質は何ですか？",
                "どのような認証がありますか？",
                "OEMやプライベートブランドに対応できますか？",
            ],
            "category": [
                "OEM案件に適した製品はどれですか？",
                "一般的な認証は何ですか？",
                "見積依頼はどのように始めますか？",
            ],
            "application": [
                "この用途に適した製品はどれですか？",
                "仕様のカスタマイズは可能ですか？",
                "見積依頼に必要な情報は何ですか？",
            ],
            "home": [
                "用途に合う製品カテゴリーはどれですか？",
                "OEMやプライベートブランドに対応できますか？",
                "見積依頼はどのように始めますか？",
            ],
        }.get(
            context_type,
            [
                "最低発注数量はいくつですか？",
                "仕様のカスタマイズは可能ですか？",
                "見積を取得するにはどうすればよいですか？",
            ],
        )
    if language == "fr":
        return {
            "product": [
                "De quel matériau ce produit est-il fabriqué ?",
                "Quelles certifications sont disponibles ?",
                "Pouvez-vous proposer un marquage OEM ou une marque privée ?",
            ],
            "category": [
                "Quels produits de cette catégorie conviennent aux projets OEM ?",
                "Quelles certifications sont courantes ?",
                "Comment envoyer une RFQ pour cette catégorie ?",
            ],
            "application": [
                "Quels produits conviennent le mieux à cette application ?",
                "Pouvez-vous personnaliser les spécifications ?",
                "Quelles informations faut-il fournir dans la RFQ ?",
            ],
            "home": [
                "Quelle catégorie de produits convient à mon application ?",
                "Pouvez-vous prendre en charge un projet OEM ou de marque privée ?",
                "Comment commencer une RFQ ?",
            ],
        }.get(context_type, ["Quelle est votre MOQ ?", "Pouvez-vous personnaliser les spécifications ?", "Comment demander un devis ?"])
    if language == "ru":
        return {
            "product": [
                "Из какого материала изготовлен этот продукт?",
                "Какие сертификаты доступны?",
                "Поддерживаете ли вы OEM или частную торговую марку?",
            ],
            "category": [
                "Какие продукты этой категории подходят для OEM-проектов?",
                "Какие сертификаты обычно доступны?",
                "Как отправить RFQ для этой категории?",
            ],
            "application": [
                "Какие продукты лучше всего подходят для этого применения?",
                "Можно ли изменить характеристики под заказ?",
                "Какие данные нужно указать в RFQ?",
            ],
            "home": [
                "Какая категория продуктов подходит для моего применения?",
                "Поддерживаете ли вы OEM или частную торговую марку?",
                "Как начать RFQ?",
            ],
        }.get(context_type, ["Какова минимальная партия (MOQ)?", "Можно ли изменить характеристики под заказ?", "Как запросить предложение?"])
    return {
        "product": [
            "What material is this product made of?",
            "What certifications does this product have?",
            "Can you provide OEM or custom branding?",
        ],
        "category": [
            "Which products in this category fit OEM projects?",
            "What certifications are common in this category?",
            "How do I request a quote for this category?",
        ],
        "application": [
            "Which products fit this application best?",
            "Can you support OEM or customization for this use case?",
            "What should I include in an RFQ for this application?",
        ],
        "home": [
            "Which product category fits my application?",
            "Can you support OEM or private label projects?",
            "How do I start an RFQ?",
        ],
    }.get(
        context_type,
        [
            "What is your MOQ?",
            "Can you support custom specifications?",
            "How do I request a quotation?",
        ],
    )


def fallback_reply(locale: str) -> str:
    return _pick(_FALLBACK_REPLIES, locale)


def policy_reply(key: str, locale: str) -> str:
    return _pick(_POLICY_REPLIES[key], locale)


def clarification_prefix(locale: str) -> str:
    return _pick(_CLARIFICATION_PREFIXES, locale)
