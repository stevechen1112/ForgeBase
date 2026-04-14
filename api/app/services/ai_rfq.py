"""
AI RFQ Analysis & Reply Draft Service  (3.1.1 + 3.1.2)

Analyzes incoming RFQ requests using AI to:
- Extract key requirements and match with catalog
- Classify urgency level and match confidence
- Generate professional draft reply email
"""
import json
import logging
from typing import Any

from app.core.config import settings
from app.core.tracing import get_openai_client, WorkflowType, observe_workflow, attach_trace_metadata

logger = logging.getLogger(__name__)
client = get_openai_client()

# ── Prompts ────────────────────────────────────────────────────────────────────

ANALYSIS_SYSTEM = """You are an expert B2B industrial sales assistant for an export manufacturer.
Analyze incoming RFQ (Request for Quotation) requests and extract structured insights for the sales team.
Always output valid JSON. Be concise and actionable. Do not invent information not present in the RFQ.
Focus on what matters most for closing the deal."""

REPLY_SYSTEM = """You are an experienced B2B sales manager writing professional reply emails to RFQs.
Write in a professional, warm, and competent tone.
- Acknowledge receipt and confirm understanding of the request
- Confirm which products/items you can fulfill
- Politely request any missing critical information (dimensions, quantity, standard, etc.)
- Set clear next steps and expected timeline
Output valid JSON only."""


# ── 3.1.1 AI RFQ Analysis ─────────────────────────────────────────────────────

async def analyze_rfq(
    rfq_data: dict[str, Any],
    products: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Analyze RFQ and return structured insights for the sales team.

    Args:
        rfq_data: Form data dict (full_name, company_name, message, specs, timeline, etc.)
        products: List of product dicts from catalog (id, model_number, name, description)

    Returns dict with keys:
        match_score, urgency_level, key_requirements, matched_products,
        unmet_requirements, recommended_actions, summary, language_detected
    """
    products_ctx = json.dumps(
        [
            {
                "id": p.get("id"),
                "model_number": p.get("model_number"),
                "name": p.get("name"),
                "description": (p.get("description") or "")[:200],
            }
            for p in products[:20]
        ],
        ensure_ascii=False,
    )

    prompt = f"""
Analyze this RFQ and return structured insights.

── RFQ Details ──
Customer: {rfq_data.get("full_name")} / Company: {rfq_data.get("company_name", "N/A")}
Country: {rfq_data.get("country", "N/A")} | Job Title: {rfq_data.get("job_title", "N/A")}
Product IDs requested: {rfq_data.get("product_ids", [])}
Application: {rfq_data.get("application_id", "N/A")}
Quantity: {rfq_data.get("quantity", "N/A")} | Timeline: {rfq_data.get("timeline", "N/A")}
Specifications: {rfq_data.get("specifications", "N/A")}
Message: {rfq_data.get("message", "N/A")}
Intent score at submission: {rfq_data.get("intent_score_at_submit", 0)}

── Available Catalog Products ──
{products_ctx}

Return JSON with this exact schema:
{{
  "match_score": <integer 0-100>,
  "urgency_level": "<low|medium|high|critical>",
  "key_requirements": [<list of extracted requirement strings, max 5>],
  "matched_products": [
    {{
      "product_id": "<uuid string>",
      "model_number": "<string>",
      "match_reason": "<one-sentence reason>"
    }}
  ],
  "unmet_requirements": [<requirements we may not be able to fulfill, empty if none>],
  "recommended_actions": [<action items for sales team, max 3 strings>],
  "summary": "<2-sentence executive summary>",
  "language_detected": "<ISO 639 language code of the inquiry message>"
}}"""

    try:
        resp = await client.chat.completions.create(
            model=settings.AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": ANALYSIS_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1000,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        logger.error(f"AI RFQ analysis failed: {e}")
        return {
            "match_score": 50,
            "urgency_level": "medium",
            "key_requirements": [],
            "matched_products": [],
            "unmet_requirements": [],
            "recommended_actions": ["Manual review required — AI analysis unavailable"],
            "summary": "AI analysis is currently unavailable. Please review the RFQ manually.",
            "language_detected": "en",
        }


# ── 3.1.2 AI RFQ Reply Draft ──────────────────────────────────────────────────

async def generate_rfq_reply_draft(
    rfq_data: dict[str, Any],
    analysis: dict[str, Any],
    company_name: str = "Our Company",
    sender_name: str = "Sales Team",
) -> dict[str, Any]:
    """
    Generate a professional draft reply email for a given RFQ.

    Returns dict with: subject, body, language
    """
    lang = analysis.get("language_detected", "en")
    lang_instruction = {
        "zh-tw": "Reply in Traditional Chinese (繁體中文). Keep it professional and formal.",
        "zh-cn": "Reply in Simplified Chinese (简体中文). Keep it professional and formal.",
        "ja": "Reply in Japanese (日本語). Use appropriate business keigo.",
        "ko": "Reply in Korean (한국어). Use formal business tone.",
        "de": "Reply in German (Deutsch). Use formal business tone.",
    }.get(lang, "Reply in English. Use professional B2B sales tone.")

    matched = analysis.get("matched_products", [])
    can_fulfill = len(matched) > 0
    match_score = analysis.get("match_score", 0)

    prompt = f"""
{lang_instruction}

Write a professional B2B reply email to this RFQ.

── RFQ Summary ──
Customer: {rfq_data.get("full_name")} ({rfq_data.get("company_name", "N/A")}, {rfq_data.get("country", "N/A")})
Original request: {rfq_data.get("message", "")[:500]}
Products requested: {rfq_data.get("quantity", "N/A")} units | Timeline: {rfq_data.get("timeline", "N/A")}
Specifications: {rfq_data.get("specifications", "N/A")}

── AI Analysis Results ──
Match score: {match_score}% | Urgency: {analysis.get("urgency_level", "medium")}
Can we fulfill: {"Yes" if can_fulfill else "Partially/No"}
Matched products: {[p["model_number"] for p in matched]}
Unmet requirements: {analysis.get("unmet_requirements", [])}
Recommended actions: {analysis.get("recommended_actions", [])}

── Sender Info ──
Company: {company_name}
Sender: {sender_name}

Write an email that:
1. Warmly acknowledges receipt, references their company/product briefly
2. Confirms our capabilities (or partial match)
3. Requests any missing critical details if needed
4. States clear next steps (e.g., "We'll prepare a quotation within X business days")
5. Ends with professional sign-off

Return JSON:
{{
  "subject": "<email subject line>",
  "body": "<full email body with proper paragraph spacing>",
  "language": "{lang}"
}}"""

    try:
        resp = await client.chat.completions.create(
            model=settings.AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": REPLY_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=1500,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        logger.error(f"AI draft reply failed: {e}")
        customer = rfq_data.get("full_name", "Customer")
        return {
            "subject": f"Re: Your RFQ Inquiry — {rfq_data.get('company_name', '').strip()}",
            "body": (
                f"Dear {customer},\n\n"
                "Thank you for your inquiry. We have received your request and our team is reviewing the details.\n\n"
                "We will get back to you with a quotation as soon as possible.\n\n"
                f"Best regards,\n{sender_name}\n{company_name}"
            ),
            "language": lang,
        }
