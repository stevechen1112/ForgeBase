"""
CF→FB Publish Contract 驗收測試（CF_FB_PUBLISH_CONTRACT.md §10）

涵蓋 Phase 2a FB 接收端：
- HTML sanitize（XSS payload 剝除）
- slug/locale/page_type 查詢（契約 §3 Phase 0 必測）
- meta-only endpoint（§4.3）
- Idempotency-Key 重送（§6）
- 跨租戶拒絕（§1）
- revalidate 路徑推導（§8）
"""
import uuid

import pytest

from tests.conftest import requires_db

from app.services.html_sanitize import sanitize_html
from app.services.revalidate import (
    TENANT_COPY_LAYOUT_PATHS,
    page_paths,
    revalidate_endpoints,
    revalidate_paths,
    revalidate_tenant_copy,
)


# ── Sanitizer 單元測試（免 DB）─────────────────────────────────────────────

def test_sanitize_strips_script_with_content():
    out = sanitize_html('<p>Hello</p><script>alert(1)</script>')
    assert "<p>Hello</p>" in out
    assert "script" not in out
    assert "alert" not in out


def test_sanitize_strips_event_handlers_and_style():
    out = sanitize_html('<p onclick="steal()" style="color:red">Text</p>')
    assert "onclick" not in out
    assert "style" not in out
    assert "Text" in out


def test_sanitize_strips_javascript_url():
    out = sanitize_html('<a href="javascript:alert(1)">x</a>')
    assert "javascript:" not in out


def test_sanitize_keeps_safe_links_and_images():
    out = sanitize_html(
        '<a href="https://example.com/a" target="_blank">link</a>'
        '<img src="https://cdn.example.com/x.jpg" alt="pic">'
    )
    assert 'href="https://example.com/a"' in out
    assert 'src="https://cdn.example.com/x.jpg"' in out


def test_sanitize_drops_iframe_but_keeps_text_of_unknown_tags():
    assert "iframe" not in sanitize_html('<iframe src="https://evil.example"></iframe>')
    out = sanitize_html('<custom-tag>keep me</custom-tag>')
    assert "keep me" in out
    assert "custom-tag" not in out


def test_sanitize_passthrough_empty():
    assert sanitize_html("") == ""
    assert sanitize_html(None) is None


# ── Revalidate 路徑推導（免 DB）────────────────────────────────────────────

def test_page_paths_default_locale():
    assert page_paths("my-article", "en") == ["/blog/my-article", "/blog"]


def test_page_paths_other_locale():
    paths = page_paths("my-article", "zh-TW")
    assert "/blog/my-article" in paths
    assert "/zh-TW/blog/my-article" in paths
    assert "/zh-TW/blog" in paths


@pytest.mark.asyncio
async def test_revalidate_skipped_when_url_unset(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "WEB_REVALIDATE_URL", "")
    monkeypatch.setattr(settings, "WEB_REVALIDATE_URLS", "")
    assert await revalidate_paths(["/blog/x"]) is False
    assert await revalidate_tenant_copy() is False


def test_revalidate_endpoints_split_urls(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "WEB_REVALIDATE_URL", "http://web/a")
    monkeypatch.setattr(settings, "WEB_REVALIDATE_URLS", "http://web/a, http://web-b/b")
    assert revalidate_endpoints() == ["http://web/a", "http://web-b/b"]


@pytest.mark.asyncio
async def test_revalidate_posts_to_every_frontend(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "WEB_REVALIDATE_URL", "http://web/a")
    monkeypatch.setattr(settings, "WEB_REVALIDATE_URLS", "http://web/a,http://web-b/b")
    monkeypatch.setattr(settings, "WEB_REVALIDATE_SECRET", "secret")
    seen: list[str] = []

    class FakeResp:
        status_code = 200
        text = "ok"

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json=None, headers=None):
            seen.append(url)
            return FakeResp()

    monkeypatch.setattr("app.services.revalidate.httpx.AsyncClient", FakeClient)
    assert await revalidate_paths(["/products"], ["/products"]) is True
    assert seen == ["http://web/a", "http://web-b/b"]


def test_tenant_copy_revalidate_covers_product_layouts():
    assert "/products" in TENANT_COPY_LAYOUT_PATHS
    assert "/zh-TW/products" in TENANT_COPY_LAYOUT_PATHS


# ── DB 整合測試 ─────────────────────────────────────────────────────────────

def _page_payload(slug: str, **overrides):
    payload = {
        "page_type": "blog_post",
        "slug": slug,
        "title": "Contract Test Page",
        "body": "<p>Body</p>",
        "locale": "en",
        "status": "draft",
    }
    payload.update(overrides)
    return payload


