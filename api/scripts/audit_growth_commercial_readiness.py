"""Read-only production audit for growth providers and email controls.

The report deliberately separates installed adapters, tenant policy, and live
transport switches. It never calls a data provider, sends email, mutates a
tenant, or prints credential values.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlmodel import col, select

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.company_identification import GrowthAutomationPolicy
from app.models.contact_enrichment import ContactPersonaPolicy
from app.models.outreach import OutreachDeliveryPolicy, OutreachDraftPolicy
from app.models.tenant import Tenant
from app.services.company_identification.providers import available_provider_names
from app.services.contact_enrichment.providers import (
    available_contact_provider_names,
    available_verification_provider_names,
)

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

SCHEMA_VERSION = 1


def _configured(value: str) -> bool:
    return bool(value.strip())


def transport_snapshot(config: Any) -> dict[str, Any]:
    """Return booleans and public identifiers only; never credential values."""

    sender = config.EMAIL_FROM.strip().lower()
    sender_identity_configured = bool(
        sender and not sender.endswith("@example.com") and "@" in sender
    )
    outbound_prerequisites = {
        "resend_api_key_configured": _configured(config.RESEND_API_KEY),
        "sender_identity_configured": sender_identity_configured,
        "resend_webhook_configured": _configured(config.RESEND_WEBHOOK_SECRET),
        "public_unsubscribe_origin_configured": _configured(
            config.OUTREACH_PUBLIC_BASE_URL
        ),
        "unsubscribe_signing_secret_configured": _configured(
            config.OUTREACH_UNSUBSCRIBE_SECRET
        ),
    }
    inbound_prerequisites = {
        "inbound_domain_configured": _configured(config.OUTREACH_INBOUND_DOMAIN),
        "inbound_signing_secret_configured": _configured(
            config.OUTREACH_INBOUND_SECRET
        ),
    }
    return {
        "provider": config.ESP_PROVIDER.lower(),
        "dry_run": bool(config.EMAIL_DRY_RUN),
        "external_delivery_enabled": bool(config.EMAIL_EXTERNAL_DELIVERY_ENABLED),
        "outreach_send_enabled": bool(config.OUTREACH_SEND_ENABLED),
        "inbound_reply_enabled": bool(config.INBOUND_REPLY_ENABLED),
        "outbound_prerequisites": outbound_prerequisites,
        "outbound_prerequisites_ready": all(outbound_prerequisites.values()),
        "inbound_prerequisites": inbound_prerequisites,
        "inbound_prerequisites_ready": all(inbound_prerequisites.values()),
        "internal_recipient_allowlist_configured": _configured(
            config.EMAIL_INTERNAL_RECIPIENT_ALLOWLIST
        ),
        "sales_handoff_recipient_configured": _configured(config.SALES_NOTIFY_EMAIL),
    }


def tenant_policy_snapshot(
    tenant: Tenant,
    company: GrowthAutomationPolicy | None,
    contacts: ContactPersonaPolicy | None,
    drafts: OutreachDraftPolicy | None,
    delivery: OutreachDeliveryPolicy | None,
) -> dict[str, Any]:
    return {
        "slug": tenant.slug,
        "active": tenant.is_active,
        "company_identification": {
            "persisted": company is not None,
            "mode": company.company_identification_mode if company else "off",
            "provider": company.provider_name if company else None,
        },
        "contact_enrichment": {
            "persisted": contacts is not None,
            "mode": contacts.mode if contacts else "off",
            "provider": contacts.contact_provider_name if contacts else None,
            "verification_provider": (
                contacts.verification_provider_name if contacts else None
            ),
        },
        "outreach_drafts": {
            "persisted": drafts is not None,
            "mode": drafts.mode if drafts else "off",
        },
        "outreach_delivery": {
            "persisted": delivery is not None,
            "mode": delivery.mode if delivery else "off",
            "provider": delivery.provider_name if delivery else None,
            "controlled_auto_opt_in": (
                bool(delivery.controlled_auto_opt_in) if delivery else False
            ),
            "controlled_auto_legal_approved": (
                bool(delivery.controlled_auto_legal_approved) if delivery else False
            ),
        },
    }


def evaluate_report(report: dict[str, Any]) -> dict[str, Any]:
    company_registry = set(report["providers"]["company_identification"])
    contact_registry = set(report["providers"]["contact_search"])
    verification_registry = set(report["providers"]["email_verification"])
    transport = report["transport"]
    violations: list[str] = []
    warnings: list[str] = []

    if "mock" in company_registry:
        violations.append("production_company_registry_exposes_mock")
    if "mock" in contact_registry:
        violations.append("production_contact_registry_exposes_mock")
    if "mock" in verification_registry:
        violations.append("production_verification_registry_exposes_mock")

    approval_send_tenants: list[str] = []
    review_contact_tenants: list[str] = []
    controlled_auto_tenants: list[str] = []
    for row in report["tenants"]:
        slug = row["slug"]
        company = row["company_identification"]
        contacts = row["contact_enrichment"]
        delivery = row["outreach_delivery"]

        if company["mode"] != "off" and company["provider"] not in company_registry:
            violations.append(f"{slug}:company_provider_unavailable")
        if company["mode"] != "off" and company["provider"] == "mock":
            violations.append(f"{slug}:production_company_policy_uses_mock")
        if company["mode"] == "controlled_auto":
            violations.append(f"{slug}:controlled_auto_company_mode_not_authorized")
        if contacts["mode"] == "review_only":
            review_contact_tenants.append(slug)
            if contacts["provider"] not in contact_registry:
                violations.append(f"{slug}:contact_provider_unavailable")
            if contacts["verification_provider"] not in verification_registry:
                violations.append(f"{slug}:verification_provider_unavailable")
            if contacts["provider"] == "mock" or contacts["verification_provider"] == "mock":
                violations.append(f"{slug}:production_contact_policy_uses_mock")
        if delivery["mode"] == "approval_send":
            approval_send_tenants.append(slug)
        if delivery["controlled_auto_opt_in"] or delivery[
            "controlled_auto_legal_approved"
        ]:
            controlled_auto_tenants.append(slug)

    if controlled_auto_tenants:
        violations.append("controlled_auto_is_not_authorized")
    if transport["outreach_send_enabled"] and not transport[
        "external_delivery_enabled"
    ]:
        violations.append("outreach_send_enabled_without_external_delivery")
    if transport["inbound_reply_enabled"] and not transport[
        "inbound_prerequisites_ready"
    ]:
        violations.append("inbound_enabled_without_required_configuration")
    if transport["external_delivery_enabled"] and not transport[
        "outbound_prerequisites_ready"
    ]:
        violations.append("external_delivery_enabled_without_required_configuration")
    if transport["external_delivery_enabled"] and transport["dry_run"]:
        warnings.append("external_delivery_enabled_but_dry_run_prevents_provider_send")
    if transport["outreach_send_enabled"] and not approval_send_tenants:
        warnings.append("global_outreach_enabled_without_approval_send_tenant")

    activation_blockers: list[str] = []
    if not review_contact_tenants:
        activation_blockers.append("no_review_only_contact_tenant")
    if not approval_send_tenants:
        activation_blockers.append("no_approval_send_tenant")
    if not transport["outbound_prerequisites_ready"]:
        activation_blockers.append("outbound_prerequisites_incomplete")
    if not transport["external_delivery_enabled"]:
        activation_blockers.append("external_delivery_kill_switch_closed")
    if not transport["outreach_send_enabled"]:
        activation_blockers.append("outreach_send_kill_switch_closed")
    if transport["dry_run"]:
        activation_blockers.append("email_dry_run_enabled")

    reply_activation_blockers: list[str] = []
    if not transport["inbound_prerequisites_ready"]:
        reply_activation_blockers.append("inbound_prerequisites_incomplete")
    if not transport["inbound_reply_enabled"]:
        reply_activation_blockers.append("inbound_reply_kill_switch_closed")

    guarded = not transport["external_delivery_enabled"] and not transport[
        "outreach_send_enabled"
    ]
    return {
        "status": "failed" if violations else "passed",
        "safe_guardrails_engaged": guarded,
        "configuration_ready_for_approval_send": not activation_blockers,
        "configuration_ready_for_reply_loop": not reply_activation_blockers,
        "automatic_outreach_enabled": False,
        "active_contact_review_tenants": review_contact_tenants,
        "active_approval_send_tenants": approval_send_tenants,
        "controlled_auto_tenants": controlled_auto_tenants,
        "activation_blockers": activation_blockers,
        "reply_activation_blockers": reply_activation_blockers,
        "warnings": warnings,
        "violations": violations,
    }


async def build_report() -> dict[str, Any]:
    engine.echo = False
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "providers": {
            "company_identification": list(available_provider_names()),
            "contact_search": list(available_contact_provider_names()),
            "email_verification": list(available_verification_provider_names()),
        },
        "transport": transport_snapshot(settings),
        "tenants": [],
        "privacy": {
            "external_provider_calls": False,
            "messages_sent": False,
            "policies_mutated": False,
            "credential_values_in_report": False,
            "contact_data_in_report": False,
        },
        "evidence_limits": [
            "provider_data_rights_not_evaluated",
            "company_precision_not_evaluated",
            "contact_relevance_not_evaluated",
            "email_deliverability_not_evaluated",
            "reply_classification_quality_not_evaluated",
            "commercial_conversion_not_evaluated",
        ],
    }
    async with AsyncSessionLocal() as session:
        tenants = list(
            (
                await session.exec(
                    select(Tenant)
                    .where(Tenant.is_active.is_(True))
                    .order_by(col(Tenant.slug))
                )
            ).all()
        )
        for tenant in tenants:
            report["tenants"].append(
                tenant_policy_snapshot(
                    tenant,
                    await session.get(GrowthAutomationPolicy, tenant.id),
                    await session.get(ContactPersonaPolicy, tenant.id),
                    await session.get(OutreachDraftPolicy, tenant.id),
                    await session.get(OutreachDeliveryPolicy, tenant.id),
                )
            )
    report["assessment"] = evaluate_report(report)
    return report


async def main() -> None:
    report = await build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["assessment"]["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
