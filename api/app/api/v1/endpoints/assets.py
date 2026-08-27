"""
ContentAsset upload endpoint.
POST /api/v1/content/assets          — upload file to R2 + save metadata
GET  /api/v1/content/assets          — list assets (with filters)
DELETE /api/v1/content/assets/{id}   — delete from R2 + DB
"""
import asyncio
import hashlib
import mimetypes
import shutil
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import SpooledTemporaryFile

import boto3
from botocore.config import Config
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from PIL import Image
from pydantic import BaseModel
from pydantic import Field as PydanticField
from slugify import slugify
from sqlalchemy import text
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import (
    get_current_user,
    require_content_editor,
    require_user_tenant_id,
)
from app.core.config import settings
from app.db.session import get_session
from app.models.content_asset import ContentAsset
from app.models.page import Page
from app.models.product import Product
from app.models.user import User
from app.schemas.base import APIResponse, PaginationMeta
from app.services.knowledge_extract import is_indexable_document
from app.services.knowledge_sync import sync_knowledge_now

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
    "image/jpeg", "image/png", "image/webp", "image/gif",
    # documents
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # CAD / data
    "application/octet-stream",
    "model/step", "model/iges",
    "text/csv", "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
UPLOAD_CHUNK_SIZE = 1024 * 1024
_CAD_EXTENSIONS = {".step", ".stp", ".iges", ".igs"}


def _validate_file_signature(filename: str, mime_type: str, head: bytes) -> None:
    """Reject common MIME spoofing before a payload reaches storage."""
    suffix = Path(filename).suffix.lower()
    if mime_type == "application/pdf" and not head.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The uploaded PDF signature is invalid.")
    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" and not head.startswith(b"PK"):
        raise HTTPException(status_code=415, detail="The uploaded DOCX signature is invalid.")
    if mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" and not head.startswith(b"PK"):
        raise HTTPException(status_code=415, detail="The uploaded XLSX signature is invalid.")
    if mime_type == "application/vnd.ms-excel" and suffix == ".xls" and not head.startswith(b"\xd0\xcf\x11\xe0"):
        raise HTTPException(status_code=415, detail="The uploaded XLS signature is invalid.")
    if mime_type == "text/csv" and suffix != ".csv":
        raise HTTPException(status_code=415, detail="CSV uploads must use the .csv extension.")
    if mime_type in {"model/step", "model/iges", "application/octet-stream"}:
        if suffix not in _CAD_EXTENSIONS:
            raise HTTPException(status_code=415, detail="Binary uploads are limited to STEP/IGES CAD files.")
        ascii_head = head.decode("ascii", errors="ignore").upper()
        if suffix in {".step", ".stp"} and "ISO-10303-21" not in ascii_head:
            raise HTTPException(status_code=415, detail="The uploaded STEP signature is invalid.")
        if not ascii_head.strip():
            raise HTTPException(status_code=415, detail="The uploaded CAD payload is invalid.")


async def _spool_upload(file: UploadFile) -> tuple[SpooledTemporaryFile, int, str, bytes]:
    spool = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    digest = hashlib.sha256()
    size = 0
    head = b""
    while chunk := await file.read(UPLOAD_CHUNK_SIZE):
        size += len(chunk)
        if size > MAX_FILE_SIZE:
            spool.close()
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)} MB.",
            )
        if len(head) < 4096:
            head += chunk[: 4096 - len(head)]
        digest.update(chunk)
        spool.write(chunk)
    if size == 0:
        spool.close()
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    spool.seek(0)
    return spool, size, digest.hexdigest(), head


def _default_alt_text(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
    return " ".join(part.capitalize() for part in stem.split())[:200]


def _compress_image_if_possible(content: bytes, mime_type: str) -> tuple[bytes, str]:
    if not mime_type.startswith("image/"):
        return content, mime_type

    try:
        image = Image.open(BytesIO(content))
        image.verify()
        if mime_type == "image/gif":
            return content, mime_type
        image = Image.open(BytesIO(content))
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        output = BytesIO()
        image.save(output, format="WEBP", quality=82, optimize=True)
        return output.getvalue(), "image/webp"
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded image payload is invalid.",
        ) from exc


async def _build_r2_key(
    session: AsyncSession,
    original_filename: str,
    product_id: uuid.UUID | None,
    page_id: uuid.UUID | None,
    tenant_id: uuid.UUID,
) -> str:
    ext = (original_filename or "file").rsplit(".", 1)[-1].lower()
    prefix = "asset"

    if product_id:
        product = await session.get(Product, product_id)
        if not product or product.tenant_id not in (None, tenant_id):
            raise HTTPException(status_code=404, detail="Product not found")
        prefix = product.slug
    elif page_id:
        page = await session.get(Page, page_id)
        if not page or page.tenant_id not in (None, tenant_id):
            raise HTTPException(status_code=404, detail="Page not found")
        prefix = slugify(page.slug) or "page"

    if ext == "jpeg":
        ext = "jpg"
    return f"assets/{tenant_id}/{prefix}-{uuid.uuid4().hex[:10]}.{ext}"


