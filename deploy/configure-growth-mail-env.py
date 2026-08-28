#!/usr/bin/env python3
"""Atomically configure growth-mail prerequisites without printing secrets."""

from __future__ import annotations

import argparse
import os
import secrets
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

SECRET_LENGTH = 48


def _parse(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _replace(lines: list[str], updates: dict[str, str]) -> list[str]:
    remaining = dict(updates)
    rendered: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            rendered.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key not in updates:
            rendered.append(line)
            continue
        if key not in seen:
            rendered.append(f"{key}={updates[key]}")
            seen.add(key)
            remaining.pop(key, None)
    if rendered and rendered[-1] != "":
        rendered.append("")
    rendered.extend(f"{key}={value}" for key, value in remaining.items())
    return rendered


def _valid_public_url(value: str) -> bool:
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and port in {None, 443}
        and parsed.username is None
        and parsed.password is None
        and parsed.query == ""
        and parsed.fragment == ""
        and parsed.path in {"", "/"}
    )


def _valid_domain(value: str) -> bool:
    labels = value.rstrip(".").lower().split(".")
    return (
        value.isascii()
        and len(value.rstrip(".")) <= 253
        and len(labels) >= 2
        and all(
            label
            and len(label) <= 63
            and label[0].isalnum()
            and label[-1].isalnum()
            and all(char.isalnum() or char == "-" for char in label)
            for label in labels
        )
    )


def configure(
    env_path: Path,
    *,
    public_base_url: str,
    inbound_domain: str | None = None,
) -> dict[str, bool]:
    public_base_url = public_base_url.rstrip("/")
    if not _valid_public_url(public_base_url):
        raise ValueError("public base URL must be an origin-only HTTPS URL")
    if inbound_domain is not None:
        inbound_domain = inbound_domain.rstrip(".").lower()
        if not _valid_domain(inbound_domain):
            raise ValueError("inbound domain is invalid")

    lines = env_path.read_text(encoding="utf-8").splitlines()
    existing = _parse(lines)
    unsubscribe_secret = existing.get("OUTREACH_UNSUBSCRIBE_SECRET", "")
    unsubscribe_rotated = len(unsubscribe_secret) < 32
    if unsubscribe_rotated:
        unsubscribe_secret = secrets.token_urlsafe(SECRET_LENGTH)

    updates = {
        "OUTREACH_PUBLIC_BASE_URL": public_base_url,
        "OUTREACH_UNSUBSCRIBE_SECRET": unsubscribe_secret,
    }
    inbound_rotated = False
    if inbound_domain is not None:
        inbound_secret = existing.get("OUTREACH_INBOUND_SECRET", "")
        inbound_rotated = len(inbound_secret) < 32
        if inbound_rotated:
            inbound_secret = secrets.token_urlsafe(SECRET_LENGTH)
        updates.update(
            {
                "OUTREACH_INBOUND_DOMAIN": inbound_domain,
                "OUTREACH_INBOUND_SECRET": inbound_secret,
            }
        )

    rendered = "\n".join(_replace(lines, updates)).rstrip("\n") + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{env_path.name}.", dir=env_path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, env_path)
        os.chmod(env_path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)

    return {
        "public_base_url_configured": True,
        "unsubscribe_secret_configured": True,
        "unsubscribe_secret_generated": unsubscribe_rotated,
        "inbound_domain_configured": inbound_domain is not None,
        "inbound_secret_configured": inbound_domain is not None,
        "inbound_secret_generated": inbound_rotated,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--public-base-url", required=True)
    parser.add_argument("--inbound-domain")
    args = parser.parse_args()
    result = configure(
        args.env_file.resolve(),
        public_base_url=args.public_base_url,
        inbound_domain=args.inbound_domain,
    )
    for key, value in result.items():
        print(f"{key}={str(value).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
