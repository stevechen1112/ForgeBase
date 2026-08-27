"""Durable application SLO evaluation and incident lifecycle."""

from __future__ import annotations

import math
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.models.inbound_reply import SalesHandoff
from app.models.knowledge import KnowledgeSyncJob
from app.models.observability import (
    OperationalIncident,
    OperationalIncidentEvent,
    ServiceLevelSnapshot,
)
from app.models.operational_job import OperationalJob
from app.models.outreach import OutreachMessage

_SLO_RETENTION_DAYS = 90
_MIN_RATE_SAMPLE = 20


def _rate_metric(
    *, key: str, label: str, numerator: int, denominator: int, target: float, window: str
) -> dict[str, Any]:
    actual = numerator / denominator if denominator else None
    failures = denominator - numerator
    allowed_failures = math.floor(denominator * (1 - target)) if denominator else 0
    budget_remaining = (
        max(0.0, min(1.0, 1 - failures / max(allowed_failures, 1)))
        if denominator
        else None
    )
    evaluable = denominator >= _MIN_RATE_SAMPLE
    return {
        "key": key,
        "label": label,
        "kind": "rate",
        "window": window,
        "target": target,
        "actual": actual,
        "numerator": numerator,
        "denominator": denominator,
        "evaluable": evaluable,
        "compliant": actual is None or not evaluable or actual >= target,
        "error_budget_remaining": budget_remaining,
    }


def _zero_metric(*, key: str, label: str, actual: int, window: str) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "kind": "zero_tolerance",
        "window": window,
        "target": 0,
        "actual": actual,
        "numerator": None,
        "denominator": None,
        "evaluable": True,
        "compliant": actual == 0,
        "error_budget_remaining": 1.0 if actual == 0 else 0.0,
    }


async def _status_counts(
    db: AsyncSession, model: Any, statuses: list[str], *, since: Any
) -> dict[str, int]:
    rows = (
        await db.exec(
            select(model.status, func.count())
            .where(model.status.in_(statuses), model.updated_at >= since)
            .group_by(model.status)
        )
    ).all()
    return {str(status): int(count) for status, count in rows}


async def evaluate_service_levels(db: AsyncSession) -> dict[str, Any]:
    now = utcnow_naive()
    day_ago = now - timedelta(hours=24)
    month_ago = now - timedelta(days=30)
    stale_before = now - timedelta(minutes=settings.OPS_STALE_JOB_MINUTES)

    operational = await _status_counts(
        db, OperationalJob, ["completed", "failed"], since=day_ago
    )
    knowledge = await _status_counts(
        db, KnowledgeSyncJob, ["succeeded", "failed"], since=day_ago
    )
    outreach = await _status_counts(
        db,
        OutreachMessage,
        [
            "sent",
            "delivered",
            "opened",
            "clicked",
            "replied",
            "bounced",
            "complained",
            "unsubscribed",
            "failed",
        ],
        since=day_ago,
    )
    operational_failed_total = int(
        (
            await db.exec(
                select(func.count()).select_from(OperationalJob).where(
                    OperationalJob.status == "failed"
                )
            )
        ).one()
    )
    stale_operational = int(
        (
            await db.exec(
                select(func.count()).select_from(OperationalJob).where(
                    OperationalJob.status == "processing",
                    OperationalJob.locked_at <= stale_before,
                )
            )
        ).one()
    )
    stale_knowledge = int(
        (
            await db.exec(
                select(func.count()).select_from(KnowledgeSyncJob).where(
                    KnowledgeSyncJob.status == "running",
                    KnowledgeSyncJob.locked_at <= stale_before,
                )
            )
        ).one()
    )
    handoff_rows = (
        await db.exec(
            select(SalesHandoff.sla_breached, func.count())
            .where(SalesHandoff.created_at >= month_ago)
            .group_by(SalesHandoff.sla_breached)
        )
    ).all()
    handoff_counts = {bool(breached): int(count) for breached, count in handoff_rows}

    operational_denominator = sum(operational.values())
    knowledge_denominator = sum(knowledge.values())
    outreach_denominator = sum(outreach.values())
    outreach_failures = (
        outreach.get("failed", 0)
        + outreach.get("bounced", 0)
        + outreach.get("complained", 0)
    )
    handoff_denominator = sum(handoff_counts.values())
    metrics = [
        _rate_metric(
            key="operational_job_success_24h",
            label="核心背景工作成功率",
            numerator=operational.get("completed", 0),
            denominator=operational_denominator,
            target=0.99,
            window="24h",
        ),
        _rate_metric(
            key="knowledge_sync_success_24h",
            label="知識同步成功率",
            numerator=knowledge.get("succeeded", 0),
            denominator=knowledge_denominator,
            target=0.99,
            window="24h",
        ),
        _rate_metric(
            key="outreach_delivery_success_24h",
            label="外聯提交後技術成功率",
            numerator=max(0, outreach_denominator - outreach_failures),
            denominator=outreach_denominator,
            target=0.98,
            window="24h",
        ),
        _rate_metric(
            key="handoff_sla_compliance_30d",
            label="真人接手 SLA 達成率",
            numerator=handoff_counts.get(False, 0),
            denominator=handoff_denominator,
            target=0.95,
            window="30d",
        ),
        _zero_metric(
            key="failed_operational_jobs",
            label="失敗工作總數",
            actual=operational_failed_total,
            window="current",
        ),
        _zero_metric(
            key="stale_queue_claims",
            label="逾時鎖定工作",
            actual=stale_operational + stale_knowledge,
            window=f">{settings.OPS_STALE_JOB_MINUTES}m",
        ),
    ]
    breached = [metric for metric in metrics if not metric["compliant"]]
    insufficient = [metric for metric in metrics if not metric["evaluable"]]
    status = "breached" if breached else "at_risk" if insufficient else "healthy"
    return {
        "status": status,
        "sampled_at": now,
        "metrics": metrics,
        "breached": [metric["key"] for metric in breached],
        "insufficient_evidence": [metric["key"] for metric in insufficient],
        "scope": "application_and_database_internal",
        "external_uptime_claimed": False,
    }


