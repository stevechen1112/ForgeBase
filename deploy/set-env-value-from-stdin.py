#!/usr/bin/env python3
"""Set one allow-listed secret in an env file without exposing it in argv."""

from __future__ import annotations

import os
from pathlib import Path
import sys


ALLOWED_KEYS = {
    "RESEND_WEBHOOK_SECRET",
    "TURNSTILE_SITE_KEY",
    "TURNSTILE_SECRET_KEY",
    "EMAIL_INTERNAL_RECIPIENT_ALLOWLIST",
    "SALES_NOTIFY_EMAIL",
    "EMAIL_DRY_RUN",
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
    "R2_PUBLIC_URL",
    "BACKUP_S3_ENDPOINT_URL",
    "BACKUP_S3_ACCESS_KEY_ID",
    "BACKUP_S3_SECRET_ACCESS_KEY",
    "BACKUP_S3_BUCKET_NAME",
    "OPS_ALERT_WEBHOOK_URL",
    "EXTERNAL_MONITOR_NAME",
    "NEXT_PUBLIC_TENANT_SLUG",
}


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: set-env-value-from-stdin.py ENV_FILE KEY")

    env_path = Path(sys.argv[1]).resolve()
    key = sys.argv[2]
    if key not in ALLOWED_KEYS:
        raise SystemExit("key is not allow-listed")

    # Windows PowerShell may prefix redirected UTF-8 stdin with a BOM.  A BOM
    # is invisible in an env file but breaks URLs and credentials at runtime.
    value = sys.stdin.read().strip().lstrip("\ufeff")
    if not value or "\n" in value or "\r" in value:
        raise SystemExit("secret value is empty or malformed")

    existing = env_path.read_text(encoding="utf-8").splitlines()
    replacement = f"{key}={value}"
    updated: list[str] = []
    found = False
    for line in existing:
        if line.startswith(f"{key}="):
            if not found:
                updated.append(replacement)
                found = True
            continue
        updated.append(line)
    if not found:
        updated.append(replacement)

    temporary = env_path.with_suffix(env_path.suffix + ".tmp")
    temporary.write_text("\n".join(updated) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(env_path)
    os.chmod(env_path, 0o600)
    print(f"Updated {key}; value not displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
