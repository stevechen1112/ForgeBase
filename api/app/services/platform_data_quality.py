"""Read-only, privacy-minimised production data-quality inspection."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_RESERVED_EMAIL_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "example.test",
    "test.invalid",
}
_SYNTHETIC_MARKERS = ("demo", "dummy", "fixture", "sample", "smoke", "test")


def _load_form_data(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        payload = json.loads(value or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def synthetic_signals(form_data: Any, test_run_id: str | None) -> list[str]:
    """Return explainable signals; signals are evidence for review, never auto-deletion."""
    payload = _load_form_data(form_data)
    signals: list[str] = []
    if test_run_id:
        signals.append("test_run_id_present")

    email = str(payload.get("email") or payload.get("contact_email") or "").strip().lower()
    email_domain = email.rsplit("@", 1)[-1] if "@" in email else ""
    if email_domain in _RESERVED_EMAIL_DOMAINS:
        signals.append("reserved_email_domain")

    names = " ".join(
        str(payload.get(key) or "").lower()
        for key in ("full_name", "contact_name", "company_name")
    )
    if any(marker in names for marker in _SYNTHETIC_MARKERS):
        signals.append("synthetic_name_marker")
    return signals


async def build_platform_data_quality_report(session: AsyncSession) -> dict[str, Any]:
    tenant_rows = await session.execute(
        text(
            """
            SELECT t.id, t.name, t.slug, t.is_active,
                   sp.brand_name, sp.site_url, sb.primary_domain,
                   (SELECT COUNT(*) FROM users u WHERE u.tenant_id = t.id) AS user_count,
                   (SELECT COUNT(*) FROM rfq_requests r WHERE r.tenant_id = t.id) AS rfq_count
            FROM tenants t
            LEFT JOIN site_profiles sp ON sp.tenant_id = t.id
            LEFT JOIN site_builds sb ON sb.tenant_id = t.id
            ORDER BY t.created_at ASC
            """
        )
    )
    tenants = []
    for row in tenant_rows.mappings().all():
        mismatch = bool(row["brand_name"] and row["name"].strip() != row["brand_name"].strip())
        tenants.append(
            {
                "id": str(row["id"]),
                "name": row["name"],
                "slug": row["slug"],
                "is_active": bool(row["is_active"]),
                "brand_name": row["brand_name"],
                "site_url": row["site_url"],
                "primary_domain": row["primary_domain"],
                "user_count": int(row["user_count"] or 0),
                "rfq_count": int(row["rfq_count"] or 0),
                "identity_mismatch": mismatch,
            }
        )

    rfq_rows = await session.execute(
        text(
            """
            SELECT r.id, r.rfq_number, r.tenant_id, t.name AS tenant_name,
                   r.status, r.is_spam, r.is_test_data, r.test_run_id,
                   r.sla_breached, r.assigned_to, r.source_page, r.form_data,
                   r.created_at, r.updated_at, r.closed_at
            FROM rfq_requests r
            LEFT JOIN tenants t ON t.id = r.tenant_id
            ORDER BY r.created_at DESC
            """
        )
    )
    rfqs = []
    for row in rfq_rows.mappings().all():
        form_data = _load_form_data(row["form_data"])
        email = str(form_data.get("email") or form_data.get("contact_email") or "").strip().lower()
        signals = synthetic_signals(form_data, row["test_run_id"])
        rfqs.append(
            {
                "id": str(row["id"]),
                "rfq_number": row["rfq_number"],
                "tenant_id": str(row["tenant_id"]) if row["tenant_id"] else None,
                "tenant_name": row["tenant_name"],
                "status": row["status"],
                "is_spam": bool(row["is_spam"]),
                "is_test_data": bool(row["is_test_data"]),
                "test_run_id_present": bool(row["test_run_id"]),
                "sla_breached": bool(row["sla_breached"]),
                "assigned": row["assigned_to"] is not None,
                "source_page": row["source_page"],
                "email_domain": email.rsplit("@", 1)[-1] if "@" in email else None,
                "company_name": form_data.get("company_name"),
                "form_fields": sorted(str(key) for key in form_data),
                "synthetic_signals": signals,
                "requires_manual_review": bool(signals) and not bool(row["is_test_data"]),
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                "closed_at": row["closed_at"].isoformat() if row["closed_at"] else None,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": "read_only_review_required",
        "summary": {
            "tenant_count": len(tenants),
            "tenant_identity_mismatch_count": sum(item["identity_mismatch"] for item in tenants),
            "rfq_count": len(rfqs),
            "rfq_manual_review_count": sum(item["requires_manual_review"] for item in rfqs),
        },
        "tenants": tenants,
        "rfqs": rfqs,
    }
