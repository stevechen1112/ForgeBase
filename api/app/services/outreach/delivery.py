"""Human-approved outreach delivery with fail-closed compliance gates."""

from __future__ import annotations

import hashlib
import html
import json
import uuid
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func
from sqlmodel import select

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.core.encryption import decrypt
from app.db.session import get_session_ctx
from app.models.contact_enrichment import ContactCandidate
from app.models.email_delivery import EmailDeliveryEvent, EmailSuppression
from app.models.inbound_reply import InboundReplyPolicy
from app.models.operational_job import OperationalJob
from app.models.outreach import OutreachDeliveryPolicy, OutreachMessage
from app.models.tenant import Tenant
from app.services.email_governance import email_hash, normalize_email
from app.services.email_service import send_email_result
from app.services.inbound_reply.routing import (
    inbound_route_configured,
    issue_reply_to,
    route_hash,
    validate_reply_route,
)
from app.services.outreach.content_guard import (
    OutreachContentError,
    OutreachDraftBlocked,
)
from app.services.outreach.errors import (
    OutreachSendBlocked,
    OutreachSendDeferred,
    OutreachSendRetryable,
)
from app.services.outreach.events import (
    apply_delivery_event,
    link_unknown_delivery_events,
)
from app.services.outreach.runtime import validate_message_for_approval
from app.services.outreach.unsubscribe import (
    issue_unsubscribe_token,
    token_hash,
    verify_unsubscribe_token,
)
from app.services.resend_webhook import resend_webhook_signing_configured
from app.services.capability_access import tenant_has_feature

OUTREACH_SEND_JOB_TYPE = "outreach_send"
_ACTIVE_DELIVERY_STATUSES = {"sent", "delivered", "opened", "clicked", "replied"}


def _scope_key(tenant_id: uuid.UUID, scope: str) -> str:
    return "global" if scope == "global" else f"tenant:{tenant_id}"


def _public_base_url() -> str:
    value = settings.OUTREACH_PUBLIC_BASE_URL.strip().rstrip("/")
    if not value.startswith(("https://", "http://")) or (
        settings.is_production and not value.startswith("https://")
    ):
        raise OutreachSendBlocked("Public unsubscribe URL is not configured")
    return value


def _quiet_delay_seconds(policy: OutreachDeliveryPolicy, now: datetime) -> int:
    if (
        not policy.quiet_hours_enabled
        or policy.quiet_start_hour == policy.quiet_end_hour
    ):
        return 0
    try:
        zone = ZoneInfo(policy.timezone)
    except ZoneInfoNotFoundError as exc:
        raise OutreachSendBlocked("Tenant outreach timezone is invalid") from exc
    local_now = now.replace(tzinfo=timezone.utc).astimezone(zone)
    current = local_now.time().replace(tzinfo=None)
    start = time(policy.quiet_start_hour)
    end = time(policy.quiet_end_hour)
    is_quiet = (
        start <= current < end if start < end else current >= start or current < end
    )
    if not is_quiet:
        return 0
    end_date = local_now.date()
    if start > end and current >= start:
        end_date += timedelta(days=1)
    local_end = datetime.combine(end_date, end, tzinfo=zone)
    return max(1, int((local_end.astimezone(timezone.utc) - local_now).total_seconds()))


def _tenant_day_window(
    policy: OutreachDeliveryPolicy, now: datetime
) -> tuple[datetime, datetime]:
    try:
        zone = ZoneInfo(policy.timezone)
    except ZoneInfoNotFoundError as exc:
        raise OutreachSendBlocked("Tenant outreach timezone is invalid") from exc
    local_now = now.replace(tzinfo=timezone.utc).astimezone(zone)
    local_start = datetime.combine(local_now.date(), time.min, tzinfo=zone)
    local_end = local_start + timedelta(days=1)
    return (
        local_start.astimezone(timezone.utc).replace(tzinfo=None),
        local_end.astimezone(timezone.utc).replace(tzinfo=None),
    )


