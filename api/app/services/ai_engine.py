"""
AI Content Generation Engine.

Supports multi-page-type prompts with structured JSON output.
Calls OpenAI (model set via AI_MODEL_NAME env var).
"""
import json
import logging
from typing import Any

from app.core.config import settings
from app.core.tracing import get_openai_client, WorkflowType, observe_workflow, attach_trace_metadata

logger = logging.getLogger(__name__)

client = get_openai_client()


# ── Page-type prompt templates ────────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """You are an expert B2B industrial content writer specializing in export manufacturers.
Write professional, accurate, SEO-optimized content for a manufacturer's website.
Always output valid JSON matching the requested schema exactly.
Use the provided brief and entity data — do not invent specifications."""

LOCALE_LANGUAGE_MAP: dict[str, str] = {
    "en": "English",
    "zh-tw": "Traditional Chinese (繁體中文)",
    "zh-cn": "Simplified Chinese (简体中文)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "de": "German (Deutsch)",
}


def _build_system_prompt(target_locale: str) -> str:
    if target_locale == "en" or target_locale not in LOCALE_LANGUAGE_MAP:
        return BASE_SYSTEM_PROMPT
    lang_name = LOCALE_LANGUAGE_MAP[target_locale]
    return (
        BASE_SYSTEM_PROMPT
        + f"\n\nIMPORTANT: Generate ALL textual content (titles, descriptions, body text, FAQ items) in {lang_name}. "
        "Only SEO fields (seo_title, seo_description) may optionally include the English model number or brand name."
    )


def _build_product_prompt(brief: dict[str, Any], product: dict[str, Any]) -> str:
    return f"""
Generate product page content based on the following:

## Content Brief
- Target audience: {brief.get("audience_persona", "B2B buyers")}
- Buyer stage: {brief.get("buyer_stage", "consideration")}
- Primary keyword: {brief.get("primary_keyword", "")}
- Secondary keywords: {brief.get("secondary_keywords", "")}
- Tone: {brief.get("tone", "professional")}
- Target word count: {brief.get("word_count_target", 800)}
- Notes: {brief.get("notes", "")}

## Product Data
- Name: {product.get("product_name", "")}
- Model number: {product.get("model_number", "")}
- Short description: {product.get("short_description", "")}
- Specifications: {product.get("specifications", "N/A")}

Output JSON with these exact keys:
{{
  "seo_title": "string (max 60 chars — include primary keyword near the front)",
  "seo_description": "string (max 155 chars — include primary keyword and an action phrase such as 'Get a quote', 'Download spec sheet', or 'Compare models')",
  "full_description": "string (Markdown, target {brief.get('word_count_target', 800)} words. REQUIRED structure: start the first paragraph with the primary keyword within the first 100 words; use at least one ## H2 heading that contains the primary keyword; use 2-3 additional ## H2 sections covering key specifications, typical use cases, and buyer benefits; use ### H3 sub-headings where appropriate)",
  "faq_suggestions": [
    {{"question": "string (must start with What / How / Why / Which / Can / Is — optimised for Google PAA)", "answer": "string"}}
  ],
  "internal_link_suggestions": [
    {{"anchor_text": "string", "target_slug": "string", "reason": "string"}}
  ],
  "cta_headline": "string",
  "cta_subheadline": "string"
}}
Provide 3-5 FAQ pairs and 2-4 internal link suggestions to related product, category, or application pages.
"""


def _build_application_prompt(brief: dict[str, Any], application: dict[str, Any]) -> str:
    return f"""
Generate application page content based on the following:

## Content Brief
- Target audience: {brief.get("audience_persona", "B2B buyers")}
- Buyer stage: {brief.get("buyer_stage", "consideration")}
- Primary keyword: {brief.get("primary_keyword", "")}
- Secondary keywords: {brief.get("secondary_keywords", "")}
- Tone: {brief.get("tone", "professional")}
- Target word count: {brief.get("word_count_target", 800)}
- Notes: {brief.get("notes", "")}

