"""
Nurture API  (2.1.4 Email Nurture Engine)

GET    /nurture/sequences           — list sequences (admin)
POST   /nurture/sequences           — create sequence
GET    /nurture/sequences/{id}      — sequence detail + steps
PATCH  /nurture/sequences/{id}      — update sequence
DELETE /nurture/sequences/{id}      — delete sequence (admin)
POST   /nurture/sequences/{id}/steps — add step
PATCH  /nurture/steps/{step_id}     — update step
DELETE /nurture/steps/{step_id}     — delete step

POST   /nurture/enroll              — enroll contact in sequence
GET    /nurture/enrollments         — list enrollments (admin)
POST   /nurture/process             — process due steps (admin/cron trigger)
"""
import uuid
from datetime import datetime, timedelta
from app.core.datetime import utcnow_naive
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor
from app.db.session import get_session
from app.models.nurture import NurtureEnrollment, NurtureSequence, NurtureStep
from app.models.contact import Contact
from app.models.user import User

router = APIRouter(prefix="/nurture", tags=["Nurture"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SequenceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str  # "intent_stage" | "segment" | "download_gate" | "manual"
    trigger_value: Optional[str] = None
    is_active: bool = True
    allow_re_enrollment: bool = False


class SequenceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_value: Optional[str] = None
    is_active: Optional[bool] = None
    allow_re_enrollment: Optional[bool] = None


class StepCreate(BaseModel):
    step_order: int
    delay_days: int = 0
    subject: str
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    from_name: Optional[str] = None
    from_email: Optional[str] = None


class StepUpdate(BaseModel):
    step_order: Optional[int] = None
    delay_days: Optional[int] = None
    subject: Optional[str] = None
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    from_name: Optional[str] = None
    from_email: Optional[str] = None


class EnrollRequest(BaseModel):
    contact_id: uuid.UUID
    sequence_id: uuid.UUID
    trigger_type: Optional[str] = "manual"
    trigger_value: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seq_dict(s: NurtureSequence) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "description": s.description,
        "trigger_type": s.trigger_type,
        "trigger_value": s.trigger_value,
        "is_active": s.is_active,
        "allow_re_enrollment": s.allow_re_enrollment,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


def _step_dict(s: NurtureStep) -> dict:
    return {
        "id": str(s.id),
        "sequence_id": str(s.sequence_id),
        "step_order": s.step_order,
        "delay_days": s.delay_days,
        "subject": s.subject,
        "html_body": s.html_body,
        "text_body": s.text_body,
        "from_name": s.from_name,
        "from_email": s.from_email,
    }


def _enrollment_dict(e: NurtureEnrollment) -> dict:
    return {
        "id": str(e.id),
        "sequence_id": str(e.sequence_id),
        "contact_id": str(e.contact_id),
        "status": e.status,
        "current_step": e.current_step,
        "enrolled_at": e.enrolled_at.isoformat(),
        "last_sent_at": e.last_sent_at.isoformat() if e.last_sent_at else None,
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        "trigger_type": e.trigger_type,
        "trigger_value": e.trigger_value,
    }


# ── Sequence endpoints ────────────────────────────────────────────────────────

@router.get("/sequences")
async def list_sequences(
    is_active: Optional[bool] = None,
    trigger_type: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    q = select(NurtureSequence).order_by(col(NurtureSequence.created_at).desc())
    if is_active is not None:
        q = q.where(NurtureSequence.is_active == is_active)
    if trigger_type:
        q = q.where(NurtureSequence.trigger_type == trigger_type)
    seqs = (await db.exec(q)).all()

    # Attach step count
    results = []
    for s in seqs:
        count = (await db.exec(
            select(func.count(NurtureStep.id)).where(NurtureStep.sequence_id == s.id)
        )).first() or 0
        results.append({**_seq_dict(s), "step_count": count})
    return results


@router.post("/sequences", status_code=status.HTTP_201_CREATED)
async def create_sequence(
    payload: SequenceCreate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    now = utcnow_naive()
    seq = NurtureSequence(**payload.model_dump(), created_at=now, updated_at=now)
    db.add(seq)
    await db.commit()
    await db.refresh(seq)
    return _seq_dict(seq)


@router.get("/sequences/{sequence_id}")
async def get_sequence(
    sequence_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    seq = (await db.exec(select(NurtureSequence).where(NurtureSequence.id == sequence_id))).first()
    if not seq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sequence not found")
    steps = (await db.exec(
        select(NurtureStep)
        .where(NurtureStep.sequence_id == sequence_id)
        .order_by(col(NurtureStep.step_order))
    )).all()
    return {**_seq_dict(seq), "steps": [_step_dict(s) for s in steps]}


@router.patch("/sequences/{sequence_id}")
async def update_sequence(
    sequence_id: uuid.UUID,
    payload: SequenceUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    seq = (await db.exec(select(NurtureSequence).where(NurtureSequence.id == sequence_id))).first()
    if not seq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sequence not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(seq, field, value)
    seq.updated_at = utcnow_naive()
    db.add(seq)
    await db.commit()
    await db.refresh(seq)
    return _seq_dict(seq)


@router.delete("/sequences/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence(
    sequence_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    seq = (await db.exec(select(NurtureSequence).where(NurtureSequence.id == sequence_id))).first()
    if not seq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sequence not found")
    await db.delete(seq)
    await db.commit()


# ── Step endpoints ────────────────────────────────────────────────────────────

@router.post("/sequences/{sequence_id}/steps", status_code=status.HTTP_201_CREATED)
async def add_step(
    sequence_id: uuid.UUID,
    payload: StepCreate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    seq = (await db.exec(select(NurtureSequence).where(NurtureSequence.id == sequence_id))).first()
    if not seq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sequence not found")
    now = utcnow_naive()
    step = NurtureStep(**payload.model_dump(), sequence_id=sequence_id, created_at=now, updated_at=now)
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return _step_dict(step)


@router.patch("/steps/{step_id}")
async def update_step(
    step_id: uuid.UUID,
    payload: StepUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    step = (await db.exec(select(NurtureStep).where(NurtureStep.id == step_id))).first()
    if not step:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Step not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(step, field, value)
    step.updated_at = utcnow_naive()
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return _step_dict(step)


@router.delete("/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    step_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    step = (await db.exec(select(NurtureStep).where(NurtureStep.id == step_id))).first()
    if not step:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Step not found")
    await db.delete(step)
    await db.commit()


# ── Enrollment endpoints ──────────────────────────────────────────────────────

@router.post("/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_contact(
    payload: EnrollRequest,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    """Enroll a contact in a nurture sequence."""
    seq = (await db.exec(select(NurtureSequence).where(NurtureSequence.id == payload.sequence_id))).first()
    if not seq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sequence not found")
    contact = (await db.exec(select(Contact).where(Contact.id == payload.contact_id))).first()
    if not contact:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")

    # Check existing active enrollment
    existing = (await db.exec(
        select(NurtureEnrollment)
        .where(NurtureEnrollment.sequence_id == payload.sequence_id)
        .where(NurtureEnrollment.contact_id == payload.contact_id)
        .where(NurtureEnrollment.status == "active")
    )).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Contact already enrolled in this sequence")

    # If allow_re_enrollment=False, also block re-enroll after completion
    if not seq.allow_re_enrollment:
        completed = (await db.exec(
            select(NurtureEnrollment)
            .where(NurtureEnrollment.sequence_id == payload.sequence_id)
            .where(NurtureEnrollment.contact_id == payload.contact_id)
        )).first()
        if completed:
            raise HTTPException(status.HTTP_409_CONFLICT, "Contact already completed this sequence. enable allow_re_enrollment to re-enroll.")

    enrollment = NurtureEnrollment(
        sequence_id=payload.sequence_id,
        contact_id=payload.contact_id,
        status="active",
        current_step=0,
        trigger_type=payload.trigger_type,
        trigger_value=payload.trigger_value,
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return _enrollment_dict(enrollment)


@router.get("/enrollments")
async def list_enrollments(
    sequence_id: Optional[uuid.UUID] = None,
    contact_id: Optional[uuid.UUID] = None,
    enrollment_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    q = select(NurtureEnrollment).order_by(col(NurtureEnrollment.enrolled_at).desc())
    if sequence_id:
        q = q.where(NurtureEnrollment.sequence_id == sequence_id)
    if contact_id:
        q = q.where(NurtureEnrollment.contact_id == contact_id)
    if enrollment_status:
        q = q.where(NurtureEnrollment.status == enrollment_status)
    q = q.offset(offset).limit(min(limit, 200))
    rows = (await db.exec(q)).all()
    return [_enrollment_dict(e) for e in rows]


@router.post("/process")
async def process_due_steps(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Admin/cron endpoint: process all due nurture steps.
    Finds active enrollments where the next step is due, sends email, advances step.
    """
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")

    background_tasks.add_task(_process_all_due_enrollments)
    return {"status": "queued"}


# ── Trigger from intent system ────────────────────────────────────────────────

async def trigger_nurture_for_contact(
    contact_id: uuid.UUID,
    trigger_type: str,
    trigger_value: str,
) -> None:
    """
    Called when a contact's intent stage changes or joins a segment.
    Finds matching active sequences and auto-enrolls the contact.
    """
    from app.db.session import get_session_ctx

    async with get_session_ctx() as db:
        # Find active sequences matching this trigger
        seqs = (await db.exec(
            select(NurtureSequence)
            .where(NurtureSequence.is_active == True)  # noqa: E712
            .where(NurtureSequence.trigger_type == trigger_type)
            .where(NurtureSequence.trigger_value == trigger_value)
        )).all()

        for seq in seqs:
            # Skip if already enrolled
            existing = (await db.exec(
                select(NurtureEnrollment)
                .where(NurtureEnrollment.sequence_id == seq.id)
                .where(NurtureEnrollment.contact_id == contact_id)
                .where(NurtureEnrollment.status == "active")
            )).first()
            if existing:
                continue

            if not seq.allow_re_enrollment:
                any_previous = (await db.exec(
                    select(NurtureEnrollment)
                    .where(NurtureEnrollment.sequence_id == seq.id)
                    .where(NurtureEnrollment.contact_id == contact_id)
                )).first()
                if any_previous:
                    continue

            enrollment = NurtureEnrollment(
                sequence_id=seq.id,
                contact_id=contact_id,
                status="active",
                current_step=0,
                trigger_type=trigger_type,
                trigger_value=trigger_value,
            )
            db.add(enrollment)

        await db.commit()


# ── Background email processing ───────────────────────────────────────────────

async def _process_all_due_enrollments() -> None:
    """
    Process all active enrollments where the next step is due.
    Called as a background task or by a cron-style endpoint.
    """
    from app.db.session import get_session_ctx
    from app.services.email_service import send_nurture_step

    now = utcnow_naive()

    async with get_session_ctx() as db:
        active = (await db.exec(
            select(NurtureEnrollment).where(NurtureEnrollment.status == "active")
        )).all()

        for enrollment in active:
            # Get next step
            steps = (await db.exec(
                select(NurtureStep)
                .where(NurtureStep.sequence_id == enrollment.sequence_id)
                .order_by(col(NurtureStep.step_order))
            )).all()

            if not steps or enrollment.current_step >= len(steps):
                # No more steps — mark complete
                enrollment.status = "completed"
                enrollment.completed_at = now
                db.add(enrollment)
                continue

            step = steps[enrollment.current_step]

            # Calculate when this step should be sent
            base_time = enrollment.last_sent_at or enrollment.enrolled_at
            due_at = base_time + timedelta(days=step.delay_days)

            if now < due_at:
                continue  # Not due yet

            # Get contact email
            contact = (await db.exec(
                select(Contact).where(Contact.id == enrollment.contact_id)
            )).first()
            if not contact:
                enrollment.status = "bounced"
                db.add(enrollment)
                continue

            # Send email
            sent = await send_nurture_step(contact, step)
            if sent:
                enrollment.last_sent_at = now
                enrollment.current_step += 1
                if enrollment.current_step >= len(steps):
                    enrollment.status = "completed"
                    enrollment.completed_at = now
                db.add(enrollment)

        await db.commit()
