"""
ContentAsset upload endpoint.
POST /api/v1/content/assets          — upload file to R2 + save metadata
GET  /api/v1/content/assets          — list assets (with filters)
DELETE /api/v1/content/assets/{id}   — delete from R2 + DB
"""
import uuid
import mimetypes
from io import BytesIO
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query, status
from pydantic import BaseModel
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from PIL import Image
from slugify import slugify

from app.api.v1.deps import get_current_user, require_content_editor
from app.core.config import settings
from app.db.session import get_session
from app.models.content_asset import ContentAsset
from app.models.page import Page
from app.models.product import Product
from app.models.user import User
from app.schemas.base import APIResponse, PaginationMeta

router = APIRouter(prefix="/assets", tags=["Content Assets"])

# ── R2 client (lazy-initialised) ─────────────────────────────────────────────

_s3_client = None

def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _s3_client


ALLOWED_MIME_TYPES = {
    # images
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml",
    # documents
    "application/pdf",
    # CAD / data
    "application/octet-stream",
    "model/step", "model/iges",
    "text/csv", "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _default_alt_text(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
    return " ".join(part.capitalize() for part in stem.split())[:200]


def _compress_image_if_possible(content: bytes, mime_type: str) -> tuple[bytes, str]:
    if not mime_type.startswith("image/") or mime_type in {"image/svg+xml", "image/gif"}:
        return content, mime_type

    try:
        image = Image.open(BytesIO(content))
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        output = BytesIO()
        image.save(output, format="WEBP", quality=82, optimize=True)
        return output.getvalue(), "image/webp"
    except Exception:
        return content, mime_type


async def _build_r2_key(
    session: AsyncSession,
    original_filename: str,
    product_id: str | None,
    page_id: str | None,
) -> str:
    ext = (original_filename or "file").rsplit(".", 1)[-1].lower()
    prefix = "asset"

    if product_id:
        product = await session.get(Product, uuid.UUID(product_id))
        if product:
            prefix = product.slug
    elif page_id:
        page = await session.get(Page, uuid.UUID(page_id))
        if page:
            prefix = slugify(page.slug) or "page"

    if ext == "jpeg":
        ext = "jpg"
    return f"assets/{prefix}-{uuid.uuid4().hex[:10]}.{ext}"


def _classify_asset_type(mime_type: str) -> str:
    if mime_type.startswith("image/"):
        return "image"
    if mime_type == "application/pdf":
        return "pdf"
    if mime_type in ("model/step", "model/iges", "application/octet-stream"):
        return "cad"
    return "other"


# ── Read schema ───────────────────────────────────────────────────────────────

class ContentAssetRead(BaseModel):
    id: uuid.UUID
    original_filename: str
    r2_key: str
    public_url: str
    mime_type: str
    file_size_bytes: int
    asset_type: str
    alt_text: str | None
    title: str | None
    is_indexable: bool = False
    seo_title: str | None = None
    requires_gate: bool = False
    product_id: uuid.UUID | None
    page_id: uuid.UUID | None
    uploaded_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Upload endpoint ───────────────────────────────────────────────────────────

@router.post("", response_model=ContentAssetRead, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    title: str | None = Form(default=None),
    is_indexable: bool = Form(default=False),
    seo_title: str | None = Form(default=None),
    product_id: str | None = Form(default=None),
    page_id: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    # ── Validate MIME type ────────────────────────────────────────────────────
    mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{mime_type}' is not allowed.",
        )

    # ── Read & size-check ─────────────────────────────────────────────────────
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    content, mime_type = _compress_image_if_possible(content, mime_type)

    # ── Build R2 key ──────────────────────────────────────────────────────────
    filename = file.filename or "file"
    if mime_type == "image/webp":
        filename = filename.rsplit(".", 1)[0] + ".webp"
    r2_key = await _build_r2_key(session, filename, product_id, page_id)

    # ── Upload to R2 ──────────────────────────────────────────────────────────
    try:
        _get_s3().put_object(
            Bucket=settings.R2_BUCKET_NAME,
            Key=r2_key,
            Body=content,
            ContentType=mime_type,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"R2 upload failed: {exc}",
        ) from exc

    public_url = f"{settings.R2_PUBLIC_URL.rstrip('/')}/{r2_key}"

    # ── Save metadata ─────────────────────────────────────────────────────────
    asset = ContentAsset(
        original_filename=filename,
        r2_key=r2_key,
        public_url=public_url,
        mime_type=mime_type,
        file_size_bytes=len(content),
        asset_type=_classify_asset_type(mime_type),
        alt_text=alt_text or _default_alt_text(filename),
        title=title,
        is_indexable=is_indexable,
        seo_title=seo_title,
        product_id=uuid.UUID(product_id) if product_id else None,
        page_id=uuid.UUID(page_id) if page_id else None,
        uploaded_by=current_user.id,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return ContentAssetRead.model_validate(asset)


# ── List endpoint ─────────────────────────────────────────────────────────────

@router.get("", response_model=APIResponse)
async def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    asset_type: str | None = Query(None),
    product_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    q = select(ContentAsset)
    if asset_type:
        q = q.where(ContentAsset.asset_type == asset_type)
    if product_id:
        q = q.where(ContentAsset.product_id == uuid.UUID(product_id))

    total = (await session.exec(select(func.count()).select_from(q.subquery()))).one()
    items = (
        await session.exec(
            q.order_by(ContentAsset.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
        )
    ).all()

    return APIResponse(
        data=[ContentAssetRead.model_validate(i) for i in items],
        meta=PaginationMeta(total=total, page=page, page_size=page_size,
                            total_pages=max(1, -(-total // page_size))),
    )


# ── Delete endpoint ───────────────────────────────────────────────────────────

@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    asset = await session.get(ContentAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Delete from R2
    try:
        _get_s3().delete_object(Bucket=settings.R2_BUCKET_NAME, Key=asset.r2_key)
    except Exception:
        pass  # Log but don't block DB removal

    await session.delete(asset)
    await session.commit()


# ── Update alt text endpoint ─────────────────────────────────────────────────

class AssetUpdate(BaseModel):
    alt_text: str | None = None
    title: str | None = None
    is_indexable: bool | None = None
    seo_title: str | None = None
    requires_gate: bool | None = None


@router.patch("/{asset_id}", response_model=ContentAssetRead)
async def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    asset = await session.get(ContentAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if payload.alt_text is not None:
        asset.alt_text = payload.alt_text
    if payload.title is not None:
        asset.title = payload.title
    if payload.is_indexable is not None:
        asset.is_indexable = payload.is_indexable
    if payload.seo_title is not None:
        asset.seo_title = payload.seo_title
    if payload.requires_gate is not None:
        asset.requires_gate = payload.requires_gate
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return ContentAssetRead.model_validate(asset)


# ── Public: indexed documents (2.3.2) ─────────────────────────────────────────

class IndexedDocRead(BaseModel):
    id: uuid.UUID
    title: str | None
    seo_title: str | None
    public_url: str
    mime_type: str
    file_size_bytes: int
    requires_gate: bool = False
    product_id: uuid.UUID | None
    created_at: datetime


@router.get("/public/indexed-docs", response_model=list[IndexedDocRead], tags=["Public Assets"])
async def list_indexed_documents(
    product_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Public endpoint: returns all PDFs marked as is_indexable, optionally filtered by product."""
    q = select(ContentAsset).where(
        ContentAsset.is_indexable == True,  # noqa: E712
        ContentAsset.asset_type == "pdf",
    )
    if product_id:
        try:
            q = q.where(ContentAsset.product_id == uuid.UUID(product_id))
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid product_id format")
    items = (
        await session.exec(q.order_by(ContentAsset.created_at.desc()))
    ).all()
    return [
        IndexedDocRead(
            id=a.id,
            title=a.title,
            seo_title=a.seo_title,
            public_url=a.public_url,
            mime_type=a.mime_type,
            file_size_bytes=a.file_size_bytes,
            product_id=a.product_id,
            created_at=a.created_at,
        )
        for a in items
    ]
