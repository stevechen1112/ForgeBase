"""
Accounts API  (2.1.2 IP-to-Company identification)

GET    /tracking/accounts           — list accounts (admin)
GET    /tracking/accounts/{id}      — account detail + associated visitors
POST   /tracking/accounts           — manually create account (admin)
PATCH  /tracking/accounts/{id}      — update enrichment data (admin)
DELETE /tracking/accounts/{id}      — super_admin only
POST   /tracking/accounts/resolve-ip — trigger IP resolution for a visitor
"""
import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor
from app.db.session import get_session
from app.models.account import Account
from app.models.visitor import Visitor
from app.models.user import User
from app.services.ip_resolver import resolve_ip_to_company

router = APIRouter(prefix="/tracking", tags=["Tracking"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    company_name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count_range: Optional[str] = None
    annual_revenue_range: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    linkedin_url: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    enrichment_source: Optional[str] = "manual"


class AccountUpdate(BaseModel):
    company_name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count_range: Optional[str] = None
    annual_revenue_range: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    linkedin_url: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    enrichment_source: Optional[str] = None
    enrichment_status: Optional[str] = None


class ResolveIPRequest(BaseModel):
    visitor_id: uuid.UUID


# ── Background task ───────────────────────────────────────────────────────────

async def _resolve_and_link(visitor_id: uuid.UUID, ip: str) -> None:
    """
    Resolve IP to company, upsert Account, and link to Visitor.
    Called as a background task — creates its own DB session.
    """
    from app.db.session import get_session_ctx

    result = await resolve_ip_to_company(ip)
    now = utcnow_naive()

    async with get_session_ctx() as db:
        if not result:
            # Mark visitor as resolved but not found
            visitor = (await db.exec(select(Visitor).where(Visitor.visitor_id == visitor_id))).first()
            if visitor:
                visitor.ip_resolved_at = now
                db.add(visitor)
                await db.commit()
            return

        company_name: str = result["company_name"]
        domain: Optional[str] = result.get("domain")

        # Upsert account — find by domain first (if available), else company_name
        account: Optional[Account] = None
        if domain:
            account = (await db.exec(select(Account).where(Account.domain == domain))).first()
        if account is None:
            account = (await db.exec(
                select(Account).where(
                    col(Account.company_name) == company_name
                )
            )).first()

        if account is None:
            account = Account(
                company_name=company_name,
                domain=domain,
                industry=result.get("industry"),
                employee_count_range=result.get("employee_count_range"),
                country=result.get("country"),
                city=result.get("city"),
                linkedin_url=result.get("linkedin_url"),
                logo_url=result.get("logo_url"),
                description=result.get("description"),
                enrichment_source=result.get("enrichment_source"),
                enrichment_status="enriched",
                last_enriched_at=now,
            )
            db.add(account)
            await db.flush()  # assign ID before linking
        else:
            # Update fields that are now more complete
            for field in ("domain", "industry", "employee_count_range", "country", "city",
                          "linkedin_url", "logo_url", "description"):
                new_val = result.get(field)
                if new_val and not getattr(account, field):
                    setattr(account, field, new_val)
            account.enrichment_source = result.get("enrichment_source", account.enrichment_source)
            account.enrichment_status = "enriched"
            account.last_enriched_at = now
            db.add(account)

        # Link visitor
        visitor = (await db.exec(select(Visitor).where(Visitor.visitor_id == visitor_id))).first()
        if visitor:
            visitor.account_id = account.id
            visitor.ip_resolved_at = now
            db.add(visitor)

        await db.commit()
        await db.refresh(account)

        # Recalculate account-level aggregates
        await _refresh_account_stats(account.id, db)


async def _refresh_account_stats(account_id: uuid.UUID, db: AsyncSession) -> None:
    """Recalculate total_visitors, total_page_views, max_intent_score for an account."""
    result = (await db.exec(
        select(
            func.count(Visitor.visitor_id),
            func.coalesce(func.sum(Visitor.total_visits), 0),
            func.coalesce(func.max(Visitor.intent_score), 0),
        ).where(Visitor.account_id == account_id)
    )).first()

    if result:
        account = (await db.exec(select(Account).where(Account.id == account_id))).first()
        if account:
            account.total_visitors = result[0]
            account.total_page_views = result[1]
            account.max_intent_score = result[2]
            db.add(account)
            await db.commit()


# ── Endpoints ─────────────────────────────────────────────────────────────────
# NOTE: Static path routes (/accounts/stats, /accounts/resolve-ip, etc.) MUST
# come before dynamic path routes (/accounts/{account_id}) to avoid FastAPI
# matching "stats" as a UUID parameter.

@router.get("/accounts")
async def list_accounts(
    search: Optional[str] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    enrichment_status: Optional[str] = None,
    min_intent_score: Optional[int] = None,
    sort_by: str = "max_intent_score",  # max_intent_score | total_visitors | company_name
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """List accounts sorted by intent signal strength. Admin only."""
    q = select(Account)

    if search:
        pattern = f"%{search}%"
        q = q.where(
            col(Account.company_name).ilike(pattern) |
            col(Account.domain).ilike(pattern)
        )
    if industry:
        q = q.where(Account.industry == industry)
    if country:
        q = q.where(Account.country == country)
    if enrichment_status:
        q = q.where(Account.enrichment_status == enrichment_status)
    if min_intent_score is not None:
        q = q.where(Account.max_intent_score >= min_intent_score)

    # Sorting
    sort_col = {
        "max_intent_score": col(Account.max_intent_score),
        "total_visitors": col(Account.total_visitors),
        "company_name": col(Account.company_name),
        "created_at": col(Account.created_at),
    }.get(sort_by, col(Account.max_intent_score))
    q = q.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    # Total count
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.exec(count_q)).first() or 0

    q = q.offset(offset).limit(min(limit, 200))
    rows = (await db.exec(q)).all()

    return {
        "total": total,
        "items": [_account_dict(a) for a in rows],
    }


@router.get("/accounts/stats")
async def get_accounts_stats(
    top_n: int = 10,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Account Enrichment summary (2.1.3).
    Returns: total accounts, enrichment breakdown, top N accounts by intent score.
    """
    total = (await db.exec(select(func.count(Account.id)))).first() or 0

    # Enrichment status breakdown
    status_rows = (await db.exec(
        select(Account.enrichment_status, func.count(Account.id))
        .group_by(Account.enrichment_status)
    )).all()
    enrichment_breakdown = {row[0]: row[1] for row in status_rows}

    # Top N accounts by intent score
    top_accounts = (await db.exec(
        select(Account)
        .where(Account.enrichment_status == "enriched")
        .order_by(col(Account.max_intent_score).desc())
        .limit(min(top_n, 50))
    )).all()

    return {
        "total_accounts": total,
        "enrichment_breakdown": enrichment_breakdown,
        "top_accounts": [_account_dict(a) for a in top_accounts],
    }


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    """Manually create an account record."""
    # Check for duplicate domain / company_name
    if payload.domain:
        existing = (await db.exec(select(Account).where(Account.domain == payload.domain))).first()
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Account with domain '{payload.domain}' already exists")

    now = utcnow_naive()
    account = Account(
        **payload.model_dump(exclude_none=True),
        enrichment_status="enriched",
        last_enriched_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return _account_dict(account)


@router.post("/accounts/resolve-ip")
async def resolve_ip_for_visitor(
    payload: ResolveIPRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    """
    Trigger IP-to-company resolution for a visitor.
    Uses visitor.last_seen_ip; enqueues as background task.
    """
    visitor = (await db.exec(
        select(Visitor).where(Visitor.visitor_id == payload.visitor_id)
    )).first()
    if not visitor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Visitor not found")
    if not visitor.last_seen_ip:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Visitor has no recorded IP address")

    background_tasks.add_task(_resolve_and_link, visitor.visitor_id, visitor.last_seen_ip)
    return {"status": "queued", "visitor_id": str(visitor.visitor_id), "ip": visitor.last_seen_ip}


@router.post("/accounts/refresh-all-stats")
async def refresh_all_stats(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Batch-refresh intent aggregates for ALL accounts (2.1.3).
    Admin-only utility. Runs in background.
    """
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")

    accounts = (await db.exec(select(Account.id))).all()
    account_ids = [a for a in accounts]

    async def _batch_refresh():
        from app.db.session import get_session_ctx
        async with get_session_ctx() as bg_db:
            for aid in account_ids:
                await _refresh_account_stats(aid, bg_db)

    background_tasks.add_task(_batch_refresh)
    return {"status": "queued", "account_count": len(account_ids)}


@router.get("/accounts/{account_id}")
async def get_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Account detail with associated visitors."""
    account = (await db.exec(select(Account).where(Account.id == account_id))).first()
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")

    visitors = (await db.exec(
        select(Visitor)
        .where(Visitor.account_id == account_id)
        .order_by(col(Visitor.intent_score).desc())
        .limit(100)
    )).all()

    return {
        **_account_dict(account),
        "visitors": [
            {
                "visitor_id": str(v.visitor_id),
                "intent_score": v.intent_score,
                "intent_stage": v.intent_stage,
                "total_visits": v.total_visits,
                "country": v.country,
                "last_seen_at": v.last_seen.isoformat() if v.last_seen else None,
            }
            for v in visitors
        ],
    }


@router.patch("/accounts/{account_id}")
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    """Update account enrichment data."""
    account = (await db.exec(select(Account).where(Account.id == account_id))).first()
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(account, field, value)
    account.updated_at = utcnow_naive()
    if payload.enrichment_status == "enriched" and not account.last_enriched_at:
        account.last_enriched_at = account.updated_at
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return _account_dict(account)


@router.post("/accounts/{account_id}/enrich")
async def enrich_account(
    account_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    """
    Re-trigger enrichment for an account (2.1.3).
    Finds the highest-intent visitor linked to this account and re-resolves their IP.
    Also refreshes account-level intent aggregates immediately.
    """
    account = (await db.exec(select(Account).where(Account.id == account_id))).first()
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")

    # Refresh aggregates immediately
    await _refresh_account_stats(account_id, db)

    # Find a visitor with an IP to re-enrich from
    visitor_with_ip = (await db.exec(
        select(Visitor)
        .where(Visitor.account_id == account_id)
        .where(Visitor.last_seen_ip.isnot(None))  # type: ignore[attr-defined]
        .order_by(col(Visitor.intent_score).desc())
        .limit(1)
    )).first()

    if visitor_with_ip and visitor_with_ip.last_seen_ip:
        # Reset ip_resolved_at so resolve will run again
        visitor_with_ip.ip_resolved_at = None
        visitor_with_ip.account_id = None
        db.add(visitor_with_ip)
        await db.commit()
        background_tasks.add_task(_resolve_and_link, visitor_with_ip.visitor_id, visitor_with_ip.last_seen_ip)
        return {"status": "queued", "account_id": str(account_id)}

    return {"status": "refreshed", "account_id": str(account_id), "note": "No visitor IP available for re-enrichment"}


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete account. Super admin only."""
    if current_user.role != "super_admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only super_admin can delete accounts")
    account = (await db.exec(select(Account).where(Account.id == account_id))).first()
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")

    # Unlink visitors before deletion
    visitors = (await db.exec(select(Visitor).where(Visitor.account_id == account_id))).all()
    for v in visitors:
        v.account_id = None
        db.add(v)

    await db.delete(account)
    await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _account_dict(a: Account) -> dict:
    return {
        "id": str(a.id),
        "company_name": a.company_name,
        "domain": a.domain,
        "industry": a.industry,
        "employee_count_range": a.employee_count_range,
        "annual_revenue_range": a.annual_revenue_range,
        "country": a.country,
        "city": a.city,
        "linkedin_url": a.linkedin_url,
        "logo_url": a.logo_url,
        "description": a.description,
        "enrichment_source": a.enrichment_source,
        "enrichment_status": a.enrichment_status,
        "last_enriched_at": a.last_enriched_at.isoformat() if a.last_enriched_at else None,
        "total_visitors": a.total_visitors,
        "total_page_views": a.total_page_views,
        "max_intent_score": a.max_intent_score,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }
