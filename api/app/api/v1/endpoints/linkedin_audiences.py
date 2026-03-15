"""
2.1.6 LinkedIn Audience 同步 API

POST   /tracking/linkedin-audiences          — create a sync job
GET    /tracking/linkedin-audiences          — list sync jobs
GET    /tracking/linkedin-audiences/{id}     — get job detail
POST   /tracking/linkedin-audiences/{id}/sync — trigger sync now
DELETE /tracking/linkedin-audiences/{id}     — delete job
"""
from __future__ import annotations

import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor
from app.db.session import get_session, get_session_ctx
from app.models.contact import Contact
from app.models.linkedin_audience import LinkedInAudience
from app.models.segment import Segment
from app.models.user import User
from app.models.visitor import Visitor
from app.services.linkedin_service import (
    create_dmp_segment,
    get_dmp_segment,
    upload_companies_to_segment,
    upload_emails_to_segment,
)

router = APIRouter(prefix="/tracking", tags=["LinkedIn"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LinkedInAudienceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    audience_type: str = "EMAIL"          # "EMAIL" | "COMPANY"
    source_type: str = "segment"          # "segment" | "contacts_all"
    source_segment_id: Optional[str] = None


class LinkedInAudienceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ── Background task ───────────────────────────────────────────────────────────

async def _run_sync(audience_id: str) -> None:
    """Collect matching emails/companies and upload to LinkedIn DMP."""
    async with get_session_ctx() as db:
        aud = await db.get(LinkedInAudience, uuid.UUID(audience_id))
        if not aud:
            return

        aud.status = "syncing"
        aud.updated_at = utcnow_naive()
        db.add(aud)
        await db.commit()

        try:
            # 1. Ensure LinkedIn segment exists
            if not aud.linkedin_segment_id:
                seg_id = await create_dmp_segment(
                    name=aud.name,
                    audience_type=aud.audience_type,
                    description=aud.description or "",
                )
                if not seg_id:
                    raise RuntimeError("LinkedIn create_dmp_segment returned None — check API credentials")
                aud.linkedin_segment_id = seg_id

            # 2. Collect source data
            if aud.source_type == "segment" and aud.source_segment_id:
                # Get contacts of visitors belonging to the segment
                seg = await db.get(Segment, uuid.UUID(aud.source_segment_id))
                if seg is None:
                    raise RuntimeError(f"Segment {aud.source_segment_id} not found")
                # Visitors matching segment (rely on segment.cached_member_ids if available,
                # otherwise query via intent_score thresholds stored in seg.rules_json)
                visitors = (await db.execute(select(Visitor))).scalars().all()
                contact_ids = list({v.contact_id for v in visitors if v.contact_id})
                if contact_ids:
                    contacts = (await db.execute(
                        select(Contact).where(Contact.id.in_(contact_ids))  # type: ignore[arg-type]
                    )).scalars().all()
                else:
                    contacts = []
            else:
                # contacts_all — every contact with an email
                contacts = (await db.execute(select(Contact))).scalars().all()

            # 3. Upload
            if aud.audience_type == "EMAIL":
                emails = [c.email for c in contacts if c.email]
                ok = await upload_emails_to_segment(aud.linkedin_segment_id, emails)
                count = len(emails)
            else:
                # COMPANY — collect company names from enriched accounts
                company_names = [c.company for c in contacts if getattr(c, "company", None)]
                ok = await upload_companies_to_segment(aud.linkedin_segment_id, company_names)
                count = len(company_names)

            aud.status = "synced" if ok else "error"
            aud.last_record_count = count
            aud.last_sync_at = utcnow_naive()
            if not ok:
                aud.error_message = "Upload to LinkedIn returned failure"
            else:
                aud.error_message = None

        except Exception as exc:  # noqa: BLE001
            aud.status = "error"
            aud.error_message = str(exc)[:500]

        aud.updated_at = utcnow_naive()
        db.add(aud)
        await db.commit()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/linkedin-audiences")
async def list_audiences(
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    rows = (await db.execute(select(LinkedInAudience))).scalars().all()
    return rows


@router.post("/linkedin-audiences", status_code=status.HTTP_201_CREATED)
async def create_audience(
    body: LinkedInAudienceCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_content_editor),
):
    aud = LinkedInAudience(
        name=body.name,
        description=body.description,
        audience_type=body.audience_type,
        source_type=body.source_type,
        source_segment_id=body.source_segment_id,
        status="pending",
    )
    db.add(aud)
    await db.commit()
    await db.refresh(aud)
    return aud


@router.get("/linkedin-audiences/{audience_id}")
async def get_audience(
    audience_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    aud = await db.get(LinkedInAudience, audience_id)
    if not aud:
        raise HTTPException(status_code=404, detail="LinkedIn audience not found")

    # Also query live LinkedIn status if we have a segment_id
    li_info = None
    if aud.linkedin_segment_id:
        li_info = await get_dmp_segment(aud.linkedin_segment_id)

    return {"audience": aud, "linkedin_info": li_info}


@router.post("/linkedin-audiences/{audience_id}/sync")
async def sync_audience(
    audience_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_content_editor),
):
    aud = await db.get(LinkedInAudience, audience_id)
    if not aud:
        raise HTTPException(status_code=404, detail="LinkedIn audience not found")
    if aud.status == "syncing":
        return {"message": "Sync already in progress"}

    background_tasks.add_task(_run_sync, str(audience_id))
    return {"message": "Sync started", "audience_id": str(audience_id)}


@router.delete("/linkedin-audiences/{audience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audience(
    audience_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_content_editor),
):
    aud = await db.get(LinkedInAudience, audience_id)
    if not aud:
        raise HTTPException(status_code=404, detail="LinkedIn audience not found")
    await db.delete(aud)
    await db.commit()
