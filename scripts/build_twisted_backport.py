"""Build/verify OwnLobby's temporary, reproducible upstream Twisted backport.

No site-packages mutation. All downloaded inputs and the output are hash checked.
The default operation verifies the committed artifact without network access.
"""

import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor/twisted"
MANIFEST = VENDOR / "provenance.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_download(url, expected):
    data = urllib.request.urlopen(url, timeout=60).read()
    if digest(data) != expected:
        raise ValueError("Upstream input integrity mismatch: " + url)
    return data


def build(manifest):
    original = checked_download(manifest["upstream_url"], manifest["upstream_sha256"])
    patch = (VENDOR / "upstream-http-header.patch").read_bytes()
    if digest(patch) != manifest["patch_sha256"]:
        raise ValueError("Committed upstream patch integrity mismatch")
    # Fetch the immutable official commit as a second provenance check.
    checked_download(manifest["patch_url"], manifest["patch_sha256"])
    with zipfile.ZipFile(io.BytesIO(original)) as wheel:
        entries = {name: wheel.read(name) for name in wheel.namelist()}
    path = "twisted/web/http.py"
    if digest(entries[path]) != manifest["original_http_sha256"]:
        raise ValueError("Unexpected upstream HTTP parser source")
    # This is the exact functional hunk in upstream 1616f702d36eda8990a5a5b22ad70fab140a7eb1.
    old = b'        if b"\\x00" in data:\n'
    new = (
        b"        # Reject NUL, CR, and LF in a header value (RFC 9110 section 5.5); a\n"
        b"        # bare CR or LF would let a lenient proxy smuggle a following header.\n"
        b'        if b"\\x00" in data or b"\\r" in data or b"\\n" in data:\n'
    )
    if entries[path].count(old) != 1:
        raise ValueError("Patch context must occur exactly once")
    entries[path] = entries[path].replace(old, new, 1)
    if digest(entries[path]) != manifest["patched_http_sha256"]:
        raise ValueError("Patched parser integrity mismatch")
    old_info = "twisted-26.4.0.dist-info/"
    new_info = "twisted-26.4.0+ownlobby.1.dist-info/"
    entries = {name.replace(old_info, new_info): data for name, data in entries.items()}
    metadata = new_info + "METADATA"
    if entries[metadata].count(b"Version: 26.4.0\n") != 1:
        raise ValueError("Unexpected upstream distribution version metadata")
    entries[metadata] = entries[metadata].replace(
        b"Version: 26.4.0\n", b"Version: 26.4.0+ownlobby.1\n", 1
    )
    entries.pop(new_info + "RECORD")
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for name, data in sorted(entries.items()):
        encoded = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        writer.writerow([name, "sha256=" + encoded, len(data)])
    writer.writerow([new_info + "RECORD", "", ""])
    entries[new_info + "RECORD"] = record.getvalue().encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as wheel:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            wheel.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Download verified upstream inputs and reproduce the committed wheel",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write reproduced wheel here, without replacing the approved artifact",
    )
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    committed = (VENDOR / manifest["filename"]).read_bytes()
    if digest(committed) != manifest["sha256"]:
        raise ValueError("Vendored Twisted wheel integrity mismatch")
    if args.rebuild:
        rebuilt = build(manifest)
        if rebuilt != committed:
            raise ValueError("Rebuilt wheel differs from committed artifact")
        if args.output:
            args.output.write_bytes(rebuilt)
    print(
        "Verified Twisted 26.4.0+ownlobby.1 upstream HTTP backport (SHA256 "
        + manifest["sha256"]
        + ")"
    )


if __name__ == "__main__":
    main()
