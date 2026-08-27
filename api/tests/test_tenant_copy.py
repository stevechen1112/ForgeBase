import pytest

from tests.conftest import requires_db
from app.services.tenant_copy import (
    apply_assets,
    apply_copy_overlay,
    apply_hidden_blocks,
    extract_locale_overlay,
    public_site_copy_overlay,
    serialize_overlay,
)


def test_locale_overlay_does_not_leak_control_keys():
    site_copy = {
        "home": {"hero": {"titleLine1": "Legacy title"}},
        "locales": {"en": {"home": {"hero": {"titleLine1": "English title"}}}},
        "hiddenBlocks": {"productInspection": True},
    }
    overlay = public_site_copy_overlay(site_copy, "en")
    assert overlay["home"]["hero"]["titleLine1"] == "English title"
    assert "hiddenBlocks" not in overlay
    assert "locales" not in overlay


def test_apply_copy_keeps_other_locale_and_strips_empty():
    existing = {"locales": {"zh-TW": {"home": {"hero": {"titleLine1": "繁中"}}}}}
    updated = apply_copy_overlay(
        existing,
        "en",
        {"home": {"hero": {"titleLine1": "  English  ", "titleLine2": ""}}},
    )
    en_overlay = extract_locale_overlay(updated, "en")
    assert en_overlay["home"]["hero"]["titleLine1"] == "English"
    assert "titleLine2" not in en_overlay["home"]["hero"]
    assert extract_locale_overlay(updated, "zh-TW")["home"]["hero"]["titleLine1"] == "繁中"


def test_public_locale_overlays_are_isolated_without_cross_language_fallback():
    existing = {
        "locales": {
            "zh-tw": {"home": {"hero": {"titleLine1": "繁中"}}},
            "ja": {"home": {"hero": {"titleLine1": "日本語"}}},
            "fr": {"home": {"hero": {"titleLine1": "Français"}}},
            "ru": {"home": {"hero": {"titleLine1": "Русский"}}},
        }
    }
    assert extract_locale_overlay(existing, "zh-TW")["home"]["hero"]["titleLine1"] == "繁中"
    for locale, expected in (("ja", "日本語"), ("fr", "Français"), ("ru", "Русский")):
        assert extract_locale_overlay(existing, locale)["home"]["hero"]["titleLine1"] == expected
    assert extract_locale_overlay(existing, "en") == {}


def test_news_empty_list_hides_default_items():
    updated = apply_copy_overlay({}, "en", {"newsPage": {"items": []}})
    assert serialize_overlay(extract_locale_overlay(updated, "en"))["newsPage"]["items"] == []


def test_apply_copy_does_not_clear_news_when_omitted():
    existing = {
        "locales": {
            "en": {"newsPage": {"items": [{"date": "2026", "title": "Keep", "summary": "Stay"}]}}
        }
    }
    updated = apply_copy_overlay(existing, "en", {"home": {"hero": {"titleLine1": "Hi"}}})
    assert extract_locale_overlay(updated, "en")["newsPage"]["items"][0]["title"] == "Keep"


def test_hidden_blocks_and_assets_whitelist():
    site_copy = apply_hidden_blocks({}, {"productInspection": True, "ignored": True})
    assert site_copy["hiddenBlocks"]["productInspection"] is True
    assert "ignored" not in site_copy["hiddenBlocks"]
    manifest = apply_assets({"productByKey": {"A": "/a.png"}}, {"homeHero": "https://cdn.example/hero.webp", "evil": "no"})
    assert manifest["homeHero"] == "https://cdn.example/hero.webp"
    assert manifest["productByKey"]["A"] == "/a.png"
    assert "evil" not in manifest


@requires_db
@pytest.mark.asyncio
async def test_tenant_can_edit_logo_and_whitelisted_copy(
    http_client,
    two_tenants,
    admin_token_for_tenant,
):
    tenant_a, tenant_b = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_a.id)}

    logo = await http_client.put(
        "/api/v1/site-profile",
        json={"logo_url": "https://cdn.example/logo.webp"},
        headers=headers,
    )
    assert logo.status_code == 200, logo.text
    assert logo.json()["logo_url"] == "https://cdn.example/logo.webp"

    source_locale = await http_client.put(
        "/api/v1/site-profile",
        json={"default_locale": "ja"},
        headers=headers,
    )
    assert source_locale.status_code == 200, source_locale.text
    assert source_locale.json()["default_locale"] == "ja"

    saved = await http_client.put(
        "/api/v1/site-profile/tenant-copy",
        json={
            "locale": "fr",
            "copy": {"home": {"hero": {"titleLine1": "Custom hero"}}},
            "assets": {"homeHero": "https://cdn.example/hero.webp"},
            "hidden_blocks": {"productInspection": True},
            "logo_url": "https://cdn.example/from-copy.webp",
        },
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["locale"] == "fr"
    assert saved.json()["copy"]["home"]["hero"]["titleLine1"] == "Custom hero"
    assert saved.json()["hidden_blocks"]["productInspection"] is True
    assert saved.json()["logo_url"] == "https://cdn.example/from-copy.webp"

    other = await http_client.get(
        "/api/v1/site-profile/tenant-copy",
        headers={"Authorization": f"Bearer {await admin_token_for_tenant(tenant_b.id)}", "X-Tenant-ID": str(tenant_b.id)},
    )
    assert other.status_code == 200
    assert other.json()["copy"].get("home", {}).get("hero", {}).get("titleLine1") != "Custom hero"
