"""Atomically install the approved production provider configuration.

The input file is a short-lived, mode-0600 dotenv file containing only the
provider credentials.  Values are never printed.  The destination dotenv is
rewritten atomically so a failed update cannot leave a partial configuration.
"""

from __future__ import annotations

import argparse
import os
import stat
import tempfile
from pathlib import Path

SECRET_KEYS = ("PDL_API_KEY", "HUNTER_API_KEY")
MANAGED_VALUES = {
    "PDL_DATA_USE_APPROVED": "true",
    # PDL bills one credit for a successful IP enrichment match.
    "PDL_IP_ENRICH_ESTIMATED_COST": "1",
    # ForgeBase uses Hunter, not PDL person search, for the first contact POC.
    "PDL_CONTACT_DATA_USE_APPROVED": "false",
    "PDL_CONTACT_ESTIMATED_COST": "0",
    "HUNTER_DATA_USE_APPROVED": "true",
    # Hunter API Domain Search uses one search credit for up to ten results.
    "HUNTER_CONTACT_ESTIMATED_COST": "1",
    # The current all-in-one free plan charges half a credit per verification.
    "HUNTER_VERIFY_ESTIMATED_COST": "0.5",
}
MANAGED_KEYS = frozenset((*SECRET_KEYS, *MANAGED_VALUES))
BLOCK_HEADER = (
    "# Managed provider configuration (GitHub Actions; values are credit units)"
)


class ProviderEnvError(ValueError):
    """Raised when a credential or dotenv file violates the sync contract."""


def _parse_secret_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    mode = stat.S_IMODE(path.stat().st_mode)
    if os.name == "posix" and mode & 0o077:
        raise ProviderEnvError("Provider credential file must have mode 0600")
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line or raw_line.lstrip().startswith("#"):
            continue
        key, separator, value = raw_line.partition("=")
        if not separator:
            raise ProviderEnvError(f"Invalid credential line {line_number}")
        key = key.strip()
        if key not in SECRET_KEYS:
            raise ProviderEnvError(f"Unexpected provider credential key: {key}")
        if key in values:
            raise ProviderEnvError(f"Duplicate provider credential key: {key}")
        if not value or "\x00" in value:
            raise ProviderEnvError(f"Provider credential is empty or invalid: {key}")
        values[key] = value
    missing = set(SECRET_KEYS) - set(values)
    if missing:
        raise ProviderEnvError(
            "Missing provider credentials: " + ", ".join(sorted(missing))
        )
    return values


def _key_for_line(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    return stripped.split("=", 1)[0].strip()


def render_updated_env(original: str, secrets: dict[str, str]) -> str:
    """Return a normalized dotenv with exactly one managed provider block."""
    if set(secrets) != set(SECRET_KEYS):
        raise ProviderEnvError("Provider credential set does not match the allowlist")
    retained = [
        line
        for line in original.splitlines()
        if _key_for_line(line) not in MANAGED_KEYS and line.strip() != BLOCK_HEADER
    ]
    while retained and not retained[-1].strip():
        retained.pop()
    block_values = {**secrets, **MANAGED_VALUES}
    block = [
        BLOCK_HEADER,
        *(f"{key}={block_values[key]}" for key in (*SECRET_KEYS, *MANAGED_VALUES)),
    ]
    return "\n".join((*retained, "", *block, ""))


def sync_provider_env(env_file: Path, credentials_file: Path) -> None:
    if not env_file.is_file():
        raise ProviderEnvError(f"Production env file does not exist: {env_file}")
    secrets = _parse_secret_file(credentials_file)
    original = env_file.read_text(encoding="utf-8")
    updated = render_updated_env(original, secrets)
    destination_stat = env_file.stat()
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{env_file.name}.providers-", dir=env_file.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, stat.S_IMODE(destination_stat.st_mode))
        os.replace(temporary, env_file)
        if os.name == "posix":
            directory_fd = os.open(env_file.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)
    print("Installed approved provider configuration for: " + ", ".join(SECRET_KEYS))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--credentials-file", required=True, type=Path)
    args = parser.parse_args()
    sync_provider_env(args.env_file, args.credentials_file)


if __name__ == "__main__":
    main()
