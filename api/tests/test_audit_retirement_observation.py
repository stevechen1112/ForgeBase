"""Production retirement snapshot policy remains fail closed."""

from scripts.audit_retirement_observation import (
    OBSERVING_DISABLED,
    REMOVED,
    validate_snapshot,
)


def _candidate(key: str, *, state: str, status: str, days: int) -> dict:
    return {
        "candidate_key": key,
        "code_state": state,
        "status": status,
        "required_observation_days": days,
        "removal_ready": False,
        "evidence": {"enabled_preferences": 0},
    }


def valid_candidates() -> list[dict]:
    rows = [
        _candidate(key, state="disabled", status="observing", days=days)
        for key, days in OBSERVING_DISABLED.items()
    ]
    rows.extend(
        _candidate(key, state="removed", status="removed", days=0)
        for key in REMOVED
    )
    return rows


def test_validate_snapshot_accepts_disabled_observation_and_retained_core() -> None:
    report = validate_snapshot(valid_candidates())
    assert report["status"] == "passed"
    assert report["new_removals_authorized"] == []
    assert report["notification_core_retained"] is True


def test_validate_snapshot_rejects_enabled_channel_and_core_retirement() -> None:
    candidates = valid_candidates()
    line = next(row for row in candidates if row["candidate_key"] == "notification_line")
    line["code_state"] = "active"
    line["evidence"]["enabled_preferences"] = 1
    candidates.append(
        _candidate("intent_scoring", state="disabled", status="observing", days=30)
    )
    report = validate_snapshot(candidates)
    assert report["status"] == "failed"
    assert "notification_line:entry_not_disabled" in report["violations"]
    assert "notification_line:enabled_preferences" in report["violations"]
    assert "north_star_marked_for_retirement:intent_scoring" in report["violations"]
