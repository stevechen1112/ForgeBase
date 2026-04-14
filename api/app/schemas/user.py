import uuid
from datetime import datetime
from typing import Optional
from pydantic import EmailStr
from sqlmodel import SQLModel
from app.models.user import UserRole


class UserCreate(SQLModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.marketing_manager


class UserRead(SQLModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    is_superuser: bool = False
    tenant_id: Optional[uuid.UUID] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class TokenResponse(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class LoginRequest(SQLModel):
    email: EmailStr
    password: str
