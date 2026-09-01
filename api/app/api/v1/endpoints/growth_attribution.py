"""Tenant-scoped North Star lineage, funnel, quality, cost and readiness APIs."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import case, distinct
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import (
    get_current_user,
    require_rfq_manager,
    require_user_tenant_id,
)
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.attribution import AttributionEvent, AttributionLink
from app.models.company_identification import (
    CompanyIdentification,
    IdentificationReview,
    ProviderUsage,
)
from app.models.contact_enrichment import ContactCandidate, ContactCandidateReview
from app.models.inbound_reply import InboundReply, SalesHandoff
from app.models.outreach import (
    OutreachDeliveryPolicy,
    OutreachMessage,
    OutreachMessageReview,
)
from app.models.rfq_request import RFQRequest
from app.models.user import User
from app.models.visitor import Visitor
from app.services.attribution import derive_attribution, override_attribution

router = APIRouter(prefix="/tracking", tags=["North Star Attribution"])
DbDep = Annotated[AsyncSession, Depends(get_session)]
UserDep = Annotated[User, Depends(get_current_user)]
ManagerDep = Annotated[User, Depends(require_rfq_manager)]

ATTRIBUTION_TYPES = ("direct", "assisted", "unknown", "manual")
MESSAGE_APPROVED_STATES = (
    "approved", "queued", "sending", "sent", "delivered", "opened", "clicked",
    "replied", "bounced", "complained", "unsubscribed", "failed",
)
MESSAGE_SENT_STATES = (
    "sent", "delivered", "opened", "clicked", "replied", "bounced",
    "complained", "unsubscribed",
)
MESSAGE_DELIVERED_STATES = ("delivered", "opened", "clicked", "replied")


class AttributionOverrideIn(BaseModel):
    attribution_type: Literal["direct", "assisted", "unknown", "manual"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=10, max_length=2000)


async def _count(db: AsyncSession, query) -> int:
    return int((await db.exec(select(func.count()).select_from(query.subquery()))).one())


def _rate(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate_pct": round(numerator / denominator * 100, 2) if denominator else None,
    }


def _attribution_dict(row: AttributionLink, events: list[AttributionEvent] | None = None) -> dict:
    return {
        "id": str(row.id),
        "rfq_request_id": str(row.rfq_request_id),
        "attribution_type": row.attribution_type,
        "confidence": row.confidence,
        "manually_overridden": row.manually_overridden,
        "override_reason": row.override_reason,
        "overridden_by": str(row.overridden_by) if row.overridden_by else None,
        "overridden_at": row.overridden_at.isoformat() if row.overridden_at else None,
        "lineage": {
            key: str(getattr(row, key)) if getattr(row, key) else None
            for key in (
                "visitor_id", "company_identification_id", "contact_candidate_id",
                "contact_id", "journey_snapshot_id", "outreach_message_id",
                "inbound_reply_id", "sales_handoff_id",
            )
        },
        "evidence": row.evidence,
        "derivation_version": row.derivation_version,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "events": [
            {
                "id": str(event.id),
                "action": event.action,
                "previous_type": event.previous_type,
                "attribution_type": event.attribution_type,
                "confidence": event.confidence,
                "reason": event.reason,
                "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
                "evidence": event.evidence,
                "created_at": event.created_at.isoformat(),
            }
            for event in (events or [])
        ],
    }


async def _north_star_layers(db: AsyncSession, tenant_id: uuid.UUID, since) -> list[dict]:
    cohort = select(Visitor.visitor_id).where(
        Visitor.tenant_id == tenant_id,
        Visitor.first_seen >= since,
        Visitor.is_test_data.is_(False),
    )
    cohort_ids = cohort.subquery()

    async def visitors(query) -> int:
        return int((await db.exec(select(func.count(distinct(query))))).one() or 0)

    tracked = await _count(db, cohort)
    company = await visitors(
        select(CompanyIdentification.visitor_id)
        .where(
            CompanyIdentification.tenant_id == tenant_id,
            CompanyIdentification.visitor_id.in_(select(cohort_ids.c.visitor_id)),
            CompanyIdentification.status.not_in(("rejected", "expired")),
        )
        .subquery().c.visitor_id
    )
    high_company = await visitors(
        select(CompanyIdentification.visitor_id)
        .where(
            CompanyIdentification.tenant_id == tenant_id,
            CompanyIdentification.visitor_id.in_(select(cohort_ids.c.visitor_id)),
            CompanyIdentification.confidence_band == "high",
            CompanyIdentification.status.in_(("candidate", "confirmed")),
        )
        .subquery().c.visitor_id
    )
    qualified_contact = await visitors(
        select(CompanyIdentification.visitor_id)
        .join(
            ContactCandidate,
            ContactCandidate.company_identification_id == CompanyIdentification.id,
        )
        .where(
            CompanyIdentification.tenant_id == tenant_id,
            CompanyIdentification.visitor_id.in_(select(cohort_ids.c.visitor_id)),
            ContactCandidate.tenant_id == tenant_id,
            ContactCandidate.status.in_(("approved", "converted")),
            ContactCandidate.verification_status == "verified",
        )
        .subquery().c.visitor_id
    )

    async def message_visitors(*conditions) -> int:
        return await visitors(
            select(OutreachMessage.visitor_id)
            .where(
                OutreachMessage.tenant_id == tenant_id,
                OutreachMessage.visitor_id.in_(select(cohort_ids.c.visitor_id)),
                *conditions,
            )
            .subquery().c.visitor_id
        )

    approved = await message_visitors(OutreachMessage.status.in_(MESSAGE_APPROVED_STATES))
    sent = await message_visitors(OutreachMessage.status.in_(MESSAGE_SENT_STATES))
    delivered = await message_visitors(OutreachMessage.status.in_(MESSAGE_DELIVERED_STATES))
    replied = await visitors(
        select(OutreachMessage.visitor_id)
        .join(InboundReply, InboundReply.outreach_message_id == OutreachMessage.id)
        .where(
            OutreachMessage.tenant_id == tenant_id,
            OutreachMessage.visitor_id.in_(select(cohort_ids.c.visitor_id)),
            InboundReply.tenant_id == tenant_id,
        )
        .subquery().c.visitor_id
    )
    positive = await visitors(
        select(OutreachMessage.visitor_id)
        .join(InboundReply, InboundReply.outreach_message_id == OutreachMessage.id)
        .where(
            OutreachMessage.tenant_id == tenant_id,
            OutreachMessage.visitor_id.in_(select(cohort_ids.c.visitor_id)),
            InboundReply.tenant_id == tenant_id,
            InboundReply.classification.in_(("positive", "question", "rfq")),
        )
        .subquery().c.visitor_id
    )
    handoff = await visitors(
        select(OutreachMessage.visitor_id)
        .join(SalesHandoff, SalesHandoff.outreach_message_id == OutreachMessage.id)
        .where(
            OutreachMessage.tenant_id == tenant_id,
            OutreachMessage.visitor_id.in_(select(cohort_ids.c.visitor_id)),
            SalesHandoff.tenant_id == tenant_id,
        )
        .subquery().c.visitor_id
    )
    rfq = await visitors(
        select(RFQRequest.visitor_id)
        .where(
            RFQRequest.tenant_id == tenant_id,
            RFQRequest.visitor_id.in_(select(cohort_ids.c.visitor_id)),
            RFQRequest.is_test_data.is_(False),
            RFQRequest.is_spam.is_(False),
            RFQRequest.merged_into_rfq_id.is_(None),
        )
        .subquery().c.visitor_id
    )
    won = await visitors(
        select(RFQRequest.visitor_id)
        .where(
            RFQRequest.tenant_id == tenant_id,
            RFQRequest.visitor_id.in_(select(cohort_ids.c.visitor_id)),
            RFQRequest.status == "won",
            RFQRequest.is_test_data.is_(False),
            RFQRequest.is_spam.is_(False),
            RFQRequest.merged_into_rfq_id.is_(None),
        )
        .subquery().c.visitor_id
    )
    definitions = [
        ("tracked_visitors", "可追蹤訪客", tracked),
        ("company_candidate", "公司候選", company),
        ("high_confidence_company", "高信心公司", high_company),
        ("qualified_contact", "合格聯絡窗口", qualified_contact),
        ("approved_outreach", "已核准外聯", approved),
        ("sent", "已寄送", sent),
        ("delivered", "已送達", delivered),
        ("replied", "已回覆", replied),
        ("positive_reply", "正向／問題／RFQ 回覆", positive),
        ("handoff", "真人接手", handoff),
        ("rfq", "RFQ", rfq),
        ("won", "成交", won),
    ]
    layers: list[dict] = []
    for index, (key, label, count) in enumerate(definitions):
        previous = definitions[index - 1][2] if index else None
        layers.append(
            {
                "stage": key,
                "label": label,
                "count": count,
                "previous_count": previous,
                "conversion_from_previous_pct": (
                    round(count / previous * 100, 2) if previous else None
                ),
                "drop_off": max(previous - count, 0) if previous is not None else None,
            }
        )
    return layers


@router.get("/growth-funnel")
async def growth_funnel(
    db: DbDep,
    current_user: UserDep,
    days: int = Query(default=30, ge=1, le=365),
):
    tenant_id = require_user_tenant_id(current_user)
    since = utcnow_naive() - timedelta(days=days)
    layers = await _north_star_layers(db, tenant_id, since)
    attribution_kind = func.coalesce(AttributionLink.attribution_type, "unknown")
    attribution_rows = list(
        (
            await db.exec(
                select(
                    attribution_kind,
                    func.count(RFQRequest.id),
                    func.coalesce(
                        func.sum(
                            case(
                                (RFQRequest.status == "won", RFQRequest.deal_amount),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                )
                .select_from(RFQRequest)
                .outerjoin(
                    AttributionLink,
                    (AttributionLink.rfq_request_id == RFQRequest.id)
                    & (AttributionLink.tenant_id == tenant_id),
                )
                .where(
                    RFQRequest.tenant_id == tenant_id,
                    RFQRequest.created_at >= since,
                    RFQRequest.is_test_data.is_(False),
                    RFQRequest.is_spam.is_(False),
                    RFQRequest.merged_into_rfq_id.is_(None),
                )
                .group_by(attribution_kind)
            )
        ).all()
    )
    attributed = {
        kind: {"count": int(count), "won_revenue": str(amount or Decimal(0))}
        for kind, count, amount in attribution_rows
    }
    for kind in ATTRIBUTION_TYPES:
        attributed.setdefault(kind, {"count": 0, "won_revenue": "0"})
    return {
        "days": days,
        "cohort_start": since.isoformat(),
        "cohort": "tenant visitors first seen in period; every stage counts distinct visitor IDs",
        "layers": layers,
        "attribution": attributed,
        "warning": "Direct is assigned only when an RFQ is created from the same reviewed inbound reply handoff; linked existing RFQs are assisted.",
    }


@router.get("/growth-funnel/costs")
async def growth_funnel_costs(
    db: DbDep,
    current_user: UserDep,
    days: int = Query(default=30, ge=1, le=365),
):
    tenant_id = require_user_tenant_id(current_user)
    since = utcnow_naive() - timedelta(days=days)
    usage = list(
        (
            await db.exec(
                select(
                    ProviderUsage.provider,
                    ProviderUsage.operation,
                    func.count(ProviderUsage.id),
                    func.sum(ProviderUsage.units),
                    func.sum(ProviderUsage.estimated_cost),
                )
                .where(
                    ProviderUsage.tenant_id == tenant_id,
                    ProviderUsage.created_at >= since,
                )
                .group_by(ProviderUsage.provider, ProviderUsage.operation)
            )
        ).all()
    )
    sent = await _count(
        db,
        select(OutreachMessage.id).where(
            OutreachMessage.tenant_id == tenant_id,
            OutreachMessage.sent_at >= since,
        ),
    )
    replies = await _count(
        db,
        select(InboundReply.id).where(
            InboundReply.tenant_id == tenant_id,
            InboundReply.received_at >= since,
        ),
    )
    total_cost = sum((Decimal(str(row[4] or 0)) for row in usage), Decimal(0))
    return {
        "days": days,
        "sample": {"sent": sent, "replies": replies},
        "provider_usage": [
            {
                "provider": provider,
                "operation": operation,
                "requests": int(requests),
                "units": int(units or 0),
                "estimated_cost": str(cost or Decimal(0)),
            }
            for provider, operation, requests, units, cost in usage
        ],
        "total_estimated_cost": str(total_cost),
        "cost_per_sent": str(total_cost / sent) if sent else None,
        "cost_per_reply": str(total_cost / replies) if replies else None,
        "currency": "provider-ledger units; do not combine currencies unless provider configuration is normalized",
    }


async def _quality_payload(db: AsyncSession, tenant_id: uuid.UUID, since) -> dict:
    id_reviews = list(
        (
            await db.exec(
                select(IdentificationReview.decision)
                .join(
                    CompanyIdentification,
                    CompanyIdentification.id
                    == IdentificationReview.company_identification_id,
                )
                .where(
                    IdentificationReview.tenant_id == tenant_id,
                    IdentificationReview.reviewed_at >= since,
                    CompanyIdentification.tenant_id == tenant_id,
                    CompanyIdentification.confidence_band == "high",
                )
            )
        ).all()
    )
    contact_reviews = list(
        (
            await db.exec(
                select(ContactCandidateReview.decision).where(
                    ContactCandidateReview.tenant_id == tenant_id,
                    ContactCandidateReview.created_at >= since,
                )
            )
        ).all()
    )
    reviews = list(
        (
            await db.exec(
                select(OutreachMessageReview.action, OutreachMessageReview.reason_code).where(
                    OutreachMessageReview.tenant_id == tenant_id,
                    OutreachMessageReview.created_at >= since,
                )
            )
        ).all()
    )
    sent_rows = list(
        (
            await db.exec(
                select(
                    OutreachMessage.bounced_at,
                    OutreachMessage.complained_at,
                    OutreachMessage.unsubscribed_at,
                ).where(
                    OutreachMessage.tenant_id == tenant_id,
                    OutreachMessage.sent_at >= since,
                )
            )
        ).all()
    )
    handoffs = list(
        (
            await db.exec(
                select(
                    SalesHandoff.accepted_at,
                    SalesHandoff.created_at,
                    SalesHandoff.sla_due_at,
                    SalesHandoff.sla_breached,
                    SalesHandoff.rfq_id,
                ).where(
                    SalesHandoff.tenant_id == tenant_id,
                    SalesHandoff.created_at >= since,
                )
            )
        ).all()
    )
    decisions = [action for action, _ in reviews if action in {"approved", "rejected"}]
    unsupported = sum(
        1
        for action, reason in reviews
        if action == "rejected" and reason in {"unsupported_claim", "unverified_claim"}
    )
    reply_total = await _count(
        db,
        select(InboundReply.id).where(
            InboundReply.tenant_id == tenant_id,
            InboundReply.received_at >= since,
        ),
    )
    positive_replies = await _count(
        db,
        select(InboundReply.id).where(
            InboundReply.tenant_id == tenant_id,
            InboundReply.received_at >= since,
            InboundReply.classification.in_(("positive", "question", "rfq")),
        ),
    )
    sent_count = len(sent_rows)
    return {
        "company_high_confidence_precision": _rate(id_reviews.count("confirm"), len(id_reviews)),
        "contact_relevance_acceptance": _rate(
            sum(1 for item in contact_reviews if item in {"approve", "convert"}),
            len(contact_reviews),
        ),
        "draft_approval": _rate(decisions.count("approved"), len(decisions)),
        "draft_revision": _rate(
            sum(1 for action, _ in reviews if action == "revised"),
            sum(1 for action, _ in reviews if action == "generated"),
        ),
        "unsupported_claim": _rate(unsupported, len(decisions)),
        "bounce": _rate(sum(1 for row in sent_rows if row[0]), sent_count),
        "complaint": _rate(sum(1 for row in sent_rows if row[1]), sent_count),
        "unsubscribe": _rate(sum(1 for row in sent_rows if row[2]), sent_count),
        "reply": _rate(reply_total, sent_count),
        "positive_reply": _rate(positive_replies, reply_total),
        "handoff_acceptance": _rate(sum(1 for row in handoffs if row[0]), len(handoffs)),
        "handoff_sla_met": _rate(
            sum(1 for row in handoffs if row[0] and row[0] <= row[2] and not row[3]),
            len(handoffs),
        ),
        "handoff_to_rfq": _rate(sum(1 for row in handoffs if row[4]), len(handoffs)),
    }


@router.get("/growth-funnel/quality")
async def growth_funnel_quality(
    db: DbDep,
    current_user: UserDep,
    days: int = Query(default=30, ge=1, le=365),
):
    tenant_id = require_user_tenant_id(current_user)
    return {
        "days": days,
        "metrics": await _quality_payload(
            db, tenant_id, utcnow_naive() - timedelta(days=days)
        ),
        "note": "Every rate includes numerator and denominator; empty samples return null instead of zero-quality claims.",
    }


@router.get("/controlled-auto/readiness")
async def controlled_auto_readiness(
    db: DbDep,
    current_user: UserDep,
    days: int = Query(default=30, ge=30, le=365),
):
    tenant_id = require_user_tenant_id(current_user)
    policy = await db.get(OutreachDeliveryPolicy, tenant_id)
    metrics = await _quality_payload(
        db, tenant_id, utcnow_naive() - timedelta(days=days)
    )
    checks = {
        "tenant_opt_in": bool(policy and policy.controlled_auto_opt_in),
        "legal_review": bool(policy and policy.controlled_auto_legal_approved),
        "region_allowlist": bool(policy and policy.controlled_auto_allowed_regions),
        "persona_allowlist": bool(policy and policy.controlled_auto_allowed_personas),
        "template_allowlist": bool(policy and policy.controlled_auto_allowed_templates),
        "company_precision": (
            metrics["company_high_confidence_precision"]["denominator"] >= 50
            and (metrics["company_high_confidence_precision"]["rate_pct"] or 0) >= 90
        ),
        "contact_relevance": (
            metrics["contact_relevance_acceptance"]["denominator"] >= 50
            and (metrics["contact_relevance_acceptance"]["rate_pct"] or 0) >= 70
        ),
        "delivery_sample": metrics["bounce"]["denominator"] >= 100,
        "unsupported_claim_zero": metrics["unsupported_claim"]["numerator"] == 0
        and metrics["unsupported_claim"]["denominator"] >= 100,
        "bounce_below_2pct": metrics["bounce"]["rate_pct"] is not None
        and metrics["bounce"]["rate_pct"] < 2,
        "complaint_below_0_1pct": metrics["complaint"]["rate_pct"] is not None
        and metrics["complaint"]["rate_pct"] < 0.1,
        "unsubscribe_below_1pct": metrics["unsubscribe"]["rate_pct"] is not None
        and metrics["unsubscribe"]["rate_pct"] < 1,
        "approval_history": metrics["draft_approval"]["denominator"] >= 100,
        "low_revision_rate": (
            metrics["draft_revision"]["denominator"] >= 100
            and metrics["draft_revision"]["rate_pct"] is not None
            and metrics["draft_revision"]["rate_pct"] <= 10
        ),
    }
    blockers = [key for key, passed in checks.items() if not passed]
    return {
        "days": days,
        "evaluation_only": True,
        "runtime_mode": "approval_send" if policy and policy.mode == "approval_send" else "off",
        "gate_passed": not blockers,
        "activation_available": False,
        "activation_blocker": "Controlled Auto runtime is not released; passing evidence gates does not queue or send mail.",
        "checks": checks,
        "blockers": blockers,
        "metrics": metrics,
        "review_sample_pct": policy.controlled_auto_review_sample_pct if policy else 100,
    }


@router.get("/rfqs/{rfq_id}/attribution")
async def rfq_attribution(
    rfq_id: uuid.UUID,
    db: DbDep,
    current_user: UserDep,
):
    tenant_id = require_user_tenant_id(current_user)
    rfq = await db.get(RFQRequest, rfq_id)
    if not rfq or rfq.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="RFQ not found")
    row = (
        await db.exec(
            select(AttributionLink).where(
                AttributionLink.tenant_id == tenant_id,
                AttributionLink.rfq_request_id == rfq_id,
            )
        )
    ).first()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Attribution has not been built; run the attribution rebuild endpoint",
        )
    events = list(
        (
            await db.exec(
                select(AttributionEvent)
                .where(
                    AttributionEvent.tenant_id == tenant_id,
                    AttributionEvent.attribution_link_id == row.id,
                )
                .order_by(col(AttributionEvent.created_at).asc())
            )
        ).all()
    )
    return _attribution_dict(row, events)


@router.put("/rfqs/{rfq_id}/attribution")
async def update_rfq_attribution(
    rfq_id: uuid.UUID,
    body: AttributionOverrideIn,
    db: DbDep,
    current_user: ManagerDep,
):
    tenant_id = require_user_tenant_id(current_user)
    rfq = await db.get(RFQRequest, rfq_id)
    if not rfq or rfq.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="RFQ not found")
    try:
        row = await override_attribution(
            db,
            rfq=rfq,
            attribution_type=body.attribution_type,
            confidence=body.confidence,
            reason=body.reason,
            actor_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(row)
    return _attribution_dict(row)


@router.post("/attribution/rebuild")
async def rebuild_attribution(
    db: DbDep,
    current_user: ManagerDep,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    tenant_id = require_user_tenant_id(current_user)
    eligible = select(RFQRequest.id).where(
        RFQRequest.tenant_id == tenant_id,
        RFQRequest.is_test_data.is_(False),
    )
    total = await _count(db, eligible)
    rfqs = list(
        (
            await db.exec(
                select(RFQRequest)
                .where(
                    RFQRequest.tenant_id == tenant_id,
                    RFQRequest.is_test_data.is_(False),
                )
                .order_by(col(RFQRequest.created_at).asc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )
    counts = {kind: 0 for kind in ATTRIBUTION_TYPES}
    for rfq in rfqs:
        row = await derive_attribution(db, rfq=rfq, actor_user_id=current_user.id)
        counts[row.attribution_type] += 1
    await db.commit()
    next_offset = offset + len(rfqs)
    return {
        "processed": len(rfqs),
        "counts": counts,
        "limit": limit,
        "offset": offset,
        "next_offset": next_offset,
        "total": total,
        "has_more": next_offset < total,
    }


@router.get("/growth-funnel/export.csv")
async def export_growth_funnel(
    db: DbDep,
    current_user: UserDep,
    days: int = Query(default=30, ge=1, le=365),
):
    tenant_id = require_user_tenant_id(current_user)
    layers = await _north_star_layers(
        db, tenant_id, utcnow_naive() - timedelta(days=days)
    )
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=(
            "stage", "label", "count", "previous_count",
            "conversion_from_previous_pct", "drop_off",
        ),
    )
    writer.writeheader()
    writer.writerows(layers)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="north-star-funnel-{days}d.csv"'
        },
    )
