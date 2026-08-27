"""
客戶成果儀表板＋業務漏斗＋顧問工作台（實效計畫 §6、§7）

  GET /api/v1/tracking/outcomes   — 客戶首屏五項（§6.1）
  GET /api/v1/tracking/funnel     — 流量→成交漏斗（§6.3）
  GET /api/v1/ops/task-queue      — 顧問「今日必處理」（§7.1）
"""
import json
import uuid
from datetime import timedelta
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_admin
from app.core.datetime import isoformat_utc, utcnow_naive
from app.db.session import get_session
from app.models.operational_job import OperationalJob
from app.models.page import Page
from app.models.rfq_request import RFQRequest
from app.models.user import User
from app.models.visitor import Visitor

tracking_router = APIRouter(prefix="/tracking", tags=["Outcomes"])
ops_router = APIRouter(prefix="/ops", tags=["Growth Ops"])

QUALIFIED_THRESHOLD = 70
_CLOSED = ("won", "lost", "expired")

# outcome-feedback 高 lift facet → 建議任務（閉環第一步：觀察 → 產生行動）
_FACET_ACTIONS = {
    "trust_validation": {
        "title": "成交訪客更重視信任驗證",
        "action": "補強認證 / 廠能 / 客戶案例頁",
        "link": "/dashboard/certifications",
    },
    "product_interest": {
        "title": "成交訪客產品瀏覽更深",
        "action": "優化熱門商品頁與規格表",
        "link": "/dashboard/products",
    },
    "procurement_readiness": {
        "title": "成交訪客採購準備度高",
        "action": "在商品頁強化 MOQ / 交期 / Incoterms 說明",
        "link": "/dashboard/products",
    },
    "urgency": {
        "title": "成交訪客急迫性訊號強",
        "action": "檢查 RFQ 回覆 SLA 與首回範本",
        "link": "/dashboard/rfqs/templates",
    },
}


def _build_facet_tasks(feedback: dict) -> list[dict]:
    """把 outcome-feedback 中 lift >= 1.5 的 facet 轉成可執行任務。"""
    if not feedback.get("statistically_actionable"):
        return []
    tasks = []
    for f in feedback.get("facets") or []:
        lift = f.get("won_lift")
        if lift is None or lift < 1.5:
            continue
        meta = _FACET_ACTIONS.get(f["facet"])
        if not meta:
            continue
        tasks.append({
            "type": "outcome_facet_action",
            "title": meta["title"],
            "count": 1,
            "severity": "medium",
            "items": [{
                "facet": f["facet"],
                "won_lift": lift,
                "avg_all": f.get("avg_all_rfq_visitors"),
                "avg_won": f.get("avg_won_visitors"),
                "action": meta["action"],
            }],
            "link": meta["link"],
        })
    return tasks


def _month_bounds(now):
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    return start, prev_start


def _naive(dt):
    """DB driver 可能回傳 tz-aware；統一轉 naive 再做算術（同 rfqs.py 慣例）。"""
    return dt.replace(tzinfo=None) if dt is not None and dt.tzinfo is not None else dt


async def _count(db, q) -> int:
    return int((await db.exec(select(func.count()).select_from(q.subquery()))).one())


# ── §6.1 客戶首屏五項 ────────────────────────────────────────────────────────

