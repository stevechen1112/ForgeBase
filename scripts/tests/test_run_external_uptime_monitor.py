from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "run_external_uptime_monitor.py"
SPEC = importlib.util.spec_from_file_location("run_external_uptime_monitor", SCRIPT_PATH)
assert SPEC and SPEC.loader
monitor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = monitor
SPEC.loader.exec_module(monitor)


def _body(check: object) -> bytes:
    validator = check.validator
    if validator == "liveness":
        return b'{"status":"ok"}'
    if validator == "readiness":
        return (
            b'{"status":"ready","checks":{"database":"ok","migration":"ok",'
            b'"storage":"ok","scheduler":"ok"}}'
        )
    if validator == "assets":
        return b'{"status":"ok","assetsMounted":true,"problems":[]}'
    return b"html"


def test_all_declared_checks_pass_without_storing_bodies() -> None:
    selected = monitor.checks("https://example.test", "https://axis.test")
    results = monitor.run_checks(
        selected,
        timeout=1,
        fetcher=lambda url, timeout: (200, _body(next(c for c in selected if c.url == url))),
    )
    payload = monitor.report(results)

    assert payload["status"] == "passed"
    assert payload["check_count"] == 8
    assert payload["failed_count"] == 0
    assert "body" not in json.dumps(payload).lower()


def test_readiness_requires_every_core_component() -> None:
    check = monitor.Check("ready", "https://example.test/health/ready", "readiness")
    result = monitor.probe(
        check,
        timeout=1,
        fetcher=lambda url, timeout: (
            200,
            (
                b'{"status":"ready","checks":{"database":"ok","migration":"ok",'
                b'"storage":"failed","scheduler":"ok"},"secret":"do-not-copy"}'
            ),
        ),
    )

    assert result.passed is False
    assert result.error == "readiness_component_not_ok"
    assert "do-not-copy" not in json.dumps(monitor.asdict(result))


def test_transport_exception_text_is_not_persisted() -> None:
    def fail(url: str, timeout: float) -> tuple[int, bytes]:
        raise RuntimeError("credential=must-not-leak")

    result = monitor.probe(
        monitor.Check("home", "https://example.test/"), timeout=1, fetcher=fail
    )

    assert result.error == "transport_error_RuntimeError"
    assert "must-not-leak" not in json.dumps(monitor.asdict(result))


def test_writers_create_machine_readable_failure_evidence(tmp_path: Path) -> None:
    result = monitor.Result(
        "home", "https://example.test/", False, 503, 12, "unexpected_http_status_503"
    )
    json_path = tmp_path / "monitor.json"
    junit_path = tmp_path / "monitor.xml"

    monitor.write_json(json_path, monitor.report([result]))
    monitor.write_junit(junit_path, [result])

    assert json.loads(json_path.read_text(encoding="utf-8"))["status"] == "failed"
    assert 'failures="1"' in junit_path.read_text(encoding="utf-8")