async def _suppressed(db, tenant_id: uuid.UUID, digest: str) -> bool:
    return bool(
        (
            await db.exec(
                select(EmailSuppression.id).where(
                    EmailSuppression.scope_key.in_(["global", f"tenant:{tenant_id}"]),
                    EmailSuppression.email_hash == digest,
                    EmailSuppression.active.is_(True),
                )
            )
        ).first()
    )


async def _preflight(
    db, message: OutreachMessage, now: datetime
) -> OutreachDeliveryPolicy:
    if (
        not settings.EMAIL_EXTERNAL_DELIVERY_ENABLED
        or not settings.OUTREACH_SEND_ENABLED
    ):
        raise OutreachSendBlocked(
            "Outreach delivery is disabled by a platform kill switch"
        )
    tenant = await db.get(Tenant, message.tenant_id)
    if (
        not tenant
        or not tenant.is_active
        or not tenant_has_feature(tenant, "outreach_send")
    ):
        raise OutreachSendBlocked("Tenant outreach delivery entitlement is disabled")
    policy = (
        await db.exec(
            select(OutreachDeliveryPolicy)
            .where(OutreachDeliveryPolicy.tenant_id == message.tenant_id)
            .with_for_update()
        )
    ).first()
    if not policy or policy.mode != "approval_send":
        raise OutreachSendBlocked("Tenant outreach delivery policy is off")
    if policy.provider_name != "resend":
        raise OutreachSendBlocked("Approval-send currently requires Resend idempotency")
    if not resend_webhook_signing_configured():
        raise OutreachSendBlocked("Resend webhook signing is not configured")
    inbound_policy = await db.get(InboundReplyPolicy, message.tenant_id)
    if (
        inbound_policy
        and inbound_policy.mode == "review_only"
        and (
            not inbound_route_configured()
            or not tenant_has_feature(tenant, "inbound_reply")
            or not tenant_has_feature(tenant, "sales_handoff")
        )
    ):
        raise OutreachSendBlocked("Tenant inbound reply routing is not ready")
    if policy.daily_send_quota == 0:
        raise OutreachSendBlocked("Tenant daily outreach quota is zero")
    if message.status not in {"queued", "sending"}:
        raise OutreachSendBlocked("Message is not queued for delivery")
    if not message.approved_by or not message.approved_at:
        raise OutreachSendBlocked("Human approval is required")
    expected_hash = hashlib.sha256(
        f"{message.subject_snapshot}\n{message.text_snapshot}\n{message.html_snapshot}".encode()
    ).hexdigest()
    if expected_hash != message.content_hash:
        raise OutreachSendBlocked("Approved content integrity check failed")
    if await _suppressed(db, message.tenant_id, message.to_email_hash):
        raise OutreachSendBlocked("Recipient is suppressed")
    candidate = await db.get(ContactCandidate, message.contact_candidate_id)
    if not candidate or candidate.status == "do_not_contact":
        raise OutreachSendBlocked("Recipient is marked do-not-contact")
    await validate_message_for_approval(db, message)

    latest = (
        await db.exec(
            select(func.max(OutreachMessage.revision_no)).where(
                OutreachMessage.tenant_id == message.tenant_id,
                OutreachMessage.contact_candidate_id == message.contact_candidate_id,
            )
        )
    ).one()
    if message.revision_no != int(latest or 0):
        raise OutreachSendBlocked("Only the latest approved revision may be sent")

    quiet_delay = _quiet_delay_seconds(policy, now)
    if quiet_delay:
        raise OutreachSendDeferred("Tenant quiet hours are active", quiet_delay)
    day_start, day_end = _tenant_day_window(policy, now)
    reserved_today = int(
        (
            await db.exec(
                select(func.count())
                .select_from(OutreachMessage)
                .where(
                    OutreachMessage.tenant_id == message.tenant_id,
                    OutreachMessage.id != message.id,
                    func.coalesce(OutreachMessage.sent_at, OutreachMessage.sending_at)
                    >= day_start,
                )
            )
        ).one()
        or 0
    )
    if reserved_today >= policy.daily_send_quota:
        raise OutreachSendDeferred(
            "Tenant daily outreach quota reached", int((day_end - now).total_seconds())
        )
    prior = (
        await db.exec(
            select(OutreachMessage.id).where(
                OutreachMessage.tenant_id == message.tenant_id,
                OutreachMessage.to_email_hash == message.to_email_hash,
                OutreachMessage.id != message.id,
                OutreachMessage.status.in_(_ACTIVE_DELIVERY_STATUSES | {"sending"}),
                func.coalesce(OutreachMessage.sent_at, OutreachMessage.sending_at)
                >= now - timedelta(days=policy.frequency_cap_days),
            )
        )
    ).first()
    if prior:
        raise OutreachSendBlocked("Recipient frequency cap is active")
    return policy


