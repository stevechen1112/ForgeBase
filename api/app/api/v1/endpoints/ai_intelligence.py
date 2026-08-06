"""
Phase 3 AI Intelligence Endpoints

3.1.1  POST /tracking/rfqs/{rfq_id}/analyze           — AI RFQ analysis
3.1.2  POST /tracking/rfqs/{rfq_id}/draft-reply       — AI draft reply email
3.1.4  GET  /tracking/visitors/{visitor_id}/recommend-cta — CTA recommendation
3.3.1  GET  /content/dynamic-cta                      — Dynamic CTA for visitor
3.3.2  GET  /content/products/{product_id}/recommend-relations
       GET  /content/applications/{app_id}/recommend-relations
"""
import uuid
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor, resolve_tenant_id
from app.db.session import get_session
from app.models.application import Application
from app.models.associations import ProductApplicationLink
from app.models.cta import CTA
from app.models.product import Product
from app.models.rfq_request import RFQProductLink, RFQRequest
from app.models.tracking_event import TrackingEvent
from app.models.user import User
from app.models.visitor import Visitor
from app.services.ai_rfq import analyze_rfq, generate_rfq_reply_draft
from app.services.ai_recommend import recommend_cta_for_visitor
from app.services.dynamic_cta import select_dynamic_cta
from app.services.relation_recommender import recommend_relations

# ── Routers (paths already include full prefix segment) ───────────────────────
# Mounted directly on api_router so full path = /api/v1/<route defined here>

rfq_ai_router = APIRouter(tags=["AI Intelligence: RFQ"])
content_ai_router = APIRouter(tags=["AI Intelligence: Content"])
visitor_ai_router = APIRouter(tags=["AI Intelligence: Visitors"])


def _cta_payload(cta: CTA) -> dict[str, str | None]:
    return {
        "id": str(cta.id),
        "name": cta.headline or cta.cta_key,
        "action_type": cta.button_action,
        "label": cta.button_label,
        "description": cta.subheadline or cta.headline,
        "target_intent_stage": cta.target_intent_stage or "any",
    }


def _parse_properties(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}


# ── 3.1.1  AI RFQ Analysis ───────────────────────────────────────────────────

