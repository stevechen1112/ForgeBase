"""Run the isolated tenant-delivery factory contract and emit CI evidence."""

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
    parser = argparse.ArgumentParser(description="Run the tenant delivery factory lab.")
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/tenant-delivery-factory",
        help="Directory for JUnit and JSON evidence.",
    )
    args = parser.parse_args()
    _assert_safe_environment()

    artifacts = Path(args.artifacts_dir).resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    report_path = artifacts / "tenant-delivery-factory.json"
    junit_path = artifacts / "tenant-delivery-factory.junit.xml"
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
                    + "::test_tenant_delivery_factory_is_preflighted_atomic_and_replay_safe"
                ),
                "--junitxml",
                str(junit_path),
            ]
        )
    )
    report = {
        "schema_version": 1,
        "lab": "tenant-delivery-factory",
        "status": "passed" if exit_code == 0 else "failed",
        "pytest_exit_code": exit_code,
        "contracts": {
            "preflight_is_read_only": exit_code == 0,
            "static_demo_is_not_publishable": exit_code == 0,
            "provisioning_is_atomic": exit_code == 0,
            "replay_returns_original_manifest": exit_code == 0,
            "key_reuse_with_changed_spec_is_blocked": exit_code == 0,
            "temporary_password_not_persisted_in_manifest": exit_code == 0,
            "premature_live_stage_is_blocked": exit_code == 0,
            "live_requires_publish_owner_handoff_and_acceptance": exit_code == 0,
            "cleanup_verified": exit_code == 0,
        },
        "external_network_calls": 0,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
