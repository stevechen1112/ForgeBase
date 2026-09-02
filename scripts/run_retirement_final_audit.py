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
        "copilot_api": "api/app/api/v1/endpoints/copilot.py",
        "copilot_service": "api/app/services/copilot",
        "ml_scoring_api": "api/app/api/v1/endpoints/ml_scoring.py",
        "ml_scoring_service": "api/app/services/ml_intent.py",
        "generic_integrations_api": "api/app/api/v1/endpoints/integrations.py",
        "generic_integrations_model": "api/app/models/integration_credential.py",
        "legacy_ip_resolver": "api/app/services/ip_resolver.py",
        "agentos_runtime": "api/app/services/agentOS.py",
        "buyer_scoring": "api/app/services/intent_scoring.py",
        "esp_sync": "api/app/api/v1/endpoints/esp.py",
    }
    for candidate, relative in removed_paths.items():
        _check(
            f"removed:{candidate}",
            not (ROOT / relative).exists(),
            f"forbidden path absent: {relative}",
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
    for channel in ("telegram", "line"):
        _check(
            f"disabled:notification_{channel}",
            (ROOT / f"api/app/services/channels/{channel}.py").is_file()
            and _contains(
                "api/app/services/notification_channel_policy.py",
                'RETIRED_NOTIFICATION_CHANNELS = frozenset({"telegram", "line"})',
            )
            and not (ROOT / "api/app/api/v1/endpoints/copilot.py").exists()
            and _contains(
                "api/app/services/notification_router.py",
                "retirement_candidate_for_channel",
                "dispatch blocked",
                "_CHANNEL_MAP = {}",
            )
            and _contains(
                "api/app/db/migrations/versions/0097_disable_unused_notification_channels.py",
                f"notification_{channel}",
                "code_state = 'disabled'",
            ),
            f"{channel} entry and dispatch are disabled while implementation remains reversible",
            checks,
        )

    migration = (ROOT / "api/app/db/migrations/versions/0086_retirement_observability.py").read_text(
        encoding="utf-8"
    )
    protected_core = [
        "full_tracking",
        "company_identification",
        "contact_enrichment",
        "journey_personalization",
        "outreach_send",
        "inbound_reply",
        "sales_handoff",
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
        "removed_verified": [
            "copilot_floating_widget",
            "copilot_api",
            "copilot_service",
            "ml_scoring_api",
            "ml_scoring_service",
            "generic_integrations_api",
            "generic_integrations_model",
            "legacy_ip_resolver",
            "agentos_runtime",
            "buyer_scoring",
            "esp_sync",
        ],
        "continue_observation": [
            "relation_recommender",
            "notification_telegram",
            "notification_line",
        ],
        "retain_operational": ["notification_core"],
        "new_removals_authorized": [],
    }
    digest_payload = {"checks": checks, "decisions": decisions}
    return {
        "schema_version": 2,
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
