"""OwnLobby release preflight: one command, all checks are read-only.

This is NOT a production cutover or restore drill. It must never set
MEDIA_*_VERIFIED flags, update live providers, or access a write transaction.
Existing previously-passed 125-object origin probe is not repeated.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

STEPS = (
    ("Offline media, recovery and containment regressions", [
        "-m", "unittest",
        "tests.test_cloudinary_containment_status",
        "tests.test_private_media_probe",
        "tests.test_chat_media_recovery",
        "tests.test_render_processes",
        "-v",
    ]),
    ("Production-record Django authorization (read-only SQL + one streamed S3 read)", [
        "scripts/ownlobby_media_record_canary.py",
    ]),
    ("Cloudinary original-asset status and public-artwork exclusions (read-only API)", [
        "scripts/ownlobby_cloudinary_containment.py", "--status",
    ]),
)


def main():
    if not (ROOT / "manage.py").is_file():
        raise SystemExit("STOP: invalid OwnLobby repository root")
    print("OWNLOBBY_BULK_PREFLIGHT_START", flush=True)
    results = []
    for number, (name, args) in enumerate(STEPS, start=1):
        print("\nSTEP", number, "OF", len(STEPS), "-", name, flush=True)
        proc = subprocess.run([sys.executable, *args], cwd=ROOT, check=False)
        results.append((number, name, proc.returncode))
        print("STEP_PASS:" if proc.returncode == 0 else "STEP_FAIL:", number, flush=True)
    print("\nOWNLOBBY_BULK_PREFLIGHT_SUMMARY", flush=True)
    for number, name, status in results:
        print("PASS" if status == 0 else "FAIL", "STEP", number, "-", name, flush=True)
    print("OFFLINE_AND_READ_ONLY_STEPS_PASSED:", sum(code == 0 for _, _, code in results), flush=True)
    print("NO_CUTOVER_OR_PRODUCTION_WRITES_ATTEMPTED", flush=True)
    print("NOT VERIFIED: independent restore, live Render delivery, Cloudinary CDN denial", flush=True)
    if any(code != 0 for _, _, code in results):
        print("OWNLOBBY_BULK_PREFLIGHT_FAIL", flush=True)
        return 2
    print("OWNLOBBY_BULK_PREFLIGHT_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
