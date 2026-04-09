from datetime import datetime
from app.core.datetime import utcnow_naive
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db.session import get_session
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.user import LoginRequest, TokenResponse, UserRead
from app.services.subscription import get_plan
from slugify import slugify

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Registration ─────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str
    plan: str = "starter"  # "starter" | "professional"


class RegisterResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead
    tenant_id: str
    tenant_slug: str


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)):
    """
    Register a new tenant + owner account.
    Creates: 1 Tenant row + 1 User row (role=owner).
    """
    # Validate plan
    if payload.plan not in ("starter", "professional"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Plan must be 'starter' or 'professional'")

    # Validate password strength
    if len(payload.password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters")

    # Check email uniqueness
    existing = await session.exec(select(User).where(User.email == payload.email))
    if existing.first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")

    # Generate unique slug from company name
    base_slug = slugify(payload.company_name, max_length=80)
    slug = base_slug
    counter = 1
    while True:
        slug_check = await session.exec(select(Tenant).where(Tenant.slug == slug))
        if not slug_check.first():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Create tenant
    plan_config = get_plan(payload.plan)
    tenant = Tenant(
        name=payload.company_name,
        slug=slug,
        plan=payload.plan,
        max_products=plan_config["max_products"],
        max_admins=plan_config["max_admins"],
    )
    session.add(tenant)
    await session.flush()  # Get tenant.id

    # Create owner user
    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role="owner",
        tenant_id=tenant.id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await session.refresh(tenant)

    # Issue tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return RegisterResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserRead.model_validate(user),
        tenant_id=str(tenant.id),
        tenant_slug=tenant.slug,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(User).where(User.email == payload.email))
    user = result.first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    user.last_login_at = utcnow_naive()
    session.add(user)
    await session.commit()

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserRead.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_token: str, session: AsyncSession = Depends(get_session)):
    payload = decode_token(refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    result = await session.exec(select(User).where(User.id == payload["sub"]))
    user = result.first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access = create_access_token(str(user.id))
    new_refresh = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=UserRead.model_validate(user),
    )


# ── Team member management ───────────────────────────────────────────────────

from app.api.v1.deps import get_current_user, require_admin


class InviteRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "marketing_manager"  # marketing_manager | sales | admin


class TeamMemberOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
    last_login_at: str | None


@router.get("/team")
async def list_team(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all team members in the current tenant."""
    if not current_user.tenant_id:
        return []

    result = await session.exec(
        select(User)
        .where(User.tenant_id == current_user.tenant_id)
        .order_by(User.created_at)
    )
    users = result.all()

    return [
        TeamMemberOut(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at.isoformat() if u.created_at else "",
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
        )
        for u in users
    ]


@router.post("/team/invite", status_code=status.HTTP_201_CREATED)
async def invite_team_member(
    payload: InviteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Invite a new team member to the current tenant. Admin/owner only."""
    if not current_user.tenant_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User has no tenant")

    # Validate role
    allowed_roles = {"admin", "marketing_manager", "sales"}
    if payload.role not in allowed_roles:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Role must be one of: {allowed_roles}")

    # Password validation
    if len(payload.password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters")

    # Check email uniqueness
    existing = await session.exec(select(User).where(User.email == payload.email))
    if existing.first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")

    # Check admin quota
    from app.services.subscription import check_quota
    if payload.role in ("admin", "owner"):
        quota_result = await check_quota(session, current_user.tenant_id, "admin")
        if not quota_result.get("allowed", True):
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail=quota_result.get("message", "Admin quota exceeded"),
            )

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        tenant_id=current_user.tenant_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return TeamMemberOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login_at=None,
    )


@router.patch("/team/{user_id}")
async def update_team_member(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
    role: str | None = None,
    is_active: bool | None = None,
):
    """Update a team member's role or active status. Admin/owner only."""
    if not current_user.tenant_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User has no tenant")

    import uuid as _uuid
    try:
        uid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    target = await session.get(User, uid)
    if not target or target.tenant_id != current_user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    # Cannot deactivate yourself
    if target.id == current_user.id and is_active is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account")

    # Cannot change owner role
    if target.role == "owner" and role and role != "owner":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot change owner role")

    if role is not None:
        allowed_roles = {"admin", "marketing_manager", "sales"}
        if role not in allowed_roles:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Role must be one of: {allowed_roles}")
        target.role = role

    if is_active is not None:
        target.is_active = is_active

    target.updated_at = utcnow_naive()
    session.add(target)
    await session.commit()
    await session.refresh(target)

    return TeamMemberOut(
        id=str(target.id),
        email=target.email,
        full_name=target.full_name,
        role=target.role,
        is_active=target.is_active,
        created_at=target.created_at.isoformat() if target.created_at else "",
        last_login_at=target.last_login_at.isoformat() if target.last_login_at else None,
    )
