"""
AI Copilot — Tool Functions (DB-backed)

Each function is called by the LLM via function calling when it needs real data.
All functions are tenant-scoped, return plain Python dicts (JSON-serialisable).

Available tools:
  get_dashboard_stats(hours)         — KPI snapshot
  list_rfqs(status, priority, limit) — filtered RFQ list
  get_rfq_detail(rfq_number)         — single RFQ full profile
  list_hot_visitors(limit)           — current hot / sales_ready visitors
  get_visitor_profile(visitor_id)    — deep visitor + contact profile
  list_overdue_rfqs(hours)           — unactioned RFQs past threshold
  get_contact_profile(email)         — contact + full history
  search_contacts(query)             — fuzzy search by name / company / country
  get_product_interest_stats(days)   — product demand ranking
  get_funnel_stats(days)             — visitor→contact→RFQ funnel
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import col, func, select

from app.db.session import get_session_ctx
from app.models.contact import Contact
from app.models.notification_preference import NotificationPreference
from app.models.product import Product
from app.models.rfq_request import RFQRequest, RFQProductLink
from app.models.visitor import Visitor

logger = logging.getLogger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M")


def _parse_form(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


# ── Tool: Dashboard Stats ─────────────────────────────────────────────────────

async def get_dashboard_stats(tenant_id: uuid.UUID, hours: int = 24) -> dict:
    """
    Return KPI snapshot for the last N hours.
    Covers: RFQ counts, visitor activity, hot leads, conversion rate.
    """
    async with get_session_ctx() as s:
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        new_rfqs = (await s.exec(
            select(func.count(RFQRequest.id))
            .where(RFQRequest.tenant_id == tenant_id)
            .where(RFQRequest.created_at >= cutoff)
        )).one() or 0

        urgent_rfqs = (await s.exec(
            select(func.count(RFQRequest.id))
            .where(RFQRequest.tenant_id == tenant_id)
            .where(RFQRequest.created_at >= cutoff)
            .where(RFQRequest.priority.in_(["high", "urgent"]))
        )).one() or 0

        overdue_rfqs = (await s.exec(
            select(func.count(RFQRequest.id))
            .where(RFQRequest.tenant_id == tenant_id)
            .where(RFQRequest.status == "new")
            .where(RFQRequest.created_at <= (datetime.utcnow() - timedelta(hours=24)))
        )).one() or 0

        active_visitors = (await s.exec(
            select(func.count(Visitor.visitor_id))
            .where(Visitor.tenant_id == tenant_id)
            .where(Visitor.last_activity_at >= cutoff)
        )).one() or 0

        hot_visitors = (await s.exec(
            select(func.count(Visitor.visitor_id))
            .where(Visitor.tenant_id == tenant_id)
            .where(Visitor.intent_stage.in_(["hot", "sales_ready"]))
            .where(Visitor.last_activity_at >= cutoff)
        )).one() or 0

        total_rfqs_all = (await s.exec(
            select(func.count(RFQRequest.id))
            .where(RFQRequest.tenant_id == tenant_id)
        )).one() or 0

        total_contacts = (await s.exec(
            select(func.count(Contact.id))
            .where(Contact.tenant_id == tenant_id)
        )).one() or 0

        # Open pipeline (new + assigned + in_progress)
        open_rfqs = (await s.exec(
            select(func.count(RFQRequest.id))
            .where(RFQRequest.tenant_id == tenant_id)
            .where(RFQRequest.status.in_(["new", "assigned", "in_progress"]))
        )).one() or 0

        won_rfqs = (await s.exec(
            select(func.count(RFQRequest.id))
            .where(RFQRequest.tenant_id == tenant_id)
            .where(RFQRequest.status == "won")
        )).one() or 0

    return {
        "period_hours": hours,
        "new_rfqs_in_period": new_rfqs,
        "urgent_or_high_rfqs_in_period": urgent_rfqs,
        "overdue_unactioned_rfqs": overdue_rfqs,
        "active_visitors_in_period": active_visitors,
        "hot_leads_in_period": hot_visitors,
        "total_open_rfqs": open_rfqs,
        "total_won_rfqs": won_rfqs,
        "total_contacts_all_time": total_contacts,
        "total_rfqs_all_time": total_rfqs_all,
    }


# ── Tool: List RFQs ───────────────────────────────────────────────────────────

async def list_rfqs(
    tenant_id: uuid.UUID,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 5,
) -> dict:
    """
    Return a list of RFQs with basic info.
    status: new / assigned / in_progress / quoted / won / lost / expired
    priority: normal / high / urgent
    """
    async with get_session_ctx() as s:
        q = (
            select(RFQRequest)
            .where(RFQRequest.tenant_id == tenant_id)
            .order_by(col(RFQRequest.created_at).desc())
        )
        if status:
            q = q.where(RFQRequest.status == status)
        if priority:
            q = q.where(RFQRequest.priority == priority)
        q = q.limit(min(limit, 20))
        rows = (await s.exec(q)).all()

        items = []
        for r in rows:
            form = _parse_form(r.form_data)
            items.append({
                "rfq_number": r.rfq_number,
                "status": r.status,
                "priority": r.priority,
                "company": form.get("company_name") or "—",
                "contact_name": form.get("full_name") or "—",
                "email": form.get("email") or "—",
                "country": form.get("country") or "—",
                "quantity": form.get("quantity") or "—",
                "timeline": form.get("timeline") or "—",
                "intent_score": r.intent_score_at_submit,
                "created_at": _fmt_dt(r.created_at),
            })

    return {"count": len(items), "rfqs": items}


# ── Tool: Get RFQ Detail ──────────────────────────────────────────────────────

async def get_rfq_detail(tenant_id: uuid.UUID, rfq_number: str) -> dict:
    """
    Return full details for a single RFQ, including contact profile,
    product interests, and full form submission data.
    """
    async with get_session_ctx() as s:
        result = await s.exec(
            select(RFQRequest)
            .where(RFQRequest.tenant_id == tenant_id)
            .where(RFQRequest.rfq_number == rfq_number.upper())
        )
        rfq = result.first()
        if not rfq:
            return {"error": f"RFQ {rfq_number} not found"}

        form = _parse_form(rfq.form_data)

        # Contact profile
        contact_info = {}
        if rfq.contact_id:
            contact = await s.get(Contact, rfq.contact_id)
            if contact:
                contact_info = {
                    "id": str(contact.id),
                    "email": contact.email,
                    "full_name": contact.full_name,
                    "company": contact.company_name,
                    "phone": contact.phone,
                    "country": contact.country,
                    "job_title": contact.job_title,
                    "how_did_you_find_us": contact.how_did_you_find_us,
                    "notes": contact.notes,
                    "created_at": _fmt_dt(contact.created_at),
                }

        # Past RFQs from same contact
        past_rfqs: list = []
        if rfq.contact_id:
            past_rows = (await s.exec(
                select(RFQRequest)
                .where(RFQRequest.contact_id == rfq.contact_id)
                .where(RFQRequest.id != rfq.id)
                .order_by(col(RFQRequest.created_at).desc())
                .limit(5)
            )).all()
            past_rfqs = [
                {"rfq_number": p.rfq_number, "status": p.status, "created_at": _fmt_dt(p.created_at)}
                for p in past_rows
            ]

        # Product interests
        product_links = (await s.exec(
            select(RFQProductLink).where(RFQProductLink.rfq_id == rfq.id)
        )).all()
        products: list = []
        for link in product_links:
            prod = await s.get(Product, link.product_id)
            if prod:
                products.append({
                    "model_number": prod.model_number,
                    "product_name": prod.product_name,
                    "category_id": str(prod.category_id),
                })

        return {
            "rfq_number": rfq.rfq_number,
            "status": rfq.status,
            "priority": rfq.priority,
            "intent_score_at_submit": rfq.intent_score_at_submit,
            "created_at": _fmt_dt(rfq.created_at),
            "form_data": {
                "company_name": form.get("company_name"),
                "full_name": form.get("full_name"),
                "email": form.get("email"),
                "phone": form.get("phone"),
                "country": form.get("country"),
                "job_title": form.get("job_title"),
                "quantity": form.get("quantity"),
                "specifications": form.get("specifications"),
                "timeline": form.get("timeline"),
                "message": form.get("message"),
                "how_did_you_find_us": form.get("how_did_you_find_us"),
            },
            "products_of_interest": products,
            "contact_profile": contact_info,
            "past_rfqs_from_same_contact": past_rfqs,
        }


# ── Tool: List Hot Visitors ───────────────────────────────────────────────────

async def list_hot_visitors(tenant_id: uuid.UUID, limit: int = 5) -> dict:
    """
    Return visitors currently in 'hot' or 'sales_ready' stage,
    enriched with contact info if identified.
    """
    async with get_session_ctx() as s:
        cutoff = datetime.utcnow() - timedelta(hours=72)  # active in last 3 days
        rows = (await s.exec(
            select(Visitor)
            .where(Visitor.tenant_id == tenant_id)
            .where(Visitor.intent_stage.in_(["hot", "sales_ready"]))
            .where(Visitor.last_activity_at >= cutoff)
            .order_by(col(Visitor.intent_score).desc())
            .limit(min(limit, 10))
        )).all()

        items = []
        for v in rows:
            # Try to resolve identity
            identity: dict = {"known": False}
            if v.contact_id:
                c = await s.get(Contact, v.contact_id)
                if c:
                    identity = {
                        "known": True,
                        "full_name": c.full_name,
                        "company": c.company_name,
                        "email": c.email,
                        "job_title": c.job_title,
                    }
            items.append({
                "visitor_id": str(v.visitor_id),
                "intent_stage": v.intent_stage,
                "intent_score": v.intent_score,
                "ml_intent_score": round(v.ml_intent_score, 3) if v.ml_intent_score else None,
                "country": v.country,
                "total_visits": v.total_visits,
                "total_page_views": v.total_page_views,
                "last_activity_at": _fmt_dt(v.last_activity_at),
                "identity": identity,
            })

    return {"count": len(items), "visitors": items}


# ── Tool: Get Visitor Profile ─────────────────────────────────────────────────

async def get_visitor_profile(tenant_id: uuid.UUID, visitor_id: str) -> dict:
    """
    Full profile of a single visitor: intent history, contact info if known,
    and all RFQs submitted.
    """
    try:
        vid = uuid.UUID(visitor_id)
    except ValueError:
        return {"error": "Invalid visitor_id format"}

    async with get_session_ctx() as s:
        v = await s.get(Visitor, vid)
        if not v or v.tenant_id != tenant_id:
            return {"error": "Visitor not found"}

        contact_info: dict = {}
        rfqs: list = []

        if v.contact_id:
            c = await s.get(Contact, v.contact_id)
            if c:
                contact_info = {
                    "full_name": c.full_name,
                    "company": c.company_name,
                    "email": c.email,
                    "phone": c.phone,
                    "country": c.country,
                    "job_title": c.job_title,
                    "how_did_you_find_us": c.how_did_you_find_us,
                }
                rfq_rows = (await s.exec(
                    select(RFQRequest)
                    .where(RFQRequest.contact_id == v.contact_id)
                    .order_by(col(RFQRequest.created_at).desc())
                    .limit(5)
                )).all()
                rfqs = [
                    {"rfq_number": r.rfq_number, "status": r.status, "priority": r.priority,
                     "created_at": _fmt_dt(r.created_at)}
                    for r in rfq_rows
                ]

        return {
            "visitor_id": visitor_id,
            "intent_stage": v.intent_stage,
            "intent_score": v.intent_score,
            "ml_intent_score": round(v.ml_intent_score, 3) if v.ml_intent_score else None,
            "country": v.country,
            "device_type": v.device_type,
            "total_visits": v.total_visits,
            "total_page_views": v.total_page_views,
            "first_seen": _fmt_dt(v.first_seen),
            "last_activity_at": _fmt_dt(v.last_activity_at),
            "is_identified": bool(v.contact_id),
            "contact": contact_info,
            "rfqs": rfqs,
        }


# ── Tool: List Overdue RFQs ───────────────────────────────────────────────────

async def list_overdue_rfqs(tenant_id: uuid.UUID, hours: int = 24) -> dict:
    """
    Return RFQs that are still in 'new' status (unassigned/unactioned)
    after the given number of hours. Default threshold: 24h.
    """
    async with get_session_ctx() as s:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        rows = (await s.exec(
            select(RFQRequest)
            .where(RFQRequest.tenant_id == tenant_id)
            .where(RFQRequest.status == "new")
            .where(RFQRequest.created_at <= cutoff)
            .order_by(RFQRequest.priority.desc(), col(RFQRequest.created_at).asc())
            .limit(10)
        )).all()

        items = []
        for r in rows:
            form = _parse_form(r.form_data)
            hours_elapsed = (datetime.utcnow() - r.created_at).total_seconds() / 3600
            items.append({
                "rfq_number": r.rfq_number,
                "priority": r.priority,
                "intent_score": r.intent_score_at_submit,
                "company": form.get("company_name") or "—",
                "email": form.get("email") or "—",
                "country": form.get("country") or "—",
                "hours_elapsed": round(hours_elapsed, 1),
                "created_at": _fmt_dt(r.created_at),
            })

    return {"threshold_hours": hours, "count": len(items), "overdue_rfqs": items}


# ── Tool: Get Contact Profile ─────────────────────────────────────────────────

async def get_contact_profile(tenant_id: uuid.UUID, email: str) -> dict:
    """
    Return a contact's full profile: personal info, all submitted RFQs,
    visitor behavior linkage, and sourcing notes.
    """
    async with get_session_ctx() as s:
        c = (await s.exec(
            select(Contact)
            .where(Contact.tenant_id == tenant_id)
            .where(Contact.email == email.lower().strip())
        )).first()

        if not c:
            return {"error": f"No contact found with email: {email}"}

        rfq_rows = (await s.exec(
            select(RFQRequest)
            .where(RFQRequest.contact_id == c.id)
            .order_by(col(RFQRequest.created_at).desc())
            .limit(10)
        )).all()

        rfqs = []
        for r in rfq_rows:
            form = _parse_form(r.form_data)
            rfqs.append({
                "rfq_number": r.rfq_number,
                "status": r.status,
                "priority": r.priority,
                "intent_score": r.intent_score_at_submit,
                "quantity": form.get("quantity"),
                "timeline": form.get("timeline"),
                "message_snippet": (form.get("message") or "")[:150],
                "created_at": _fmt_dt(r.created_at),
            })

        # Visitor linkage
        visitor_info: dict = {}
        if c.visitor_id:
            v = await s.get(Visitor, c.visitor_id)
            if v:
                visitor_info = {
                    "intent_stage": v.intent_stage,
                    "intent_score": v.intent_score,
                    "total_visits": v.total_visits,
                    "total_page_views": v.total_page_views,
                    "last_activity_at": _fmt_dt(v.last_activity_at),
                }

        return {
            "email": c.email,
            "full_name": c.full_name,
            "company": c.company_name,
            "phone": c.phone,
            "country": c.country,
            "job_title": c.job_title,
            "how_did_you_find_us": c.how_did_you_find_us,
            "intent_score_at_first_rfq": c.intent_score_at_creation,
            "notes": c.notes,
            "created_at": _fmt_dt(c.created_at),
            "rfq_count": len(rfqs),
            "rfqs": rfqs,
            "visitor_behavior": visitor_info,
        }


# ── Tool: Search Contacts ─────────────────────────────────────────────────────

async def search_contacts(tenant_id: uuid.UUID, query: str) -> dict:
    """
    Search contacts by name, company name, or country (case-insensitive).
    Returns up to 8 matches.
    """
    async with get_session_ctx() as s:
        q = query.strip().lower()
        rows = (await s.exec(
            select(Contact)
            .where(Contact.tenant_id == tenant_id)
            .where(
                col(Contact.full_name).ilike(f"%{q}%")
                | col(Contact.company_name).ilike(f"%{q}%")
                | col(Contact.country).ilike(f"%{q}%")
                | col(Contact.email).ilike(f"%{q}%")
            )
            .limit(8)
        )).all()

        items = [
            {
                "email": c.email,
                "full_name": c.full_name,
                "company": c.company_name,
                "country": c.country,
                "job_title": c.job_title,
                "created_at": _fmt_dt(c.created_at),
            }
            for c in rows
        ]

    return {"query": query, "count": len(items), "contacts": items}


# ── Tool: Product Interest Stats ──────────────────────────────────────────────

async def get_product_interest_stats(tenant_id: uuid.UUID, days: int = 30) -> dict:
    """
    Return a ranked list of products by inquiry volume over the last N days.
    Shows which products are driving the most RFQ demand.
    """
    async with get_session_ctx() as s:
        cutoff = datetime.utcnow() - timedelta(days=days)

        # RFQs in period for this tenant
        rfq_ids_result = await s.exec(
            select(RFQRequest.id)
            .where(RFQRequest.tenant_id == tenant_id)
            .where(RFQRequest.created_at >= cutoff)
        )
        rfq_ids = [r for r in rfq_ids_result.all()]

        if not rfq_ids:
            return {"days": days, "count": 0, "products": []}

        # Count RFQ links per product
        link_rows = (await s.exec(
            select(RFQProductLink.product_id, func.count(RFQProductLink.rfq_id).label("cnt"))
            .where(RFQProductLink.rfq_id.in_(rfq_ids))
            .group_by(RFQProductLink.product_id)
            .order_by(col("cnt").desc())
            .limit(10)
        )).all()

        products: list = []
        for row in link_rows:
            prod = await s.get(Product, row[0])
            if prod:
                products.append({
                    "model_number": prod.model_number,
                    "product_name": prod.product_name,
                    "rfq_count": row[1],
                    "status": prod.status,
                })

    return {"days": days, "count": len(products), "products": products}


# ── Tool: Funnel Stats ────────────────────────────────────────────────────────

async def get_funnel_stats(tenant_id: uuid.UUID, days: int = 30) -> dict:
    """
    Return the visitor → contact → RFQ conversion funnel for the last N days.
    Also breaks down RFQ pipeline by status and stage distribution of current visitors.
    """
    async with get_session_ctx() as s:
        cutoff = datetime.utcnow() - timedelta(days=days)

        total_visitors = (await s.exec(
            select(func.count(Visitor.visitor_id))
            .where(Visitor.tenant_id == tenant_id)
            .where(Visitor.last_activity_at >= cutoff)
        )).one() or 0

        new_contacts = (await s.exec(
            select(func.count(Contact.id))
            .where(Contact.tenant_id == tenant_id)
            .where(Contact.created_at >= cutoff)
        )).one() or 0

        new_rfqs = (await s.exec(
            select(func.count(RFQRequest.id))
            .where(RFQRequest.tenant_id == tenant_id)
            .where(RFQRequest.created_at >= cutoff)
        )).one() or 0

        won_rfqs = (await s.exec(
            select(func.count(RFQRequest.id))
            .where(RFQRequest.tenant_id == tenant_id)
            .where(RFQRequest.created_at >= cutoff)
            .where(RFQRequest.status == "won")
        )).one() or 0

        # Stage distribution (all-time current state)
        stage_rows = (await s.exec(
            select(Visitor.intent_stage, func.count(Visitor.visitor_id).label("cnt"))
            .where(Visitor.tenant_id == tenant_id)
            .group_by(Visitor.intent_stage)
        )).all()
        stages = {row[0]: row[1] for row in stage_rows}

        # RFQ pipeline
        pipeline_rows = (await s.exec(
            select(RFQRequest.status, func.count(RFQRequest.id).label("cnt"))
            .where(RFQRequest.tenant_id == tenant_id)
            .group_by(RFQRequest.status)
        )).all()
        pipeline = {row[0]: row[1] for row in pipeline_rows}

        rfq_rate = round(new_rfqs / new_contacts * 100, 1) if new_contacts > 0 else 0
        win_rate = round(won_rfqs / new_rfqs * 100, 1) if new_rfqs > 0 else 0

    return {
        "period_days": days,
        "funnel": {
            "visitors": total_visitors,
            "new_contacts": new_contacts,
            "new_rfqs": new_rfqs,
            "won": won_rfqs,
            "rfq_rate_pct": rfq_rate,
            "win_rate_pct": win_rate,
        },
        "visitor_stages": stages,
        "rfq_pipeline": pipeline,
    }
