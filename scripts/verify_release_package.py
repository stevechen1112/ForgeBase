"""Verify all ForgeBase release-package integrity and policy declarations."""

import argparse
import json
from pathlib import Path

from release_package import ReleasePackageError, verify_release_package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    try:
        manifest = verify_release_package(args.package)
    except (ReleasePackageError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 1
    print(json.dumps({"status": "passed", "manifest": manifest}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
