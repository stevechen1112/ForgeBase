from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _module():
    path = Path(__file__).parents[2] / "deploy" / "set-controlled-inbound-window.py"
    spec = importlib.util.spec_from_file_location("controlled_inbound_window", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _env(path: Path, *, inbound_secret: str = "s" * 40) -> None:
    path.write_text(
        "EMAIL_EXTERNAL_DELIVERY_ENABLED=false\n"
        "OUTREACH_SEND_ENABLED=false\n"
        "INBOUND_REPLY_ENABLED=false\n"
        "OUTREACH_INBOUND_DOMAIN=replies.example.test\n"
        f"OUTREACH_INBOUND_SECRET={inbound_secret}\n",
        encoding="utf-8",
    )


def test_opens_and_closes_only_inbound_switch(tmp_path: Path) -> None:
    module = _module()
    path = tmp_path / "api.env"
    _env(path)
    opened = module.configure(path, enabled=True)
    assert opened == {
        "external_delivery_enabled": False,
        "outreach_send_enabled": False,
        "inbound_reply_enabled": True,
    }
    text = path.read_text(encoding="utf-8")
    assert "INBOUND_REPLY_ENABLED=true" in text
    assert "EMAIL_EXTERNAL_DELIVERY_ENABLED=false" in text
    module.configure(path, enabled=False)
    assert "INBOUND_REPLY_ENABLED=false" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        (
            "EMAIL_EXTERNAL_DELIVERY_ENABLED=true",
            "external_delivery_switch_must_be_closed",
        ),
        ("OUTREACH_SEND_ENABLED=true", "outreach_send_switch_must_be_closed"),
        ("OUTREACH_INBOUND_DOMAIN=", "inbound_domain_missing"),
        ("OUTREACH_INBOUND_SECRET=short", "inbound_route_secret_missing"),
    ],
)
def test_fails_closed_for_unsafe_prerequisites(
    tmp_path: Path, line: str, reason: str
) -> None:
    module = _module()
    path = tmp_path / "api.env"
    _env(path)
    key = line.split("=", 1)[0]
    rows = [
        line if row.startswith(f"{key}=") else row
        for row in path.read_text(encoding="utf-8").splitlines()
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(module.WindowError, match=reason):
        module.configure(path, enabled=True)
