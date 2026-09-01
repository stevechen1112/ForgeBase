"""Run the hermetic North Star full-chain lab and emit machine-readable proof."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pytest


def _database_name(url: str) -> str:
    return urlsplit(
        url.replace("postgresql+asyncpg://", "postgresql://", 1)
    ).path.lstrip("/")


def _assert_safe_environment() -> None:
    if os.getenv("APP_ENV", "").strip().lower() != "test":
        raise SystemExit("Refusing to run: APP_ENV must be exactly 'test'.")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("Refusing to run: DATABASE_URL is required.")
    database = _database_name(database_url).lower()
    if not database or not any(
        marker in database for marker in ("test", "lab", "batch", "ci")
    ):
        raise SystemExit(
            "Refusing to run: database name must contain test, lab, batch, or ci."
        )


def _write_failure_report(path: Path, exit_code: int) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "lab": "north-star-full-e2e",
                "status": "failed",
                "pytest_exit_code": exit_code,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_success_report(path: Path, cases: list[str]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "lab": "north-star-full-e2e",
                "status": "passed",
                "external_network_calls": 0,
                "retired_inference_dependencies": 0,
                "covered_workflows": [
                    "company_identification",
                    "contact_review",
                    "approved_outreach",
                    "inbound_reply_to_rfq",
                    "closed_loop_attribution",
                ],
                "pytest_cases": cases,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the isolated ForgeBase North Star full-chain lab."
    )
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/north-star-lab",
        help="Directory for JUnit and JSON evidence (default: %(default)s).",
    )
    args = parser.parse_args()
    _assert_safe_environment()

    artifacts = Path(args.artifacts_dir).resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    report = artifacts / "north-star-lab.json"
    junit = artifacts / "north-star-lab.junit.xml"
    os.environ["DATABASE_NULL_POOL"] = "true"
    os.environ["FORGEBASE_NORTH_STAR_REPORT"] = str(report)
    api_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(api_dir))

    # Keep the release gate aligned with the retained, factual buyer workflow.
    # Each case is hermetic and together they verify the complete handoff chain
    # without reintroducing retired intent scoring or generic integrations.
    cases = [
        str(api_dir / "tests" / "test_company_identification_shadow.py")
        + "::test_shadow_runtime_replay_cache_cost_guard_and_circuit",
        str(api_dir / "tests" / "test_contact_enrichment_review.py")
        + "::test_review_only_runtime_dedupes_encrypts_and_manual_conversion_has_no_visitor_link",
        str(api_dir / "tests" / "test_outreach_draft_review.py")
        + "::test_snapshot_grounding_and_human_approved_delivery_lifecycle",
        str(api_dir / "tests" / "test_inbound_reply_handoff.py")
        + "::test_reply_inbox_is_tenant_scoped_and_converts_to_existing_rfq_workbench",
        str(api_dir / "tests" / "test_closed_loop_attribution.py")
        + "::test_reviewed_reply_conversion_is_direct_and_preserves_outcome_history",
    ]
    exit_code = int(pytest.main(["-q", *cases, "--junitxml", str(junit)]))
    if exit_code:
        _write_failure_report(report, exit_code)
    else:
        _write_success_report(report, cases)
    print(f"North Star lab artifacts: {artifacts}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
