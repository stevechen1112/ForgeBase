from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "configure_resend_inbound_readiness.py"
SPEC = importlib.util.spec_from_file_location("configure_resend_inbound_readiness", SCRIPT_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_verifies_domain_and_adds_inbound_event_without_removing_existing_events() -> None:
    calls = []
    webhook_reads = 0
    domain_reads = 0

    def request(method, path, payload=None):
        nonlocal domain_reads, webhook_reads
        calls.append((method, path, payload))
        if path == "/domains?limit=100":
            return {
                "data": [
                    {
                        "id": "domain-provider-id",
                        "name": "replies.premierbiz.com.tw",
                        "status": "not_started",
                        "capabilities": {"sending": "disabled", "receiving": "enabled"},
                    }
                ],
                "has_more": False,
            }
        if path == "/domains/domain-provider-id/verify":
            return {"id": "domain-provider-id"}
        if path == "/domains/domain-provider-id":
            domain_reads += 1
            return {
                "name": "replies.premierbiz.com.tw",
                "status": "not_started" if domain_reads == 1 else "verified",
                "capabilities": {"sending": "disabled", "receiving": "enabled"},
            }
        if path == "/webhooks?limit=100":
            webhook_reads += 1
            events = [
                "email.sent",
                "email.delivered",
                "email.bounced",
                "email.complained",
            ]
            if webhook_reads > 1:
                events.append("email.received")
            return {
                "data": [
                    {
                        "id": "webhook-provider-id",
                        "endpoint": "https://pcbrm.tw/api/v1/webhooks/resend/",
                        "status": "enabled",
                        "events": events,
                    }
                ],
                "has_more": False,
            }
        if path == "/webhooks/webhook-provider-id":
            return {"id": "webhook-provider-id"}
        raise AssertionError((method, path, payload))

    report = module.configure(
        api_key="configured",  # pragma: allowlist secret
        inbound_domain="Replies.PremierBiz.com.tw.",
        root_domain="premierbiz.com.tw",
        webhook_endpoint="https://pcbrm.tw/api/v1/webhooks/resend/",
        request=request,
        sleep=lambda _seconds: None,
    )

    assert report["assessment"]["status"] == "passed"
    assert report["operation"] == [
        "domain_verification_triggered",
        "webhook_events_aligned",
    ]
    webhook_patch = next(call for call in calls if call[:2] == ("PATCH", "/webhooks/webhook-provider-id"))
    assert set(webhook_patch[2]["events"]) == module.REQUIRED_OUTBOUND_EVENTS | {
        "email.received"
    }
    rendered = str(report)
    assert "provider-id" not in rendered
    assert "configured" not in rendered


def test_already_aligned_is_idempotent() -> None:
    def request(method, path, payload=None):
        assert method == "GET"
        if path == "/domains?limit=100":
            return {
                "data": [
                    {
                        "id": "domain-id",
                        "name": "replies.premierbiz.com.tw",
                        "status": "verified",
                        "capabilities": {"sending": "disabled", "receiving": "enabled"},
                    }
                ],
                "has_more": False,
            }
        if path == "/webhooks?limit=100":
            return {
                "data": [
                    {
                        "id": "webhook-id",
                        "endpoint": "https://pcbrm.tw/api/v1/webhooks/resend",
                        "status": "enabled",
                        "events": sorted(module.REQUIRED_OUTBOUND_EVENTS | {"email.received"}),
                    }
                ],
                "has_more": False,
            }
        if path == "/domains/domain-id":
            return {
                "name": "replies.premierbiz.com.tw",
                "status": "verified",
                "capabilities": {"sending": "disabled", "receiving": "enabled"},
            }
        raise AssertionError((method, path, payload))

    report = module.configure(
        api_key="configured",  # pragma: allowlist secret
        inbound_domain="replies.premierbiz.com.tw",
        root_domain="premierbiz.com.tw",
        webhook_endpoint="https://pcbrm.tw/api/v1/webhooks/resend",
        request=request,
    )

    assert report["operation"] == ["already_aligned"]
    assert report["assessment"]["status"] == "passed"


def test_reports_pending_domain_after_bounded_polling() -> None:
    reads = 0
    methods = []

    def request(method, path, payload=None):
        nonlocal reads
        methods.append((method, path))
        if path == "/domains?limit=100":
            return {
                "data": [
                    {
                        "id": "domain-id",
                        "name": "replies.premierbiz.com.tw",
                        "status": "pending",
                        "capabilities": {"sending": "disabled", "receiving": "enabled"},
                    }
                ],
                "has_more": False,
            }
        if path == "/domains/domain-id":
            reads += 1
            return {
                "name": "replies.premierbiz.com.tw",
                "status": "pending",
                "capabilities": {"sending": "disabled", "receiving": "enabled"},
            }
        if path == "/webhooks?limit=100":
            return {
                "data": [
                    {
                        "id": "webhook-id",
                        "endpoint": "https://pcbrm.tw/api/v1/webhooks/resend",
                        "status": "enabled",
                        "events": sorted(module.REQUIRED_OUTBOUND_EVENTS | {"email.received"}),
                    }
                ],
                "has_more": False,
            }
        raise AssertionError((method, path, payload))

    report = module.configure(
        api_key="configured",  # pragma: allowlist secret
        inbound_domain="replies.premierbiz.com.tw",
        root_domain="premierbiz.com.tw",
        webhook_endpoint="https://pcbrm.tw/api/v1/webhooks/resend",
        attempts=2,
        poll_seconds=0,
        request=request,
        sleep=lambda _seconds: None,
    )

    assert reads == 3
    assert ("POST", "/domains/domain-id/verify") not in methods
    assert report["assessment"]["status"] == "attention_required"
    assert report["assessment"]["blockers"] == ["inbound_domain_not_verified"]


def test_fails_closed_when_provider_does_not_apply_domain_capabilities() -> None:
    def request(method, path, payload=None):
        if path == "/domains?limit=100":
            return {
                "data": [
                    {
                        "id": "domain-id",
                        "name": "replies.premierbiz.com.tw",
                        "status": "verified",
                        "capabilities": {"sending": "enabled", "receiving": "disabled"},
                    }
                ],
                "has_more": False,
            }
        if path == "/domains/domain-id" and method == "PATCH":
            return {"id": "domain-id"}
        if path == "/domains/domain-id":
            return {
                "name": "replies.premierbiz.com.tw",
                "status": "verified",
                "capabilities": {"sending": "enabled", "receiving": "disabled"},
            }
        if path == "/webhooks?limit=100":
            return {
                "data": [
                    {
                        "id": "webhook-id",
                        "endpoint": "https://pcbrm.tw/api/v1/webhooks/resend",
                        "status": "enabled",
                        "events": sorted(module.REQUIRED_OUTBOUND_EVENTS | {"email.received"}),
                    }
                ],
                "has_more": False,
            }
        raise AssertionError((method, path, payload))

    report = module.configure(
        api_key="configured",  # pragma: allowlist secret
        inbound_domain="replies.premierbiz.com.tw",
        root_domain="premierbiz.com.tw",
        webhook_endpoint="https://pcbrm.tw/api/v1/webhooks/resend",
        request=request,
    )

    assert report["assessment"]["status"] == "attention_required"
    assert report["assessment"]["blockers"] == [
        "inbound_domain_capabilities_not_aligned"
    ]


@pytest.mark.parametrize(
    ("domain", "endpoint"),
    [
        ("premierbiz.com.tw", "https://pcbrm.tw/api/v1/webhooks/resend"),
        ("回覆.premierbiz.com.tw", "https://pcbrm.tw/api/v1/webhooks/resend"),
        ("replies.premierbiz.com.tw", "http://pcbrm.tw/api/v1/webhooks/resend"),
        ("replies.premierbiz.com.tw", "https://user:pass@pcbrm.tw/webhook"),
    ],
)
def test_rejects_unsafe_targets(domain, endpoint) -> None:
    with pytest.raises(ValueError):
        module.configure(
            api_key="configured",  # pragma: allowlist secret
            inbound_domain=domain,
            root_domain="premierbiz.com.tw",
            webhook_endpoint=endpoint,
            request=lambda *_args, **_kwargs: {},
        )
