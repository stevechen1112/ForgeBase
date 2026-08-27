#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifacts_dir="${1:-$repo_dir/artifacts/restore-rollback-lab}"
lock_dir="$repo_dir/artifacts/.restore-rollback-lab.lock"
mkdir -p "$(dirname "$lock_dir")"
if ! mkdir "$lock_dir" 2>/dev/null; then
  printf 'Another restore/rollback lab is already running.\n' >&2
  exit 1
fi
trap 'rmdir "$lock_dir" >/dev/null 2>&1 || true' EXIT
work_dir="$(mktemp -d)"
project="forgebase_restore_lab_$RANDOM"
compose_file="$work_dir/compose.yml"
env_file="$work_dir/lab.env"
api_env_file="$work_dir/api.env"
backup_dir="$work_dir/backups"
rollback_evidence_dir="$artifacts_dir/rollback"
restore_evidence_dir="$artifacts_dir/restore"
manifest="$work_dir/images.manifest"
checks=()

case "$work_dir" in
  /tmp/*|/var/tmp/*|/private/tmp/*) ;;
  *) printf 'Unsafe lab directory: %s\n' "$work_dir" >&2; exit 1 ;;
esac
case "$project" in forgebase_restore_lab_*) ;; *) exit 1 ;; esac

compose() {
  docker compose --project-name "$project" --env-file "$env_file" \
    -f "$compose_file" "$@"
}
cleanup() {
  exit_code=$?
  trap - EXIT
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  for image in \
    forgebase-rollback-lab-api-old:local \
    forgebase-rollback-lab-api-target:local \
    forgebase-rollback-lab-web-old:local \
    forgebase-rollback-lab-web-target:local; do
    docker image rm "$image" >/dev/null 2>&1 || true
  done
  case "$work_dir" in
    /tmp/*|/var/tmp/*|/private/tmp/*) rm -rf -- "$work_dir" ;;
  esac
  rmdir "$lock_dir" >/dev/null 2>&1 || true
  if [ "$exit_code" -ne 0 ] &&
    [ ! -f "$artifacts_dir/restore-rollback-lab.json" ]; then
    mkdir -p "$artifacts_dir"
    checks_csv="$(IFS=,; printf '%s' "${checks[*]}")"
    python3 - "$artifacts_dir" "$checks_csv" "$exit_code" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

artifacts = Path(sys.argv[1])
checks = list(filter(None, sys.argv[2].split(",")))
exit_code = int(sys.argv[3])
payload = {
    "schema_version": 1,
    "lab": "restore-rollback",
    "status": "failed",
    "finished_at": datetime.now(timezone.utc).isoformat(),
    "exit_code": exit_code,
    "completed_checks": checks,
    "production_resources_touched": False,
}
(artifacts / "restore-rollback-lab.json").write_text(
    json.dumps(payload, indent=2) + "\n", encoding="utf-8"
)
suite = ElementTree.Element(
    "testsuite",
    {"name": "restore-rollback-lab", "tests": "1", "failures": "1"},
)
case = ElementTree.SubElement(
    suite, "testcase", {"classname": "operations.recovery", "name": "lab"}
)
failure = ElementTree.SubElement(case, "failure", {"message": "lab failed"})
failure.text = f"Restore/Rollback lab exited with code {exit_code}"
ElementTree.ElementTree(suite).write(
    artifacts / "restore-rollback-lab.junit.xml",
    encoding="utf-8",
    xml_declaration=True,
)
PY
  fi
  exit "$exit_code"
}
trap cleanup EXIT

mkdir -p "$artifacts_dir" "$backup_dir" \
  "$rollback_evidence_dir" "$restore_evidence_dir"
rm -f -- "$artifacts_dir/restore-rollback-lab.json" \
  "$artifacts_dir/restore-rollback-lab.junit.xml"
find "$rollback_evidence_dir" -maxdepth 1 -type f \
  -name 'rollback-*.json' -delete
find "$restore_evidence_dir" -maxdepth 1 -type f \
  -name 'restore-drill-*.json' -delete

cat > "$env_file" <<'ENV'
POSTGRES_USER=forgebase_lab
POSTGRES_PASSWORD=forgebase_lab_password
POSTGRES_DB=forgebase_lab
ENV
cat > "$api_env_file" <<'ENV'
BACKUP_S3_BUCKET_NAME=
ENV
cat > "$compose_file" <<'YAML'
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 1s
      timeout: 3s
      retries: 30
  api:
    image: forgebase-rollback-lab-api-target:local
    command: ["sleep", "300"]
  web:
    image: forgebase-rollback-lab-web-target:local
    command: ["sleep", "300"]
  caddy:
    image: alpine:3.21
    command: ["sleep", "300"]
YAML

compose up -d --wait db
checks+=("database_started")
compose exec -T db psql -v ON_ERROR_STOP=1 -U forgebase_lab -d forgebase_lab <<'SQL'
CREATE TABLE alembic_version (version_num varchar(64) PRIMARY KEY);
INSERT INTO alembic_version VALUES ('restore_lab_head');
CREATE TABLE tenants (id integer PRIMARY KEY, name text NOT NULL);
CREATE TABLE users (id integer PRIMARY KEY, tenant_id integer NOT NULL);
CREATE TABLE visitors (id integer PRIMARY KEY, tenant_id integer NOT NULL);
CREATE TABLE tracking_events (id integer PRIMARY KEY, visitor_id integer NOT NULL);
CREATE TABLE rfq_requests (id integer PRIMARY KEY, tenant_id integer NOT NULL);
CREATE TABLE restore_lab_canary (id integer PRIMARY KEY, payload text NOT NULL);
INSERT INTO tenants VALUES (1, 'ForgeBase Lab');
INSERT INTO users VALUES (1, 1), (2, 1);
INSERT INTO visitors VALUES (1, 1), (2, 1), (3, 1);
INSERT INTO tracking_events VALUES (1, 1), (2, 1), (3, 2), (4, 3);
INSERT INTO rfq_requests VALUES (1, 1);
INSERT INTO restore_lab_canary VALUES (1, 'must survive backup and restore');
SQL

export FORGEBASE_COMPOSE_FILE="$compose_file"
export FORGEBASE_ENV_FILE="$env_file"
export FORGEBASE_API_ENV_FILE="$api_env_file"
export FORGEBASE_BACKUP_DIR="$backup_dir"
export FORGEBASE_BACKUP_STAMP="lab-$RANDOM"
export FORGEBASE_COMPOSE_PROJECT_NAME="$project"
export FORGEBASE_RESTORE_EVIDENCE_DIR="$restore_evidence_dir"
export FORGEBASE_ROLLBACK_EVIDENCE_DIR="$rollback_evidence_dir"
export FORGEBASE_ROLLBACK_HEALTH_ATTEMPTS=5
export FORGEBASE_ROLLBACK_HEALTH_DELAY_SECONDS=1

bash "$repo_dir/deploy/backup.sh"
backup_file="$(find "$backup_dir" -maxdepth 1 -name 'database-*.sql.gz' -print -quit)"
test -f "$backup_file"
backup_manifest="${backup_file%.sql.gz}.manifest.json"
test -f "$backup_manifest"
python3 - "$backup_manifest" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload["status"] == "passed"
assert payload["offsite_status"] == "not_configured"
assert payload["alembic_version"] == "restore_lab_head"
assert payload["critical_row_counts"]["tenants"] == 1
PY
checks+=("backup_manifest_created")
backup_checksum="$(sha256sum "$backup_file" | awk '{print $1}')"
if bash "$repo_dir/deploy/backup.sh" >/dev/null 2>&1; then
  printf 'Backup unexpectedly overwrote an existing recovery point.\n' >&2
  exit 1
fi
test "$(sha256sum "$backup_file" | awk '{print $1}')" = "$backup_checksum"
checks+=("backup_overwrite_blocked")

corrupt_dir="$work_dir/corrupt"
mkdir -p "$corrupt_dir"
cp "$backup_file" "$corrupt_dir/corrupt.sql.gz"
cp "$backup_manifest" "$corrupt_dir/corrupt.manifest.json"
python3 - "$corrupt_dir/corrupt.sql.gz" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = bytearray(path.read_bytes())
payload[len(payload) // 2] ^= 1
path.write_bytes(payload)
PY
if bash "$repo_dir/deploy/restore-drill.sh" --local \
  "$corrupt_dir/corrupt.sql.gz" >/dev/null 2>&1; then
  printf 'Corrupted backup unexpectedly restored.\n' >&2
  exit 1
fi
checks+=("corrupted_backup_rejected")

compose exec -T db psql -v ON_ERROR_STOP=1 -U forgebase_lab -d forgebase_lab \
  -c "INSERT INTO tenants VALUES (2, 'Post-backup mutation');" >/dev/null
bash "$repo_dir/deploy/restore-drill.sh" --local "$backup_file"
restore_evidence="$(find "$restore_evidence_dir" -name 'restore-drill-*.json' -print -quit)"
test -f "$restore_evidence"
python3 - "$restore_evidence" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload["status"] == "passed"
assert payload["alembic_version"] == "restore_lab_head"
assert payload["critical_row_counts"]["tenants"] == 1
assert payload["critical_row_counts"]["users"] == 2
assert payload["critical_row_counts"]["tracking_events"] == 4
assert payload["critical_row_counts"]["rfq_requests"] == 1
assert payload["disposable_database_removed"] is True
PY
checks+=("point_in_time_restore_verified")
remaining_drills="$(compose exec -T db psql -At -U forgebase_lab -d forgebase_lab \
  -c "SELECT count(*) FROM pg_database WHERE datname LIKE 'forgebase_restore_drill_%';")"
test "$remaining_drills" = "0"
checks+=("disposable_database_removed")

docker pull alpine:3.20 >/dev/null
docker pull alpine:3.21 >/dev/null
docker image tag alpine:3.20 forgebase-rollback-lab-api-old:local
docker image tag alpine:3.20 forgebase-rollback-lab-web-old:local
docker image tag alpine:3.21 forgebase-rollback-lab-api-target:local
docker image tag alpine:3.21 forgebase-rollback-lab-web-target:local
compose up -d api web caddy
cat > "$manifest" <<'MANIFEST'
api|forgebase-rollback-lab-api-old:local|forgebase-rollback-lab-api-target:local
web|forgebase-rollback-lab-web-old:local|forgebase-rollback-lab-web-target:local
MANIFEST

bad_manifest="$work_dir/bad-target.manifest"
cat > "$bad_manifest" <<'MANIFEST'
web|forgebase-rollback-lab-web-old:local|attacker-controlled-target:latest
MANIFEST
if bash "$repo_dir/deploy/rollback.sh" --dry-run \
  "$bad_manifest" >/dev/null 2>&1; then
  printf 'Rollback with a mismatched Compose target unexpectedly passed.\n' >&2
  exit 1
fi
checks+=("rollback_target_mismatch_rejected")

if bash "$repo_dir/deploy/rollback.sh" --dry-run "$manifest" >/dev/null 2>&1; then
  printf 'Rollback without API schema approval unexpectedly passed.\n' >&2
  exit 1
fi
checks+=("api_schema_approval_required")

old_api_id="$(docker image inspect --format '{{.Id}}' forgebase-rollback-lab-api-old:local)"
current_target_id="$(docker image inspect --format '{{.Id}}' forgebase-rollback-lab-api-target:local)"
test "$old_api_id" != "$current_target_id"
bash "$repo_dir/deploy/rollback.sh" --dry-run \
  --approve-api-schema-compatibility "$manifest" >/dev/null
test "$(docker image inspect --format '{{.Id}}' forgebase-rollback-lab-api-target:local)" \
  = "$current_target_id"
checks+=("rollback_dry_run_non_mutating")

bash "$repo_dir/deploy/rollback.sh" \
  --approve-api-schema-compatibility "$manifest"
api_container="$(compose ps -q api)"
web_container="$(compose ps -q web)"
test "$(docker inspect --format '{{.Image}}' "$api_container")" = "$old_api_id"
test "$(docker inspect --format '{{.Image}}' "$web_container")" = \
  "$(docker image inspect --format '{{.Id}}' forgebase-rollback-lab-web-old:local)"
checks+=("application_images_rolled_back")
test -n "$(find "$rollback_evidence_dir" -name 'rollback-*.json' -print -quit)"
checks+=("rollback_evidence_created")

checks_csv="$(IFS=,; printf '%s' "${checks[*]}")"
python3 - "$artifacts_dir" "$checks_csv" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

artifacts = Path(sys.argv[1])
checks = list(filter(None, sys.argv[2].split(",")))
payload = {
    "schema_version": 1,
    "lab": "restore-rollback",
    "status": "passed",
    "finished_at": datetime.now(timezone.utc).isoformat(),
    "summary": {"total": len(checks), "passed": len(checks), "failed": 0},
    "checks": checks,
    "production_resources_touched": False,
}
(artifacts / "restore-rollback-lab.json").write_text(
    json.dumps(payload, indent=2) + "\n", encoding="utf-8"
)
suite = ElementTree.Element(
    "testsuite",
    {
        "name": "restore-rollback-lab",
        "tests": str(len(checks)),
        "failures": "0",
        "errors": "0",
    },
)
for check in checks:
    ElementTree.SubElement(
        suite, "testcase", {"classname": "operations.recovery", "name": check}
    )
ElementTree.ElementTree(suite).write(
    artifacts / "restore-rollback-lab.junit.xml",
    encoding="utf-8",
    xml_declaration=True,
)
PY
printf 'Restore/Rollback lab passed: %s checks. Artifacts: %s\n' \
  "${#checks[@]}" "$artifacts_dir"
