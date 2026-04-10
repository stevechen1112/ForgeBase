"""
Redirect management — CRUD for 301/302 SEO redirect rules.

Routes (all require auth):
  GET    /content/redirects           — list all active redirects
  POST   /content/redirects           — create a new redirect rule
  PATCH  /content/redirects/{id}      — update a redirect rule
  DELETE /content/redirects/{id}      — deactivate (soft-delete) a redirect

Public resolution endpoint (no auth):
  GET    /content/redirects/resolve?path=... — used by Next.js middleware
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import RequireFeature, get_current_user
from app.db.session import get_session
from app.models.redirect import Redirect
from app.models.user import User
from app.schemas.redirect import RedirectCreate, RedirectRead, RedirectUpdate
from app.core.datetime import utcnow_naive

router = APIRouter(prefix="/redirects", tags=["Redirects"])


# ── Public resolve endpoint (no auth — called by Next.js middleware) ──────────

@router.get("/resolve", response_model=Optional[RedirectRead], include_in_schema=False)
async def resolve_redirect(
    path: str = Query(..., description="Incoming request path, e.g. /products/old-slug"),
    db: AsyncSession = Depends(get_session),
):
    """
    Look up a redirect rule for the given path.
    Returns the redirect row if found and active, otherwise null.
    Used by Next.js middleware to perform server-side 301/302 redirects.
    """
    result = await db.exec(
        select(Redirect).where(
            Redirect.from_path == path,
            Redirect.is_active == True,  # noqa: E712
        )
    )
    return result.first()


# ── Admin CRUD ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[RedirectRead])
async def list_redirects(
    active_only: bool = Query(True),
    _feature: User = Depends(RequireFeature("seo_redirects")),
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    stmt = select(Redirect)
    if active_only:
        stmt = stmt.where(Redirect.is_active == True)  # noqa: E712
    stmt = stmt.order_by(Redirect.created_at.desc())
    result = await db.exec(stmt)
    return result.all()


@router.post("", response_model=RedirectRead, status_code=201)
async def create_redirect(
    body: RedirectCreate,
    _feature: User = Depends(RequireFeature("seo_redirects")),
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    # Prevent redirect loops
    if body.from_path == body.to_path:
        raise HTTPException(status_code=400, detail="from_path and to_path must differ")

    # Check for existing rule on this path
    existing = await db.exec(
        select(Redirect).where(Redirect.from_path == body.from_path)
    )
    if existing.first():
        raise HTTPException(
            status_code=409,
            detail=f"A redirect rule already exists for '{body.from_path}'",
        )

    redirect = Redirect(**body.model_dump())
    db.add(redirect)
    await db.commit()
    await db.refresh(redirect)
    return redirect


@router.patch("/{redirect_id}", response_model=RedirectRead)
async def update_redirect(
    redirect_id: uuid.UUID,
    body: RedirectUpdate,
    _feature: User = Depends(RequireFeature("seo_redirects")),
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    redirect = await db.get(Redirect, redirect_id)
    if not redirect:
        raise HTTPException(status_code=404, detail="Redirect not found")

    patch = body.model_dump(exclude_unset=True)
    if "from_path" in patch and "to_path" in patch:
        if patch["from_path"] == patch["to_path"]:
            raise HTTPException(status_code=400, detail="from_path and to_path must differ")
    elif "from_path" in patch and patch["from_path"] == redirect.to_path:
        raise HTTPException(status_code=400, detail="from_path and to_path must differ")
    elif "to_path" in patch and patch["to_path"] == redirect.from_path:
        raise HTTPException(status_code=400, detail="from_path and to_path must differ")

    for field, value in patch.items():
        setattr(redirect, field, value)
    redirect.updated_at = utcnow_naive()

    db.add(redirect)
    await db.commit()
    await db.refresh(redirect)
    return redirect


@router.delete("/{redirect_id}", status_code=204)
async def deactivate_redirect(
    redirect_id: uuid.UUID,
    _feature: User = Depends(RequireFeature("seo_redirects")),
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    """Soft-delete: sets is_active=False rather than destroying the record."""
    redirect = await db.get(Redirect, redirect_id)
    if not redirect:
        raise HTTPException(status_code=404, detail="Redirect not found")

    redirect.is_active = False
    redirect.updated_at = utcnow_naive()
    db.add(redirect)
    await db.commit()