def _classify_asset_type(mime_type: str) -> str:
    if mime_type.startswith("image/"):
        return "image"
    if mime_type == "application/pdf":
        return "pdf"
    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "document"
    if mime_type in ("model/step", "model/iges", "application/octet-stream"):
        return "cad"
    return "other"


# ── Read schema ───────────────────────────────────────────────────────────────

class ContentAssetRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    original_filename: str
    r2_key: str
    public_url: str
    mime_type: str
    file_size_bytes: int
    sha256: str | None
    asset_type: str
    alt_text: str | None
    title: str | None
    is_indexable: bool = False
    index_status: str = "not_indexed"
    index_error: str | None = None
    seo_title: str | None = None
    product_id: uuid.UUID | None
    page_id: uuid.UUID | None
    display_order: int = 0
    uploaded_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


async def _next_display_order(
    session: AsyncSession,
    product_id: uuid.UUID | None,
    tenant_id: uuid.UUID,
) -> int:
    if not product_id:
        return 0
    current = (
        await session.exec(
            select(func.max(ContentAsset.display_order)).where(
                ContentAsset.product_id == product_id,
                ContentAsset.tenant_id == tenant_id,
            )
        )
    ).one()
    return int(current or 0) + 1


# ── Upload endpoint ───────────────────────────────────────────────────────────