@requires_db
@pytest.mark.asyncio
async def test_page_create_sanitizes_body(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    headers = {"Authorization": f"Bearer {token}"}
    slug = f"xss-{uuid.uuid4().hex[:8]}"

    resp = await http_client.post(
        "/api/v1/content/pages",
        json=_page_payload(slug, body='<p>ok</p><script>alert(1)</script><a href="javascript:x()">l</a>'),
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]["body"]
    assert "script" not in body
    assert "javascript:" not in body
    assert "<p>ok</p>" in body


@requires_db
@pytest.mark.asyncio
async def test_slug_locale_page_type_query(http_client, two_tenants, admin_token_for_tenant):
    """契約 §3 Phase 0 必測：slug+locale+page_type 查詢（含 service-account tenant 覆寫）。"""
    tenant_a, tenant_b = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)
    slug = f"lookup-{uuid.uuid4().hex[:8]}"

    resp = await http_client.post(
        "/api/v1/content/pages",
        json=_page_payload(slug),
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 201, resp.text

    # 命中：三條件齊全
    resp = await http_client.get(
        f"/api/v1/content/pages?slug={slug}&locale=en&page_type=blog_post",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["slug"] == slug

    # locale 不符 → 空
    resp = await http_client.get(
        f"/api/v1/content/pages?slug={slug}&locale=ja&page_type=blog_post",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.json()["data"] == []

    # 他租戶查不到（tenant 隔離）
    token_b = await admin_token_for_tenant(tenant_b.id)
    resp = await http_client.get(
        f"/api/v1/content/pages?slug={slug}&locale=en&page_type=blog_post",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.json()["data"] == []


@requires_db
@pytest.mark.asyncio
async def test_meta_only_endpoint(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    headers = {"Authorization": f"Bearer {token}"}
    slug = f"meta-{uuid.uuid4().hex[:8]}"

    resp = await http_client.post("/api/v1/content/pages", json=_page_payload(slug), headers=headers)
    page = resp.json()["data"]
    page_id = page["id"]
    original_body = page["body"]

    # 合法 meta 更新
    resp = await http_client.patch(
        f"/api/v1/content/pages/{page_id}/meta",
        json={"seo_title": "New Title", "seo_description": "New desc"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["seo_title"] == "New Title"
    assert data["body"] == original_body  # meta 路徑不得改 body

    # 夾帶 body/slug → 422（extra=forbid）
    resp = await http_client.patch(
        f"/api/v1/content/pages/{page_id}/meta",
        json={"seo_title": "X", "body": "<p>hack</p>"},
        headers=headers,
    )
    assert resp.status_code == 422

    # 空 payload → 422
    resp = await http_client.patch(
        f"/api/v1/content/pages/{page_id}/meta", json={}, headers=headers
    )
    assert resp.status_code == 422


@requires_db
@pytest.mark.asyncio
async def test_idempotency_key_replay(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": f"cf-article-{uuid.uuid4()}"}
    slug = f"idem-{uuid.uuid4().hex[:8]}"

    first = await http_client.post("/api/v1/content/pages", json=_page_payload(slug), headers=headers)
    assert first.status_code == 201, first.text
    first_id = first.json()["data"]["id"]

    # 同 key 重送 → 回傳首次結果，不建新頁
    second = await http_client.post("/api/v1/content/pages", json=_page_payload(slug), headers=headers)
    assert second.json()["data"]["id"] == first_id

    resp = await http_client.get(
        f"/api/v1/content/pages?slug={slug}", headers={"Authorization": f"Bearer {token}"}
    )
    assert len(resp.json()["data"]) == 1


@requires_db
@pytest.mark.asyncio
async def test_cross_tenant_publish_and_meta_denied(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, tenant_b = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)
    token_b = await admin_token_for_tenant(tenant_b.id)

    resp = await http_client.post(
        "/api/v1/content/pages",
        json=_page_payload(f"xtenant-{uuid.uuid4().hex[:8]}"),
        headers={"Authorization": f"Bearer {token_a}"},
    )
    page_id = resp.json()["data"]["id"]

    # B tenant 嘗試 publish A 的 page → 404
    resp = await http_client.post(
        f"/api/v1/content/pages/{page_id}/publish",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404

    # B tenant 嘗試 meta 更新 A 的 page → 404
    resp = await http_client.patch(
        f"/api/v1/content/pages/{page_id}/meta",
        json={"seo_title": "hijack"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404
