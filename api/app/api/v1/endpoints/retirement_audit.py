"""Platform-only evidence and decision gate for non-core retirement candidates."""

from __future__ import annotations

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
from app.models.rfq_request import RFQRequest
from app.models.user import User
from app.models.visitor import Visitor

router = APIRouter(prefix="/admin/retirement-audit", tags=["Retirement Audit"])
DbDep = Annotated[AsyncSession, Depends(get_session)]
SuperuserDep = Annotated[User, Depends(require_superuser)]


class RetirementDecisionIn(BaseModel):
    status: Literal["retained", "approved_removal"]
    reason: str = Field(min_length=20, max_length=2000)


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
    if candidate_key == "agentos_runtime":
        row = (
            await db.exec(
                select(
                    func.count(RFQRequest.id),
                    func.count(distinct(RFQRequest.tenant_id)),
                    func.max(RFQRequest.updated_at),
                ).where(
                    RFQRequest.agent_run_id.is_not(None),
                    RFQRequest.updated_at >= since,
                )
            )
        ).one()
        return int(row[0]), int(row[1]), row[2], {
            "signal": "RFQs with an AgentOS run id updated in the observation window"
        }
    if candidate_key == "ml_scoring_runtime":
        row = (
            await db.exec(
                select(
                    func.count(Visitor.visitor_id),
                    func.count(distinct(Visitor.tenant_id)),
                    func.max(Visitor.ml_score_updated_at),
                ).where(Visitor.ml_score_updated_at >= since)
            )
        ).one()
        return int(row[0]), int(row[1]), row[2], {
            "signal": "Visitors whose persisted ML score changed in the window"
        }
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
    removal_ready = (
        row.code_state == "disabled"
        and window_complete
        and recent_usage == 0
        and configured_dependencies == 0
        and row.status in {"observing", "approved_removal"}
    )
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
    return {
        "candidate_key": row.candidate_key,
        "display_name": row.display_name,
        "status": row.status,
        "code_state": row.code_state,
        "started_at": row.started_at.isoformat(),
        "required_observation_days": row.required_observation_days,
        "observed_days": observed_days,
        "window_complete": window_complete,
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
    return {
        "generated_at": utcnow_naive().isoformat(),
        "policy": (
            "Removal requires a disabled entry, a completed 30/60-day window, "
            "zero observed usage, data disposition, review and a forward migration."
        ),
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
    if body.status == "approved_removal" and not payload["removal_ready"]:
        raise HTTPException(
            status_code=409,
            detail={"message": "Removal gate has not passed", "blockers": payload["blockers"]},
        )
    now = utcnow_naive()
    previous = row.status
    row.status = body.status
    row.decision_reason = body.reason.strip()
    row.decided_by = current_user.id
    row.decided_at = now
    row.updated_at = now
    db.add(row)
    db.add(
        PlatformAuditLog(
            actor_user_id=current_user.id,
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
                    },
                }
            ),
            created_at=now,
        )
    )
    await db.commit()
    await db.refresh(row)
    return await _candidate_payload(db, row)
