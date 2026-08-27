#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

usage() {
  printf 'Usage: %s --local <database.sql.gz> | --offsite <object-key>\n' "$0" >&2
  exit 2
}

mode=""
source_value=""
if [ "$#" -eq 1 ]; then
  mode="offsite"
  source_value="$1"
elif [ "$#" -eq 2 ]; then
  case "$1" in
    --local) mode="local" ;;
    --offsite) mode="offsite" ;;
    *) usage ;;
  esac
  source_value="$2"
else
  usage
fi
test -n "$source_value"

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="${FORGEBASE_COMPOSE_FILE:-$repo_dir/docker-compose.prod.yml}"
env_file="${FORGEBASE_ENV_FILE:-$repo_dir/.env}"
api_env_file="${FORGEBASE_API_ENV_FILE:-$repo_dir/deploy/api.env}"
backup_dir="${FORGEBASE_BACKUP_DIR:-$repo_dir/backups}"
evidence_dir="${FORGEBASE_RESTORE_EVIDENCE_DIR:-$backup_dir/restore-drills}"
stamp="$(date -u +%Y%m%d%H%M%S)"
drill_id="${stamp}_$RANDOM"
drill_db="forgebase_restore_drill_$drill_id"
drill_database_removed=false
drill_dir="$(mktemp -d)"
downloaded_file="$drill_dir/restore.sql.gz"
project_args=()
if [ -n "${FORGEBASE_COMPOSE_PROJECT_NAME:-}" ]; then
  project_args=(--project-name "$FORGEBASE_COMPOSE_PROJECT_NAME")
fi
compose() {
  API_ENV_FILE="$api_env_file" docker compose "${project_args[@]}" \
    --env-file "$env_file" -f "$compose_file" "$@"
}

