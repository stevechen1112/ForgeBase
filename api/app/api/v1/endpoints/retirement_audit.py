"""Platform-only evidence and decision gate for non-core retirement candidates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import col, distinct, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_superuser
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.notification_log import NotificationLog
from app.models.notification_preference import NotificationPreference
from app.models.platform_audit_log import PlatformAuditLog
from app.models.retirement import (
    RetirementCandidateObservation,
    RetirementUsageEvent,
)
from app.models.user import User

router = APIRouter(prefix="/admin/retirement-audit", tags=["Retirement Audit"])
DbDep = Annotated[AsyncSession, Depends(get_session)]
SuperuserDep = Annotated[User, Depends(require_superuser)]


class RetirementDecisionIn(BaseModel):
    status: Literal["retained", "approved_removal"]
    reason: str = Field(min_length=20, max_length=2000)
    telemetry_evidence_ref: str | None = Field(default=None, min_length=5, max_length=500)
    data_disposition: Literal["not_applicable", "retained", "exported", "deleted"] | None = None
    rollback_revision: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{7,40}$"
    )
    removal_plan_ref: str | None = Field(default=None, min_length=5, max_length=500)


def _latest(*values: datetime | None) -> datetime | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


async def _telemetry_usage(
    db: AsyncSession,
    candidate_key: str,
    since: datetime,
) -> tuple[int, int, datetime | None]:
    row = (
        await db.exec(
            select(
                func.count(RetirementUsageEvent.id),
                func.count(distinct(RetirementUsageEvent.tenant_id)),
                func.max(RetirementUsageEvent.occurred_at),
            ).where(
                RetirementUsageEvent.candidate_key == candidate_key,
                RetirementUsageEvent.occurred_at >= since,
            )
        )
    ).one()
    return int(row[0]), int(row[1]), row[2]


async def _domain_usage(
    db: AsyncSession,
    candidate_key: str,
    since: datetime,
) -> tuple[int, int, datetime | None, dict]:
    channel = {
        "notification_telegram": "telegram",
        "notification_line": "line",
    }.get(candidate_key)
    if channel:
        log_row = (
            await db.exec(
                select(
                    func.count(NotificationLog.id),
                    func.count(distinct(NotificationLog.tenant_id)),
                    func.max(NotificationLog.sent_at),
                ).where(
                    NotificationLog.channel == channel,
                    NotificationLog.sent_at >= since,
                )
            )
        ).one()
        enabled_preferences = int(
            (
                await db.exec(
                    select(func.count(NotificationPreference.id)).where(
                        NotificationPreference.channel == channel,
                        NotificationPreference.enabled.is_(True),
                    )
                )
            ).one()
        )
        return int(log_row[0]), int(log_row[1]), log_row[2], {
            "signal": "Notification delivery attempts in the observation window",
            "enabled_preferences": enabled_preferences,
        }
    return 0, 0, None, {"signal": "PII-free retirement usage events"}


async def _candidate_payload(
    db: AsyncSession,
    row: RetirementCandidateObservation,
) -> dict:
    now = utcnow_naive()
    observed_days = max((now - row.started_at).days, 0)
    telemetry_count, telemetry_tenants, telemetry_last = await _telemetry_usage(
        db, row.candidate_key, row.started_at
    )
    domain_count, domain_tenants, domain_last, evidence = await _domain_usage(
        db, row.candidate_key, row.started_at
    )
    recent_usage = telemetry_count + domain_count
    configured_dependencies = int(evidence.get("enabled_preferences", 0))
    window_complete = observed_days >= row.required_observation_days
    technical_removal_ready = (
        row.code_state == "disabled"
        and window_complete
        and recent_usage == 0
        and configured_dependencies == 0
        and row.status in {"observing", "approved_removal"}
    )
    governance_complete = all(
        (
            row.telemetry_verified_at,
            row.telemetry_verified_by,
            row.telemetry_evidence_ref,
            row.data_disposition,
            row.rollback_revision,
            row.removal_plan_ref,
        )
    )
    removal_ready = technical_removal_ready and governance_complete
    blockers: list[str] = []
    if row.code_state == "active":
        blockers.append("entry_not_disabled")
    if not window_complete:
        blockers.append("observation_window_incomplete")
    if recent_usage:
        blockers.append("usage_detected")
    if configured_dependencies:
        blockers.append("configuration_detected")
    if row.status == "retained":
        blockers.append("retained_by_decision")
    if row.code_state != "removed" and (
        not row.telemetry_verified_at or not row.telemetry_verified_by
    ):
        blockers.append("telemetry_continuity_unverified")
    if row.code_state != "removed" and not row.data_disposition:
        blockers.append("data_disposition_missing")
    if row.code_state != "removed" and not row.rollback_revision:
        blockers.append("rollback_revision_missing")
    if row.code_state != "removed" and not row.removal_plan_ref:
        blockers.append("removal_plan_missing")
    return {
        "candidate_key": row.candidate_key,
        "display_name": row.display_name,
        "status": row.status,
        "code_state": row.code_state,
        "started_at": row.started_at.isoformat(),
        "required_observation_days": row.required_observation_days,
        "observed_days": observed_days,
        "window_complete": window_complete,
        "technical_removal_ready": technical_removal_ready,
        "recent_usage_count": recent_usage,
        "tenant_count": max(telemetry_tenants, domain_tenants),
        "last_used_at": (
            _latest(telemetry_last, domain_last).isoformat()
            if _latest(telemetry_last, domain_last)
            else None
        ),
        "removal_ready": removal_ready,
        "blockers": blockers,
        "evidence": {
            **evidence,
            "telemetry_events": telemetry_count,
            "domain_records": domain_count,
            "stores_request_payload_or_pii": False,
        },
        "decision": {
            "reason": row.decision_reason,
            "decided_at": row.decided_at.isoformat() if row.decided_at else None,
            "decided_by": str(row.decided_by) if row.decided_by else None,
            "telemetry_verified_at": row.telemetry_verified_at.isoformat()
            if row.telemetry_verified_at
            else None,
            "telemetry_verified_by": str(row.telemetry_verified_by)
            if row.telemetry_verified_by
            else None,
            "telemetry_evidence_ref": row.telemetry_evidence_ref,
            "data_disposition": row.data_disposition,
            "rollback_revision": row.rollback_revision,
            "removal_plan_ref": row.removal_plan_ref,
        },
    }


@router.get("")
async def retirement_audit_report(db: DbDep, _: SuperuserDep):
    rows = list(
        (
            await db.exec(
                select(RetirementCandidateObservation).order_by(
                    col(RetirementCandidateObservation.candidate_key)
                )
            )
        ).all()
    )
    candidates = [await _candidate_payload(db, row) for row in rows]
    policy = (
        "Removal requires a disabled entry, a completed 30/60-day window, "
        "zero observed usage, verified telemetry continuity, explicit data "
        "disposition, an immutable rollback revision and a reviewed removal plan."
    )
    snapshot = {"policy": policy, "candidates": candidates}
    report_sha256 = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "generated_at": utcnow_naive().isoformat(),
        "report_sha256": report_sha256,
        "policy": policy,
        "candidates": candidates,
    }


@router.put("/{candidate_key}/decision")
async def decide_retirement_candidate(
    candidate_key: str,
    body: RetirementDecisionIn,
    db: DbDep,
    current_user: SuperuserDep,
):
    row = await db.get(RetirementCandidateObservation, candidate_key)
    if not row:
        raise HTTPException(status_code=404, detail="Retirement candidate not found")
    if row.status == "removed":
        raise HTTPException(status_code=409, detail="Removed decisions are immutable")
    payload = await _candidate_payload(db, row)
    if body.status == "approved_removal":
        if not payload["technical_removal_ready"]:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Technical removal gate has not passed",
                    "blockers": payload["blockers"],
                },
            )
        governance = {
            "telemetry_evidence_ref": body.telemetry_evidence_ref,
            "data_disposition": body.data_disposition,
            "rollback_revision": body.rollback_revision,
            "removal_plan_ref": body.removal_plan_ref,
        }
        missing = [key for key, value in governance.items() if not value]
        if missing:
            raise HTTPException(
                status_code=409,
                detail={"message": "Retirement governance evidence missing", "missing": missing},
            )
    now = utcnow_naive()
    previous = row.status
    row.status = body.status
    row.decision_reason = body.reason.strip()
    row.decided_by = current_user.id
    row.decided_at = now
    if body.status == "approved_removal":
        row.telemetry_verified_at = now
        row.telemetry_verified_by = current_user.id
        row.telemetry_evidence_ref = body.telemetry_evidence_ref
        row.data_disposition = body.data_disposition
        row.rollback_revision = body.rollback_revision
        row.removal_plan_ref = body.removal_plan_ref
    row.updated_at = now
    db.add(row)
    db.add(
        PlatformAuditLog(
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            action="retirement_candidate_decided",
            target_type="retirement_candidate",
            target_id=candidate_key,
            changes_json=json.dumps(
                {
                    "previous_status": previous,
                    "status": body.status,
                    "reason": body.reason.strip(),
                    "evidence": {
                        "observed_days": payload["observed_days"],
                        "recent_usage_count": payload["recent_usage_count"],
                        "code_state": payload["code_state"],
                        "telemetry_evidence_ref": body.telemetry_evidence_ref,
                        "data_disposition": body.data_disposition,
                        "rollback_revision": body.rollback_revision,
                        "removal_plan_ref": body.removal_plan_ref,
                    },
                }
            ),
            created_at=now,
        )
    )
    await db.commit()
    await db.refresh(row)
    return await _candidate_payload(db, row)
