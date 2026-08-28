from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "provision_resend_inbound_domain.py"
SPEC = importlib.util.spec_from_file_location("provision_resend_inbound_domain", SCRIPT_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_creates_receiving_only_subdomain_and_returns_dns_records() -> None:
    calls = []

    def request(method, path, payload=None):
        calls.append((method, path, payload))
        if path == "/domains?limit=100":
            return {"data": []}
        if method == "POST":
            return {
                "id": "domain-id",
                "name": "replies.premierbiz.com.tw",
                "capabilities": {"sending": "disabled", "receiving": "enabled"},
            }
        return {
            "name": "replies.premierbiz.com.tw",
            "status": "not_started",
            "capabilities": {"sending": "disabled", "receiving": "enabled"},
            "records": [
                {
                    "record": "Receiving",
                    "type": "MX",
                    "name": "replies",
                    "value": "inbound-smtp.example.net",
                    "priority": 10,
                    "status": "not_started",
                }
            ],
        }

    report = module.provision(
        api_key="configured",  # pragma: allowlist secret
        inbound_domain="Replies.PremierBiz.com.tw.",
        request=request,
    )

    assert report["operation"] == "created"
    assert report["assessment"]["ready_for_dns_configuration"] is True
    assert report["dns_records"][0]["type"] == "MX"
    assert calls[1][2]["capabilities"] == {
        "sending": "disabled",
        "receiving": "enabled",
    }
    assert "domain-id" not in str(report)


def test_updates_existing_domain_capabilities() -> None:
    calls = []

    def request(method, path, payload=None):
        calls.append((method, path, payload))
        if path == "/domains?limit=100":
            return {
                "data": [
                    {
                        "id": "domain-id",
                        "name": "replies.premierbiz.com.tw",
                        "capabilities": {"sending": "enabled", "receiving": "disabled"},
                    }
                ]
            }
        if method == "PATCH":
            return {"id": "domain-id"}
        return {
            "name": "replies.premierbiz.com.tw",
            "status": "pending",
            "capabilities": {"sending": "disabled", "receiving": "enabled"},
            "records": [
                {"record": "Receiving", "type": "MX", "name": "replies", "value": "mx.example.net"}
            ],
        }

    report = module.provision(
        api_key="configured",  # pragma: allowlist secret
        inbound_domain="replies.premierbiz.com.tw",
        request=request,
    )

    assert report["operation"] == "updated"
    assert any(method == "PATCH" for method, _path, _payload in calls)


@pytest.mark.parametrize("domain", ["premierbiz.com.tw", "localhost", "回覆.example.com"])
def test_rejects_non_subdomains(domain) -> None:
    with pytest.raises(ValueError, match="valid subdomain"):
        module.provision(
            api_key="configured",  # pragma: allowlist secret
            inbound_domain=domain,
            request=lambda *_args, **_kwargs: {},
        )
