"""
Translator service unit tests — no DB, no network.

Covers:
- load_glossary parsing (valid / empty / malformed payloads)
- translate_fields whitelisting and error mapping (LLM mocked)
- translate_specifications value-only localization (LLM mocked)

Run: pytest tests/test_translator.py -v
"""
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.translator import (
    TranslationError,
    load_glossary,
    translate_fields,
    translate_specifications,
)


# ── load_glossary ─────────────────────────────────────────────────────────────

def test_load_glossary_valid():
    raw = json.dumps([
        {"source": "Chrome Vanadium", "target": "鉻釩鋼", "note": "材料"},
        {"source": "Ratchet", "target": "棘輪"},
    ])
    entries = load_glossary(raw)
    assert entries == [
        {"source": "Chrome Vanadium", "target": "鉻釩鋼", "note": "材料"},
        {"source": "Ratchet", "target": "棘輪", "note": ""},
    ]


def test_load_glossary_empty_and_none():
    assert load_glossary(None) == []
    assert load_glossary("") == []
    assert load_glossary("[]") == []


def test_load_glossary_malformed():
    assert load_glossary("{not json") == []
    assert load_glossary('{"dict": true}') == []
    # Entries missing source/target are dropped
    raw = json.dumps([{"source": "A"}, {"target": "B"}, {"source": "C", "target": "丙"}])
    assert load_glossary(raw) == [{"source": "C", "target": "丙", "note": ""}]


# ── translate_fields ─────────────────────────────────────────────────────────

def _mock_llm_response(payload: dict):
    return _mock_llm_response_raw(json.dumps(payload, ensure_ascii=False))


def _mock_llm_response_raw(content: str):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    return resp


@pytest.mark.asyncio
async def test_translate_fields_whitelists_and_translates():
    with patch("app.services.translator.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response({"product_name": "棘輪扳手", "hacked": "x"})
        )
        result = await translate_fields(
            "product",
            {
                "product_name": "Ratchet Wrench",
                "slug": "ratchet-wrench",        # not translatable — excluded from LLM payload
                "model_number": "RW-100",        # not translatable
                "full_description": "",          # empty — excluded
            },
            "zh-tw",
            [{"source": "Ratchet", "target": "棘輪", "note": ""}],
        )
    assert result == {"product_name": "棘輪扳手"}

    # LLM 只收到白名單內的非空欄位
    sent = mock_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "Ratchet Wrench" in sent
    assert "RW-100" not in sent
    assert "ratchet-wrench" not in sent


@pytest.mark.asyncio
async def test_translate_fields_rejects_unsupported_locale():
    with pytest.raises(TranslationError):
        await translate_fields("product", {"product_name": "x"}, "fr")


@pytest.mark.asyncio
async def test_translate_fields_llm_failure_raises_translation_error():
    with patch("app.services.translator.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))
        with pytest.raises(TranslationError):
            await translate_fields("faq", {"question": "Q?", "answer": "A."}, "zh-tw")


@pytest.mark.asyncio
async def test_translate_fields_empty_payload_skips_llm():
    with patch("app.services.translator.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock()
        result = await translate_fields("faq", {"question": "  ", "answer": ""}, "zh-tw")
    assert result == {}
    mock_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_translate_fields_non_object_json_raises_translation_error():
    # Some providers may return a JSON array/scalar despite
    # response_format=json_object — must surface as 502-mappable error, not 500.
    with patch("app.services.translator.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response_raw('["not", "an", "object"]')
        )
        with pytest.raises(TranslationError):
            await translate_fields("faq", {"question": "Q?"}, "zh-tw")


# ── translate_specifications ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_translate_specifications_translates_values_only():
    specs = json.dumps([
        {"name": "Material", "value": "Chrome Vanadium Steel", "unit": ""},
        {"name": "Length", "value": "250", "unit": "mm"},
    ])
    with patch("app.services.translator.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response({"0": "鉻釩鋼", "1": "250"})
        )
        out = json.loads(await translate_specifications(specs, "zh-tw"))
    assert out[0] == {"name": "Material", "value": "鉻釩鋼", "unit": ""}
    assert out[1] == {"name": "Length", "value": "250", "unit": "mm"}


@pytest.mark.asyncio
async def test_translate_specifications_passthrough_on_bad_input():
    assert await translate_specifications("not json", "zh-tw") == "not json"
    assert await translate_specifications("[]", "zh-tw") == "[]"
