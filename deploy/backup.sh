#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="${FORGEBASE_COMPOSE_FILE:-$repo_dir/docker-compose.prod.yml}"
env_file="${FORGEBASE_ENV_FILE:-$repo_dir/.env}"
api_env_file="${FORGEBASE_API_ENV_FILE:-$repo_dir/deploy/api.env}"
backup_dir="${FORGEBASE_BACKUP_DIR:-$repo_dir/backups}"
stamp="${FORGEBASE_BACKUP_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
database_file="$backup_dir/database-$stamp.sql.gz"
partial_file="$database_file.partial"
compose_snapshot="$backup_dir/compose-$stamp.yml"
manifest_file="$backup_dir/database-$stamp.manifest.json"
api_runtime_uid="${FORGEBASE_API_RUNTIME_UID:-10001}"
api_runtime_gid="${FORGEBASE_API_RUNTIME_GID:-10001}"
database_permissions_delegated=false
database_original_uid=""
database_original_gid=""
database_original_mode=""
case "$api_runtime_uid" in ''|*[!0-9]*) printf 'Invalid API runtime UID.\n' >&2; exit 1 ;; esac
case "$api_runtime_gid" in ''|*[!0-9]*) printf 'Invalid API runtime GID.\n' >&2; exit 1 ;; esac
if ! test "$api_runtime_uid" -gt 0; then
  printf 'Invalid API runtime UID.\n' >&2
  exit 1
fi
if ! test "$api_runtime_gid" -gt 0; then
  printf 'Invalid API runtime GID.\n' >&2
  exit 1
fi
project_args=()
if [ -n "${FORGEBASE_COMPOSE_PROJECT_NAME:-}" ]; then
  project_args=(--project-name "$FORGEBASE_COMPOSE_PROJECT_NAME")
fi

compose() {
  API_ENV_FILE="$api_env_file" docker compose "${project_args[@]}" \
    --env-file "$env_file" -f "$compose_file" "$@"
}

test -f "$env_file"
test -f "$compose_file"
mkdir -p "$backup_dir"
for target in "$database_file" "$compose_snapshot" "$manifest_file"; do
  if [ -e "$target" ]; then
    printf 'Refusing to overwrite existing backup artifact: %s\n' "$target" >&2
    exit 1
  fi
done
restore_database_permissions() {
  if [ "$database_permissions_delegated" = true ] && [ -e "$database_file" ]; then
    chown -- "$database_original_uid:$database_original_gid" "$database_file"
    chmod -- "$database_original_mode" "$database_file"
    database_permissions_delegated=false
  fi
}
cleanup() {
  rm -f -- "$partial_file"
  restore_database_permissions || true
}
trap cleanup EXIT

# Variables expand inside the db container.
# shellcheck disable=SC2016
db_user="$(compose exec -T db sh -c 'printf "%s" "$POSTGRES_USER"')"
# Variables expand inside the db container.
# shellcheck disable=SC2016
db_name="$(compose exec -T db sh -c 'printf "%s" "$POSTGRES_DB"')"
test -n "$db_user"
test -n "$db_name"

schema_head="$(compose exec -T db psql -At -U "$db_user" -d "$db_name" \
  -c "SELECT version_num FROM alembic_version LIMIT 1;")"
test -n "$schema_head"
table_count="$(compose exec -T db psql -At -U "$db_user" -d "$db_name" \
  -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")"
test "$table_count" -gt 0

critical_counts=()
for table in tenants users visitors tracking_events company_identifications \
  contact_candidates journey_snapshots outreach_messages inbound_replies rfq_requests; do
  exists="$(compose exec -T db psql -At -U "$db_user" -d "$db_name" \
    -c "SELECT to_regclass('public.$table') IS NOT NULL;")"
  if [ "$exists" = "t" ]; then
    count="$(compose exec -T db psql -At -U "$db_user" -d "$db_name" \
      -c "SELECT count(*) FROM $table;")"
    critical_counts+=("$table=$count")
  fi
