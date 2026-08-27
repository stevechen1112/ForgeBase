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

bash "$repo_dir/deploy/backup.sh"
# This production host has limited memory. Building several Next.js images in
# parallel can exhaust RAM/swap and make the running site temporarily
# unreachable. Build one release image at a time, while old containers stay
# online, and switch only after every image succeeds.
docker compose --env-file "$repo_dir/.env" -f "$compose_file" build migrate
for service in "${release_services[@]}"; do
  [ "$service" = "api" ] && continue  # migrate and api share forgebase-api
  docker compose --env-file "$repo_dir/.env" -f "$compose_file" build "$service"
done
docker compose --env-file "$repo_dir/.env" -f "$compose_file" run --rm migrate
# Switch the API first and wait for its own health check before touching any
# server-rendered website. A general `compose up` cannot be used yet because
# Caddy depends on web health and an old web process may still cache the API's
# retired container IP.
docker compose --env-file "$repo_dir/.env" -f "$compose_file" up -d --no-deps api
api_ready=false
for attempt in $(seq 1 18); do
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
docker compose --env-file "$repo_dir/.env" -f "$compose_file" up -d --remove-orphans
# Caddyfile is a bind mount. Recreate Caddy so a replaced config inode is never
# left pointing at the previous release during a managed-site delivery.
docker compose --env-file "$repo_dir/.env" -f "$compose_file" up -d --no-deps --force-recreate caddy

domain="$(sed -n 's/^DOMAIN=//p' "$repo_dir/.env" | tail -n 1)"
protocol="$(sed -n 's/^PROTOCOL=//p' "$repo_dir/.env" | tail -n 1)"
protocol="${protocol:-https}"
for attempt in $(seq 1 18); do
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
  if [ "$services_ready" = true ] && curl --fail --silent --show-error --max-time 8 "$protocol://$domain/health/ready" >/dev/null; then
    printf 'Deployment healthy. Rollback manifest: %s\n' "$manifest"
    exit 0
  fi
  sleep 5
done

printf 'Deployment readiness failed. Use deploy/rollback.sh %s after inspection.\n' "$manifest" >&2
exit 1