@tracking_router.get("/outcomes")
async def get_outcomes(
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    now = utcnow_naive()
    month_start, prev_start = _month_bounds(now)
    tid = _.tenant_id

    def _scoped(q):
        q = q.where(RFQRequest.is_test_data.is_(False))
        return q.where(RFQRequest.tenant_id == tid) if tid else q

    # 1. 本月 Qualified RFQ（與上月比較）
    qualified_this = await _count(db, _scoped(select(RFQRequest).where(
        RFQRequest.created_at >= month_start,
        RFQRequest.quality_score >= QUALIFIED_THRESHOLD,
    )))
    qualified_prev = await _count(db, _scoped(select(RFQRequest).where(
        RFQRequest.created_at >= prev_start,
        RFQRequest.created_at < month_start,
        RFQRequest.quality_score >= QUALIFIED_THRESHOLD,
    )))

    # 2. 平均首回時間／SLA 達成率（本月建立的 RFQ）
    rows = (await db.exec(_scoped(select(
        RFQRequest.first_response_at, RFQRequest.created_at,
        RFQRequest.sla_due_at, RFQRequest.sla_breached,
    ).where(RFQRequest.created_at >= month_start)))).all()
    frt_hours: list[float] = []
    sla_total = sla_met = 0
    for first_response_at, created_at, sla_due_at, breached in rows:
        first_response_at = _naive(first_response_at)
        created_at = _naive(created_at)
        sla_due_at = _naive(sla_due_at)
        if first_response_at and created_at:
            frt_hours.append(max(0.0, (first_response_at - created_at).total_seconds() / 3600))
        if sla_due_at:
            sla_total += 1
            if first_response_at and first_response_at <= sla_due_at and not breached:
                sla_met += 1
    avg_frt = round(sum(frt_hours) / len(frt_hours), 1) if frt_hours else None
    sla_rate = round(sla_met / sla_total * 100, 1) if sla_total else None

    # 3. RFQ 狀態漏斗（目前快照）
    status_counts = (await db.exec(_scoped(
        select(RFQRequest.status, func.count(RFQRequest.id)).group_by(RFQRequest.status)
    ))).all()
    funnel_status = {str(s): int(c) for s, c in status_counts}

    # 4. 內容／landing 來源（本月 RFQ 依 source_page 分組，§6.2 歸因最小版）
    source_rows = (await db.exec(_scoped(
        select(RFQRequest.source_page, func.count(RFQRequest.id))
        .where(RFQRequest.created_at >= month_start, RFQRequest.source_page.is_not(None))
        .group_by(RFQRequest.source_page)
        .order_by(func.count(RFQRequest.id).desc())
        .limit(5)
    ))).all()
    top_sources = [{"source_page": s, "rfq_count": int(c)} for s, c in source_rows]

    # 5. 下週建議（規則產生，最多 3 條）
    suggestions: list[str] = []
    breached_count = await _count(db, _scoped(select(RFQRequest).where(
        RFQRequest.sla_breached.is_(True),
        RFQRequest.status.not_in(_CLOSED),
    )))
    if breached_count:
        suggestions.append(f"催辦 {breached_count} 件 SLA 逾期的 RFQ，避免買家轉向競爭對手")
    unassigned_hot = await _count(db, _scoped(select(RFQRequest).where(
        RFQRequest.status == "new",
        RFQRequest.quality_score >= QUALIFIED_THRESHOLD,
        RFQRequest.assigned_to.is_(None),
    )))
    if unassigned_hot:
        suggestions.append(f"指派 {unassigned_hot} 件高品質 RFQ 給負責業務，搶先回覆")
    stale_quotes = await _count(db, _scoped(select(RFQRequest).where(
        RFQRequest.status == "quoted",
        RFQRequest.quote_sent_at <= now - timedelta(days=7),
    )))
    if stale_quotes:
        suggestions.append(f"追蹤 {stale_quotes} 件報價送出超過 7 天未進談判的案子")
    if not suggestions:
        suggestions.append("本週無緊急待辦；建議檢視信任內容（認證／產能頁）完整度")

    return {
        "period": {"month_start": month_start.isoformat(), "prev_month_start": prev_start.isoformat()},
        "qualified_rfq": {"this_month": qualified_this, "prev_month": qualified_prev},
        "first_response": {"avg_hours": avg_frt, "sla_rate_pct": sla_rate, "responded": len(frt_hours)},
        "funnel_status": funnel_status,
        "top_source_pages": top_sources,
        "next_week_suggestions": suggestions[:3],
    }


# ── §6.3 業務漏斗：流量 → 成交 ───────────────────────────────────────────────

@tracking_router.get("/funnel")
async def get_funnel(
    days: int = 30,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """每一層轉化率可查（§6.3），避免行銷／業務互相推託。"""
    days = min(max(days, 1), 365)
    since = utcnow_naive() - timedelta(days=days)
    tid = _.tenant_id

    # Use one acquisition cohort consistently: visitors first seen in-period.
    # Counting sessions here would mix returning visitors into the denominator
    # while the high-intent layer used first_seen, producing a non-cohort funnel.
    sessions_q = select(Visitor.visitor_id).where(
        Visitor.first_seen >= since,
        Visitor.is_test_data.is_(False),
    )
    if tid:
        sessions_q = sessions_q.where(Visitor.tenant_id == tid)
    traffic = await _count(db, sessions_q)

    hi_q = select(Visitor).where(
        Visitor.first_seen >= since,
        Visitor.intent_stage.in_(["hot", "sales_ready"]),
        Visitor.is_test_data.is_(False),
    )
    if tid:
        hi_q = hi_q.where(Visitor.tenant_id == tid)
    high_intent = await _count(db, hi_q)

    def _rfq_q(*conds):
        q = select(RFQRequest).where(*conds, RFQRequest.is_test_data.is_(False))
        return q.where(RFQRequest.tenant_id == tid) if tid else q

    rfq_total = await _count(db, _rfq_q(RFQRequest.created_at >= since))
    qualified = await _count(db, _rfq_q(
        RFQRequest.created_at >= since, RFQRequest.quality_score >= QUALIFIED_THRESHOLD,
    ))
    # The RFQ lifecycle is a separate cohort from anonymous visitors.  Keep its
    # stages cumulative and nested so the displayed percentages cannot exceed
    # 100% simply because a record has moved beyond a previous current status.
    quoted = await _count(db, _rfq_q(
        RFQRequest.created_at >= since,
        RFQRequest.quote_sent_at.is_not(None),
    ))
    negotiation = await _count(db, _rfq_q(
        RFQRequest.created_at >= since,
        RFQRequest.quote_sent_at.is_not(None),
        RFQRequest.status.in_(["negotiation", "won"]),
    ))
    won = await _count(db, _rfq_q(
        RFQRequest.created_at >= since,
        RFQRequest.quote_sent_at.is_not(None),
        RFQRequest.status == "won",
    ))

    layers = [
        {"layer": "traffic", "label": "流量（不重複訪客）", "count": traffic, "cohort": "visitor"},
        {"layer": "high_intent", "label": "高關注訪客", "count": high_intent, "cohort": "visitor"},
        {"layer": "rfq", "label": "詢價單", "count": rfq_total, "cohort": "rfq"},
        {"layer": "qualified_rfq", "label": "合格詢價", "count": qualified, "cohort": "rfq"},
        {"layer": "quoted", "label": "報價送出", "count": quoted, "cohort": "rfq"},
        {"layer": "negotiation", "label": "談判或成交", "count": negotiation, "cohort": "rfq"},
        {"layer": "won", "label": "成交", "count": won, "cohort": "rfq"},
    ]
    for i, layer in enumerate(layers):
        previous = layers[i - 1] if i else None
        # Only divide stages that are genuine nested sets.  Qualified RFQ is a
        # quality branch, not the parent of quote-sent, so that transition is
        # intentionally left blank as well.
        comparable_transitions = {
            ("traffic", "high_intent"),
            ("rfq", "qualified_rfq"),
            ("quoted", "negotiation"),
            ("negotiation", "won"),
        }
        pair = (previous["layer"], layer["layer"]) if previous else None
        prev = previous["count"] if pair in comparable_transitions else None
        layer["conversion_from_prev_pct"] = (
            round(layer["count"] / prev * 100, 1) if prev else None
        )

    bottleneck = None
    rates = [(l["layer"], l["conversion_from_prev_pct"]) for l in layers[1:] if l["conversion_from_prev_pct"] is not None]
    if rates:
        bottleneck = min(rates, key=lambda x: x[1])[0]

    return {
        "days": days,
        "cohort_start": since.isoformat(),
        "methodology": "Traffic/high-intent use the visitor acquisition cohort first seen in period. RFQ and sales stages use a separate RFQ cohort created in period, so visitor-to-RFQ conversion is intentionally not calculated. Qualified RFQ is a quality branch; quote, negotiation and won are cumulative lifecycle stages based on quote_sent_at and current advanced status.",
        "layers": layers,
        "bottleneck_layer": bottleneck,
    }


# ── §7.1 顧問「今日必處理」任務佇列 ──────────────────────────────────────────

@ops_router.get("/task-queue")
async def get_task_queue(
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    tid = _.tenant_id
    if not tid:
        raise HTTPException(status_code=403, detail="Tenant context required")
    now = utcnow_naive()

    def _rfq_q(*conds):
        q = select(RFQRequest).where(
            *conds,
            RFQRequest.tenant_id == tid,
            RFQRequest.is_spam.is_(False),
            RFQRequest.merged_into_rfq_id.is_(None),
            RFQRequest.is_test_data.is_(False),
        )
        if _.role == "sales":
            q = q.where(RFQRequest.assigned_to == _.id)
        return q

    # 使用者真正要處理的下次跟進，而不是技術 SLA 名詞。
    follow_up_rows = (await db.exec(_rfq_q(
        RFQRequest.next_follow_up_at.is_not(None),
        col(RFQRequest.next_follow_up_at) < now + timedelta(days=1),
        RFQRequest.status.not_in(_CLOSED),
    ).order_by(col(RFQRequest.next_follow_up_at).asc()).limit(10))).all()
    overdue_follow_ups = [r for r in follow_up_rows if r.next_follow_up_at and r.next_follow_up_at < now]

    # SLA 逾期 RFQ（未結案）
    sla_rows = (await db.exec(_rfq_q(
        RFQRequest.sla_breached.is_(True), RFQRequest.status.not_in(_CLOSED),
    ).order_by(col(RFQRequest.sla_due_at).asc()).limit(5))).all()

    # Hot 訪客 72h 內活躍但未送 RFQ（未被跟進）
    # 以 rfq_requests.visitor_id 為準（表單建立不一定寫入 rfq_submit 事件）
    hot_q = (
        select(Visitor)
        .where(
            Visitor.intent_stage.in_(["hot", "sales_ready"]),
            Visitor.last_seen >= now - timedelta(hours=72),
        )
        .order_by(col(Visitor.intent_score).desc())
        .limit(20)
    )
    if tid:
        hot_q = hot_q.where(Visitor.tenant_id == tid)
    hot_visitors = (await db.exec(hot_q)).all()
    hot_without_rfq: list[Visitor] = []
    for v in hot_visitors:
        rfq_exists_q = select(RFQRequest.id).where(RFQRequest.visitor_id == v.visitor_id).limit(1)
        if tid:
            rfq_exists_q = rfq_exists_q.where(RFQRequest.tenant_id == tid)
        has_rfq = (await db.exec(rfq_exists_q)).first()
        if not has_rfq:
            hot_without_rfq.append(v)
        if len(hot_without_rfq) >= 5:
            break

    # 低品質 RFQ 待過濾
    low_q_count = await _count(db, _rfq_q(
        RFQRequest.status == "new", RFQRequest.quality_score < 40,
    ))
    low_q_rows = (await db.exec(_rfq_q(
        RFQRequest.status == "new", RFQRequest.quality_score < 40,
    ).order_by(col(RFQRequest.created_at).asc()).limit(5))).all()

    # 待核准內容（草稿頁；CF 串接後為主要核准來源）
    drafts_q = select(Page).where(Page.status == "draft")
    if tid:
        drafts_q = drafts_q.where(Page.tenant_id == tid)
    draft_count = await _count(db, drafts_q)
    draft_rows = (await db.exec(drafts_q.order_by(col(Page.updated_at).asc()).limit(5))).all()

    # 成交迴路觀察：高 lift facet 自動產生行動任務（閉環）
    facet_tasks: list[dict] = []
    try:
        feedback = await get_intent_outcome_feedback(db=db, _=_)
        facet_tasks = _build_facet_tasks(feedback)
    except Exception:
        facet_tasks = []

    tasks = [
        {
            "type": "rfq_follow_up_due",
            "title": "24 小時內要跟進的詢價",
            "count": len(follow_up_rows),
            "severity": "high" if overdue_follow_ups else "medium" if follow_up_rows else "none",
            "items": [
                {
                    "id": str(r.id),
                    "rfq_number": r.rfq_number,
                    "next_follow_up_at": isoformat_utc(r.next_follow_up_at),
                    "overdue": bool(r.next_follow_up_at and r.next_follow_up_at < now),
                }
                for r in follow_up_rows
            ],
            "link": "/dashboard/rfqs?follow_up=due",
        },
        {
            "type": "sla_breached_rfq",
            "title": "尚未回覆且已逾期",
            "count": len(sla_rows),
            "severity": "high" if sla_rows else "none",
            "items": [
                {
                    "id": str(r.id),
                    "rfq_number": r.rfq_number,
                    "sla_due_at": r.sla_due_at.isoformat() if r.sla_due_at else None,
                    "quality_score": r.quality_score,
                }
                for r in sla_rows
            ],
            "link": "/dashboard/rfqs?sla=breached",
        },
        {
            "type": "hot_visitor_unassigned",
            "title": "高關注訪客未跟進（72 小時內活躍、尚未送出詢價）",
            "count": len(hot_without_rfq),
            "severity": "medium" if hot_without_rfq else "none",
            "items": [
                {
                    "visitor_id": str(v.visitor_id),
                    "intent_score": v.intent_score,
                    "intent_stage": v.intent_stage,
                    "intent_explanation": v.intent_explanation,
                }
                for v in hot_without_rfq
            ],
            "link": "/dashboard/intent",
        },
        {
            "type": "low_quality_rfq",
            "title": "低品質 RFQ 待過濾",
            "count": low_q_count,
            "severity": "low" if low_q_count else "none",
            "items": [
                {
                    "id": str(r.id),
                    "rfq_number": r.rfq_number,
                    "quality_score": r.quality_score,
                    "sla_due_at": r.sla_due_at.isoformat() if r.sla_due_at else None,
                }
                for r in low_q_rows
            ],
            "link": "/dashboard/rfqs",
        },
        {
            "type": "content_pending_approval",
            "title": "待核准內容（草稿）",
            "count": draft_count,
            "severity": "low" if draft_count else "none",
            "items": [
                {
                    "id": str(page.id),
                    "page_title": page.title,
                    "slug": page.slug,
                    "updated_at": page.updated_at.isoformat(),
                }
                for page in draft_rows
            ],
            "link": "/dashboard/pages",
        },
        {
            "type": "verification_anomaly",
            "title": "線上驗證異常",
            "count": 0,
            "severity": "none",
            "available": False,
            "reason": "需完成 ContentFlow 線上驗證資料串接後提供",
            "items": [],
            "link": None,
        },
        *facet_tasks,
    ]
    if _.role == "sales":
        tasks = [task for task in tasks if task["type"] in {"rfq_follow_up_due", "sla_breached_rfq", "low_quality_rfq"}]
    total_open = sum(t["count"] for t in tasks)
    return {"generated_at": now.isoformat(), "total_open": total_open, "tasks": tasks}


# ── 內容→成交歸因（回答「哪種內容帶來會成交的單」）──

def _source_path_segments(source_page: str) -> list[str]:
    """正規化 source_page 為 path segments，供精確 slug 比對（避免子字串誤命中）。"""
    raw = (source_page or "").strip()
    if not raw:
        return []
    path = urlparse(raw).path if "://" in raw else raw.split("?", 1)[0]
    return [s for s in path.strip("/").split("/") if s]


def match_source_to_page(
    source_page: str,
    pages: list[tuple],
) -> Optional[dict]:
    """精確 path-segment 比對；多命中時取最長 slug（較具體）。"""
    segs = set(_source_path_segments(source_page))
    if not segs:
        return None
    best: Optional[dict] = None
    for slug, title, page_type in pages:
        if slug and slug in segs and (best is None or len(slug) > len(best["slug"])):
            best = {"slug": slug, "title": title, "page_type": page_type}
    return best


@tracking_router.get("/attribution/content")
async def get_content_attribution(
    days: int = 90,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """RFQ source_page 對照 pages 表，依 page_type 聚合 RFQ／Qualified／成交。"""
    days = min(max(days, 1), 365)
    since = utcnow_naive() - timedelta(days=days)
    tid = _.tenant_id

    rfq_q = select(RFQRequest).where(
        RFQRequest.created_at >= since,
        RFQRequest.source_page.is_not(None),
        RFQRequest.is_test_data.is_(False),
    )
    if tid:
        rfq_q = rfq_q.where(RFQRequest.tenant_id == tid)
    rfqs = (await db.exec(rfq_q)).all()

    page_q = select(Page.slug, Page.title, Page.page_type)
    if tid:
        page_q = page_q.where(Page.tenant_id == tid)
    pages = (await db.exec(page_q)).all()

    def _match(source_page: str):
        return match_source_to_page(source_page, list(pages))

    buckets: dict[str, dict] = {}

    def _bucket(key: str, label: str) -> dict:
        return buckets.setdefault(key, {
            "key": key, "label": label,
            "rfq": 0, "qualified_rfq": 0, "quoted": 0, "won": 0,
        })

    unmatched = 0
    for r in rfqs:
        meta = _match(r.source_page or "")
        if meta is None:
            unmatched += 1
            b = _bucket("__unmatched__", "未對照到頁面（外部／直接輸入 URL）")
        else:
            b = _bucket(meta["page_type"] or "unknown", meta["page_type"] or "unknown")
        b["rfq"] += 1
        if r.quality_score >= QUALIFIED_THRESHOLD:
            b["qualified_rfq"] += 1
        if r.quote_sent_at is not None:
            b["quoted"] += 1
        if r.status == "won":
            b["won"] += 1

    result = sorted(buckets.values(), key=lambda x: (x["won"], x["qualified_rfq"]), reverse=True)
    for b in result:
        b["won_rate_pct"] = round(b["won"] / b["rfq"] * 100, 1) if b["rfq"] else 0.0
    return {
        "days": days,
        "rfq_with_source": len(rfqs),
        "unmatched_source_pages": unmatched,
        "by_page_type": result,
    }


@ops_router.get("/operational-jobs")
async def list_operational_jobs(
    status: str = "failed",
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Operational visibility for durable RFQ/Chat side effects and retries."""
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
                "available_at": job.available_at.isoformat(),
                "last_error": job.last_error,
                "updated_at": job.updated_at.isoformat(),
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
    return {"counts": counts, "stale_processing": stale, "healthy": counts.get("failed", 0) == 0 and stale == 0}


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
    return {"id": str(job.id), "status": job.status, "available_at": job.available_at.isoformat()}


# ── Phase 5：成交原因回寫 intent（§8.3，observational — 只觀察、不自動改權重）──

_FACET_FIELDS = (
    "facet_product_interest", "facet_trust_validation",
    "facet_procurement_readiness", "facet_urgency",
)


@tracking_router.get("/intent/outcome-feedback")
async def get_intent_outcome_feedback(
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """比較「成交單的訪客 facet 輪廓」與全體 RFQ 訪客，產生觀察性權重建議。

    ⚠️ observational：僅呈現相對 lift，不自動修改評分權重（§8.3 長期迴路的第一步）。
    """
    tid = _.tenant_id
    rfq_q = select(RFQRequest).where(
        RFQRequest.visitor_id.is_not(None),
        RFQRequest.is_test_data.is_(False),
    )
    if tid:
        rfq_q = rfq_q.where(RFQRequest.tenant_id == tid)
    rfqs = (await db.exec(rfq_q)).all()
    if not rfqs:
        return {
            "sample": {"rfq_with_snapshot": 0, "won": 0, "legacy_without_snapshot": 0},
            "statistically_actionable": False,
            "minimum_sample": {"rfq": 10, "won": 3},
            "facets": [],
            "note": "尚無連結訪客的 RFQ，無法計算",
        }

    won_snapshots: list[dict] = []
    all_snapshots: list[dict] = []
    legacy_without_snapshot = 0
    for r in rfqs:
        if not r.intent_snapshot_json:
            legacy_without_snapshot += 1
            continue
        try:
            snapshot = json.loads(r.intent_snapshot_json)
            facets_snapshot = snapshot.get("facets") or {}
        except (TypeError, json.JSONDecodeError):
            legacy_without_snapshot += 1
            continue
        all_snapshots.append(facets_snapshot)
        if r.status == "won":
            won_snapshots.append(facets_snapshot)

    def _avg(group: list[dict], field: str) -> float:
        if not group:
            return 0.0
        key = field.replace("facet_", "")
        return sum(float(v.get(key, 0) or 0) for v in group) / len(group)

    facets = []
    for field in _FACET_FIELDS:
        base = _avg(all_snapshots, field)
        won_avg = _avg(won_snapshots, field)
        lift = round(won_avg / base, 2) if base > 0 else None
        facets.append({
            "facet": field.replace("facet_", ""),
            "avg_all_rfq_visitors": round(base, 1),
            "avg_won_visitors": round(won_avg, 1),
            "won_lift": lift,
            "hint": (
                f"成交訪客此面向為全體的 {lift}x，可考慮提高權重" if lift and lift >= 1.5
                else "差異不顯著，維持現行權重"
            ) if lift is not None else "樣本不足",
        })

    return {
        "sample": {"rfq_with_snapshot": len(all_snapshots), "won": len(won_snapshots), "legacy_without_snapshot": legacy_without_snapshot},
        "statistically_actionable": len(all_snapshots) >= 10 and len(won_snapshots) >= 3,
        "minimum_sample": {"rfq": 10, "won": 3},
        "facets": facets,
        "note": "觀察性數據（observational）：未自動調整評分權重；調整需經人工確認並記錄於評分規則。",
    }
