from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from slugify import slugify
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_session
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Registration ─────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str
    registration_key: str = ""


class RegisterResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead
    tenant_id: str
    tenant_slug: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)):
    """
    Register a new tenant + owner account.
    Creates: 1 Tenant row + 1 User row (role=owner).
    Requires REGISTRATION_KEY to be set in environment.
    """
    from app.core.config import settings
    # Require REGISTRATION_KEY in production; in dev, allow open registration only when key is not set
    if settings.REGISTRATION_KEY:
        if payload.registration_key != settings.REGISTRATION_KEY:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid registration key")
    elif settings.is_production:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Registration is closed")

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
    tenant = Tenant(
        name=payload.company_name,
        slug=slug,
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
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_session)):
    token_payload = decode_token(payload.refresh_token)

    if not token_payload or token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    result = await session.exec(select(User).where(User.id == token_payload["sub"]))
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

from app.api.v1.deps import require_admin


class InviteRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "marketing_manager"  # marketing_manager | sales | admin


class TeamMemberUpdateRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None


@router.get("/team", response_model=list[UserRead])
async def list_team(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
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

    return [UserRead.model_validate(u) for u in users]


@router.post("/team/invite", response_model=UserRead, status_code=status.HTTP_201_CREATED)
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

    # Only owner can invite admin-role users
    if payload.role == "admin" and current_user.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the owner can invite admin users")

    # Password validation
    if len(payload.password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters")

    # Check email uniqueness
    existing = await session.exec(select(User).where(User.email == payload.email))
    if existing.first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")

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

    return UserRead.model_validate(user)


@router.patch("/team/{user_id}", response_model=UserRead)
async def update_team_member(
    user_id: str,
    payload: TeamMemberUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
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
    if target.id == current_user.id and payload.is_active is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account")

    if target.role == "owner":
        if current_user.role != "owner":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only owner can manage owner account")
        if payload.role and payload.role != "owner":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot change owner role")
        if payload.is_active is False:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate owner account")

    if payload.role is not None:
        allowed_roles = {"admin", "marketing_manager", "sales"}
        if payload.role not in allowed_roles:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Role must be one of: {allowed_roles}")
        # Only owner can promote to admin or manage admin users
        if (payload.role == "admin" or target.role == "admin") and current_user.role != "owner":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the owner can manage admin roles")
        target.role = payload.role

    if payload.is_active is not None:
        # Only owner can deactivate admin users
        if target.role == "admin" and payload.is_active is False and current_user.role != "owner":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the owner can deactivate admin users")
        target.is_active = payload.is_active

    target.updated_at = utcnow_naive()
    session.add(target)
    await session.commit()
    await session.refresh(target)

    return UserRead.model_validate(target)
