#!/usr/bin/env bash
set -Eeuo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_dir/docker-compose.prod.yml"
# Docker repository/tag names must be lowercase.  Keep the timestamp readable
# while avoiding uppercase T/Z, otherwise rollback tagging aborts before backup.
stamp="$(date -u +%Y%m%dt%H%M%Sz)"
manifest="$repo_dir/backups/images-$stamp.manifest"
mkdir -p "$repo_dir/backups"
test -f "$repo_dir/.env"
test -f "$repo_dir/deploy/api.env"

mapfile -t release_services < <(
  docker compose --env-file "$repo_dir/.env" -f "$compose_file" config --services |
    while IFS= read -r service; do
      case "$service" in
        api|admin|web|web_*|marketing|templates) printf '%s\n' "$service" ;;
      esac
    done
)
if [ "${#release_services[@]}" -eq 0 ]; then
  printf 'No application services found in %s.\n' "$compose_file" >&2
  exit 1
fi

compose_json="$(docker compose --env-file "$repo_dir/.env" -f "$compose_file" config --format json)"
for service in "${release_services[@]}"; do
  image_id="$(docker compose --env-file "$repo_dir/.env" -f "$compose_file" images -q "$service" 2>/dev/null || true)"
  if [ -n "$image_id" ]; then
    rollback_tag="forgebase-rollback-$stamp-${service//_/-}"
    target_image="$(printf '%s' "$compose_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"][sys.argv[1]]["image"])' "$service")"
    docker image tag "$image_id" "$rollback_tag"
    printf '%s|%s|%s\n' "$service" "$rollback_tag" "$target_image" >> "$manifest"
  fi
done

# BuildKit keeps intermediate layers from every release. On the production
# host those caches are disposable, but over time they can consume the disk
# while the tagged rollback images and running containers still need to be
# preserved. Reclaim only builder cache before the first build and between
# sequential application builds; this does not remove images, containers,
# volumes, the database backup, or the rollback tags recorded above.
reclaim_build_cache() {
  docker builder prune --all --force
}
reclaim_build_cache

# Disk exhaustion can leave PostgreSQL replaying recovery records while the
# host comes back. Cache reclamation must happen before the backup attempt, and
# the deployment must wait for PostgreSQL to accept connections rather than
# failing immediately or attempting a migration during recovery.
database_ready=false
for _attempt in $(seq 1 24); do
  if docker compose --env-file "$repo_dir/.env" -f "$compose_file" \
    exec -T db pg_isready >/dev/null 2>&1; then
    database_ready=true
    break
  fi
  sleep 5
done
if [ "$database_ready" != true ]; then
  printf 'Database did not recover before the backup safety gate.\n' >&2
  exit 1
fi

bash "$repo_dir/deploy/backup.sh"

# This production host has limited memory. Building several Next.js images in
# parallel can exhaust RAM/swap and make the running site temporarily
# unreachable. Build one release image at a time, while old containers stay
# online, and switch only after every image succeeds.
docker compose --env-file "$repo_dir/.env" -f "$compose_file" build migrate
reclaim_build_cache
for service in "${release_services[@]}"; do
  [ "$service" = "api" ] && continue  # migrate and api share forgebase-api
  docker compose --env-file "$repo_dir/.env" -f "$compose_file" build "$service"
  reclaim_build_cache
done

# Migration 0102 intentionally removes legacy CRM-style RFQ fields.  Export
# them once, after the new API image exists but before any migration runs.  The
# full database backup above remains the recovery source; this protected JSON
# is a review-friendly audit export and is never uploaded as a CI artifact.
db_user="$(docker compose --env-file "$repo_dir/.env" -f "$compose_file" \
  exec -T db sh -c 'printf "%s" "$POSTGRES_USER"')"
db_name="$(docker compose --env-file "$repo_dir/.env" -f "$compose_file" \
  exec -T db sh -c 'printf "%s" "$POSTGRES_DB"')"
legacy_rfq_sales_schema="$(docker compose --env-file "$repo_dir/.env" -f "$compose_file" \
  exec -T db psql -At -U "$db_user" -d "$db_name" -c \
  "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='rfq_requests' AND column_name='quality_score');")"
if [ "$legacy_rfq_sales_schema" = "t" ]; then
  retired_export_name="retired-rfq-sales-$stamp.json"
  docker compose --env-file "$repo_dir/.env" -f "$compose_file" \
    run --rm --no-deps --user 0:0 \
    -v "$repo_dir/backups:/protected-exports" api \
    python scripts/export_retired_rfq_sales_data.py \
      --output "/protected-exports/$retired_export_name"
  test -s "$repo_dir/backups/$retired_export_name"
  chmod 0600 "$repo_dir/backups/$retired_export_name"
  printf 'Protected retired RFQ sales export passed: %s\n' "$retired_export_name"
