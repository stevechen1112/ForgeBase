from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "verify_production_platform_resources.py"
)
SPEC = importlib.util.spec_from_file_location(
    "verify_production_platform_resources", SCRIPT_PATH
)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)
validate_resource_page = verifier.validate_resource_page


def test_validate_resource_page_accepts_rendered_recovery_evidence() -> None:
    result = validate_resource_page(
        """外部服務與資料
異地備份
證據狀態
備份與還原皆已驗證
最後備份證據
2026/8/28 上午9:30:00
還原演練
2026/8/28 上午9:45:00
告警與站外監控
"""
    )
    assert result["status"] == "passed"


@pytest.mark.parametrize("label", ["最後備份證據", "還原演練"])
def test_validate_resource_page_rejects_missing_evidence(label: str) -> None:
    text = """外部服務與資料
異地備份
備份與還原皆已驗證
最後備份證據
2026/8/28 上午9:30:00
還原演練
2026/8/28 上午9:45:00
"""
    text = text.replace(f"{label}\n2026/8/28", f"{label}\n尚未記錄\n2026/8/28")
    with pytest.raises(ValueError, match=label):
        validate_resource_page(text)