def _delivery_copy(
    message: OutreachMessage, unsubscribe_url: str
) -> tuple[str, str, dict[str, str]]:
    text_footer = f"\n\nStop receiving these emails: {unsubscribe_url}"
    html_footer = (
        '<p style="font-size:12px;color:#666">'
        f'<a href="{html.escape(unsubscribe_url, quote=True)}">Unsubscribe</a></p>'
    )
    headers = {
        "List-Unsubscribe": f"<{unsubscribe_url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        "X-ForgeBase-Outreach-Message": str(message.id),
    }
    return (
        message.text_snapshot + text_footer,
        message.html_snapshot + html_footer,
        headers,
    )


async def run_outreach_send_job(message_id: uuid.UUID, *, retry_count: int = 0) -> None:
    now = utcnow_naive()
    async with get_session_ctx() as db:
        message = (
            await db.exec(
                select(OutreachMessage)
                .where(OutreachMessage.id == message_id)
                .with_for_update()
            )
        ).first()
        if not message:
            raise OutreachSendBlocked("Outreach message not found")
        if message.provider_message_id and message.sent_at:
            return
        if message.sending_at and now - message.sending_at >= timedelta(hours=23):
            message.status = "failed"
            message.last_error = "Idempotency replay window expired before provider acceptance was confirmed"
            message.updated_at = now
            db.add(message)
            await db.commit()
            raise OutreachSendBlocked(message.last_error)
        try:
            policy = await _preflight(db, message, now)
        except OutreachSendDeferred as exc:
            message.scheduled_for = now + timedelta(seconds=exc.delay_seconds)
            message.updated_at = now
            db.add(message)
            await db.commit()
            raise
        except (
            OutreachSendBlocked,
            OutreachDraftBlocked,
            OutreachContentError,
            ValueError,
        ) as exc:
            if (
                message.status in {"queued", "sending"}
                and not message.provider_message_id
            ):
                message.status = "failed"
                message.last_error = str(exc)[:2000]
                message.updated_at = now
                db.add(message)
                await db.commit()
            raise
        try:
            reply_route_digest: str | None = None
            address = normalize_email(decrypt(message.to_email_ciphertext))
            if email_hash(address) != message.to_email_hash:
                raise OutreachSendBlocked("Recipient integrity check failed")
            if message.sent_headers:
                unsubscribe_url = message.sent_headers.get(
                    "List-Unsubscribe", ""
                ).strip("<>")
                token = unsubscribe_url.rsplit("/", 1)[-1]
                if (
                    not message.sent_subject_snapshot
                    or not message.sent_from_name
                    or not message.sent_from_email
                    or not message.sent_text_snapshot
                    or not message.sent_html_snapshot
                    or not message.unsubscribe_token_hash
                    or token_hash(token) != message.unsubscribe_token_hash
                ):
                    raise OutreachSendBlocked("Stored delivery snapshot is incomplete")
                verify_unsubscribe_token(token)
                reply_to = message.sent_reply_to
                if reply_to and (
                    not message.reply_route_token_hash
                    or route_hash(reply_to) != message.reply_route_token_hash
                    or not validate_reply_route(
                        reply_to,
                        message_id=message.id,
                        tenant_id=message.tenant_id,
                        email_digest=message.to_email_hash,
                    )
                ):
                    raise OutreachSendBlocked("Stored reply route is invalid")
            else:
                token = issue_unsubscribe_token(
                    message_id=message.id,
                    tenant_id=message.tenant_id,
                    email_hash=message.to_email_hash,
                    scope=policy.unsubscribe_scope,
                )
                unsubscribe_url = (
                    f"{_public_base_url()}/api/v1/outreach/unsubscribe/{token}"
                )
                inbound_policy = await db.get(InboundReplyPolicy, message.tenant_id)
                if inbound_policy and inbound_policy.mode == "review_only":
                    reply_to, reply_route_digest = issue_reply_to(
                        message_id=message.id,
                        tenant_id=message.tenant_id,
                        email_digest=message.to_email_hash,
                    )
                else:
                    reply_to, reply_route_digest = None, None
        except (OutreachSendBlocked, ValueError) as exc:
            message.status = "failed"
            message.last_error = str(exc)[:2000]
            message.updated_at = now
            db.add(message)
            await db.commit()
            if isinstance(exc, OutreachSendBlocked):
                raise
            raise OutreachSendBlocked(str(exc)) from exc
        if message.sent_headers:
            sent_subject = message.sent_subject_snapshot
            sent_from_name = message.sent_from_name
            sent_from_email = message.sent_from_email
            sent_text = message.sent_text_snapshot
            sent_html = message.sent_html_snapshot
            headers = message.sent_headers
        else:
            sent_subject = message.subject_snapshot
            sent_from_name = settings.EMAIL_FROM_NAME
            sent_from_email = settings.EMAIL_FROM
            sent_text, sent_html, headers = _delivery_copy(message, unsubscribe_url)
        message.status = "sending"
        message.provider = "resend"
        message.send_attempts += 1
        message.sending_at = message.sending_at or now
        message.scheduled_for = None
        message.sent_subject_snapshot = sent_subject
        message.sent_from_name = sent_from_name
        message.sent_from_email = sent_from_email
        message.sent_reply_to = reply_to
        if not message.reply_route_token_hash:
            message.reply_route_token_hash = reply_route_digest
        message.sent_text_snapshot = sent_text
        message.sent_html_snapshot = sent_html
        message.sent_headers = headers
        message.unsubscribe_token_hash = token_hash(token)
        message.last_error = None
        message.updated_at = now
        db.add(message)
        await db.commit()
        idempotency_key = message.send_idempotency_key

    # Recheck mutable recipient controls immediately before the provider call;
    # preparation intentionally commits first so no database lock is held over
    # external I/O.
    async with get_session_ctx() as db:
        current = (
            await db.exec(
                select(OutreachMessage)
                .where(OutreachMessage.id == message_id)
                .with_for_update()
            )
        ).first()
        if not current:
            raise OutreachSendBlocked("Outreach message not found before provider call")
        if current.status in {"cancelled", "bounced", "complained", "unsubscribed"}:
            return
        candidate = await db.get(ContactCandidate, current.contact_candidate_id)
        if (
            await _suppressed(db, current.tenant_id, current.to_email_hash)
            or not candidate
            or candidate.status not in {"approved", "converted"}
            or candidate.verification_status != "verified"
            or candidate.expires_at <= utcnow_naive()
        ):
            current.status = "cancelled"
            current.last_error = (
                "Recipient became ineligible before provider submission"
            )
            current.updated_at = utcnow_naive()
            db.add(current)
            await db.commit()
            return
        if (
            not settings.EMAIL_EXTERNAL_DELIVERY_ENABLED
            or not settings.OUTREACH_SEND_ENABLED
        ):
            current.status = "failed"
            current.last_error = "Platform outreach delivery kill switch changed"
            current.updated_at = utcnow_naive()
            db.add(current)
            await db.commit()
            raise OutreachSendBlocked(current.last_error)

    result = await send_email_result(
        to=address,
        subject=sent_subject,
        html_body=sent_html,
        text_body=sent_text,
        from_name=sent_from_name,
        from_email=sent_from_email,
        idempotency_key=idempotency_key,
        recipient_kind="external",
        message_headers=headers,
        provider_override="resend",
        reply_to=reply_to,
    )
    if result.dry_run:
        error = "Dry-run output is not an external delivery"
    elif not result.success or not result.delivered or not result.message_id:
        error = result.error or "Provider acceptance was not confirmed"
    else:
        error = None

    async with get_session_ctx() as db:
        current = (
            await db.exec(
                select(OutreachMessage)
                .where(OutreachMessage.id == message_id)
                .with_for_update()
            )
        ).first()
        if not current:
            raise OutreachSendBlocked(
                "Outreach message disappeared after provider call"
            )
        if error:
            if current.status in {"cancelled", "bounced", "complained", "unsubscribed"}:
                return
            current.last_error = error[:2000]
            current.updated_at = utcnow_naive()
            if (
                error
                in {
                    "missing_api_key",
                    "external_delivery_disabled",
                    "recipient_suppressed",
                }
                or result.dry_run
            ):
                current.status = "failed"
                db.add(current)
                await db.commit()
                raise OutreachSendBlocked(error)
            db.add(current)
            await db.commit()
            raise OutreachSendRetryable(error)
        current.provider = "resend"
        current.provider_message_id = result.message_id
        accepted_at = utcnow_naive()
        apply_delivery_event(current, "email.sent", accepted_at)
        current.last_error = None
        db.add(
            EmailDeliveryEvent(
                tenant_id=current.tenant_id,
                outreach_message_id=current.id,
                provider="resend",
                provider_event_id=f"forgebase:accepted:{current.id}",
                provider_message_id=result.message_id,
                event_type="email.sent",
                recipient_hash=current.to_email_hash,
                recipient_masked=current.to_email_masked,
                event_data_json=json.dumps({"source": "provider_response"}),
                occurred_at=accepted_at,
            )
        )
        db.add(current)
        await db.commit()
    # The webhook performs the same post-commit reconciliation. Whichever
    # transaction commits last can therefore close the early-webhook race.
    async with get_session_ctx() as db:
        current = (
            await db.exec(
                select(OutreachMessage)
                .where(OutreachMessage.id == message_id)
                .with_for_update()
            )
        ).first()
        if current:
            await link_unknown_delivery_events(db, current)
            db.add(current)
            await db.commit()


