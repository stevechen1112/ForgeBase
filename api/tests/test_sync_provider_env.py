from __future__ import annotations

import importlib.util
import os
import stat
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "deploy" / "sync-provider-env.py"
SPEC = importlib.util.spec_from_file_location("sync_provider_env", SCRIPT_PATH)
assert SPEC and SPEC.loader
sync_provider_env = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_provider_env)


def _credentials(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)
    return path


def test_render_replaces_managed_values_without_touching_unrelated_settings() -> None:
    rendered = sync_provider_env.render_updated_env(
        "DATABASE_URL=postgres://example\nPDL_API_KEY=old\nHUNTER_DATA_USE_APPROVED=false\n",
        {"PDL_API_KEY": "new-pdl", "HUNTER_API_KEY": "new-hunter"},
    )

    assert "DATABASE_URL=postgres://example" in rendered
    assert rendered.count("PDL_API_KEY=") == 1
    assert "PDL_API_KEY=new-pdl" in rendered
    assert "HUNTER_API_KEY=new-hunter" in rendered
    assert "PDL_DATA_USE_APPROVED=true" in rendered
    assert "PDL_CONTACT_DATA_USE_APPROVED=false" in rendered
    assert "HUNTER_DATA_USE_APPROVED=true" in rendered
    assert "HUNTER_VERIFY_ESTIMATED_COST=0.5" in rendered


def test_secret_file_rejects_unknown_or_missing_keys(tmp_path: Path) -> None:
    unknown = _credentials(
        tmp_path / "unknown.env", "PDL_API_KEY=pdl\nOTHER_KEY=value\n"
    )
    with pytest.raises(sync_provider_env.ProviderEnvError, match="Unexpected"):
        sync_provider_env._parse_secret_file(unknown)

    missing = _credentials(tmp_path / "missing.env", "PDL_API_KEY=pdl\n")
    with pytest.raises(sync_provider_env.ProviderEnvError, match="Missing"):
        sync_provider_env._parse_secret_file(missing)


def test_sync_is_atomic_and_does_not_leave_temporary_files(tmp_path: Path) -> None:
    env_file = tmp_path / "api.env"
    env_file.write_text("DATABASE_URL=postgres://example\n", encoding="utf-8")
    env_file.chmod(0o640)
    credentials = _credentials(
        tmp_path / "providers.env",
        "PDL_API_KEY=pdl-secret\nHUNTER_API_KEY=hunter-secret\n",
    )

    sync_provider_env.sync_provider_env(env_file, credentials)

    output = env_file.read_text(encoding="utf-8")
    assert "PDL_API_KEY=pdl-secret" in output
    assert "HUNTER_API_KEY=hunter-secret" in output
    if os.name == "posix":
        assert stat.S_IMODE(env_file.stat().st_mode) == 0o640
    assert not list(tmp_path.glob(".api.env.providers-*"))
