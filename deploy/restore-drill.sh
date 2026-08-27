#!/usr/bin/env bash
set -Eeuo pipefail

if [ "$#" -ne 1 ]; then
  printf 'Usage: %s <off-site-object-key>\n' "$0" >&2
  exit 2
fi

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_dir/docker-compose.prod.yml"
object_key="$1"
stamp="$(date -u +%Y%m%d%H%M%S)"
drill_db="forgebase_restore_drill_$stamp"
drill_dir="$(mktemp -d)"
backup_file="$drill_dir/restore.sql.gz"

case "$drill_dir" in /tmp/*|/var/tmp/*) ;; *) printf 'Unsafe temporary path: %s\n' "$drill_dir" >&2; exit 1 ;; esac
cleanup() {
  docker compose --env-file "$repo_dir/.env" -f "$compose_file" exec -T db \
    dropdb -U "$(sed -n 's/^POSTGRES_USER=//p' "$repo_dir/.env" | tail -n 1)" --if-exists "$drill_db" >/dev/null 2>&1 || true
  rm -rf -- "$drill_dir"
}
trap cleanup EXIT

docker compose --env-file "$repo_dir/.env" -f "$compose_file" run --rm --no-deps \
  -v "$drill_dir:/drill" api \
  python scripts/offsite_backup.py download "$object_key" /drill/restore.sql.gz
gzip -t "$backup_file"
db_user="$(sed -n 's/^POSTGRES_USER=//p' "$repo_dir/.env" | tail -n 1)"
docker compose --env-file "$repo_dir/.env" -f "$compose_file" exec -T db createdb -U "$db_user" "$drill_db"
gzip -dc "$backup_file" | docker compose --env-file "$repo_dir/.env" -f "$compose_file" exec -T db \
  psql -v ON_ERROR_STOP=1 -U "$db_user" -d "$drill_db" >/dev/null
table_count="$(docker compose --env-file "$repo_dir/.env" -f "$compose_file" exec -T db \
  psql -At -U "$db_user" -d "$drill_db" -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")"
test "$table_count" -gt 0
printf 'Restore drill passed: %s tables restored into disposable database %s.\n' "$table_count" "$drill_db"
