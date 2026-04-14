"""
Platform Admin API（Superuser 專用）
=====================================
提供跨租戶管理、平台統計、系統健康監控等功能。
所有 endpoint 均需 is_superuser=True。

Revision notes (참고 aihr admin.py):
- ForgeBase 沒有 UsageRecord / Document model；改用 rfq / visitor / chat_session 計量
- tenant 的 status 用 is_active (bool) 而非 status (str)
- 同步 aihr 的 dashboard / tenants / tenant-detail / users / system-health 架構
"""

import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_superuser
from app.db.session import get_session
from app.models.user import User
from app.models.tenant import Tenant

router = APIRouter(prefix="/admin", tags=["Platform Admin"])

_START_TIME = time.time()


# ═══════════════════════════════════════════
#  Response Schemas
# ═══════════════════════════════════════════


class TenantSummary(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    is_active: bool
    created_at: Optional[datetime]
    user_count: int = 0
    product_count: int = 0
    rfq_count: int = 0
    visitor_count: int = 0
    paypal_subscription_id: Optional[str] = None


class TenantDetail(TenantSummary):
    max_products: Optional[int]
    max_admins: Optional[int]
    paypal_payer_email: Optional[str]
    users: List[dict] = []
    recent_rfqs: List[dict] = []


class PlatformDashboard(BaseModel):
    total_tenants: int
    active_tenants: int
    total_users: int
    active_users: int
    total_products: int
    total_rfqs: int
    total_visitors: int
    # 近 7 天 RFQ 趨勢
    daily_rfqs: List[dict]
    top_tenants: List[dict]


class AdminUserInfo(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_superuser: bool
    tenant_id: Optional[str]
    tenant_name: Optional[str]
    created_at: Optional[datetime]
    last_login_at: Optional[datetime]


class SystemHealth(BaseModel):
    status: str
    database: str
    uptime_seconds: float
    python_version: str


class TenantUpdate(BaseModel):
    plan: Optional[str] = None
    is_active: Optional[bool] = None
    max_products: Optional[int] = None
    max_admins: Optional[int] = None


# ═══════════════════════════════════════════
#  Platform Dashboard
# ═══════════════════════════════════════════


@router.get("/dashboard", response_model=PlatformDashboard)
async def platform_dashboard(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    """平台總覽儀表板"""

    # Basic counts via raw SQL for performance
    row = await session.execute(
        text("""
            SELECT
                (SELECT COUNT(*) FROM tenants) AS total_tenants,
                (SELECT COUNT(*) FROM tenants WHERE is_active = TRUE) AS active_tenants,
                (SELECT COUNT(*) FROM users) AS total_users,
                (SELECT COUNT(*) FROM users WHERE is_active = TRUE) AS active_users,
                (SELECT COUNT(*) FROM products) AS total_products,
                (SELECT COUNT(*) FROM rfq_requests) AS total_rfqs,
                (SELECT COUNT(*) FROM visitors) AS total_visitors
        """)
    )
    counts = row.mappings().first() or {}

    # Daily RFQs — last 7 days
    since = datetime.now(timezone.utc) - timedelta(days=7)
    daily_rows = await session.execute(
        text("""
            SELECT DATE(created_at) AS day, COUNT(*) AS cnt
            FROM rfq_requests
            WHERE created_at >= :since
            GROUP BY DATE(created_at)
            ORDER BY day
        """),
        {"since": since},
    )
    daily_rfqs = [
        {"date": str(r["day"]), "count": r["cnt"]}
        for r in daily_rows.mappings().all()
    ]

    # Top 5 tenants by RFQ count
    top_rows = await session.execute(
        text("""
            SELECT t.name, COUNT(r.id) AS rfq_count
            FROM tenants t
            LEFT JOIN rfq_requests r ON r.tenant_id = t.id
            GROUP BY t.name
            ORDER BY rfq_count DESC
            LIMIT 5
        """)
    )
    top_tenants = [
        {"name": r["name"], "rfq_count": r["rfq_count"]}
        for r in top_rows.mappings().all()
    ]

    return PlatformDashboard(
        total_tenants=counts.get("total_tenants", 0),
        active_tenants=counts.get("active_tenants", 0),
        total_users=counts.get("total_users", 0),
        active_users=counts.get("active_users", 0),
        total_products=counts.get("total_products", 0),
        total_rfqs=counts.get("total_rfqs", 0),
        total_visitors=counts.get("total_visitors", 0),
        daily_rfqs=daily_rfqs,
        top_tenants=top_tenants,
    )


# ═══════════════════════════════════════════
#  Tenant Management
# ═══════════════════════════════════════════


@router.get("/tenants", response_model=List[TenantSummary])
async def list_all_tenants(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    """全租戶列表（含用量摘要）"""
    where_clauses = []
    params: dict = {"skip": skip, "limit": limit}

    if search:
        where_clauses.append("(t.name ILIKE :search OR t.slug ILIKE :search)")
        params["search"] = f"%{search}%"
    if is_active is not None:
        where_clauses.append("t.is_active = :is_active")
        params["is_active"] = is_active

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    rows = await session.execute(
        text(f"""
            SELECT
                t.id, t.name, t.slug, t.plan, t.is_active, t.created_at,
                t.max_products, t.max_admins,
                t.paypal_subscription_id,
                COALESCE(uc.cnt, 0) AS user_count,
                COALESCE(pc.cnt, 0) AS product_count,
                COALESCE(rc.cnt, 0) AS rfq_count,
                COALESCE(vc.cnt, 0) AS visitor_count
            FROM tenants t
            LEFT JOIN (SELECT tenant_id, COUNT(*) cnt FROM users GROUP BY tenant_id) uc ON uc.tenant_id = t.id
            LEFT JOIN (SELECT tenant_id, COUNT(*) cnt FROM products GROUP BY tenant_id) pc ON pc.tenant_id = t.id
            LEFT JOIN (SELECT tenant_id, COUNT(*) cnt FROM rfq_requests GROUP BY tenant_id) rc ON rc.tenant_id = t.id
            LEFT JOIN (SELECT tenant_id, COUNT(*) cnt FROM visitors GROUP BY tenant_id) vc ON vc.tenant_id = t.id
            {where_sql}
            ORDER BY t.created_at DESC
            OFFSET :skip LIMIT :limit
        """),
        params,
    )

    return [
        TenantSummary(
            id=str(r["id"]),
            name=r["name"],
            slug=r["slug"],
            plan=r["plan"],
            is_active=r["is_active"],
            created_at=r["created_at"],
            user_count=r["user_count"],
            product_count=r["product_count"],
            rfq_count=r["rfq_count"],
            visitor_count=r["visitor_count"],
            paypal_subscription_id=r["paypal_subscription_id"],
        )
        for r in rows.mappings().all()
    ]


@router.get("/tenants/{tenant_id}", response_model=TenantDetail)
async def get_tenant_detail(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    """單租戶詳細資訊 + 用戶列表 + 最近 RFQ"""
    from sqlmodel import select

    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Counts
    counts_row = await session.execute(
        text("""
            SELECT
                COALESCE((SELECT COUNT(*) FROM users WHERE tenant_id = :tid), 0) AS user_count,
                COALESCE((SELECT COUNT(*) FROM products WHERE tenant_id = :tid), 0) AS product_count,
                COALESCE((SELECT COUNT(*) FROM rfq_requests WHERE tenant_id = :tid), 0) AS rfq_count,
                COALESCE((SELECT COUNT(*) FROM visitors WHERE tenant_id = :tid), 0) AS visitor_count
        """),
        {"tid": str(tenant_id)},
    )
    counts = counts_row.mappings().first() or {}

    # Users
    user_rows = await session.execute(
        text("""
            SELECT id, email, full_name, role, is_active, created_at, last_login_at
            FROM users WHERE tenant_id = :tid ORDER BY created_at
        """),
        {"tid": str(tenant_id)},
    )
    users = [
        {
            "id": str(r["id"]),
            "email": r["email"],
            "full_name": r["full_name"],
            "role": r["role"],
            "is_active": r["is_active"],
        }
        for r in user_rows.mappings().all()
    ]

    # Recent RFQs (last 10)
    rfq_rows = await session.execute(
        text("""
            SELECT r.id, r.rfq_number, r.status, r.created_at,
                   c.email AS contact_email, COALESCE(c.full_name, c.company_name, r.rfq_number) AS contact_name
            FROM rfq_requests r
            LEFT JOIN contacts c ON c.id = r.contact_id
            WHERE r.tenant_id = :tid ORDER BY r.created_at DESC LIMIT 10
        """),
        {"tid": str(tenant_id)},
    )
    recent_rfqs = [
        {
            "id": str(r["id"]),
            "contact_name": r["contact_name"] or r["rfq_number"],
            "contact_email": r["contact_email"] or "",
            "status": r["status"],
            "submitted_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rfq_rows.mappings().all()
    ]

    return TenantDetail(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        max_products=tenant.max_products,
        max_admins=tenant.max_admins,
        paypal_subscription_id=tenant.paypal_subscription_id,
        paypal_payer_email=tenant.paypal_payer_email,
        user_count=counts.get("user_count", 0),
        product_count=counts.get("product_count", 0),
        rfq_count=counts.get("rfq_count", 0),
        visitor_count=counts.get("visitor_count", 0),
        users=users,
        recent_rfqs=recent_rfqs,
    )


@router.put("/tenants/{tenant_id}", response_model=TenantSummary)
async def update_tenant(
    tenant_id: UUID,
    body: TenantUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    """更新租戶方案 / 狀態 / Quota"""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.plan is not None:
        tenant.plan = body.plan
        # Sync quota from plan matrix
        from app.services.subscription import PLAN_MATRIX
        matrix = PLAN_MATRIX.get(body.plan, {})
        tenant.max_products = matrix.get("max_products", tenant.max_products)
        tenant.max_admins = matrix.get("max_admins", tenant.max_admins)

    if body.is_active is not None:
        tenant.is_active = body.is_active
    if body.max_products is not None:
        tenant.max_products = body.max_products
    if body.max_admins is not None:
        tenant.max_admins = body.max_admins

    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    return TenantSummary(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        max_products=tenant.max_products,
        max_admins=tenant.max_admins,
        paypal_subscription_id=tenant.paypal_subscription_id,
    )


# ═══════════════════════════════════════════
#  User Management
# ═══════════════════════════════════════════


@router.get("/users", response_model=List[AdminUserInfo])
async def list_all_users(
    search: Optional[str] = Query(None),
    tenant_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    """全用戶列表（跨租戶）"""
    where_clauses = []
    params: dict = {"skip": skip, "limit": limit}

    if search:
        where_clauses.append("(u.email ILIKE :search OR u.full_name ILIKE :search)")
        params["search"] = f"%{search}%"
    if tenant_id:
        where_clauses.append("u.tenant_id = :tenant_id")
        params["tenant_id"] = str(tenant_id)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    rows = await session.execute(
        text(f"""
            SELECT u.id, u.email, u.full_name, u.role, u.is_active, u.is_superuser,
                   u.tenant_id, u.created_at, u.last_login_at, t.name AS tenant_name
            FROM users u
            LEFT JOIN tenants t ON t.id = u.tenant_id
            {where_sql}
            ORDER BY u.created_at DESC
            OFFSET :skip LIMIT :limit
        """),
        params,
    )

    return [
        AdminUserInfo(
            id=str(r["id"]),
            email=r["email"],
            full_name=r["full_name"],
            role=r["role"],
            is_active=r["is_active"],
            is_superuser=r["is_superuser"],
            tenant_id=str(r["tenant_id"]) if r["tenant_id"] else None,
            tenant_name=r["tenant_name"],
            created_at=r["created_at"],
            last_login_at=r["last_login_at"],
        )
        for r in rows.mappings().all()
    ]


# ═══════════════════════════════════════════
#  System Health
# ═══════════════════════════════════════════


@router.get("/system/health", response_model=SystemHealth)
async def system_health(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    """平台系統健康狀態"""
    # DB ping
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return SystemHealth(
        status="healthy" if db_status == "ok" else "degraded",
        database=db_status,
        uptime_seconds=round(time.time() - _START_TIME, 1),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )
