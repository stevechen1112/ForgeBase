#!/usr/bin/env python3
"""Atomically configure growth-mail prerequisites without printing secrets."""

from __future__ import annotations

import argparse
import os
import re
import secrets
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

SECRET_LENGTH = 48
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+$")


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


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    local, separator, domain = normalized.partition("@")
    if (
        not normalized.isascii()
        or len(normalized) > 254
        or not separator
        or not local
        or not EMAIL_PATTERN.fullmatch(normalized)
        or not _valid_domain(domain)
    ):
        raise ValueError("growth mail identity email is invalid")
    return normalized


def _validate_sender_name(value: str) -> str:
    if any(char in value for char in "\r\n="):
        raise ValueError("growth mail sender name is invalid")
    normalized = " ".join(value.strip().split())
    if not 1 <= len(normalized) <= 100:
        raise ValueError("growth mail sender name is invalid")
    return normalized


def configure(
    env_path: Path,
    *,
    public_base_url: str,
    sender_email: str,
    sender_name: str,
    internal_recipient: str,
    sales_notify_email: str,
    manager_email: str,
    inbound_domain: str | None = None,
) -> dict[str, bool]:
    public_base_url = public_base_url.rstrip("/")
    if not _valid_public_url(public_base_url):
        raise ValueError("public base URL must be an origin-only HTTPS URL")
    if inbound_domain is not None:
        inbound_domain = inbound_domain.rstrip(".").lower()
        if not _valid_domain(inbound_domain):
            raise ValueError("inbound domain is invalid")
    sender_email = _normalize_email(sender_email)
    sender_name = _validate_sender_name(sender_name)
    internal_recipient = _normalize_email(internal_recipient)
    sales_notify_email = _normalize_email(sales_notify_email)
    manager_email = _normalize_email(manager_email)
    if len({sender_email, internal_recipient, sales_notify_email, manager_email}) != 1:
        raise ValueError("growth mail internal identities must match exactly")

    lines = env_path.read_text(encoding="utf-8").splitlines()
    existing = _parse(lines)
    unsubscribe_secret = existing.get("OUTREACH_UNSUBSCRIBE_SECRET", "")
    unsubscribe_rotated = len(unsubscribe_secret) < 32
    if unsubscribe_rotated:
        unsubscribe_secret = secrets.token_urlsafe(SECRET_LENGTH)

    updates = {
        "EMAIL_FROM": sender_email,
        "EMAIL_FROM_NAME": sender_name,
        "EMAIL_INTERNAL_RECIPIENT_ALLOWLIST": internal_recipient,
        "SALES_NOTIFY_EMAIL": sales_notify_email,
        "MANAGER_EMAIL": manager_email,
        # Readiness configuration must always fail closed.  Controlled probes
        # may open one of these switches temporarily, but replaying this
        # command is also the recovery path after an interrupted probe.
        "EMAIL_EXTERNAL_DELIVERY_ENABLED": "false",
        "OUTREACH_SEND_ENABLED": "false",
        "INBOUND_REPLY_ENABLED": "false",
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
        "sender_identity_configured": True,
        "internal_recipient_aligned": True,
        "sales_handoff_recipient_aligned": True,
        "delivery_switches_closed": True,
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
    parser.add_argument("--sender-email", required=True)
    parser.add_argument("--sender-name", required=True)
    parser.add_argument("--internal-recipient", required=True)
    parser.add_argument("--sales-notify-email", required=True)
    parser.add_argument("--manager-email", required=True)
    parser.add_argument("--inbound-domain")
    args = parser.parse_args()
    result = configure(
        args.env_file.resolve(),
        public_base_url=args.public_base_url,
        sender_email=args.sender_email,
        sender_name=args.sender_name,
        internal_recipient=args.internal_recipient,
        sales_notify_email=args.sales_notify_email,
        manager_email=args.manager_email,
        inbound_domain=args.inbound_domain,
    )
    for key, value in result.items():
        print(f"{key}={str(value).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
