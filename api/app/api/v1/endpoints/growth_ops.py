"""Operational work queue for website-to-RFQ handoff.

This module intentionally stops at human acceptance.  It does not calculate
quotation, negotiation, won/lost, revenue, or buyer-quality scores.
"""

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_admin
from app.core.datetime import isoformat_utc, utcnow_naive
from app.db.session import get_session
from app.models.application import Application
from app.models.capability import Capability
from app.models.certification import Certification
from app.models.comparison_topic import ComparisonTopic
from app.models.faq_item import FAQItem
from app.models.operational_job import OperationalJob
from app.models.page import Page
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.rfq_request import RFQRequest
from app.models.user import User

ops_router = APIRouter(prefix="/ops", tags=["Operations"])


async def _count(db: AsyncSession, query) -> int:
    return int((await db.exec(select(func.count()).select_from(query.subquery()))).one())


@ops_router.get("/task-queue")
async def get_task_queue(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return only work that ForgeBase can verify from first-party state."""
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")

    def _rfq_query(*conditions):
        query = select(RFQRequest).where(
            *conditions,
            RFQRequest.tenant_id == tenant_id,
            RFQRequest.is_spam.is_(False),
            RFQRequest.merged_into_rfq_id.is_(None),
            RFQRequest.is_test_data.is_(False),
        )
        if current_user.role == "sales":
            query = query.where(RFQRequest.assigned_to == current_user.id)
        return query

    unassigned_rows = []
    unassigned_count = 0
    if current_user.role != "sales":
        unassigned_count = await _count(db, _rfq_query(
            RFQRequest.status == "new",
            RFQRequest.assigned_to.is_(None),
        ))
        unassigned_rows = list((await db.exec(
            _rfq_query(
                RFQRequest.status == "new",
                RFQRequest.assigned_to.is_(None),
            )
            .order_by(col(RFQRequest.created_at).asc())
            .limit(10)
        )).all())

    awaiting_query = _rfq_query(
        RFQRequest.status == "assigned",
        RFQRequest.accepted_at.is_(None),
    )
    awaiting_count = await _count(db, awaiting_query)
    overdue_count = await _count(db, awaiting_query.where(
        RFQRequest.acceptance_sla_breached.is_(True)
        | (col(RFQRequest.acceptance_due_at) < utcnow_naive()),
    ))
    awaiting_rows = list((await db.exec(
        awaiting_query
        .order_by(col(RFQRequest.acceptance_due_at).asc())
        .limit(10)
    )).all())

    def _is_overdue(row: RFQRequest) -> bool:
        due = row.acceptance_due_at
        if due is not None and due.tzinfo is not None:
            due = due.replace(tzinfo=None)
        return bool(row.acceptance_sla_breached or (due and due < utcnow_naive()))

    content_sources = (
        ("pages", Page, "title"),
        ("products", Product, "product_name"),
        ("categories", ProductCategory, "category_name"),
        ("applications", Application, "application_name"),
        ("faqs", FAQItem, "question"),
        ("comparisons", ComparisonTopic, "topic_title"),
        ("certifications", Certification, "cert_name"),
        ("capabilities", Capability, "capability_name"),
    )
    pending_content = []
    for content_type, model, title_attribute in content_sources:
        query = select(model).where(model.status == "draft", model.tenant_id == tenant_id)
        rows = list((await db.exec(query)).all())
        pending_content.extend(
            (
                row.updated_at,
                {
                    "id": str(row.id),
                    "content_title": str(getattr(row, title_attribute)),
                    "content_type": content_type,
                    "slug": getattr(row, "slug", None),
                    "updated_at": isoformat_utc(row.updated_at),
                },
            )
            for row in rows
        )
    pending_content.sort(key=lambda item: item[0])
    draft_count = len(pending_content)
    draft_rows = [item for _, item in pending_content[:5]]

    tasks = [
        {
            "type": "rfq_unassigned",
            "title": "新詢價尚未分派",
            "count": unassigned_count,
            "severity": "high" if unassigned_count else "none",
            "items": [
                {
                    "id": str(row.id),
                    "rfq_number": row.rfq_number,
                    "created_at": isoformat_utc(row.created_at),
                    "priority": row.priority,
                }
                for row in unassigned_rows
            ],
            "link": "/dashboard/rfqs?attention=unassigned",
        },
        {
            "type": "rfq_awaiting_acceptance",
            "title": "已分派，等待業務接手",
            "count": awaiting_count,
            "severity": "high" if overdue_count else "medium" if awaiting_count else "none",
            "items": [
                {
                    "id": str(row.id),
                    "rfq_number": row.rfq_number,
                    "acceptance_due_at": isoformat_utc(row.acceptance_due_at),
                    "overdue": _is_overdue(row),
                    "priority": row.priority,
                }
                for row in awaiting_rows
            ],
            "link": "/dashboard/rfqs?attention=awaiting_acceptance",
        },
    ]

    if current_user.role != "sales":
        tasks.append({
            "type": "content_pending_approval",
            "title": "待核准內容",
            "count": draft_count,
            "severity": "low" if draft_count else "none",
            "items": draft_rows,
            "link": "/dashboard/pages",
        })

    total_open = sum(task["count"] for task in tasks)
    return {"generated_at": isoformat_utc(utcnow_naive()), "total_open": total_open, "tasks": tasks}


@ops_router.get("/operational-jobs")
async def list_operational_jobs(
    status: str = "failed",
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    limit = min(max(limit, 1), 200)
    query = (
        select(OperationalJob)
        .where(OperationalJob.status == status)
        .order_by(col(OperationalJob.updated_at).desc())
        .limit(limit)
    )
    if current_user.tenant_id:
        query = query.where(OperationalJob.tenant_id == current_user.tenant_id)
    jobs = (await db.exec(query)).all()
    return {
        "status": status,
        "items": [
            {
                "id": str(job.id),
                "job_type": job.job_type,
                "attempts": job.attempts,
                "max_attempts": job.max_attempts,
                "available_at": isoformat_utc(job.available_at),
                "last_error": job.last_error,
                "updated_at": isoformat_utc(job.updated_at),
            }
            for job in jobs
        ],
    }


@ops_router.get("/operational-jobs/summary")
async def operational_jobs_summary(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    now = utcnow_naive()
    query = select(OperationalJob.status, func.count(OperationalJob.id)).group_by(OperationalJob.status)
    if current_user.tenant_id:
        query = query.where(OperationalJob.tenant_id == current_user.tenant_id)
    counts = {str(status): int(count) for status, count in (await db.exec(query)).all()}
    stale_query = select(func.count()).select_from(OperationalJob).where(
        OperationalJob.status == "processing",
        OperationalJob.locked_at <= now - timedelta(minutes=15),
    )
    if current_user.tenant_id:
        stale_query = stale_query.where(OperationalJob.tenant_id == current_user.tenant_id)
    stale = int((await db.exec(stale_query)).one())
    return {
        "counts": counts,
        "stale_processing": stale,
        "healthy": counts.get("failed", 0) == 0 and stale == 0,
    }


@ops_router.post("/operational-jobs/{job_id}/retry")
async def retry_operational_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    job = await db.get(OperationalJob, job_id)
    if not job or (current_user.tenant_id and job.tenant_id != current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Operational job not found")
    if job.status not in {"failed", "retry"}:
        raise HTTPException(status_code=409, detail="Only failed or retrying jobs can be retried")
    job.status = "retry"
    job.attempts = 0
    job.available_at = utcnow_naive()
    job.locked_at = None
    job.completed_at = None
    job.last_error = None
    job.updated_at = utcnow_naive()
    db.add(job)
    await db.commit()
    return {"id": str(job.id), "status": job.status, "available_at": isoformat_utc(job.available_at)}