## Application Data
- Name: {application.get("application_name", "")}
- Industry: {application.get("industry", "")}
- Description: {application.get("description", "")}
- Challenge: {application.get("challenge", "")}
- Solution: {application.get("solution", "")}

Output JSON with these exact keys:
{{
  "seo_title": "string (max 60 chars — include primary keyword near the front)",
  "seo_description": "string (max 155 chars — include primary keyword and an action phrase such as 'Learn more', 'See how it works', or 'Request a sample')",
  "description": "string (Markdown overview, target {brief.get('word_count_target', 300)} words. Include the primary keyword in the first 100 words and at least one ## H2 heading containing the primary keyword)",
  "challenge": "string (Markdown, ~200 words. Use ## H2 heading for this section)",
  "solution": "string (Markdown, ~300 words. Use ## H2 heading for this section; weave in secondary keywords naturally)",
  "faq_suggestions": [
    {{"question": "string (must start with What / How / Why / Which / Can / Is — optimised for Google PAA)", "answer": "string"}}
  ],
  "internal_link_suggestions": [
    {{"anchor_text": "string", "target_slug": "string", "reason": "string"}}
  ]
}}
Provide 3-5 FAQ pairs and 2-3 internal link suggestions to related products or capability pages.
"""


def _build_faq_prompt(brief: dict[str, Any], context: dict[str, Any]) -> str:
    return f"""
Generate FAQ content based on the following:

## Content Brief
- Primary keyword: {brief.get("primary_keyword", "")}
- Target audience: {brief.get("audience_persona", "B2B buyers")}
- Tone: {brief.get("tone", "professional")}
- Notes: {brief.get("notes", "")}

## Context
{json.dumps(context, indent=2)}

Output JSON with these exact keys:
{{
  "faq_items": [
    {{"question": "string (MUST start with What / How / Why / Which / Can / Is / Does / Should — Google People Also Ask format)", "answer": "string (40-60 words, direct answer in first sentence, optimised for featured snippet)", "category_tag": "string"}}
  ]
}}
Provide 5-8 Q&A pairs. Vary the question starters; do not repeat the same opening word more than twice.
"""


def _build_comparison_prompt(brief: dict[str, Any], context: dict[str, Any]) -> str:
    return f"""
Generate competitive comparison content based on the following:

## Content Brief
- Primary keyword: {brief.get("primary_keyword", "")}
- Target audience: {brief.get("audience_persona", "B2B buyers")}
- Tone: {brief.get("tone", "professional")}
- Notes: {brief.get("notes", "")}

## Comparison Context
{json.dumps(context, indent=2)}

Output JSON with these exact keys:
{{
  "seo_title": "string (max 60 chars — include primary keyword near the front)",
  "seo_description": "string (max 155 chars — include primary keyword and a phrase like 'See the full comparison' or 'Find out which is right for you')",
  "summary": "string (Markdown overview, ~200 words. Include the primary keyword in the first 100 words)",
  "dimensions": [
    {{"label": "string (comparison dimension name)", "our_value": "string", "competitor_value": "string", "winner": "us | competitor | tie"}}
  ],
  "conclusion": "string (Markdown recommendation, ~150 words. Include a CTA phrase at the end)"
}}
Provide 4-6 comparison dimensions.
"""


def _build_category_prompt(brief: dict[str, Any], category: dict[str, Any]) -> str:
    return f"""
Generate product category page content based on the following:

## Content Brief
- Target audience: {brief.get("audience_persona", "B2B buyers")}
- Primary keyword: {brief.get("primary_keyword", "")}
- Secondary keywords: {brief.get("secondary_keywords", "")}
- Tone: {brief.get("tone", "professional")}
- Target word count: {brief.get("word_count_target", 600)}
- Notes: {brief.get("notes", "")}

## Category Data
- Name: {category.get("category_name", "")}
- Current description: {category.get("description", "None")}

