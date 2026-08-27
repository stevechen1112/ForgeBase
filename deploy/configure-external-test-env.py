"""Add safe external-test defaults without replacing existing production secrets."""
from __future__ import annotations

import argparse
import base64
import secrets
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("env_file", type=Path)
    args = parser.parse_args()
    content = args.env_file.read_text(encoding="utf-8")
    existing = {line.split("=", 1)[0].strip() for line in content.splitlines() if "=" in line}
    defaults = {
        "EMAIL_EXTERNAL_DELIVERY_ENABLED": "false",
        "EMAIL_INTERNAL_RECIPIENT_ALLOWLIST": "",
        "RESEND_WEBHOOK_SECRET": "",
        "TURNSTILE_ALLOWED_HOSTNAMES": "pcbrm.tw,axisform.172-233-64-5.sslip.io",
        "TURNSTILE_EXPECTED_ACTION": "rfq_submit",
        "SYNTHETIC_TEST_TOKEN": secrets.token_urlsafe(32),
        "BACKUP_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        "EXTERNAL_MONITOR_NAME": "",
    }
    additions = [f"{key}={value}" for key, value in defaults.items() if key not in existing]
    if additions:
        content = content.rstrip() + "\n\n# External-test hardening\n" + "\n".join(additions) + "\n"
        args.env_file.write_text(content, encoding="utf-8")
    print(f"Configured {len(additions)} missing external-test settings; existing values preserved.")


if __name__ == "__main__":
    main()
