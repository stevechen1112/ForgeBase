"""Prepare one real, allowlisted Reply-To probe and audit its inbound handoff."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.core.encryption import encrypt
from app.db.session import get_session_ctx
from app.models.company_identification import (
    CompanyIdentification,
    NetworkObservation,
)
from app.models.contact_enrichment import ContactCandidate, ContactPersonaPolicy
from app.models.inbound_reply import InboundReply, InboundReplyPolicy, SalesHandoff
from app.models.outreach import (
    JourneySnapshot,
    OutreachDeliveryPolicy,
    OutreachDraftPolicy,
    OutreachMessage,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.models.visitor import Visitor
from app.services.email_governance import (
    email_hash,
    mask_email,
    normalize_email,
)
from app.services.outreach.content_guard import canonical_cta, validate_content
from app.services.outreach.delivery import run_outreach_send_job
from sqlmodel import col, select

from scripts.run_controlled_email_probe import (
    FAILURE_EVENTS,
    SUCCESS_EVENTS,
    _provider_last_event,
    _webhook_events,
)

SCHEMA_VERSION = 1
PROBE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")
TENANT_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
ROOT_DOMAIN = "premierbiz.com.tw"
INBOUND_DOMAIN = "replies.premierbiz.com.tw"


class ControlledInboundProbeError(RuntimeError):
    pass


def _exact_internal_addresses() -> set[str]:
    return {
        normalize_email(value)
        for value in settings.EMAIL_INTERNAL_RECIPIENT_ALLOWLIST.split(",")
        if "@" in value and normalize_email(value)
    }


def _validate_prepare(recipient: str, probe_id: str) -> str:
    normalized = normalize_email(recipient)
    if not PROBE_ID.fullmatch(probe_id):
        raise ControlledInboundProbeError("probe_id_invalid")
    if normalized not in _exact_internal_addresses():
        raise ControlledInboundProbeError("recipient_not_exactly_internal_allowlisted")
    if normalized != normalize_email(settings.EMAIL_FROM):
        raise ControlledInboundProbeError("recipient_must_match_verified_sender")
    if normalized.partition("@")[2] != ROOT_DOMAIN:
        raise ControlledInboundProbeError("recipient_domain_not_controlled")
    if settings.EMAIL_DRY_RUN:
        raise ControlledInboundProbeError("email_dry_run_enabled")
    if not (
        settings.EMAIL_EXTERNAL_DELIVERY_ENABLED
        and settings.OUTREACH_SEND_ENABLED
        and settings.INBOUND_REPLY_ENABLED
    ):
        raise ControlledInboundProbeError("process_scoped_probe_switches_not_enabled")
    if not settings.RESEND_API_KEY.strip():
        raise ControlledInboundProbeError("resend_not_configured")
    if not settings.RESEND_WEBHOOK_SECRET.strip():
        raise ControlledInboundProbeError("resend_webhook_not_configured")
    if settings.OUTREACH_INBOUND_DOMAIN.strip().lower().rstrip(".") != INBOUND_DOMAIN:
        raise ControlledInboundProbeError("inbound_domain_not_expected")
    if len(settings.OUTREACH_INBOUND_SECRET.strip()) < 32:
        raise ControlledInboundProbeError("inbound_route_secret_missing")
    return normalized


def _set_mode(row, mode: str, now: datetime) -> None:
    row.mode = mode
    row.updated_at = now


def _probe_content() -> tuple[str, str, str]:
    subject = "ForgeBase 真人回信閉環驗收（請回覆）"
    body = "這是 ForgeBase 受控內部收件路由、分類與真人接手驗收。"
    validate_content(subject=subject, body_without_cta=body)
    text_body = f"{body}\n\n{canonical_cta('zh-TW')}"
    html_body = "".join(
        f"<p>{html.escape(part)}</p>" for part in text_body.split("\n\n")
    )
    return subject, text_body, html_body


def _actor_is_authorized(actor: User | None) -> bool:
    return bool(
        actor
        and actor.is_active
        and (actor.is_superuser or actor.role in {"admin", "owner"})
    )


def _validate_controlled_identity(
    actor_email: str, tenant_slug: str
) -> tuple[str, str]:
    normalized_actor = normalize_email(actor_email)
    normalized_slug = tenant_slug.strip().lower()
    if not normalized_actor or "@" not in normalized_actor:
        raise ControlledInboundProbeError("controlled_actor_email_required")
    if not TENANT_SLUG.fullmatch(normalized_slug):
        raise ControlledInboundProbeError("controlled_tenant_slug_required")
    return normalized_actor, normalized_slug


async def _resolve_controlled_tenant(db, actor: User, tenant_slug: str) -> Tenant:
    normalized_slug = tenant_slug.strip().lower()
    if not TENANT_SLUG.fullmatch(normalized_slug):
        raise ControlledInboundProbeError("controlled_tenant_slug_required")
    tenant = (
        await db.exec(select(Tenant).where(Tenant.slug == normalized_slug))
    ).one_or_none()
    if not tenant or not tenant.is_active:
        raise ControlledInboundProbeError("controlled_tenant_missing_or_inactive")
    if actor.tenant_id is not None and actor.tenant_id != tenant.id:
        raise ControlledInboundProbeError("controlled_actor_tenant_mismatch")
    if actor.tenant_id is None and not actor.is_superuser:
        raise ControlledInboundProbeError("platform_actor_must_be_superuser")
    return tenant


async def _resolve_controlled_context(
    db, actor_email: str, tenant_slug: str
) -> tuple[User, Tenant]:
    normalized_actor, normalized_slug = _validate_controlled_identity(
        actor_email, tenant_slug
    )
    actor = (
        await db.exec(
            select(User).where(
                User.email == normalized_actor,
                User.is_active.is_(True),
            )
        )
    ).one_or_none()
    if not _actor_is_authorized(actor):
        raise ControlledInboundProbeError("controlled_actor_missing_or_unauthorized")
    return actor, await _resolve_controlled_tenant(db, actor, normalized_slug)


async def _prepare_rows(
    recipient: str, probe_id: str, actor_email: str, tenant_slug: str
) -> OutreachMessage:
    send_key = f"forgebase-inbound-probe:{probe_id}"
    async with get_session_ctx() as db:
        actor, tenant = await _resolve_controlled_context(db, actor_email, tenant_slug)
        existing = (
            await db.exec(
                select(OutreachMessage).where(
                    OutreachMessage.tenant_id == tenant.id,
                    OutreachMessage.send_idempotency_key == send_key,
                )
            )
        ).first()
        if existing:
            return existing

        draft_policy = await db.get(OutreachDraftPolicy, tenant.id)
        delivery_policy = await db.get(OutreachDeliveryPolicy, tenant.id)
        persona_policy = await db.get(ContactPersonaPolicy, tenant.id)
        inbound_policy = await db.get(InboundReplyPolicy, tenant.id)
        if any(
            row and row.mode != "off"
            for row in (draft_policy, delivery_policy, persona_policy, inbound_policy)
        ):
            raise ControlledInboundProbeError("controlled_tenant_policy_not_off")
        overrides = dict(tenant.feature_overrides or {})
        if any(
            overrides.get(key, False)
            for key in ("outreach_send", "inbound_reply", "sales_handoff")
        ):
            raise ControlledInboundProbeError("controlled_tenant_feature_not_off")

        now = utcnow_naive()
        expires = now + timedelta(days=7)
        overrides.update(
            {"outreach_send": True, "inbound_reply": True, "sales_handoff": True}
        )
        tenant.feature_overrides = overrides
        tenant.updated_at = now
        db.add(tenant)

        draft_policy = draft_policy or OutreachDraftPolicy(tenant_id=tenant.id)
        _set_mode(draft_policy, "review_only", now)
        draft_policy.allowed_languages = ["zh-TW"]
        draft_policy.policy_version = "controlled-inbound-v1"
        db.add(draft_policy)

        delivery_policy = delivery_policy or OutreachDeliveryPolicy(tenant_id=tenant.id)
        _set_mode(delivery_policy, "approval_send", now)
        delivery_policy.quiet_hours_enabled = False
        delivery_policy.daily_send_quota = 10
        delivery_policy.frequency_cap_days = 1
        db.add(delivery_policy)

        persona_policy = persona_policy or ContactPersonaPolicy(tenant_id=tenant.id)
        _set_mode(persona_policy, "review_only", now)
        persona_policy.contact_provider_name = "hunter_domain"
        persona_policy.verification_provider_name = "hunter"
        persona_policy.min_relevance_score = 60
        db.add(persona_policy)

        inbound_policy = inbound_policy or InboundReplyPolicy(tenant_id=tenant.id)
        _set_mode(inbound_policy, "review_only", now)
        inbound_policy.handoff_sla_hours = 4
        inbound_policy.content_retention_days = 7
        db.add(inbound_policy)

        visitor = Visitor(
            visitor_id=uuid.uuid4(),
            tenant_id=tenant.id,
            analytics_consent_status="granted",
            is_test_data=True,
            test_run_id=probe_id,
        )
        db.add(visitor)
        await db.flush()
        observation = NetworkObservation(
            tenant_id=tenant.id,
            visitor_id=visitor.visitor_id,
            ip_hash=hashlib.sha256(f"controlled:{probe_id}".encode()).hexdigest(),
            ip_masked="internal-controlled-probe",
            ip_version=4,
            ip_source="internal_test",
            eligibility_status="eligible",
            country="TW",
            consent_state="granted",
            policy_version="controlled-inbound-v1",
            dedupe_key=f"controlled-inbound:{probe_id}",
            observed_at=now,
            expires_at=expires,
        )
        db.add(observation)
        await db.flush()
        company = CompanyIdentification(
            tenant_id=tenant.id,
            visitor_id=visitor.visitor_id,
            network_observation_id=observation.id,
            company_name="Premier Business International Corporation",
            domain=ROOT_DOMAIN,
            provider="internal_controlled_probe",
            candidate_key=f"controlled:{probe_id}",
            confidence=1.0,
            confidence_band="high",
            evidence_json={"controlled_internal_probe": True},
            match_method="internal_allowlist",
            status="confirmed",
            reviewed_by=actor.id,
            reviewed_at=now,
            review_note="Controlled production inbound acceptance",
            expires_at=expires,
        )
        db.add(company)
        await db.flush()
        candidate = ContactCandidate(
            tenant_id=tenant.id,
            company_identification_id=company.id,
            source_company_name=company.company_name,
            source_company_domain=ROOT_DOMAIN,
            full_name="ForgeBase Internal Reviewer",
            job_title="Internal Acceptance Reviewer",
            department="sales",
            seniority="owner",
            location="TW",
            email_ciphertext=encrypt(recipient),
            email_hash=email_hash(recipient),
            email_masked=mask_email(recipient),
            verification_status="verified",
            verification_provider="internal_controlled_probe",
            verified_at=now,
            source_provider="internal_controlled_probe",
            source_person_id=f"controlled:{probe_id}",
            source_freshness=now,
            relevance_score=100,
            relevance_reasons=["exact_internal_allowlist", "controlled_acceptance"],
            confidence=1.0,
            status="approved",
            reviewed_by=actor.id,
            reviewed_at=now,
            review_reason_code="controlled_internal_acceptance",
            review_note="Not provider data; internal acceptance identity",
            expires_at=expires,
        )
        db.add(candidate)
        await db.flush()
        snapshot = JourneySnapshot(
            tenant_id=tenant.id,
            visitor_id=visitor.visitor_id,
            company_identification_id=company.id,
            contact_candidate_id=candidate.id,
            generation_key=f"controlled-inbound:{probe_id}",
            journey_signals={
                "controlled_internal_probe": True,
                "suggested_language": "zh-TW",
            },
            summary="Controlled internal Reply-To and human handoff acceptance.",
            evidence_event_ids=[],
            knowledge_references=[],
            policy_version=draft_policy.policy_version,
            generated_at=now,
            expires_at=expires,
        )
        db.add(snapshot)
        await db.flush()

        subject, text_body, html_body = _probe_content()
        content_hash = hashlib.sha256(
            f"{subject}\n{text_body}\n{html_body}".encode()
        ).hexdigest()
        message = OutreachMessage(
            tenant_id=tenant.id,
            visitor_id=visitor.visitor_id,
            company_identification_id=company.id,
            contact_candidate_id=candidate.id,
            journey_snapshot_id=snapshot.id,
            language="zh-TW",
            to_email_ciphertext=encrypt(recipient),
            to_email_hash=email_hash(recipient),
            to_email_masked=mask_email(recipient),
            subject_snapshot=subject,
            html_snapshot=html_body,
            text_snapshot=text_body,
            personalization_evidence={
                "company": {"name": company.company_name, "domain": company.domain},
                "controlled_internal_probe": True,
            },
            knowledge_version="controlled-inbound-v1",
            prompt_version="controlled-inbound-v1",
            policy_version=draft_policy.policy_version,
            generation_model="deterministic-controlled-probe",
            content_hash=content_hash,
            status="queued",
            approved_by=actor.id,
            approved_at=now,
            review_note="Human-approved controlled internal acceptance",
            created_by=actor.id,
            send_idempotency_key=send_key,
            send_requested_by=actor.id,
            send_requested_at=now,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message


async def _restore_outbound_policy(tenant_id) -> None:
    async with get_session_ctx() as db:
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            return
        overrides = dict(tenant.feature_overrides or {})
        overrides["outreach_send"] = False
        tenant.feature_overrides = overrides
        tenant.updated_at = utcnow_naive()
        db.add(tenant)
        for model in (
            OutreachDraftPolicy,
            OutreachDeliveryPolicy,
            ContactPersonaPolicy,
        ):
            row = await db.get(model, tenant_id)
            if row:
                row.mode = "off"
                row.updated_at = utcnow_naive()
                db.add(row)
        await db.commit()


async def _close_controlled_tenant(tenant_id) -> None:
    async with get_session_ctx() as db:
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise ControlledInboundProbeError("controlled_tenant_missing_during_close")
        overrides = dict(tenant.feature_overrides or {})
        overrides.update(
            {"outreach_send": False, "inbound_reply": False, "sales_handoff": False}
        )
        tenant.feature_overrides = overrides
        tenant.updated_at = utcnow_naive()
        db.add(tenant)
        for model in (
            OutreachDraftPolicy,
            OutreachDeliveryPolicy,
            ContactPersonaPolicy,
            InboundReplyPolicy,
        ):
            row = await db.get(model, tenant.id)
            if row:
                row.mode = "off"
                row.updated_at = utcnow_naive()
                db.add(row)
        await db.commit()


async def close(actor_email: str, tenant_slug: str) -> dict:
    async with get_session_ctx() as db:
        _actor, tenant = await _resolve_controlled_context(db, actor_email, tenant_slug)
        tenant_id = tenant.id
    await _close_controlled_tenant(tenant_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operation": "controlled_internal_reply_window_closed",
        "assessment": {"status": "passed", "controlled_window_closed": True},
        "controls": {
            "tenant_outreach_feature_off": True,
            "tenant_inbound_feature_off": True,
            "tenant_sales_handoff_feature_off": True,
            "all_controlled_policies_off": True,
        },
        "privacy": {
            "recipient_in_report": False,
            "credential_values_in_report": False,
            "message_content_in_report": False,
        },
    }


async def prepare(
    recipient: str, probe_id: str, actor_email: str, tenant_slug: str
) -> dict:
    normalized = _validate_prepare(recipient, probe_id)
    _validate_controlled_identity(actor_email, tenant_slug)
    try:
        message = await _prepare_rows(normalized, probe_id, actor_email, tenant_slug)
    except ControlledInboundProbeError:
        raise
    except Exception as exc:
        raise ControlledInboundProbeError(
            f"prepare_rows_unexpected_{type(exc).__name__}"
        ) from exc
    try:
        try:
            await run_outreach_send_job(message.id)
        finally:
            await _restore_outbound_policy(message.tenant_id)
    except Exception as exc:
        try:
            await _close_controlled_tenant(message.tenant_id)
        except Exception as cleanup_exc:
            raise ControlledInboundProbeError(
                f"delivery_cleanup_unexpected_{type(cleanup_exc).__name__}"
            ) from cleanup_exc
        if isinstance(exc, ControlledInboundProbeError):
            raise
        raise ControlledInboundProbeError(
            f"delivery_unexpected_{type(exc).__name__}"
        ) from exc

    try:
        async with get_session_ctx() as db:
            current = await db.get(OutreachMessage, message.id)
            if (
                not current
                or not current.provider_message_id
                or not current.sent_reply_to
            ):
                raise ControlledInboundProbeError(
                    "provider_send_or_reply_route_missing"
                )
            if not current.sent_reply_to.endswith(f"@{INBOUND_DOMAIN}"):
                raise ControlledInboundProbeError("reply_route_domain_mismatch")
            provider_message_id = current.provider_message_id
    except ControlledInboundProbeError:
        raise
    except Exception as exc:
        raise ControlledInboundProbeError(
            f"delivery_receipt_unexpected_{type(exc).__name__}"
        ) from exc

    provider_event = None
    webhook_events: set[str] = set()
    for attempt in range(31):
        try:
            provider_event, webhook_events = await asyncio.gather(
                _provider_last_event(provider_message_id),
                _webhook_events(provider_message_id),
            )
        except Exception as exc:
            raise ControlledInboundProbeError(
                f"delivery_confirmation_unexpected_{type(exc).__name__}"
            ) from exc
        if provider_event in SUCCESS_EVENTS | FAILURE_EVENTS and webhook_events & (
            SUCCESS_EVENTS | FAILURE_EVENTS
        ):
            break
        if attempt < 30:
            await asyncio.sleep(3)
    delivered = provider_event in SUCCESS_EVENTS and bool(
        webhook_events & SUCCESS_EVENTS
    )
    if not delivered:
        await _close_controlled_tenant(message.tenant_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operation": "controlled_internal_reply_probe_prepared",
        "assessment": {
            "status": "passed" if delivered else "failed",
            "provider_delivery_confirmed": provider_event in SUCCESS_EVENTS,
            "delivery_webhook_confirmed": bool(webhook_events & SUCCESS_EVENTS),
            "reply_route_issued": True,
            "ready_for_human_reply": delivered,
            "blockers": [] if delivered else ["delivery_not_confirmed"],
        },
        "controls": {
            "recipient_exactly_internal_allowlisted": True,
            "automatic_outreach_used": False,
            "tenant_outbound_policy_restored_off": True,
            "tenant_outreach_feature_restored_off": True,
            "inbound_review_window_open": delivered,
        },
        "evidence": {
            "outreach_message_id_sha256": hashlib.sha256(
                str(message.id).encode()
            ).hexdigest(),
            "provider_message_id_sha256": hashlib.sha256(
                provider_message_id.encode()
            ).hexdigest(),
        },
        "privacy": {
            "recipient_in_report": False,
            "reply_address_in_report": False,
            "provider_message_id_in_report": False,
            "credential_values_in_report": False,
            "message_body_in_report": False,
        },
    }


async def status(probe_id: str, tenant_slug: str) -> dict:
    if not PROBE_ID.fullmatch(probe_id):
        raise ControlledInboundProbeError("probe_id_invalid")
    normalized_slug = tenant_slug.strip().lower()
    if not TENANT_SLUG.fullmatch(normalized_slug):
        raise ControlledInboundProbeError("controlled_tenant_slug_required")
    async with get_session_ctx() as db:
        tenant = (
            await db.exec(select(Tenant).where(Tenant.slug == normalized_slug))
        ).one_or_none()
        if not tenant or not tenant.is_active:
            raise ControlledInboundProbeError("controlled_tenant_missing_or_inactive")
        message = (
            await db.exec(
                select(OutreachMessage).where(
                    OutreachMessage.tenant_id == tenant.id,
                    OutreachMessage.send_idempotency_key
                    == f"forgebase-inbound-probe:{probe_id}",
                )
            )
        ).one_or_none()
        if not message:
            raise ControlledInboundProbeError("probe_message_missing")
        replies = list(
            (
                await db.exec(
                    select(InboundReply)
                    .where(InboundReply.outreach_message_id == message.id)
                    .order_by(col(InboundReply.received_at).desc())
                )
            ).all()
        )
        latest = replies[0] if replies else None
        handoff = (
            await db.exec(
                select(SalesHandoff).where(
                    SalesHandoff.outreach_message_id == message.id
                )
            )
        ).first()
    passed = bool(
        latest
        and latest.status == "handed_off"
        and latest.classification in {"positive", "question", "rfq"}
        and handoff
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operation": "controlled_internal_reply_probe_status",
        "assessment": {
            "status": "passed" if passed else "waiting",
            "reply_received": latest is not None,
            "reply_status": latest.status if latest else "not_received",
            "classification": latest.classification if latest else "unknown",
            "handoff_created": handoff is not None,
            "message_status": message.status,
        },
        "privacy": {
            "recipient_in_report": False,
            "reply_address_in_report": False,
            "sender_in_report": False,
            "message_content_in_report": False,
            "credential_values_in_report": False,
        },
    }


def _failure_report(operation: str, reason: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "assessment": {"status": "failed", "blockers": [reason[:100]]},
        "privacy": {
            "recipient_in_report": False,
            "credential_values_in_report": False,
            "message_content_in_report": False,
        },
    }


def _write_report(report: dict, output: str) -> None:
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if output == "-":
        print(payload, end="")
        return
    Path(output).write_text(payload, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("prepare", "status", "close"))
    parser.add_argument("--probe-id", required=True)
    parser.add_argument("--recipient", default="")
    parser.add_argument("--actor-email", default="")
    parser.add_argument("--tenant-slug", default="")
    parser.add_argument(
        "--output",
        required=True,
        help="Write redacted JSON to this path, or '-' for stdout",
    )
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            operation = prepare(
                args.recipient,
                args.probe_id,
                args.actor_email,
                args.tenant_slug,
            )
        elif args.mode == "status":
            operation = status(args.probe_id, args.tenant_slug)
        else:
            operation = close(args.actor_email, args.tenant_slug)
        report = asyncio.run(operation)
    except ControlledInboundProbeError as exc:
        report = _failure_report(args.mode, str(exc))
    except Exception:  # noqa: BLE001 -- never disclose provider or contact data
        report = _failure_report(args.mode, "unexpected_probe_failure")
    _write_report(report, args.output)
    return 0 if report["assessment"]["status"] in {"passed", "waiting"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
