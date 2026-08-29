from typing import Optional
from urllib.parse import urlparse
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_session
from app.models.tenant import Tenant
from app.models.tenant_domain import TenantDomain
from app.models.user import User
from app.services.tenant_domains import normalize_hostname, valid_hostname

bearer_scheme = HTTPBearer(auto_error=False)


def _parse_service_account_tokens() -> dict[str, str]:
    """Parse SERVICE_ACCOUNT_TOKENS config into {token: user_id} mapping."""
    raw = settings.SERVICE_ACCOUNT_TOKENS.strip()
    if not raw:
        return {}
    mapping: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        token, user_id = pair.split(":", 1)
        mapping[token.strip()] = user_id.strip()
    return mapping


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    # --- Try service account token (X-API-Key header) first ---
    api_key = request.headers.get("X-API-Key")
    if api_key:
        sa_map = _parse_service_account_tokens()
        user_id = sa_map.get(api_key)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        result = await session.exec(select(User).where(User.id == user_id))
        user = result.first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Service account user not found or inactive",
            )
        if user.tenant_id and not getattr(user, "is_superuser", False):
            tenant = await session.get(Tenant, user.tenant_id)
            if not tenant or not tenant.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is inactive")
        return user

    # --- Fallback to JWT bearer token ---
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    result = await session.exec(select(User).where(User.id == user_id))
    user = result.first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if user.tenant_id and not getattr(user, "is_superuser", False):
        tenant = await session.get(Tenant, user.tenant_id)
        if not tenant or not tenant.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is inactive")

    return user


async def optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """get_current_user 的非強制版：無憑證或憑證無效時回傳 None 而非 401。

    用於公開查詢端點——帶有效憑證（如 CF service account）時以其
    tenant 範圍查詢，未帶憑證時維持原有 host/header 解析行為。
    """
    try:
        return await get_current_user(request, credentials, session)
    except HTTPException:
        return None


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser and current_user.role not in ("admin", "owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_owner(current_user: User = Depends(get_current_user)) -> User:
    """Only the tenant owner can perform this action."""
    if current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required",
        )
    return current_user


async def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Platform-level super admin access only."""
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return current_user


async def require_content_editor(current_user: User = Depends(get_current_user)) -> User:
    """Allow admin, owner, and marketing_manager to create/edit content."""
    if current_user.role not in ("admin", "owner", "marketing_manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Content editor access required",
        )
    return current_user


async def require_rfq_operator(current_user: User = Depends(get_current_user)) -> User:
    """Allow the people who actually operate sales cases.

    Marketing users retain read-only visibility for attribution, while sales
    users can update RFQs assigned to them. Endpoint-level ownership checks
    still enforce the latter boundary.
    """
    if current_user.role not in ("admin", "owner", "sales"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RFQ operator access required",
        )
    return current_user


async def require_rfq_manager(current_user: User = Depends(get_current_user)) -> User:
    """Restrict assignment, merging and exports to tenant managers."""
    if current_user.role not in ("admin", "owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RFQ manager access required",
        )
    return current_user


def require_user_tenant_id(current_user: User) -> UUID:
    """Return the authenticated tenant boundary or reject tenantless access.

    Platform superusers must assume a tenant through a tenant-owned user before
    using tenant data APIs. This prevents a missing tenant from silently
    becoming a global, cross-tenant scope.
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context required",
        )
    return current_user.tenant_id


class RequireFeature:
    """Block access when a tenant capability is not operationally enabled."""

    def __init__(self, feature: str):
        self.feature = feature

    async def __call__(
        self,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant context required",
            )

        tenant = await session.get(Tenant, current_user.tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )

        from app.services.capability_access import tenant_has_feature

        if not tenant_has_feature(tenant, self.feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_not_available",
                    "feature": self.feature,
                    "message": f"Feature '{self.feature}' is not enabled for this tenant.",
                },
            )

        return current_user


