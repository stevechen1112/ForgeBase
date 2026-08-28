from __future__ import annotations

import importlib.util
import stat
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "deploy" / "configure-growth-mail-env.py"
SPEC = importlib.util.spec_from_file_location("configure_growth_mail_env", SCRIPT_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

IDENTITY = {
    "sender_email": "steve_chen@premierbiz.com.tw",
    "sender_name": "ForgeBase Business Team",
    "internal_recipient": "steve_chen@premierbiz.com.tw",
    "sales_notify_email": "steve_chen@premierbiz.com.tw",
    "manager_email": "steve_chen@premierbiz.com.tw",
}


def _values(path: Path) -> dict[str, str]:
    return module._parse(path.read_text(encoding="utf-8").splitlines())


def test_configures_outbound_atomically_without_changing_unrelated_values(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "api.env"
    env_file.write_text(
        "OTHER=keep\n"
        "OUTREACH_PUBLIC_BASE_URL=\n"
        "EMAIL_EXTERNAL_DELIVERY_ENABLED=true\n"
        "OUTREACH_SEND_ENABLED=true\n"
        "INBOUND_REPLY_ENABLED=true\n",
        encoding="utf-8",
    )

    result = module.configure(
        env_file,
        public_base_url="https://pcbrm.tw/",
        **IDENTITY,
    )
    values = _values(env_file)

    assert values["OTHER"] == "keep"
    assert values["OUTREACH_PUBLIC_BASE_URL"] == "https://pcbrm.tw"
    assert values["EMAIL_FROM"] == "steve_chen@premierbiz.com.tw"
    assert values["EMAIL_FROM_NAME"] == "ForgeBase Business Team"
    assert values["EMAIL_INTERNAL_RECIPIENT_ALLOWLIST"] == IDENTITY["sender_email"]
    assert values["SALES_NOTIFY_EMAIL"] == IDENTITY["sender_email"]
    assert values["MANAGER_EMAIL"] == IDENTITY["sender_email"]
    assert values["EMAIL_EXTERNAL_DELIVERY_ENABLED"] == "false"
    assert values["OUTREACH_SEND_ENABLED"] == "false"
    assert values["INBOUND_REPLY_ENABLED"] == "false"
    assert len(values["OUTREACH_UNSUBSCRIBE_SECRET"]) >= 32
    assert result["unsubscribe_secret_generated"] is True
    assert result["delivery_switches_closed"] is True
    if sys.platform != "win32":
        assert stat.S_IMODE(env_file.stat().st_mode) == 0o600


def test_replay_preserves_existing_signing_secrets(tmp_path: Path) -> None:
    existing_unsubscribe = "u" * 40
    existing_inbound = "i" * 40
    env_file = tmp_path / "api.env"
    env_file.write_text(
        "\n".join(
            [
                f"OUTREACH_UNSUBSCRIBE_SECRET={existing_unsubscribe}",
                f"OUTREACH_INBOUND_SECRET={existing_inbound}",
            ]
        ),
        encoding="utf-8",
    )

    result = module.configure(
        env_file,
        public_base_url="https://pcbrm.tw",
        inbound_domain="Replies.PremierBiz.com.tw.",
        **IDENTITY,
    )
    values = _values(env_file)

    assert values["OUTREACH_UNSUBSCRIBE_SECRET"] == existing_unsubscribe
    assert values["OUTREACH_INBOUND_SECRET"] == existing_inbound
    assert values["OUTREACH_INBOUND_DOMAIN"] == "replies.premierbiz.com.tw"
    assert values["EMAIL_EXTERNAL_DELIVERY_ENABLED"] == "false"
    assert values["OUTREACH_SEND_ENABLED"] == "false"
    assert values["INBOUND_REPLY_ENABLED"] == "false"
    assert result["unsubscribe_secret_generated"] is False
    assert result["inbound_secret_generated"] is False


@pytest.mark.parametrize(
    "url",
    [
        "http://pcbrm.tw",
        "https://user:" + "pass@pcbrm.tw",
        "https://pcbrm.tw/path",
        "https://pcbrm.tw?query=1",
        "https://pcbrm.tw:8443",
        "https://pcbrm.tw:bad",
    ],
)
def test_rejects_unsafe_public_origins(tmp_path: Path, url: str) -> None:
    env_file = tmp_path / "api.env"
    env_file.write_text("OTHER=keep\n", encoding="utf-8")

    with pytest.raises(ValueError, match="origin-only HTTPS"):
        module.configure(env_file, public_base_url=url, **IDENTITY)

    assert env_file.read_text(encoding="utf-8") == "OTHER=keep\n"


@pytest.mark.parametrize(
    "domain",
    [
        "localhost",
        "https://reply.example.com",
        "-bad.example.com",
        "bad_.example.com",
        "回覆.example.com",
        f"{'a' * 63}.{'b' * 63}.{'c' * 63}.{'d' * 62}.com",
    ],
)
def test_rejects_invalid_inbound_domains(tmp_path: Path, domain: str) -> None:
    env_file = tmp_path / "api.env"
    env_file.write_text("OTHER=keep\n", encoding="utf-8")

    with pytest.raises(ValueError, match="inbound domain"):
        module.configure(
            env_file,
            public_base_url="https://pcbrm.tw",
            inbound_domain=domain,
            **IDENTITY,
        )

    assert env_file.read_text(encoding="utf-8") == "OTHER=keep\n"


def test_collapses_duplicate_managed_keys(tmp_path: Path) -> None:
    env_file = tmp_path / "api.env"
    env_file.write_text(
        "OUTREACH_PUBLIC_BASE_URL=https://old.example.com\n"
        "OTHER=keep\n"
        "OUTREACH_PUBLIC_BASE_URL=https://duplicate.example.com\n",
        encoding="utf-8",
    )

    module.configure(env_file, public_base_url="https://pcbrm.tw", **IDENTITY)

    lines = env_file.read_text(encoding="utf-8").splitlines()
    assert lines.count("OUTREACH_PUBLIC_BASE_URL=https://pcbrm.tw") == 1
    assert not any("old.example.com" in line for line in lines)
    assert not any("duplicate.example.com" in line for line in lines)


@pytest.mark.parametrize(
    "overrides",
    [
        {"sender_email": "not-an-email"},
        {"sender_name": "Bad\nName"},
        {"internal_recipient": "other@premierbiz.com.tw"},
        {"sales_notify_email": "other@premierbiz.com.tw"},
        {"manager_email": "other@premierbiz.com.tw"},
    ],
)
def test_rejects_invalid_or_misaligned_identity(tmp_path: Path, overrides) -> None:
    env_file = tmp_path / "api.env"
    env_file.write_text("OTHER=keep\n", encoding="utf-8")
    identity = {**IDENTITY, **overrides}

    with pytest.raises(ValueError, match="growth mail"):
        module.configure(
            env_file,
            public_base_url="https://pcbrm.tw",
            **identity,
        )

    assert env_file.read_text(encoding="utf-8") == "OTHER=keep\n"
