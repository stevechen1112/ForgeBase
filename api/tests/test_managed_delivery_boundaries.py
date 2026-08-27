"""Security boundaries for operator-managed website delivery."""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.publish import _ensure_publish_access
from app.core.security import create_access_token, get_password_hash
from app.models.page import Page
from app.models.user import User
from tests.conftest import _make_engine, requires_db


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _token_for_role(tenant_id: uuid.UUID, role: str) -> str:
    engine, factory = _make_engine()
    try:
        async with factory() as session:
            user = User(
                tenant_id=tenant_id,
                email=f"{role}-{uuid.uuid4().hex[:10]}@test.invalid",
                full_name=f"Test {role}",
                hashed_password=get_password_hash("testpass"),
                role=role,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return create_access_token(str(user.id))
    finally:
        await engine.dispose()


async def _create_legacy_global_page() -> uuid.UUID:
    engine, factory = _make_engine()
    try:
        async with factory() as session:
            page = Page(
                tenant_id=None,
                page_type="landing",
                slug=f"legacy-global-{uuid.uuid4().hex[:8]}",
                title="Legacy global page",
                body="{}",
                locale="en",
                status="draft",
            )
            session.add(page)
            await session.commit()
            await session.refresh(page)
            return page.id
    finally:
        await engine.dispose()


async def _delete_page(page_id: uuid.UUID) -> None:
    engine, factory = _make_engine()
    try:
        async with factory() as session:
            page = await session.get(Page, page_id)
            if page is not None:
                await session.delete(page)
                await session.commit()
    finally:
        await engine.dispose()


def test_legacy_global_content_requires_platform_superuser() -> None:
    content = SimpleNamespace(tenant_id=None)
    tenant_admin = SimpleNamespace(
        is_superuser=False,
        tenant_id=uuid.uuid4(),
    )
    with pytest.raises(HTTPException) as exc_info:
        _ensure_publish_access(content, tenant_admin)
    assert exc_info.value.status_code == 404

    platform_admin = SimpleNamespace(is_superuser=True, tenant_id=None)
    _ensure_publish_access(content, platform_admin)


@requires_db
@pytest.mark.asyncio
async def test_page_preview_publish_and_authoring_are_operator_managed(
    http_client,
    two_tenants,
    admin_token_for_tenant,
) -> None:
    tenant_a, tenant_b = two_tenants
    admin_a = await admin_token_for_tenant(tenant_a.id)
    admin_b = await admin_token_for_tenant(tenant_b.id)
    marketing_b = await _token_for_role(tenant_b.id, "marketing_manager")

    payload = {
        "page_type": "landing",
        "slug": f"managed-page-{uuid.uuid4().hex[:8]}",
        "title": "Managed delivery page",
        "body": '{"blocks":[{"type":"hero","title":"Managed"}]}',
        "locale": "en",
        "status": "draft",
    }
    create = await http_client.post(
        "/api/v1/content/pages",
        json=payload,
        headers=_auth(admin_b),
    )
    assert create.status_code == 201, create.text
    page_id = create.json()["data"]["id"]

    denied_preview = await http_client.post(
        f"/api/v1/content/pages/{page_id}/preview-token",
        json={},
        headers=_auth(admin_a),
    )
    assert denied_preview.status_code == 404

    allowed_preview = await http_client.post(
        f"/api/v1/content/pages/{page_id}/preview-token",
        json={},
        headers=_auth(admin_b),
    )
    assert allowed_preview.status_code == 200, allowed_preview.text
    preview_token = allowed_preview.json()["token"]
    preview = await http_client.get(f"/api/v1/content/preview/{preview_token}")
    assert preview.status_code == 200, preview.text
    assert preview.json()["id"] == page_id

    denied_publish = await http_client.post(
        f"/api/v1/content/pages/{page_id}/publish",
        json={},
        headers=_auth(admin_a),
    )
    assert denied_publish.status_code == 404

    marketing_publish = await http_client.post(
        f"/api/v1/content/pages/{page_id}/publish",
        json={},
        headers=_auth(marketing_b),
    )
    assert marketing_publish.status_code == 403

    allowed_publish = await http_client.post(
        f"/api/v1/content/pages/{page_id}/publish",
        json={},
        headers=_auth(admin_b),
    )
    assert allowed_publish.status_code == 200, allowed_publish.text

    marketing_create = await http_client.post(
        "/api/v1/content/pages",
        json={**payload, "slug": f"blocked-{uuid.uuid4().hex[:8]}"},
        headers=_auth(marketing_b),
    )
    assert marketing_create.status_code == 403


@requires_db
@pytest.mark.asyncio
async def test_tenant_admin_cannot_mutate_legacy_global_page(
    http_client,
    two_tenants,
    admin_token_for_tenant,
) -> None:
    tenant_a, _ = two_tenants
    admin_a = await admin_token_for_tenant(tenant_a.id)
    page_id = await _create_legacy_global_page()
    try:
        listing = await http_client.get(
            "/api/v1/content/pages",
            headers=_auth(admin_a),
        )
        assert listing.status_code == 200, listing.text
        assert str(page_id) not in {item["id"] for item in listing.json()["data"]}

        read = await http_client.get(
            f"/api/v1/content/pages/{page_id}",
            headers=_auth(admin_a),
        )
        assert read.status_code == 404

        update = await http_client.patch(
            f"/api/v1/content/pages/{page_id}",
            json={"title": "Tenant takeover attempt"},
            headers=_auth(admin_a),
        )
        assert update.status_code == 404

        publish = await http_client.post(
            f"/api/v1/content/pages/{page_id}/publish",
            json={},
            headers=_auth(admin_a),
        )
        assert publish.status_code == 404
    finally:
        await _delete_page(page_id)
