"""
Nurture API — Email Nurture Engine.

GET    /nurture/sequences            list sequences
POST   /nurture/sequences            create sequence
GET    /nurture/sequences/{id}       sequence detail + steps
PATCH  /nurture/sequences/{id}       update sequence
DELETE /nurture/sequences/{id}       delete sequence
POST   /nurture/sequences/{id}/steps add step
PATCH  /nurture/steps/{step_id}      update step
DELETE /nurture/steps/{step_id}      delete step

POST   /nurture/enroll               enroll contact in sequence
GET    /nurture/enrollments          list enrollments
POST   /nurture/process              process due steps (admin)
"""
import uuid
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_admin, require_content_editor
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.contact import Contact
from app.models.nurture import NurtureEnrollment, NurtureSequence, NurtureStep, NurtureOutbox
from app.models.user import User

router = APIRouter(prefix="/nurture", tags=["Nurture"])


class SequenceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str  # "intent_stage" | "segment" | "manual"
    trigger_value: Optional[str] = None
    is_active: bool = True
    allow_re_enrollment: bool = False


class SequenceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_value: Optional[str] = None
    is_active: Optional[bool] = None
    # is_approved is intentionally NOT patchable — use /approve|/unapprove (admin only)
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


def _seq_dict(s: NurtureSequence) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "description": s.description,
        "trigger_type": s.trigger_type,
        "trigger_value": s.trigger_value,
        "is_active": s.is_active,
        "allow_re_enrollment": s.allow_re_enrollment,
        "is_approved": s.is_approved,
        "approved_at": s.approved_at.isoformat() if s.approved_at else None,
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


# ── Sequence endpoints ──────────────────────────────────────────────────────


