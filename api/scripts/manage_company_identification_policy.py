"""Audit or enable the real production IP-to-company provider safely.

The command never prints credentials, raw IP addresses, provider payloads, or
company candidates.  ``apply`` changes only the selected tenants and keeps the
capability in Shadow Mode so a human must review every inferred company.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

from app.core.datetime import utcnow_naive
from app.db.session import AsyncSessionLocal, engine
from app.models.company_identification import GrowthAutomationPolicy
from app.models.platform_audit_log import PlatformAuditLog
from app.models.tenant import Tenant
from app.services.company_identification.providers import (
    CompanyLookupContext,
    available_provider_names,
    get_company_identification_provider,
)
from sqlmodel import col, select

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

SCHEMA_VERSION = 1
REAL_PROVIDER = "pdl_ip"
SHADOW_MODE = "shadow"
PROBE_IP = "8.8.8.8"  # Public recursive DNS address; never a visitor address.
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_tenant_slugs(raw: str) -> list[str]:
    slugs: list[str] = []
    for item in raw.split(","):
        slug = item.strip().lower()
        if not slug:
            continue
        if not SLUG_PATTERN.fullmatch(slug):
            raise ValueError(f"Invalid tenant slug: {slug}")
        if slug not in slugs:
            slugs.append(slug)
    if not slugs:
        raise ValueError("At least one explicit tenant slug is required")
    return slugs


def policy_snapshot(policy: GrowthAutomationPolicy | None) -> dict:
    if policy is None:
        return {
            "persisted": False,
            "company_identification_mode": "off",
            "provider_name": "mock",
        }
    return {
        "persisted": True,
        "company_identification_mode": policy.company_identification_mode,
        "provider_name": policy.provider_name,
        "observation_retention_days": policy.observation_retention_days,
        "daily_lookup_quota": policy.daily_lookup_quota,
        "daily_provider_cost_limit": float(policy.daily_provider_cost_limit),
        "medium_confidence_threshold": policy.medium_confidence_threshold,
        "high_confidence_threshold": policy.high_confidence_threshold,
        "allowed_countries": policy.allowed_countries,
    }


def policy_is_ready(policy: GrowthAutomationPolicy | None) -> bool:
    return bool(
        policy
        and policy.company_identification_mode == SHADOW_MODE
        and policy.provider_name == REAL_PROVIDER
        and policy.daily_lookup_quota > 0
        and policy.daily_provider_cost_limit > 0
    )


async def probe_real_provider() -> dict:
    """Prove network access and credential acceptance without visitor data."""

    adapter = get_company_identification_provider(REAL_PROVIDER)
    result = await adapter.identify_company(
        CompanyLookupContext(
            tenant_id=uuid.uuid4(),
            observation_id=uuid.uuid4(),
            ip_address=PROBE_IP,
            country="US",
            asn=None,
        )
    )
    return {
        "provider": result.provider,
        "authenticated_request_completed": True,
        "result_class": "matched" if result.candidates else "no_match",
        "candidate_count": len(result.candidates),
        "units": result.units,
    }


async def run(action: str, tenant_slugs: list[str], actor_email: str) -> dict:
    engine.echo = False
    provider_registry = list(available_provider_names())
    if REAL_PROVIDER not in provider_registry:
        raise RuntimeError("pdl_ip is not configured in this deployment")
    # Fail closed: production policy is not changed unless a real external
    # request has already proved that PDL accepts the installed credentials.
    probe = await probe_real_provider() if action == "apply" else None

    async with AsyncSessionLocal() as session:
        tenants = list(
            (
                await session.exec(
                    select(Tenant)
                    .where(Tenant.slug.in_(tenant_slugs), Tenant.is_active.is_(True))
                    .order_by(col(Tenant.slug))
                )
            ).all()
        )
        found = {tenant.slug for tenant in tenants}
        missing = sorted(set(tenant_slugs) - found)
        if missing:
            raise RuntimeError("Active tenant not found: " + ", ".join(missing))

        changed: list[str] = []
        if action == "apply":
            now = utcnow_naive()
            for tenant in tenants:
                policy = await session.get(GrowthAutomationPolicy, tenant.id)
                before = policy_snapshot(policy)
                if policy is None:
                    policy = GrowthAutomationPolicy(tenant_id=tenant.id)
                policy.company_identification_mode = SHADOW_MODE
                policy.provider_name = REAL_PROVIDER
                # A persisted zero quota/cost is a deliberate stop switch.  New
                # policies receive conservative defaults from the model.
                policy.updated_at = now
                session.add(policy)
                after = policy_snapshot(policy)
                if before != after:
                    changed.append(tenant.slug)
                    session.add(
                        PlatformAuditLog(
                            actor_email=actor_email[:255] or None,
                            tenant_id=tenant.id,
                            action="company_identification.production_policy_applied",
                            target_type="growth_automation_policy",
                            target_id=str(tenant.id),
                            changes_json=json.dumps(
                                {
                                    "before": before,
                                    "after": after,
                                    "reason": "enable_real_pdl_shadow_mode",
                                },
                                ensure_ascii=False,
                                default=str,
                            ),
                        )
                    )
            await session.commit()

        tenant_rows = []
        for tenant in tenants:
            policy = await session.get(GrowthAutomationPolicy, tenant.id)
            tenant_rows.append(
                {
                    "slug": tenant.slug,
                    "name": tenant.name,
                    "active": tenant.is_active,
                    "ready": policy_is_ready(policy),
                    "policy": policy_snapshot(policy),
                }
            )

    ready = all(row["ready"] for row in tenant_rows)
    status = "passed" if ready and (probe or {}).get("authenticated_request_completed") else "needs_changes"
    if action == "audit" and ready:
        status = "passed"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "status": status,
        "real_provider": REAL_PROVIDER,
        "provider_registry": provider_registry,
        "changed_tenants": changed,
        "tenants": tenant_rows,
        "real_provider_probe": probe,
        "privacy": {
            "visitor_ip_used_for_probe": False,
            "raw_ip_in_report": False,
            "provider_payload_in_report": False,
            "mode": SHADOW_MODE,
            "automatic_contact_or_send": False,
        },
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=("audit", "apply"), required=True)
    parser.add_argument("--tenant-slugs", required=True)
    args = parser.parse_args()
    report = await run(
        args.action,
        parse_tenant_slugs(args.tenant_slugs),
        os.getenv("COMPANY_POLICY_ACTOR_EMAIL", "github-actions@forgebase.com"),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.action == "apply" and report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
