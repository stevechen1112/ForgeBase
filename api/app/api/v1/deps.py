from typing import Optional
from uuid import UUID
from urllib.parse import urlparse

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db.session import get_session
from app.core.security import decode_token
from app.models.user import User
from app.models.tenant import Tenant
from app.core.config import settings

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
    if current_user.role not in ("admin", "owner"):
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
    """FastAPI dependency that blocks access when tenant plan lacks a feature."""

    def __init__(self, feature: str):
        self.feature = feature

    async def __call__(
        self,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not current_user.tenant_id:
            if current_user.role in ("admin", "owner"):
                return current_user
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

        from app.services.subscription import get_plan_feature

        if not get_plan_feature(tenant.plan, self.feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_not_available",
                    "feature": self.feature,
                    "message": f"Feature '{self.feature}' requires a higher plan.",
                },
            )

        return current_user


class QuotaEnforcer:
    """FastAPI dependency that checks tenant resource quota before proceeding.

    Usage::

        @router.post("/products")
        async def create(
            ...,
            _quota=Depends(QuotaEnforcer("product")),
        ):
    """

    def __init__(self, resource: str):
        self.resource = resource

    async def __call__(
        self,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user),
    ):
        if not current_user.tenant_id:
            if current_user.role in ("admin", "owner"):
                return
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant context required",
            )

        from app.services.subscription import check_quota

        result = await check_quota(session, current_user.tenant_id, self.resource)
        if not result.get("allowed", True):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "quota_exceeded",
                    "message": result["message"],
                    "resource": self.resource,
                    "current": result.get("current"),
                    "limit": result.get("limit"),
                },
            )


async def resolve_tenant_id(
    request: Request,
    x_tenant_id: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
) -> Optional[UUID]:
    """Resolve tenant from X-Tenant-ID header (public endpoints).

    Returns tenant UUID if header is present and valid, else None.
    Uses a process-level TTL cache for host→tenant_id lookups to avoid
    full-table scans on every public request.
    """
    async def _resolve_identifier(identifier: str) -> Optional[UUID]:
        try:
            return UUID(identifier)
        except ValueError:
            from app.models.tenant import Tenant

            result = await session.exec(select(Tenant).where(Tenant.slug == identifier))
            tenant = result.first()
            if tenant:
                return tenant.id
            return None

    def _extract_host(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        parsed = urlparse(value if "://" in value else f"https://{value}")
        host = (parsed.hostname or "").strip().lower()
        return host or None

    if x_tenant_id:
        resolved = await _resolve_identifier(x_tenant_id.strip())
        if not resolved:
            raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID")
        return resolved

    candidate_hosts = [
        _extract_host(request.headers.get("x-tenant-host")),
        _extract_host(request.headers.get("origin")),
        _extract_host(request.headers.get("referer")),
        _extract_host(request.headers.get("x-forwarded-host")),
        _extract_host(request.headers.get("host")),
    ]
    candidate_hosts = [host for host in candidate_hosts if host]
    if not candidate_hosts:
        return await _resolve_identifier(settings.PUBLIC_TENANT_SLUG) if settings.PUBLIC_TENANT_SLUG else None

    # Check process-level TTL cache first
    import time as _time
    now = _time.monotonic()
    for host in candidate_hosts:
        cached = _TENANT_HOST_CACHE.get(host)
        if cached is not None:
            tenant_id, cached_at = cached
            if now - cached_at < _TENANT_HOST_CACHE_TTL:
                return tenant_id

    from app.models.site_profile import SiteProfile
    from app.models.tenant import Tenant

    tenant_column = getattr(SiteProfile, "tenant_id", None)
    profiles = (
        await session.exec(
            select(SiteProfile.site_url, SiteProfile.tenant_id).where(tenant_column.is_not(None))
        )
    ).all()

    # Build a host→tenant_id map from profiles for efficient O(1) lookups
    profile_map: dict[str, UUID] = {}
    for site_url, tenant_id in profiles:
        profile_host = _extract_host(site_url)
        if profile_host and tenant_id is not None:
            profile_map[profile_host] = tenant_id

    for host in candidate_hosts:
        tid = profile_map.get(host)
        if tid:
            _TENANT_HOST_CACHE[host] = (tid, now)
            return tid

        subdomain = host.split(".", 1)[0]
        if subdomain and subdomain not in {"www", "app", "api", "localhost"}:
            tenant = (
                await session.exec(select(Tenant).where(Tenant.slug == subdomain))
            ).first()
            if tenant:
                _TENANT_HOST_CACHE[host] = (tenant.id, now)
                return tenant.id

        # Cache miss — record negative result to avoid re-querying
        _TENANT_HOST_CACHE[host] = (None, now)

    if settings.PUBLIC_TENANT_SLUG:
        return await _resolve_identifier(settings.PUBLIC_TENANT_SLUG)
    return None


# ── Process-level TTL cache for host→tenant_id ──────────────────────────────
import time as _time_mod
_TENANT_HOST_CACHE: dict[str, tuple[Optional[UUID], float]] = {}
_TENANT_HOST_CACHE_TTL = 120.0  # seconds
