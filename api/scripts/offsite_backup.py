"""Encrypt and transfer ForgeBase backups to an S3-compatible off-site bucket."""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import secrets
import sys
import tempfile
from pathlib import Path

import boto3
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"FGBK1"
CHUNK = 1024 * 1024


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing {name}")
    return value


def encryption_key() -> bytes:
    value = required("BACKUP_ENCRYPTION_KEY")
    try:
        key = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except ValueError as exc:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY must be URL-safe base64") from exc
    if len(key) != 32:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


def client():
    return boto3.client(
        "s3",
        endpoint_url=required("BACKUP_S3_ENDPOINT_URL"),
        aws_access_key_id=required("BACKUP_S3_ACCESS_KEY_ID"),
        aws_secret_access_key=required("BACKUP_S3_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("BACKUP_S3_REGION", "auto"),
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def encrypted_scratch_path(anchor: Path) -> Path:
    configured_work_dir = os.environ.get("BACKUP_WORK_DIR", "").strip()
    work_dir = Path(configured_work_dir) if configured_work_dir else anchor.parent
    work_dir.mkdir(parents=True, exist_ok=True)
    descriptor, scratch_name = tempfile.mkstemp(
        dir=work_dir,
        prefix=f".{anchor.name}.",
        suffix=".enc",
    )
    os.close(descriptor)
    return Path(scratch_name)


def encrypt(source: Path, target: Path) -> str:
    nonce = secrets.token_bytes(12)
    encryptor = Cipher(algorithms.AES(encryption_key()), modes.GCM(nonce)).encryptor()
    digest = hashlib.sha256()
    with source.open("rb") as src, target.open("wb") as dst:
        dst.write(MAGIC + nonce)
        while chunk := src.read(CHUNK):
            digest.update(chunk)
            dst.write(encryptor.update(chunk))
        dst.write(encryptor.finalize())
        dst.write(encryptor.tag)
    return digest.hexdigest()


def decrypt(source: Path, target: Path) -> None:
    size = source.stat().st_size
    if size <= len(MAGIC) + 12 + 16:
        raise RuntimeError("Encrypted backup is truncated")
    with source.open("rb") as src:
        if src.read(len(MAGIC)) != MAGIC:
            raise RuntimeError("Unknown backup format")
        nonce = src.read(12)
        src.seek(-16, 2)
        tag = src.read(16)
        ciphertext_length = size - len(MAGIC) - 12 - 16
        src.seek(len(MAGIC) + 12)
        decryptor = Cipher(algorithms.AES(encryption_key()), modes.GCM(nonce, tag)).decryptor()
        remaining = ciphertext_length
        with target.open("wb") as dst:
            while remaining:
                chunk = src.read(min(CHUNK, remaining))
                if not chunk:
                    raise RuntimeError("Encrypted backup ended early")
                remaining -= len(chunk)
                dst.write(decryptor.update(chunk))
            dst.write(decryptor.finalize())


def upload(source: Path) -> None:
    if not source.is_file():
        raise RuntimeError(f"Backup does not exist: {source}")
    encrypted = encrypted_scratch_path(source)
    object_name = f"{source.name}.enc"
    try:
        checksum = encrypt(source, encrypted)
        bucket = required("BACKUP_S3_BUCKET_NAME")
        prefix = os.environ.get("BACKUP_S3_PREFIX", "forgebase").strip("/")
        key = f"{prefix}/{object_name}"
        client().upload_file(
            str(encrypted), bucket, key,
            ExtraArgs={"Metadata": {"plaintext-sha256": checksum, "format": "fgbk1-aes256-gcm"}},
        )
    finally:
        encrypted.unlink(missing_ok=True)
    print(key)


def download(key: str, destination: Path) -> None:
    s3 = client()
    bucket = required("BACKUP_S3_BUCKET_NAME")
    metadata = s3.head_object(Bucket=bucket, Key=key).get("Metadata", {})
    expected_checksum = str(metadata.get("plaintext-sha256", "")).strip().lower()
    if len(expected_checksum) != 64 or any(
        character not in "0123456789abcdef" for character in expected_checksum
    ):
        raise RuntimeError("Backup object is missing a valid plaintext SHA-256")
    destination.parent.mkdir(parents=True, exist_ok=True)
    encrypted = encrypted_scratch_path(destination)
    try:
        s3.download_file(bucket, key, str(encrypted))
        try:
            decrypt(encrypted, destination)
            actual_checksum = file_sha256(destination)
            if not secrets.compare_digest(actual_checksum, expected_checksum):
                raise RuntimeError("Backup plaintext checksum mismatch")
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    finally:
        encrypted.unlink(missing_ok=True)
    print(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    upload_parser = sub.add_parser("upload")
    upload_parser.add_argument("source", type=Path)
    download_parser = sub.add_parser("download")
    download_parser.add_argument("key")
    download_parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        upload(args.source) if args.command == "upload" else download(args.key, args.destination)
        return 0
    except Exception as exc:
        print(f"off-site backup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
