"""Deployment recovery utilities must preserve the non-root trust boundary."""

import os
import shlex
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_offsite_backup_delegates_only_one_read_only_file() -> None:
    script = (ROOT / "deploy/backup.sh").read_text(encoding="utf-8")

    assert 'api_runtime_uid="${FORGEBASE_API_RUNTIME_UID:-10001}"' in script
    assert 'case "$api_runtime_uid" in \'\'|*[!0-9]*)' in script
    assert 'if ! test "$api_runtime_uid" -gt 0' in script
    assert 'database_original_uid="$(stat -c \'%u\' -- "$database_file")"' in script
    assert 'chmod -- 0400 "$database_file"' in script
    assert 'container_database_file="/offsite-work/$(basename "$database_file")"' in script
    assert '"$database_file:$container_database_file:ro"' in script
    assert 'upload "$container_database_file"' in script
    assert 'BACKUP_WORK_DIR=/offsite-work' in script  # pragma: allowlist secret -- env/path contract
    assert '"$offsite_work_dir:/offsite-work"' in script
    assert '"$backup_dir:/backups"' not in script
    assert "restore_database_permissions" in script
    assert "cleanup_offsite_work_dir" in script


def test_offsite_restore_exposes_only_a_precreated_destination_file() -> None:
    script = (ROOT / "deploy/restore-drill.sh").read_text(encoding="utf-8")

    assert 'install -m 0600 -o "$api_runtime_uid" -g "$api_runtime_gid"' in script
    assert 'if ! test "$api_runtime_uid" -gt 0' in script
    assert 'container_downloaded_file="/offsite-work/restore.sql.gz"' in script
    assert '"$downloaded_file:$container_downloaded_file"' in script
    assert 'BACKUP_WORK_DIR=/offsite-work' in script  # pragma: allowlist secret -- env/path contract
    assert '"$offsite_work_dir:/offsite-work"' in script
    assert '"$drill_dir:/drill"' not in script
    assert 'chown -- "$(id -u):$(id -g)" "$downloaded_file"' in script


@pytest.mark.parametrize("script_name", ["backup.sh", "restore-drill.sh"])
@pytest.mark.parametrize("invalid_uid", ["0", "--reference=/tmp/untrusted"])
def test_recovery_scripts_reject_root_or_non_numeric_runtime_uid(
    script_name: str, invalid_uid: str
) -> None:
    command = (
        f"FORGEBASE_API_RUNTIME_UID={shlex.quote(invalid_uid)} "
        f"bash deploy/{script_name}"
    )
    if script_name == "restore-drill.sh":
        command += " --offsite dummy"
    completed = subprocess.run(
        ["bash", "-c", command],
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "Invalid API runtime UID." in completed.stderr
