import json
import logging
import uuid
from datetime import timedelta
from typing import Any

from sqlmodel import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.db.session import get_session_ctx
from app.models.operational_job import OperationalJob
from app.services.company_identification.providers.base import (
    CompanyProviderPermanentError,
)
from app.services.contact_enrichment.providers import ContactProviderPermanentError
from app.services.inbound_reply.provider import InboundProviderPermanent
from app.services.outreach.content_guard import OutreachDraftBlocked
from app.services.outreach.errors import OutreachSendBlocked, OutreachSendDeferred
from app.services.rfq_auto_reply import AutoReplyDeferred

logger = logging.getLogger(__name__)

_JOB_FEATURES = {
    "rfq_notify": "notifications",
    "company_identify": "company_identification",
    "contact_enrich": "contact_enrichment",
    "journey_summarize": "journey_personalization",
    "outreach_draft": "outreach_review",
    "outreach_send": "outreach_send",
    "inbound_reply_fetch": "inbound_reply",
}


async def _job_feature_enabled(job: OperationalJob) -> bool:
    feature = _JOB_FEATURES.get(job.job_type)
    if not feature:
        return True
    if not job.tenant_id:
        # Legacy jobs created before tenant_id was persisted retain their
        # previous behavior. New enqueue paths always carry tenant_id and are
        # governed by the entitlement.
        return True
    from app.models.tenant import Tenant
    from app.services.capability_access import tenant_has_feature

    async with get_session_ctx() as db:
        tenant = await db.get(Tenant, job.tenant_id)
        return bool(tenant and tenant_has_feature(tenant, feature))


def enqueue_operational_job(
    db: AsyncSession,
    *,
    job_type: str,
    payload: dict[str, Any],
    idempotency_key: str,
    tenant_id: uuid.UUID | None = None,
) -> OperationalJob:
    job = OperationalJob(
        tenant_id=tenant_id,
        job_type=job_type,
        payload_json=json.dumps(payload),
        idempotency_key=idempotency_key,
    )
    db.add(job)
    return job


async def _execute(job: OperationalJob) -> None:
    if not await _job_feature_enabled(job):
        logger.info(
            "Skipping operational job %s because its tenant feature is disabled", job.id
        )
        return
    payload = json.loads(job.payload_json)
    if job.job_type == "rfq_route":
        from app.services.rfq_routing import route_rfq

        await route_rfq(uuid.UUID(payload["rfq_id"]))
    elif job.job_type == "rfq_notify":
        from app.services.notifications import notify_new_rfq

        await notify_new_rfq(uuid.UUID(payload["rfq_id"]))
    elif job.job_type == "rfq_auto_reply":
        from app.services.rfq_auto_reply import maybe_auto_reply

        await maybe_auto_reply(
            uuid.UUID(payload["rfq_id"]), uuid.UUID(payload["tenant_id"])
        )
    elif job.job_type == "company_identify":
        from app.services.company_identification.runtime import (
            run_company_identification_job,
        )

        await run_company_identification_job(
            uuid.UUID(payload["network_observation_id"]),
            retry_count=max(0, job.attempts - 1),
        )
    elif job.job_type == "contact_enrich":
        from app.services.contact_enrichment.runtime import run_contact_enrichment_job

        await run_contact_enrichment_job(
            uuid.UUID(payload["company_identification_id"]),
            retry_count=max(0, job.attempts - 1),
        )
    elif job.job_type == "journey_summarize":
        from app.services.outreach.runtime import run_journey_summarize_job

        await run_journey_summarize_job(uuid.UUID(payload["contact_candidate_id"]))
    elif job.job_type == "outreach_draft":
        from app.services.outreach.runtime import run_outreach_draft_job

        await run_outreach_draft_job(
            uuid.UUID(payload["journey_snapshot_id"]),
            uuid.UUID(payload["contact_candidate_id"]),
        )
    elif job.job_type == "outreach_send":
        from app.services.outreach.delivery import run_outreach_send_job

        await run_outreach_send_job(
            uuid.UUID(payload["outreach_message_id"]),
            retry_count=max(0, job.attempts - 1),
        )
    elif job.job_type == "inbound_reply_fetch":
        from app.services.inbound_reply.runtime import run_inbound_reply_fetch

        await run_inbound_reply_fetch(uuid.UUID(payload["inbound_reply_id"]))
    else:
        raise ValueError(f"Unsupported operational job type: {job.job_type}")


async def _run_worker_maintenance(db: AsyncSession) -> None:
    """Keep auxiliary maintenance failures from stopping the durable queue."""
    from app.services.inbound_reply.runtime import (
        mark_breached_handoff_slas,
        redact_expired_inbound_content,
    )

    for label, operation in (
        ("inbound content retention", redact_expired_inbound_content),
        ("handoff SLA scan", mark_breached_handoff_slas),
    ):
        try:
            async with db.begin_nested():
                await operation(db)
        except Exception:
            logger.exception("Operational outbox maintenance failed: %s", label)


