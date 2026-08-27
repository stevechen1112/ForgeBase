"""
Contact API — 1b.2.3 + 1b.4.3 (Contact Form submission)

POST /forms/contact        — submit contact form (public, no auth)
GET  /tracking/contacts    — list contacts (admin)
GET  /tracking/contacts/{id} — contact detail (admin)
PUT  /tracking/contacts/{id} — update contact notes/etc (admin)
"""
import logging
import uuid
from typing import Optional
from uuid import UUID as _UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor, resolve_tenant_id
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.contact import Contact
from app.models.user import User
from app.models.visitor import Visitor

logger = logging.getLogger(__name__)

# Two separate routers — one public (forms), one admin (tracking)
forms_router = APIRouter(prefix="/forms", tags=["Forms"])
tracking_router = APIRouter(prefix="/tracking", tags=["Tracking"])

# ── Public: Contact form submission ──────────────────────────────────────────

HOW_DID_YOU_FIND_VALUES = {
    "google", "linkedin", "trade_show", "referral",
    "direct", "email", "other",
}


class ContactFormIn(BaseModel):
    full_name: str
    email: EmailStr
    company_name: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    job_title: Optional[str] = None
    message: Optional[str] = None
    how_did_you_find_us: Optional[str] = None
    visitor_id: Optional[str] = None  # UUID string from client cookie
    source_page: Optional[str] = None

    @field_validator("how_did_you_find_us")
    @classmethod
    def validate_how(cls, v):
        if v and v not in HOW_DID_YOU_FIND_VALUES:
            raise ValueError("Invalid how_did_you_find_us value")
        return v

    @field_validator("full_name")
    @classmethod
    def sanitize_name(cls, v):
        return v.strip()[:100]


@forms_router.post("/contact", status_code=status.HTTP_201_CREATED)
async def submit_contact_form(
    body: ContactFormIn,
    request: Request,
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[_UUID] = Depends(resolve_tenant_id),
):
    """
    Submit the contact enquiry form.
    Deduplicates by email — updates record if contact already exists.
    """
    visitor_id_parsed: Optional[uuid.UUID] = None
    if body.visitor_id:
        try:
            visitor_id_parsed = uuid.UUID(body.visitor_id)
        except ValueError:
            pass

    # Determine intent score from visitor if known
    intent_score = 0
    visitor: Optional[Visitor] = None
    if visitor_id_parsed:
        visitor = await db.get(Visitor, visitor_id_parsed)
        if visitor and visitor.tenant_id != tenant_id:
            raise HTTPException(status_code=422, detail="visitor_id does not belong to this site")
        if visitor:
            intent_score = visitor.intent_score
        else:
            visitor_id_parsed = None

    # Dedup by (tenant_id, email) — same email in another tenant is a
    # separate Contact (multi-tenant isolation).
    contact = (
        await db.exec(
            select(Contact).where(
                Contact.email == body.email,
                Contact.tenant_id == tenant_id,
            )
        )
    ).first()

    now = utcnow_naive()
    if contact:
        # Update existing contact
        contact.full_name = body.full_name
        if body.company_name:
            contact.company_name = body.company_name
        if body.phone:
            contact.phone = body.phone
        if body.country:
            contact.country = body.country
        if body.job_title:
            contact.job_title = body.job_title
        if visitor and visitor.contact_id is None:
            visitor.contact_id = contact.id
            visitor.updated_at = now
            db.add(visitor)
        contact.updated_at = now
        db.add(contact)
        await db.commit()
        return {"contact_id": str(contact.id), "new": False}

    contact = Contact(
        email=body.email,
        full_name=body.full_name,
        company_name=body.company_name,
        phone=body.phone,
        country=body.country,
        job_title=body.job_title,
        intent_score_at_creation=intent_score,
        how_did_you_find_us=body.how_did_you_find_us,
        source_page=body.source_page,
        notes=body.message,
        tenant_id=tenant_id,
    )
    db.add(contact)
    await db.flush()
    if visitor and visitor.contact_id is None:
        visitor.contact_id = contact.id
        visitor.updated_at = now
        db.add(visitor)
    await db.commit()
    await db.refresh(contact)

    # 1b.5.3 contact.created webhook
    try:
        from app.services.webhook import fire_webhook
        fire_webhook("contact.created", {
            "contact_id":   str(contact.id),
            "full_name":    contact.full_name,
            "email":        contact.email,
            "company_name": contact.company_name,
            "country":      contact.country,
            "intent_score": intent_score,
            "source_page":  body.source_page,
        })
    except Exception:
        logger.warning("contact.created webhook failed", exc_info=True)

    return {"contact_id": str(contact.id), "new": True}


