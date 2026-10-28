"""Read-only Supabase S3 canary for OwnLobby's migrated confidential media.

Lists objects, HEADs their metadata, and reads one byte from five samples.
Also checks that unsigned S3 GET/HEAD is denied for the same five samples.
Never writes or logs object keys or credentials. This does not prove Django
record-level authorization, Cloudinary CDN denial or independent restoration.
"""
import os
from pathlib import Path
from urllib.parse import urlsplit

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
BUCKET = "ownlobby-private-media"
EXPECTED_OBJECTS = 125
EXPECTED_METADATA_BYTES = 109908333


def private_s3_settings(env):
    names = {
        "bucket": "MEDIA_PRIVATE_BUCKET",
        "endpoint": "MEDIA_PRIVATE_ENDPOINT_URL",
        "region": "MEDIA_PRIVATE_REGION",
        "key": "MEDIA_PRIVATE_ACCESS_KEY_ID",
        "secret": "MEDIA_PRIVATE_SECRET_ACCESS_KEY",
    }
    config = {key: str(env.get(name) or "").strip() for key, name in names.items()}
    if not all(config.values()):
        raise ValueError("Incomplete private S3 credentials")
    url = urlsplit(config["endpoint"])
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment
            or not url.hostname.endswith(".storage.supabase.co")
            or url.path.rstrip("/") != "/storage/v1/s3"
            or config["bucket"] != BUCKET
            or config["region"].lower() == "auto"):
        raise ValueError("Not the approved HTTPS Supabase private storage origin")
    return config


def verify_unsigned_denial(client, bucket, keys):
    """Unsigned HEAD and one-byte GET must both be denied at private S3 origin."""
    verified = 0
    for key in keys:
        for operation in ("head_object", "get_object"):
            try:
                response = getattr(client, operation)(
                    Bucket=bucket, Key=key,
                    **({"Range": "bytes=0-0"} if operation == "get_object" else {}),
                )
            except ClientError as err:
                status = err.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if status not in (401, 403):
                    raise ValueError("Unsigned S3 denial was not proven") from None
                verified += 1
            else:
                body = response.get("Body") if isinstance(response, dict) else None
                if body:
                    body.close()
                raise ValueError("Unsigned private file was accessible")
    return verified


def inspect_private_origin(client, bucket, expected_count=EXPECTED_OBJECTS,
                           expected_bytes=EXPECTED_METADATA_BYTES, unsigned_client=None):
    keys = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        keys.extend(item["Key"] for item in page.get("Contents", []))
        if len(keys) > 10000:
            raise ValueError("Unexpected origin inventory size")
    if len(keys) != expected_count or len(set(keys)) != len(keys):
        raise ValueError("Origin object inventory count/uniqueness mismatch")
    keys.sort()
    total_bytes = 0
    for key in keys:
        info = client.head_object(Bucket=bucket, Key=key)
        content_length = int(info.get("ContentLength", -1))
        if content_length < 1:
            raise ValueError("Empty or unavailable private object")
        total_bytes += content_length
    if total_bytes != expected_bytes:
        raise ValueError("Private origin byte total differs from the audited migration")
    positions = sorted({round(i * (len(keys) - 1) / 4) for i in range(5)})
    for i in positions:
        item = client.get_object(Bucket=bucket, Key=keys[i], Range="bytes=0-0")
        body = item["Body"]
        try:
            if len(body.read(1)) != 1:
                raise ValueError("Signed private origin read failed")
        finally:
            body.close()
    denial_count = (verify_unsigned_denial(unsigned_client, bucket, [keys[i] for i in positions])
                    if unsigned_client is not None else 0)
    return len(keys), len(positions), denial_count


def main():
    env = {**dotenv_values(ROOT / ".env", interpolate=False), **os.environ}
    try:
        config = private_s3_settings(env)
        client = boto3.client(
            "s3", endpoint_url=config["endpoint"], region_name=config["region"],
            aws_access_key_id=config["key"], aws_secret_access_key=config["secret"],
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                          connect_timeout=5, read_timeout=15, retries={"max_attempts": 2}),
        )
        unsigned_client = boto3.client(
            "s3", endpoint_url=config["endpoint"], region_name=config["region"],
            config=Config(signature_version=UNSIGNED, s3={"addressing_style": "path"},
                          connect_timeout=5, read_timeout=15, retries={"max_attempts": 2}),
        )
        count, reads, denials = inspect_private_origin(
            client, config["bucket"], unsigned_client=unsigned_client)
    except Exception as err:
        print("PRIVATE_ORIGIN_FAIL:", type(err).__name__)
        raise SystemExit(2) from None
    print("PRIVATE_ORIGIN_READ_ONLY_PASS")
    print("OBJECTS_HEAD_VERIFIED:", count)
    print("SIGNED_READS:", reads)
    print("UNSIGNED_GET_HEAD_DENIALS:", denials)
    print("NOT VERIFIED: backup restoration, Cloudinary CDN denial, record authorization")


if __name__ == "__main__":
    main()