async def process_operational_jobs(
    limit: int = 25, *, job_types: set[str] | None = None
) -> dict[str, int]:
    stats = {"completed": 0, "retried": 0, "failed": 0}
    async with get_session_ctx() as db:
        now = utcnow_naive()
        await _run_worker_maintenance(db)
        statement = select(OperationalJob).where(
            or_(
                (OperationalJob.status.in_(["pending", "retry"]))
                & (OperationalJob.available_at <= now),
                (OperationalJob.status == "processing")
                & (OperationalJob.locked_at <= now - timedelta(minutes=10)),
            ),
        )
        if job_types:
            statement = statement.where(OperationalJob.job_type.in_(job_types))
        jobs = list(
            (
                await db.exec(
                    statement
                    .order_by(OperationalJob.available_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for job in jobs:
            job.status = "processing"
            job.locked_at = now
            job.attempts += 1
            job.updated_at = now
            db.add(job)
        await db.commit()

        for job in jobs:
            try:
                await _execute(job)
                job.status = "completed"
                job.completed_at = utcnow_naive()
                job.locked_at = None
                job.last_error = None
                stats["completed"] += 1
            except AutoReplyDeferred as exc:
                # Scheduling is not a failed attempt. Release the claim and
                # let another short worker tick pick it up at business open.
                job.attempts = max(0, job.attempts - 1)
                job.status = "retry"
                job.available_at = utcnow_naive() + timedelta(seconds=exc.delay_seconds)
                job.locked_at = None
                job.last_error = None
                stats["retried"] += 1
            except OutreachSendDeferred as exc:
                job.attempts = max(0, job.attempts - 1)
                job.status = "retry"
                job.available_at = utcnow_naive() + timedelta(seconds=exc.delay_seconds)
                job.locked_at = None
                job.last_error = None
                stats["retried"] += 1
            except (
                CompanyProviderPermanentError,
                ContactProviderPermanentError,
                InboundProviderPermanent,
                OutreachDraftBlocked,
                OutreachSendBlocked,
            ) as exc:
                job.status = "failed"
                job.locked_at = None
                job.last_error = str(exc)[:2000]
                if job.job_type == "inbound_reply_fetch":
                    from app.models.inbound_reply import InboundReply

                    try:
                        reply_id = uuid.UUID(
                            json.loads(job.payload_json)["inbound_reply_id"]
                        )
                        reply = await db.get(InboundReply, reply_id)
                        if reply and reply.status in {"fetch_pending", "processing"}:
                            reply.status = "failed"
                            reply.processing_error = job.last_error
                            reply.updated_at = utcnow_naive()
                            db.add(reply)
                    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                        logger.exception(
                            "Invalid inbound reply payload for failed job %s", job.id
                        )
                stats["failed"] += 1
            except Exception as exc:
                logger.exception("Operational job failed: %s", job.id)
                job.last_error = str(exc)[:2000]
                job.locked_at = None
                if job.attempts >= job.max_attempts:
                    job.status = "failed"
                    if job.job_type == "outreach_send":
                        from app.models.outreach import OutreachMessage

                        try:
                            message_id = uuid.UUID(
                                json.loads(job.payload_json)["outreach_message_id"]
                            )
                            message = await db.get(OutreachMessage, message_id)
                            if (
                                message
                                and not message.provider_message_id
                                and message.status == "sending"
                            ):
                                message.status = "failed"
                                message.last_error = job.last_error
                                message.updated_at = utcnow_naive()
                                db.add(message)
                        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                            logger.exception(
                                "Invalid outreach send payload for failed job %s",
                                job.id,
                            )
                    elif job.job_type == "inbound_reply_fetch":
                        from app.models.inbound_reply import InboundReply

                        try:
                            reply_id = uuid.UUID(
                                json.loads(job.payload_json)["inbound_reply_id"]
                            )
                            reply = await db.get(InboundReply, reply_id)
                            if reply and reply.status in {
                                "fetch_pending",
                                "processing",
                            }:
                                reply.status = "failed"
                                reply.processing_error = job.last_error
                                reply.updated_at = utcnow_naive()
                                db.add(reply)
                        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                            logger.exception(
                                "Invalid inbound reply payload for failed job %s",
                                job.id,
                            )
                    stats["failed"] += 1
                else:
                    job.status = "retry"
                    retry_after = getattr(exc, "retry_after_seconds", None)
                    delay_seconds = (
                        max(1, min(int(retry_after), 3600))
                        if retry_after is not None
                        else 60 * (2 ** min(job.attempts, 6))
                    )
                    job.available_at = utcnow_naive() + timedelta(seconds=delay_seconds)
                    stats["retried"] += 1
            job.updated_at = utcnow_naive()
            db.add(job)
            await db.commit()
    return stats
