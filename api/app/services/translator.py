"""
Translation Draft Service — LLM-assisted locale drafting for content entities.

Given a source entity (e.g. an English Product) and a target locale
(e.g. zh-TW), produces a *draft* of the translatable fields. The result is
never auto-saved: the admin reviews the draft in the form and saves manually.

Design rules:
- Only whitelisted text fields are translated; slugs, model numbers, URLs,
  status, and relations are never touched.
- A per-tenant glossary (SiteProfile.translation_glossary_json) pins B2B
  terminology so translations stay consistent across the catalog.
- Failures raise TranslationError; the endpoint maps it to 502 so the UI can
  show a retry-able error instead of a silent empty form.
"""
import json
import logging
from typing import Any, Optional

from app.core.config import settings
from app.core.tracing import get_openai_client, chat_completion_kwargs, WorkflowType, observe_workflow

logger = logging.getLogger(__name__)
client = get_openai_client()

SOURCE_LOCALE = "en"
SUPPORTED_TARGETS: dict[str, str] = {
    "zh-tw": "Traditional Chinese (Taiwan, 繁體中文)",
}

# Fields the LLM may translate, per entity type. Anything not listed is copied
# verbatim by the endpoint (or left blank, per form defaults).
TRANSLATABLE_FIELDS: dict[str, list[str]] = {
    "product": [
        "product_name", "short_description", "full_description",
        "seo_title", "seo_description", "image_alt",
    ],
    "category": ["category_name", "description", "seo_title", "seo_description"],
    "application": [
        "application_name", "industry", "description", "challenge", "solution",
        "seo_title", "seo_description",
    ],
    "faq": ["question", "answer"],
    "certification": ["cert_name", "description"],
    "capability": ["capability_name", "short_description", "detail"],
    "comparison": ["topic_title", "summary", "conclusion"],
    "page": ["title", "subtitle", "body", "seo_title", "seo_description"],
    "cta": ["headline", "subheadline", "button_label"],
}

# Product specifications is a JSON string [{name, value, unit}]. Names/units
# stay as-is (engineering terms); only `value` strings may be localized when
# they contain prose (e.g. "Chrome plated" → "鍍鉻").

SYSTEM_PROMPT = """You are a professional technical translator for a B2B export manufacturer \
(hand tools / industrial hardware). Translate the given English content into \
{target_language} for international buyers.

Rules:
- Preserve technical accuracy. Model numbers, standards (ISO, DIN, ANSI, JIS), \
material grades, measurements, and units stay untranslated.
- Use natural business {target_language}, not literal machine translation. \
Keep the tone professional and specification-focused.
- HTML tags in rich-text fields must be preserved exactly; only translate the text nodes.
- SEO titles ≤ 60 characters where possible; SEO descriptions ≤ 155 characters.
- Honor the glossary below for terminology consistency.

Glossary (source → required translation):
{glossary}

Return valid JSON only: an object with the SAME keys as the input fields object, \
values translated. Do not add, remove, or rename keys."""


class TranslationError(Exception):
    """LLM translation failed — the UI should surface this and allow retry."""


def load_glossary(raw: Optional[str]) -> list[dict[str, str]]:
    """Parse SiteProfile.translation_glossary_json → [{source, target, note?}]."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [
        {"source": str(g["source"]), "target": str(g["target"]), "note": str(g.get("note", ""))}
        for g in data
        if isinstance(g, dict) and g.get("source") and g.get("target")
    ]


def _glossary_block(glossary: list[dict[str, str]]) -> str:
    if not glossary:
        return "(empty — use standard industry terminology)"
    lines = [f"- {g['source']} → {g['target']}" + (f"  ({g['note']})" if g["note"] else "") for g in glossary[:200]]
    return "\n".join(lines)


@observe_workflow(WorkflowType.TRANSLATE)
async def translate_fields(
    entity_type: str,
    fields: dict[str, Any],
    target_locale: str,
    glossary: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """
    Translate whitelisted fields for one entity.

    Args:
        entity_type: key of TRANSLATABLE_FIELDS (product, faq, ...)
        fields: {field_name: source_text} — only translatable, non-empty fields
        target_locale: e.g. "zh-tw"
        glossary: tenant glossary entries

    Returns dict with the same keys, translated values.
    Raises TranslationError on LLM/parse failure.
    """
    if target_locale not in SUPPORTED_TARGETS:
        raise TranslationError(f"Unsupported target locale: {target_locale}")
    allowed = set(TRANSLATABLE_FIELDS.get(entity_type, []))
    payload = {k: v for k, v in fields.items() if k in allowed and isinstance(v, str) and v.strip()}
    if not payload:
        return {}

    target_language = SUPPORTED_TARGETS[target_locale]
    prompt = (
        f"Entity type: {entity_type}\n"
        f"Translate these fields (JSON object):\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.AI_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(
                        target_language=target_language,
                        glossary=_glossary_block(glossary or []),
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            **chat_completion_kwargs(temperature=0.3, max_output_tokens=4000),
        )
        result = json.loads(resp.choices[0].message.content)
    except TranslationError:
        raise
    except Exception as e:
        logger.error("Translation draft failed (%s → %s): %s", entity_type, target_locale, e)
        raise TranslationError(str(e)) from e

    if not isinstance(result, dict):
        logger.error("Translation draft returned non-object JSON: %r", result)
        raise TranslationError("LLM 回傳格式異常（非 JSON object）")

    # Keep only keys we asked for; coerce values to str
    return {k: (str(result[k]) if result.get(k) is not None else v) for k, v in payload.items()}


async def translate_specifications(
    specifications: str,
    target_locale: str,
    glossary: Optional[list[dict[str, str]]] = None,
) -> str:
    """
    Translate the `value` prose of a product specifications JSON string.

    Spec names and units are engineering vocabulary and stay untouched.
    Returns the original string unchanged if it is not a valid spec array
    or there is nothing prose-like to translate.
    """
    try:
        specs = json.loads(specifications)
    except (TypeError, json.JSONDecodeError):
        return specifications
    if not isinstance(specs, list) or not specs:
        return specifications

    values = [s.get("value", "") for s in specs if isinstance(s, dict)]
    if not any(isinstance(v, str) and v.strip() for v in values):
        return specifications

    try:
        resp = await client.chat.completions.create(
            model=settings.AI_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(
                        target_language=SUPPORTED_TARGETS[target_locale],
                        glossary=_glossary_block(glossary or []),
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Translate these specification VALUES (JSON object of index → text). "
                        "Keep numbers, tolerances, standards, and units as-is:\n"
                        + json.dumps({str(i): v for i, v in enumerate(values)}, ensure_ascii=False)
                    ),
                },
            ],
            response_format={"type": "json_object"},
            **chat_completion_kwargs(temperature=0.2, max_output_tokens=2000),
        )
        translated = json.loads(resp.choices[0].message.content)
    except Exception as e:
        logger.error("Spec translation failed: %s", e)
        raise TranslationError(str(e)) from e

    if not isinstance(translated, dict):
        logger.error("Spec translation returned non-object JSON: %r", translated)
        raise TranslationError("LLM 回傳格式異常（非 JSON object）")

    out = []
    for i, s in enumerate(specs):
        if not isinstance(s, dict):
            out.append(s)
            continue
        new_val = translated.get(str(i))
        out.append({**s, "value": str(new_val) if new_val else s.get("value", "")})
    return json.dumps(out, ensure_ascii=False)
