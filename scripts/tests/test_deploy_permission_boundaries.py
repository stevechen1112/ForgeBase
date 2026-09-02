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


def test_safe_deploy_keeps_edge_running_until_dependencies_are_healthy() -> None:
    script = (ROOT / "deploy/safe-deploy.sh").read_text(encoding="utf-8")

    application_switch = 'up -d --remove-orphans db migrate "${release_services[@]}"'
    dependency_gate = 'if [ "$services_ready" != true ]; then'
    edge_switch = "up -d --no-deps --force-recreate caddy"
    assert application_switch in script
    assert dependency_gate in script
    assert edge_switch in script
    assert script.index(application_switch) < script.index(dependency_gate)
    assert script.index(dependency_gate) < script.index(edge_switch)
    assert 'up -d --remove-orphans\n' not in script


def test_safe_deploy_exports_retired_rfq_fields_before_migration() -> None:
    script = (ROOT / "deploy/safe-deploy.sh").read_text(encoding="utf-8")

    backup = 'bash "$repo_dir/deploy/backup.sh"'
    retired_export = "python scripts/export_retired_rfq_sales_data.py"
    migration = 'run --rm migrate'
    assert backup in script
    assert retired_export in script
    assert migration in script
    assert script.index(backup) < script.index(retired_export) < script.index(migration)
    assert '-v "$repo_dir/backups:/protected-exports"' in script
    assert 'chmod 0600 "$repo_dir/backups/$retired_export_name"' in script
    assert "legacy columns are already absent" in script


def test_safe_deploy_reclaims_only_disposable_builder_cache() -> None:
    script = (ROOT / "deploy/safe-deploy.sh").read_text(encoding="utf-8")

    backup = 'bash "$repo_dir/deploy/backup.sh"'
    cache_prune = "docker builder prune --all --force"
    database_ready = "exec -T db pg_isready"
    first_build = 'build migrate'
    assert cache_prune in script
    assert script.index(cache_prune) < script.index(database_ready)
    assert script.index(database_ready) < script.index(backup) < script.index(first_build)
    assert "Database did not recover before the backup safety gate." in script
    assert "docker system prune" not in script
    assert "docker image prune" not in script
    assert "docker container prune" not in script
    assert "docker volume prune" not in script


def test_reference_site_uses_an_explicit_host_not_a_stale_tenant_slug() -> None:
    compose = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    reference = compose.split("  web_reference:", 1)[1].split("\n  caddy:", 1)[0]

    assert reference.count('NEXT_PUBLIC_TENANT_SLUG: ""') == 2
    assert "${NEXT_PUBLIC_TENANT_SLUG" not in reference
    assert reference.count(
        "FORGEBASE_TENANT_HOST_OVERRIDE: "
        "${REFERENCE_TENANT_HOST:-default-tenant.forgebase.com}"
    ) == 2


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
