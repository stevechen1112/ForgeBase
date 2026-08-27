from app.services.legacy_public_paths import rewrite_legacy_public_hrefs, rewrite_legacy_public_path


def test_rewrite_maps_stale_footer_paths_and_strips_locale_prefix():
    assert rewrite_legacy_public_path("/technical-docs") == "/docs"
    assert rewrite_legacy_public_path("/zh-TW/dealer-locator") == "/dealers"
    assert rewrite_legacy_public_path("/cookie-policy?ref=footer") == "/cookies?ref=footer"
    assert rewrite_legacy_public_path("/custom-solutions") == "/oem-odm"
    assert rewrite_legacy_public_path("/about") == "/about"
    assert rewrite_legacy_public_path("https://example.com/technical-docs") == "https://example.com/technical-docs"


def test_rewrite_walks_footer_json_hrefs():
    rewritten = rewrite_legacy_public_hrefs(
        [
            {
                "heading": "Support",
                "items": [
                    {"href": "/technical-docs", "label": "Docs"},
                    {"href": "/dealer-locator", "label": "Dealers"},
                    {"href": "/faq", "label": "FAQ"},
                ],
            }
        ]
    )
    hrefs = [item["href"] for item in rewritten[0]["items"]]
    assert hrefs == ["/docs", "/dealers", "/faq"]
