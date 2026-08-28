"""Static retirement report must preserve North Star and verify removed code."""

from scripts.run_retirement_final_audit import run_audit


def test_final_retirement_static_audit_passes_without_new_removals() -> None:
    report = run_audit()
    assert report["status"] == "passed"
    assert report["checks_passed"] == report["checks_total"]
    assert report["decisions"]["new_removals_authorized"] == []
    assert set(report["decisions"]["removed_verified"]) == {
        "copilot_floating_widget",
        "legacy_ip_resolver",
    }
    assert set(report["decisions"]["continue_observation"]) == {
        "agentos_runtime",
        "ml_scoring_runtime",
        "relation_recommender",
        "notification_telegram",
        "notification_line",
    }
    assert report["decisions"]["retain_operational"] == ["notification_core"]
    assert report["external_observation_claimed_complete"] is False
