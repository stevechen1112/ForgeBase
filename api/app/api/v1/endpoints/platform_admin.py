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

import json
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import clear_tenant_host_cache, require_superuser
from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.core.locale import PUBLIC_SITE_LOCALES
from app.core.security import get_password_hash
from app.db.session import get_session
from app.models.observability import (
    OperationalIncident,
    OperationalIncidentEvent,
    ServiceLevelSnapshot,
)
from app.models.platform_audit_log import PlatformAuditLog
from app.models.privacy_operation import PrivacyOperation
from app.models.site_build import SiteBuild
from app.models.site_profile import SiteProfile
from app.models.tenant import Tenant
from app.models.tenant_provisioning_run import TenantProvisioningRun
from app.models.user import User
from app.schemas.site_profile import SiteProfileRead, SiteProfileUpdate
from app.services.capability_access import (
    FEATURE_CATALOG,
    feature_catalog_payload,
    resolve_tenant_features,
)
from app.services.external_test_readiness import external_test_readiness
from app.services.observability import (
    collect_observability_snapshot,
    evaluate_service_levels,
    update_incident_status,
)
from app.services.privacy_operations import (
    erase_anonymous_visitor,
    export_anonymous_visitor,
    privacy_request_fingerprint,
    privacy_subject_hash,
    retention_inventory,
)
from app.services.privacy_retention import purge_expired_analytics
from app.services.recovery_evidence import load_recovery_evidence
from app.services.site_provisioning import (
    SITE_TEMPLATES,
    evaluate_delivery_stage,
    evaluate_site_readiness,
    template_catalog,
    validate_and_store_readiness,
)
from app.services.tenant_delivery_factory import (
    evaluate_provisioning_preflight,
    request_fingerprint,
)

router = APIRouter(prefix="/admin", tags=["Platform Admin"])

_START_TIME = time.time()
DELIVERY_STAGES = {"intake", "content", "build", "qa", "client_review", "launch_ready", "live", "on_hold"}
ACCEPTANCE_STATUSES = {"pending", "requested", "accepted", "waived"}


# ═══════════════════════════════════════════
#  Response Schemas
# ═══════════════════════════════════════════


class TenantSummary(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    created_at: Optional[datetime]
    user_count: int = 0
    product_count: int = 0
    rfq_count: int = 0
    visitor_count: int = 0
    rfq_count_30d: int = 0
    failed_job_count: int = 0
    last_activity_at: Optional[datetime] = None
    site_build_status: Optional[str] = None
    primary_domain: Optional[str] = None
    cms_connected: bool = False
    site_ready: bool = False
    attention_reasons: List[str] = Field(default_factory=list)


class TenantDetail(TenantSummary):
    feature_overrides: dict[str, bool] = Field(default_factory=dict)
    resolved_features: dict[str, bool] = Field(default_factory=dict)
    users: List[dict] = Field(default_factory=list)
    recent_rfqs: List[dict] = Field(default_factory=list)


class PlatformDashboard(BaseModel):
    total_tenants: int
    active_tenants: int
    total_users: int
    active_users: int
    total_products: int
    total_rfqs: int
    total_visitors: int
    legacy_unassigned_rfqs: int
    legacy_unassigned_visitors: int
    published_sites: int
    blocked_sites: int
    tenants_needing_attention: int
    failed_jobs: int
    rfqs_30d: int
    # 近 7 天 RFQ 趨勢
    daily_rfqs: List[dict]
    top_tenants: List[dict]
    attention_tenants: List[dict]


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
    external_test: dict


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    feature_overrides: Optional[dict[str, bool]] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Tenant name must contain at least 2 characters")
        return normalized

    @field_validator("feature_overrides")
    @classmethod
    def validate_feature_overrides(cls, value: Optional[dict[str, bool]]) -> Optional[dict[str, bool]]:
        if value is None:
            return value
        unknown = set(value) - set(FEATURE_CATALOG)
        unavailable = {key for key in value if not FEATURE_CATALOG[key].get("configurable", True)}
        if unknown:
            raise ValueError(f"Unknown features: {', '.join(sorted(unknown))}")
        if unavailable:
            raise ValueError(f"Features not configurable: {', '.join(sorted(unavailable))}")
        return value


class PlatformOperatorCreate(BaseModel):
    """Create a ForgeBase internal operator; never creates a tenant account."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    temporary_password: str = Field(min_length=12, max_length=128)


class PlatformOperatorUpdate(BaseModel):
    is_active: bool


class TenantProvisionIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=100)
    owner_email: EmailStr
    owner_full_name: str = Field(min_length=2, max_length=100)
    temporary_password: str = Field(min_length=12, max_length=128)
    template_key: str = "handtool-company"
    brand_name: str = Field(min_length=2, max_length=120)
    logo_mark: str = Field(min_length=1, max_length=10)
    contact_email: EmailStr
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    site_url: str = Field(min_length=8, max_length=500)
    primary_domain: Optional[str] = Field(default=None, max_length=255)
    default_locale: str = Field(default="zh-TW", pattern=r"^(en|zh-TW|ja|fr|ru)$")
    locales: list[str] = Field(default_factory=lambda: ["en"], min_length=1, max_length=5)
    theme_key: str = Field(default="cobalt", max_length=30)
    layout_key: str = Field(default="classic", max_length=30)

    @field_validator("template_key")
    @classmethod
    def validate_template(cls, value: str) -> str:
        if value not in SITE_TEMPLATES:
            raise ValueError("Unknown site template")
        return value

    @field_validator("locales")
    @classmethod
    def validate_locales(cls, value: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(value))
        if any(locale not in PUBLIC_SITE_LOCALES for locale in cleaned):
            raise ValueError("Unsupported public-site locale")
        return cleaned


class VisitorPrivacyOperationIn(BaseModel):
    tenant_id: UUID
    visitor_id: UUID
    reason: str = Field(min_length=10, max_length=500)


class RetentionRunIn(BaseModel):
    confirm: bool = False
    reason: str = Field(min_length=10, max_length=500)


class IncidentActionIn(BaseModel):
    action: str = Field(pattern=r"^(acknowledge|resolve)$")
    note: str = Field(min_length=10, max_length=1000)


class SiteBuildUpdate(BaseModel):
    template_key: Optional[str] = None
    primary_domain: Optional[str] = Field(default=None, max_length=255)
    locales: Optional[list[str]] = None
    customization: Optional[dict[str, Any]] = None
    cms_connected: Optional[bool] = None
    delivery_stage: Optional[str] = None
    delivery_owner_id: Optional[UUID] = None
    target_launch_at: Optional[datetime] = None
    handoff_at: Optional[datetime] = None
    acceptance_status: Optional[str] = None
    internal_note: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("template_key")
    @classmethod
    def validate_template(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in SITE_TEMPLATES:
            raise ValueError("Unknown site template")
        return value

    @field_validator("delivery_stage")
    @classmethod
    def validate_delivery_stage(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in DELIVERY_STAGES:
            raise ValueError("Unknown delivery stage")
        return value

    @field_validator("acceptance_status")
    @classmethod
    def validate_acceptance_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in ACCEPTANCE_STATUSES:
            raise ValueError("Unknown acceptance status")
        return value


class SiteBuildCreate(BaseModel):
    template_key: str = "handtool-company"
    primary_domain: Optional[str] = Field(default=None, max_length=255)
    locales: list[str] = Field(default_factory=lambda: ["en"], min_length=1, max_length=5)
    delivery_stage: str = "intake"
    target_launch_at: Optional[datetime] = None

    @field_validator("template_key")
    @classmethod
    def validate_template(cls, value: str) -> str:
        if value not in SITE_TEMPLATES:
            raise ValueError("Unknown site template")
        return value

    @field_validator("locales")
    @classmethod
    def validate_locales(cls, value: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(value))
        if any(locale not in PUBLIC_SITE_LOCALES for locale in cleaned):
            raise ValueError("Unsupported locales")
        return cleaned

    @field_validator("delivery_stage")
    @classmethod
    def validate_delivery_stage(cls, value: str) -> str:
        if value not in DELIVERY_STAGES:
            raise ValueError("Unknown delivery stage")
        return value


class PlatformAuditItem(BaseModel):
    id: str
    actor_email: str
    action: str
    target_type: str
    target_id: Optional[str]
    changes: dict[str, Any]
    created_at: datetime


class PlatformWorkItem(BaseModel):
    kind: str
    severity: str
    title: str
    detail: str
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None
    href: str
    created_at: Optional[datetime] = None


class PlatformWorkspace(BaseModel):
    counts: dict[str, int]
    work_items: List[PlatformWorkItem]


class DeliveryBoardItem(BaseModel):
    id: str
    tenant_id: str
    tenant_name: str
    tenant_slug: str
    template_key: str
    delivery_stage: str
    acceptance_status: str
    delivery_owner_id: Optional[str] = None
    delivery_owner_name: Optional[str] = None
    target_launch_at: Optional[datetime] = None
    handoff_at: Optional[datetime] = None
    technical_status: str
    primary_domain: Optional[str] = None
    cms_connected: bool
    readiness: dict[str, Any] = Field(default_factory=dict)
    last_error: Optional[str] = None
    updated_at: datetime


class PlatformRFQItem(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    tenant_name: str
    rfq_number: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    status: str
    priority: str
    quality_score: int
    assigned_to: Optional[str] = None
    assigned_name: Optional[str] = None
    sla_due_at: Optional[datetime] = None
    sla_breached: bool
    created_at: datetime
    is_spam: bool
    is_test_data: bool


class PlatformRFQList(BaseModel):
    data: List[PlatformRFQItem]
    total: int


class PlatformResourceStatus(BaseModel):
    external_test: dict[str, Any]
    forms: dict[str, Any]
    email: dict[str, Any]
    storage: dict[str, Any]
    backups: dict[str, Any]
    monitoring: dict[str, Any]


class PlatformUsageSummary(BaseModel):
    totals: dict[str, int]
    tenants: List[dict[str, Any]]


async def _record_platform_audit(
    session: AsyncSession,
    actor: User,
    *,
    action: str,
    target_type: str,
    target_id: str | None,
    tenant_id: UUID | None,
    changes: dict[str, Any],
) -> None:
    session.add(
        PlatformAuditLog(
            actor_user_id=actor.id,
            tenant_id=tenant_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            changes_json=json.dumps(changes, default=str, ensure_ascii=False),
        )
    )


def _parse_readiness_ready(value: Any) -> bool:
    if not value:
        return False
    try:
        payload = value if isinstance(value, dict) else json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return payload.get("ready") is True


def _naive_utc(value: datetime | None) -> datetime | None:
    """Keep API date inputs compatible with legacy TIMESTAMP WITHOUT TIME ZONE columns."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _tenant_attention_reasons(row: Any) -> list[str]:
    reasons: list[str] = []
    if not row["is_active"]:
        reasons.append("tenant_inactive")
    if not row.get("site_build_status"):
        reasons.append("site_build_missing")
    elif row["site_build_status"] != "published":
        reasons.append("site_not_published")
    if row.get("site_build_status") == "blocked" or row.get("site_last_error"):
        reasons.append("site_blocked")
    if not row.get("cms_connected", False):
        reasons.append("cms_not_connected")
    if int(row.get("active_owner_count") or 0) == 0:
        reasons.append("active_owner_missing")
    if int(row.get("failed_job_count") or 0) > 0:
        reasons.append("failed_jobs")
    return list(dict.fromkeys(reasons))


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
    row = await session.exec(
        text("""
            SELECT
                (SELECT COUNT(*) FROM tenants) AS total_tenants,
                (SELECT COUNT(*) FROM tenants WHERE is_active = TRUE) AS active_tenants,
                (SELECT COUNT(*) FROM users) AS total_users,
                (SELECT COUNT(*) FROM users WHERE is_active = TRUE) AS active_users,
                (SELECT COUNT(*) FROM products) AS total_products,
                (SELECT COUNT(*) FROM rfq_requests WHERE tenant_id IS NOT NULL AND is_test_data = FALSE) AS total_rfqs,
                (SELECT COUNT(*) FROM visitors WHERE tenant_id IS NOT NULL AND is_test_data = FALSE) AS total_visitors,
                (SELECT COUNT(*) FROM rfq_requests WHERE tenant_id IS NULL AND is_test_data = FALSE) AS legacy_unassigned_rfqs,
                (SELECT COUNT(*) FROM visitors WHERE tenant_id IS NULL AND is_test_data = FALSE) AS legacy_unassigned_visitors,
                (SELECT COUNT(*) FROM site_builds WHERE status = 'published') AS published_sites,
                (SELECT COUNT(*) FROM site_builds WHERE status = 'blocked') AS blocked_sites,
                (SELECT COUNT(*) FROM operational_jobs WHERE status = 'failed') AS failed_jobs,
                (SELECT COUNT(*) FROM rfq_requests WHERE tenant_id IS NOT NULL AND is_test_data = FALSE AND created_at >= NOW() - INTERVAL '30 days') AS rfqs_30d,
                (
                    SELECT COUNT(*) FROM tenants t
                    WHERE t.is_active = FALSE
                       OR NOT EXISTS (
                           SELECT 1 FROM site_builds sb
                           WHERE sb.tenant_id = t.id AND sb.status = 'published' AND sb.cms_connected = TRUE
                       )
                       OR NOT EXISTS (
                           SELECT 1 FROM users u
                           WHERE u.tenant_id = t.id AND u.role = 'owner' AND u.is_active = TRUE
                       )
                       OR EXISTS (
                           SELECT 1 FROM operational_jobs oj
                           WHERE oj.tenant_id = t.id AND oj.status = 'failed'
                       )
                ) AS tenants_needing_attention
        """)
    )
    counts = row.mappings().first() or {}

    # Daily RFQs — last 7 days
    since = datetime.now(timezone.utc) - timedelta(days=7)
    daily_rows = await session.exec(
        text("""
            SELECT DATE(created_at) AS day, COUNT(*) AS cnt
            FROM rfq_requests
            WHERE tenant_id IS NOT NULL AND created_at >= :since AND is_test_data = FALSE
            GROUP BY DATE(created_at)
            ORDER BY day
        """),
        params={"since": since},
    )
    daily_rfqs = [
        {"date": str(r["day"]), "count": r["cnt"]}
        for r in daily_rows.mappings().all()
    ]

    # Top 5 tenants by RFQ count
    top_rows = await session.exec(
        text("""
            SELECT t.name, COUNT(r.id) AS rfq_count
            FROM tenants t
            LEFT JOIN rfq_requests r ON r.tenant_id = t.id AND r.is_test_data = FALSE
            GROUP BY t.name
            ORDER BY rfq_count DESC
            LIMIT 5
        """)
    )
    top_tenants = [
        {"name": r["name"], "rfq_count": r["rfq_count"]}
        for r in top_rows.mappings().all()
    ]

    attention_rows = await session.exec(
        text("""
            SELECT t.id, t.name, t.slug, t.is_active,
                   sb.status AS site_build_status, sb.primary_domain,
                   COALESCE(sb.cms_connected, FALSE) AS cms_connected,
                   sb.last_error AS site_last_error,
                   COALESCE(owners.cnt, 0) AS active_owner_count,
                   COALESCE(jobs.cnt, 0) AS failed_job_count
            FROM tenants t
            LEFT JOIN site_builds sb ON sb.tenant_id = t.id
            LEFT JOIN (
                SELECT tenant_id, COUNT(*) cnt FROM users
                WHERE role = 'owner' AND is_active = TRUE GROUP BY tenant_id
            ) owners ON owners.tenant_id = t.id
            LEFT JOIN (
                SELECT tenant_id, COUNT(*) cnt FROM operational_jobs
                WHERE status = 'failed' GROUP BY tenant_id
            ) jobs ON jobs.tenant_id = t.id
            WHERE t.is_active = FALSE
               OR sb.id IS NULL OR sb.status != 'published' OR sb.cms_connected = FALSE
               OR COALESCE(owners.cnt, 0) = 0 OR COALESCE(jobs.cnt, 0) > 0
            ORDER BY COALESCE(jobs.cnt, 0) DESC, t.updated_at DESC
            LIMIT 8
        """)
    )
    attention_tenants = [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "slug": r["slug"],
            "reasons": _tenant_attention_reasons(r),
        }
        for r in attention_rows.mappings().all()
    ]

    return PlatformDashboard(
        total_tenants=counts.get("total_tenants", 0),
        active_tenants=counts.get("active_tenants", 0),
        total_users=counts.get("total_users", 0),
        active_users=counts.get("active_users", 0),
        total_products=counts.get("total_products", 0),
        total_rfqs=counts.get("total_rfqs", 0),
        total_visitors=counts.get("total_visitors", 0),
        legacy_unassigned_rfqs=counts.get("legacy_unassigned_rfqs", 0),
        legacy_unassigned_visitors=counts.get("legacy_unassigned_visitors", 0),
        published_sites=counts.get("published_sites", 0),
        blocked_sites=counts.get("blocked_sites", 0),
        tenants_needing_attention=counts.get("tenants_needing_attention", 0),
        failed_jobs=counts.get("failed_jobs", 0),
        rfqs_30d=counts.get("rfqs_30d", 0),
        daily_rfqs=daily_rfqs,
        top_tenants=top_tenants,
        attention_tenants=attention_tenants,
    )


