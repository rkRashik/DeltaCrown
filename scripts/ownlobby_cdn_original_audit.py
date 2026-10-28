"""Read-only audit of exact original Cloudinary URLs before/after containment.

--capture: records the 111 known-working sensitive original URLs and two
deliberately public artwork URLs in an AES-GCM encrypted manifest alongside
the existing, operator-verified independent media backup.

--verify: after an explicitly approved cutover, requires HEAD and one-byte
streamed GET denial of ALL 111 captured original URLs, and readability of both
public artworks. DOES NOT modify Cloudinary, S3 or the production database.

IMPORTANT: Cloudinary URL variants (transforms/versionless/embedded) not in
this snapshot remain separately unverified; NEVER claim full CDN containment
from original URLs alone. Do not print URL paths or asset names.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor, as_completed

import cloudinary
import cloudinary.api
import requests
from dotenv import dotenv_values
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Direct execution from scripts/ has no implicit project-root import path.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ownlobby_cloudinary_containment import (
    INVENTORY, asset_matches,
)
from scripts.ownlobby_encrypted_media_recovery import (
    BACKUP_BASE, KEY_BASE, encrypt_to, decrypt_from,
)

AAD = b"ownlobby-original-cdn-baseline-v1"
BASELINE_FILE = "cdn-original-baseline.enc"
DENIED = {401, 403, 404, 410}
REACHABLE = {200, 206}


def latest_media_backup():
    if not BACKUP_BASE.is_dir():
        raise ValueError("No independent encrypted media backup directory")
    choices = []
    for folder in BACKUP_BASE.iterdir():
        key_file = KEY_BASE / (folder.name + ".key")
        if folder.is_dir() and (folder / "manifest.enc").is_file() and key_file.is_file():
            choices.append((folder.stat().st_mtime, folder, key_file))
    if not choices:
        raise ValueError("No complete independent media backup/key pair")
    _, folder, key_file = max(choices, key=lambda row: row[0])
    key = key_file.read_bytes()
    if len(key) != 32:
        raise ValueError("Invalid local backup encryption key")
    return folder, key


def allowed_cdn_url(raw, account):
    if not isinstance(raw, str):
        raise ValueError("CDN URL absent")
    parsed = urlsplit(raw)
    if (parsed.scheme != "https" or parsed.hostname != "res.cloudinary.com"
            or parsed.username or parsed.password or parsed.port is not None
            or parsed.query or parsed.fragment):
        raise ValueError("Unexpected Cloudinary CDN URL")
    if not parsed.path.startswith("/" + account + "/"):
        raise ValueError("Unexpected Cloudinary cloud/account path")
    if "/upload/" not in parsed.path or ".." in parsed.path:
        raise ValueError("Unexpected original Cloudinary delivery path")
    return raw


def sample_http(url):
    """HEAD + streamed Range GET. Never read a confidential media body."""
    statuses = []
    for method in ("HEAD", "GET"):
        headers = {"Range": "bytes=0-0"} if method == "GET" else {}
        with requests.request(
            method, url, headers=headers, timeout=20, stream=True,
            allow_redirects=False,
        ) as response:
            statuses.append(response.status_code)
    return tuple(statuses)


def verify_http(rows, phase):
    failures = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        tasks = {
            pool.submit(sample_http, row["url"]): row["classification"]
            for row in rows
        }
        for result in as_completed(tasks):
            classification = tasks[result]
            try:
                statuses = result.result()
                expected = (REACHABLE if phase == "capture" or classification == "public" else DENIED)
                if any(status not in expected for status in statuses):
                    failures += 1
            except Exception:
                failures += 1
    if failures:
        raise ValueError("Cloudinary CDN HEAD/GET evidence mismatches: " + str(failures))


def configure_cloudinary():
    env = dotenv_values(ROOT / ".env", interpolate=False)
    cloud_url = urlsplit(env.get("CLOUDINARY_URL") or "")
    if (cloud_url.scheme != "cloudinary"
            or not all((cloud_url.hostname, cloud_url.username, cloud_url.password))):
        raise ValueError("Cloudinary credentials unavailable locally")
    cloudinary.config(cloud_name=cloud_url.hostname, api_key=cloud_url.username,
                      api_secret=cloud_url.password, secure=True)
    return cloud_url.hostname


def approved_inventory():
    inv = json.loads(INVENTORY.read_text(encoding="utf-8-sig"))
    secret = [x["sources"][0] for x in inv["items"]
              if x.get("classification") == "copy_private_supabase"]
    public = [x["sources"][0] for x in inv["items"]
              if x.get("classification") == "keep_cloudinary"]
    all_ids = [x["asset_id"] for x in secret + public]
    if len(secret) != 111 or len(public) != 2 or len(set(all_ids)) != 113:
        raise ValueError("Approved source inventory changed")
    return secret, public


def capture():
    account = configure_cloudinary()
    secret, public = approved_inventory()
    folder, key = latest_media_backup()
    baseline_path = folder / BASELINE_FILE
    if baseline_path.exists():
        raise ValueError("Existing encrypted CDN baseline is immutable")
    rows = []
    for classification, sources in (("private", secret), ("public", public)):
        for source in sources:
            item = cloudinary.api.resource(
                source["public_id"], resource_type=source["resource_type"],
                type="upload",
            )
            if not asset_matches(item, source, "upload"):
                raise ValueError("Cloudinary source identity mismatch")
            url = allowed_cdn_url(item.get("secure_url"), account)
            rows.append({"classification": classification, "url": url,
                         "asset_id": source["asset_id"]})
    # Prove each recorded endpoint was reachable before containment so a
    # later 404 cannot be mistaken for protection of an invalid old URL.
    verify_http(rows, "capture")
    encrypt_to(baseline_path, key, json.dumps(rows).encode("utf-8"), AAD)
    print("CDN_ORIGINAL_BASELINE_CAPTURE_PASS")
    print("PROVEN_REACHABLE_PRIVATE_ORIGINALS: 111")
    print("PROVEN_REACHABLE_PUBLIC_EXCLUSIONS: 2")
    print("BASELINE_ENCRYPTED_WITH_LOCAL_BACKUP_KEY; NO URLS PRINTED")
    print("NO_PROVIDER_OR_DATABASE_WRITES")
    print("NOT COVERED: transformed, versionless, embedded and worldwide CDN variants")


def verify():
    account = configure_cloudinary()
    secret, public = approved_inventory()
    folder, key = latest_media_backup()
    baseline_path = folder / BASELINE_FILE
    if not baseline_path.exists():
        raise ValueError("Capture pre-containment original URLs first")
    rows = json.loads(decrypt_from(baseline_path, key, AAD))
    if (len(rows) != 113
            or sum(x["classification"] == "private" for x in rows) != 111
            or sum(x["classification"] == "public" for x in rows) != 2
            or {x["asset_id"] for x in rows}
            != {s["asset_id"] for s in secret + public}):
        raise ValueError("Captured inventory does not match approved sources")
    for row in rows:
        allowed_cdn_url(row["url"], account)
    # Check the two deliberate exclusions are still Cloudinary upload assets
    for source in public:
        meta = cloudinary.api.resource(
            source["public_id"], resource_type=source["resource_type"],
            type="upload",
        )
        if not asset_matches(meta, source, "upload"):
            raise ValueError("Approved public artwork has changed")
    # Verify sensitive sources moved to authenticated delivery, not simply
    # vanished. No public upload delivery should remain.
    for source in secret:
        try:
            cloudinary.api.resource(
                source["public_id"], resource_type=source["resource_type"],
                type="upload",
            )
        except cloudinary.api.NotFound:
            pass
        else:
            raise ValueError("Sensitive original still has upload delivery")
        meta = cloudinary.api.resource(
            source["public_id"], resource_type=source["resource_type"],
            type="authenticated",
        )
        if meta.get("asset_id") != source["asset_id"] or meta.get("type") != "authenticated":
            raise ValueError("Sensitive source authenticated identity mismatch")
    verify_http(rows, "verify")
    print("CDN_ORIGINAL_DENIAL_PASS")
    print("PRIVATE_ORIGINALS_DENIED_GET_AND_HEAD: 111")
    print("PUBLIC_ARTWORK_REMAINS_READABLE: 2")
    print("NO_PROVIDER_OR_DATABASE_WRITES")
    print("NOT COVERED: transformed, versionless, embedded and worldwide CDN variants")



def verify_variants():
    """Check likely old CDN variants without printing private URL paths.

    Versionless alternatives and a minimal image transformation are tested
    anonymously via both HEAD and a streamed one-byte GET. Unlike the 111
    originals, these alternate URLs were not captured before containment.
    A denial is strong current-path evidence but NOT historical reachability
    evidence, exhaustive CDN cache invalidation or global edge proof.
    """
    account = configure_cloudinary()
    private, public = approved_inventory()
    folder, key = latest_media_backup()
    baseline = folder / BASELINE_FILE
    if not baseline.exists():
        raise ValueError("Missing immutable original CDN pre-cutover evidence")
    rows = json.loads(decrypt_from(baseline, key, AAD))
    if (len(rows) != 113 or
        {x["asset_id"] for x in rows} !=
            {source["asset_id"] for source in private + public}):
        raise ValueError("Encrypted CDN inventory changed")
    variants = {}
    for row in rows:
        if row["classification"] != "private":
            continue
        original = allowed_cdn_url(row["url"], account)
        parts = urlsplit(original)
        # Safely derive an unversioned URL only when /vNNN/ occurs immediately
        # after /upload/. Resource identifiers are never logged.
        unversioned = re.sub(r"(/upload/)v[0-9]+/", r"\1", parts.path, count=1)
        if unversioned != parts.path:
            variants[parts._replace(path=unversioned).geturl()] = "versionless"
        if "/image/upload/" in parts.path:
            transformed = parts.path.replace(
                "/image/upload/", "/image/upload/c_scale,w_1/", 1)
            variants[parts._replace(path=transformed).geturl()] = "transformed"
    if not variants or "transformed" not in variants.values():
        raise ValueError("No representative CDN variants could be derived")
    failed = 0
    passed = {"versionless": 0, "transformed": 0}
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = {pool.submit(sample_http, url): kind for url, kind in variants.items()}
        for job in as_completed(jobs):
            kind = jobs[job]
            try:
                statuses = job.result()
                if all(code in DENIED for code in statuses):
                    passed[kind] += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
    if failed:
        raise ValueError("Anonymous CDN alternate URL HEAD/GET failures: " + str(failed))
    print("CDN_VARIANT_DENIAL_PASS")
    print("VERSIONLESS_VARIANTS_DENIED_GET_AND_HEAD:", passed["versionless"])
    print("IMAGE_TRANSFORM_VARIANTS_DENIED_GET_AND_HEAD:", passed["transformed"])
    print("NO_PROVIDER_OR_DATABASE_WRITES; NO PRIVATE URLS PRINTED")
    print("NOT VERIFIED: prior variant reachability, all embedded/CDN cache/edge URLs")

def main():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--capture", action="store_true")
    group.add_argument("--verify", action="store_true")
    group.add_argument("--verify-variants", action="store_true")
    args = p.parse_args()
    try:
        if args.capture:
            capture()
        elif args.verify_variants:
            verify_variants()
        else:
            verify()
    except Exception as error:
        print("CDN_ORIGINAL_AUDIT_FAIL:", type(error).__name__)
        print("NO_PROVIDER_OR_DATABASE_WRITES; check encrypted baseline state")
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
