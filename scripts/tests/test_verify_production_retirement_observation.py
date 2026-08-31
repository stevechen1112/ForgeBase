from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "verify_production_retirement_observation.py"
)
SPEC = importlib.util.spec_from_file_location(
    "verify_production_retirement_observation", SCRIPT_PATH
)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)
validate_retirement_page = verifier.validate_retirement_page


def rendered_page() -> str:
    observing = "觀察中\n程式狀態\ndisabled\n觀察進度\n0／60 天\n觀察期尚未完成"
    return f"""功能退場稽核
AI relation 推薦介面
{observing}
Telegram 通知渠道
{observing}
LINE 通知渠道
{observing}
不安全且未接線的舊 IP resolver
已安全移除
"""


def test_validate_retirement_page_accepts_disabled_observation() -> None:
    report = validate_retirement_page(rendered_page())
    assert report["status"] == "passed"
    assert report["notification_channels_observing"] is True
    assert report["new_removals_authorized"] == []


@pytest.mark.parametrize("label", ["Telegram 通知渠道", "LINE 通知渠道"])
def test_validate_retirement_page_rejects_active_channel(label: str) -> None:
    text = rendered_page().replace(
        f"{label}\n觀察中\n程式狀態\ndisabled",
        f"{label}\n觀察中\n程式狀態\nactive",
    )
    with pytest.raises(ValueError, match=label):
        validate_retirement_page(text)