@router.post("", response_model=ContentAssetRead, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None, max_length=200),
    title: str | None = Form(default=None, max_length=200),
    is_indexable: bool = Form(default=False),
    seo_title: str | None = Form(default=None, max_length=200),
    product_id: uuid.UUID | None = Form(default=None),
    page_id: uuid.UUID | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    tenant_id = require_user_tenant_id(current_user)
    # ── Validate MIME type ────────────────────────────────────────────────────
    mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{mime_type}' is not allowed.",
        )

    # ── Read & size-check ─────────────────────────────────────────────────────
    spool, file_size, sha256, head = await _spool_upload(file)
    filename = file.filename or "file"
    try:
        _validate_file_signature(filename, mime_type, head)
    except Exception:
        spool.close()
        raise

    # Serialize quota checks per tenant so concurrent uploads cannot both see
    # the same remaining capacity and overrun the configured allowance.
    if session.get_bind().dialect.name == "postgresql":
        await session.exec(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            params={"lock_key": f"forgebase-asset-quota-{tenant_id}"},
        )
    used_bytes = (
        await session.exec(
            select(func.coalesce(func.sum(ContentAsset.file_size_bytes), 0)).where(
                ContentAsset.tenant_id == tenant_id
            )
        )
    ).one()
    if int(used_bytes or 0) + file_size > settings.ASSET_TENANT_QUOTA_BYTES:
        spool.close()
        raise HTTPException(status_code=413, detail="Tenant asset storage quota exceeded.")

    if mime_type.startswith("image/"):
        try:
            content, mime_type = _compress_image_if_possible(spool.read(), mime_type)
        finally:
            spool.close()
        spool = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
        spool.write(content)
        spool.seek(0)
        file_size = len(content)
        sha256 = hashlib.sha256(content).hexdigest()

    # ── Build R2 key ──────────────────────────────────────────────────────────
    if mime_type == "image/webp":
        filename = filename.rsplit(".", 1)[0] + ".webp"
    try:
        r2_key = await _build_r2_key(session, filename, product_id, page_id, tenant_id)
    except Exception:
        spool.close()
        raise

    # ── Upload: R2 when configured, otherwise local disk for development ─────
    use_r2 = bool(settings.R2_ACCOUNT_ID and settings.R2_ACCESS_KEY_ID and settings.R2_PUBLIC_URL)
    if use_r2:
        try:
            await asyncio.to_thread(
                _get_s3().put_object,
                Bucket=settings.R2_BUCKET_NAME,
                Key=r2_key,
                Body=spool,
                ContentType=mime_type,
                Metadata={"sha256": sha256},
            )
        except Exception as exc:
            spool.close()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="R2 upload failed.",
            ) from exc
        public_url = f"{settings.R2_PUBLIC_URL.rstrip('/')}/{r2_key}"
    else:
        local_root = Path(__file__).resolve().parents[4] / "uploads"
        local_path = local_root / r2_key
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with local_path.open("wb") as destination:
            shutil.copyfileobj(spool, destination)
        # Prefer 127.0.0.1 over localhost (Windows IPv6 / localhost hangs)
        base = (settings.APP_URL or "http://127.0.0.1:8001").rstrip("/")
        if "://localhost" in base:
            base = base.replace("://localhost", "://127.0.0.1")
        public_url = f"{base}/uploads/{r2_key}"

    # ── Save metadata ─────────────────────────────────────────────────────────
    asset = ContentAsset(
        tenant_id=tenant_id,
        original_filename=filename,
        r2_key=r2_key,
        public_url=public_url,
        mime_type=mime_type,
        file_size_bytes=file_size,
        sha256=sha256,
        asset_type=_classify_asset_type(mime_type),
        alt_text=alt_text or _default_alt_text(filename),
        title=title,
        is_indexable=is_indexable,
        seo_title=seo_title,
        product_id=product_id,
        page_id=page_id,
        display_order=await _next_display_order(session, product_id, tenant_id),
        uploaded_by=current_user.id,
        index_status=(
            "pending"
            if is_indexable and is_indexable_document(mime_type, filename)
            else ("not_applicable" if not is_indexable_document(mime_type, filename) else "not_indexed")
        ),
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    await sync_knowledge_now(session, tenant_id=tenant_id, item=asset)
    await session.commit()
    await session.refresh(asset)
    spool.close()
    return ContentAssetRead.model_validate(asset)


# ── List endpoint ─────────────────────────────────────────────────────────────

@router.get("", response_model=APIResponse)
async def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    asset_type: str | None = Query(None),
    product_id: uuid.UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    tenant_id = require_user_tenant_id(current_user)
    q = select(ContentAsset).where(ContentAsset.tenant_id == tenant_id)
    if asset_type:
        q = q.where(ContentAsset.asset_type == asset_type)
    if product_id:
        q = q.where(ContentAsset.product_id == product_id)

    total = (await session.exec(select(func.count()).select_from(q.subquery()))).one()
    items = (
        await session.exec(
            q.order_by(ContentAsset.display_order, ContentAsset.created_at.desc())
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
    tenant_id = require_user_tenant_id(current_user)
    asset = (
        await session.exec(
            select(ContentAsset).where(
                ContentAsset.id == asset_id,
                ContentAsset.tenant_id == tenant_id,
            )
        )
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    await sync_knowledge_now(session, tenant_id=tenant_id, item=asset, action="tombstone")

    # Delete from storage (R2 or local)
    try:
        if settings.R2_ACCOUNT_ID and settings.R2_ACCESS_KEY_ID:
            await asyncio.to_thread(
                _get_s3().delete_object,
                Bucket=settings.R2_BUCKET_NAME,
                Key=asset.r2_key,
            )
        else:
            from pathlib import Path
            local_path = Path(__file__).resolve().parents[4] / "uploads" / asset.r2_key
            if local_path.is_file():
                local_path.unlink()
    except Exception:
        pass  # Log but don't block DB removal

    await session.delete(asset)
    await session.commit()


# ── Update alt text endpoint ─────────────────────────────────────────────────

class AssetUpdate(BaseModel):
    alt_text: str | None = PydanticField(default=None, max_length=200)
    title: str | None = PydanticField(default=None, max_length=200)
    is_indexable: bool | None = None
    seo_title: str | None = PydanticField(default=None, max_length=200)
    display_order: int | None = PydanticField(default=None, ge=0, le=1000)
    product_id: uuid.UUID | None = None


@router.patch("/{asset_id}", response_model=ContentAssetRead)
async def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    tenant_id = require_user_tenant_id(current_user)
    asset = (
        await session.exec(
            select(ContentAsset).where(
                ContentAsset.id == asset_id,
                ContentAsset.tenant_id == tenant_id,
            )
        )
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if payload.alt_text is not None:
        asset.alt_text = payload.alt_text
    if payload.title is not None:
        asset.title = payload.title
    if payload.is_indexable is not None:
        asset.is_indexable = payload.is_indexable
        if payload.is_indexable:
            asset.index_status = "pending"
        else:
            asset.index_status = "withdrawn"
    if payload.seo_title is not None:
        asset.seo_title = payload.seo_title
    if payload.display_order is not None:
        asset.display_order = payload.display_order
    if payload.product_id is not None:
        product = await session.get(Product, payload.product_id)
        if not product or product.tenant_id not in (None, tenant_id):
            raise HTTPException(status_code=404, detail="Product not found")
        asset.product_id = payload.product_id
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    await sync_knowledge_now(session, tenant_id=tenant_id, item=asset)
    await session.commit()
    await session.refresh(asset)
    return ContentAssetRead.model_validate(asset)
