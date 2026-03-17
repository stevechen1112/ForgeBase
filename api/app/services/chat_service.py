import json
import logging
import re
import uuid
from typing import Any, Optional
from urllib.parse import urlencode

from openai import AsyncOpenAI
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.models.application import Application
from app.models.certification import Certification
from app.models.chat import ChatMessage, ChatSession
from app.models.faq_item import FAQItem
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.tracking_event import TrackingEvent
from app.models.tracking_session import TrackingSession
from app.models.visitor import Visitor
from app.services.chat_orchestrator import finalize_generated_chat_response
from app.services.chat_policy import infer_clarifying_question as _infer_clarifying_question
from app.services.chat_response_utils import (
    contains_any as _contains_any,
    has_quantity_signal as _has_quantity_signal,
    merge_reply_and_clarifying_question as _merge_reply_and_clarifying_question,
    normalize_question as _normalize_question,
)
from app.services.intent_scoring import calculate_score_delta, get_intent_stage

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def _product_greeting(product_name: Optional[str]) -> str:
    if product_name:
        return f"I can help with material, MOQ, certification, or OEM options for {product_name}."
    return "I can help with product specs, certification, MOQ, or OEM questions."


def _faq_greeting() -> str:
    return "I can help you quickly find MOQ, customization, certification, or quotation-related answers."


def _home_greeting() -> str:
    return "I can help you find the right product category, OEM capability, MOQ guidance, or the fastest path to an RFQ."


def _category_greeting(category_name: Optional[str]) -> str:
    if category_name:
        return f"I can help you compare options in {category_name}, narrow down fit, and move toward an RFQ."
    return "I can help you compare product categories, OEM options, and the fastest path to a quotation."


def _application_greeting(application_name: Optional[str]) -> str:
    if application_name:
        return f"I can help you evaluate products, requirements, and RFQ next steps for {application_name}."
    return "I can help you connect application needs to the right products, OEM scope, and RFQ next steps."


def _default_suggestions(context_entity_type: str) -> list[str]:
    if context_entity_type == "product":
        return [
            "What material is this product made of?",
            "What certifications does this product have?",
            "Can you provide OEM or custom branding?",
        ]
    if context_entity_type == "category":
        return [
            "Which products in this category fit OEM projects?",
            "What certifications are common in this category?",
            "How do I request a quote for this category?",
        ]
    if context_entity_type == "application":
        return [
            "Which products fit this application best?",
            "Can you support OEM or customization for this use case?",
            "What should I include in an RFQ for this application?",
        ]
    if context_entity_type == "home":
        return [
            "Which product category fits my application?",
            "Can you support OEM or private label projects?",
            "How do I start an RFQ?",
        ]
    return [
        "What is your MOQ?",
        "Can you support custom specifications?",
        "How do I request a quotation?",
    ]


def _safe_json_loads(value: Optional[str]) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _trim_text(value: Optional[str], max_chars: int = 800) -> str:
    if not value:
        return ""
    text = value.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _strip_html(value: Optional[str]) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", text).strip()


def _format_product_snapshot(product: Product, *, max_specs: int = 4) -> str:
    specs = _safe_json_loads(product.specifications)
    spec_parts: list[str] = []
    if isinstance(specs, list):
        for item in specs[:max_specs]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            value = str(item.get("value") or "").strip()
            unit = str(item.get("unit") or "").strip()
            joined_value = f"{value} {unit}".strip()
            if name and joined_value:
                spec_parts.append(f"{name}: {joined_value}")
    elif isinstance(specs, dict):
        for key, value in list(specs.items())[:max_specs]:
            spec_parts.append(f"{key}: {value}")

    spec_text = "; ".join(spec_parts) if spec_parts else "N/A"
    return (
        f"{product.product_name}"
        f" (model: {product.model_number}; "
        f"summary: {_trim_text(_strip_html(product.short_description), 140)}; "
        f"specs: {_trim_text(spec_text, 180)})"
    )


def _format_faq_snapshot(faq: FAQItem) -> str:
    return f"Q: {faq.question} A: {_trim_text(_strip_html(faq.answer), 220)}"