async def resolve_tenant_id(
    request: Request,
    x_tenant_id: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
) -> Optional[UUID]:
    """Resolve a public tenant from an exact, active hostname.

    X-Tenant-ID remains a temporary build-time compatibility path only when
    the request host is not assigned. A recognized host always wins and any
    conflicting header fails closed. Arbitrary first-label/slug inference is
    intentionally forbidden.
    """
    async def _resolve_identifier(identifier: str) -> Optional[UUID]:
        try:
            tenant_id = UUID(identifier)
            tenant = await session.get(Tenant, tenant_id)
            return tenant.id if tenant and tenant.is_active else None
        except ValueError:
            result = await session.exec(select(Tenant).where(Tenant.slug == identifier, Tenant.is_active.is_(True)))
            tenant = result.first()
            if tenant:
                return tenant.id
            return None

    def _extract_host(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            parsed = urlparse(value if "://" in value else f"https://{value}")
        except ValueError:
            return None
        normalized = normalize_hostname(parsed.hostname)
        return normalized if valid_hostname(normalized) else None

    request_host = _extract_host(request.headers.get("host"))

    # Check process-level TTL cache first
    import time as _time
    now = _time.monotonic()
    host_tenant_id: Optional[UUID] = None
    host_cache_hit = False
    if request_host:
        cached = _TENANT_HOST_CACHE.get(request_host)
        if cached is not None:
            tenant_id, cached_at = cached
            if now - cached_at < _TENANT_HOST_CACHE_TTL:
                host_tenant_id = tenant_id
                host_cache_hit = True

    if request_host and not host_cache_hit:
        host_tenant_id = (
            await session.exec(
                select(TenantDomain.tenant_id)
                .join(Tenant, Tenant.id == TenantDomain.tenant_id)
                .where(
                    TenantDomain.hostname == request_host,
                    TenantDomain.status == "active",
                    Tenant.is_active.is_(True),
                )
            )
        ).first()

        _cache_tenant_host(request_host, host_tenant_id, now)

    header_tenant_id: Optional[UUID] = None
    if x_tenant_id:
        if not host_tenant_id and not settings.PUBLIC_TENANT_HEADER_COMPATIBILITY_ENABLED:
            raise HTTPException(status_code=400, detail="X-Tenant-ID compatibility is disabled")
        header_tenant_id = await _resolve_identifier(x_tenant_id.strip())
        if not header_tenant_id:
            raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID")
        if host_tenant_id and header_tenant_id != host_tenant_id:
            raise HTTPException(status_code=400, detail="Tenant host/header mismatch")

    return host_tenant_id or header_tenant_id


# ── Process-level TTL cache for host→tenant_id ──────────────────────────────
_TENANT_HOST_CACHE: dict[str, tuple[Optional[UUID], float]] = {}
_TENANT_HOST_CACHE_TTL = 120.0  # seconds
_TENANT_HOST_CACHE_MAX = 4096


def _cache_tenant_host(host: str, tenant_id: Optional[UUID], cached_at: float) -> None:
    """Bound attacker-controlled negative host cache entries."""
    if len(_TENANT_HOST_CACHE) >= _TENANT_HOST_CACHE_MAX:
        expired_before = cached_at - _TENANT_HOST_CACHE_TTL
        for key, (_, item_cached_at) in list(_TENANT_HOST_CACHE.items()):
            if item_cached_at < expired_before:
                _TENANT_HOST_CACHE.pop(key, None)
        while len(_TENANT_HOST_CACHE) >= _TENANT_HOST_CACHE_MAX:
            _TENANT_HOST_CACHE.pop(next(iter(_TENANT_HOST_CACHE)))
    _TENANT_HOST_CACHE[host] = (tenant_id, cached_at)


def clear_tenant_host_cache() -> None:
    """Invalidate host resolution after tenant, domain, or profile changes."""
    _TENANT_HOST_CACHE.clear()
