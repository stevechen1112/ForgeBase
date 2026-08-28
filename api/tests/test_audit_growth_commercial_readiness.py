import json
from types import SimpleNamespace

from scripts.audit_growth_commercial_readiness import (
    evaluate_report,
    tenant_policy_snapshot,
    transport_snapshot,
)


def _config(**overrides):
    values = {
        "EMAIL_FROM": "sales@example.com",
        "RESEND_API_KEY": "resend-sensitive-value",  # pragma: allowlist secret
        "RESEND_WEBHOOK_SECRET": "webhook-sensitive-value",  # pragma: allowlist secret
        "OUTREACH_PUBLIC_BASE_URL": "https://api.example.test",
        "OUTREACH_UNSUBSCRIBE_SECRET": "unsubscribe-sensitive-value",  # pragma: allowlist secret
        "OUTREACH_INBOUND_DOMAIN": "reply.example.test",
        "OUTREACH_INBOUND_SECRET": "inbound-sensitive-value",  # pragma: allowlist secret
        "ESP_PROVIDER": "resend",
        "EMAIL_DRY_RUN": False,
        "EMAIL_EXTERNAL_DELIVERY_ENABLED": False,
        "OUTREACH_SEND_ENABLED": False,
        "INBOUND_REPLY_ENABLED": False,
        "EMAIL_INTERNAL_RECIPIENT_ALLOWLIST": "ops@example.test",
        "SALES_NOTIFY_EMAIL": "sales@example.test",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _tenant_row(**overrides):
    row = {
        "slug": "default-tenant",
        "active": True,
        "company_identification": {
            "persisted": True,
            "mode": "shadow",
            "provider": "pdl_ip",
        },
        "contact_enrichment": {
            "persisted": False,
            "mode": "off",
            "provider": None,
            "verification_provider": None,
        },
        "outreach_drafts": {"persisted": False, "mode": "off"},
        "outreach_delivery": {
            "persisted": False,
            "mode": "off",
            "provider": None,
            "controlled_auto_opt_in": False,
            "controlled_auto_legal_approved": False,
        },
    }
    row.update(overrides)
    return row


def _report(transport, tenants):
    report = {
        "providers": {
            "company_identification": ["pdl_ip"],
            "contact_search": ["hunter_domain"],
            "email_verification": ["hunter"],
        },
        "transport": transport,
        "tenants": tenants,
    }
    report["assessment"] = evaluate_report(report)
    return report


def test_transport_snapshot_never_exposes_credentials_or_addresses():
    snapshot = transport_snapshot(_config(EMAIL_FROM="team@forgebase.test"))
    rendered = json.dumps(snapshot)

    assert snapshot["outbound_prerequisites_ready"] is True
    assert snapshot["inbound_prerequisites_ready"] is True
    assert "sensitive-value" not in rendered
    assert "team@forgebase.test" not in rendered
    assert "ops@example.test" not in rendered
    assert "sales@example.test" not in rendered


def test_guarded_production_state_passes_without_claiming_send_readiness():
    report = _report(
        transport_snapshot(_config(EMAIL_FROM="team@forgebase.test")),
        [_tenant_row()],
    )
    assessment = report["assessment"]

    assert assessment["status"] == "passed"
    assert assessment["safe_guardrails_engaged"] is True
    assert assessment["configuration_ready_for_approval_send"] is False
    assert assessment["configuration_ready_for_reply_loop"] is False
    assert assessment["automatic_outreach_enabled"] is False
    assert "no_review_only_contact_tenant" in assessment["activation_blockers"]
    assert "no_approval_send_tenant" in assessment["activation_blockers"]
    assert "external_delivery_kill_switch_closed" in assessment["activation_blockers"]
    assert "inbound_reply_kill_switch_closed" in assessment[
        "reply_activation_blockers"
    ]


def test_production_registry_rejects_any_mock_adapter():
    report = _report(
        transport_snapshot(_config()),
        [_tenant_row()],
    )
    report["providers"]["company_identification"].append("mock")
    report["providers"]["contact_search"].append("mock")
    report["providers"]["email_verification"].append("mock")

    assessment = evaluate_report(report)

    assert assessment["status"] == "failed"
    assert "production_company_registry_exposes_mock" in assessment["violations"]
    assert "production_contact_registry_exposes_mock" in assessment["violations"]
    assert "production_verification_registry_exposes_mock" in assessment["violations"]


def test_unsafe_provider_and_switch_drift_fails_closed():
    transport = transport_snapshot(
        _config(
            EMAIL_FROM="noreply@example.com",
            OUTREACH_SEND_ENABLED=True,
            EMAIL_EXTERNAL_DELIVERY_ENABLED=False,
            INBOUND_REPLY_ENABLED=True,
            OUTREACH_INBOUND_SECRET="",
        )
    )
    contact_policy = {
        "persisted": True,
        "mode": "review_only",
        "provider": "mock",
        "verification_provider": "mock",
    }
    delivery_policy = {
        "persisted": True,
        "mode": "approval_send",
        "provider": "resend",
        "controlled_auto_opt_in": True,
        "controlled_auto_legal_approved": True,
    }
    report = _report(
        transport,
        [
            _tenant_row(
                contact_enrichment=contact_policy,
                outreach_delivery=delivery_policy,
            )
        ],
    )

    violations = report["assessment"]["violations"]
    assert report["assessment"]["status"] == "failed"
    assert "default-tenant:contact_provider_unavailable" in violations
    assert "default-tenant:verification_provider_unavailable" in violations
    assert "default-tenant:production_contact_policy_uses_mock" in violations
    assert "controlled_auto_is_not_authorized" in violations
    assert "outreach_send_enabled_without_external_delivery" in violations
    assert "inbound_enabled_without_required_configuration" in violations


def test_reply_loop_readiness_is_independent_from_outbound_send_readiness():
    transport = transport_snapshot(
        _config(
            EMAIL_FROM="team@forgebase.test",
            INBOUND_REPLY_ENABLED=True,
        )
    )
    report = _report(transport, [_tenant_row()])

    assert report["assessment"]["configuration_ready_for_reply_loop"] is True
    assert report["assessment"]["configuration_ready_for_approval_send"] is False


def test_tenant_snapshot_contains_policy_state_without_tenant_name_or_contact_data():
    tenant = SimpleNamespace(slug="tenant-a", is_active=True)
    company = SimpleNamespace(
        company_identification_mode="shadow", provider_name="pdl_ip"
    )
    contacts = SimpleNamespace(
        mode="review_only",
        contact_provider_name="hunter_domain",
        verification_provider_name="hunter",
    )
    drafts = SimpleNamespace(mode="review_only")
    delivery = SimpleNamespace(
        mode="off",
        provider_name="resend",
        controlled_auto_opt_in=False,
        controlled_auto_legal_approved=False,
    )

    snapshot = tenant_policy_snapshot(tenant, company, contacts, drafts, delivery)

    assert snapshot["slug"] == "tenant-a"
    assert snapshot["contact_enrichment"]["provider"] == "hunter_domain"
    assert "name" not in snapshot
    assert "email" not in json.dumps(snapshot).lower()
