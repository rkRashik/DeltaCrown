"""OwnLobby Cloudinary source containment. Default: READ ONLY.
Run ONLY on the approved coordinated production cutover window.
Local confidential inventory stays ignored; no credentials/URLs printed.
"""
import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import cloudinary
import cloudinary.api
import cloudinary.uploader
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "Artifacts/media-audit/confidential-inventory-20261027/inventory.json"


def asset_matches(current, source, delivery="upload"):
    return (
        current.get("asset_id") == source["asset_id"]
        and current.get("public_id") == source["public_id"]
        and current.get("resource_type") == source["resource_type"]
        and str(current.get("version")) == str(source["version"])
        and int(current.get("bytes", -1)) == int(source["verified_bytes"])
        and current.get("type") == delivery
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="CHANGES LIVE ASSETS; requires cutover confirmation")
    parser.add_argument("--status", action="store_true", help="READ ONLY: count original versus authenticated source assets")
    parser.add_argument("--cutover-confirmation", default="")
    args = parser.parse_args()
    if args.apply and args.status:
        parser.error('--status and --apply cannot be combined')

    if not INVENTORY.is_file():
        raise SystemExit("STOP: confidential inventory missing")
    inv = json.loads(INVENTORY.read_text(encoding="utf-8-sig"))
    private = [x["sources"][0] for x in inv["items"] if x["classification"] == "copy_private_supabase"]
    public = [x["sources"][0] for x in inv["items"] if x["classification"] == "keep_cloudinary"]
    if not (len(private) == 111 and len(public) == 2
            and len({s["asset_id"] for s in private + public}) == 113):
        raise SystemExit("STOP: inventory totals/uniqueness differ from approved evidence")
    if args.apply and args.cutover_confirmation != "I_APPROVE_111_LIVE_CLOUDINARY_CHANGES":
        raise SystemExit("STOP: explicit cutover confirmation missing")
    env = dotenv_values(ROOT / ".env", interpolate=False)
    url = urlsplit(env.get("CLOUDINARY_URL") or "")
    if url.scheme != "cloudinary" or not all([url.hostname, url.username, url.password]):
        raise SystemExit("STOP: Cloudinary API configuration missing")
    cloudinary.config(cloud_name=url.hostname, api_key=url.username,
                      api_secret=url.password, secure=True)

    if args.status:
        print("MODE: READ ONLY STATUS")
        counts = Counter()
        for s in private:
            for delivery in ("upload", "authenticated"):
                try:
                    item = cloudinary.api.resource(s["public_id"],
                        resource_type=s["resource_type"], type=delivery)
                except cloudinary.api.NotFound:
                    continue
                except Exception as err:
                    print("STOP: provider read error:", type(err).__name__)
                    raise SystemExit(2)
                if asset_matches(item, s, delivery):
                    counts[delivery] += 1
                else:
                    counts["mismatch"] += 1
            time.sleep(0.15)
        # The two deliberately public exclusions must still be intact.
        for s in public:
            try:
                item = cloudinary.api.resource(
                    s["public_id"], resource_type=s["resource_type"], type="upload")
            except Exception as err:
                print("STOP: public exclusion metadata read failed:", type(err).__name__)
                raise SystemExit(2)
            if asset_matches(item, s, "upload"):
                counts["public_exclusions"] += 1
            else:
                counts["mismatch"] += 1
        print("PUBLIC_EXCLUSIONS_VERIFIED:", counts["public_exclusions"])
        print("STILL_PUBLIC:", counts["upload"])
        print("AUTHENTICATED:", counts["authenticated"])
        print("MISMATCHES:", counts["mismatch"])
        if (counts["upload"] + counts["authenticated"] != 111
                or counts["public_exclusions"] != 2 or counts["mismatch"]):
            raise SystemExit("STOP: asset status inconsistent; manual reconciliation required")
        print("STATUS_PASS: no changes made")
        return
    print("MODE:", "LIVE APPLY" if args.apply else "READ ONLY")
    print("Checking 111 private targets + 2 public exclusions...")
    verified = []
    counters = Counter()
    for label, sources in [("private", private), ("public", public)]:
        for s in sources:
            try:
                info = cloudinary.api.resource(s["public_id"],
                      resource_type=s["resource_type"], type="upload")
                if not asset_matches(info, s):
                    counters[label + "_mismatch"] += 1
                else:
                    verified.append((label, s))
                    counters[label + "_match"] += 1
            except Exception as err:
                print("STOP: provider metadata read failed:", type(err).__name__)
                raise SystemExit(2)
            time.sleep(0.15)
    print("MATCHED_PRIVATE:", counters["private_match"])
    print("MATCHED_PUBLIC:", counters["public_match"])
    print("MISMATCHES:", counters["private_mismatch"] + counters["public_mismatch"])
    if counters["private_match"] != 111 or counters["public_match"] != 2:
        raise SystemExit("STOP: preconditions failed; no mutation attempted")
    if not args.apply:
        print("PREFLIGHT_PASS: no changes made")
        return
    # No automated rollback: once protected, sources MUST NOT be made public again.
    # Operator must coordinate with hybrid deployment and CDN denial tests.
    changed = 0
    for label, s in verified:
        if label != "private":
            continue
        try:
            current = cloudinary.api.resource(
                s["public_id"], resource_type=s["resource_type"], type="upload")
            if not asset_matches(current, s):
                raise RuntimeError("identity changed during cutover")
            cloudinary.uploader.rename(
                s["public_id"], s["public_id"],
                resource_type=s["resource_type"], type="upload",
                to_type="authenticated", overwrite=False, invalidate=True)
            # Confirm transfer to authenticated delivery without disclosing IDs.
            moved = cloudinary.api.resource(
                s["public_id"], resource_type=s["resource_type"], type="authenticated")
            if moved.get("asset_id") != s["asset_id"] or moved.get("type") != "authenticated":
                raise RuntimeError("post-change identity/delivery verification failed")
            changed += 1
            print("PROTECTED_COUNT:", changed, flush=True)
        except Exception as err:
            print("STOP: after", changed, "successful changes; failure:", type(err).__name__)
            print("DO NOT rerun --apply blindly. Retain private sources; reconcile changed state.")
            raise SystemExit(3)
    print("TRANSFER_COMPLETE:", changed)
    print("NOT YET PRIVACY VERIFIED: anonymous original/versioned/transformed/embedded GET+HEAD denial still required")


if __name__ == "__main__":
    main()
