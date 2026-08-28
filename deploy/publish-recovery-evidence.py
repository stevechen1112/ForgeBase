"""Publish a PII-free recovery summary for the read-only Admin mount."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return timestamp if timestamp.tzinfo is not None else None


def _load_passed(
    path: Path, *, timestamp_key: str
) -> tuple[datetime, dict[str, Any]] | None:
    try:
        if path.is_symlink() or path.stat().st_size > 1_000_000:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    timestamp = (
        _timestamp(payload.get(timestamp_key)) if isinstance(payload, dict) else None
    )
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or payload.get("status") != "passed"
        or timestamp is None
    ):
        return None
    return timestamp, payload


def _latest(
    paths: list[Path], *, timestamp_key: str
) -> tuple[datetime, dict[str, Any]] | None:
    rows = [
        row
        for path in paths
        if (row := _load_passed(path, timestamp_key=timestamp_key)) is not None
    ]
    return max(rows, key=lambda row: row[0]) if rows else None


def recovery_summary(backup_dir: Path) -> dict[str, Any]:
    backup = _latest(
        list(backup_dir.glob("database-*.manifest.json")),
        timestamp_key="created_at",
    )
    restore = _latest(
        list((backup_dir / "restore-drills").glob("restore-drill-*.json")),
        timestamp_key="finished_at",
    )
    backup_at = backup[0].isoformat() if backup else None
    restore_at = restore[0].isoformat() if restore else None
    offsite_status = (
        str(backup[1].get("offsite_status") or "unknown") if backup else None
    )
    restore_verified = bool(
        backup
        and restore
        and restore[1].get("disposable_database_removed") is True
        and _timestamp(restore[1].get("backup_created_at")) == backup[0]
    )
    if backup and restore_verified and offsite_status == "passed":
        evidence_status = "verified"
    elif backup:
        evidence_status = "backup_only"
    else:
        evidence_status = "not_recorded"
    return {
        "schema_version": 1,
        "last_backup_at": backup_at,
        "last_backup_offsite_status": offsite_status,
        "last_restore_drill_at": restore_at if restore_verified else None,
        "evidence_status": evidence_status,
    }


def publish(backup_dir: Path, output: Path) -> None:
    payload = recovery_summary(backup_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        output.parent.chmod(0o755)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, output)
        if os.name == "posix":
            directory_fd = os.open(output.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Published recovery evidence status: {payload['evidence_status']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    publish(args.backup_dir.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
