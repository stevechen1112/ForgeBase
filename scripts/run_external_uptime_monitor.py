#!/usr/bin/env python3
"""Run privacy-minimized synthetic checks from outside the production host."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_RESPONSE_BYTES = 65_536


@dataclass(frozen=True)
class Check:
    name: str
    url: str
    validator: str = "status"


@dataclass(frozen=True)
class Result:
    name: str
    url: str
    passed: bool
    http_status: int | None
    latency_ms: int
    error: str | None


Fetcher = Callable[[str, float], tuple[int, bytes]]


def checks(base_url: str, axis_url: str) -> list[Check]:
    base = base_url.rstrip("/")
    axis = axis_url.rstrip("/")
    return [
        Check("ForgeBase homepage", f"{base}/"),
        Check("API liveness", f"{base}/health", "liveness"),
        Check("API core readiness", f"{base}/health/ready", "readiness"),
        Check("Admin login", f"{base}/backend/login"),
        Check("NorthForge site", f"{base}/northforge-tools/en"),
        Check(
            "NorthForge asset probe",
            f"{base}/northforge-tools/api/health/assets",
            "assets",
        ),
        Check("AxisForm site", f"{axis}/en"),
        Check("AxisForm asset probe", f"{axis}/api/health/assets", "assets"),
    ]


def fetch(url: str, timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ForgeBase-External-Uptime/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        # HTML bodies are deliberately ignored; JSON probes are small and a
        # truncated oversized response will fail closed during JSON parsing.
        body = response.read(MAX_RESPONSE_BYTES)
        return response.status, body


def _validate(validator: str, body: bytes) -> str | None:
    if validator == "status":
        return None
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "invalid_json"
    if not isinstance(payload, dict):
        return "invalid_json_shape"
    if validator == "liveness":
        return None if payload.get("status") == "ok" else "liveness_not_ok"
    if validator == "readiness":
        expected = {"database", "migration", "storage", "scheduler"}
        observed = payload.get("checks")
        if payload.get("status") != "ready" or not isinstance(observed, dict):
            return "readiness_not_ready"
        return (
            None
            if all(observed.get(component) == "ok" for component in expected)
            else "readiness_component_not_ok"
        )
    if validator == "assets":
        problems = payload.get("problems")
        return (
            None
            if payload.get("status") == "ok"
            and payload.get("assetsMounted") is True
            and problems == []
            else "assets_not_ready"
        )
    return "unknown_validator"


def probe(check: Check, *, timeout: float, fetcher: Fetcher = fetch) -> Result:
    started = time.monotonic()
    status: int | None = None
    error: str | None = None
    try:
        status, body = fetcher(check.url, timeout)
        if status != 200:
            error = f"unexpected_http_status_{status}"
        else:
            error = _validate(check.validator, body)
    except urllib.error.HTTPError as exc:
        status = exc.code
        error = f"http_error_{exc.code}"
    except TimeoutError:
        error = "timeout"
    # A custom fetcher can surface transport-library-specific exceptions.  We
    # intentionally persist only the exception class, never its message.
    except Exception as exc:  # noqa: BLE001
        error = f"transport_error_{type(exc).__name__}"
    latency_ms = max(0, round((time.monotonic() - started) * 1000))
    return Result(check.name, check.url, error is None, status, latency_ms, error)


def run_checks(
    selected: list[Check], *, timeout: float, fetcher: Fetcher = fetch
) -> list[Result]:
    return [probe(item, timeout=timeout, fetcher=fetcher) for item in selected]


def report(results: list[Result]) -> dict[str, Any]:
    passed = all(item.passed for item in results)
    return {
        "schema_version": 1,
        "monitor": "forgebase-production-external-uptime",
        "execution_origin": "off_host_synthetic",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "status": "passed" if passed else "failed",
        "check_count": len(results),
        "failed_count": sum(not item.passed for item in results),
        "checks": [asdict(item) for item in results],
        "evidence_limits": [
            "availability_and_declared_health_only",
            "does_not_prove_end_user_notification_delivery",
            "does_not_prove_business_workflow_correctness",
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_junit(path: Path, results: list[Result]) -> None:
    suite = ET.Element(
        "testsuite",
        name="production-external-uptime",
        tests=str(len(results)),
        failures=str(sum(not item.passed for item in results)),
    )
    for item in results:
        case = ET.SubElement(
            suite,
            "testcase",
            name=item.name,
            time=f"{item.latency_ms / 1000:.3f}",
        )
        if not item.passed:
            failure = ET.SubElement(case, "failure", message=item.error or "failed")
            failure.text = item.error or "failed"
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://pcbrm.tw")
    parser.add_argument(
        "--axis-url", default="https://axisform.172-233-64-5.sslip.io"
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--junit-output", type=Path, required=True)
    args = parser.parse_args()
    if args.timeout <= 0 or args.timeout > 60:
        parser.error("--timeout must be between 0 and 60 seconds")

    results = run_checks(
        checks(args.base_url, args.axis_url),
        timeout=args.timeout,
    )
    payload = report(results)
    write_json(args.json_output, payload)
    write_junit(args.junit_output, results)
    print(
        f"External uptime monitor {payload['status']}: "
        f"{payload['check_count'] - payload['failed_count']}/{payload['check_count']} checks"
    )
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
