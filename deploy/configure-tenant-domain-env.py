#!/usr/bin/env python3
"""Idempotently configure production tenant-domain routing without exposing secrets."""

from __future__ import annotations

import argparse
import os
import secrets
import tempfile
from pathlib import Path


PLACEHOLDER_VALUES = {
    "",
    "change_me",
    "change-me",
    "change_me_請使用高熵隨機值",
}


def _parse_env(text: str) -> tuple[list[str], dict[str, str]]:
    lines = text.splitlines()
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key and key.replace("_", "").isalnum():
            values[key] = value
    return lines, values


def configure_env(
    env_path: Path,
    *,
    base_domain: str,
    cname_target: str,
    resolver_url: str,
    timeout_seconds: int,
) -> dict[str, str]:
    if not env_path.is_file():
        raise FileNotFoundError(f"Production env file not found: {env_path}")

    original = env_path.read_text(encoding="utf-8")
    lines, values = _parse_env(original)
    current_secret = values.get("TENANT_ROUTING_SECRET", "").strip()
    if current_secret.lower() in PLACEHOLDER_VALUES or len(current_secret) < 43:
        current_secret = secrets.token_urlsafe(48)

    desired = {
        "TENANT_BASE_DOMAIN": base_domain.strip().lower().rstrip("."),
        "TENANT_CNAME_TARGET": cname_target.strip().lower().rstrip("."),
        "DOMAIN_DNS_RESOLVER_URL": resolver_url.strip(),
        "DOMAIN_DNS_TIMEOUT_SECONDS": str(timeout_seconds),
        "TENANT_ROUTING_SECRET": current_secret,
    }
    if not desired["TENANT_BASE_DOMAIN"] or not desired["TENANT_CNAME_TARGET"]:
        raise ValueError("Tenant base domain and CNAME target are required")
    if timeout_seconds < 1 or timeout_seconds > 30:
        raise ValueError("DNS timeout must be between 1 and 30 seconds")

    replaced: set[str] = set()
    updated_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0]
            if key in desired:
                if key in replaced:
                    continue
                updated_lines.append(f"{key}={desired[key]}")
                replaced.add(key)
                continue
        updated_lines.append(line)
    while updated_lines and updated_lines[-1] == "":
        updated_lines.pop()
    for key, value in desired.items():
        if key not in replaced:
            updated_lines.append(f"{key}={value}")
    rendered = "\n".join(updated_lines) + "\n"

    if rendered != original:
        fd, temp_name = tempfile.mkstemp(prefix=f".{env_path.name}.", dir=env_path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, env_path)
        finally:
            temp_path.unlink(missing_ok=True)

    return desired


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--base-domain", default="forgebase.com")
    parser.add_argument("--cname-target", default="edge.forgebase.com")
    parser.add_argument(
        "--resolver-url",
        default="https://cloudflare-dns.com/dns-query",
    )
    parser.add_argument("--timeout-seconds", type=int, default=8)
    args = parser.parse_args()
    configured = configure_env(
        args.env_file,
        base_domain=args.base_domain,
        cname_target=args.cname_target,
        resolver_url=args.resolver_url,
        timeout_seconds=args.timeout_seconds,
    )
    safe_keys = ", ".join(sorted(configured))
    print(f"Tenant-domain runtime configured: {safe_keys}")
    print("TENANT_ROUTING_SECRET is present; its value was not printed.")


if __name__ == "__main__":
    main()
