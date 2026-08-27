#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

usage() {
  printf 'Usage: %s [--dry-run] [--approve-api-schema-compatibility] <manifest>\n' "$0" >&2
  exit 2
}

dry_run=false
approve_api=false
manifest=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) dry_run=true ;;
    --approve-api-schema-compatibility) approve_api=true ;;
    -*) usage ;;
    *)
      [ -z "$manifest" ] || usage
      manifest="$1"
      ;;
  esac
  shift
done
if [ -z "$manifest" ] || [ ! -f "$manifest" ]; then
  usage
fi

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="${FORGEBASE_COMPOSE_FILE:-$repo_dir/docker-compose.prod.yml}"
env_file="${FORGEBASE_ENV_FILE:-$repo_dir/.env}"
api_env_file="${FORGEBASE_API_ENV_FILE:-$repo_dir/deploy/api.env}"
evidence_dir="${FORGEBASE_ROLLBACK_EVIDENCE_DIR:-$repo_dir/backups/rollback-drills}"
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
compose_json="$(compose config --format json)"
services=()
images=()
targets=()
declare -A seen=()
line_number=0
api_in_manifest=false

while IFS='|' read -r service image target_image; do
  line_number="$((line_number + 1))"
  [ -n "$service$image$target_image" ] || continue
  case "$service" in \#*) continue ;; esac
  # Backward compatibility with the original service=image manifests.
  if [ -z "$image" ] && [[ "$service" == *=* ]]; then
    image="${service#*=}"
    service="${service%%=*}"
  fi
  case "$service" in
    api|admin|web|web_*|marketing|templates) ;;
    *)
      printf 'Invalid rollback service on line %s: %s\n' \
        "$line_number" "$service" >&2
      exit 1
      ;;
  esac
  if [ -n "${seen[$service]:-}" ]; then
    printf 'Duplicate rollback service: %s\n' "$service" >&2
    exit 1
  fi
  seen["$service"]=1
  expected_target="$(printf '%s' "$compose_json" | python3 -c \
    'import json,sys; print(json.load(sys.stdin)["services"][sys.argv[1]]["image"])' \
    "$service")"
  target_image="${target_image:-$expected_target}"
  if [ "$target_image" != "$expected_target" ]; then
    printf 'Manifest target mismatch for %s: expected %s, got %s\n' \
      "$service" "$expected_target" "$target_image" >&2
    exit 1
  fi
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    printf 'Rollback image is missing for %s: %s\n' "$service" "$image" >&2
    exit 1
  fi
  services+=("$service")
  images+=("$image")
  targets+=("$target_image")
  if [ "$service" = "api" ]; then
    api_in_manifest=true
  fi
done < "$manifest"

if [ "${#services[@]}" -eq 0 ]; then
  printf 'No restorable services found in %s.\n' "$manifest" >&2
  exit 1
fi
if [ "$api_in_manifest" = true ] && [ "$approve_api" != true ]; then
  printf '%s\n' \
    'API rollback requires --approve-api-schema-compatibility after migration review.' >&2
  exit 1
fi

if [ "$dry_run" = true ]; then
  for index in "${!services[@]}"; do
    printf 'PLAN %s: %s -> %s\n' \
      "${services[$index]}" "${images[$index]}" "${targets[$index]}"
  done
  printf 'Rollback preflight passed; no image tags or containers were changed.\n'
  exit 0
fi

for index in "${!services[@]}"; do
  docker image tag "${images[$index]}" "${targets[$index]}"
done
compose up -d --no-build --force-recreate "${services[@]}"
if printf '%s' "$compose_json" | python3 -c \
  'import json,sys; raise SystemExit(0 if "caddy" in json.load(sys.stdin)["services"] else 1)'; then
  compose up -d --no-deps --force-recreate caddy
fi

attempts="${FORGEBASE_ROLLBACK_HEALTH_ATTEMPTS:-12}"
delay_seconds="${FORGEBASE_ROLLBACK_HEALTH_DELAY_SECONDS:-5}"
ready=false
for _attempt in $(seq 1 "$attempts"); do
  ready=true
  for service in "${services[@]}"; do
    container_id="$(compose ps -q "$service")"
    if [ -z "$container_id" ]; then
      ready=false
      break
    fi
    state="$(docker inspect --format '{{.State.Status}}' "$container_id")"
    health="$(docker inspect --format \
      '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
      "$container_id")"
    if [ "$state" != "running" ] ||
      { [ "$health" != "none" ] && [ "$health" != "healthy" ]; }; then
      ready=false
      break
    fi
  done
  [ "$ready" = true ] && break
  sleep "$delay_seconds"
done
if [ "$ready" != true ]; then
  printf 'Rollback containers did not become ready.\n' >&2
  exit 1
fi

mkdir -p "$evidence_dir"
stamp="$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
evidence_file="$evidence_dir/rollback-$stamp.json"
services_csv="$(IFS=,; printf '%s' "${services[*]}")"
python3 - "$evidence_file" "$manifest" "$services_csv" "$api_in_manifest" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

evidence_file, manifest, services_csv, api_in_manifest = sys.argv[1:]
payload = {
    "schema_version": 1,
    "lab": "application-image-rollback",
    "status": "passed",
    "finished_at": datetime.now(timezone.utc).isoformat(),
    "manifest": Path(manifest).name,
    "services": list(filter(None, services_csv.split(","))),
    "api_schema_compatibility_approved": api_in_manifest == "true",
    "database_restored": False,
}
Path(evidence_file).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
printf 'Application rollback passed. Evidence: %s\n' "$evidence_file"
printf '%s\n' \
  'Database was not restored; schema compatibility remains an explicit human decision.'
