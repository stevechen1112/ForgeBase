from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.recovery_evidence import load_recovery_evidence

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "deploy" / "publish-recovery-evidence.py"
)
SPEC = importlib.util.spec_from_file_location("publish_recovery_evidence", SCRIPT_PATH)
assert SPEC and SPEC.loader
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_publisher_projects_only_latest_safe_recovery_fields(tmp_path: Path) -> None:
    _write(
        tmp_path / "database-old.manifest.json",
        {
            "schema_version": 1,
            "status": "passed",
            "created_at": "2026-08-01T00:00:00+00:00",
            "offsite_status": "passed",
            "sha256": "must-not-be-published",
            "critical_row_counts": {"users": 99},
        },
    )
    _write(
        tmp_path / "database-new.manifest.json",
        {
            "schema_version": 1,
            "status": "passed",
            "created_at": "2026-08-28T01:00:00+00:00",
            "offsite_status": "passed",
            "offsite_object_key": "must-not-be-published",
        },
    )
    _write(
        tmp_path / "restore-drills" / "restore-drill-new.json",
        {
            "schema_version": 1,
            "status": "passed",
            "finished_at": "2026-08-28T02:00:00+00:00",
            "backup_created_at": "2026-08-28T01:00:00+00:00",
            "disposable_database_removed": True,
            "critical_row_counts": {"users": 99},
        },
    )

    output = tmp_path / "public" / "status.json"
    publisher.publish(tmp_path, output)
    raw = output.read_text(encoding="utf-8")
    payload = json.loads(raw)

    assert payload == {
        "schema_version": 1,
        "last_backup_at": "2026-08-28T01:00:00+00:00",
        "last_backup_offsite_status": "passed",
        "last_restore_drill_at": "2026-08-28T02:00:00+00:00",
        "evidence_status": "verified",
    }
    assert "sha256" not in raw
    assert "critical_row_counts" not in raw
    assert "offsite_object_key" not in raw


def test_reader_validates_schema_status_and_required_timestamps(tmp_path: Path) -> None:
    evidence = tmp_path / "status.json"
    _write(
        evidence,
        {
            "schema_version": 1,
            "last_backup_at": "2026-08-28T01:00:00+00:00",
            "last_backup_offsite_status": "passed",
            "last_restore_drill_at": "2026-08-28T02:00:00+00:00",
            "evidence_status": "verified",
        },
    )
    result = load_recovery_evidence(evidence)
    assert result is not None
    assert result["evidence_status"] == "verified"
    assert result["last_backup_at"] == datetime(2026, 8, 28, 1, tzinfo=timezone.utc)

    _write(evidence, {"schema_version": 1, "evidence_status": "verified"})
    assert load_recovery_evidence(evidence) is None


def test_publisher_requires_restore_to_match_latest_backup(tmp_path: Path) -> None:
    _write(
        tmp_path / "database-new.manifest.json",
        {
            "schema_version": 1,
            "status": "passed",
            "created_at": "2026-08-28T03:00:00+00:00",
            "offsite_status": "passed",
        },
    )
    _write(
        tmp_path / "restore-drills" / "restore-drill-old.json",
        {
            "schema_version": 1,
            "status": "passed",
            "finished_at": "2026-08-28T02:00:00+00:00",
            "backup_created_at": "2026-08-28T01:00:00+00:00",
            "disposable_database_removed": True,
        },
    )

    payload = publisher.recovery_summary(tmp_path)

    assert payload["evidence_status"] == "backup_only"
    assert payload["last_restore_drill_at"] is None


def test_reader_rejects_timezone_free_timestamps(tmp_path: Path) -> None:
    evidence = tmp_path / "status.json"
    _write(
        evidence,
        {
            "schema_version": 1,
            "last_backup_at": "2026-08-28T01:00:00",
            "last_restore_drill_at": None,
            "evidence_status": "backup_only",
        },
    )
    assert load_recovery_evidence(evidence) is None


def test_reader_rejects_timestamps_that_conflict_with_status(tmp_path: Path) -> None:
    evidence = tmp_path / "status.json"
    _write(
        evidence,
        {
            "schema_version": 1,
            "last_backup_at": "2026-08-28T01:00:00+00:00",
            "last_restore_drill_at": "2026-08-28T02:00:00+00:00",
            "evidence_status": "backup_only",
        },
    )
    assert load_recovery_evidence(evidence) is None


def test_reader_rejects_oversized_or_malformed_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "status.json"
    evidence.write_text("{not-json", encoding="utf-8")
    assert load_recovery_evidence(evidence) is None
    evidence.write_bytes(b"x" * (64 * 1024 + 1))
    assert load_recovery_evidence(evidence) is None
