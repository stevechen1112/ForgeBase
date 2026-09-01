"""Read-only preview contract for the waiting-buyer list builder."""

import uuid

import pytest
from sqlmodel import func, select

from app.models.segment import Segment
from app.models.visitor import Visitor
from tests.conftest import _make_engine, requires_db


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@requires_db
@pytest.mark.asyncio
async def test_segment_preview_counts_matches_without_creating_a_segment(
    http_client,
    two_tenants,
    admin_token_for_tenant,
) -> None:
    tenant, _ = two_tenants
    token = await admin_token_for_tenant(tenant.id)
    engine, factory = _make_engine()
    try:
        async with factory() as session:
            session.add(
                Visitor(visitor_id=uuid.uuid4(), tenant_id=tenant.id, country="TW")
            )
            await session.commit()

        response = await http_client.post(
            "/api/v1/tracking/segments/preview",
            headers=_auth(token),
            json={
                "conditions": [{"type": "country", "op": "eq", "value": "TW"}],
                "combinator": "AND",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"total_matches": 1}

        async with factory() as session:
            count = await session.exec(
                select(func.count()).select_from(Segment).where(Segment.tenant_id == tenant.id)
            )
            assert count.one() == 0
    finally:
        await engine.dispose()
