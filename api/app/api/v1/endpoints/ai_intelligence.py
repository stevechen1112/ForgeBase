"""
Phase 3 AI Intelligence Endpoints

3.1.1  POST /tracking/rfqs/{rfq_id}/analyze           — AI RFQ analysis
3.1.2  POST /tracking/rfqs/{rfq_id}/draft-reply       — AI draft reply email
3.1.3  POST /content/intelligence/optimize            — AI content optimizer
3.1.4  GET  /tracking/visitors/{visitor_id}/recommend-cta — CTA recommendation
3.2.3  GET  /tracking/accounts/{account_id}/insight   — Account-level insight
3.3.1  GET  /content/dynamic-cta                      — Dynamic CTA for visitor
3.3.2  POST /nurture/sequences/{seq_id}/optimize      — Nurture path optimizer
3.3.3  GET  /content/products/{product_id}/recommend-relations
       GET  /content/applications/{app_id}/recommend-relations
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor
from app.db.session import get_session
from app.models.user import User
from app.services.ai_rfq import analyze_rfq, generate_rfq_reply_draft
from app.services.content_optimizer import optimize_content
from app.services.ai_recommend import recommend_cta_for_visitor
from app.services.dynamic_cta import select_dynamic_cta
from app.services.nurture_optimizer import optimize_nurture_sequence
from app.services.relation_recommender import recommend_relations

# ── Routers (paths already include full prefix segment) ───────────────────────
# Mounted directly on api_router so full path = /api/v1/<route defined here>

rfq_ai_router = APIRouter(tags=["AI Intelligence: RFQ"])
content_ai_router = APIRouter(tags=["AI Intelligence: Content"])
visitor_ai_router = APIRouter(tags=["AI Intelligence: Visitors"])
nurture_ai_router = APIRouter(tags=["AI Intelligence: Nurture"])


# ── 3.1.1  AI RFQ Analysis ───────────────────────────────────────────────────

@rfq_ai_router.post("/tracking/rfqs/{rfq_id}/analyze")
async def analyze_rfq_endpoint(
    rfq_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Run AI analysis on an RFQ — match products, classify urgency, extract requirements."""
    # Fetch RFQ + form data
    rfq_sql = text("SELECT id, form_data, intent_score_at_submit FROM rfq_requests WHERE id = :id")
    rfq_result = await session.execute(rfq_sql, {"id": rfq_id})
    rfq_row = rfq_result.mappings().first()
    if not rfq_row:
        raise HTTPException(status_code=404, detail="RFQ not found")

    rfq_data: dict = dict(rfq_row.get("form_data") or {})
    rfq_data["intent_score_at_submit"] = rfq_row.get("intent_score_at_submit", 0)

    # Fetch linked products + details
    products_sql = text("""
        SELECT p.id::text, p.model_number, p.name, p.description
        FROM rfq_product_links rpl
        JOIN products p ON rpl.product_id = p.id
        WHERE rpl.rfq_request_id = :rfq_id
    """)
    products_result = await session.execute(products_sql, {"rfq_id": rfq_id})
    products = [dict(r) for r in products_result.mappings().all()]

    # If no specific products linked, include top catalog products for matching
    if not products:
        all_prods_sql = text(
            "SELECT id::text, model_number, name, description FROM products "
            "WHERE status = 'published' ORDER BY created_at DESC LIMIT 20"
        )
        all_result = await session.execute(all_prods_sql)
        products = [dict(r) for r in all_result.mappings().all()]

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
    rfq_sql = text("SELECT form_data, intent_score_at_submit FROM rfq_requests WHERE id = :id")
    rfq_result = await session.execute(rfq_sql, {"id": rfq_id})
    rfq_row = rfq_result.mappings().first()
    if not rfq_row:
        raise HTTPException(status_code=404, detail="RFQ not found")

    rfq_data: dict = dict(rfq_row.get("form_data") or {})
    rfq_data["intent_score_at_submit"] = rfq_row.get("intent_score_at_submit", 0)

    # Run analysis if not provided
    analysis = payload.analysis
    if not analysis:
        products_sql = text("""
            SELECT p.id::text, p.model_number, p.name, p.description
            FROM rfq_product_links rpl
            JOIN products p ON rpl.product_id = p.id
            WHERE rpl.rfq_request_id = :rfq_id
        """)
        products_result = await session.execute(products_sql, {"rfq_id": rfq_id})
        products = [dict(r) for r in products_result.mappings().all()]
        analysis = await analyze_rfq(rfq_data, products)

    sender_name = payload.sender_name or current_user.full_name or current_user.email
    draft = await generate_rfq_reply_draft(
        rfq_data, analysis,
        company_name=payload.company_name or "ForgeBase",
        sender_name=sender_name,
    )
    return draft


