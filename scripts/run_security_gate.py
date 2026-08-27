"""Run ForgeBase's blocking source and Python supply-chain security contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "security-gate"


def run(command: list[str], output_name: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    (ARTIFACT_DIR / output_name).write_text(
        result.stdout + ("\nSTDERR:\n" + result.stderr if result.stderr else ""),
        encoding="utf-8",
    )
    return result


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"{label} failed with exit code {result.returncode}")


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    requirements = str(ROOT / "api" / "requirements.txt")

    audit = run(
        [python, "-m", "pip_audit", "-r", requirements, "--strict", "--format", "json"],
        "python-dependency-audit.json",
    )
    require_success(audit, "Python dependency audit")

    sbom_path = ARTIFACT_DIR / "python-sbom.cdx.json"
    sbom = run(
        [
            python,
            "-m",
            "pip_audit",
            "-r",
            requirements,
            "--strict",
            "--format",
            "cyclonedx-json",
            "--output",
            str(sbom_path),
        ],
        "python-sbom.log",
    )
    require_success(sbom, "Python SBOM generation")

    bandit = run(
        [
            python,
            "-m",
            "bandit",
            "-r",
            str(ROOT / "api" / "app"),
            "-x",
            str(ROOT / "api" / "app" / "db" / "migrations"),
            "-ll",
            "-ii",
            "-f",
            "json",
        ],
        "python-sast.json",
    )
    require_success(bandit, "Python SAST")

    secrets = run(
        [python, "-m", "detect_secrets", "scan", "--no-verify", "--slim"],
        "secret-scan.json",
    )
    require_success(secrets, "Secret scan")
    secret_report = json.loads(secrets.stdout)
    findings = secret_report.get("results", {})
    if findings:
        files = ", ".join(sorted(findings))
        raise SystemExit(f"Secret scan found unreviewed candidates in: {files}")

    summary = {
        "dependency_vulnerabilities": 0,
        "sast_medium_or_high_findings": 0,
        "unreviewed_secret_candidates": 0,
        "sbom": sbom_path.name,
    }
    (ARTIFACT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
