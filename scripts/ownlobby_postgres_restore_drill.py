"""Read-only production public-schema dump and isolated local PostgreSQL 17 restore.

Requires Docker Desktop locally. Uses an ephemeral postgres:17 container that
has NO host port published. It only READS production PostgreSQL. A freshly
encrypted local backup is retained with a SEPARATE key, while plaintext dump
and temporary credentials are destroyed after rehearsal.

This is a public/application schema restore, NOT a full Supabase platform
restore (auth/storage/vault/infrastructure are outside this drill).
No production DB writes, schema changes, or verification flag modifications.
"""
from __future__ import annotations
import os
import json
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, unquote
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import dotenv_values
from scripts.ownlobby_encrypted_media_recovery import BACKUP_BASE, KEY_BASE

EXPECTED_MIN_TABLES = 200
AAD = b"ownlobby-production-public-db-dump-v1"


def task(stage, argv, *, timeout=160, acceptable=(0,)):
    try:
        result = subprocess.run(
            argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError(stage + " unavailable/timeout") from None
    if result.returncode not in acceptable:
        raise RuntimeError(stage + " exit " + str(result.returncode))
    return result.stdout.strip()


def source_url():
    env = {**dotenv_values(ROOT / ".env", interpolate=False), **os.environ}
    raw = str(env.get("DATABASE_URL") or "")
    parsed = urlsplit(raw)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme not in ("postgresql", "postgres")
            or not (host.endswith(".supabase.co") or host.endswith(".pooler.supabase.com"))
            or unquote(parsed.path.strip("/")) != "postgres"
            or not parsed.username or not parsed.password):
        raise ValueError("Expected configured production Supabase postgres DATABASE_URL")
    # Avoid printing or passing the password as a subprocess argument.
    return {
        "host": host, "port": parsed.port or 5432,
        "user": unquote(parsed.username), "password": unquote(parsed.password),
        "db": "postgres",
    }


def pgpass_escape(text):
    return str(text).replace("\\", "\\\\").replace(":", "\\:")


def wait_for_local_postgres(container):
    for _ in range(35):
        try:
            task("local ready", ["docker", "exec", container,
                                 "pg_isready", "-U", "postgres"], timeout=10)
            return
        except RuntimeError:
            time.sleep(1)
    raise RuntimeError("Isolated PostgreSQL 17 did not become ready")


