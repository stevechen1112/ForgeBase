"""Run the isolated internal performance, capacity, and short-soak gate."""

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
    database = _database_name(database_url).lower() if database_url else ""
    if not database or not any(
        marker in database for marker in ("test", "lab", "batch", "ci")
    ):
        raise SystemExit(
            "Refusing to run: database name must contain test, lab, batch, or ci."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts-dir", default="artifacts/performance-capacity-soak"
    )
    args = parser.parse_args()
    _assert_safe_environment()
    artifacts = Path(args.artifacts_dir).resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    report = artifacts / "performance-capacity-soak.json"
    junit = artifacts / "performance-capacity-soak.junit.xml"
    report.unlink(missing_ok=True)
    junit.unlink(missing_ok=True)
    os.environ["DATABASE_NULL_POOL"] = "true"
    os.environ["FORGEBASE_PERFORMANCE_REPORT"] = str(report)
    api_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(api_dir))
    exit_code = int(
        pytest.main(
            [
                "-q",
                str(api_dir / "tests" / "test_performance_capacity_soak.py"),
                "--junitxml",
                str(junit),
            ]
        )
    )
    if exit_code and not report.exists():
        report.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "lab": "performance-capacity-soak",
                    "status": "failed",
                    "pytest_exit_code": exit_code,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(f"Performance/capacity artifacts: {artifacts}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
