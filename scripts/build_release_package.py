"""Build a fail-closed ForgeBase internal release candidate package."""

import argparse
import json
from pathlib import Path

from release_package import ReleasePackageError, build_release_package, sha256_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/release-package"))
    parser.add_argument("--version")
    parser.add_argument("--allow-dirty", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        package = build_release_package(
            root, (root / args.output).resolve(), args.version, allow_dirty=args.allow_dirty
        )
    except ReleasePackageError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 1
    print(json.dumps({"status": "passed", "package": str(package), "sha256": sha256_file(package)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