async def cancel_queued_for_hash(
    db, *, email_digest: str, tenant_id: uuid.UUID | None, reason: str
) -> int:
    query = select(OutreachMessage).where(
        OutreachMessage.to_email_hash == email_digest,
        OutreachMessage.status == "queued",
    )
    if tenant_id is not None:
        query = query.where(OutreachMessage.tenant_id == tenant_id)
    rows = list((await db.exec(query.with_for_update())).all())
    now = utcnow_naive()
    for row in rows:
        row.status = "cancelled"
        row.last_error = reason[:2000]
        row.updated_at = now
        db.add(row)
        job = (
            await db.exec(
                select(OperationalJob).where(
                    OperationalJob.idempotency_key
                    == f"outreach-send:{row.tenant_id}:{row.id}",
                    OperationalJob.status.in_(["pending", "retry"]),
                )
            )
        ).first()
        if job:
            job.status = "failed"
            job.last_error = reason[:2000]
            job.updated_at = now
            db.add(job)
    return len(rows)


async def record_suppression(
    db,
    *,
    tenant_id: uuid.UUID,
    email_digest: str,
    email_masked: str,
    scope: str,
    reason: str,
    source_event_id: str,
) -> EmailSuppression:
    scope_key = _scope_key(tenant_id, scope)
    row = (
        await db.exec(
            select(EmailSuppression).where(
                EmailSuppression.scope_key == scope_key,
                EmailSuppression.email_hash == email_digest,
            )
        )
    ).first()
    now = utcnow_naive()
    if row:
        row.active = True
        row.reason = reason[:50]
        row.source_event_id = source_event_id[:120]
        row.updated_at = now
    else:
        row = EmailSuppression(
            scope_key=scope_key,
            email_hash=email_digest,
            email_masked=email_masked,
            reason=reason[:50],
            source_event_id=source_event_id[:120],
            active=True,
            provider="forgebase" if reason == "unsubscribe" else "resend",
        )
    db.add(row)
    return row
