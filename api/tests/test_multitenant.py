"""
Multi-tenant isolation and white-label boundary tests.

These tests require a live DATABASE_URL (the `forgebase` DB created during
local setup or in CI). They are skipped automatically when DATABASE_URL is
not set.

Coverage:
  - Tenant data isolation: tenant A content is invisible to tenant B
  - Slug uniqueness: same slug is allowed across different tenants
  - Auth boundary: admin of tenant A cannot read/modify tenant B content
  - Plan gating: Professional-only features blocked for Starter tenants
  - Chat session: chat created under tenant A is isolated from tenant B
  - SiteProfile isolation: each tenant gets its own site profile
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from tests.conftest import requires_db


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _tenant_header(tenant_id: uuid.UUID) -> dict:
    return {"X-Tenant-ID": str(tenant_id)}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Category data isolation
# ─────────────────────────────────────────────────────────────────────────────

@requires_db
@pytest.mark.asyncio
async def test_category_created_by_tenant_a_invisible_to_tenant_b(
    http_client: AsyncClient,
    two_tenants,
    admin_token_for_tenant,
):
    """A category created under tenant A must not appear in tenant B's listing."""
    tenant_a, tenant_b = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)

    slug = f"fasteners-{uuid.uuid4().hex[:6]}"

    # Create category as tenant A
    create_resp = await http_client.post(
        "/api/v1/content/categories",
        json={
            "category_name": "Fasteners",
            "slug": slug,
            "locale": "en",
            "status": "published",
        },
        headers={**_auth(token_a), **_tenant_header(tenant_a.id)},
    )
    assert create_resp.status_code == 201, create_resp.text

    # List categories as tenant B — should NOT see the category
    list_resp = await http_client.get(
        "/api/v1/content/categories",
        headers=_tenant_header(tenant_b.id),
    )
    assert list_resp.status_code == 200
    slugs = [c["slug"] for c in list_resp.json()["data"]]
    assert slug not in slugs, "Tenant B should not see tenant A's category"


@requires_db
@pytest.mark.asyncio
async def test_same_slug_allowed_for_different_tenants(
    http_client: AsyncClient,
    two_tenants,
    admin_token_for_tenant,
):
    """The same slug must be accepted for both tenants (tenant-scoped uniqueness)."""
    tenant_a, tenant_b = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)
    token_b = await admin_token_for_tenant(tenant_b.id)

    shared_slug = f"wrenches-{uuid.uuid4().hex[:6]}"

    resp_a = await http_client.post(
        "/api/v1/content/categories",
        json={"category_name": "Wrenches A", "slug": shared_slug, "locale": "en", "status": "draft"},
        headers={**_auth(token_a), **_tenant_header(tenant_a.id)},
    )
    assert resp_a.status_code == 201, f"Tenant A create failed: {resp_a.text}"

    resp_b = await http_client.post(
        "/api/v1/content/categories",
        json={"category_name": "Wrenches B", "slug": shared_slug, "locale": "en", "status": "draft"},
        headers={**_auth(token_b), **_tenant_header(tenant_b.id)},
    )
    assert resp_b.status_code == 201, (
        f"Tenant B should be able to reuse the same slug — got {resp_b.status_code}: {resp_b.text}"
    )


