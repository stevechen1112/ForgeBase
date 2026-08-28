#!/usr/bin/env python3
"""Apply one reviewed, replay-safe production data-quality correction plan."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_rfq_plan(raw: str) -> list[dict[str, str]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("RFQ plan must be valid JSON") from exc
    if not isinstance(payload, list) or not 1 <= len(payload) <= 50:
        raise ValueError("RFQ plan must contain 1 to 50 records")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in payload:
        if not isinstance(item, dict) or set(item) != {"id", "rfq_number"}:
            raise ValueError("Every RFQ plan record must contain only id and rfq_number")
        record_id = str(uuid.UUID(str(item["id"])))
        number = str(item["rfq_number"]).strip()
        if not number.startswith("RFQ-") or len(number) > 30:
            raise ValueError("Invalid RFQ number")
        if record_id in seen:
            raise ValueError("Duplicate RFQ id")
        seen.add(record_id)
        result.append({"id": record_id, "rfq_number": number})
    return result


def _request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    token: str | None = None,
) -> Any:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/v1{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"API {method} {path} failed ({exc.code}): {detail}") from exc


def main() -> None:
    if os.environ.get("FORGEBASE_CONFIRM") != "APPLY_REVIEWED_DATA_QUALITY_PLAN":
        raise SystemExit("Explicit correction confirmation is required")
    base_url = os.environ.get("FORGEBASE_PRODUCTION_URL", "").strip()
    email = os.environ.get("FORGEBASE_PLATFORM_EMAIL", "").strip()
    password = os.environ.get("FORGEBASE_PLATFORM_PASSWORD", "")
    tenant_id = str(uuid.UUID(os.environ.get("FORGEBASE_TENANT_ID", "")))
    expected_name = os.environ.get("FORGEBASE_EXPECTED_TENANT_NAME", "").strip()
    new_name = os.environ.get("FORGEBASE_NEW_TENANT_NAME", "").strip()
    reason = os.environ.get("FORGEBASE_CORRECTION_REASON", "").strip()
    plan = parse_rfq_plan(os.environ.get("FORGEBASE_RFQ_PLAN_JSON", ""))
    if not base_url.startswith("https://") or len(password) < 20:
        raise SystemExit("Protected production URL and one-run credentials are required")
    if len(expected_name) < 2 or len(new_name) < 2 or len(reason) < 10:
        raise SystemExit("Tenant names and a detailed correction reason are required")

    login = _request(
        base_url,
        "/auth/login",
        method="POST",
        body={"email": email, "password": password},
    )
    token = login["access_token"]
    if not login.get("user", {}).get("is_superuser"):
        raise RuntimeError("One-run account is not a Platform Admin")

    tenant = _request(base_url, f"/admin/tenants/{tenant_id}", token=token)
    current_name = tenant["name"]
    if current_name not in {expected_name, new_name}:
        raise RuntimeError("Tenant identity no longer matches the reviewed plan")

    # Validate the complete plan before the first mutation. Individual writes
    # are replay-safe so a transport failure can resume without double changes.
    listing = _request(
        base_url,
        "/admin/rfqs?include_test=true&include_spam=true&limit=200",
        token=token,
    )
    by_id = {item["id"]: item for item in listing["data"]}
    for planned in plan:
        actual = by_id.get(planned["id"])
        if not actual or actual["rfq_number"] != planned["rfq_number"]:
            raise RuntimeError(f"RFQ no longer matches reviewed plan: {planned['rfq_number']}")

    tenant_changed = False
    if current_name == expected_name and expected_name != new_name:
        _request(
            base_url,
            f"/admin/tenants/{tenant_id}",
            method="PUT",
            body={"name": new_name},
            token=token,
        )
        tenant_changed = True

    changed_rfqs: list[str] = []
    already_classified: list[str] = []
    for planned in plan:
        actual = by_id.get(planned["id"])
        if actual["is_test_data"]:
            already_classified.append(planned["rfq_number"])
            continue
        _request(
            base_url,
            f"/admin/rfqs/{planned['id']}/classification",
            method="PATCH",
            body={"is_test_data": True, "reason": reason},
            token=token,
        )
        changed_rfqs.append(planned["rfq_number"])

    output = {
        "schema_version": 1,
        "status": "passed",
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "tenant_changed": tenant_changed,
        "new_tenant_name": new_name,
        "rfq_changed_count": len(changed_rfqs),
        "rfq_already_classified_count": len(already_classified),
        "changed_rfqs": changed_rfqs,
        "already_classified_rfqs": already_classified,
    }
    output_path = Path(os.environ.get("FORGEBASE_CORRECTION_REPORT", "artifacts/data-quality-correction.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Data-quality plan applied: tenant_changed={tenant_changed}, "
        f"rfqs_changed={len(changed_rfqs)}, replayed={len(already_classified)}"
    )


if __name__ == "__main__":
    main()
