"""Reproducible ForgeBase release-package build and verification primitives."""

from __future__ import annotations

import ast
import gzip
import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

VERSION_PATTERN = re.compile(r"^\d{4}\.\d{2}\.\d{2}-internal\.\d+$")
PACKAGE_SCHEMA_VERSION = 1


class ReleasePackageError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(root: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=False
    )
    if result.returncode:
        raise ReleasePackageError(
            f"git {' '.join(args)} failed: {result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout if binary else result.stdout.decode().strip()


def _migration_value(text: str, name: str) -> Any:
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            return ast.literal_eval(node.value)
    raise ReleasePackageError(f"Migration variable missing: {name}")


def migration_topology(root: Path) -> dict[str, Any]:
    revisions: dict[str, tuple[str, ...]] = {}
    folder = root / "api/app/db/migrations/versions"
    for path in sorted(folder.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        try:
            revision = _migration_value(text, "revision")
            down_revision = _migration_value(text, "down_revision")
        except (SyntaxError, ValueError) as exc:
            raise ReleasePackageError(
                f"Cannot parse migration topology: {path.name}"
            ) from exc
        if not isinstance(revision, str):
            raise ReleasePackageError(f"Invalid migration revision: {path.name}")
        if revision in revisions:
            raise ReleasePackageError(f"Duplicate migration revision: {revision}")
        if down_revision is None:
            parents_for_revision: tuple[str, ...] = ()
        elif isinstance(down_revision, str):
            parents_for_revision = (down_revision,)
        elif isinstance(down_revision, (tuple, list)) and all(
            isinstance(parent, str) for parent in down_revision
        ):
            parents_for_revision = tuple(down_revision)
        else:
            raise ReleasePackageError(f"Invalid down_revision: {path.name}")
        revisions[revision] = parents_for_revision
    parents = {parent for values in revisions.values() for parent in values}
    missing = sorted(parents - set(revisions))
    heads = sorted(set(revisions) - parents)
    if missing or len(heads) != 1:
        raise ReleasePackageError(
            f"Migration topology invalid: heads={heads}, missing_parents={missing}"
        )
    return {"head": heads[0], "revision_count": len(revisions), "heads": heads}


def _tracked_critical_files(root: Path) -> list[str]:
    tracked = str(run_git(root, "ls-files", "-z")).split("\x00")
    exact = {"docker-compose.prod.yml", "release/VERSION", "release/release-spec.json"}
    suffixes = ("Dockerfile", "package-lock.json", "requirements.txt", "requirements-runtime.txt")
    prefixes = (".github/workflows/", "deploy/", "api/app/db/migrations/versions/")
    return sorted(
        path
        for path in tracked
        if path
        and (path in exact or path.endswith(suffixes) or path.startswith(prefixes))
    )


def _source_archive(root: Path, destination: Path) -> None:
    raw_tar = run_git(root, "archive", "--format=tar", "HEAD", binary=True)
    with destination.open("wb") as output, gzip.GzipFile(
        fileobj=output, mode="wb", mtime=0, filename=""
    ) as zipped:
        zipped.write(raw_tar)


def _copy_evidence(root: Path, stage: Path, spec: dict[str, Any]) -> list[dict[str, Any]]:
    evidence_root = root / "artifacts"
    copied: list[dict[str, Any]] = []
    for relative in spec["required_local_evidence"]:
        source = evidence_root / relative
        if not source.is_file():
            raise ReleasePackageError(f"Required release evidence missing: {relative}")
        target = stage / "evidence" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        copied.append({"path": f"evidence/{relative}", "sha256": sha256_file(target)})
    security = json.loads((evidence_root / "security-gate/summary.json").read_text(encoding="utf-8"))
    for key in (
        "dependency_vulnerabilities",
        "sast_medium_or_high_findings",
        "unreviewed_secret_candidates",
    ):
        if security.get(key) != 0:
            raise ReleasePackageError(f"Security evidence is not releasable: {key}")
    sbom = json.loads((evidence_root / "security-gate/python-sbom.cdx.json").read_text(encoding="utf-8"))
    if sbom.get("bomFormat") != "CycloneDX":
        raise ReleasePackageError("Python SBOM is not CycloneDX")
    return copied


def _write_checksums(stage: Path) -> None:
    lines = []
    for path in sorted(item for item in stage.rglob("*") if item.is_file()):
        relative = path.relative_to(stage).as_posix()
        if relative == "CHECKSUMS.sha256":
            continue
        lines.append(f"{sha256_file(path)}  {relative}")
    (stage / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _deterministic_tar(source: Path, destination: Path) -> None:
    with (
        destination.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as zipped,
        tarfile.open(fileobj=zipped, mode="w") as archive,
    ):
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source.parent).as_posix()
            info = archive.gettarinfo(str(path), arcname=relative)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            if path.is_file():
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
            else:
                archive.addfile(info)


def build_release_package(
    root: Path, output: Path, version: str | None = None, *, allow_dirty: bool = False
) -> Path:
    root = root.resolve()
    version = version or (root / "release/VERSION").read_text(encoding="utf-8").strip()
    if not VERSION_PATTERN.fullmatch(version):
        raise ReleasePackageError(f"Invalid internal release version: {version}")
    configured_version = (root / "release/VERSION").read_text(encoding="utf-8").strip()
    if version != configured_version:
        raise ReleasePackageError("Requested version does not match release/VERSION")
    dirty = bool(run_git(root, "status", "--porcelain"))
    if dirty and not allow_dirty:
        raise ReleasePackageError("Release packaging requires a clean Git working tree")
    revision = str(run_git(root, "rev-parse", "HEAD"))
    spec = json.loads((root / "release/release-spec.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    package = output / f"forgebase-{version}.tar.gz"
    with tempfile.TemporaryDirectory(prefix="forgebase-release-") as raw_temp:
        temp = Path(raw_temp)
        stage = temp / f"forgebase-{version}"
        stage.mkdir()
        source_archive = stage / "SOURCE.tar.gz"
        _source_archive(root, source_archive)
        evidence = _copy_evidence(root, stage, spec)
        critical = [
            {"path": path, "sha256": sha256_file(root / path)}
            for path in _tracked_critical_files(root)
        ]
        manifest = {
            "schema_version": PACKAGE_SCHEMA_VERSION,
            "product": spec["product"],
            "version": version,
            "release_channel": spec["release_channel"],
            "source_revision": revision,
            "dirty": dirty,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "migration": migration_topology(root),
            "components": spec["components"],
            "critical_files": critical,
            "evidence": evidence,
            "source_archive_sha256": sha256_file(source_archive),
            "required_external_gates": spec["required_external_gates"],
            "external_gates_completed": False,
            "attestation": "GitHub release workflow only; local package is unsigned",
        }
        (stage / "RELEASE_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        _write_checksums(stage)
        _deterministic_tar(stage, package)
    package_digest = sha256_file(package)
    package.with_suffix(package.suffix + ".sha256").write_text(
        f"{package_digest}  {package.name}\n", encoding="utf-8"
    )
    return package


def _safe_extract(package: Path, destination: Path) -> Path:
    with tarfile.open(package, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ReleasePackageError(f"Unsafe package member: {member.name}")
        archive.extractall(destination, filter="data")
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise ReleasePackageError("Release package must contain one root directory")
    return roots[0]


def verify_release_package(package: Path) -> dict[str, Any]:
    package = package.resolve()
    if not package.is_file():
        raise ReleasePackageError(f"Package not found: {package}")
    outer = package.with_suffix(package.suffix + ".sha256")
    if outer.exists():
        expected = outer.read_text(encoding="utf-8").split()[0]
        if sha256_file(package) != expected:
            raise ReleasePackageError("Outer package checksum mismatch")
    with tempfile.TemporaryDirectory(prefix="forgebase-verify-") as raw_temp:
        root = _safe_extract(package, Path(raw_temp))
        checksum_path = root / "CHECKSUMS.sha256"
        manifest_path = root / "RELEASE_MANIFEST.json"
        if not checksum_path.is_file() or not manifest_path.is_file():
            raise ReleasePackageError("Manifest or checksums missing")
        for line in checksum_path.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            target = root / relative
            if not target.is_file() or sha256_file(target) != digest:
                raise ReleasePackageError(f"Embedded checksum mismatch: {relative}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != PACKAGE_SCHEMA_VERSION:
            raise ReleasePackageError("Unsupported release manifest schema")
        if not VERSION_PATTERN.fullmatch(str(manifest.get("version", ""))):
            raise ReleasePackageError("Invalid manifest version")
        if manifest.get("dirty") is not False:
            raise ReleasePackageError("Dirty package cannot be accepted as a release")
        if manifest.get("external_gates_completed") is not False:
            raise ReleasePackageError("External gate declaration is invalid")
        source = root / "SOURCE.tar.gz"
        if sha256_file(source) != manifest.get("source_archive_sha256"):
            raise ReleasePackageError("Source archive digest mismatch")
        return manifest