Output JSON with these exact keys:
{{
  "seo_title": "string (max 60 chars — include primary keyword near the front)",
  "seo_description": "string (max 155 chars — include primary keyword and a phrase like 'Browse our range' or 'Request a quote')",
  "description": "string (Markdown overview, target {brief.get('word_count_target', 600)} words — explain what this product category is, who uses it, and why buyers should care. REQUIRED: include primary keyword in first 100 words; use at least two ## H2 headings; weave secondary keywords naturally)",
  "faq_suggestions": [
    {{"question": "string (must start with What / How / Why / Which / Can / Is — optimised for Google PAA)", "answer": "string (40-60 words)"}}
  ],
  "internal_link_suggestions": [
    {{"anchor_text": "string", "target_slug": "string", "reason": "string"}}
  ]
}}
Provide 3-5 FAQ pairs and 2-4 internal link suggestions to related category or product pages.
"""


def _build_certification_prompt(brief: dict[str, Any], certification: dict[str, Any]) -> str:
    return f"""
Generate certification page content based on the following:

## Content Brief
- Target audience: {brief.get("audience_persona", "B2B buyers, procurement managers")}
- Primary keyword: {brief.get("primary_keyword", "")}
- Tone: {brief.get("tone", "authoritative")}
- Notes: {brief.get("notes", "")}

## Certification Data
- Name: {certification.get("cert_name", "")}
- Issuer: {certification.get("issuer", "N/A")}
- Certificate number: {certification.get("cert_number", "N/A")}
- Description: {certification.get("description", "None")}

Output JSON with these exact keys:
{{
  "seo_title": "string (max 60 chars — include the certification name and primary keyword)",
  "seo_description": "string (max 155 chars — explain what the certification guarantees and include a phrase like 'View certified products' or 'Download certificate')",
  "description": "string (Markdown, 400-600 words — REQUIRED sections: (1) ## What is [cert name]? (explain the certification body and scope); (2) ## Why It Matters to Buyers (procurement, compliance, market access angle); (3) ## Standards and Requirements (key technical standards covered); (4) ## Our Certified Products (name the product types, with internal links placeholders [product name](slug)). Weave in secondary keywords naturally.)",
  "trust_points": ["string", "string", "string"],
  "faq_suggestions": [
    {{"question": "string (must start with What / How / Why / Which / Can / Is — optimised for Google PAA)", "answer": "string (40-60 words)"}}
  ]
}}
Provide 3-5 trust-building bullet points and 3-4 FAQ pairs.
"""



PAGE_TYPE_BUILDERS = {
    "product": _build_product_prompt,
    "application": _build_application_prompt,
    "faq": _build_faq_prompt,
    "comparison": _build_comparison_prompt,
    "category": _build_category_prompt,
    "certification": _build_certification_prompt,
}


# ── Core generation function ──────────────────────────────────────────────────

class AIGenerationError(Exception):
    pass


async def generate_content(
    page_type: str,
    brief: dict[str, Any],
    entity_data: dict[str, Any],
    *,
    target_locale: str = "en",
    max_retries: int = 2,
) -> dict[str, Any]:
    """
    Call the AI model and return parsed structured JSON output.

    Raises AIGenerationError on failure after retries.
    """
    builder = PAGE_TYPE_BUILDERS.get(page_type)
    if not builder:
        raise AIGenerationError(f"No prompt template for page_type='{page_type}'")

    user_prompt = builder(brief, entity_data)
    system_prompt = _build_system_prompt(target_locale)

    for attempt in range(1, max_retries + 2):
        try:
            response = await client.chat.completions.create(
                model=settings.AI_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            text = response.choices[0].message.content or "{}"
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("AI JSON parse error (attempt %d): %s", attempt, e)
            if attempt > max_retries:
                raise AIGenerationError(f"Failed to parse AI JSON after {max_retries + 1} attempts") from e
        except Exception as e:
            logger.error("AI API error (attempt %d): %s", attempt, e)
            if attempt > max_retries:
                raise AIGenerationError(f"AI API failed: {e}") from e

    raise AIGenerationError("Unreachable")
