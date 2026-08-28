from app.services.platform_data_quality import synthetic_signals


def test_synthetic_signals_are_explainable_and_do_not_classify_real_domains() -> None:
    assert synthetic_signals(
        {"email": "buyer@example.com", "company_name": "Demo Company"},
        "smoke-123",
    ) == ["test_run_id_present", "reserved_email_domain", "synthetic_name_marker"]
    assert synthetic_signals(
        {"contact_email": "buyer@manufacturer.tw", "company_name": "Precision Works"},
        None,
    ) == []


def test_synthetic_signals_tolerate_invalid_legacy_payloads() -> None:
    assert synthetic_signals("not-json", None) == []
    assert synthetic_signals([], None) == []
