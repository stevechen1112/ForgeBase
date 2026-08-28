from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "audit_resend_account.py"
SPEC = importlib.util.spec_from_file_location("audit_resend_account", SCRIPT_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def _getter(responses):
    calls = []

    def get_json(path):
        calls.append(path)
        for prefix, payload in responses.items():
            if path.startswith(prefix):
                return payload
        raise AssertionError(f"unexpected path: {path}")

    return get_json, calls


def test_reports_verified_sender_and_complete_webhook_without_secrets() -> None:
    get_json, calls = _getter(
        {
            "/domains": {
                "data": [
                    {
                        "id": "domain-provider-id",
                        "name": "premierbiz.com.tw",
                        "status": "verified",
                        "region": "ap-northeast-1",
                        "capabilities": {
                            "sending": "enabled",
                            "receiving": "disabled",
                        },
                        "records": [{"value": "sensitive-dkim-value"}],
                    },
                    {
                        "id": "other-domain-id",
                        "name": "private-tenant.example",
                        "status": "verified",
                        "capabilities": {"sending": "enabled"},
                    }
                ],
                "has_more": False,
            },
            "/webhooks": {
                "data": [
                    {
                        "id": "webhook-provider-id",
                        "endpoint": "https://pcbrm.tw/api/v1/webhooks/resend/",
                        "status": "enabled",
                        "events": [
                            "email.sent",
                            "email.delivered",
                            "email.bounced",
                            "email.complained",
                            "email.received",
                        ],
                        "signing_secret": "fixture-redacted",  # pragma: allowlist secret
                    },
                    {
                        "id": "other-id",
                        "endpoint": "https://hooks.example.com/private-route?opaque=value",
                        "status": "enabled",
                        "events": ["email.sent"],
                    }
                ],
                "has_more": False,
            },
        }
    )

    report = module.build_report(
        api_key="configured",
        expected_sending_domain="PremierBiz.com.tw.",
        expected_webhook_endpoint="https://pcbrm.tw/api/v1/webhooks/resend/",
        get_json=get_json,
    )
    rendered = str(report)

    assert report["assessment"]["status"] == "passed"
    assert report["assessment"]["sending_domain_ready"] is True
    assert report["assessment"]["outbound_webhook_ready"] is True
    assert report["assessment"]["inbound_webhook_ready"] is True
    assert all("limit=100" in call for call in calls)
    assert "configured" not in rendered
    assert "sensitive-dkim-value" not in rendered
    assert "provider-id" not in rendered
    assert "fixture-redacted" not in rendered
    assert "private-route" not in rendered
    assert "private-tenant.example" not in rendered
    assert report["domains"]["total_count"] == 2
    assert report["domains"]["nonmatching_count"] == 1
    assert report["webhooks"]["total_count"] == 2
    assert report["webhooks"]["nonmatching_count"] == 1


def test_reports_specific_readiness_gaps() -> None:
    get_json, _ = _getter(
        {
            "/domains": {
                "data": [
                    {
                        "name": "premierbiz.com.tw",
                        "status": "pending",
                        "capabilities": {"sending": "enabled"},
                    }
                ],
                "has_more": False,
            },
            "/webhooks": {
                "data": [
                    {
                        "endpoint": "https://pcbrm.tw/api/v1/webhooks/resend",
                        "status": "enabled",
                        "events": ["email.sent"],
                    }
                ],
                "has_more": False,
            },
        }
    )

    report = module.build_report(
        api_key="configured",
        expected_sending_domain="premierbiz.com.tw",
        expected_webhook_endpoint="https://pcbrm.tw/api/v1/webhooks/resend",
        get_json=get_json,
    )

    assert report["assessment"]["status"] == "attention_required"
    assert report["assessment"]["blockers"] == [
        "sending_domain_not_ready",
        "outbound_webhook_events_incomplete",
    ]
    assert report["assessment"]["missing_outbound_events"] == [
        "email.bounced",
        "email.complained",
        "email.delivered",
    ]


def test_follows_bounded_pagination() -> None:
    pages = iter(
        [
            {"data": [{"id": "first", "name": "one.example"}], "has_more": True},
            {"data": [{"id": "second", "name": "two.example"}], "has_more": False},
        ]
    )
    calls = []

    def get_json(path):
        calls.append(path)
        return next(pages)

    rows = module._list_all("/domains", get_json)

    assert len(rows) == 2
    assert calls == ["/domains?limit=100", "/domains?limit=100&after=first"]


def test_provider_client_does_not_follow_redirects(monkeypatch) -> None:
    observed = {"requests": 0, "closed": False}

    class FakeResponse:
        status = 302

    class FakeConnection:
        def __init__(self, host, timeout):
            assert host == "api.resend.com"
            assert timeout == 15

        def request(self, method, path, headers):
            observed["requests"] += 1
            assert method == "GET"
            assert path == "/domains?limit=100"
            assert headers["Authorization"].startswith("Bearer ")

        def getresponse(self):
            return FakeResponse()

        def close(self):
            observed["closed"] = True

    monkeypatch.setattr(module.http.client, "HTTPSConnection", FakeConnection)

    with pytest.raises(module.ResendAuditError, match="HTTP 302"):
        module._provider_get("configured", "/domains?limit=100")

    assert observed == {"requests": 1, "closed": True}


@pytest.mark.parametrize(
    ("domain", "endpoint"),
    [
        ("localhost", "https://pcbrm.tw/api/v1/webhooks/resend"),
        ("回覆.example.com", "https://pcbrm.tw/api/v1/webhooks/resend"),
        ("premierbiz.com.tw", "http://pcbrm.tw/api/v1/webhooks/resend"),
        ("premierbiz.com.tw", "https://user:" + "pass@pcbrm.tw/webhook"),
        ("premierbiz.com.tw", "https://pcbrm.tw:8443/webhook"),
    ],
)
def test_rejects_unsafe_expectations(domain, endpoint) -> None:
    with pytest.raises(ValueError):
        module.build_report(
            api_key="configured",
            expected_sending_domain=domain,
            expected_webhook_endpoint=endpoint,
            get_json=lambda _path: {"data": [], "has_more": False},
        )