def _format_cert_snapshot(cert: Certification) -> str:
    issuer = cert.issuer or "Issuer not listed"
    return f"{cert.cert_name} ({issuer}): {_trim_text(_strip_html(cert.description), 160)}"


def _detect_handoff(user_question: str, reply: str) -> tuple[str, bool]:
    combined = f"{user_question} {reply}".lower()
    handoff_terms = [
        "quote",
        "quotation",
        "rfq",
        "price",
        "pricing",
        "moq",
        "oem",
        "custom",
        "branding",
        "private label",
        "lead time",
        "sample",
    ]
    if any(term in combined for term in handoff_terms):
        return "rfq", True
    return "none", False


def _build_handoff_prefill(
    question: str,
    context_entity_type: str,
    context_entity_id: Optional[uuid.UUID],
) -> dict[str, Any]:
    prefill: dict[str, Any] = {"message": question}
    if context_entity_type == "product" and context_entity_id:
        prefill["product_ids"] = [str(context_entity_id)]
    return prefill


def _build_rfq_prefill_url(prefill: dict[str, Any]) -> str:
    normalized: dict[str, str] = {}
    for key, value in prefill.items():
        if isinstance(value, list):
            normalized[key] = ",".join(str(item) for item in value)
        else:
            normalized[key] = str(value)
    return f"/rfq?{urlencode(normalized)}"


def _build_system_prompt() -> str:
    return (
        "You are the AI Product Advisor for a B2B manufacturer website.\n\n"
        "Your job is to help buyers understand product specifications, certifications, OEM capability, MOQ, and quotation process.\n\n"
        "Rules:\n"
        "1. Use only the supplied context.\n"
        "2. Never invent pricing, lead time, legal compliance, or unsupported claims.\n"
        "3. If information is missing, say it is not confirmed and suggest RFQ or contact.\n"
        "4. Keep answers concise, practical, and professional.\n"
        "5. If the buyer asks a broad category or application question without enough commercial detail, answer briefly and then ask exactly one clarifying question.\n"
        "6. Prioritize clarifying gaps in this order: program type (standard vs OEM/private label), quantity/MOQ, branding/packaging scope, market/compliance requirement.\n"
        "7. If the buyer shows clear purchase intent and the missing detail is small, keep moving toward RFQ while still asking one key clarification when useful.\n"
        "8. Always return valid JSON matching the requested schema."
    )


