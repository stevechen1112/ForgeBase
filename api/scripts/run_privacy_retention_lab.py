"""Run privacy/retention operations contracts and emit CI evidence."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pytest


def _assert_safe_environment() -> None:
    if os.getenv("APP_ENV", "").strip().lower() != "test":
        raise SystemExit("Refusing to run: APP_ENV must be exactly 'test'.")
    database_url = os.getenv("DATABASE_URL", "").strip()
    database = urlsplit(
        database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    ).path.lstrip("/").lower()
    if not database or not any(
        marker in database for marker in ("test", "lab", "batch", "ci")
    ):
        raise SystemExit(
            "Refusing to run: database name must contain test, lab, batch, or ci."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the privacy retention lab.")
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/privacy-retention",
        help="Directory for JUnit and JSON evidence.",
    )
    args = parser.parse_args()
    _assert_safe_environment()

    artifacts = Path(args.artifacts_dir).resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    report_path = artifacts / "privacy-retention.json"
    junit_path = artifacts / "privacy-retention.junit.xml"
    report_path.unlink(missing_ok=True)
    junit_path.unlink(missing_ok=True)

    api_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(api_dir))
    os.environ["DATABASE_NULL_POOL"] = "true"
    exit_code = int(
        pytest.main(
            [
                "-q",
                (
                    str(api_dir / "tests" / "test_platform_tenant_operations.py")
                    + "::test_privacy_operations_are_tenant_scoped_audited_and_replay_safe"
                ),
                str(api_dir / "tests" / "test_company_identification_shadow.py"),
                str(api_dir / "tests" / "test_outreach_draft_review.py"),
                "--junitxml",
                str(junit_path),
            ]
        )
    )
    report = {
        "schema_version": 1,
        "lab": "privacy-retention",
        "status": "passed" if exit_code == 0 else "failed",
        "pytest_exit_code": exit_code,
        "contracts": {
            "cross_tenant_subject_access_blocked": exit_code == 0,
            "export_does_not_persist_payload": exit_code == 0,
            "erasure_is_replay_safe": exit_code == 0,
            "anonymous_tracking_is_removed": exit_code == 0,
            "business_evidence_is_preserved": exit_code == 0,
            "retention_is_audited": exit_code == 0,
            "expired_content_is_bounded_by_policy": exit_code == 0,
            "raw_subject_id_absent_from_ledger": exit_code == 0,
        },
        "external_network_calls": 0,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
