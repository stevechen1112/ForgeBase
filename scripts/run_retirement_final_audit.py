"""Fail-closed static and policy audit for category-four retirement candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _contains(path: str, *needles: str) -> bool:
    text = (ROOT / path).read_text(encoding="utf-8")
    return all(needle in text for needle in needles)


def _check(name: str, condition: bool, detail: str, checks: list[dict]) -> None:
    checks.append({"name": name, "passed": condition, "detail": detail})


def run_audit() -> dict:
    checks: list[dict] = []
    removed_paths = {
        "copilot_floating_widget": "admin/src/components/copilot/CopilotFloatingWidget.tsx",
        "legacy_ip_resolver": "api/app/services/ip_resolver.py",
    }
    for candidate, relative in removed_paths.items():
        _check(
            f"removed:{candidate}",
            not (ROOT / relative).exists(),
            f"forbidden path absent: {relative}",
            checks,
        )

    _check(
        "disabled:ml_scoring",
        _contains(
            "api/app/services/capability_access.py",
            '"ml_scoring"',
            '"status": "retirement_observation"',
        )
        and _contains(
            "admin/src/components/auth/FeatureAccessGuard.tsx",
            'path: "/dashboard/ml-scoring"',
            'feature: "ml_scoring"',
        )
        and _contains(
            "api/app/api/v1/endpoints/ml_scoring.py",
            'RequireFeature("ml_scoring")',
            'candidate_key="ml_scoring_runtime"',
        ),
        "runtime, route and telemetry remain fail-closed during observation",
        checks,
    )
    _check(
        "disabled:relation_recommender",
        _contains(
            "api/app/api/v1/endpoints/ai_intelligence.py",
            'RequireFeature("ai_relation_recommendations")',
            'candidate_key="relation_recommender"',
        ),
        "recommendation endpoints require the disabled retirement capability",
        checks,
    )
    _check(
        "disabled:agentos_runtime",
        _contains(
            "api/app/services/capability_access.py",
            '"automation_runs"',
            '"status": "service_required"',
            '"configurable": False',
        )
        and _contains(
            "admin/src/components/auth/FeatureAccessGuard.tsx",
            'path: "/dashboard/agent-runs"',
            'feature: "automation_runs"',
        )
        and _contains(
            "api/app/services/operational_outbox.py", "locked-off retirement candidate"
        ),
        "AgentOS cannot be enabled by tenant override or tenantless outbox work",
        checks,
    )

    for channel in ("telegram", "line"):
        _check(
            f"retained:notification_{channel}",
            (ROOT / f"api/app/services/channels/{channel}.py").is_file()
            and _contains(
                "api/app/api/v1/endpoints/retirement_audit.py",
                f'"notification_{channel}": "{channel}"',
                "enabled_preferences",
            ),
            f"active {channel} channel remains protected by usage and configuration evidence",
            checks,
        )

    migration = (ROOT / "api/app/db/migrations/versions/0086_retirement_observability.py").read_text(
        encoding="utf-8"
    )
    protected_core = [
        "full_tracking",
        "intent_scoring",
        "company_identification",
        "contact_enrichment",
        "journey_personalization",
        "outreach_send",
        "inbound_reply",
        "sales_handoff",
        "closed_loop_attribution",
        "rfq_workspace",
    ]
    for feature in protected_core:
        _check(
            f"core-protected:{feature}",
            f'"candidate_key": "{feature}"' not in migration,
            "North Star capability is not seeded as a retirement candidate",
            checks,
        )

    failed = [check["name"] for check in checks if not check["passed"]]
    decisions = {
        "removed_verified": ["copilot_floating_widget", "legacy_ip_resolver"],
        "continue_observation": [
            "agentos_runtime",
            "ml_scoring_runtime",
            "relation_recommender",
        ],
        "retain_operational": ["notification_telegram", "notification_line"],
        "new_removals_authorized": [],
    }
    digest_payload = {"checks": checks, "decisions": decisions}
    return {
        "schema_version": 1,
        "status": "failed" if failed else "passed",
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed_checks": failed,
        "decisions": decisions,
        "report_sha256": hashlib.sha256(
            json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "checks": checks,
        "external_observation_claimed_complete": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/retirement-final-audit")
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    report = run_audit()
    (output / "summary.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
