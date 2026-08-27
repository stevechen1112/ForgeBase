from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.locale_draft import _require_content_editor_role
from app.core.locale import locale_catalog_payload, to_content_locale, to_route_locale
from app.services.locale_support import (
    buyer_locales,
    contains_cjk,
    default_buyer_locale,
    is_stale,
    profile_to_content_locale,
)
from tests.conftest import requires_db


def test_source_locale_helpers():
    assert profile_to_content_locale("zh-TW") == "zh-tw"
    assert default_buyer_locale("zh-tw") == "en"
    assert buyer_locales("en") == ("zh-tw", "ja", "fr", "ru")
    assert to_content_locale("ja-JP", default="") == ""
    assert to_content_locale("ja") == "ja"
    assert to_route_locale("zh-tw") == "zh-TW"
    assert {row["content_locale"] for row in locale_catalog_payload()} == {"en", "zh-tw", "ja", "fr", "ru"}
    assert {row["content_locale"] for row in locale_catalog_payload() if row["public_shell_ready"]} == {"en", "zh-tw"}
    assert contains_cjk("工業扭力扳手")
    assert not contains_cjk("Torque wrench")


def test_locale_draft_rejects_sales_role():
    with pytest.raises(HTTPException) as exc_info:
        _require_content_editor_role(SimpleNamespace(role="sales"))
    assert getattr(exc_info.value, "status_code", None) == 403


def test_stale_requires_later_source_publish():
    from datetime import datetime, timedelta

    older = datetime(2026, 8, 1, 10, 0, 0)
    newer = older + timedelta(hours=2)
    source = SimpleNamespace(status="published", published_at=newer, updated_at=newer)
    target = SimpleNamespace(status="published", published_at=older, updated_at=older)
    assert is_stale(source, target)
    source_draft = SimpleNamespace(status="draft", published_at=newer, updated_at=newer)
    assert not is_stale(source_draft, target)


@requires_db
@pytest.mark.asyncio
async def test_locale_draft_creates_unpublished_english_and_does_not_overwrite_published(
    http_client, two_tenants, admin_token_for_tenant
):
    tenant, starter = two_tenants
    token = await admin_token_for_tenant(tenant.id)
    starter_token = await admin_token_for_tenant(starter.id)
    headers = {"Authorization": f"Bearer {token}"}

    category = await http_client.post(
        "/api/v1/content/categories",
        json={
            "category_name": "扭力工具",
            "slug": "torque-tools-draft",
            "locale": "zh-tw",
            "status": "published",
        },
        headers=headers,
    )
    assert category.status_code == 201, category.text
    category_id = category.json()["data"]["id"]

    product = await http_client.post(
        "/api/v1/content/products",
        json={
            "product_name": "工業扭力扳手",
            "slug": "industrial-torque-wrench-draft",
            "model_number": "NF-TWD-100",
            "short_description": "適用於工業組裝的扭力扳手。",
            "full_description": "提供可追溯的扭力控制。",
            "specifications": '[{"name":"Drive","value":"1/2","unit":"in"}]',
            "category_id": category_id,
            "locale": "zh-tw",
            "status": "published",
        },
        headers=headers,
    )
    assert product.status_code == 201, product.text
    product_id = product.json()["data"]["id"]

    denied = await http_client.post(
        f"/api/v1/content/products/{product_id}/locale-draft",
        json={"target_locale": "en"},
        headers={"Authorization": f"Bearer {starter_token}"},
    )
    assert denied.status_code in {403, 404}

    class _Choice:
        def __init__(self):
            self.message = SimpleNamespace(
                content='{"product_name":"Industrial Torque Wrench","short_description":"A torque wrench for industrial assembly.","full_description":"Provides traceable torque control.","seo_title":"Industrial Torque Wrench","seo_description":"Industrial torque wrench.","image_alt":"Torque wrench"}'
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(choices=[_Choice()]))))
    )

    with patch("app.services.translation_draft.get_openai_client", return_value=fake_client), patch(
        "app.services.translation_draft.settings.OPENAI_API_KEY",
        "test-key",
    ):
        drafted = await http_client.post(
            f"/api/v1/content/products/{product_id}/locale-draft",
            json={"target_locale": "en"},
            headers=headers,
        )
    assert drafted.status_code == 200, drafted.text
    body = drafted.json()
    assert body["status"] == "draft"
    target_id = body["target_id"]

    fetched = await http_client.get(f"/api/v1/content/products/{target_id}", headers=headers)
    assert fetched.status_code == 200, fetched.text
    row = fetched.json()["data"]
    assert row["locale"] == "en"
    assert row["status"] == "draft"
    assert row["model_number"] == "NF-TWD-100"
    assert row["product_name"] == "Industrial Torque Wrench"
    assert "1/2" in (row.get("specifications") or "")

    cjk_publish = await http_client.post(
        f"/api/v1/content/products/{target_id}/publish",
        headers=headers,
    )
    # English copy has no CJK, so publish is allowed after draft.
    assert cjk_publish.status_code == 200, cjk_publish.text

    with patch("app.services.translation_draft.get_openai_client", return_value=fake_client), patch(
        "app.services.translation_draft.settings.OPENAI_API_KEY",
        "test-key",
    ):
        blocked = await http_client.post(
            f"/api/v1/content/products/{product_id}/locale-draft",
            json={"target_locale": "en"},
            headers=headers,
        )
    assert blocked.status_code == 409, blocked.text