@requires_db
@pytest.mark.asyncio
async def test_duplicate_slug_rejected_within_same_tenant(
    http_client: AsyncClient,
    two_tenants,
    admin_token_for_tenant,
):
    """Creating the same slug twice under the same tenant must fail with 409/422."""
    tenant_a, _ = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)

    slug = f"pliers-{uuid.uuid4().hex[:6]}"
    payload = {"category_name": "Pliers", "slug": slug, "locale": "en", "status": "draft"}
    headers = {**_auth(token_a), **_tenant_header(tenant_a.id)}

    first  = await http_client.post("/api/v1/content/categories", json=payload, headers=headers)
    second = await http_client.post("/api/v1/content/categories", json=payload, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code in (409, 422), (
        f"Duplicate slug within same tenant should be rejected — got {second.status_code}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Auth cross-tenant boundary
# ─────────────────────────────────────────────────────────────────────────────

@requires_db
@pytest.mark.asyncio
async def test_admin_of_tenant_a_cannot_delete_tenant_b_category(
    http_client: AsyncClient,
    two_tenants,
    admin_token_for_tenant,
):
    """Tenant A's admin token must not be able to delete a category belonging to tenant B."""
    tenant_a, tenant_b = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)
    token_b = await admin_token_for_tenant(tenant_b.id)

    slug = f"sockets-{uuid.uuid4().hex[:6]}"

    # Create under tenant B
    create_resp = await http_client.post(
        "/api/v1/content/categories",
        json={"category_name": "Sockets", "slug": slug, "locale": "en", "status": "draft"},
        headers={**_auth(token_b), **_tenant_header(tenant_b.id)},
    )
    assert create_resp.status_code == 201
    cat_id = create_resp.json()["data"]["id"]

    # Try to delete with tenant A's token (no tenant header override — uses token_a's tenant)
    delete_resp = await http_client.delete(
        f"/api/v1/content/categories/{cat_id}",
        headers={**_auth(token_a), **_tenant_header(tenant_a.id)},
    )
    # Should be 403 (wrong tenant) or 404 (record not visible)
    assert delete_resp.status_code in (403, 404), (
        f"Cross-tenant delete should be blocked — got {delete_resp.status_code}: {delete_resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Public listing isolation (no auth)
# ─────────────────────────────────────────────────────────────────────────────

@requires_db
@pytest.mark.asyncio
async def test_public_category_list_scoped_by_tenant_header(
    http_client: AsyncClient,
    two_tenants,
    admin_token_for_tenant,
):
    """Public GET /categories (no auth) must respect the X-Tenant-ID header."""
    tenant_a, tenant_b = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)

    slug_a = f"pub-cat-{uuid.uuid4().hex[:6]}"
    create = await http_client.post(
        "/api/v1/content/categories",
        json={"category_name": "PubCat A", "slug": slug_a, "locale": "en", "status": "published"},
        headers={**_auth(token_a), **_tenant_header(tenant_a.id)},
    )
    assert create.status_code == 201, create.text

    # Request as tenant A — should see it
    resp_a = await http_client.get(
        "/api/v1/content/categories",
        headers=_tenant_header(tenant_a.id),
    )
    assert resp_a.status_code == 200
    slugs_a = [c["slug"] for c in resp_a.json()["data"]]
    assert slug_a in slugs_a

    # Request as tenant B — should NOT see it
    resp_b = await http_client.get(
        "/api/v1/content/categories",
        headers=_tenant_header(tenant_b.id),
    )
    assert resp_b.status_code == 200
    slugs_b = [c["slug"] for c in resp_b.json()["data"]]
    assert slug_a not in slugs_b


# ─────────────────────────────────────────────────────────────────────────────
# 4. Chat session isolation
# ─────────────────────────────────────────────────────────────────────────────

@requires_db
@pytest.mark.asyncio
async def test_chat_session_scoped_to_tenant(
    http_client: AsyncClient,
    two_tenants,
    admin_token_for_tenant,
):
    """Chat sessions created with tenant A header should not appear for tenant B admin."""
    tenant_a, tenant_b = two_tenants
    token_b = await admin_token_for_tenant(tenant_b.id)

    visitor_id = str(uuid.uuid4())
    tracking_session_id = str(uuid.uuid4())

    # The public page tracker may run before chat tenant resolution and create
    # global visitor/session rows. Chat should safely claim those NULL-tenant
    # rows instead of returning 409, while preserving cross-tenant isolation.
    tracking_resp = await http_client.post(
        "/api/v1/tracking/events",
        json={
            "event_name": "page_view",
            "visitor_id": visitor_id,
            "session_id": tracking_session_id,
            "page_url": "https://test.invalid/",
            "page_type": "home",
        },
    )
    assert tracking_resp.status_code in (200, 201, 202), tracking_resp.text

    # Create chat session under tenant A (public API, no auth required)
    create_resp = await http_client.post(
        "/api/v1/chat/sessions",
        json={
            "visitor_id": visitor_id,
            "session_id": tracking_session_id,
            "context_entity_type": "home",
            "context_entity_id": None,
        },
        headers=_tenant_header(tenant_a.id),
    )
    assert create_resp.status_code == 201, create_resp.text
    session_id = create_resp.json()["data"]["chat_session_id"]

    # Public mutation routes must enforce the same tenant boundary, even when
    # an attacker knows both the visitor and chat-session identifiers.
    message_resp = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"visitor_id": visitor_id, "content": "Send me a quote"},
        headers=_tenant_header(tenant_b.id),
    )
    assert message_resp.status_code == 404

    handoff_resp = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/handoff",
        json={
            "visitor_id": visitor_id,
            "intent_reason": "test",
            "prefill": {"message": "Send me a quote"},
        },
        headers=_tenant_header(tenant_b.id),
    )
    assert handoff_resp.status_code == 404

    # Tenant B admin should get 404 when fetching that session
    get_resp = await http_client.get(
        f"/api/v1/chat-admin/sessions/{session_id}",
        headers={**_auth(token_b), **_tenant_header(tenant_b.id)},
    )
    assert get_resp.status_code in (403, 404), (
        f"Chat session should not be accessible across tenants — got {get_resp.status_code}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. SiteProfile isolation
# ─────────────────────────────────────────────────────────────────────────────

@requires_db
@pytest.mark.asyncio
async def test_expired_certification_hidden_from_public_but_visible_to_admin(
    http_client: AsyncClient,
    two_tenants,
    admin_token_for_tenant,
):
    """Expired certifications remain editable but are not public trust signals."""
    tenant_a, _ = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)
    slug = f"expired-cert-{uuid.uuid4().hex[:6]}"

    create_resp = await http_client.post(
        "/api/v1/content/certifications",
        json={
            "cert_name": "Expired QA Certificate",
            "slug": slug,
            "expires_at": "2020-01-01T00:00:00Z",
            "locale": "en",
            "status": "published",
        },
        headers={**_auth(token_a), **_tenant_header(tenant_a.id)},
    )
    assert create_resp.status_code == 201, create_resp.text

    public_resp = await http_client.get(
        "/api/v1/content/certifications",
        headers=_tenant_header(tenant_a.id),
    )
    assert public_resp.status_code == 200, public_resp.text
    assert slug not in {item["slug"] for item in public_resp.json()["data"]}

    admin_resp = await http_client.get(
        "/api/v1/content/certifications",
        headers={**_auth(token_a), **_tenant_header(tenant_a.id)},
    )
    assert admin_resp.status_code == 200, admin_resp.text
    assert slug in {item["slug"] for item in admin_resp.json()["data"]}


@requires_db
@pytest.mark.asyncio
async def test_site_profile_scoped_to_tenant(
    http_client: AsyncClient,
    two_tenants,
    admin_token_for_tenant,
):
    """Each tenant's site profile must be independent."""
    tenant_a, tenant_b = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)
    token_b = await admin_token_for_tenant(tenant_b.id)

    # Upsert site profile for tenant A
    upsert_a = await http_client.put(
        "/api/v1/site-profile",
        json={"brand_name": "Alpha Tools", "site_url": "https://alphatools.test"},
        headers={**_auth(token_a), **_tenant_header(tenant_a.id)},
    )
    assert upsert_a.status_code in (200, 201), upsert_a.text

    # Get site profile as tenant B — should not see tenant A's brand
    get_b = await http_client.get(
        "/api/v1/site-profile",
        headers=_tenant_header(tenant_b.id),
    )
    if get_b.status_code == 200:
        brand = (get_b.json().get("data") or get_b.json()).get("brand_name", "")
        assert brand != "Alpha Tools", (
            f"Tenant B should not see tenant A's brand_name — got: {brand}"
        )
    else:
        # 404 is also acceptable (tenant B has no profile yet)
        assert get_b.status_code == 404
