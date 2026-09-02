"""Fail CI when current and historical product documents become ambiguous."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX = "FORGEBASE_DOCUMENT_AUTHORITY_INDEX_2026-08-28.md"
CURRENT_AUDIT = "FORGEBASE_FUNCTION_MODULE_COMPLETENESS_AUDIT_2026-08-15.md"
CURRENT_SCOPE_DECISION = "FORGEBASE_PRODUCT_SCOPE_REALIGNMENT_DECISION_2026-09-02.md"
HISTORICAL_MARKERS = {
    "FORGEBASE_PRODUCT_CLAIMS_IMPLEMENTATION_AUDIT_2026-08-26.md": "歷史基線／已被取代",
    "FORGEBASE_COMPANY_IDENTIFICATION_AND_CONTACT_ENRICHMENT_PLAN_2026-08-16.md": "歷史方案／已被北極星計畫取代",
    "FORGEBASE_COMPREHENSIVE_AUDIT_2026-08-11.md": "歷史稽核",
    "FORGEBASE_AI_CUSTOMER_SERVICE_AUDIT_2026-08-11.md": "歷史稽核",
    "FORGEBASE_MASTER_ROADMAP.md": "舊 roadmap，已不再是唯一執行總表",
    "FORGEBASE_PHASE1_P0_EXTERNAL_PILOT_TODO_2026-08-16.md": "歷史兩階段 TODO",
    "FORGEBASE_EXTERNAL_TEST_HARDENING_REPORT_2026-08-16.md": "歷史 hardening 快照",
    "FORGEBASE_CLOSED_TEST_READINESS_COMPLETION_REPORT_2026-08-15.md": "歷史完成度快照",
    "FORGEBASE_PLAN_B_REFERENCE_SITE_TODO_2026-08-11.md": "歷史 Reference Site TODO",
}


def violations(repo_root: Path = REPO_ROOT) -> list[str]:
    failures: list[str] = []
    index_path = repo_root / INDEX
    audit_path = repo_root / CURRENT_AUDIT
    decision_path = repo_root / CURRENT_SCOPE_DECISION
    readme_path = repo_root / "README.md"

    for required in (index_path, audit_path, decision_path, readme_path):
        if not required.is_file():
            failures.append(f"missing_required_document:{required.name}")
    if failures:
        return failures

    index = index_path.read_text(encoding="utf-8")
    audit = audit_path.read_text(encoding="utf-8")
    readme = readme_path.read_text(encoding="utf-8")
    if INDEX not in readme:
        failures.append("readme_missing_authority_index")
    if CURRENT_SCOPE_DECISION not in index or CURRENT_SCOPE_DECISION not in readme:
        failures.append("scope_decision_missing_from_current_authority_chain")
    if index.find(CURRENT_SCOPE_DECISION) > index.find(CURRENT_AUDIT):
        failures.append("scope_decision_not_prioritized_over_historical_audit")
    if "本次完整更新：2026-08-28" not in audit or "92.7%" not in audit:
        failures.append("current_audit_missing_version_or_score")
    if len(re.findall(r"^### (?:[1-9]|1[0-7])\. ", audit, re.MULTILINE)) != 17:
        failures.append("current_audit_module_count_is_not_17")

    for relative, marker in HISTORICAL_MARKERS.items():
        path = repo_root / relative
        if not path.is_file():
            failures.append(f"missing_historical_document:{relative}")
            continue
        head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:12])
        if marker not in head:
            failures.append(f"historical_marker_missing:{relative}")

    for reference in sorted(set(re.findall(r"`([^`]+\.md)`", index))):
        if not (repo_root / reference).is_file():
            failures.append(f"authority_index_broken_reference:{reference}")
    return failures


def main() -> None:
    failures = violations()
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        raise SystemExit(1)
    print(
        "Document authority contract passed: current audit, README index, "
        f"and {len(HISTORICAL_MARKERS)} historical markers verified."
    )


if __name__ == "__main__":
    main()
