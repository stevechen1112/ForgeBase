"""
2.4.1 Salesforce 整合 + 2.4.2 CRM 雙向同步

Endpoints:
  POST /tracking/crm/sf/sync-contact       — push a Contact to Salesforce
  POST /tracking/crm/sf/sync-rfq           — push an RFQ as an Opportunity
  POST /tracking/crm/sf/bulk-sync-contacts — bulk push all contacts
  POST /tracking/crm/sf/pull-opportunity   — pull Opportunity stage back (2.4.2)
  GET  /tracking/crm/sync-logs             — view sync history
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor
from app.db.session import get_session, get_session_ctx
from app.models.contact import Contact
from app.models.crm_sync_log import CrmSyncLog
from app.models.rfq_request import RFQRequest
from app.models.user import User
from app.services.salesforce_service import (
    create_opportunity,
    get_contact_by_email,
    update_opportunity_stage,
    upsert_contact,
)

router = APIRouter(prefix="/tracking", tags=["CRM"])

# ── Helpers ───────────────────────────────────────────────────────────────────

# Map our RFQ status → Salesforce Opportunity StageName
RFQ_TO_SF_STAGE: dict[str, str] = {
    "new": "Prospecting",
    "assigned": "Qualification",
    "in_progress": "Value Proposition",
    "quoted": "Proposal/Price Quote",
    "won": "Closed Won",
    "lost": "Closed Lost",
    "expired": "Closed Lost",
}

SF_STAGE_TO_RFQ: dict[str, str] = {
    "Closed Won": "won",
    "Closed Lost": "lost",
    "Proposal/Price Quote": "quoted",
    "Value Proposition": "in_progress",
    "Qualification": "assigned",
    "Prospecting": "new",
}


async def _log(
    db: AsyncSession,
    *,
    crm: str = "salesforce",
    direction: str = "push",
    entity_type: str,
    local_id: Optional[str] = None,
    remote_id: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    payload_summary: Optional[str] = None,
) -> None:
    log = CrmSyncLog(
        crm=crm,
        direction=direction,
        entity_type=entity_type,
        local_id=local_id,
        remote_id=remote_id,
        status=status,
        error_message=error_message,
        payload_summary=payload_summary,
    )
    db.add(log)
    await db.commit()


# ── Schemas ───────────────────────────────────────────────────────────────────

class SyncContactRequest(BaseModel):
    contact_id: uuid.UUID


class SyncRfqRequest(BaseModel):
    rfq_id: uuid.UUID
    opportunity_name: Optional[str] = None
    close_date: str = "2099-12-31"
    amount: Optional[float] = None


class PullOpportunityRequest(BaseModel):
    rfq_id: uuid.UUID
    sf_opportunity_id: str


# ── Background bulk sync ──────────────────────────────────────────────────────

async def _bulk_sync_contacts() -> None:
    async with get_session_ctx() as db:
        contacts = (await db.execute(select(Contact))).scalars().all()
        for contact in contacts:
            first, *rest = (contact.full_name or "Unknown").split(" ", 1)
            last = rest[0] if rest else ""
            result = await upsert_contact(
                email=contact.email,
                first_name=first,
                last_name=last,
                company=contact.company_name or "",
                phone=contact.phone or "",
                extra_fields={"Title": contact.job_title or ""},
            )
            status = "error" if result.get("error") else "success"
            await _log(
                db,
                entity_type="contact",
                local_id=str(contact.id),
                remote_id=result.get("id"),
                status=status,
                error_message=result.get("error"),
                payload_summary=f"{contact.email} → Salesforce Contact",
            )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/crm/sf/sync-contact")
async def sync_contact_to_sf(
    body: SyncContactRequest,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_content_editor),
):
    """Push a single contact to Salesforce as a Contact record."""
    contact = await db.get(Contact, body.contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    first, *rest = (contact.full_name or "Unknown").split(" ", 1)
    last = rest[0] if rest else ""
    result = await upsert_contact(
        email=contact.email,
        first_name=first,
        last_name=last,
        company=contact.company_name or "",
        phone=contact.phone or "",
        extra_fields={"Title": contact.job_title or ""},
    )

    err = result.get("error")
    await _log(
        db,
        entity_type="contact",
        local_id=str(contact.id),
        remote_id=result.get("id"),
        status="error" if err else "success",
        error_message=err,
        payload_summary=f"{contact.email} → Salesforce Contact",
    )

    if err:
        raise HTTPException(status_code=502, detail=f"Salesforce error: {err}")

    return {"success": True, "salesforce_id": result.get("id"), "email": contact.email}


@router.post("/crm/sf/sync-rfq")
async def sync_rfq_to_sf(
    body: SyncRfqRequest,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_content_editor),
):
    """Push an RFQ as a Salesforce Opportunity, linked to the Contact."""
    rfq = await db.get(RFQRequest, body.rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    # Look up Salesforce Contact ID via email
    sf_contact_id: Optional[str] = None
    if rfq.contact_id:
        contact = await db.get(Contact, rfq.contact_id)
        if contact:
            sf_contact = await get_contact_by_email(contact.email)
            sf_contact_id = (sf_contact or {}).get("Id")

    stage = RFQ_TO_SF_STAGE.get(rfq.status, "Prospecting")
    name = body.opportunity_name or rfq.rfq_number
    result = await create_opportunity(
        name=name,
        stage=stage,
        close_date=body.close_date,
        contact_id=sf_contact_id,
        amount=body.amount,
        description=f"Synced from ForgeBase RFQ {rfq.rfq_number}",
    )

    err = result.get("error")
    await _log(
        db,
        entity_type="opportunity",
        local_id=str(rfq.id),
        remote_id=result.get("id"),
        status="error" if err else "success",
        error_message=err,
        payload_summary=f"{rfq.rfq_number} → Salesforce Opportunity ({stage})",
    )

    if err:
        raise HTTPException(status_code=502, detail=f"Salesforce error: {err}")

    return {"success": True, "salesforce_id": result.get("id"), "rfq_number": rfq.rfq_number}


@router.post("/crm/sf/bulk-sync-contacts")
async def bulk_sync_contacts(
    background_tasks: BackgroundTasks,
    _current_user: User = Depends(require_content_editor),
):
    """Bulk push ALL contacts to Salesforce (background job)."""
    background_tasks.add_task(_bulk_sync_contacts)
    return {"message": "Bulk sync started in background"}


@router.post("/crm/sf/pull-opportunity")
async def pull_opportunity_stage(
    body: PullOpportunityRequest,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_content_editor),
):
    """
    2.4.2 — Pull Salesforce Opportunity stage → update local RFQ status.
    Closes CRM loop: Closed Won → rfq.status = 'won', etc.
    """
    from sqlmodel import select as sqlselect
    from app.models.rfq_request import RFQRequest as RFQ

    # Verify RFQ exists
    rfq = await db.get(RFQ, body.rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    # Fetch live stage from Salesforce
    from app.services.salesforce_service import _sf_request
    sf_data = await _sf_request(
        "GET",
        f"/sobjects/Opportunity/{body.sf_opportunity_id}",
        params={"fields": "Id,StageName,Amount,CloseDate"},
    )

    if sf_data.get("error"):
        raise HTTPException(status_code=502, detail=f"Salesforce error: {sf_data['error']}")

    sf_stage = sf_data.get("StageName", "")
    new_rfq_status = SF_STAGE_TO_RFQ.get(sf_stage)

    changes: dict = {"sf_stage": sf_stage}
    if new_rfq_status and rfq.status != new_rfq_status:
        rfq.status = new_rfq_status  # type: ignore[assignment]
        db.add(rfq)
        changes["rfq_status_updated_to"] = new_rfq_status

    # Log
    await _log(
        db,
        direction="pull",
        entity_type="opportunity",
        local_id=str(rfq.id),
        remote_id=body.sf_opportunity_id,
        status="success",
        payload_summary=f"SF stage={sf_stage} → rfq.status={new_rfq_status or 'no change'}",
    )

    await db.commit()
    return {"success": True, **changes}


@router.get("/crm/sync-logs")
async def get_sync_logs(
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
    crm: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 50,
):
    """List recent CRM sync logs."""
    stmt = select(CrmSyncLog).order_by(col(CrmSyncLog.synced_at).desc()).limit(limit)
    if crm:
        stmt = stmt.where(CrmSyncLog.crm == crm)
    if entity_type:
        stmt = stmt.where(CrmSyncLog.entity_type == entity_type)
    logs = (await db.execute(stmt)).scalars().all()
    return logs
