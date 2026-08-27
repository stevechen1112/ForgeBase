#!/usr/bin/env bash
set -Eeuo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_dir/docker-compose.prod.yml"
backup_dir="$repo_dir/backups"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"

test -f "$repo_dir/.env"
docker compose --env-file "$repo_dir/.env" -f "$compose_file" exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$backup_dir/database-$stamp.sql.gz"
# Preserve the deployment shape without expanding service env files or
# interpolation values into a backup artifact that may later be copied.
docker compose --env-file "$repo_dir/.env" -f "$compose_file" config \
  --no-interpolate --no-env-resolution > "$backup_dir/compose-$stamp.yml"
if grep -Eq '^BACKUP_S3_BUCKET_NAME=.+$' "$repo_dir/deploy/api.env"; then
  docker compose --env-file "$repo_dir/.env" -f "$compose_file" run --rm --no-deps \
    -v "$backup_dir:/backups" api \
    python scripts/offsite_backup.py upload "/backups/database-$stamp.sql.gz"
else
  printf 'Off-site backup skipped: BACKUP_S3_BUCKET_NAME is not configured.\n' >&2
fi
printf '%s\n' "$backup_dir/database-$stamp.sql.gz"
