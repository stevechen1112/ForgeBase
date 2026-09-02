"""Run the hermetic website-to-RFQ handoff lab and emit release evidence."""

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


def _write_report(path: Path, *, exit_code: int, cases: list[str]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "lab": "website-to-rfq-handoff",
                "status": "passed" if exit_code == 0 else "failed",
                "pytest_exit_code": exit_code,
                "external_network_calls": 0,
                "covered_workflows": [
                    "public_rfq_submission",
                    "permission_scoped_assignment",
                    "reply_preparation",
                    "visitor_to_rfq_linkage",
                    "retired_crm_route_absence",
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
        description="Run the isolated ForgeBase website-to-RFQ handoff lab."
    )
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/website-to-rfq-handoff",
        help="Directory for JUnit and JSON evidence (default: %(default)s).",
    )
    args = parser.parse_args()
    _assert_safe_environment()

    artifacts = Path(args.artifacts_dir).resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    report = artifacts / "website-to-rfq-handoff.json"
    junit = artifacts / "website-to-rfq-handoff.junit.xml"
    os.environ["DATABASE_NULL_POOL"] = "true"
    api_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(api_dir))

    cases = [
        str(api_dir / "tests" / "test_rfq_sales_workspace.py")
        + "::test_rfq_handoff_end_to_end",
        str(api_dir / "tests" / "test_growth_ops.py")
        + "::test_reply_assist_and_task_queue_remain_operational",
        str(api_dir / "tests" / "test_review_fixes.py")
        + "::test_has_rfq_uses_rfq_requests_not_tracking_event",
        str(api_dir / "tests" / "test_review_fixes.py")
        + "::test_retired_crm_and_unverifiable_handoff_routes_are_not_registered",
    ]
    exit_code = int(pytest.main(["-q", *cases, "--junitxml", str(junit)]))
    _write_report(report, exit_code=exit_code, cases=cases)
    print(f"Website-to-RFQ handoff lab artifacts: {artifacts}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
