"""Release packaging must fail closed on topology, evidence and integrity."""

import json
from pathlib import Path

import pytest

from scripts import release_package
from scripts.release_package import (
    VERSION_PATTERN,
    ReleasePackageError,
    build_release_package,
    migration_topology,
    verify_release_package,
)

ROOT = Path(__file__).resolve().parents[2]


def test_release_version_and_migration_topology_are_unambiguous() -> None:
    version = (ROOT / "release/VERSION").read_text(encoding="utf-8").strip()
    assert VERSION_PATTERN.fullmatch(version)
    topology = migration_topology(ROOT)
    assert topology["heads"] == ["0099_managed_tenant_subdomains"]
    assert topology["revision_count"] >= 100


def test_release_spec_keeps_external_gates_explicit() -> None:
    spec = json.loads((ROOT / "release/release-spec.json").read_text(encoding="utf-8"))
    assert spec["release_channel"] == "internal-candidate"
    assert len(spec["components"]) == 6
    assert len(spec["required_ci_evidence"]) == 6
    assert len(spec["required_external_gates"]) >= 5
    assert "security-gate/python-sbom.cdx.json" in spec["required_local_evidence"]


def test_verifier_rejects_corrupt_outer_checksum(tmp_path: Path) -> None:
    package = tmp_path / "forgebase-2026.08.27-internal.1.tar.gz"
    package.write_bytes(b"not-a-release-package")
    package.with_suffix(package.suffix + ".sha256").write_text(
        f"{'0' * 64}  {package.name}\n", encoding="utf-8"
    )
    with pytest.raises(ReleasePackageError, match="Outer package checksum mismatch"):
        verify_release_package(package)


def test_dirty_tree_is_rejected_for_release(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(release_package, "run_git", lambda *_args, **_kwargs: " M changed")
    with pytest.raises(ReleasePackageError, match="clean Git working tree"):
        build_release_package(ROOT, tmp_path)
