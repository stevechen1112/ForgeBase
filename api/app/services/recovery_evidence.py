"""Read the PII-free recovery evidence projection mounted by production."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings

MAX_EVIDENCE_BYTES = 64 * 1024
VALID_STATUSES = {"verified", "backup_only", "not_recorded"}


def _datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return timestamp if timestamp.tzinfo is not None else None


def load_recovery_evidence(path: Path | None = None) -> dict[str, Any] | None:
    evidence_file = path or Path(settings.RECOVERY_EVIDENCE_FILE)
    try:
        if (
            evidence_file.is_symlink()
            or not evidence_file.is_file()
            or evidence_file.stat().st_size > MAX_EVIDENCE_BYTES
        ):
            return None
        payload = json.loads(evidence_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        return None
    status = payload.get("evidence_status")
    if status not in VALID_STATUSES:
        return None
    backup_at = _datetime(payload.get("last_backup_at"))
    restore_at = _datetime(payload.get("last_restore_drill_at"))
    if status in {"verified", "backup_only"} and backup_at is None:
        return None
    if status == "verified" and restore_at is None:
        return None
    if status == "backup_only" and restore_at is not None:
        return None
    if status == "not_recorded" and (backup_at is not None or restore_at is not None):
        return None
    return {
        "last_backup_at": backup_at,
        "last_restore_drill_at": restore_at,
        "evidence_status": status,
        "last_backup_offsite_status": payload.get("last_backup_offsite_status"),
    }
