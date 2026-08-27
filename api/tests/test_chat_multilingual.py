import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.core.locale import infer_message_locale, normalize_chat_locale
from app.schemas.chat import ChatMessageCreate, ChatSessionCreate, GeneratedChatPayload
from app.services.chat_grounding import apply_grounding_policy
from app.services.chat_locale import (
    fallback_reply,
    localized_greeting,
    localized_suggestions,
)
from app.services.chat_orchestrator import finalize_generated_chat_response
from app.services.chat_service import (
    ChatService,
    _build_system_prompt,
    _localized_public_path,
    _tenant_chat_copy,
)


@pytest.mark.parametrize(
    ("message", "fallback", "expected"),
    [
        ("こんにちは", "en", "ja"),
        ("この製品の最低発注数量を教えてください。", "en", "ja"),
        ("見積希望", "en", "ja"),
        ("Wie hoch ist die Mindestbestellmenge für dieses Produkt?", "en", "de"),
        ("이 제품의 최소 주문 수량은 얼마인가요?", "en", "ko"),
        ("¿Cuál es la cantidad mínima de pedido?", "en", "es"),
        ("Quel est le délai de livraison pour cette commande industrielle ?", "en", "fr"),
        ("Каков минимальный объём заказа для этого продукта?", "en", "ru"),
        ("MOQ 500", "ja", "ja"),
        ("你好，我想詢價", "en", "zh-TW"),
    ],
)
def test_message_language_detection(message: str, fallback: str, expected: str):
    assert infer_message_locale(message, fallback) == expected


def test_public_source_paths_follow_the_active_public_locale():
    assert _localized_public_path("/certifications/iso-9001", "en") == (
        "/certifications/iso-9001"
    )
    assert _localized_public_path("/certifications/iso-9001", "fr") == (
        "/fr/certifications/iso-9001"
    )
    assert _localized_public_path("/products", "ru-RU") == "/ru/products"


def test_chat_schema_preserves_response_language_outside_site_locales():
    session = ChatSessionCreate(visitor_id=uuid.uuid4(), locale="ja")
    message = ChatMessageCreate(
        visitor_id=uuid.uuid4(), content="Guten Tag", locale="de-DE"
    )
    assert session.locale == "ja"
    assert message.locale == "de-DE"
    assert normalize_chat_locale("ko_KR") == "ko-KR"


@pytest.mark.parametrize(
    ("model_value", "expected"),
    [
        ("request_quote", "rfq"),
        ("request-quotation", "rfq"),
        ("contact_sales", "contact"),
        ("unexpected", "none"),
    ],
)
def test_generated_chat_payload_normalizes_action_synonyms(
    model_value: str, expected: str
):
    payload = GeneratedChatPayload(reply="回答", suggested_action=model_value)
    assert payload.suggested_action == expected


def test_system_prompt_requires_latest_visitor_language_not_source_language():
    prompt = _build_system_prompt("ja")
    assert "same language as the latest visitor question" in prompt
    assert "detected language hint is ja" in prompt
    assert "Never switch to English" in prompt


@pytest.mark.asyncio
async def test_non_english_question_is_translated_only_for_knowledge_retrieval(
    monkeypatch,
):
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"query":"minimum order quantity OEM hand tools"}'
                    )
                )
            ]
        )
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(
        "app.services.chat_service.get_openai_client",
        lambda: client,
    )

    translated = await ChatService(SimpleNamespace())._translate_retrieval_query(
        "OEM工具の最低発注数量を教えてください。",
        "ja",
    )

    assert translated == "minimum order quantity OEM hand tools"
    request = create.await_args.kwargs
    assert "Do not answer the question" in request["messages"][0]["content"]
    assert "OEM工具" in request["messages"][1]["content"]


def test_japanese_fixed_copy_and_failure_fallback_do_not_switch_to_english():
    assert "製品" in localized_greeting("home", locale="ja")
    assert "見積" in " ".join(localized_suggestions("home", "ja"))
    reply = fallback_reply("ja")
    assert "確認済み" in reply
    assert "I don't" not in reply


@pytest.mark.parametrize(
    ("locale", "greeting_token", "fallback_token"),
    [("fr", "aider", "confirmées"), ("ru", "помочь", "Опубликован")],
)
def test_french_and_russian_fixed_copy_do_not_fall_back_to_english(
    locale: str, greeting_token: str, fallback_token: str
):
    assert greeting_token.casefold() in localized_greeting("home", locale=locale).casefold()
    assert len(localized_suggestions("home", locale)) == 3
    assert fallback_token.casefold() in fallback_reply(locale).casefold()


def test_english_tenant_copy_does_not_override_japanese_system_copy():
    site_copy = json.dumps(
        {
            "chat": {
                "greeting": "How may I help?",
                "suggestions": ["What is your MOQ?"],
            }
        }
    )

    greeting, suggestions = _tenant_chat_copy(site_copy, "ja-JP")

    assert greeting is None
    assert suggestions is None


def test_exact_tenant_language_copy_is_preserved():
    site_copy = json.dumps(
        {
            "chat": {
                "greeting": {"en": "How may I help?", "ja": "何をお探しですか？"},
                "suggestions": {
                    "en": ["What is your MOQ?"],
                    "ja": ["最低発注数量はいくつですか？"],
                },
            }
        }
    )

    greeting, suggestions = _tenant_chat_copy(site_copy, "ja-JP")

    assert greeting == "何をお探しですか？"
    assert suggestions == ["最低発注数量はいくつですか？"]


def test_grounding_safety_replies_follow_japanese_and_german():
    japanese = apply_grounding_policy(
        question="この製品について教えてください。",
        reply="回答",
        sources=[],
        locale="ja",
    )
    assert japanese.status == "limited"
    assert "公開" in japanese.reply
    assert "website material" not in japanese.reply

    german = apply_grounding_policy(
        question="Ist dieses Produkt zertifiziert?",
        reply="Ja.",
        sources=[],
        locale="de",
    )
    assert german.status == "limited"
    assert "veröffentlichten" in german.reply
    assert "published material" not in german.reply


@pytest.mark.parametrize(
    ("locale", "question", "token"),
    [
        ("fr", "Quel est le prix exact et le délai garanti ?", "RFQ"),
        ("ru", "Назовите точную цену и гарантированный срок поставки", "RFQ"),
    ],
)
def test_commercial_risk_degrades_in_public_site_languages(
    locale: str, question: str, token: str
):
    result = apply_grounding_policy(
        question=question,
        reply="guaranteed",
        sources=[{"type": "product", "id": str(uuid.uuid4()), "name": "Model", "url": "/products/model"}],
        locale=locale,
        evidence_texts=["Model X"],
    )
    assert result.status == "limited"
    assert "commercial_terms_require_sales_confirmation" in result.warnings
    assert token in result.reply


def test_japanese_rfq_clarification_stays_japanese():
    payload = finalize_generated_chat_response(
        user_question="OEMの見積をお願いします。",
        context_entity_type="product",
        recent_messages=[],
        payload={
            "reply": "OEMのお見積りに必要な条件を整理します。",
            "suggested_action": "rfq",
            "needs_clarification": True,
            "clarifying_question": "予定数量を教えていただけますか？",
        },
        locale="ja",
    )
    assert payload["suggested_action"] == "rfq"
    assert payload["needs_clarification"] is True
    assert "数量" in payload["clarifying_question"]
    assert "One key question" not in payload["reply"]
    assert not payload["clarifying_question"].endswith("？?")
