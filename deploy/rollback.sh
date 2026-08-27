#!/usr/bin/env bash
set -Eeuo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_dir/docker-compose.prod.yml"
manifest="${1:-}"
if [ -z "$manifest" ] || [ ! -f "$manifest" ]; then
  printf 'Usage: %s /absolute/path/to/images-TIMESTAMP.manifest\n' "$0" >&2
  exit 2
fi

restored_services=()
while IFS='|' read -r service image target_image; do
  # Backward compatibility with the original service=image manifests.
  if [ -z "$image" ] && [[ "$service" == *=* ]]; then
    image="${service#*=}"
    service="${service%%=*}"
  fi
  case "$service" in
    api|admin|web|web_*|marketing|templates)
      target_image="${target_image:-forgebase-${service//_/-}}"
      docker image tag "$image" "$target_image"
      restored_services+=("$service")
      ;;
  esac
done < "$manifest"
if [ "${#restored_services[@]}" -eq 0 ]; then
  printf 'No restorable services found in %s.\n' "$manifest" >&2
  exit 1
fi
docker compose --env-file "$repo_dir/.env" -f "$compose_file" up -d --no-build --force-recreate "${restored_services[@]}"
docker compose --env-file "$repo_dir/.env" -f "$compose_file" up -d --no-deps --force-recreate caddy
printf 'Application images restored. Database restoration is intentionally manual; review the migration before restoring a database backup.\n'
