#!/usr/bin/env python3
"""Open or close the inbound-only production acceptance window safely."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path


class WindowError(RuntimeError):
    pass


def _read(path: Path) -> tuple[list[str], dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return lines, values


def configure(path: Path, *, enabled: bool) -> dict[str, bool]:
    lines, values = _read(path)
    if values.get("EMAIL_EXTERNAL_DELIVERY_ENABLED", "false").lower() != "false":
        raise WindowError("external_delivery_switch_must_be_closed")
    if values.get("OUTREACH_SEND_ENABLED", "false").lower() != "false":
        raise WindowError("outreach_send_switch_must_be_closed")
    if not values.get("OUTREACH_INBOUND_DOMAIN", "").strip():
        raise WindowError("inbound_domain_missing")
    if len(values.get("OUTREACH_INBOUND_SECRET", "").strip()) < 32:
        raise WindowError("inbound_route_secret_missing")

    replacement = f"INBOUND_REPLY_ENABLED={'true' if enabled else 'false'}"
    found = False
    updated: list[str] = []
    for line in lines:
        if line.strip().startswith("INBOUND_REPLY_ENABLED="):
            updated.append(replacement)
            found = True
        else:
            updated.append(line)
    if not found:
        updated.append(replacement)

    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent), text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(updated) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {
        "external_delivery_enabled": False,
        "outreach_send_enabled": False,
        "inbound_reply_enabled": enabled,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--state", required=True, choices=("open", "closed"))
    args = parser.parse_args()
    result = configure(args.env_file, enabled=args.state == "open")
    print(
        "Controlled inbound window aligned: "
        f"inbound_reply_enabled={str(result['inbound_reply_enabled']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