def main():
    if shutil.which("docker") is None:
        print("NEEDS_DOCKER_DESKTOP_FOR_ISOLATED_DB_RESTORE")
        print("NO_PRODUCTION_ACTION_ATTEMPTED")
        return 3
    task("Docker daemon", ["docker", "info", "--format", "{{.ServerVersion}}"], timeout=20)
    source = source_url()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    container = "ownlobby-restore-" + uuid4().hex[:12]
    password = secrets.token_urlsafe(27)
    created = False
    step = "initialization"
    try:
        step = "creating isolated local PostgreSQL"
        # NO -p port mapping. Docker host is never connected to the test DB.
        task(step, [
            "docker", "run", "-d", "--rm", "--name", container,
            "--env", "POSTGRES_USER=postgres",
            "--env", "POSTGRES_PASSWORD=" + password,
            "postgres:17",
        ], timeout=300)
        created = True
        wait_for_local_postgres(container)
        with tempfile.TemporaryDirectory(prefix="ownlobby-private-db-drill-") as workdir:
            tmp = Path(workdir)
            pgpass = tmp / ".pgpass"
            pgpass.write_text(
                ":".join(pgpass_escape(source[k]) for k in ("host", "port", "db", "user", "password"))
                + "\n", encoding="utf-8",
            )
            try:
                os.chmod(pgpass, 0o600)
            except OSError:
                pass

            step = "supplying short-lived private connection file"
            task(step, ["docker", "cp", str(pgpass), container + ":/tmp/source.pgpass"], timeout=30)
            task(step, ["docker", "exec", container, "chmod", "600", "/tmp/source.pgpass"], timeout=15)
            pgpass.unlink()

            # PostgreSQL 17 pg_dump against production: SELECT/read-only only.
            # A consistent snapshot is built on the Supabase source; the
            # output lives only inside the isolated local Docker container.
            step = "read-only production public-schema pg_dump"
            task(step, [
                "docker", "exec", "-e", "PGSSLMODE=require",
                "-e", "PGPASSFILE=/tmp/source.pgpass",
                container, "pg_dump", "--format=custom", "--no-owner",
                "--no-acl", "--schema=public", "--no-password",
                "--host=" + source["host"],
                "--port=" + str(source["port"]),
                "--username=" + source["user"],
                "--dbname=postgres",
                "--file=/tmp/source-public.dump",
            ], timeout=700)

            task("remove temporary production password", [
                "docker", "exec", container, "rm", "-f", "/tmp/source.pgpass",
            ], timeout=20)
            step = "export encrypted database backup"
            plain = tmp / "source-public.dump"
            task(step, ["docker", "cp", container + ":/tmp/source-public.dump", str(plain)], timeout=120)
            data = plain.read_bytes()
            if len(data) < 1000 or data[:5] != b"PGDMP":
                raise ValueError("Invalid PostgreSQL custom dump")
            key = AESGCM.generate_key(bit_length=256)
            nonce = secrets.token_bytes(12)
            BACKUP_BASE.mkdir(parents=True, exist_ok=True)
            KEY_BASE.mkdir(parents=True, exist_ok=True)
            archive = BACKUP_BASE / ("db-public-" + run_id + ".enc")
            key_path = KEY_BASE / ("db-public-" + run_id + ".key")
            with archive.open("xb") as handle:
                handle.write(nonce + AESGCM(key).encrypt(nonce, data, AAD))
                handle.flush()
                os.fsync(handle.fileno())
            with key_path.open("xb") as handle:
                handle.write(key)
                handle.flush()
                os.fsync(handle.fileno())
            for fp in (archive, key_path):
                try:
                    os.chmod(fp, 0o600)
                except OSError:
                    pass
            plain.unlink()
            del data

            step = "independent application-schema restore"
            task(step, [
                "docker", "exec", container, "createdb",
                "-U", "postgres", "ownlobby_recovery",
            ], timeout=30)
            # Restores into a NEW, ISOLATED local DB only; abort on any error.
            task(step, [
                "docker", "exec", container, "pg_restore",
                "--exit-on-error", "--no-owner", "--no-acl",
                "-U", "postgres", "--dbname=ownlobby_recovery",
                "/tmp/source-public.dump",
            ], timeout=700)
            step = "count restored application tables"
            total = int(task(step, [
                "docker", "exec", container, "psql", "-U", "postgres",
                "-d", "ownlobby_recovery", "-At",
                "-c", "select count(*) from pg_tables where schemaname='public';",
            ], timeout=30))
            if total < EXPECTED_MIN_TABLES:
                raise RuntimeError("Restored too few public tables")
            print("POSTGRES_PUBLIC_SCHEMA_LOCAL_RESTORE_PASS")
            print("RESTORED_APPLICATION_TABLES:", total)
            print("ENCRYPTED_DB_BACKUP_LOCATION:", archive)
            print("SEPARATE_DB_BACKUP_KEY_LOCATION:", key_path)
            print("SOURCE_DB_WRITES: 0")
            print("NOT VERIFIED: full Supabase DB/platform, Render deployed recovery, Cloudinary CDN")
            return 0
    except Exception as exc:
        print("POSTGRES_LOCAL_RESTORE_FAIL_AT:", step)
        print("FAILURE_TYPE:", type(exc).__name__)
        print("NO_PRODUCTION_DB_WRITES_ATTEMPTED")
        print("Partial encrypted backup, if created, is NOT a certified restoration.")
        return 2
    finally:
        if created:
            try:
                task("Docker cleanup", ["docker", "rm", "-f", container], timeout=40)
            except Exception:
                print("WARNING: cleanup Docker container manually:", container)


if __name__ == "__main__":
    raise SystemExit(main())