# ── 3.1.3  AI Content Optimizer ───────────────────────────────────────────────

class OptimizeRequest(BaseModel):
    entity_type: str        # "product" | "application" | "category"
    entity_id: str          # UUID
    period_days: int = 30


@content_ai_router.post("/content/intelligence/optimize")
async def optimize_page_content_endpoint(
    payload: OptimizeRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    """Analyze page performance and generate AI-powered content improvement suggestions."""
    etype = payload.entity_type
    eid = payload.entity_id
    days = payload.period_days

    # Fetch entity info
    pages_sql_map = {
        "product": "SELECT name, seo_title, seo_description AS description, full_description FROM products WHERE id = :id",
        "application": "SELECT name, seo_title, seo_description AS description, full_description FROM applications WHERE id = :id",
        "category": "SELECT name, seo_title, seo_description AS description, NULL AS full_description FROM product_categories WHERE id = :id",
    }
    if etype not in pages_sql_map:
        raise HTTPException(status_code=400, detail=f"Unsupported entity_type: {etype}")

    entity_result = await session.execute(text(pages_sql_map[etype]), {"id": eid})
    entity_row = entity_result.mappings().first()
    if not entity_row:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Fetch analytics data for this entity
    analytics_sql = text("""
        SELECT
            COUNT(*) FILTER (WHERE event_name = 'page_view') AS page_views,
            COUNT(DISTINCT visitor_id) FILTER (WHERE event_name = 'page_view') AS unique_visitors,
            COUNT(*) FILTER (WHERE event_name = 'spec_download') AS spec_downloads,
            COUNT(DISTINCT v.visitor_id) FILTER (WHERE r.id IS NOT NULL) AS rfq_count,
            COALESCE(AVG(v.intent_score), 0) AS avg_intent_score
        FROM tracking_events e
        LEFT JOIN visitors v ON e.visitor_id = v.visitor_id
        LEFT JOIN rfq_requests r ON v.visitor_id = r.visitor_id
        WHERE e.properties->>'entity_id' = :entity_id
          AND e.created_at > NOW() - (:days || ' days')::interval
    """)
    analytics_result = await session.execute(
        analytics_sql, {"entity_id": eid, "days": days}
    )
    analytics_row = analytics_result.mappings().first() or {}
    analytics = {
        "page_views": int(analytics_row.get("page_views") or 0),
        "unique_visitors": int(analytics_row.get("unique_visitors") or 0),
        "spec_downloads": int(analytics_row.get("spec_downloads") or 0),
        "rfq_count": int(analytics_row.get("rfq_count") or 0),
        "avg_intent_score": float(analytics_row.get("avg_intent_score") or 0),
        "period_days": days,
    }

    page_info = {
        "page_type": etype,
        "entity_name": entity_row.get("name", ""),
        "title": entity_row.get("name", ""),
        "seo_title": entity_row.get("seo_title"),
        "description": entity_row.get("description"),
        "full_description": entity_row.get("full_description"),
    }

    suggestions = await optimize_content(page_info, analytics)
    return {"entity_id": eid, "entity_type": etype, "analytics": analytics, **suggestions}


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
    # Fetch visitor
    visitor_sql = text("""
        SELECT intent_score, intent_stage, total_page_views, total_visits, country, device_type
        FROM visitors WHERE visitor_id = :vid
    """)
    v_result = await session.execute(visitor_sql, {"vid": visitor_id})
    visitor_row = v_result.mappings().first()
    if not visitor_row:
        raise HTTPException(status_code=404, detail="Visitor not found")

    # Fetch recent event history
    events_sql = text("""
        SELECT event_name, properties
        FROM tracking_events
        WHERE visitor_id = :vid
        ORDER BY created_at DESC
        LIMIT 30
    """)
    events_result = await session.execute(events_sql, {"vid": visitor_id})
    events = events_result.mappings().all()
    recent_events = [e["event_name"] for e in events]

    # Extract product/application interest from events
    product_names: list[str] = []
    app_names: list[str] = []
    for ev in events:
        props = ev.get("properties") or {}
        if ev["event_name"] == "product_view" and props.get("product_name"):
            product_names.append(props["product_name"])
        if ev["event_name"] == "application_view" and props.get("application_name"):
            app_names.append(props["application_name"])

    # Fetch all published CTAs
    ctas_sql = text("""
        SELECT id::text, name, action_type, label, description
        FROM ctas WHERE status = 'published' LIMIT 20
    """)
    ctas_result = await session.execute(ctas_sql)
    ctas = [dict(r) for r in ctas_result.mappings().all()]

    visitor_profile = {
        **dict(visitor_row),
        "top_products_viewed": list(dict.fromkeys(product_names))[:3],
        "top_applications_viewed": list(dict.fromkeys(app_names))[:3],
        "has_downloaded_spec": "spec_download" in recent_events,
        "has_submitted_rfq": "rfq_submit" in recent_events,
        "recent_events": recent_events[:15],
    }
    page_context = {"page_type": page_type, "entity_id": entity_id} if page_type else None

    return await recommend_cta_for_visitor(visitor_profile, ctas, page_context)


# ── 3.2.3  Account-level Insight ──────────────────────────────────────────────

@visitor_ai_router.get("/tracking/accounts/{account_id}/insight")
async def account_insight_endpoint(
    account_id: uuid.UUID,
    period_days: int = Query(30, ge=7, le=365),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Aggregate behavioral insight for all visitors from a company account.
    Combines intent data, product interest, RFQ history for account-level view.
    """
    # Fetch account
    acct_sql = text("""
        SELECT id::text, company_name, domain, industry, employee_count_range,
               country, enrichment_status
        FROM accounts WHERE id = :id
    """)
    acct_result = await session.execute(acct_sql, {"id": account_id})
    account = acct_result.mappings().first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Aggregate visitor stats
    visitor_stats_sql = text("""
        SELECT
            COUNT(*) AS visitor_count,
            AVG(intent_score) AS avg_intent_score,
            MAX(intent_score) AS max_intent_score,
            SUM(total_page_views) AS total_page_views,
            MAX(last_activity_at) AS last_activity,
            COUNT(*) FILTER (WHERE intent_stage = 'hot') AS hot_visitors,
            COUNT(*) FILTER (WHERE intent_stage = 'sales_ready') AS sales_ready_visitors,
            COUNT(*) FILTER (WHERE intent_stage = 'warm') AS warm_visitors
        FROM visitors
        WHERE account_id = :account_id
    """)
    vstats_result = await session.execute(visitor_stats_sql, {"account_id": account_id})
    vstats = vstats_result.mappings().first() or {}

    # RFQ count from this account
    rfq_sql = text("""
        SELECT COUNT(*) AS rfq_count, MAX(r.created_at) AS last_rfq_date
        FROM rfq_requests r
        JOIN visitors v ON r.visitor_id = v.visitor_id
        WHERE v.account_id = :account_id
          AND r.created_at > NOW() - (:days || ' days')::interval
    """)
    rfq_result = await session.execute(rfq_sql, {"account_id": account_id, "days": period_days})
    rfq_data = rfq_result.mappings().first() or {}

    # Spec downloads
    dl_sql = text("""
        SELECT COUNT(*) AS spec_downloads
        FROM tracking_events e
        JOIN visitors v ON e.visitor_id = v.visitor_id
        WHERE v.account_id = :account_id
          AND e.event_name = 'spec_download'
          AND e.created_at > NOW() - (:days || ' days')::interval
    """)
    dl_result = await session.execute(dl_sql, {"account_id": account_id, "days": period_days})
    dl_data = dl_result.mappings().first() or {}

    # Top 5 products viewed by account visitors
    top_products_sql = text("""
        SELECT
            e.properties->>'product_name' AS product_name,
            COUNT(*) AS view_count
        FROM tracking_events e
        JOIN visitors v ON e.visitor_id = v.visitor_id
        WHERE v.account_id = :account_id
          AND e.event_name = 'product_view'
          AND e.properties->>'product_name' IS NOT NULL
          AND e.created_at > NOW() - (:days || ' days')::interval
        GROUP BY product_name
        ORDER BY view_count DESC
        LIMIT 5
    """)
    top_prods_result = await session.execute(
        top_products_sql, {"account_id": account_id, "days": period_days}
    )
    top_products = [dict(r) for r in top_prods_result.mappings().all()]

    # Opportunity assessment
    max_intent = int(vstats.get("max_intent_score") or 0)
    rfq_count = int(rfq_data.get("rfq_count") or 0)
    spec_dl = int(dl_data.get("spec_downloads") or 0)
    last_activity = vstats.get("last_activity")
    days_since_active: Optional[float] = None
    if last_activity:
        if isinstance(last_activity, datetime):
            days_since_active = (datetime.now(timezone.utc) - last_activity).days
        else:
            try:
                la = datetime.fromisoformat(str(last_activity))
                if la.tzinfo is None:
                    la = la.replace(tzinfo=timezone.utc)
                days_since_active = (datetime.now(timezone.utc) - la).days
            except Exception:
                pass

    if rfq_count > 0:
        opportunity_tier = "active_deal"
    elif max_intent >= 30 or spec_dl >= 3:
        opportunity_tier = "high_potential"
    elif max_intent >= 10 or spec_dl >= 1:
        opportunity_tier = "nurture"
    elif days_since_active and days_since_active > 60:
        opportunity_tier = "re_engage"
    else:
        opportunity_tier = "cold"

    return {
        "account": dict(account),
        "visitor_summary": {
            "total_visitors": int(vstats.get("visitor_count") or 0),
            "avg_intent_score": round(float(vstats.get("avg_intent_score") or 0), 1),
            "max_intent_score": max_intent,
            "total_page_views": int(vstats.get("total_page_views") or 0),
            "hot_visitors": int(vstats.get("hot_visitors") or 0),
            "sales_ready_visitors": int(vstats.get("sales_ready_visitors") or 0),
            "warm_visitors": int(vstats.get("warm_visitors") or 0),
            "last_activity": last_activity.isoformat() if isinstance(last_activity, datetime) else str(last_activity) if last_activity else None,
            "days_since_active": days_since_active,
        },
        "rfq_summary": {
            "rfq_count": rfq_count,
            "last_rfq_date": str(rfq_data.get("last_rfq_date") or ""),
        },
        "engagement": {
            "spec_downloads": spec_dl,
            "top_products_viewed": top_products,
        },
        "opportunity_tier": opportunity_tier,
        "period_days": period_days,
    }


# ── 3.3.1  Dynamic CTA ────────────────────────────────────────────────────────

@content_ai_router.get("/content/dynamic-cta")
async def dynamic_cta_endpoint(
    visitor_id: Optional[str] = Query(None),
    page_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    entity_name: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Return the optimal CTA for a visitor in the current page context.
    Public endpoint (no auth) — used by the frontend.
    """
    intent_stage = "cold"
    intent_score = 0
    top_products: list[str] = []

    if visitor_id:
        v_sql = text(
            "SELECT intent_score, intent_stage FROM visitors WHERE visitor_id = :vid::uuid"
        )
        try:
            v_result = await session.execute(v_sql, {"vid": visitor_id})
            v_row = v_result.mappings().first()
            if v_row:
                intent_stage = v_row["intent_stage"] or "cold"
                intent_score = int(v_row["intent_score"] or 0)
        except Exception:
            pass

        # Get recently viewed products
        ev_sql = text("""
            SELECT properties->>'product_name' AS pname
            FROM tracking_events
            WHERE visitor_id = :vid::uuid
              AND event_name = 'product_view'
              AND properties->>'product_name' IS NOT NULL
            ORDER BY created_at DESC LIMIT 5
        """)
        try:
            ev_result = await session.execute(ev_sql, {"vid": visitor_id})
            top_products = list(
                dict.fromkeys(
                    r["pname"] for r in ev_result.mappings().all() if r["pname"]
                )
            )
        except Exception:
            pass

    # Fetch published CTAs
    ctas_sql = text(
        "SELECT id::text, name, action_type, label, description FROM ctas "
        "WHERE status = 'published' LIMIT 15"
    )
    ctas_result = await session.execute(ctas_sql)
    ctas = [dict(r) for r in ctas_result.mappings().all()]

    page_context = {"page_type": page_type, "entity_name": entity_name, "entity_id": entity_id}
    return select_dynamic_cta(intent_stage, intent_score, ctas, page_context, top_products)


# ── 3.3.2  Nurture Sequence Optimizer ────────────────────────────────────────

@nurture_ai_router.post("/nurture/sequences/{seq_id}/optimize")
async def optimize_nurture_sequence_endpoint(
    seq_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """AI analysis of nurture sequence performance with reordering + rewrite suggestions."""
    # Fetch sequence
    seq_sql = text("""
        SELECT id::text, name, trigger_stage, trigger_event, description
        FROM nurture_sequences WHERE id = :id
    """)
    seq_result = await session.execute(seq_sql, {"id": seq_id})
    sequence = seq_result.mappings().first()
    if not sequence:
        raise HTTPException(status_code=404, detail="Nurture sequence not found")

    # Fetch steps
    steps_sql = text("""
        SELECT step_number, subject, delay_days, body_html
        FROM nurture_steps WHERE sequence_id = :sid ORDER BY step_number
    """)
    steps_result = await session.execute(steps_sql, {"sid": seq_id})
    steps = [dict(r) for r in steps_result.mappings().all()]

    # Fetch click event counts per step (proxy for engagement)
    # nurture_step_id is stored in tracking_event properties
    clicks_sql = text("""
        SELECT
            properties->>'nurture_step' AS step_num,
            COUNT(*) AS click_count
        FROM tracking_events
        WHERE event_name = 'cta_click'
          AND properties->>'nurture_sequence_id' = :sid::text
        GROUP BY step_num
    """)
    clicks_result = await session.execute(clicks_sql, {"sid": seq_id})
    click_map: dict[str, int] = {
        r["step_num"]: int(r["click_count"])
        for r in clicks_result.mappings().all()
        if r["step_num"]
    }

    # Enriched steps
    enrollments_sql = text("""
        SELECT
            COUNT(*) AS total_enrolled,
            COUNT(*) FILTER (WHERE status = 'active') AS active,
            COUNT(*) FILTER (WHERE status = 'completed') AS completed,
            COUNT(*) FILTER (WHERE status IN ('dropped', 'unsubscribed')) AS dropped
        FROM nurture_enrollments WHERE sequence_id = :sid
    """)
    enr_result = await session.execute(enrollments_sql, {"sid": seq_id})
    enr_data = dict(enr_result.mappings().first() or {})
    total_enrolled = int(enr_data.get("total_enrolled") or 1)
    completed = int(enr_data.get("completed") or 0)
    enr_data["avg_completion_rate"] = round(completed / total_enrolled * 100, 1)

    # Count proxy "sent" for each step from enrollments * position assumption
    steps_with_metrics = []
    for step in steps:
        sn = str(step.get("step_number"))
        clicks = click_map.get(sn, 0)
        # Approximate sent count based on enrollment
        sent = max(1, total_enrolled)
        steps_with_metrics.append({
            "step_number": step.get("step_number"),
            "subject": step.get("subject", ""),
            "delay_days": step.get("delay_days"),
            "sent_count": sent,
            "click_count": clicks,
            "click_rate": round(clicks / sent * 100, 1),
        })

    result = await optimize_nurture_sequence(dict(sequence), steps_with_metrics, enr_data)
    return {"sequence_id": str(seq_id), "sequence_name": sequence["name"], **result}


# ── 3.3.3  Relation Recommendations ──────────────────────────────────────────

@content_ai_router.get("/content/products/{product_id}/recommend-relations")
async def recommend_product_relations(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """AI-powered suggestions for new Product ↔ Application relationships."""
    # Fetch product
    prod_sql = text(
        "SELECT id::text, name, description FROM products WHERE id = :id"
    )
    prod_result = await session.execute(prod_sql, {"id": product_id})
    product = prod_result.mappings().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Existing linked applications
    existing_sql = text("""
        SELECT a.id::text AS id, a.name
        FROM product_applications pa
        JOIN applications a ON pa.application_id = a.id
        WHERE pa.product_id = :pid
    """)
    existing_result = await session.execute(existing_sql, {"pid": product_id})
    existing = [dict(r) for r in existing_result.mappings().all()]

    # All applications as candidates
    all_apps_sql = text(
        "SELECT id::text, name, description FROM applications WHERE status = 'published' LIMIT 50"
    )
    all_apps_result = await session.execute(all_apps_sql)
    candidates = [dict(r) for r in all_apps_result.mappings().all()]

    return await recommend_relations(
        session,
        entity_type="product",
        entity_id=str(product_id),
        entity_name=product["name"],
        entity_description=(product.get("description") or "")[:400],
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
    app_sql = text(
        "SELECT id::text, name, description FROM applications WHERE id = :id"
    )
    app_result = await session.execute(app_sql, {"id": app_id})
    application = app_result.mappings().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    existing_sql = text("""
        SELECT p.id::text AS id, p.name
        FROM product_applications pa
        JOIN products p ON pa.product_id = p.id
        WHERE pa.application_id = :aid
    """)
    existing_result = await session.execute(existing_sql, {"aid": app_id})
    existing = [dict(r) for r in existing_result.mappings().all()]

    all_prods_sql = text(
        "SELECT id::text, name, description FROM products WHERE status = 'published' LIMIT 50"
    )
    all_prods_result = await session.execute(all_prods_sql)
    candidates = [dict(r) for r in all_prods_result.mappings().all()]

    return await recommend_relations(
        session,
        entity_type="application",
        entity_id=str(app_id),
        entity_name=application["name"],
        entity_description=(application.get("description") or "")[:400],
        existing_relations=existing,
        candidate_info=candidates,
    )
