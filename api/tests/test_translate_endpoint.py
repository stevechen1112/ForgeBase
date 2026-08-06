"""
Translate-draft endpoint integration tests.

Covers:
- Tenant isolation: X-Tenant-ID header is ignored; the caller's own
  tenant_id (from JWT) governs. A forged header must NOT leak another
  tenant's entity content.
- Same-tenant happy path returns a translated draft (LLM mocked).

Run: pytest tests/test_translate_endpoint.py -v
"""
import json
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import requires_db


def _mock_llm(payload: dict):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps(payload, ensure_ascii=False)
    return resp


async def _make_faq(factory, tenant_id) -> uuid.UUID:
    from app.models.faq_item import FAQItem

    async with factory() as session:
        faq = FAQItem(
            question="What is a ratchet wrench?",
            answer="A hand tool.",
            locale="en",
            status="published",
            tenant_id=tenant_id,
        )
        session.add(faq)
        await session.commit()
        await session.refresh(faq)
        return faq.id


@requires_db
@pytest.mark.asyncio
async def test_translate_draft_rejects_cross_tenant_header(
    http_client, two_tenants, admin_token_for_tenant
):
    """Caller belongs to tenant B but forges X-Tenant-ID: <tenant A>.
    The endpoint must NOT trust the header — tenant A's FAQ stays invisible (404)."""
    from tests.conftest import _make_engine

    tenant_a, tenant_b = two_tenants
    _, factory = _make_engine()
    # Starter plan lacks the multilingual feature (403 before isolation check);
    # upgrade tenant B to professional so the tenant-isolation path is exercised.
    from sqlalchemy import text
    async with factory() as session:
        await session.execute(
            text("UPDATE tenants SET plan = 'professional' WHERE id = :tid"),
            {"tid": str(tenant_b.id)},
        )
        await session.commit()

    faq_a_id = await _make_faq(factory, tenant_a.id)

    token_b = await admin_token_for_tenant(tenant_b.id)
    resp = await http_client.post(
        "/api/v1/content/translate-draft",
        json={
            "entity_type": "faq",
            "source_id": str(faq_a_id),
            "target_locale": "zh-tw",
        },
        headers={
            "Authorization": f"Bearer {token_b}",
            "X-Tenant-ID": str(tenant_a.id),  # forged — must be ignored
        },
    )
    assert resp.status_code == 404, resp.text


@requires_db
@pytest.mark.asyncio
async def test_translate_draft_same_tenant_ok(
    http_client, two_tenants, admin_token_for_tenant
):
    """Same-tenant request succeeds; LLM mocked. Tenant A is on professional plan
    (multilingual feature enabled)."""
    from tests.conftest import _make_engine

    tenant_a, _ = two_tenants
    _, factory = _make_engine()
    faq_id = await _make_faq(factory, tenant_a.id)

    token = await admin_token_for_tenant(tenant_a.id)
    with patch("app.services.translator.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm({"question": "什麼是棘輪扳手？", "answer": "一種手工具。"})
        )
        resp = await http_client.post(
            "/api/v1/content/translate-draft",
            json={
                "entity_type": "faq",
                "source_id": str(faq_id),
                "target_locale": "zh-tw",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["target_locale"] == "zh-tw"
    assert body["fields"]["question"] == "什麼是棘輪扳手？"


@requires_db
@pytest.mark.asyncio
async def test_translate_draft_validates_entity_type(
    http_client, two_tenants, admin_token_for_tenant
):
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    resp = await http_client.post(
        "/api/v1/content/translate-draft",
        json={
            "entity_type": "rfq_request",
            "source_id": str(uuid.uuid4()),
            "target_locale": "zh-tw",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text
