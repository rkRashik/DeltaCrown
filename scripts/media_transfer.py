"""Offline, non-destructive manifest/copy tool. No provider or DB connection.

Input is an owner-controlled reference export. Defaults to plan/checksum only.
--copy writes exclusively to separate local staging destinations; no source is
removed, no existing destination is replaced and no database value is changed.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path


def contained(root, key):
    root = Path(root).resolve()
    if not key or "\\" in key or Path(key).is_absolute() or ".." in Path(key).parts:
        raise ValueError("Unsafe object key")
    path = (root / key).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Object leaves approved root")
    return path


def checksum(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "size": size}


def make_plan(references, source_root):
    keys = {}
    for row in references:
        alias, key = row["alias"], row["key"]
        if alias not in {"public_media", "private_media"}:
            raise ValueError("Unknown destination alias")
        if key in keys and keys[key] != alias:
            raise ValueError("Shared public/private key requires manual confidentiality review")
        keys[key] = alias
    return [
        dict(key=key, alias=alias, **checksum(contained(source_root, key)))
        for key, alias in sorted(keys.items())
    ]


def copy_verified(plan, source_root, destinations):
    roots = [
        Path(source_root).resolve(),
        *(Path(destinations[k]).resolve() for k in ("public_media", "private_media")),
    ]
    for index, root in enumerate(roots):
        for other in roots[index + 1 :]:
            if root.is_relative_to(other) or other.is_relative_to(root):
                raise ValueError("Source and destination roots must be disjoint")
    results = []
    for row in plan:
        source = contained(source_root, row["key"])
        destination = contained(destinations[row["alias"]], row["key"])
        expected = {k: row[k] for k in ("sha256", "size")}
        if checksum(source) != expected:
            raise ValueError("Source changed since manifest; regenerate reviewed plan")
        if destination.exists():
            if checksum(destination) != expected:
                raise ValueError("Existing destination differs; nothing overwritten")
            results.append("already-verified")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        created = False
        try:
            with source.open("rb") as reader, destination.open("xb") as writer:
                created = True
                os.chmod(destination, 0o600)
                for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                    writer.write(chunk)
                writer.flush()
                os.fsync(writer.fileno())
            if checksum(destination) != expected or checksum(source) != expected:
                raise ValueError("Copy integrity failed")
        except Exception:
            # Only our own newly created partial file, checked inside its destination.
            if created and destination == contained(destinations[row["alias"]], row["key"]):
                destination.unlink()
            raise
        results.append("copied-verified")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--copy", action="store_true")
    parser.add_argument("--destination-public")
    parser.add_argument("--destination-private")
    args = parser.parse_args()
    refs = json.loads(Path(args.references).read_text(encoding="utf-8"))["references"]
    plan = make_plan(refs, args.source_root)
    output = {"objects": plan, "source_unchanged": True, "database_changes": False}
    if args.copy:
        if not args.destination_public or not args.destination_private:
            parser.error("--copy needs both separate destination roots")
        output["results"] = copy_verified(
            plan,
            args.source_root,
            {
                "public_media": args.destination_public,
                "private_media": args.destination_private,
            },
        )
    with Path(args.manifest).open("x", encoding="utf-8") as handle:
        os.chmod(args.manifest, 0o600)
        json.dump(output, handle, indent=2)
    print(
        "Local manifest complete; treat paths/checksums as confidential. No source deletion or DB mutation."
    )


if __name__ == "__main__":
    main()