# ── Admin: Contact management ─────────────────────────────────────────────────

class ContactUpdate(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    job_title: Optional[str] = None
    notes: Optional[str] = None
    hubspot_contact_id: Optional[str] = None


@tracking_router.get("/contacts")
async def list_contacts(
    country: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    q = select(Contact).order_by(col(Contact.created_at).desc())
    if _.tenant_id:
        q = q.where(Contact.tenant_id == _.tenant_id)
    if country:
        q = q.where(Contact.country == country)
    q = q.offset(offset).limit(min(limit, 200))
    rows = (await db.exec(q)).all()
    visitor_map = await _visitor_ids_by_contact(db, [row.id for row in rows])
    return [_contact_row(r, visitor_map.get(r.id, [])) for r in rows]


@tracking_router.get("/contacts/{contact_id}")
async def get_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    c = await db.get(Contact, contact_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")
    if _.tenant_id and c.tenant_id != _.tenant_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    visitor_map = await _visitor_ids_by_contact(db, [c.id])
    return _contact_row(c, visitor_map.get(c.id, []), full=True)


@tracking_router.put("/contacts/{contact_id}")
async def update_contact(
    contact_id: uuid.UUID,
    body: ContactUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    c = await db.get(Contact, contact_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")
    if _.tenant_id and c.tenant_id != _.tenant_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(c, field, value)
    c.updated_at = utcnow_naive()
    db.add(c)
    await db.commit()
    await db.refresh(c)
    visitor_map = await _visitor_ids_by_contact(db, [c.id])
    return _contact_row(c, visitor_map.get(c.id, []), full=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _visitor_ids_by_contact(
    db: AsyncSession,
    contact_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[uuid.UUID]]:
    if not contact_ids:
        return {}
    rows = (
        await db.exec(
            select(Visitor.contact_id, Visitor.visitor_id)
            .where(Visitor.contact_id.in_(contact_ids))
            .order_by(Visitor.first_seen.asc())
        )
    ).all()
    result: dict[uuid.UUID, list[uuid.UUID]] = {}
    for contact_id, visitor_id in rows:
        if contact_id is not None:
            result.setdefault(contact_id, []).append(visitor_id)
    return result


def _contact_row(
    c: Contact,
    visitor_ids: list[uuid.UUID],
    full: bool = False,
) -> dict:
    base = {
        "id": str(c.id),
        "email": c.email,
        "full_name": c.full_name,
        "company_name": c.company_name,
        "country": c.country,
        "job_title": c.job_title,
        "intent_score_at_creation": c.intent_score_at_creation,
        # ``visitor_id`` is retained as a compatibility alias for the first
        # linked identity. New clients should consume ``visitor_ids``.
        "visitor_id": str(visitor_ids[0]) if visitor_ids else None,
        "visitor_ids": [str(visitor_id) for visitor_id in visitor_ids],
        "hubspot_contact_id": c.hubspot_contact_id,
        "created_at": c.created_at.isoformat(),
    }
    if full:
        base["phone"] = c.phone
        base["how_did_you_find_us"] = c.how_did_you_find_us
        base["source_page"] = c.source_page
        base["notes"] = c.notes
        base["updated_at"] = c.updated_at.isoformat()
    return base