else
  printf 'Protected retired RFQ sales export skipped: legacy columns are already absent.\n'
fi

# The uploads volume may have been created by an older root-running API.
# Normalize it with the already scanned API image before the non-root UID 10001
# starts; this is replay-safe and avoids weakening the volume to world-writable.
docker compose --env-file "$repo_dir/.env" -f "$compose_file" \
  run --rm --no-deps --user 0:0 api \
  sh -c 'chown -R 10001:10001 /app/uploads && chmod -R u+rwX,go-rwx /app/uploads'
docker compose --env-file "$repo_dir/.env" -f "$compose_file" run --rm migrate
# Switch the API first and wait for its own health check before touching any
# server-rendered website. A general `compose up` cannot be used yet because
# Caddy depends on web health and an old web process may still cache the API's
# retired container IP.
docker compose --env-file "$repo_dir/.env" -f "$compose_file" up -d --no-deps api
api_ready=false
for _attempt in $(seq 1 18); do
  api_container_id="$(docker compose --env-file "$repo_dir/.env" -f "$compose_file" ps -q api)"
  api_health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$api_container_id")"
  if [ "$api_health" = "healthy" ]; then
    api_ready=true
    break
  fi
  sleep 5
done
if [ "$api_ready" != true ]; then
  printf 'API did not become healthy before website switch.\n' >&2
  exit 1
fi

# Next.js server-side fetch may keep the resolved container IP for the API.
# When Compose recreates api but reuses an unchanged web image, the old web
# process can continue calling the retired IP and become unhealthy. Recreate
# every managed-site web process after the API switch so service discovery is
# refreshed on every release.
web_services=()
for service in "${release_services[@]}"; do
  case "$service" in web|web_*) web_services+=("$service") ;; esac
done
if [ "${#web_services[@]}" -gt 0 ]; then
  docker compose --env-file "$repo_dir/.env" -f "$compose_file" \
    up -d --no-deps --force-recreate "${web_services[@]}"
fi
# Keep the currently serving edge alive until every replacement dependency is
# healthy. A generic `compose up` includes Caddy and may stop it before Compose
# discovers an unhealthy website, turning a contained rollout failure into a
# whole-platform outage.
docker compose --env-file "$repo_dir/.env" -f "$compose_file" \
  up -d --remove-orphans db migrate "${release_services[@]}"

domain="$(sed -n 's/^DOMAIN=//p' "$repo_dir/.env" | tail -n 1)"
protocol="$(sed -n 's/^PROTOCOL=//p' "$repo_dir/.env" | tail -n 1)"
protocol="${protocol:-https}"
services_ready=false
for _attempt in $(seq 1 18); do
  services_ready=true
  for service in "${release_services[@]}"; do
    container_id="$(docker compose --env-file "$repo_dir/.env" -f "$compose_file" ps -q "$service")"
    if [ -z "$container_id" ]; then
      services_ready=false
      break
    fi
    state="$(docker inspect --format '{{.State.Status}}' "$container_id")"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")"
    if [ "$state" != "running" ] || { [ "$health" != "none" ] && [ "$health" != "healthy" ]; }; then
      services_ready=false
      break
    fi
  done
  [ "$services_ready" = true ] && break
  sleep 5
done

if [ "$services_ready" != true ]; then
  printf 'Deployment readiness failed before edge switch. Inspect migration compatibility, then use deploy/rollback.sh --approve-api-schema-compatibility %s.\n' "$manifest" >&2
  exit 1
fi

# Caddyfile is a bind mount. Recreate Caddy only after every replacement
# dependency is healthy, so the previous edge keeps serving during a failed
# rollout and a replaced config inode is picked up during a successful one.
docker compose --env-file "$repo_dir/.env" -f "$compose_file" up -d --no-deps --force-recreate caddy

edge_ready=false
for _attempt in $(seq 1 18); do
  if curl --fail --silent --show-error --max-time 8 "$protocol://$domain/health/ready" >/dev/null; then
    edge_ready=true
    break
  fi
  sleep 5
done
if [ "$edge_ready" != true ]; then
  printf 'Deployment edge readiness failed. Inspect Caddy without rolling back the migrated database; rollback manifest: %s.\n' "$manifest" >&2
  exit 1
fi

printf 'Deployment healthy. Rollback manifest: %s\n' "$manifest"