@rfq_ai_router.post("/tracking/rfqs/{rfq_id}/analyze")
async def analyze_rfq_endpoint(
    rfq_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Run AI analysis on an RFQ — match products, classify urgency, extract requirements."""
    rfq = await session.get(RFQRequest, rfq_id)
    if not rfq or (current_user.tenant_id and rfq.tenant_id != current_user.tenant_id):
        raise HTTPException(status_code=404, detail="RFQ not found")

    rfq_data: dict = _parse_properties(rfq.form_data)
    rfq_data["intent_score_at_submit"] = rfq.intent_score_at_submit

    products = [
        {
            "id": str(product.id),
            "model_number": product.model_number,
            "name": product.product_name,
            "description": product.full_description or product.short_description,
        }
        for product in (
            await session.exec(
                select(Product)
                .join(RFQProductLink, RFQProductLink.product_id == Product.id)
                .where(
                    RFQProductLink.rfq_id == rfq_id,
                    Product.tenant_id == rfq.tenant_id,
                )
            )
        ).all()
    ]

    # If no specific products linked, include top catalog products for matching
    if not products:
        products = [
            {
                "id": str(product.id),
                "model_number": product.model_number,
                "name": product.product_name,
                "description": product.full_description or product.short_description,
            }
            for product in (
                await session.exec(
                    select(Product)
                    .where(
                        Product.status == "published",
                        Product.tenant_id == rfq.tenant_id,
                    )
                    .order_by(Product.created_at.desc())
                    .limit(20)
                )
            ).all()
        ]

    analysis = await analyze_rfq(rfq_data, products)
    return analysis


# ── 3.1.2  AI RFQ Draft Reply ─────────────────────────────────────────────────

class DraftReplyRequest(BaseModel):
    analysis: Optional[dict] = None          # pass existing analysis to reuse
    sender_name: Optional[str] = None
    company_name: Optional[str] = "ForgeBase"


@rfq_ai_router.post("/tracking/rfqs/{rfq_id}/draft-reply")
async def draft_rfq_reply_endpoint(
    rfq_id: uuid.UUID,
    payload: DraftReplyRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate a professional draft reply email for an RFQ."""
    rfq = await session.get(RFQRequest, rfq_id)
    if not rfq or (current_user.tenant_id and rfq.tenant_id != current_user.tenant_id):
        raise HTTPException(status_code=404, detail="RFQ not found")

    rfq_data: dict = _parse_properties(rfq.form_data)
    rfq_data["intent_score_at_submit"] = rfq.intent_score_at_submit

    # Run analysis if not provided
    analysis = payload.analysis
    if not analysis:
        products = [
            {
                "id": str(product.id),
                "model_number": product.model_number,
                "name": product.product_name,
                "description": product.full_description or product.short_description,
            }
            for product in (
                await session.exec(
                    select(Product)
                    .join(RFQProductLink, RFQProductLink.product_id == Product.id)
                    .where(
                        RFQProductLink.rfq_id == rfq_id,
                        Product.tenant_id == rfq.tenant_id,
                    )
                )
            ).all()
        ]
        analysis = await analyze_rfq(rfq_data, products)

    sender_name = payload.sender_name or current_user.full_name or current_user.email
    draft = await generate_rfq_reply_draft(
        rfq_data, analysis,
        company_name=payload.company_name or "ForgeBase",
        sender_name=sender_name,
    )
    return draft


# ── 3.1.4  CTA Recommendation for Visitor ────────────────────────────────────

@visitor_ai_router.get("/tracking/visitors/{visitor_id}/recommend-cta")
async def recommend_cta_endpoint(
    visitor_id: uuid.UUID,
    page_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get the AI-recommended CTA for a specific visitor."""
    visitor = await session.get(Visitor, visitor_id)
    if not visitor or (current_user.tenant_id and visitor.tenant_id != current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Visitor not found")

    events = (
        await session.exec(
            select(TrackingEvent)
            .where(
                TrackingEvent.visitor_id == visitor_id,
                TrackingEvent.tenant_id == visitor.tenant_id,
            )
            .order_by(TrackingEvent.timestamp.desc())
            .limit(30)
        )
    ).all()
    recent_events = [event.event_name for event in events]

    # Extract product/application interest from events
    product_names: list[str] = []
    app_names: list[str] = []
    for ev in events:
        props = _parse_properties(ev.properties)
        if ev.event_name == "product_view" and props.get("product_name"):
            product_names.append(props["product_name"])
        if ev.event_name == "application_view" and props.get("application_name"):
            app_names.append(props["application_name"])

    ctas = [
        _cta_payload(cta)
        for cta in (
            await session.exec(
                select(CTA)
                .where(
                    CTA.tenant_id == visitor.tenant_id,
                    CTA.status.in_(["active", "published"]),
                )
                .limit(20)
            )
        ).all()
    ]

    visitor_profile = {
        "intent_score": visitor.intent_score,
        "intent_stage": visitor.intent_stage,
        "total_page_views": visitor.total_page_views,
        "total_visits": visitor.total_visits,
        "country": visitor.country,
        "device_type": visitor.device_type,
        "top_products_viewed": list(dict.fromkeys(product_names))[:3],
        "top_applications_viewed": list(dict.fromkeys(app_names))[:3],
        "has_downloaded_spec": "spec_download" in recent_events,
        "has_submitted_rfq": "rfq_submit" in recent_events,
        "recent_events": recent_events[:15],
    }
    page_context = {"page_type": page_type, "entity_id": entity_id} if page_type else None

    return await recommend_cta_for_visitor(visitor_profile, ctas, page_context)


# ── 3.3.1  Dynamic CTA ────────────────────────────────────────────────────────

@content_ai_router.get("/content/dynamic-cta")
async def dynamic_cta_endpoint(
    visitor_id: Optional[str] = Query(None),
    page_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    entity_name: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID | None = Depends(resolve_tenant_id),
):
    """
    Return the optimal CTA for a visitor in the current page context.
    Public endpoint (no auth) — used by the frontend.
    """
    intent_stage = "cold"
    intent_score = 0
    top_products: list[str] = []
    visitor_facets: dict[str, int] | None = None

    if visitor_id:
        try:
            visitor = await session.get(Visitor, uuid.UUID(visitor_id))
            if visitor and visitor.tenant_id == tenant_id:
                intent_stage = visitor.intent_stage or "cold"
                intent_score = int(visitor.intent_score or 0)
                visitor_facets = {
                    "product_interest": visitor.facet_product_interest,
                    "trust_validation": visitor.facet_trust_validation,
                    "procurement_readiness": visitor.facet_procurement_readiness,
                    "urgency": visitor.facet_urgency,
                }
        except Exception:
            pass

        # Get recently viewed products
        try:
            event_rows = (
                await session.exec(
                    select(TrackingEvent)
                    .where(
                        TrackingEvent.visitor_id == uuid.UUID(visitor_id),
                        TrackingEvent.tenant_id == tenant_id,
                        TrackingEvent.event_name == "product_view",
                    )
                    .order_by(TrackingEvent.timestamp.desc())
                    .limit(5)
                )
            ).all()
            top_products = list(dict.fromkeys([
                _parse_properties(row.properties).get("product_name")
                for row in event_rows
                if _parse_properties(row.properties).get("product_name")
            ]))
        except Exception:
            pass

    ctas = [
        _cta_payload(cta)
        for cta in (
            await session.exec(
                select(CTA)
                .where(
                    CTA.tenant_id == tenant_id,
                    CTA.status.in_(["active", "published"]),
                )
                .limit(15)
            )
        ).all()
    ]

    page_context = {"page_type": page_type, "entity_name": entity_name, "entity_id": entity_id}
    return select_dynamic_cta(intent_stage, intent_score, ctas, page_context, top_products, facets=visitor_facets)


# ── 3.3.3  Relation Recommendations ──────────────────────────────────────────

@content_ai_router.get("/content/products/{product_id}/recommend-relations")
async def recommend_product_relations(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """AI-powered suggestions for new Product ↔ Application relationships."""
    product = await session.get(Product, product_id)
    if not product or (current_user.tenant_id and product.tenant_id != current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Product not found")

    existing_applications = (
        await session.exec(
            select(Application)
            .join(ProductApplicationLink, ProductApplicationLink.application_id == Application.id)
            .where(
                ProductApplicationLink.product_id == product_id,
                Application.tenant_id == product.tenant_id,
            )
        )
    ).all()
    existing = [{"id": str(app.id), "name": app.application_name} for app in existing_applications]

    candidates = [
        {
            "id": str(app.id),
            "name": app.application_name,
            "description": app.description,
        }
        for app in (
            await session.exec(
                select(Application)
                .where(
                    Application.status == "published",
                    Application.tenant_id == product.tenant_id,
                )
                .limit(50)
            )
        ).all()
    ]

    return await recommend_relations(
        session,
        entity_type="product",
        entity_id=str(product_id),
        entity_name=product.product_name,
        entity_description=((product.full_description or product.short_description or "")[:400]),
        existing_relations=existing,
        candidate_info=candidates,
    )


@content_ai_router.get("/content/applications/{app_id}/recommend-relations")
async def recommend_application_relations(
    app_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """AI-powered suggestions for new Application ↔ Product relationships."""
    application = await session.get(Application, app_id)
    if not application or (current_user.tenant_id and application.tenant_id != current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Application not found")

    existing_products = (
        await session.exec(
            select(Product)
            .join(ProductApplicationLink, ProductApplicationLink.product_id == Product.id)
            .where(
                ProductApplicationLink.application_id == app_id,
                Product.tenant_id == application.tenant_id,
            )
        )
    ).all()
    existing = [{"id": str(product.id), "name": product.product_name} for product in existing_products]

    candidates = [
        {
            "id": str(product.id),
            "name": product.product_name,
            "description": product.full_description or product.short_description,
        }
        for product in (
            await session.exec(
                select(Product)
                .where(
                    Product.status == "published",
                    Product.tenant_id == application.tenant_id,
                )
                .limit(50)
            )
        ).all()
    ]

    return await recommend_relations(
        session,
        entity_type="application",
        entity_id=str(app_id),
        entity_name=application.application_name,
        entity_description=((application.description or "")[:400]),
        existing_relations=existing,
        candidate_info=candidates,
    )