@router.get("/workspace", response_model=PlatformWorkspace)
async def platform_workspace(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    """One operational queue for managed delivery; it never sends external email."""
    counts_row = await session.exec(
        text("""
            SELECT
                (SELECT COUNT(*) FROM adoption_applications
                 WHERE is_test_data = FALSE AND status IN ('new', 'reviewing')) AS adoption_review,
                (SELECT COUNT(*) FROM site_builds
                 WHERE status != 'published' OR delivery_stage != 'live') AS delivery_open,
                (SELECT COUNT(*) FROM rfq_requests
                 WHERE is_test_data = FALSE AND is_spam = FALSE
                   AND status IN ('new', 'assigned', 'in_progress', 'quoted', 'negotiation')
                   AND (assigned_to IS NULL OR sla_breached = TRUE)) AS rfq_attention,
                (SELECT COUNT(*) FROM operational_jobs WHERE status = 'failed') AS failed_jobs
        """)
    )
    counts = {key: int(value or 0) for key, value in (counts_row.mappings().first() or {}).items()}
    items: list[PlatformWorkItem] = []

    applications = await session.exec(
        text("""
            SELECT id, company_name, status, created_at
            FROM adoption_applications
            WHERE is_test_data = FALSE AND status IN ('new', 'reviewing')
            ORDER BY created_at ASC LIMIT 8
        """)
    )
    for row in applications.mappings().all():
        items.append(PlatformWorkItem(
            kind="adoption_application",
            severity="high" if row["status"] == "new" else "normal",
            title=f"導入申請：{row['company_name']}",
            detail="等待平台人員評估與決定下一步",
            href="/platform/applications",
            created_at=row["created_at"],
        ))

    delivery_rows = await session.exec(
        text("""
            SELECT sb.id, sb.tenant_id, t.name AS tenant_name, sb.delivery_stage,
                   sb.status, sb.last_error, sb.target_launch_at, sb.updated_at
            FROM site_builds sb
            JOIN tenants t ON t.id = sb.tenant_id
            WHERE sb.status != 'published' OR sb.delivery_stage != 'live'
            ORDER BY
                CASE WHEN sb.status = 'blocked' THEN 0 ELSE 1 END,
                sb.target_launch_at NULLS LAST, sb.updated_at ASC
            LIMIT 10
        """)
    )
    for row in delivery_rows.mappings().all():
        detail = row["last_error"] or f"目前交付階段：{row['delivery_stage']}"
        items.append(PlatformWorkItem(
            kind="delivery",
            severity="urgent" if row["status"] == "blocked" else "normal",
            title=f"網站交付：{row['tenant_name']}",
            detail=detail,
            tenant_id=str(row["tenant_id"]),
            tenant_name=row["tenant_name"],
            href=f"/platform/tenants/{row['tenant_id']}",
            created_at=row["updated_at"],
        ))

    rfq_rows = await session.exec(
        text("""
            SELECT r.id, r.tenant_id, t.name AS tenant_name, r.rfq_number,
                   r.priority, r.assigned_to, r.sla_breached, r.created_at
            FROM rfq_requests r
            LEFT JOIN tenants t ON t.id = r.tenant_id
            WHERE r.is_test_data = FALSE AND r.is_spam = FALSE
              AND r.status IN ('new', 'assigned', 'in_progress', 'quoted', 'negotiation')
              AND (r.assigned_to IS NULL OR r.sla_breached = TRUE)
            ORDER BY r.sla_breached DESC, r.created_at ASC
            LIMIT 10
        """)
    )
    for row in rfq_rows.mappings().all():
        attention = "已逾期" if row["sla_breached"] else "尚未指派負責業務"
        items.append(PlatformWorkItem(
            kind="rfq",
            severity="urgent" if row["sla_breached"] else "high",
            title=f"RFQ {row['rfq_number']}：{row['tenant_name'] or '未歸屬租戶'}",
            detail=attention,
            tenant_id=str(row["tenant_id"]) if row["tenant_id"] else None,
            tenant_name=row["tenant_name"],
            href="/platform/rfqs",
            created_at=row["created_at"],
        ))

    failed_jobs = await session.exec(
        text("""
            SELECT oj.id, oj.tenant_id, t.name AS tenant_name, oj.job_type,
                   oj.last_error, oj.updated_at
            FROM operational_jobs oj
            LEFT JOIN tenants t ON t.id = oj.tenant_id
            WHERE oj.status = 'failed'
            ORDER BY oj.updated_at ASC LIMIT 10
        """)
    )
    for row in failed_jobs.mappings().all():
        items.append(PlatformWorkItem(
            kind="operational_job",
            severity="urgent",
            title=f"背景工作失敗：{row['job_type']}",
            detail=(row["last_error"] or "等待平台人員檢查")[:240],
            tenant_id=str(row["tenant_id"]) if row["tenant_id"] else None,
            tenant_name=row["tenant_name"],
            href="/platform/health",
            created_at=row["updated_at"],
        ))

    external = external_test_readiness()
    for blocker in external["blockers"]:
        items.append(PlatformWorkItem(
            kind="external_readiness",
            severity="high",
            title=f"對外測試封板：{external['checks'][blocker]['label']}",
            detail="尚未完成有效設定，因此不可宣告可對不特定外部流量開放。",
            href="/platform/resources",
        ))

    severity_order = {"urgent": 0, "high": 1, "normal": 2}
    items.sort(
        key=lambda item: (
            severity_order.get(item.severity, 9),
            _naive_utc(item.created_at) or datetime.max,
        )
    )
    return PlatformWorkspace(counts=counts, work_items=items[:32])


@router.get("/delivery-board", response_model=List[DeliveryBoardItem])
async def delivery_board(
    stage: Optional[str] = Query(None),
    include_live: bool = False,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    if stage and stage not in DELIVERY_STAGES:
        raise HTTPException(status_code=422, detail="Unknown delivery stage")
    filters = []
    params: dict[str, Any] = {}
    if stage:
        filters.append("sb.delivery_stage = :stage")
        params["stage"] = stage
    if not include_live:
        filters.append("sb.delivery_stage != 'live'")
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    rows = await session.exec(
        text(f"""
            SELECT sb.id, sb.tenant_id, t.name AS tenant_name, t.slug AS tenant_slug,
                   sb.template_key, sb.delivery_stage, sb.acceptance_status,
                   sb.delivery_owner_id, owner.full_name AS delivery_owner_name,
                   sb.target_launch_at, sb.handoff_at, sb.status AS technical_status,
                   sb.primary_domain, sb.cms_connected, sb.readiness_json,
                   sb.last_error, sb.updated_at
            FROM site_builds sb
            JOIN tenants t ON t.id = sb.tenant_id
            LEFT JOIN users owner ON owner.id = sb.delivery_owner_id
            {where_sql}
            ORDER BY
                CASE WHEN sb.status = 'blocked' THEN 0 ELSE 1 END,
                sb.target_launch_at NULLS LAST, sb.updated_at ASC
        """),
        params=params,
    )
    return [
        DeliveryBoardItem(
            id=str(row["id"]), tenant_id=str(row["tenant_id"]),
            tenant_name=row["tenant_name"], tenant_slug=row["tenant_slug"],
            template_key=row["template_key"], delivery_stage=row["delivery_stage"],
            acceptance_status=row["acceptance_status"],
            delivery_owner_id=str(row["delivery_owner_id"]) if row["delivery_owner_id"] else None,
            delivery_owner_name=row["delivery_owner_name"], target_launch_at=row["target_launch_at"],
            handoff_at=row["handoff_at"], technical_status=row["technical_status"],
            primary_domain=row["primary_domain"], cms_connected=bool(row["cms_connected"]),
            readiness=json.loads(row["readiness_json"] or "{}"), last_error=row["last_error"],
            updated_at=row["updated_at"],
        )
        for row in rows.mappings().all()
    ]


@router.get("/rfqs", response_model=PlatformRFQList)
async def platform_rfqs(
    status: Optional[str] = Query(None),
    needs_attention: bool = False,
    include_spam: bool = False,
    include_test: bool = False,
    search: Optional[str] = Query(None, max_length=200),
    limit: int = Query(100, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    filters = []
    params: dict[str, Any] = {"limit": limit}
    if status:
        filters.append("r.status = :status")
        params["status"] = status
    if not include_spam:
        filters.append("r.is_spam = FALSE")
    if not include_test:
        filters.append("r.is_test_data = FALSE")
    if needs_attention:
        filters.append(
            "(r.status IN ('new', 'assigned', 'in_progress', 'quoted', 'negotiation') "
            "AND (r.assigned_to IS NULL OR r.sla_breached = TRUE))"
        )
    if search:
        filters.append("(r.rfq_number ILIKE :search OR t.name ILIKE :search OR r.form_data ILIKE :search)")
        params["search"] = f"%{search.strip()}%"
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    count_row = await session.exec(
        text(f"SELECT COUNT(*) AS total FROM rfq_requests r LEFT JOIN tenants t ON t.id = r.tenant_id {where_sql}"),
        params=params,
    )
    rows = await session.exec(
        text(f"""
            SELECT r.id, r.tenant_id, t.name AS tenant_name, r.rfq_number, r.form_data,
                   r.status, r.priority, r.quality_score, r.assigned_to,
                   assignee.full_name AS assigned_name, r.sla_due_at, r.sla_breached,
                   r.created_at, r.is_spam, r.is_test_data
            FROM rfq_requests r
            LEFT JOIN tenants t ON t.id = r.tenant_id
            LEFT JOIN users assignee ON assignee.id = r.assigned_to
            {where_sql}
            ORDER BY r.sla_breached DESC, r.created_at DESC
            LIMIT :limit
        """),
        params=params,
    )
    data: list[PlatformRFQItem] = []
    for row in rows.mappings().all():
        try:
            form_data = json.loads(row["form_data"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            form_data = {}
        data.append(PlatformRFQItem(
            id=str(row["id"]), tenant_id=str(row["tenant_id"]) if row["tenant_id"] else None,
            tenant_name=row["tenant_name"] or "未歸屬租戶", rfq_number=row["rfq_number"],
            contact_name=form_data.get("full_name") or form_data.get("contact_name"),
            contact_email=form_data.get("email") or form_data.get("contact_email"),
            status=row["status"], priority=row["priority"], quality_score=int(row["quality_score"] or 0),
            assigned_to=str(row["assigned_to"]) if row["assigned_to"] else None,
            assigned_name=row["assigned_name"], sla_due_at=row["sla_due_at"],
            sla_breached=bool(row["sla_breached"]), created_at=row["created_at"],
            is_spam=bool(row["is_spam"]), is_test_data=bool(row["is_test_data"]),
        ))
    return PlatformRFQList(data=data, total=int((count_row.mappings().first() or {}).get("total", 0)))


# ═══════════════════════════════════════════
#  Tenant Management
# ═══════════════════════════════════════════


@router.get("/feature-catalog")
async def get_feature_catalog(_: User = Depends(require_superuser)) -> Any:
    """Return capability defaults and governance metadata."""
    return {"features": feature_catalog_payload()}


@router.get("/tenants", response_model=List[TenantSummary])
async def list_all_tenants(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    site_status: Optional[str] = Query(None),
    needs_attention: Optional[bool] = Query(None),
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
    if site_status is not None:
        if site_status not in {"missing", "draft", "ready", "blocked", "published"}:
            raise HTTPException(status_code=422, detail="Unknown site status")
        where_clauses.append("COALESCE(sb.status, 'missing') = :site_status")
        params["site_status"] = site_status
    if needs_attention is not None:
        attention_sql = """(
            t.is_active = FALSE OR sb.id IS NULL OR sb.status != 'published'
            OR sb.cms_connected = FALSE OR COALESCE(owners.cnt, 0) = 0
            OR COALESCE(jobs.cnt, 0) > 0
        )"""
        where_clauses.append(attention_sql if needs_attention else f"NOT {attention_sql}")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    rows = await session.exec(
        text(f"""
            SELECT
                t.id, t.name, t.slug, t.is_active, t.created_at,
                COALESCE(uc.cnt, 0) AS user_count,
                COALESCE(pc.cnt, 0) AS product_count,
                COALESCE(rc.cnt, 0) AS rfq_count,
                COALESCE(rc.cnt_30d, 0) AS rfq_count_30d,
                COALESCE(vc.cnt, 0) AS visitor_count,
                COALESCE(jobs.cnt, 0) AS failed_job_count,
                COALESCE(owners.cnt, 0) AS active_owner_count,
                GREATEST(rc.last_at, vc.last_at, cc.last_at) AS last_activity_at,
                sb.status AS site_build_status, sb.primary_domain,
                COALESCE(sb.cms_connected, FALSE) AS cms_connected,
                sb.readiness_json, sb.last_error AS site_last_error
            FROM tenants t
            LEFT JOIN (SELECT tenant_id, COUNT(*) cnt FROM users GROUP BY tenant_id) uc ON uc.tenant_id = t.id
            LEFT JOIN (SELECT tenant_id, COUNT(*) cnt FROM products GROUP BY tenant_id) pc ON pc.tenant_id = t.id
            LEFT JOIN (
                SELECT tenant_id, COUNT(*) cnt,
                       COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') cnt_30d,
                       MAX(created_at) last_at
                FROM rfq_requests WHERE is_test_data = FALSE GROUP BY tenant_id
            ) rc ON rc.tenant_id = t.id
            LEFT JOIN (
                SELECT tenant_id, COUNT(*) cnt, MAX(last_activity_at) last_at
                FROM visitors WHERE is_test_data = FALSE GROUP BY tenant_id
            ) vc ON vc.tenant_id = t.id
            LEFT JOIN (
                SELECT tenant_id, MAX(created_at) last_at FROM chat_sessions GROUP BY tenant_id
            ) cc ON cc.tenant_id = t.id
            LEFT JOIN (
                SELECT tenant_id, COUNT(*) cnt FROM users
                WHERE role = 'owner' AND is_active = TRUE GROUP BY tenant_id
            ) owners ON owners.tenant_id = t.id
            LEFT JOIN (
                SELECT tenant_id, COUNT(*) cnt FROM operational_jobs
                WHERE status = 'failed' GROUP BY tenant_id
            ) jobs ON jobs.tenant_id = t.id
            LEFT JOIN site_builds sb ON sb.tenant_id = t.id
            {where_sql}
            ORDER BY COALESCE(jobs.cnt, 0) DESC,
                     CASE WHEN sb.status = 'published' THEN 1 ELSE 0 END,
                     GREATEST(rc.last_at, vc.last_at, cc.last_at) DESC NULLS LAST,
                     t.created_at DESC
            OFFSET :skip LIMIT :limit
        """),
        params=params,
    )

    result: list[TenantSummary] = []
    for r in rows.mappings().all():
        result.append(TenantSummary(
            id=str(r["id"]),
            name=r["name"],
            slug=r["slug"],
            is_active=r["is_active"],
            created_at=r["created_at"],
            user_count=r["user_count"],
            product_count=r["product_count"],
            rfq_count=r["rfq_count"],
            visitor_count=r["visitor_count"],
            rfq_count_30d=r["rfq_count_30d"],
            failed_job_count=r["failed_job_count"],
            last_activity_at=r["last_activity_at"],
            site_build_status=r["site_build_status"],
            primary_domain=r["primary_domain"],
            cms_connected=r["cms_connected"],
            site_ready=_parse_readiness_ready(r["readiness_json"]),
            attention_reasons=_tenant_attention_reasons(r),
        ))
    return result


@router.get("/tenants/{tenant_id}", response_model=TenantDetail)
async def get_tenant_detail(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    """單租戶詳細資訊 + 用戶列表 + 最近 RFQ"""

    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Counts
    counts_row = await session.exec(
        text("""
            SELECT
                COALESCE((SELECT COUNT(*) FROM users WHERE tenant_id = :tid), 0) AS user_count,
                COALESCE((SELECT COUNT(*) FROM products WHERE tenant_id = :tid), 0) AS product_count,
                COALESCE((SELECT COUNT(*) FROM rfq_requests WHERE tenant_id = :tid AND is_test_data = FALSE), 0) AS rfq_count,
                COALESCE((SELECT COUNT(*) FROM rfq_requests WHERE tenant_id = :tid AND is_test_data = FALSE AND created_at >= NOW() - INTERVAL '30 days'), 0) AS rfq_count_30d,
                COALESCE((SELECT COUNT(*) FROM visitors WHERE tenant_id = :tid AND is_test_data = FALSE), 0) AS visitor_count,
                COALESCE((SELECT COUNT(*) FROM operational_jobs WHERE tenant_id = :tid AND status = 'failed'), 0) AS failed_job_count,
                COALESCE((SELECT COUNT(*) FROM users WHERE tenant_id = :tid AND role = 'owner' AND is_active = TRUE), 0) AS active_owner_count,
                GREATEST(
                    (SELECT MAX(created_at) FROM rfq_requests WHERE tenant_id = :tid AND is_test_data = FALSE),
                    (SELECT MAX(last_activity_at) FROM visitors WHERE tenant_id = :tid AND is_test_data = FALSE),
                    (SELECT MAX(created_at) FROM chat_sessions WHERE tenant_id = :tid)
                ) AS last_activity_at,
                (SELECT status FROM site_builds WHERE tenant_id = :tid) AS site_build_status,
                (SELECT primary_domain FROM site_builds WHERE tenant_id = :tid) AS primary_domain,
                COALESCE((SELECT cms_connected FROM site_builds WHERE tenant_id = :tid), FALSE) AS cms_connected,
                (SELECT readiness_json FROM site_builds WHERE tenant_id = :tid) AS readiness_json,
                (SELECT last_error FROM site_builds WHERE tenant_id = :tid) AS site_last_error
        """),
        params={"tid": str(tenant_id)},
    )
    counts = counts_row.mappings().first() or {}

    # Users
    user_rows = await session.exec(
        text("""
            SELECT id, email, full_name, role, is_active, created_at, last_login_at
            FROM users WHERE tenant_id = :tid ORDER BY created_at
        """),
        params={"tid": str(tenant_id)},
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
    rfq_rows = await session.exec(
        text("""
            SELECT r.id, r.rfq_number, r.status, r.created_at,
                   c.email AS contact_email, COALESCE(c.full_name, c.company_name, r.rfq_number) AS contact_name
            FROM rfq_requests r
            LEFT JOIN contacts c ON c.id = r.contact_id
            WHERE r.tenant_id = :tid AND r.is_test_data = FALSE ORDER BY r.created_at DESC LIMIT 10
        """),
        params={"tid": str(tenant_id)},
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
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        feature_overrides=tenant.feature_overrides or {},
        resolved_features=resolve_tenant_features(tenant),
        user_count=counts.get("user_count", 0),
        product_count=counts.get("product_count", 0),
        rfq_count=counts.get("rfq_count", 0),
        visitor_count=counts.get("visitor_count", 0),
        rfq_count_30d=counts.get("rfq_count_30d", 0),
        failed_job_count=counts.get("failed_job_count", 0),
        last_activity_at=counts.get("last_activity_at"),
        site_build_status=counts.get("site_build_status"),
        primary_domain=counts.get("primary_domain"),
        cms_connected=counts.get("cms_connected", False),
        site_ready=_parse_readiness_ready(counts.get("readiness_json")),
        attention_reasons=_tenant_attention_reasons({**counts, "is_active": tenant.is_active}),
        users=users,
        recent_rfqs=recent_rfqs,
    )


@router.put("/tenants/{tenant_id}", response_model=TenantSummary)
async def update_tenant(
    tenant_id: UUID,
    body: TenantUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    """Update tenant identity, status, and governed capability overrides."""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    before = {
        "name": tenant.name,
        "feature_overrides": tenant.feature_overrides or {},
        "is_active": tenant.is_active,
    }
    if body.name is not None:
        tenant.name = body.name

    if body.feature_overrides is not None:
        tenant.feature_overrides = dict(body.feature_overrides)

    if body.is_active is not None:
        tenant.is_active = body.is_active

    after = {
        "name": tenant.name,
        "feature_overrides": tenant.feature_overrides or {},
        "is_active": tenant.is_active,
    }
    changes = {
        key: {"from": before[key], "to": value}
        for key, value in after.items()
        if before[key] != value
    }
    if not changes:
        raise HTTPException(status_code=422, detail="No tenant changes supplied")

    tenant.updated_at = utcnow_naive()
    session.add(tenant)
    await _record_platform_audit(
        session,
        current_user,
        action="tenant.updated",
        target_type="tenant",
        target_id=str(tenant.id),
        tenant_id=tenant.id,
        changes=changes,
    )
    await session.commit()
    await session.refresh(tenant)
    clear_tenant_host_cache()

    return TenantSummary(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
    )


# ═══════════════════════════════════════════
#  User Management
# ═══════════════════════════════════════════


@router.post("/platform-users", response_model=AdminUserInfo, status_code=201)
async def create_platform_operator(
    body: PlatformOperatorCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    """Create an internal-only platform operator with no tenant membership."""
    email = str(body.email).lower()
    existing = (await session.exec(select(User).where(User.email == email))).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    operator = User(
        tenant_id=None,
        email=email,
        full_name=body.full_name.strip(),
        hashed_password=get_password_hash(body.temporary_password),
        role="admin",
        is_active=True,
        is_superuser=True,
    )
    session.add(operator)
    await session.flush()
    await _record_platform_audit(
        session,
        current_user,
        action="platform_operator.created",
        target_type="platform_user",
        target_id=str(operator.id),
        tenant_id=None,
        changes={"email": operator.email, "full_name": operator.full_name, "is_active": True},
    )
    await session.commit()
    await session.refresh(operator)
    return AdminUserInfo(
        id=str(operator.id), email=operator.email, full_name=operator.full_name,
        role=operator.role, is_active=operator.is_active, is_superuser=operator.is_superuser,
        tenant_id=None, tenant_name=None, created_at=operator.created_at,
        last_login_at=operator.last_login_at,
    )


@router.patch("/platform-users/{user_id}", response_model=AdminUserInfo)
async def update_platform_operator(
    user_id: UUID,
    body: PlatformOperatorUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    """Activate or suspend a platform operator without touching tenant users."""
    operator = await session.get(User, user_id)
    if not operator or not operator.is_superuser or operator.tenant_id is not None:
        raise HTTPException(status_code=404, detail="Platform operator not found")
    if operator.id == current_user.id and not body.is_active:
        raise HTTPException(status_code=422, detail="You cannot suspend your own platform account")
    if not body.is_active and operator.is_active:
        active_count = (await session.exec(
            text("SELECT COUNT(*) AS cnt FROM users WHERE is_superuser = TRUE AND is_active = TRUE AND tenant_id IS NULL")
        )).mappings().first()
        if int((active_count or {}).get("cnt", 0)) <= 1:
            raise HTTPException(status_code=422, detail="At least one active platform operator is required")
    if operator.is_active == body.is_active:
        raise HTTPException(status_code=422, detail="No platform operator changes supplied")
    before_active = operator.is_active
    operator.is_active = body.is_active
    session.add(operator)
    await _record_platform_audit(
        session,
        current_user,
        action="platform_operator.updated",
        target_type="platform_user",
        target_id=str(operator.id),
        tenant_id=None,
        changes={"is_active": {"from": before_active, "to": operator.is_active}},
    )
    await session.commit()
    await session.refresh(operator)
    return AdminUserInfo(
        id=str(operator.id), email=operator.email, full_name=operator.full_name,
        role=operator.role, is_active=operator.is_active, is_superuser=operator.is_superuser,
        tenant_id=None, tenant_name=None, created_at=operator.created_at,
        last_login_at=operator.last_login_at,
    )


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

    rows = await session.exec(
        text(f"""
            SELECT u.id, u.email, u.full_name, u.role, u.is_active, u.is_superuser,
                   u.tenant_id, u.created_at, u.last_login_at, t.name AS tenant_name
            FROM users u
            LEFT JOIN tenants t ON t.id = u.tenant_id
            {where_sql}
            ORDER BY u.created_at DESC
            OFFSET :skip LIMIT :limit
        """),
        params=params,
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
        await session.exec(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return SystemHealth(
        status="healthy" if db_status == "ok" else "degraded",
        database=db_status,
        uptime_seconds=round(time.time() - _START_TIME, 1),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        external_test=external_test_readiness(),
    )


def _incident_payload(
    incident: OperationalIncident,
    events: list[OperationalIncidentEvent] | None = None,
) -> dict[str, Any]:
    return {
        "id": str(incident.id),
        "incident_key": incident.incident_key,
        "incident_type": incident.incident_type,
        "severity": incident.severity,
        "status": incident.status,
        "title": incident.title,
        "summary": incident.summary,
        "metrics": incident.metrics,
        "occurrence_count": incident.occurrence_count,
        "first_seen_at": incident.first_seen_at,
        "last_seen_at": incident.last_seen_at,
        "acknowledged_at": incident.acknowledged_at,
        "resolved_at": incident.resolved_at,
        "last_notified_at": incident.last_notified_at,
        "notification_error": incident.notification_error,
        "events": [
            {
                "id": str(event.id),
                "action": event.action,
                "actor_user_id": str(event.actor_user_id)
                if event.actor_user_id
                else None,
                "note": event.note,
                "detail": event.detail,
                "created_at": event.created_at,
            }
            for event in (events or [])
        ],
    }


@router.get("/operations/slo")
async def service_level_status(
    history_limit: int = Query(default=24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> dict[str, Any]:
    """Current internal SLO evaluation plus durable sampling history."""
    current = await evaluate_service_levels(session)
    rows = (
        await session.exec(
            select(ServiceLevelSnapshot)
            .order_by(ServiceLevelSnapshot.sampled_at.desc())
            .limit(history_limit)
        )
    ).all()
    return {
        "current": current,
        "history": [
            {
                "id": str(row.id),
                "status": row.status,
                "metrics": row.metrics,
                "sampled_at": row.sampled_at,
            }
            for row in rows
        ],
        "scope": "application_and_database_internal",
        "external_uptime_claimed": False,
    }


@router.post("/operations/slo/sample")
async def sample_service_levels(
    session: AsyncSession = Depends(get_session),
    actor: User = Depends(require_superuser),
) -> dict[str, Any]:
    """Persist a sample and reconcile incident lifecycle immediately."""
    result = await collect_observability_snapshot(session)
    await _record_platform_audit(
        session,
        actor,
        action="observability.sampled",
        target_type="service_level_snapshot",
        target_id=result["snapshot_id"],
        tenant_id=None,
        changes={"status": result["status"], "breached": result["breached"]},
    )
    await session.commit()
    return result


@router.get("/operations/incidents")
async def operational_incidents(
    status: str | None = Query(default=None, pattern=r"^(open|acknowledged|resolved)$"),
    limit: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> dict[str, Any]:
    query = select(OperationalIncident)
    if status:
        query = query.where(OperationalIncident.status == status)
    incidents = (
        await session.exec(
            query.order_by(
                OperationalIncident.resolved_at.asc().nullsfirst(),
                OperationalIncident.last_seen_at.desc(),
            ).limit(limit)
        )
    ).all()
    events_by_incident: dict[UUID, list[OperationalIncidentEvent]] = {}
    if incidents:
        ids = [incident.id for incident in incidents]
        events = (
            await session.exec(
                select(OperationalIncidentEvent)
                .where(OperationalIncidentEvent.incident_id.in_(ids))
                .order_by(OperationalIncidentEvent.created_at.desc())
            )
        ).all()
        for event in events:
            bucket = events_by_incident.setdefault(event.incident_id, [])
            if len(bucket) < 20:
                bucket.append(event)
    return {
        "items": [
            _incident_payload(incident, events_by_incident.get(incident.id, []))
            for incident in incidents
        ],
        "total": len(incidents),
    }


@router.post("/operations/incidents/{incident_id}/actions")
async def act_on_operational_incident(
    incident_id: UUID,
    payload: IncidentActionIn,
    session: AsyncSession = Depends(get_session),
    actor: User = Depends(require_superuser),
) -> dict[str, Any]:
    incident = await session.get(OperationalIncident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    try:
        await update_incident_status(
            session,
            incident=incident,
            action=payload.action,
            actor_user_id=actor.id,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await _record_platform_audit(
        session,
        actor,
        action=f"incident.{payload.action}",
        target_type="operational_incident",
        target_id=str(incident.id),
        tenant_id=None,
        changes={"status": incident.status, "note": payload.note},
    )
    await session.commit()
    await session.refresh(incident)
    return _incident_payload(incident)


@router.get("/resources/status", response_model=PlatformResourceStatus)
async def platform_resource_status(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    """Expose configuration and evidence status without exposing any credential."""
    asset_row = await session.exec(
        text("""
            SELECT COUNT(*) AS asset_count,
                   COALESCE(SUM(file_size_bytes), 0) AS asset_bytes,
                   COUNT(DISTINCT tenant_id) AS tenants_with_assets,
                   MAX(created_at) AS latest_asset_at
            FROM content_assets
        """)
    )
    assets = asset_row.mappings().first() or {}
    backup_configured = all((
        settings.BACKUP_S3_ENDPOINT_URL.strip(),
        settings.BACKUP_S3_ACCESS_KEY_ID.strip(),
        settings.BACKUP_S3_SECRET_ACCESS_KEY.strip(),
        settings.BACKUP_S3_BUCKET_NAME.strip(),
        settings.BACKUP_ENCRYPTION_KEY.strip(),
    ))
    r2_configured = all((
        settings.R2_ACCOUNT_ID.strip(),
        settings.R2_ACCESS_KEY_ID.strip(),
        settings.R2_SECRET_ACCESS_KEY.strip(),
        settings.R2_BUCKET_NAME.strip(),
        settings.R2_PUBLIC_URL.strip(),
    ))
    recovery_evidence = load_recovery_evidence() or {}
    return PlatformResourceStatus(
        external_test=external_test_readiness(),
        forms={
            "signed_challenge_required": bool(settings.is_production or settings.RFQ_BOT_CHALLENGE_REQUIRED),
            "turnstile_configured": bool(
                settings.TURNSTILE_SITE_KEY.strip()
                and settings.TURNSTILE_SECRET_KEY.strip()
                and settings.TURNSTILE_ALLOWED_HOSTNAMES.strip()
            ),
            "allowed_hostnames_configured": bool(settings.TURNSTILE_ALLOWED_HOSTNAMES.strip()),
        },
        email={
            "provider": settings.ESP_PROVIDER,
            "provider_configured": bool(settings.RESEND_API_KEY.strip()),
            "webhook_configured": bool(settings.RESEND_WEBHOOK_SECRET.strip()),
            "dry_run": bool(settings.EMAIL_DRY_RUN),
            "external_delivery_enabled": bool(settings.EMAIL_EXTERNAL_DELIVERY_ENABLED),
            "internal_allowlist_configured": bool(settings.EMAIL_INTERNAL_RECIPIENT_ALLOWLIST.strip()),
            "sales_notify_configured": bool(settings.SALES_NOTIFY_EMAIL.strip()),
        },
        storage={
            "r2_configured": r2_configured,
            "asset_count": int(assets.get("asset_count") or 0),
            "asset_bytes": int(assets.get("asset_bytes") or 0),
            "tenants_with_assets": int(assets.get("tenants_with_assets") or 0),
            "latest_asset_at": assets.get("latest_asset_at"),
        },
        backups={
            "offsite_configured": backup_configured,
            "last_backup_at": recovery_evidence.get("last_backup_at"),
            "last_restore_drill_at": recovery_evidence.get("last_restore_drill_at"),
            "evidence_status": recovery_evidence.get("evidence_status", "not_recorded"),
        },
        monitoring={
            "incident_alert_configured": bool(settings.OPS_ALERT_WEBHOOK_URL.strip()) or all((
                settings.RESEND_API_KEY.strip(),
                settings.EMAIL_INTERNAL_RECIPIENT_ALLOWLIST.strip(),
                settings.SALES_NOTIFY_EMAIL.strip(),
            )) and not settings.EMAIL_DRY_RUN,
            "external_monitor_configured": bool(settings.EXTERNAL_MONITOR_NAME.strip()),
            "external_monitor_name": settings.EXTERNAL_MONITOR_NAME.strip() or None,
        },
    )


@router.get("/usage", response_model=PlatformUsageSummary)
async def platform_usage(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    totals_row = await session.exec(
        text("""
            SELECT
                (SELECT COUNT(*) FROM products) AS products,
                (SELECT COUNT(*) FROM content_assets) AS assets,
                (SELECT COALESCE(SUM(file_size_bytes), 0) FROM content_assets) AS asset_bytes,
                (SELECT COUNT(*) FROM rfq_requests WHERE is_test_data = FALSE) AS rfqs,
                (SELECT COUNT(*) FROM visitors WHERE is_test_data = FALSE) AS visitors,
                (SELECT COUNT(*) FROM users WHERE is_active = TRUE) AS active_users
        """)
    )
    tenant_rows = await session.exec(
        text("""
            SELECT t.id, t.name, t.slug,
                   COALESCE(products.cnt, 0) AS product_count,
                   COALESCE(assets.cnt, 0) AS asset_count,
                   COALESCE(assets.bytes, 0) AS asset_bytes,
                   COALESCE(rfqs.cnt, 0) AS rfq_count,
                   COALESCE(visitors.cnt, 0) AS visitor_count
            FROM tenants t
            LEFT JOIN (SELECT tenant_id, COUNT(*) AS cnt FROM products GROUP BY tenant_id) products ON products.tenant_id = t.id
            LEFT JOIN (SELECT tenant_id, COUNT(*) AS cnt, SUM(file_size_bytes) AS bytes FROM content_assets GROUP BY tenant_id) assets ON assets.tenant_id = t.id
            LEFT JOIN (SELECT tenant_id, COUNT(*) AS cnt FROM rfq_requests WHERE is_test_data = FALSE GROUP BY tenant_id) rfqs ON rfqs.tenant_id = t.id
            LEFT JOIN (SELECT tenant_id, COUNT(*) AS cnt FROM visitors WHERE is_test_data = FALSE GROUP BY tenant_id) visitors ON visitors.tenant_id = t.id
            ORDER BY COALESCE(assets.bytes, 0) DESC, COALESCE(rfqs.cnt, 0) DESC, t.name
        """)
    )
    return PlatformUsageSummary(
        totals={key: int(value or 0) for key, value in (totals_row.mappings().first() or {}).items()},
        tenants=[
            {
                "tenant_id": str(row["id"]), "tenant_name": row["name"], "slug": row["slug"],
                "product_count": int(row["product_count"] or 0),
                "asset_count": int(row["asset_count"] or 0), "asset_bytes": int(row["asset_bytes"] or 0),
                "rfq_count": int(row["rfq_count"] or 0), "visitor_count": int(row["visitor_count"] or 0),
            }
            for row in tenant_rows.mappings().all()
        ],
    )


@router.get("/audit-log", response_model=List[PlatformAuditItem])
async def platform_audit_log(
    tenant_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=300),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    where_sql = "WHERE pal.tenant_id = :tenant_id" if tenant_id else ""
    params: dict[str, Any] = {"limit": limit}
    if tenant_id:
        params["tenant_id"] = str(tenant_id)
    rows = await session.exec(
        text(f"""
            SELECT pal.id, pal.action, pal.target_type, pal.target_id, pal.changes_json,
                   pal.created_at, u.email AS actor_email
            FROM platform_audit_logs pal
            JOIN users u ON u.id = pal.actor_user_id
            {where_sql}
            ORDER BY pal.created_at DESC LIMIT :limit
        """),
        params=params,
    )
    return [
        PlatformAuditItem(
            id=str(row["id"]), actor_email=row["actor_email"], action=row["action"],
            target_type=row["target_type"], target_id=row["target_id"],
            changes=json.loads(row["changes_json"] or "{}"), created_at=row["created_at"],
        )
        for row in rows.mappings().all()
    ]


def _privacy_operation_payload(row: PrivacyOperation) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "operation_type": row.operation_type,
        "tenant_id": str(row.tenant_id) if row.tenant_id else None,
        "subject_hash_prefix": row.subject_hash[:12] if row.subject_hash else None,
        "reason": row.reason,
        "status": row.status,
        "result": json.loads(row.result_json),
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }


def _validate_privacy_reason(reason: str, *, raw_subject: UUID | None = None) -> None:
    normalized = reason.lower()
    if "@" in reason or (raw_subject and str(raw_subject).lower() in normalized):
        raise HTTPException(
            status_code=422,
            detail="Privacy reason must use a ticket/reference and contain no email or raw subject ID",
        )


@router.get("/privacy/retention")
async def platform_privacy_retention(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    return await retention_inventory(session)


@router.get("/privacy/operations")
async def platform_privacy_operations(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    rows = list(
        (
            await session.exec(
                select(PrivacyOperation)
                .order_by(PrivacyOperation.created_at.desc())
                .limit(limit)
            )
        ).all()
    )
    return [_privacy_operation_payload(row) for row in rows]


@router.post("/privacy/retention/run")
async def platform_run_privacy_retention(
    body: RetentionRunIn,
    idempotency_key: str = Header(
        min_length=8, max_length=128, alias="Idempotency-Key"
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    if not body.confirm:
        raise HTTPException(status_code=422, detail="Explicit retention confirmation required")
    _validate_privacy_reason(body.reason)
    fingerprint = privacy_request_fingerprint(
        {"operation_type": "retention_run", "reason": body.reason}
    )
    if session.get_bind().dialect.name == "postgresql":
        await session.exec(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            params={"lock_key": f"forgebase-privacy:{idempotency_key}"},
        )
    replay = (
        await session.exec(
            select(PrivacyOperation).where(
                PrivacyOperation.idempotency_key == idempotency_key
            )
        )
    ).first()
    if replay:
        if replay.request_fingerprint != fingerprint:
            raise HTTPException(status_code=409, detail="Privacy operation key conflict")
        return {**json.loads(replay.result_json), "replayed": True}
    before = await retention_inventory(session)
    deleted = await purge_expired_analytics(session, commit=False)
    after = await retention_inventory(session)
    run = PrivacyOperation(
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        operation_type="retention_run",
        actor_user_id=current_user.id,
        reason=body.reason,
        result_json="{}",
    )
    response = {
        "operation_id": str(run.id),
        "operation_type": "retention_run",
        "before": before["expired"],
        "processed": deleted,
        "after": after["expired"],
        "replayed": False,
    }
    run.result_json = json.dumps(response, default=str)
    session.add(run)
    await _record_platform_audit(
        session,
        current_user,
        action="privacy.retention_run",
        target_type="privacy_operation",
        target_id=str(run.id),
        tenant_id=None,
        changes={"before": before["total_expired"], "after": after["total_expired"]},
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Privacy operation conflict") from exc
    return response


@router.post("/privacy/visitors/export")
async def platform_export_visitor_data(
    body: VisitorPrivacyOperationIn,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    _validate_privacy_reason(body.reason, raw_subject=body.visitor_id)
    exported = await export_anonymous_visitor(
        session, tenant_id=body.tenant_id, visitor_id=body.visitor_id
    )
    if exported is None:
        raise HTTPException(status_code=404, detail="Privacy subject not found")
    subject_hash = privacy_subject_hash(
        tenant_id=body.tenant_id, visitor_id=body.visitor_id
    )
    run = PrivacyOperation(
        idempotency_key=f"privacy-export:{uuid.uuid4()}",
        request_fingerprint=privacy_request_fingerprint(
            {
                "operation_type": "visitor_export",
                "tenant_id": body.tenant_id,
                "subject_hash": subject_hash,
            }
        ),
        operation_type="visitor_export",
        tenant_id=body.tenant_id,
        actor_user_id=current_user.id,
        subject_hash=subject_hash,
        reason=body.reason,
        result_json=json.dumps(
            {
                "category_counts": {
                    key: len(value)
                    for key, value in exported.items()
                    if isinstance(value, list)
                }
            }
        ),
    )
    session.add(run)
    await _record_platform_audit(
        session,
        current_user,
        action="privacy.visitor_exported",
        target_type="privacy_operation",
        target_id=str(run.id),
        tenant_id=body.tenant_id,
        changes={"subject_hash_prefix": subject_hash[:12]},
    )
    await session.commit()
    return {"operation_id": str(run.id), "export": exported}


@router.post("/privacy/visitors/erase")
async def platform_erase_visitor_data(
    body: VisitorPrivacyOperationIn,
    idempotency_key: str = Header(
        min_length=8, max_length=128, alias="Idempotency-Key"
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    _validate_privacy_reason(body.reason, raw_subject=body.visitor_id)
    subject_hash = privacy_subject_hash(
        tenant_id=body.tenant_id, visitor_id=body.visitor_id
    )
    fingerprint = privacy_request_fingerprint(
        {
            "operation_type": "visitor_erasure",
            "tenant_id": body.tenant_id,
            "subject_hash": subject_hash,
            "reason": body.reason,
        }
    )
    if session.get_bind().dialect.name == "postgresql":
        await session.exec(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            params={"lock_key": f"forgebase-privacy:{idempotency_key}"},
        )
    replay = (
        await session.exec(
            select(PrivacyOperation).where(
                PrivacyOperation.idempotency_key == idempotency_key
            )
        )
    ).first()
    if replay:
        if replay.request_fingerprint != fingerprint:
            raise HTTPException(status_code=409, detail="Privacy operation key conflict")
        return {**json.loads(replay.result_json), "replayed": True}
    erased = await erase_anonymous_visitor(
        session, tenant_id=body.tenant_id, visitor_id=body.visitor_id
    )
    if erased is None:
        raise HTTPException(status_code=404, detail="Privacy subject not found")
    run = PrivacyOperation(
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        operation_type="visitor_erasure",
        tenant_id=body.tenant_id,
        actor_user_id=current_user.id,
        subject_hash=subject_hash,
        reason=body.reason,
        result_json="{}",
    )
    response = {
        "operation_id": str(run.id),
        "operation_type": "visitor_erasure",
        **erased,
        "replayed": False,
    }
    run.result_json = json.dumps(response)
    session.add(run)
    await _record_platform_audit(
        session,
        current_user,
        action="privacy.visitor_erased",
        target_type="privacy_operation",
        target_id=str(run.id),
        tenant_id=body.tenant_id,
        changes={
            "subject_hash_prefix": subject_hash[:12],
            "deleted_total": sum(erased["deleted"].values()),
        },
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Privacy operation conflict") from exc
    return response

@router.get("/site-templates")
async def list_site_templates(_: User = Depends(require_superuser)) -> Any:
    return template_catalog()


@router.post("/tenant-provisioning/preflight")
async def tenant_provisioning_preflight(
    body: TenantProvisionIn,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    """Validate the complete delivery specification without mutating state."""
    return await evaluate_provisioning_preflight(
        session,
        slug=body.slug,
        owner_email=str(body.owner_email),
        template_key=body.template_key,
        site_url=body.site_url,
        primary_domain=body.primary_domain,
        default_locale=body.default_locale,
        locales=body.locales,
    )


@router.post("/tenants", status_code=201)
async def provision_tenant(
    body: TenantProvisionIn,
    idempotency_key: str = Header(
        min_length=8, max_length=128, alias="Idempotency-Key"
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    fingerprint = request_fingerprint(body.model_dump(mode="json"))
    if session.get_bind().dialect.name == "postgresql":
        await session.exec(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            params={"lock_key": f"forgebase-tenant-provision:{idempotency_key}"},
        )
    replay = (
        await session.exec(
            select(TenantProvisioningRun).where(
                TenantProvisioningRun.idempotency_key == idempotency_key
            )
        )
    ).first()
    if replay:
        if replay.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key was already used with a different delivery specification",
            )
        return JSONResponse(
            status_code=replay.status_code,
            content=json.loads(replay.response_json),
            headers={"Idempotent-Replayed": "true"},
        )

    preflight = await evaluate_provisioning_preflight(
        session,
        slug=body.slug,
        owner_email=str(body.owner_email),
        template_key=body.template_key,
        site_url=body.site_url,
        primary_domain=body.primary_domain,
        default_locale=body.default_locale,
        locales=body.locales,
    )
    if not preflight["ready"]:
        raise HTTPException(
            status_code=409,
            detail={"error": "tenant_delivery_preflight_failed", **preflight},
        )

    normalized = preflight["normalized"]

    tenant = Tenant(
        name=body.name.strip(), slug=body.slug,
    )
    session.add(tenant)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Tenant delivery conflicts with an existing slug, owner, domain, or request key",
        ) from exc
    owner = User(
        tenant_id=tenant.id, email=normalized["owner_email"], full_name=body.owner_full_name.strip(),
        hashed_password=get_password_hash(body.temporary_password), role="owner", is_active=True,
    )
    profile = SiteProfile(
        tenant_id=tenant.id, brand_name=body.brand_name.strip(), logo_mark=body.logo_mark.strip().upper(),
        contact_email=str(body.contact_email).lower(), contact_phone=body.contact_phone,
        site_url=normalized["site_url"], default_locale=body.default_locale,
        theme_key=body.theme_key, layout_key=body.layout_key,
    )
    build = SiteBuild(
        tenant_id=tenant.id, template_key=body.template_key,
        primary_domain=normalized["primary_domain"],
        locales_json=json.dumps(body.locales), cms_connected=False,
    )
    session.add(owner)
    session.add(profile)
    session.add(build)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Tenant delivery conflicts with an existing slug, owner, domain, or request key",
        ) from exc
    readiness = await evaluate_site_readiness(session, build)
    build.readiness_json = json.dumps(readiness)
    build.status = "ready" if readiness["ready"] else "blocked"
    build.last_error = None if readiness["ready"] else ", ".join(readiness["blockers"])
    response = {
        "tenant_id": str(tenant.id),
        "owner_id": str(owner.id),
        "site_build_id": str(build.id),
        "status": build.status,
        "delivery_stage": build.delivery_stage,
        "readiness": readiness,
        "next_actions": ["confirm_cms_adapter", "validate_site", "publish_site"],
    }
    run = TenantProvisioningRun(
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        actor_user_id=current_user.id,
        tenant_id=tenant.id,
        status_code=201,
        response_json=json.dumps(response),
    )
    session.add(run)
    response["provisioning_run_id"] = str(run.id)
    run.response_json = json.dumps(response)
    session.add(run)
    await _record_platform_audit(
        session,
        current_user,
        action="tenant.provisioned",
        target_type="tenant",
        target_id=str(tenant.id),
        tenant_id=tenant.id,
        changes={
            "slug": tenant.slug,
            "owner_email": owner.email,
            "template_key": build.template_key,
            "primary_domain": build.primary_domain,
            "provisioning_run_id": str(run.id),
            "readiness_blockers": readiness["blockers"],
        },
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Tenant delivery conflicts with an existing slug, owner, domain, or request key",
        ) from exc
    clear_tenant_host_cache()
    return response


@router.get("/tenants/{tenant_id}/provisioning-manifest")
async def tenant_provisioning_manifest(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    """Return the latest immutable creation manifest for delivery evidence."""
    run = (
        await session.exec(
            select(TenantProvisioningRun)
            .where(TenantProvisioningRun.tenant_id == tenant_id)
            .order_by(TenantProvisioningRun.created_at.desc())
        )
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Provisioning manifest not found")
    return {
        "run_id": str(run.id),
        "created_at": run.created_at,
        "status_code": run.status_code,
        "manifest": json.loads(run.response_json),
    }


def _site_build_payload(build: SiteBuild) -> dict[str, Any]:
    template = SITE_TEMPLATES.get(build.template_key, {})
    return {
        "id": str(build.id), "tenant_id": str(build.tenant_id), "template_key": build.template_key,
        "template": template, "status": build.status, "primary_domain": build.primary_domain,
        "locales": json.loads(build.locales_json or "[]"),
        "customization": json.loads(build.customization_json or "{}"),
        "cms_connected": build.cms_connected,
        "readiness": json.loads(build.readiness_json or "{}"), "published_at": build.published_at,
        "last_error": build.last_error,
        "delivery_stage": build.delivery_stage,
        "delivery_owner_id": str(build.delivery_owner_id) if build.delivery_owner_id else None,
        "target_launch_at": build.target_launch_at,
        "handoff_at": build.handoff_at,
        "acceptance_status": build.acceptance_status,
        "internal_note": build.internal_note,
    }


@router.get("/tenants/{tenant_id}/audit-log", response_model=List[PlatformAuditItem])
async def tenant_audit_log(
    tenant_id: UUID,
    limit: int = Query(30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    if not await session.get(Tenant, tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    rows = await session.exec(
        text("""
            SELECT pal.id, pal.action, pal.target_type, pal.target_id,
                   pal.changes_json, pal.created_at, u.email AS actor_email
            FROM platform_audit_logs pal
            JOIN users u ON u.id = pal.actor_user_id
            WHERE pal.tenant_id = :tenant_id
            ORDER BY pal.created_at DESC
            LIMIT :limit
        """),
        params={"tenant_id": str(tenant_id), "limit": limit},
    )
    return [
        PlatformAuditItem(
            id=str(r["id"]),
            actor_email=r["actor_email"],
            action=r["action"],
            target_type=r["target_type"],
            target_id=r["target_id"],
            changes=json.loads(r["changes_json"] or "{}"),
            created_at=r["created_at"],
        )
        for r in rows.mappings().all()
    ]


@router.post("/tenants/{tenant_id}/site-build", status_code=201)
async def create_site_build(
    tenant_id: UUID,
    body: SiteBuildCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    existing = (await session.exec(select(SiteBuild).where(SiteBuild.tenant_id == tenant_id))).first()
    if existing:
        raise HTTPException(status_code=409, detail="Site build already exists")
    normalized_domain = (body.primary_domain or "").strip().lower() or None
    if normalized_domain:
        duplicate = (
            await session.exec(select(SiteBuild).where(SiteBuild.primary_domain == normalized_domain))
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Primary domain is already assigned")
    build = SiteBuild(
        tenant_id=tenant_id,
        template_key=body.template_key,
        primary_domain=normalized_domain,
        locales_json=json.dumps(body.locales),
        cms_connected=False,
        delivery_stage=body.delivery_stage,
        target_launch_at=_naive_utc(body.target_launch_at),
    )
    session.add(build)
    profile = (
        await session.exec(select(SiteProfile).where(SiteProfile.tenant_id == tenant_id))
    ).first()
    if profile is None:
        site_url = f"https://{normalized_domain}" if normalized_domain else "https://example.com"
        contact_domain = normalized_domain or "example.com"
        logo_mark = "".join(part[0] for part in tenant.name.split() if part)[:3].upper() or "FB"
        session.add(
            SiteProfile(
                tenant_id=tenant_id,
                brand_name=tenant.name,
                logo_mark=logo_mark,
                contact_email=f"sales@{contact_domain}",
                site_url=site_url,
                default_locale=body.locales[0] if body.locales else "en",
            )
        )
    await session.flush()
    await _record_platform_audit(
        session,
        current_user,
        action="site_build.created",
        target_type="site_build",
        target_id=str(build.id),
        tenant_id=tenant_id,
        changes={
            "template_key": build.template_key,
            "primary_domain": build.primary_domain,
            "locales": body.locales,
            "delivery_stage": build.delivery_stage,
            "target_launch_at": build.target_launch_at,
        },
    )
    await session.commit()
    await session.refresh(build)
    return _site_build_payload(build)


@router.get("/tenants/{tenant_id}/site-build")
async def get_site_build(tenant_id: UUID, session: AsyncSession = Depends(get_session), _: User = Depends(require_superuser)) -> Any:
    build = (await session.exec(select(SiteBuild).where(SiteBuild.tenant_id == tenant_id))).first()
    if not build:
        raise HTTPException(status_code=404, detail="Site build not found")
    return _site_build_payload(build)


_SITE_PROFILE_JSON_FIELDS = {
    "header_nav_json",
    "header_actions_json",
    "footer_sections_json",
    "footer_badges_json",
    "social_links_json",
    "asset_manifest_json",
    "site_copy_json",
}


@router.get("/tenants/{tenant_id}/site-profile", response_model=SiteProfileRead)
async def get_tenant_site_profile(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
) -> Any:
    if not await session.get(Tenant, tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    profile = (await session.exec(select(SiteProfile).where(SiteProfile.tenant_id == tenant_id))).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Site profile not found")
    return profile


@router.put("/tenants/{tenant_id}/site-profile", response_model=SiteProfileRead)
async def update_tenant_site_profile(
    tenant_id: UUID,
    body: SiteProfileUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    if not await session.get(Tenant, tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    profile = (await session.exec(select(SiteProfile).where(SiteProfile.tenant_id == tenant_id))).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Site profile not found")

    updates = body.model_dump(exclude_unset=True)
    for field in _SITE_PROFILE_JSON_FIELDS:
        value = updates.get(field)
        if value:
            try:
                json.loads(value)
            except (TypeError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=422, detail=f"{field} must contain valid JSON") from exc

    changes: dict[str, dict[str, Any]] = {}
    for field, value in updates.items():
        previous = getattr(profile, field)
        if previous != value:
            changes[field] = {"from": previous, "to": value}
            setattr(profile, field, value)
    if not changes:
        raise HTTPException(status_code=422, detail="No site profile changes supplied")

    profile.updated_at = utcnow_naive()
    session.add(profile)
    await _record_platform_audit(
        session,
        current_user,
        action="site_profile.updated",
        target_type="site_profile",
        target_id=str(profile.id),
        tenant_id=tenant_id,
        changes=changes,
    )
    await session.commit()
    await session.refresh(profile)
    clear_tenant_host_cache()
    return profile


@router.put("/tenants/{tenant_id}/site-build")
async def update_site_build(
    tenant_id: UUID,
    body: SiteBuildUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    build = (await session.exec(select(SiteBuild).where(SiteBuild.tenant_id == tenant_id))).first()
    if not build:
        raise HTTPException(status_code=404, detail="Site build not found")
    before = {
        "template_key": build.template_key,
        "primary_domain": build.primary_domain,
        "locales": json.loads(build.locales_json or "[]"),
        "customization": json.loads(build.customization_json or "{}"),
        "cms_connected": build.cms_connected,
        "delivery_stage": build.delivery_stage,
        "delivery_owner_id": str(build.delivery_owner_id) if build.delivery_owner_id else None,
        "target_launch_at": build.target_launch_at,
        "handoff_at": build.handoff_at,
        "acceptance_status": build.acceptance_status,
        "internal_note": build.internal_note,
    }
    technical_settings_changed = False
    if body.template_key is not None and body.template_key != build.template_key:
        build.template_key = body.template_key
        # Changing templates invalidates any prior adapter confirmation.
        # Re-saving the same template must not silently disconnect CMS.
        build.cms_connected = False
        technical_settings_changed = True
    if body.primary_domain is not None:
        normalized_domain = body.primary_domain.strip().lower() or None
        if normalized_domain:
            duplicate = (
                await session.exec(
                    select(SiteBuild).where(
                        SiteBuild.primary_domain == normalized_domain,
                        SiteBuild.id != build.id,
                    )
                )
            ).first()
            if duplicate:
                raise HTTPException(status_code=409, detail="Primary domain is already assigned")
        build.primary_domain = normalized_domain
        technical_settings_changed = technical_settings_changed or before["primary_domain"] != build.primary_domain
    if body.locales is not None:
        if not body.locales or any(locale not in PUBLIC_SITE_LOCALES for locale in body.locales):
            raise HTTPException(status_code=422, detail="Unsupported locales")
        build.locales_json = json.dumps(list(dict.fromkeys(body.locales)))
        technical_settings_changed = technical_settings_changed or before["locales"] != json.loads(build.locales_json)
    if body.customization is not None:
        build.customization_json = json.dumps(body.customization)
        technical_settings_changed = technical_settings_changed or before["customization"] != body.customization
    if body.cms_connected is not None:
        if body.cms_connected and not SITE_TEMPLATES[build.template_key]["cms_connected"]:
            raise HTTPException(status_code=422, detail="This static demo has no CMS adapter")
        build.cms_connected = body.cms_connected
        technical_settings_changed = technical_settings_changed or before["cms_connected"] != build.cms_connected
    if "delivery_stage" in body.model_fields_set:
        build.delivery_stage = body.delivery_stage or "intake"
    if "delivery_owner_id" in body.model_fields_set:
        if body.delivery_owner_id is not None:
            owner = await session.get(User, body.delivery_owner_id)
            if not owner or not owner.is_superuser or not owner.is_active:
                raise HTTPException(status_code=422, detail="Delivery owner must be an active platform operator")
        build.delivery_owner_id = body.delivery_owner_id
    if "target_launch_at" in body.model_fields_set:
        build.target_launch_at = _naive_utc(body.target_launch_at)
    if "handoff_at" in body.model_fields_set:
        build.handoff_at = _naive_utc(body.handoff_at)
    if "acceptance_status" in body.model_fields_set:
        build.acceptance_status = body.acceptance_status or "pending"
    if "internal_note" in body.model_fields_set:
        build.internal_note = body.internal_note.strip() if body.internal_note else None
    after = {
        "template_key": build.template_key,
        "primary_domain": build.primary_domain,
        "locales": json.loads(build.locales_json or "[]"),
        "customization": json.loads(build.customization_json or "{}"),
        "cms_connected": build.cms_connected,
        "delivery_stage": build.delivery_stage,
        "delivery_owner_id": str(build.delivery_owner_id) if build.delivery_owner_id else None,
        "target_launch_at": build.target_launch_at,
        "handoff_at": build.handoff_at,
        "acceptance_status": build.acceptance_status,
        "internal_note": build.internal_note,
    }
    changes = {
        key: {"from": before[key], "to": value}
        for key, value in after.items()
        if before[key] != value
    }
    if not changes:
        raise HTTPException(status_code=422, detail="No site build changes supplied")
    if technical_settings_changed:
        build.status = "draft"
        build.readiness_json = "{}"
        build.last_error = None
    delivery_readiness = evaluate_delivery_stage(build)
    if not delivery_readiness["ready"]:
        raise HTTPException(
            status_code=409,
            detail={"error": "delivery_stage_not_ready", **delivery_readiness},
        )
    build.updated_at = utcnow_naive()
    session.add(build)
    await _record_platform_audit(
        session,
        current_user,
        action="site_build.updated",
        target_type="site_build",
        target_id=str(build.id),
        tenant_id=tenant_id,
        changes=changes,
    )
    await session.commit()
    await session.refresh(build)
    return _site_build_payload(build)


@router.post("/tenants/{tenant_id}/site-build/validate")
async def validate_site_build(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    build = (await session.exec(select(SiteBuild).where(SiteBuild.tenant_id == tenant_id))).first()
    if not build:
        raise HTTPException(status_code=404, detail="Site build not found")
    readiness = await validate_and_store_readiness(session, build)
    await _record_platform_audit(
        session,
        current_user,
        action="site_build.validated",
        target_type="site_build",
        target_id=str(build.id),
        tenant_id=tenant_id,
        changes={"ready": readiness["ready"], "blockers": readiness["blockers"]},
    )
    await session.commit()
    return _site_build_payload(build)


@router.post("/tenants/{tenant_id}/site-build/publish")
async def publish_site_build(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
) -> Any:
    build = (await session.exec(select(SiteBuild).where(SiteBuild.tenant_id == tenant_id))).first()
    if not build:
        raise HTTPException(status_code=404, detail="Site build not found")
    readiness = await validate_and_store_readiness(session, build)
    if not readiness["ready"]:
        await _record_platform_audit(
            session,
            current_user,
            action="site_build.publish_blocked",
            target_type="site_build",
            target_id=str(build.id),
            tenant_id=tenant_id,
            changes={"ready": False, "blockers": readiness["blockers"]},
        )
        await session.commit()
        raise HTTPException(status_code=409, detail={"error": "site_not_ready", **readiness})
    build.status = "published"
    build.published_at = utcnow_naive()
    build.updated_at = utcnow_naive()
    session.add(build)
    await _record_platform_audit(
        session,
        current_user,
        action="site_build.published",
        target_type="site_build",
        target_id=str(build.id),
        tenant_id=tenant_id,
        changes={"status": {"from": "ready", "to": "published"}},
    )
    await session.commit()
    await session.refresh(build)
    return _site_build_payload(build)
