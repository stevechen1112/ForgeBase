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

    exit_code = int(
        pytest.main(
            [
                "-q",
                str(api_dir / "tests" / "test_north_star_full_e2e.py"),
                "--junitxml",
                str(junit),
            ]
        )
    )
    if exit_code:
        _write_failure_report(report, exit_code)
    print(f"North Star lab artifacts: {artifacts}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