@requires_db
@pytest.mark.asyncio
async def test_publish_rejects_english_copy_that_still_contains_chinese(
    http_client, two_tenants, admin_token_for_tenant
):
    tenant, _ = two_tenants
    token = await admin_token_for_tenant(tenant.id)
    headers = {"Authorization": f"Bearer {token}"}
    category = await http_client.post(
        "/api/v1/content/categories",
        json={"category_name": "Tools", "slug": "tools-cjk", "locale": "en", "status": "published"},
        headers=headers,
    )
    assert category.status_code == 201, category.text
    product = await http_client.post(
        "/api/v1/content/products",
        json={
            "product_name": "工業扭力扳手",
            "slug": "cjk-english-product",
            "model_number": "NF-CJK-1",
            "short_description": "中文說明不應出現在英文頁。",
            "category_id": category.json()["data"]["id"],
            "locale": "en",
            "status": "draft",
        },
        headers=headers,
    )
    assert product.status_code == 201, product.text
    published = await http_client.post(
        f"/api/v1/content/products/{product.json()['data']['id']}/publish",
        headers=headers,
    )
    assert published.status_code == 422


@requires_db
@pytest.mark.asyncio
async def test_locale_batch_creates_bounded_french_drafts_without_publishing(
    http_client, two_tenants, admin_token_for_tenant
):
    tenant, _ = two_tenants
    token = await admin_token_for_tenant(tenant.id)
    headers = {"Authorization": f"Bearer {token}"}
    source_ids = []
    for index in range(2):
        page = await http_client.post(
            "/api/v1/content/pages",
            json={
                "title": f"來源頁面 {index}",
                "slug": f"batch-locale-page-{index}",
                "page_type": "custom",
                "body": "這是經核准的來源內容。",
                "locale": "zh-tw",
                "status": "published",
            },
            headers=headers,
        )
        assert page.status_code == 201, page.text
        source_ids.append(page.json()["data"]["id"])

    class _Choice:
        def __init__(self):
            self.message = SimpleNamespace(
                content='{"title":"Page source","body":"Contenu source approuvé."}'
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(choices=[_Choice()]))))
    )
    with patch("app.services.translation_draft.get_openai_client", return_value=fake_client), patch(
        "app.services.translation_draft.settings.OPENAI_API_KEY", "test-key"
    ):
        response = await http_client.post(
            "/api/v1/content/locale-drafts/batch",
            json={"entity": "pages", "source_ids": source_ids, "target_locale": "fr"},
            headers=headers,
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["requested"] == 2
    assert payload["created_or_updated"] == 2
    assert payload["failed"] == 0
    assert payload["published"] == 0
    for result in payload["results"]:
        drafted = await http_client.get(
            f"/api/v1/content/pages/{result['target_id']}", headers=headers
        )
        assert drafted.status_code == 200
        assert drafted.json()["data"]["locale"] == "fr"
        assert drafted.json()["data"]["status"] == "draft"

    settings = await http_client.get("/api/v1/content/locale-settings", headers=headers)
    assert settings.status_code == 200
    french = next(row for row in settings.json()["content_locales"] if row["content_locale"] == "fr")
    assert french["public_shell_ready"] is False
    coverage = await http_client.get(
        "/api/v1/content/locale-coverage?target_locale=fr", headers=headers
    )
    assert coverage.status_code == 200, coverage.text
    pages = next(row for row in coverage.json()["entities"] if row["entity"] == "pages")
    assert "missing_ids" in pages
    assert coverage.json()["target_locale"] == "fr"
