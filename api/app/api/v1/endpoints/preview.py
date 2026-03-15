"""
內容預覽 Token 系統  (1a.6.4)

Two endpoints:
  POST /content/pages/{page_id}/preview-token   → generates a short-lived (1h) signed JWT
  GET  /content/preview/{token}                 → validates token, returns page data (any status)

The preview JWT uses type="preview" and page_id claim so it can't be used as a user access token.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_content_editor
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

def _create_preview_token(page_id: str) -> str:
    """Return a 1-hour signed JWT for previewing a specific page."""
    expire = datetime.now(timezone.utc) + timedelta(hours=PREVIEW_TOKEN_TTL_HOURS)
    payload = {
        "type": "preview",
        "page_id": page_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _decode_preview_token(token: str) -> str:
    """Return page_id if the token is valid, else raise 401."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired preview token") from exc

    if payload.get("type") != "preview":
        raise HTTPException(status_code=401, detail="Not a preview token")

    page_id = payload.get("page_id")
    if not page_id:
        raise HTTPException(status_code=401, detail="Malformed preview token")

    return page_id


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
    _: User = Depends(require_content_editor),
):
    page = await session.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    token = _create_preview_token(str(page_id))
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
    page_id_str = _decode_preview_token(token)

    try:
        resolved_id = uuid.UUID(page_id_str)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Malformed page_id in token") from exc

    page = await session.get(Page, resolved_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

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
