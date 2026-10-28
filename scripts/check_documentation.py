"""Offline local-link checks; active documents fail on missing/untracked targets.

Historical/workspace-only links are reported, not silently removed. No external
URL is fetched and no owner/private document content is traversed.
"""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]\n]*\]\((<[^>\n]+>|[^\s)]+)(?:\s+[^)]*)?\)")


def heading_anchors(text):
    anchors = set(re.findall(r'(?:id|name)=["\']([^"\']+)["\']', text))
    counts = {}
    for title in re.findall(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", text, flags=re.M):
        slug = re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        anchors.add(slug + ("-" + str(count) if count else ""))
        counts[slug] = count + 1
    return anchors


def link_results(root, document, tracked):
    text = (root / document).read_text(encoding="utf-8-sig")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    rows = []
    for match in LINK.finditer(text):
        target = match.group(1).strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            continue
        if target.startswith("/"):
            continue  # Application routes are verified through Django, not the filesystem.
        candidate = (
            ((root / document).parent / unquote(parsed.path)).resolve()
            if parsed.path
            else root / document
        )
        try:
            relative = candidate.relative_to(root.resolve()).as_posix()
        except ValueError:
            rows.append({"document": document, "target": target, "status": "outside-workspace"})
            continue
        if not candidate.exists():
            status = "missing"
        elif (candidate.is_file() and relative not in tracked) or (
            candidate.is_dir()
            and not any(name.startswith(relative.rstrip("/") + "/") for name in tracked)
        ):
            status = "workspace-only"
        else:
            status = "exists"
        if (
            status == "exists"
            and parsed.fragment
            and candidate.suffix == ".md"
            and not relative.startswith("Documents/")
        ):
            if unquote(parsed.fragment) not in heading_anchors(
                candidate.read_text(encoding="utf-8-sig")
            ):
                status = "missing-anchor"
        rows.append({"document": document, "target": target, "status": status})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all", action="store_true", help="Also report historical tracked Markdown"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    policy = json.loads((ROOT / "config/repository-policy.json").read_text())
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    tracked = {path for path in paths if path}
    active = set(policy["active_documents"])
    documents = sorted(
        active
        | (
            {path for path in tracked if path.endswith(".md") and not path.startswith("Documents/")}
            if args.all
            else set()
        )
    )
    rows = []
    missing_documents = [path for path in documents if not (ROOT / path).is_file()]
    for document in documents:
        if document not in missing_documents:
            rows.extend(link_results(ROOT, document, tracked))
    failures = [row for row in rows if row["document"] in active and row["status"] != "exists"]
    report = {
        "documents": len(documents),
        "links": len(rows),
        "active_failures": failures,
        "missing_documents": missing_documents,
        "historical_findings": [
            row for row in rows if row["document"] not in active and row["status"] != "exists"
        ],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return bool(failures or missing_documents)


if __name__ == "__main__":
    sys.exit(main())
