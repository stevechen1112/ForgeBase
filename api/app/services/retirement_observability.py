"""PII-free usage recording for candidates in a formal retirement window."""

from __future__ import annotations

import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.retirement import RetirementUsageEvent


async def record_retirement_usage(
    db: AsyncSession,
    *,
    candidate_key: str,
    event_name: str,
    tenant_id: uuid.UUID | None,
    source: str = "api",
) -> None:
    """Append minimal usage evidence; never store request bodies or identifiers."""
    db.add(
        RetirementUsageEvent(
            candidate_key=candidate_key,
            tenant_id=tenant_id,
            event_name=event_name,
            source=source,
        )
    )
    await db.commit()
