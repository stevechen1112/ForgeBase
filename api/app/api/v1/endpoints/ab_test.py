"""
2.5.4 A/B Test API endpoints

Routes (prefix: /ab-tests, mounted on tracking_router → /api/v1/tracking/ab-tests/):
  GET    /                          — list all tests (admin)
  POST   /                          — create a test
  GET    /{test_id}                 — detail + live stats
  PATCH  /{test_id}                 — update (name, variants, split_ratio, is_active)
  DELETE /{test_id}                 — delete
  GET    /{test_id}/variant         — assign / retrieve variant for a visitor  ← public frontend call
  POST   /{test_id}/convert         — record a conversion for a visitor        ← public frontend call
  POST   /{test_id}/recalc-stats    — recalculate cached stats from raw views
"""
from __future__ import annotations

import hashlib
import uuid as _uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import select, func

from app.api.v1.deps import require_admin as get_current_admin
from app.db.session import get_session
from app.models.ab_test import ABTest, ABTestView

router = APIRouter(prefix="/ab-tests", tags=["ab-tests"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ABTestCreate(BaseModel):
    name: str
    description: Optional[str] = None
    page_id: Optional[str] = None
    test_element: str = "cta"
    variant_a: str
    variant_b: str
    split_ratio: float = 0.5


class ABTestUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variant_a: Optional[str] = None
    variant_b: Optional[str] = None
    split_ratio: Optional[float] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assign_variant(test: ABTest, visitor_id: str) -> str:
    """
    Deterministically assign variant 'a' or 'b' for a given visitor_id.
    Uses stable hash bucketing: if hash(visitor_id + test_id) % 100 < split_ratio*100 → 'b'
    This ensures the same visitor always sees the same variant.
    """
    digest = hashlib.sha256(f"{visitor_id}:{test.id}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return "b" if bucket < int(test.split_ratio * 100) else "a"


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@router.get("/")
async def list_ab_tests(
    db=Depends(get_session),
    _admin=Depends(get_current_admin),
):
    tests = (await db.execute(select(ABTest).order_by(ABTest.created_at.desc()))).scalars().all()
    return tests


@router.post("/", status_code=201)
async def create_ab_test(
    payload: ABTestCreate,
    db=Depends(get_session),
    _admin=Depends(get_current_admin),
):
    page_uuid = None
    if payload.page_id:
        try:
            page_uuid = _uuid.UUID(payload.page_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid page_id UUID")

    if not (0.0 < payload.split_ratio < 1.0):
        raise HTTPException(status_code=422, detail="split_ratio must be between 0 and 1 (exclusive)")

    test = ABTest(
        name=payload.name,
        description=payload.description,
        page_id=page_uuid,
        test_element=payload.test_element,
        variant_a=payload.variant_a,
        variant_b=payload.variant_b,
        split_ratio=payload.split_ratio,
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test


@router.get("/{test_id}")
async def get_ab_test(
    test_id: _uuid.UUID,
    db=Depends(get_session),
    _admin=Depends(get_current_admin),
):
    test = (await db.execute(select(ABTest).where(ABTest.id == test_id))).scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")

    ctr_a = round(test.conversions_a / test.views_a * 100, 2) if test.views_a else 0.0
    ctr_b = round(test.conversions_b / test.views_b * 100, 2) if test.views_b else 0.0
    uplift = round(ctr_b - ctr_a, 2)

    return {
        **test.model_dump(),
        "ctr_a": ctr_a,
        "ctr_b": ctr_b,
        "uplift": uplift,
    }


@router.patch("/{test_id}")
async def update_ab_test(
    test_id: _uuid.UUID,
    payload: ABTestUpdate,
    db=Depends(get_session),
    _admin=Depends(get_current_admin),
):
    test = (await db.execute(select(ABTest).where(ABTest.id == test_id))).scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(test, field, value)
    test.updated_at = datetime.utcnow()

    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test


@router.delete("/{test_id}", status_code=204)
async def delete_ab_test(
    test_id: _uuid.UUID,
    db=Depends(get_session),
    _admin=Depends(get_current_admin),
):
    test = (await db.execute(select(ABTest).where(ABTest.id == test_id))).scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    await db.delete(test)
    await db.commit()


@router.post("/{test_id}/recalc-stats")
async def recalc_stats(
    test_id: _uuid.UUID,
    db=Depends(get_session),
    _admin=Depends(get_current_admin),
):
    """Recalculate cached view/conversion counts from raw ABTestView logs."""
    test = (await db.execute(select(ABTest).where(ABTest.id == test_id))).scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")

    # Count views per variant
    def _count(variant: str, converted: Optional[bool] = None):
        q = select(func.count()).where(
            ABTestView.test_id == test_id,
            ABTestView.variant == variant,
        )
        if converted is not None:
            q = q.where(ABTestView.converted == converted)
        return q

    test.views_a = (await db.execute(_count("a"))).scalar() or 0
    test.views_b = (await db.execute(_count("b"))).scalar() or 0
    test.conversions_a = (await db.execute(_count("a", True))).scalar() or 0
    test.conversions_b = (await db.execute(_count("b", True))).scalar() or 0
    test.updated_at = datetime.utcnow()

    db.add(test)
    await db.commit()
    await db.refresh(test)
    return {"views_a": test.views_a, "views_b": test.views_b,
            "conversions_a": test.conversions_a, "conversions_b": test.conversions_b}


# ---------------------------------------------------------------------------
# Public (frontend/visitor-facing) endpoints — no auth required
# ---------------------------------------------------------------------------

class VariantResponse(BaseModel):
    test_id: str
    variant: str
    content: str


@router.get("/{test_id}/variant", response_model=VariantResponse)
async def get_variant(
    test_id: _uuid.UUID,
    request: Request,
    db=Depends(get_session),
    visitor_id: Optional[str] = None,
):
    """
    Return which variant a visitor should see, and record the view.
    visitor_id: pass as query param; falls back to IP-based pseudo-ID.
    The same visitor always receives the same variant (deterministic hash).
    """
    test = (await db.execute(
        select(ABTest).where(ABTest.id == test_id, ABTest.is_active == True)  # noqa: E712
    )).scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Active A/B test not found")

    vid = visitor_id or request.client.host or "anonymous"
    variant = _assign_variant(test, vid)

    # Record view
    view = ABTestView(
        test_id=test_id,
        visitor_id=vid,
        variant=variant,
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
    )
    db.add(view)

    # Increment cached counter
    if variant == "a":
        test.views_a += 1
    else:
        test.views_b += 1
    db.add(test)
    await db.commit()

    return VariantResponse(
        test_id=str(test_id),
        variant=variant,
        content=test.variant_a if variant == "a" else test.variant_b,
    )


class ConvertIn(BaseModel):
    visitor_id: Optional[str] = None


@router.post("/{test_id}/convert")
async def record_conversion(
    test_id: _uuid.UUID,
    payload: ConvertIn,
    request: Request,
    db=Depends(get_session),
):
    """Mark the most recent view for this visitor as a conversion."""
    test = (await db.execute(
        select(ABTest).where(ABTest.id == test_id, ABTest.is_active == True)  # noqa: E712
    )).scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Active A/B test not found")

    vid = payload.visitor_id or request.client.host or "anonymous"

    # Find the most recent unconverted view for this visitor
    view = (await db.execute(
        select(ABTestView)
        .where(
            ABTestView.test_id == test_id,
            ABTestView.visitor_id == vid,
            ABTestView.converted == False,  # noqa: E712
        )
        .order_by(ABTestView.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    if not view:
        return {"recorded": False, "reason": "No unconverted view found for this visitor"}

    view.converted = True
    db.add(view)

    # Increment cached counter
    if view.variant == "a":
        test.conversions_a += 1
    else:
        test.conversions_b += 1
    test.updated_at = datetime.utcnow()
    db.add(test)
    await db.commit()

    return {"recorded": True, "variant": view.variant}