done
critical_counts_csv="$(IFS=,; printf '%s' "${critical_counts[*]}")"

compose exec -T db pg_dump -U "$db_user" -d "$db_name" \
  --no-owner --no-privileges | gzip -9 > "$partial_file"
gzip -t "$partial_file"
mv -- "$partial_file" "$database_file"
checksum="$(sha256sum "$database_file" | awk '{print $1}')"
compressed_bytes="$(wc -c < "$database_file" | tr -d ' ')"
test "$compressed_bytes" -gt 0

# Preserve the deployment shape without expanding service env files or
# interpolation values into an artifact that may later be copied.
compose config --no-interpolate --no-env-resolution > "$compose_snapshot"

offsite_object_key=""
offsite_configured=false
if [ -f "$api_env_file" ] &&
  grep -Eq '^BACKUP_S3_BUCKET_NAME=.+$' "$api_env_file"; then
  offsite_configured=true
fi
python3 - "$manifest_file" "$database_file" "$compose_snapshot" "$checksum" \
  "$compressed_bytes" "$schema_head" "$table_count" "$critical_counts_csv" \
  "$offsite_object_key" "$offsite_configured" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    manifest,
    database_file,
    compose_snapshot,
    checksum,
    compressed_bytes,
    schema_head,
    table_count,
    critical_counts_csv,
    offsite_object_key,
    offsite_configured,
) = sys.argv[1:]
critical_counts = {}
for item in filter(None, critical_counts_csv.split(",")):
    table, count = item.split("=", 1)
    critical_counts[table] = int(count)
payload = {
    "schema_version": 1,
    "status": "passed",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "database_file": Path(database_file).name,
    "compose_snapshot": Path(compose_snapshot).name,
    "sha256": checksum,
    "compressed_bytes": int(compressed_bytes),
    "alembic_version": schema_head,
    "public_table_count": int(table_count),
    "critical_row_counts": critical_counts,
    "offsite_object_key": offsite_object_key or None,
    "offsite_status": "pending" if offsite_configured == "true" else "not_configured",
}
Path(manifest).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

# The local manifest is durable before attempting the network transfer. A
# configured off-site upload still fails the deployment, but never erases the
# usable local recovery metadata.
if [ "$offsite_configured" = true ]; then
  # The backup is created with umask 077 by the deployment user. Delegate only
  # this file to the non-root API utility process, expose it read-only, and
  # restore the exact original owner/mode even when the upload is interrupted.
  database_original_uid="$(stat -c '%u' -- "$database_file")"
  database_original_gid="$(stat -c '%g' -- "$database_file")"
  database_original_mode="$(stat -c '%a' -- "$database_file")"
  database_permissions_delegated=true
  chown -- "$api_runtime_uid:$api_runtime_gid" "$database_file"
  chmod -- 0400 "$database_file"
  if offsite_object_key="$(compose run --rm --no-deps \
    -v "$database_file:/backups/database.sql.gz:ro" api \
    python scripts/offsite_backup.py upload /backups/database.sql.gz)"; then
    offsite_status="passed"
  else
    offsite_status="failed"
  fi
  restore_database_permissions
  python3 - "$manifest_file" "$offsite_object_key" "$offsite_status" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
payload["offsite_object_key"] = sys.argv[2] or None
payload["offsite_status"] = sys.argv[3]
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
  if [ "$offsite_status" != "passed" ]; then
    printf 'Configured off-site backup upload failed; local recovery point remains valid.\n' >&2
    exit 1
  fi
else
  printf 'Off-site backup skipped: BACKUP_S3_BUCKET_NAME is not configured.\n' >&2
fi

printf 'Backup passed: %s (sha256=%s, tables=%s, alembic=%s)\n' \
  "$database_file" "$checksum" "$table_count" "$schema_head"
printf '%s\n' "$database_file"
