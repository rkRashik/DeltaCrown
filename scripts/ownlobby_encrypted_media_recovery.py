"""Independent encrypted media-only backup + separate-process offline restore drill.

READS production private S3; WRITES ONLY encrypted local backup and short-lived
private local restore files. No production provider writes, DB access, CDN changes,
or verification-flag updates. This does not restore database metadata or prove a
Render deployment can recover. Keep the generated key separate from the backup.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import boto3
from botocore.config import Config
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import dotenv_values
from scripts.private_media_probe import (
    BUCKET, EXPECTED_OBJECTS, EXPECTED_METADATA_BYTES, private_s3_settings,
)

MANIFEST_AAD = b"ownlobby-media-backup-v1"
BACKUP_BASE = Path.home() / "OwnLobby-Encrypted-Recovery"
KEY_BASE = Path.home() / ".ownlobby-recovery-keys"


def safe_key(name):
    p = PurePosixPath(name)
    if not name or name.startswith("/") or "\\" in name or ".." in p.parts or "." in p.parts:
        raise ValueError("Unsafe origin key")
    return name


def encrypt_to(path, key, data, aad):
    nonce = os.urandom(12)
    with path.open("xb") as handle:
        handle.write(nonce + AESGCM(key).encrypt(nonce, data, aad))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def decrypt_from(path, key, aad):
    blob = path.read_bytes()
    if len(blob) < 29:
        raise ValueError("Encrypted backup item is truncated")
    return AESGCM(key).decrypt(blob[:12], blob[12:], aad)


def offline_restore(backup, key_file):
    """Entire restore runs with no provider client or network calls."""
    key = key_file.read_bytes()
    if len(key) != 32:
        raise ValueError("Invalid independent encryption key")
    manifest = json.loads(decrypt_from(backup / "manifest.enc", key, MANIFEST_AAD))
    if (len(manifest) != EXPECTED_OBJECTS
            or len({row["key"] for row in manifest}) != len(manifest)):
        raise ValueError("Backup manifest count or uniqueness mismatch")
    total = 0
    with tempfile.TemporaryDirectory(prefix="ownlobby-offline-restore-") as root:
        restore_root = Path(root).resolve()
        try:
            os.chmod(restore_root, 0o700)
        except OSError:
            pass
        for row in manifest:
            name = safe_key(row["key"])
            ciphertext_name = hashlib.sha256(name.encode("utf-8")).hexdigest() + ".enc"
            recovered = decrypt_from(backup / ciphertext_name, key, name.encode("utf-8"))
            if (hashlib.sha256(recovered).hexdigest() != row["sha256"]
                    or len(recovered) != row["size"]):
                raise ValueError("Recovered byte checksum mismatch")
            destination = (restore_root / name).resolve()
            if not destination.is_relative_to(restore_root):
                raise ValueError("Backup attempted path traversal")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as out:
                out.write(recovered)
            try:
                os.chmod(destination, 0o600)
            except OSError:
                pass
            with destination.open("rb") as restored:
                if hashlib.file_digest(restored, "sha256").hexdigest() != row["sha256"]:
                    raise ValueError("Restored local file differs")
            total += len(recovered)
    if total != EXPECTED_METADATA_BYTES:
        raise ValueError("Restored media total differs")
    print("ENCRYPTED_BACKUP_OFFLINE_RESTORE_PASS", flush=True)
    print("RESTORED_PRIVATE_OBJECTS:", len(manifest), flush=True)
    print("RESTORED_BYTES:", total, flush=True)
    print("NO_PRODUCTION_WRITES_OR_DATABASE_CHANGES", flush=True)
    print("NOT VERIFIED: independent DB restore, post-restart Render media, CDN denial", flush=True)


def create_backup():
    values = {**dotenv_values(ROOT / ".env", interpolate=False), **os.environ}
    env = private_s3_settings(values)
    config = Config(signature_version="s3v4", s3={"addressing_style": "path"},
                    retries={"mode": "standard", "total_max_attempts": 3})
    s3 = boto3.client(
        "s3", endpoint_url=env["endpoint"], region_name=env["region"],
        aws_access_key_id=env["key"], aws_secret_access_key=env["secret"],
        config=config,
    )
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET):
        keys.extend(safe_key(entry["Key"]) for entry in page.get("Contents", []))
    if len(keys) != EXPECTED_OBJECTS or len(set(keys)) != len(keys):
        raise ValueError("Private-origin object inventory changed")
    keys.sort()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = stamp + "-" + uuid4().hex[:8]
    BACKUP_BASE.mkdir(parents=True, exist_ok=True)
    KEY_BASE.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_BASE / run_id
    backup.mkdir(mode=0o700)
    key_file = KEY_BASE / (run_id + ".key")
    key = os.urandom(32)
    descriptor = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as out:
        out.write(key)
        out.flush()
        os.fsync(out.fileno())

    rows = []
    total = 0
    for number, name in enumerate(keys, 1):
        response = s3.get_object(Bucket=BUCKET, Key=name)
        body = response["Body"]
        try:
            payload = body.read()
        finally:
            body.close()
        if len(payload) == 0 or len(payload) != int(response.get("ContentLength", -1)):
            raise ValueError("Private origin object length mismatch")
        hashed_name = hashlib.sha256(name.encode("utf-8")).hexdigest() + ".enc"
        encrypt_to(backup / hashed_name, key, payload, name.encode("utf-8"))
        rows.append({"key": name, "size": len(payload),
                     "sha256": hashlib.sha256(payload).hexdigest()})
        total += len(payload)
        if number % 25 == 0:
            print("ENCRYPTED_BACKUP_PROGRESS:", number, "of", EXPECTED_OBJECTS, flush=True)
    if total != EXPECTED_METADATA_BYTES:
        raise ValueError("Private origin total bytes changed during backup")
    encrypt_to(backup / "manifest.enc", key,
               json.dumps(rows, separators=(",", ":")).encode("utf-8"), MANIFEST_AAD)
    print("ENCRYPTED_BACKUP_COMPLETE", flush=True)
    print("BACKUP_LOCATION:", backup, flush=True)
    print("SEPARATE_KEY_LOCATION:", key_file, flush=True)

    # Independent Python process: this phase has NO S3 client and can
    # reconstruct the entire file tree if the origin is offline.
    cmd = [sys.executable, str(Path(__file__).resolve()),
           "--restore-only", "--backup-path", str(backup), "--key-path", str(key_file)]
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode:
        raise ValueError("Independent offline encrypted backup restore did not pass")
    print("MEDIA_ONLY_INDEPENDENT_LOCAL_RECOVERY_PASS", flush=True)
    print("Keep backup and key in separate secure locations; do not upload either to GitHub.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore-only", action="store_true")
    parser.add_argument("--backup-path")
    parser.add_argument("--key-path")
    args = parser.parse_args()
    try:
        if args.restore_only:
            if not args.backup_path or not args.key_path:
                parser.error("--restore-only requires backup and key paths")
            offline_restore(Path(args.backup_path), Path(args.key_path))
        else:
            if args.backup_path or args.key_path:
                parser.error("backup/key paths require --restore-only")
            create_backup()
    except Exception as err:
        print("MEDIA_BACKUP_RECOVERY_FAIL:", type(err).__name__, flush=True)
        print("NO_REMOTE_WRITES_ATTEMPTED; any new local encrypted backup remains untouched", flush=True)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