case "$drill_db" in forgebase_restore_drill_*) ;; *) exit 1 ;; esac
cleanup() {
  if [ -n "${db_user:-}" ] && [ "$drill_database_removed" != true ]; then
    compose exec -T db dropdb -U "$db_user" --if-exists "$drill_db" \
      >/dev/null 2>&1 || true
  fi
  case "$drill_dir" in
    /tmp/*|/var/tmp/*|/private/tmp/*) rm -rf -- "$drill_dir" ;;
  esac
}
trap cleanup EXIT

test -f "$env_file"
test -f "$compose_file"
mkdir -p "$evidence_dir"
started_epoch="$(date +%s)"

manifest_file=""
if [ "$mode" = "local" ]; then
  backup_file="$source_value"
  test -f "$backup_file"
  candidate_manifest="${backup_file%.sql.gz}.manifest.json"
  if [ -f "$candidate_manifest" ]; then
    manifest_file="$candidate_manifest"
  fi
else
  backup_file="$downloaded_file"
  compose run --rm --no-deps -v "$drill_dir:/drill" api \
    python scripts/offsite_backup.py download "$source_value" /drill/restore.sql.gz
fi

gzip -t "$backup_file"
actual_checksum="$(sha256sum "$backup_file" | awk '{print $1}')"
expected_checksum=""
expected_schema_head=""
expected_table_count=""
expected_counts_json="{}"
backup_created_at=""
if [ -n "$manifest_file" ]; then
  mapfile -t manifest_values < <(python3 - "$manifest_file" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
if payload.get("schema_version") != 1 or payload.get("status") != "passed":
    raise SystemExit("Unsupported or failed backup manifest")
print(payload.get("sha256", ""))
print(payload.get("alembic_version", ""))
print(payload.get("public_table_count", ""))
print(json.dumps(payload.get("critical_row_counts", {}), sort_keys=True))
print(payload.get("created_at", ""))
PY
  )
  expected_checksum="${manifest_values[0]:-}"
  expected_schema_head="${manifest_values[1]:-}"
  expected_table_count="${manifest_values[2]:-}"
  expected_counts_json="${manifest_values[3]:-\{\}}"
  backup_created_at="${manifest_values[4]:-}"
  test "$actual_checksum" = "$expected_checksum"
fi

# Variable expands inside the db container.
# shellcheck disable=SC2016
db_user="$(compose exec -T db sh -c 'printf "%s" "$POSTGRES_USER"')"
test -n "$db_user"
compose exec -T db createdb -U "$db_user" "$drill_db"
gzip -dc "$backup_file" | compose exec -T db \
  psql -v ON_ERROR_STOP=1 -U "$db_user" -d "$drill_db" >/dev/null

table_count="$(compose exec -T db psql -At -U "$db_user" -d "$drill_db" \
  -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")"
test "$table_count" -gt 0
schema_head="$(compose exec -T db psql -At -U "$db_user" -d "$drill_db" \
  -c "SELECT version_num FROM alembic_version LIMIT 1;")"
test -n "$schema_head"
if [ -n "$expected_schema_head" ]; then
  test "$schema_head" = "$expected_schema_head"
  test "$table_count" = "$expected_table_count"
fi

critical_counts=()
for table in tenants users visitors tracking_events company_identifications \
  contact_candidates journey_snapshots outreach_messages inbound_replies rfq_requests; do
  exists="$(compose exec -T db psql -At -U "$db_user" -d "$drill_db" \
    -c "SELECT to_regclass('public.$table') IS NOT NULL;")"
  if [ "$exists" = "t" ]; then
    count="$(compose exec -T db psql -At -U "$db_user" -d "$drill_db" \
      -c "SELECT count(*) FROM $table;")"
    critical_counts+=("$table=$count")
  fi
done
actual_counts_csv="$(IFS=,; printf '%s' "${critical_counts[*]}")"
python3 - "$expected_counts_json" "$actual_counts_csv" <<'PY'
import json
import sys

expected = json.loads(sys.argv[1])
actual = {}
for item in filter(None, sys.argv[2].split(",")):
    table, count = item.split("=", 1)
    actual[table] = int(count)
if expected and actual != expected:
    raise SystemExit(f"Critical row count mismatch: expected={expected}, actual={actual}")
PY

compose exec -T db dropdb -U "$db_user" "$drill_db"
remaining_drill="$(compose exec -T db psql -At -U "$db_user" -d postgres \
  -c "SELECT count(*) FROM pg_database WHERE datname = '$drill_db';")"
test "$remaining_drill" = "0"
drill_database_removed=true

finished_epoch="$(date +%s)"
duration_seconds="$((finished_epoch - started_epoch))"
evidence_file="$evidence_dir/restore-drill-$drill_id.json"
python3 - "$evidence_file" "$mode" "$actual_checksum" "$schema_head" \
  "$table_count" "$actual_counts_csv" "$duration_seconds" "$backup_created_at" \
  "$drill_database_removed" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    evidence_file,
    source_mode,
    checksum,
    schema_head,
    table_count,
    counts_csv,
    duration_seconds,
    backup_created_at,
    drill_database_removed,
) = sys.argv[1:]
counts = {}
for item in filter(None, counts_csv.split(",")):
    table, count = item.split("=", 1)
    counts[table] = int(count)
rpo_seconds = None
if backup_created_at:
    created = datetime.fromisoformat(backup_created_at.replace("Z", "+00:00"))
    rpo_seconds = max(0, int((datetime.now(timezone.utc) - created).total_seconds()))
payload = {
    "schema_version": 1,
    "lab": "database-restore-drill",
    "status": "passed",
    "finished_at": datetime.now(timezone.utc).isoformat(),
    "source_mode": source_mode,
    "sha256": checksum,
    "alembic_version": schema_head,
    "public_table_count": int(table_count),
    "critical_row_counts": counts,
    "rto_seconds": int(duration_seconds),
    "backup_age_seconds": rpo_seconds,
    "disposable_database_removed": drill_database_removed == "true",
}
Path(evidence_file).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

printf 'Restore drill passed: %s tables, alembic %s, RTO %ss. Evidence: %s\n' \
  "$table_count" "$schema_head" "$duration_seconds" "$evidence_file"
