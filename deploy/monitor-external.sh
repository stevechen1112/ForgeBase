#!/usr/bin/env bash
set -Eeuo pipefail

base_url="${1:-https://pcbrm.tw}"
axis_url="${2:-https://axisform.172-233-64-5.sslip.io}"
failed=0

check() {
  label="$1"
  url="$2"
  if curl --fail --silent --show-error --location --max-time 15 "$url" >/dev/null; then
    printf 'ok      %s %s\n' "$label" "$url"
  else
    printf 'failed  %s %s\n' "$label" "$url" >&2
    failed=1
  fi
}

check "ForgeBase homepage" "$base_url/"
check "API liveness" "$base_url/health"
check "API core readiness" "$base_url/health/ready"
check "Admin login" "$base_url/backend/login"
check "NorthForge site" "$base_url/northforge-tools/en"
check "NorthForge asset probe" "$base_url/northforge-tools/api/health/assets"
check "AxisForm site" "$axis_url/en"
check "AxisForm asset probe" "$axis_url/api/health/assets"

exit "$failed"
