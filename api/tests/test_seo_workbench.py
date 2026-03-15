from app.services.seo_workbench import audit_entity_payload, build_entity_path


def test_audit_entity_payload_flags_missing_seo_fields():
    result = audit_entity_payload(
        "product",
        {
            "product_name": "Hydraulic Seal Kit",
            "model_number": "HSK-200",
            "slug": "hydraulic-seal-kit",
            "short_description": "Industrial sealing solution",
            "full_description": "",
            "seo_title": "",
            "seo_description": "",
            "category_slug": "seals",
        },
    )

    assert result["status"] in {"needs-work", "critical"}
    assert any(check["id"] == "seo_title" and check["status"] == "critical" for check in result["checks"])
    assert any(suggestion.get("field") == "seo_title" for suggestion in result["suggestions"])
    assert result["recommended"]["seo_title"]
    assert result["recommended"]["seo_description"]


def test_build_entity_path_handles_locale_and_product_paths():
    url = build_entity_path(
        "product",
        {
            "slug": "hsk-200",
            "category_slug": "seals",
            "locale": "zh-tw",
        },
        site_url="https://example.com",
    )

    assert url == "https://example.com/zh-tw/products/seals/hsk-200"