@router.get("/sequences")
async def list_sequences(
    is_active: Optional[bool] = None,
    trigger_type: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    q = select(NurtureSequence).order_by(col(NurtureSequence.created_at).desc())
    if current_user.tenant_id:
        q = q.where(NurtureSequence.tenant_id == current_user.tenant_id)
    if is_active is not None:
        q = q.where(NurtureSequence.is_active == is_active)
    if trigger_type:
        q = q.where(NurtureSequence.trigger_type == trigger_type)
    seqs = (await db.exec(q)).all()

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
    current_user: User = Depends(require_content_editor),
):
    now = utcnow_naive()
    seq = NurtureSequence(
        **payload.model_dump(),
        tenant_id=current_user.tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(seq)
    await db.commit()
    await db.refresh(seq)
    return _seq_dict(seq)


@router.get("/sequences/{sequence_id}")
async def get_sequence(
    sequence_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    seq = await _get_scoped_sequence(sequence_id, db, current_user)
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
    current_user: User = Depends(require_content_editor),
):
    seq = await _get_scoped_sequence(sequence_id, db, current_user)
    data = payload.model_dump(exclude_unset=True)
    # Hard block: approval fields are admin-only via /approve|/unapprove
    data.pop("is_approved", None)
    data.pop("approved_at", None)
    data.pop("approved_by", None)
    for k, v in data.items():
        setattr(seq, k, v)
    seq.updated_at = utcnow_naive()
    db.add(seq)
    await db.commit()
    await db.refresh(seq)
    return _seq_dict(seq)


@router.post("/sequences/{sequence_id}/approve")
async def approve_sequence(
    sequence_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Approve a sequence so its emails may be sent (admin/owner gate)."""
    seq = await _get_scoped_sequence(sequence_id, db, current_user)
    now = utcnow_naive()
    seq.is_approved = True
    seq.approved_at = now
    seq.approved_by = current_user.id
    seq.updated_at = now
    db.add(seq)
    await db.commit()
    await db.refresh(seq)
    return _seq_dict(seq)


@router.post("/sequences/{sequence_id}/unapprove")
async def unapprove_sequence(
    sequence_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Revoke approval: stops further sends for this sequence."""
    seq = await _get_scoped_sequence(sequence_id, db, current_user)
    seq.is_approved = False
    seq.approved_at = None
    seq.approved_by = None
    seq.updated_at = utcnow_naive()
    db.add(seq)
    await db.commit()
    await db.refresh(seq)
    return _seq_dict(seq)


@router.delete("/sequences/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence(
    sequence_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    seq = await _get_scoped_sequence(sequence_id, db, current_user)
    await db.delete(seq)
    await db.commit()


async def _get_scoped_sequence(
    sequence_id: uuid.UUID, db: AsyncSession, current_user: User
) -> NurtureSequence:
    seq = (await db.exec(select(NurtureSequence).where(NurtureSequence.id == sequence_id))).first()
    if not seq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sequence not found")
    if current_user.tenant_id and seq.tenant_id and seq.tenant_id != current_user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sequence not found")
    return seq


# ── Step endpoints ──────────────────────────────────────────────────────────


@router.post("/sequences/{sequence_id}/steps", status_code=status.HTTP_201_CREATED)
async def add_step(
    sequence_id: uuid.UUID,
    payload: StepCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    seq = await _get_scoped_sequence(sequence_id, db, current_user)
    now = utcnow_naive()
    step = NurtureStep(
        **payload.model_dump(),
        sequence_id=seq.id,
        tenant_id=seq.tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return _step_dict(step)


@router.patch("/steps/{step_id}")
async def update_step(
    step_id: uuid.UUID,
    payload: StepUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    step = await _get_scoped_step(step_id, db, current_user)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(step, k, v)
    step.updated_at = utcnow_naive()
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return _step_dict(step)


@router.delete("/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    step_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    step = await _get_scoped_step(step_id, db, current_user)
    await db.delete(step)
    await db.commit()


async def _get_scoped_step(step_id: uuid.UUID, db: AsyncSession, current_user: User) -> NurtureStep:
    step = (await db.exec(select(NurtureStep).where(NurtureStep.id == step_id))).first()
    if not step:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Step not found")
    await _get_scoped_sequence(step.sequence_id, db, current_user)
    return step


# ── Enrollment endpoints ────────────────────────────────────────────────────


@router.post("/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_contact(
    payload: EnrollRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    seq = await _get_scoped_sequence(payload.sequence_id, db, current_user)
    contact = (await db.exec(select(Contact).where(Contact.id == payload.contact_id))).first()
    if not contact:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")
    # Tenant isolation: contact must belong to the same tenant as the sequence / user
    if seq.tenant_id and contact.tenant_id and contact.tenant_id != seq.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")
    if current_user.tenant_id and contact.tenant_id and contact.tenant_id != current_user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")

    existing = (await db.exec(
        select(NurtureEnrollment)
        .where(NurtureEnrollment.sequence_id == payload.sequence_id)
        .where(NurtureEnrollment.contact_id == payload.contact_id)
        .where(NurtureEnrollment.status == "active")
    )).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Contact already enrolled in this sequence")

    if not seq.allow_re_enrollment:
        completed = (await db.exec(
            select(NurtureEnrollment)
            .where(NurtureEnrollment.sequence_id == payload.sequence_id)
            .where(NurtureEnrollment.contact_id == payload.contact_id)
        )).first()
        if completed:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Contact already completed this sequence. enable allow_re_enrollment to re-enroll.",
            )

    enrollment = NurtureEnrollment(
        sequence_id=payload.sequence_id,
        contact_id=payload.contact_id,
        tenant_id=seq.tenant_id,
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
    current_user: User = Depends(get_current_user),
):
    q = select(NurtureEnrollment).order_by(col(NurtureEnrollment.enrolled_at).desc())
    if current_user.tenant_id:
        q = q.where(NurtureEnrollment.tenant_id == current_user.tenant_id)
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
    _: User = Depends(require_admin),
):
    """Queue processing of all due nurture steps (admin / cron)."""
    background_tasks.add_task(process_all_due_enrollments)
    return {"status": "queued"}


# ── Trigger from intent system ─────────────────────────────────────────────


async def trigger_nurture_for_contact(
    contact_id: uuid.UUID,
    trigger_type: str,
    trigger_value: str,
    tenant_id: Optional[uuid.UUID] = None,
) -> None:
    """Auto-enroll a contact into active sequences matching the trigger."""
    from app.db.session import get_session_ctx

    async with get_session_ctx() as db:
        q = (
            select(NurtureSequence)
            .where(NurtureSequence.is_active == True)  # noqa: E712
            .where(NurtureSequence.trigger_type == trigger_type)
            .where(NurtureSequence.trigger_value == trigger_value)
        )
        if tenant_id:
            q = q.where(NurtureSequence.tenant_id == tenant_id)
        seqs = (await db.exec(q)).all()

        for seq in seqs:
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
                tenant_id=seq.tenant_id,
                status="active",
                current_step=0,
                trigger_type=trigger_type,
                trigger_value=trigger_value,
            )
            db.add(enrollment)

        await db.commit()


# ── Background email processing ────────────────────────────────────────────


async def process_all_due_enrollments() -> dict:
    """Queue due nurture steps into the outbox for manual approval (no auto-send)."""
    from app.db.session import get_session_ctx

    now = utcnow_naive()
    stats = {"queued": 0, "skipped_existing": 0, "completed": 0, "bounced": 0}

    async with get_session_ctx() as db:
        active = (await db.exec(
            select(NurtureEnrollment).where(NurtureEnrollment.status == "active")
        )).all()

        # Approval gate: only queue for sequences explicitly approved by an admin.
        approved_cache: dict = {}
        async def _is_approved(seq_id) -> bool:
            if seq_id not in approved_cache:
                s = (await db.exec(
                    select(NurtureSequence.is_approved).where(NurtureSequence.id == seq_id)
                )).first()
                approved_cache[seq_id] = bool(s)
            return approved_cache[seq_id]

        for enrollment in active:
            if not await _is_approved(enrollment.sequence_id):
                continue

            steps = (await db.exec(
                select(NurtureStep)
                .where(NurtureStep.sequence_id == enrollment.sequence_id)
                .order_by(col(NurtureStep.step_order))
            )).all()

            if not steps or enrollment.current_step >= len(steps):
                enrollment.status = "completed"
                enrollment.completed_at = now
                stats["completed"] += 1
                db.add(enrollment)
                continue

            step = steps[enrollment.current_step]
            base_time = enrollment.last_sent_at or enrollment.enrolled_at
            due_at = base_time + timedelta(days=step.delay_days)

            if now < due_at:
                continue

            contact = (await db.exec(
                select(Contact).where(Contact.id == enrollment.contact_id)
            )).first()
            if not contact:
                enrollment.status = "bounced"
                stats["bounced"] += 1
                db.add(enrollment)
                continue

            # Don't double-queue a pending item for the same enrollment+step.
            existing = (await db.exec(
                select(NurtureOutbox)
                .where(NurtureOutbox.enrollment_id == enrollment.id)
                .where(NurtureOutbox.step_id == step.id)
                .where(NurtureOutbox.status == "pending")
            )).first()
            if existing:
                stats["skipped_existing"] += 1
                continue

            try:
                async with db.begin_nested():
                    db.add(NurtureOutbox(
                        tenant_id=enrollment.tenant_id,
                        enrollment_id=enrollment.id,
                        sequence_id=enrollment.sequence_id,
                        step_id=step.id,
                        contact_id=enrollment.contact_id,
                        status="pending",
                        subject=step.subject,
                        due_at=due_at,
                    ))
                    await db.flush()
                stats["queued"] += 1
            except IntegrityError:
                # Concurrent worker already queued this enrollment+step (partial unique index)
                stats["skipped_existing"] += 1

        await db.commit()

    return stats


async def _advance_enrollment_after_send(
    db: AsyncSession, enrollment: NurtureEnrollment
) -> None:
    """Mark enrollment progress after an outbox email was sent."""
    now = utcnow_naive()
    steps = (await db.exec(
        select(NurtureStep)
        .where(NurtureStep.sequence_id == enrollment.sequence_id)
        .order_by(col(NurtureStep.step_order))
    )).all()
    enrollment.last_sent_at = now
    enrollment.current_step += 1
    if not steps or enrollment.current_step >= len(steps):
        enrollment.status = "completed"
        enrollment.completed_at = now
    db.add(enrollment)


# ── Outbox (manual per-email approval) ─────────────────────────────────────


def _outbox_dict(o: NurtureOutbox) -> dict:
    return {
        "id": str(o.id),
        "enrollment_id": str(o.enrollment_id),
        "sequence_id": str(o.sequence_id),
        "step_id": str(o.step_id),
        "contact_id": str(o.contact_id),
        "status": o.status,
        "subject": o.subject,
        "due_at": o.due_at.isoformat() if o.due_at else None,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "sent_at": o.sent_at.isoformat() if o.sent_at else None,
        "error": o.error,
    }


@router.get("/outbox")
async def list_outbox(
    outbox_status: str = "pending",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    q = select(NurtureOutbox).order_by(col(NurtureOutbox.created_at).desc())
    if current_user.tenant_id:
        q = q.where(NurtureOutbox.tenant_id == current_user.tenant_id)
    if outbox_status:
        q = q.where(NurtureOutbox.status == outbox_status)
    q = q.offset(offset).limit(min(limit, 200))
    rows = (await db.exec(q)).all()
    return [_outbox_dict(o) for o in rows]


async def _get_scoped_outbox(
    outbox_id: uuid.UUID, db: AsyncSession, current_user: User
) -> NurtureOutbox:
    o = (await db.exec(select(NurtureOutbox).where(NurtureOutbox.id == outbox_id))).first()
    if not o:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Outbox item not found")
    if current_user.tenant_id and o.tenant_id and o.tenant_id != current_user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Outbox item not found")
    return o


@router.post("/outbox/{outbox_id}/send")
async def send_outbox_item(
    outbox_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Manually approve and send one queued nurture email."""
    from app.services.email_service import send_nurture_step

    # Atomic claim: lock row so concurrent send/skip cannot double-send
    o = (await db.exec(
        select(NurtureOutbox).where(NurtureOutbox.id == outbox_id).with_for_update()
    )).first()
    if not o:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Outbox item not found")
    if current_user.tenant_id and o.tenant_id and o.tenant_id != current_user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Outbox item not found")
    if o.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Outbox item already {o.status}")

    seq = await _get_scoped_sequence(o.sequence_id, db, current_user)
    if not seq.is_approved:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sequence is not approved for sending")

    step = (await db.exec(select(NurtureStep).where(NurtureStep.id == o.step_id))).first()
    contact = (await db.exec(select(Contact).where(Contact.id == o.contact_id))).first()
    enrollment = (await db.exec(
        select(NurtureEnrollment)
        .where(NurtureEnrollment.id == o.enrollment_id)
        .with_for_update()
    )).first()
    if not step or not contact or not enrollment:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Outbox references missing data")
    if enrollment.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Enrollment already {enrollment.status}")

    # Guard: only send if this outbox still matches the enrollment's current step
    steps = (await db.exec(
        select(NurtureStep)
        .where(NurtureStep.sequence_id == enrollment.sequence_id)
        .order_by(col(NurtureStep.step_order))
    )).all()
    if (
        enrollment.current_step >= len(steps)
        or steps[enrollment.current_step].id != o.step_id
    ):
        o.status = "skipped"
        o.error = "stale step — enrollment already advanced"
        o.reviewed_by = current_user.id
        o.reviewed_at = utcnow_naive()
        db.add(o)
        await db.commit()
        await db.refresh(o)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Outbox step no longer matches enrollment current_step",
        )

    now = utcnow_naive()
    sent = await send_nurture_step(contact, step)
    o.reviewed_by = current_user.id
    o.reviewed_at = now
    if sent:
        o.status = "sent"
        o.sent_at = now
        await _advance_enrollment_after_send(db, enrollment)
    else:
        o.status = "failed"
        o.error = "send failed (check ESP config)"
    db.add(o)
    await db.commit()
    await db.refresh(o)
    return _outbox_dict(o)


@router.post("/outbox/{outbox_id}/skip")
async def skip_outbox_item(
    outbox_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Skip one queued email and advance the enrollment to the next step."""
    o = (await db.exec(
        select(NurtureOutbox).where(NurtureOutbox.id == outbox_id).with_for_update()
    )).first()
    if not o:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Outbox item not found")
    if current_user.tenant_id and o.tenant_id and o.tenant_id != current_user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Outbox item not found")
    if o.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Outbox item already {o.status}")

    enrollment = (await db.exec(
        select(NurtureEnrollment)
        .where(NurtureEnrollment.id == o.enrollment_id)
        .with_for_update()
    )).first()
    now = utcnow_naive()
    o.status = "skipped"
    o.reviewed_by = current_user.id
    o.reviewed_at = now
    db.add(o)
    if enrollment and enrollment.status == "active":
        steps = (await db.exec(
            select(NurtureStep)
            .where(NurtureStep.sequence_id == enrollment.sequence_id)
            .order_by(col(NurtureStep.step_order))
        )).all()
        # Only advance if this outbox is still the current step
        if (
            enrollment.current_step < len(steps)
            and steps[enrollment.current_step].id == o.step_id
        ):
            await _advance_enrollment_after_send(db, enrollment)
    await db.commit()
    await db.refresh(o)
    return _outbox_dict(o)
