from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db.session import get_session
from app.core.security import decode_token
from app.models.user import User
from app.models.tenant import Tenant

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
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


async def require_content_editor(current_user: User = Depends(get_current_user)) -> User:
    """Allow admin, owner, and marketing_manager to create/edit content."""
    if current_user.role not in ("admin", "owner", "marketing_manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Content editor access required",
        )
    return current_user


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
            return current_user

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
            return  # legacy user without tenant — skip check

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
    x_tenant_id: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
) -> Optional[UUID]:
    """Resolve tenant from X-Tenant-ID header (public endpoints).

    Returns tenant UUID if header is present and valid, else None.
    """
    if not x_tenant_id:
        return None
    try:
        tid = UUID(x_tenant_id)
    except ValueError:
        # Try slug lookup
        from app.models.tenant import Tenant
        result = await session.exec(select(Tenant).where(Tenant.slug == x_tenant_id))
        tenant = result.first()
        if not tenant:
            raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID")
        return tenant.id
    return tid
