#!/usr/bin/env python3
"""Check tracked/non-ignored root placement; never change owner files.

Ignored local media, documents and databases require separate inventory/review.
This command never recommends deleting them or moving docs into ignored paths.
"""
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def repository_paths(root):
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        capture_output=True,
        check=True,
    )
    return sorted(set(value for value in result.stdout.decode("utf-8").split("\0") if value))


def get_suggested_location(filename):
    if filename.endswith((".sqlite3", ".db", ".dump", ".sql")):
        return "Preserve and review provenance, ownership and recovery requirements; no automatic deletion"
    if filename.endswith(".md"):
        return "Review against OWNLOBBY_DOCUMENTATION_GUIDE.md; do not move owner documents automatically"
    return "Review purpose and references before changing placement"


def check_root_hygiene():
    policy = json.loads(
        (PROJECT_ROOT / "config/repository-policy.json").read_text(encoding="utf-8")
    )
    allowed = set(policy["allowed_root_files"])
    violations = []
    for name in repository_paths(PROJECT_ROOT):
        if "/" in name:
            continue
        sensitive = (
            name == ".env"
            or name.startswith(".env.")
            or name.endswith((".sqlite3", ".db", ".dump", ".log"))
        )
        if sensitive or name not in allowed:
            violations.append(
                {
                    "file": name,
                    "reason": (
                        "Sensitive/generated root file requires review"
                        if sensitive
                        else "Not in reviewed root placement policy"
                    ),
                    "suggest": get_suggested_location(name),
                }
            )
    return violations


def main():
    violations = check_root_hygiene()
    for item in violations:
        print(item["file"] + ": " + item["reason"] + "; " + item["suggest"])
    if not violations:
        print(
            "Reviewed tracked/non-ignored root placement passes. Ignored owner files and release gates require separate review."
        )
    return bool(violations)


if __name__ == "__main__":
    sys.exit(main())