def _build_user_prompt(
    context_page: Optional[str],
    context_entity_type: str,
    entity_summary: str,
    faq_summary: str,
    cert_summary: str,
    recent_messages: list[ChatMessage],
    user_question: str,
) -> str:
    history_lines = [f"{message.role}: {message.content}" for message in recent_messages]
    history = "\n".join(history_lines) if history_lines else "None"
    return f"""
CURRENT PAGE:
{context_page or 'N/A'}

ENTITY TYPE:
{context_entity_type}

ENTITY DATA:
{entity_summary or 'N/A'}

RELATED FAQS:
{faq_summary or 'N/A'}

RELATED CERTIFICATIONS:
{cert_summary or 'N/A'}

RECENT CHAT HISTORY:
{history}

USER QUESTION:
{user_question}

If one key commercial detail is still missing, set needs_clarification=true and provide exactly one high-value clarifying_question.

Return JSON with keys:
{{
  "reply": "string",
  "needs_clarification": false,
  "clarifying_question": null,
  "suggested_action": "none",
  "handoff_reason": null,
  "prefill": {{}}
}}
"""


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _ensure_visitor_exists(self, visitor_id: uuid.UUID) -> None:
        visitor = await self.db.get(Visitor, visitor_id)
        if visitor is None:
            self.db.add(Visitor(visitor_id=visitor_id))
            await self.db.flush()

    async def _ensure_tracking_session_exists(
        self,
        *,
        session_id: Optional[uuid.UUID],
        visitor_id: uuid.UUID,
        page_url: Optional[str],
    ) -> None:
        if session_id is None:
            return

        tracking_session = await self.db.get(TrackingSession, session_id)
        if tracking_session is None:
            self.db.add(
                TrackingSession(
                    session_id=session_id,
                    visitor_id=visitor_id,
                    entry_page=page_url,
                    exit_page=page_url,
                )
            )
            await self.db.flush()

    async def create_session(
        self,
        *,
        visitor_id: uuid.UUID,
        session_id: Optional[uuid.UUID],
        context_page: Optional[str],
        context_entity_type: str,
        context_entity_id: Optional[uuid.UUID],
    ) -> tuple[ChatSession, str, list[str]]:
        product_name: Optional[str] = None
        category_name: Optional[str] = None
        application_name: Optional[str] = None
        if context_entity_type == "product" and context_entity_id:
            product = await self.db.get(Product, context_entity_id)
            if product:
                product_name = product.product_name
        elif context_entity_type == "category" and context_entity_id:
            category = await self.db.get(ProductCategory, context_entity_id)
            if category:
                category_name = category.category_name
        elif context_entity_type == "application" and context_entity_id:
            application = await self.db.get(Application, context_entity_id)
            if application:
                application_name = application.application_name

        await self._ensure_visitor_exists(visitor_id)
        await self._ensure_tracking_session_exists(
            session_id=session_id,
            visitor_id=visitor_id,
            page_url=context_page,
        )

        chat_session = ChatSession(
            visitor_id=visitor_id,
            session_id=session_id,
            context_page=context_page,
            context_entity_type=context_entity_type,
            context_entity_id=context_entity_id,
        )
        await self._record_tracking_event(
            visitor_id=visitor_id,
            session_id=session_id,
            event_name="chat_start",
            page_url=context_page,
            page_type=context_entity_type,
            page_id=context_entity_id,
            properties={
                "source": "chat_widget",
                "context_entity_type": context_entity_type,
            },
        )
        self.db.add(chat_session)
        await self.db.commit()
        await self.db.refresh(chat_session)

        if context_entity_type == "product":
            greeting = _product_greeting(product_name)
        elif context_entity_type == "category":
            greeting = _category_greeting(category_name)
        elif context_entity_type == "application":
            greeting = _application_greeting(application_name)
        elif context_entity_type == "home":
            greeting = _home_greeting()
        else:
            greeting = _faq_greeting()
        return chat_session, greeting, _default_suggestions(context_entity_type)

    async def answer_message(
        self,
        *,
        chat_session: ChatSession,
        content: str,
    ) -> dict[str, Any]:
        user_message = ChatMessage(
            chat_session_id=chat_session.id,
            role="user",
            content=content,
        )
        self.db.add(user_message)
        chat_session.message_count += 1
        chat_session.updated_at = utcnow_naive()
        self.db.add(chat_session)
        await self.db.commit()

        recent_messages = await self._get_recent_messages(chat_session.id)
        entity_summary, sources = await self._build_context(chat_session)
        faq_summary = self._build_faq_summary(sources)
        cert_summary = self._build_cert_summary(sources)

        payload = await self._generate_reply(
            context_page=chat_session.context_page,
            context_entity_type=chat_session.context_entity_type or "unknown",
            entity_summary=entity_summary,
            faq_summary=faq_summary,
            cert_summary=cert_summary,
            recent_messages=recent_messages,
            user_question=content,
        )

        payload = finalize_generated_chat_response(
            user_question=content,
            context_entity_type=chat_session.context_entity_type or "unknown",
            recent_messages=recent_messages,
            payload=payload,
        )

        reply = payload.get("reply") or "I don't have confirmed information for that yet. The fastest next step is to submit an RFQ or contact request."
        suggested_action = payload.get("suggested_action") or "none"
        needs_clarification = bool(payload.get("needs_clarification"))
        clarifying_question = _normalize_question(payload.get("clarifying_question"))
        handoff_prefill = payload.get("prefill") or {}
        if not handoff_prefill:
            handoff_prefill = _build_handoff_prefill(
                content,
                chat_session.context_entity_type or "unknown",
                chat_session.context_entity_id,
            )

        detected_action, handoff_ready = _detect_handoff(content, reply)
        if suggested_action == "none" and detected_action != "none":
            suggested_action = detected_action

        assistant_message = ChatMessage(
            chat_session_id=chat_session.id,
            role="assistant",
            content=reply,
            sources=json.dumps(sources) if sources else None,
        )
        self.db.add(assistant_message)
        chat_session.message_count += 1
        chat_session.updated_at = utcnow_naive()
        if suggested_action == "rfq":
            chat_session.status = "handoff_ready"
        self.db.add(chat_session)
        await self.db.commit()

        return {
            "reply": reply,
            "sources": sources,
            "suggested_action": suggested_action,
            "needs_clarification": needs_clarification,
            "clarifying_question": clarifying_question,
            "handoff_ready": handoff_ready or suggested_action == "rfq",
            "handoff_prefill": handoff_prefill,
        }

    async def create_handoff(
        self,
        *,
        chat_session: ChatSession,
        prefill: dict[str, Any],
    ) -> dict[str, Any]:
        chat_session.status = "handoff_completed"
        chat_session.updated_at = utcnow_naive()
        self.db.add(chat_session)
        await self._record_tracking_event(
            visitor_id=chat_session.visitor_id,
            session_id=chat_session.session_id,
            event_name="chat_rfq_handoff",
            page_url=chat_session.context_page,
            page_type=chat_session.context_entity_type,
            page_id=chat_session.context_entity_id,
            properties={
                "source": "chat_widget",
                "prefill_fields": sorted(prefill.keys()),
            },
        )
        await self.db.commit()
        return {
            "rfq_prefill_url": _build_rfq_prefill_url(prefill),
            "prefill": prefill,
        }

    async def _record_tracking_event(
        self,
        *,
        visitor_id: uuid.UUID,
        session_id: Optional[uuid.UUID],
        event_name: str,
        page_url: Optional[str],
        page_type: Optional[str],
        page_id: Optional[uuid.UUID],
        properties: Optional[dict[str, Any]] = None,
    ) -> None:
        with self.db.no_autoflush:
            visitor = await self.db.get(Visitor, visitor_id)
        if visitor is None:
            visitor = Visitor(visitor_id=visitor_id)

        score_delta = calculate_score_delta(event_name, properties or {})
        visitor.intent_score = max(0, visitor.intent_score + score_delta)
        visitor.intent_stage = get_intent_stage(visitor.intent_score)
        visitor.last_activity_at = utcnow_naive()
        visitor.last_seen = utcnow_naive()
        visitor.updated_at = utcnow_naive()
        self.db.add(visitor)

        event = TrackingEvent(
            event_name=event_name,
            session_id=session_id,
            visitor_id=visitor_id,
            page_url=page_url,
            page_type=page_type,
            page_id=page_id,
            properties=json.dumps(properties or {}),
            score_delta=score_delta,
        )
        self.db.add(event)

    async def _get_recent_messages(self, chat_session_id: uuid.UUID) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == chat_session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        messages = list((await self.db.exec(statement)).all())
        return list(reversed(messages))

    async def _build_context(self, chat_session: ChatSession) -> tuple[str, list[dict[str, str]]]:
        context_entity_type = chat_session.context_entity_type or "unknown"
        sources: list[dict[str, str]] = []

        if context_entity_type == "product" and chat_session.context_entity_id:
            statement = (
                select(Product)
                .where(Product.id == chat_session.context_entity_id)
                .options(
                    selectinload(Product.category),
                    selectinload(Product.faqs),
                    selectinload(Product.certifications),
                )
            )
            product = (await self.db.exec(statement)).first()
            if not product:
                return "", []

            category_name = product.category.category_name if product.category else ""
            faq_summary_parts = []
            cert_summary_parts = []

            sources.append(
                {
                    "type": "product",
                    "id": str(product.id),
                    "name": product.product_name,
                    "url": chat_session.context_page or "",
                }
            )

            for faq in product.faqs[:3]:
                faq_summary_parts.append(_format_faq_snapshot(faq))
                sources.append(
                    {
                        "type": "faq",
                        "id": str(faq.id),
                        "name": faq.question,
                        "url": f"/faq/{faq.category_tag}" if faq.category_tag else "/faq",
                    }
                )

            for cert in product.certifications[:3]:
                cert_summary_parts.append(_format_cert_snapshot(cert))
                sources.append(
                    {
                        "type": "certification",
                        "id": str(cert.id),
                        "name": cert.cert_name,
                        "url": f"/certifications/{cert.slug}",
                    }
                )

            entity_summary = (
                f"Product name: {product.product_name}\n"
                f"Model number: {product.model_number}\n"
                f"Category: {category_name}\n"
                f"Short description: {_trim_text(_strip_html(product.short_description), 220)}\n"
                f"Full description: {_trim_text(_strip_html(product.full_description), 600)}\n"
                f"Specifications: {_trim_text(_format_product_snapshot(product, max_specs=6), 500)}\n"
                f"Related FAQs: {' | '.join(faq_summary_parts) if faq_summary_parts else 'N/A'}\n"
                f"Related certifications: {' | '.join(cert_summary_parts) if cert_summary_parts else 'N/A'}"
            )
            return entity_summary, sources

        if context_entity_type == "category" and chat_session.context_entity_id:
            statement = (
                select(ProductCategory)
                .where(ProductCategory.id == chat_session.context_entity_id)
                .options(
                    selectinload(ProductCategory.products).selectinload(Product.certifications),
                    selectinload(ProductCategory.products).selectinload(Product.faqs),
                )
            )
            category = (await self.db.exec(statement)).first()
            if category:
                related_products = category.products[:6]
                product_summaries = []
                faq_summary_parts: list[str] = []
                cert_summary_parts: list[str] = []
                seen_faq_ids: set[uuid.UUID] = set()
                seen_cert_ids: set[uuid.UUID] = set()
                for product in related_products:
                    product_summaries.append(_format_product_snapshot(product))
                    sources.append(
                        {
                            "type": "product",
                            "id": str(product.id),
                            "name": product.product_name,
                            "url": f"/products/{category.slug}/{product.slug}",
                        }
                    )
                    for faq in product.faqs[:2]:
                        if faq.id in seen_faq_ids:
                            continue
                        seen_faq_ids.add(faq.id)
                        faq_summary_parts.append(_format_faq_snapshot(faq))
                        sources.append(
                            {
                                "type": "faq",
                                "id": str(faq.id),
                                "name": faq.question,
                                "url": f"/faq/{faq.category_tag}" if faq.category_tag else "/faq",
                            }
                        )
                    for cert in product.certifications[:2]:
                        if cert.id in seen_cert_ids:
                            continue
                        seen_cert_ids.add(cert.id)
                        cert_summary_parts.append(_format_cert_snapshot(cert))
                        sources.append(
                            {
                                "type": "certification",
                                "id": str(cert.id),
                                "name": cert.cert_name,
                                "url": f"/certifications/{cert.slug}",
                            }
                        )

                entity_summary = (
                    f"Category name: {category.category_name}\n"
                    f"SEO description: {_trim_text(category.seo_description, 180)}\n"
                    f"Description: {_trim_text(_strip_html(category.description), 400)}\n"
                    f"Representative products: {' | '.join(product_summaries) if product_summaries else 'N/A'}\n"
                    f"Common FAQs: {' | '.join(faq_summary_parts) if faq_summary_parts else 'N/A'}\n"
                    f"Common certifications: {' | '.join(cert_summary_parts) if cert_summary_parts else 'N/A'}"
                )
                return entity_summary, sources

        if context_entity_type == "application" and chat_session.context_entity_id:
            statement = (
                select(Application)
                .where(Application.id == chat_session.context_entity_id)
                .options(
                    selectinload(Application.products).selectinload(Product.category),
                    selectinload(Application.products).selectinload(Product.certifications),
                    selectinload(Application.products).selectinload(Product.faqs),
                    selectinload(Application.faqs),
                )
            )
            application = (await self.db.exec(statement)).first()
            if application:
                product_summaries = []
                faq_summary_parts: list[str] = []
                cert_summary_parts: list[str] = []
                seen_faq_ids: set[uuid.UUID] = set()
                seen_cert_ids: set[uuid.UUID] = set()
                for product in application.products[:5]:
                    category_name = product.category.category_name if product.category else "Uncategorized"
                    product_summaries.append(f"[{category_name}] {_format_product_snapshot(product)}")
                    sources.append(
                        {
                            "type": "product",
                            "id": str(product.id),
                            "name": product.product_name,
                            "url": f"/products/{product.category.slug}/{product.slug}" if product.category else "/products",
                        }
                    )
                    for faq in product.faqs[:1]:
                        if faq.id in seen_faq_ids:
                            continue
                        seen_faq_ids.add(faq.id)
                        faq_summary_parts.append(_format_faq_snapshot(faq))
                        sources.append(
                            {
                                "type": "faq",
                                "id": str(faq.id),
                                "name": faq.question,
                                "url": f"/faq/{faq.category_tag}" if faq.category_tag else "/faq",
                            }
                        )
                    for cert in product.certifications[:2]:
                        if cert.id in seen_cert_ids:
                            continue
                        seen_cert_ids.add(cert.id)
                        cert_summary_parts.append(_format_cert_snapshot(cert))
                        sources.append(
                            {
                                "type": "certification",
                                "id": str(cert.id),
                                "name": cert.cert_name,
                                "url": f"/certifications/{cert.slug}",
                            }
                        )

                for faq in application.faqs[:3]:
                    if faq.id not in seen_faq_ids:
                        seen_faq_ids.add(faq.id)
                        faq_summary_parts.append(_format_faq_snapshot(faq))
                    sources.append(
                        {
                            "type": "faq",
                            "id": str(faq.id),
                            "name": faq.question,
                            "url": f"/faq/{faq.category_tag}" if faq.category_tag else "/faq",
                        }
                    )

                entity_summary = (
                    f"Application name: {application.application_name}\n"
                    f"Industry: {application.industry}\n"
                    f"SEO description: {_trim_text(application.seo_description, 180)}\n"
                    f"Description: {_trim_text(_strip_html(application.description), 400)}\n"
                    f"Buyer challenge: {_trim_text(_strip_html(application.challenge), 260)}\n"
                    f"Recommended solution direction: {_trim_text(_strip_html(application.solution), 260)}\n"
                    f"Related products: {' | '.join(product_summaries) if product_summaries else 'N/A'}\n"
                    f"Relevant FAQs: {' | '.join(faq_summary_parts) if faq_summary_parts else 'N/A'}\n"
                    f"Relevant certifications: {' | '.join(cert_summary_parts) if cert_summary_parts else 'N/A'}"
                )
                return entity_summary, sources

        # FAQ context fallback
        faq_statement = select(FAQItem).where(FAQItem.status == "published").order_by(FAQItem.sort_order)
        faqs = list((await self.db.exec(faq_statement)).all())[:5]
        faq_lines = []
        for faq in faqs:
            faq_lines.append(_format_faq_snapshot(faq))
            sources.append(
                {
                    "type": "faq",
                    "id": str(faq.id),
                    "name": faq.question,
                    "url": f"/faq/{faq.category_tag}" if faq.category_tag else "/faq",
                }
            )
        return "\n".join(faq_lines), sources

    def _build_faq_summary(self, sources: list[dict[str, str]]) -> str:
        faq_names = [source["name"] for source in sources if source["type"] == "faq"]
        return " | ".join(faq_names)

    def _build_cert_summary(self, sources: list[dict[str, str]]) -> str:
        cert_names = [source["name"] for source in sources if source["type"] == "certification"]
        return " | ".join(cert_names)

    async def _generate_reply(
        self,
        *,
        context_page: Optional[str],
        context_entity_type: str,
        entity_summary: str,
        faq_summary: str,
        cert_summary: str,
        recent_messages: list[ChatMessage],
        user_question: str,
    ) -> dict[str, Any]:
        try:
            response = await client.chat.completions.create(
                model=settings.AI_MODEL_NAME,
                messages=[
                    {"role": "system", "content": _build_system_prompt()},
                    {
                        "role": "user",
                        "content": _build_user_prompt(
                            context_page,
                            context_entity_type,
                            entity_summary,
                            faq_summary,
                            cert_summary,
                            recent_messages,
                            user_question,
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as exc:
            logger.exception("chat reply generation failed: %s", exc)
            return {
                "reply": "I don't have confirmed information for that in the current record. The fastest next step is to submit an RFQ or contact request.",
                "needs_clarification": False,
                "clarifying_question": None,
                "suggested_action": "contact",
                "handoff_reason": None,
                "prefill": {},
            }