def _incident_definitions(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metrics = {metric["key"]: metric for metric in snapshot["metrics"]}
    return {
        "failed-operational-jobs": {
            "active": metrics["failed_operational_jobs"]["actual"]
            >= settings.OPS_FAILED_JOB_ALERT_THRESHOLD,
            "incident_type": "durable_job_failure",
            "severity": "critical",
            "title": "核心背景工作失敗",
            "summary": f"目前有 {metrics['failed_operational_jobs']['actual']} 筆 terminal failed 工作。",
            "metrics": metrics["failed_operational_jobs"],
        },
        "stale-queue-claims": {
            "active": metrics["stale_queue_claims"]["actual"] > 0,
            "incident_type": "stale_queue_claim",
            "severity": "critical",
            "title": "背景工作鎖定逾時",
            "summary": f"目前有 {metrics['stale_queue_claims']['actual']} 筆工作超過鎖定時限。",
            "metrics": metrics["stale_queue_claims"],
        },
        "operational-job-slo": {
            "active": metrics["operational_job_success_24h"]["evaluable"]
            and not metrics["operational_job_success_24h"]["compliant"],
            "incident_type": "slo_breach",
            "severity": "warning",
            "title": "背景工作 24 小時成功率低於 SLO",
            "summary": "核心背景工作成功率低於 99%。",
            "metrics": metrics["operational_job_success_24h"],
        },
        "knowledge-sync-slo": {
            "active": metrics["knowledge_sync_success_24h"]["evaluable"]
            and not metrics["knowledge_sync_success_24h"]["compliant"],
            "incident_type": "slo_breach",
            "severity": "warning",
            "title": "知識同步 24 小時成功率低於 SLO",
            "summary": "知識同步成功率低於 99%。",
            "metrics": metrics["knowledge_sync_success_24h"],
        },
        "outreach-delivery-slo": {
            "active": metrics["outreach_delivery_success_24h"]["evaluable"]
            and not metrics["outreach_delivery_success_24h"]["compliant"],
            "incident_type": "slo_breach",
            "severity": "critical",
            "title": "外聯寄送技術成功率低於 SLO",
            "summary": "外聯提交後技術成功率低於 98%。",
            "metrics": metrics["outreach_delivery_success_24h"],
        },
        "handoff-sla": {
            "active": metrics["handoff_sla_compliance_30d"]["evaluable"]
            and not metrics["handoff_sla_compliance_30d"]["compliant"],
            "incident_type": "slo_breach",
            "severity": "warning",
            "title": "真人接手 SLA 低於目標",
            "summary": "最近 30 天真人接手 SLA 達成率低於 95%。",
            "metrics": metrics["handoff_sla_compliance_30d"],
        },
    }


async def collect_observability_snapshot(db: AsyncSession) -> dict[str, Any]:
    now = utcnow_naive()
    snapshot = await evaluate_service_levels(db)
    row = ServiceLevelSnapshot(
        status=snapshot["status"], metrics=snapshot["metrics"], sampled_at=now
    )
    db.add(row)
    notification_candidates: list[str] = []
    for incident_key, definition in _incident_definitions(snapshot).items():
        incident = (
            await db.exec(
                select(OperationalIncident).where(
                    OperationalIncident.incident_key == incident_key
                )
            )
        ).first()
        if definition["active"]:
            action = None
            if incident is None:
                incident = OperationalIncident(
                    incident_key=incident_key,
                    incident_type=definition["incident_type"],
                    severity=definition["severity"],
                    title=definition["title"],
                    summary=definition["summary"],
                    metrics=definition["metrics"],
                    first_seen_at=now,
                    last_seen_at=now,
                )
                action = "opened"
            elif incident.status == "resolved":
                incident.status = "open"
                incident.severity = definition["severity"]
                incident.summary = definition["summary"]
                incident.metrics = definition["metrics"]
                incident.last_seen_at = now
                incident.resolved_at = None
                incident.resolved_by = None
                incident.acknowledged_at = None
                incident.acknowledged_by = None
                incident.occurrence_count += 1
                action = "reopened"
            else:
                incident.last_seen_at = now
                incident.summary = definition["summary"]
                incident.metrics = definition["metrics"]
                incident.occurrence_count += 1
            incident.updated_at = now
            db.add(incident)
            if action:
                db.add(
                    OperationalIncidentEvent(
                        incident_id=incident.id,
                        action=action,
                        detail={"metrics": definition["metrics"]},
                    )
                )
            if incident.last_notified_at is None or now - incident.last_notified_at >= timedelta(
                minutes=settings.OPS_ALERT_COOLDOWN_MINUTES
            ):
                notification_candidates.append(str(incident.id))
        elif incident and incident.status != "resolved":
            incident.status = "resolved"
            incident.resolved_at = now
            incident.resolved_by = None
            incident.updated_at = now
            db.add(incident)
            db.add(
                OperationalIncidentEvent(
                    incident_id=incident.id,
                    action="resolved",
                    note="Condition recovered automatically",
                    detail={"automatic": True},
                )
            )
    await db.exec(
        delete(ServiceLevelSnapshot).where(
            ServiceLevelSnapshot.sampled_at < now - timedelta(days=_SLO_RETENTION_DAYS)
        )
    )
    await db.commit()
    snapshot["snapshot_id"] = str(row.id)
    snapshot["notification_candidates"] = notification_candidates
    return snapshot


async def update_incident_status(
    db: AsyncSession,
    *,
    incident: OperationalIncident,
    action: str,
    actor_user_id: uuid.UUID,
    note: str,
) -> OperationalIncident:
    now = utcnow_naive()
    if action == "acknowledge":
        if incident.status == "resolved":
            raise ValueError("resolved_incident")
        if incident.status == "acknowledged":
            raise ValueError("incident_already_acknowledged")
        incident.status = "acknowledged"
        incident.acknowledged_at = now
        incident.acknowledged_by = actor_user_id
        event_action = "acknowledged"
    elif action == "resolve":
        if incident.status == "resolved":
            raise ValueError("incident_already_resolved")
        incident.status = "resolved"
        incident.resolved_at = now
        incident.resolved_by = actor_user_id
        event_action = "resolved"
    else:
        raise ValueError("unknown_action")
    incident.updated_at = now
    db.add(incident)
    db.add(
        OperationalIncidentEvent(
            incident_id=incident.id,
            actor_user_id=actor_user_id,
            action=event_action,
            note=note,
            detail={"automatic": False},
        )
    )
    return incident
