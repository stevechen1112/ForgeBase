"""
內容預覽 Token 系統  (1a.6.4)

Two endpoints:
  POST /content/pages/{page_id}/preview-token   → generates a short-lived (1h) signed JWT
  GET  /content/preview/{token}                 → validates token, returns page data (any status)

The preview JWT uses type="preview" plus page_id and tenant_id claims, so it
cannot be used as a user access token or replayed against another tenant page.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_admin
from app.core.config import settings
from app.db.session import get_session
from app.models.page import Page
from app.models.user import User

router = APIRouter(tags=["Preview"])

ALGORITHM = "HS256"
PREVIEW_TOKEN_TTL_HOURS = 1


# ── Schemas ───────────────────────────────────────────────────────────────────

class PreviewTokenOut(BaseModel):
    token: str
    expires_in_seconds: int
    preview_url: str


class PagePreviewOut(BaseModel):
    id: uuid.UUID
    slug: str
    page_type: str
    title: str
    subtitle: str | None
    body: str | None
    hero_image_url: str | None
    seo_title: str | None
    seo_description: str | None
    og_image_url: str | None
    structured_data: str | None
    locale: str
    status: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_preview_token(page_id: str, tenant_id: str | None) -> str:
    """Return a 1-hour signed JWT for previewing a specific page."""
    expire = datetime.now(timezone.utc) + timedelta(hours=PREVIEW_TOKEN_TTL_HOURS)
    payload = {
        "type": "preview",
        "page_id": page_id,
        "tenant_id": tenant_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _decode_preview_token(token: str) -> tuple[str, str | None]:
    """Return the bound page and tenant IDs if the token is valid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired preview token") from exc

    if payload.get("type") != "preview":
        raise HTTPException(status_code=401, detail="Not a preview token")

    page_id = payload.get("page_id")
    if not page_id:
        raise HTTPException(status_code=401, detail="Malformed preview token")

    return page_id, payload.get("tenant_id")


def _ensure_page_admin_access(page: Page, user: User) -> None:
    """Only platform staff or an administrator of the owning tenant may preview."""
    if user.is_superuser:
        return
    if page.tenant_id is None or user.tenant_id is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Page not found")


# ═══════════════════════════════════════════════════════════════════════════════
# POST /content/pages/{page_id}/preview-token
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/pages/{page_id}/preview-token",
    response_model=PreviewTokenOut,
    summary="Generate a short-lived preview token for a page (admin only)",
)
async def create_preview_token(
    page_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    page = await session.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    _ensure_page_admin_access(page, current_user)

    token = _create_preview_token(
        str(page_id),
        str(page.tenant_id) if page.tenant_id is not None else None,
    )
    web_url = settings.FRONTEND_URL

    return PreviewTokenOut(
        token=token,
        expires_in_seconds=PREVIEW_TOKEN_TTL_HOURS * 3600,
        preview_url=f"{web_url}/preview/{token}",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GET /content/preview/{token}
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/preview/{token}",
    response_model=PagePreviewOut,
    summary="Fetch page data using a preview token (no auth required)",
)
async def get_preview_page(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    page_id_str, token_tenant_id = _decode_preview_token(token)

    try:
        resolved_id = uuid.UUID(page_id_str)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Malformed page_id in token") from exc

    page = await session.get(Page, resolved_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    page_tenant_id = str(page.tenant_id) if page.tenant_id is not None else None
    if page_tenant_id != token_tenant_id:
        raise HTTPException(status_code=401, detail="Preview token tenant mismatch")

    return PagePreviewOut(
        id=page.id,
        slug=page.slug,
        page_type=page.page_type,
        title=page.title,
        subtitle=page.subtitle,
        body=page.body,
        hero_image_url=page.hero_image_url,
        seo_title=page.seo_title,
        seo_description=page.seo_description,
        og_image_url=page.og_image_url,
        structured_data=page.structured_data,
        locale=page.locale,
        status=page.status,
    )
