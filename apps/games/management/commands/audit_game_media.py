"""
Audit Game media files against the configured storage backend.

Checks every active Game's icon, logo, banner, card_image and all
GameMapPool image fields. For each field it reports:

  - DB value (stored name/path)
  - Generated URL
  - Whether storage.exists(name) returns True
  - Optionally: HTTP HEAD status for remote storage URLs

Usage::

    python manage.py audit_game_media
    python manage.py audit_game_media --only-missing
    python manage.py audit_game_media --json
    python manage.py audit_game_media --include-head-check
    python manage.py audit_game_media --include-inactive
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from typing import Optional

from django.core.management.base import BaseCommand

from apps.common.media_urls import storage_file_exists
from apps.games.models.game import Game
from apps.games.models.map_pool import GameMapPool


IMAGE_FIELDS = ("icon", "logo", "banner", "card_image")


def _head_check(url: str) -> Optional[int]:
    """Return HTTP status code from a HEAD request, or None on error."""
    if not url or not url.startswith(("http://", "https://")):
        return None
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return None


def _audit_field(field_name: str, field_obj, include_head: bool) -> dict:
    name = getattr(field_obj, "name", "") or ""
    if not name:
        return {
            "field": field_name,
            "db_name": "",
            "url": "",
            "storage_exists": None,
            "http_status": None,
            "status": "empty",
        }

    url = ""
    try:
        url = field_obj.url or ""
    except Exception as exc:
        url = f"[url-error: {exc}]"

    exists = storage_file_exists(field_obj)

    http_status = None
    if include_head and url.startswith(("http://", "https://")):
        http_status = _head_check(url)

    if exists:
        overall = "ok"
    elif http_status is not None and 200 <= http_status < 300:
        overall = "ok"
    else:
        overall = "missing"

    return {
        "field": field_name,
        "db_name": name,
        "url": url,
        "storage_exists": exists,
        "http_status": http_status,
        "status": overall,
    }


class Command(BaseCommand):
    help = "Audit Game media files against configured storage. Reports missing files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Only report games/fields where storage file is missing.",
        )
        parser.add_argument(
            "--json",
            dest="json_output",
            action="store_true",
            help="Output results as JSON.",
        )
        parser.add_argument(
            "--include-head-check",
            action="store_true",
            help="Perform HTTP HEAD requests to verify remote URLs (slow).",
        )
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Audit inactive games as well as active ones.",
        )

    def handle(self, *args, **opts):
        only_missing = opts["only_missing"]
        json_output = opts["json_output"]
        include_head = opts["include_head_check"]
        include_inactive = opts["include_inactive"]

        qs = Game.objects.all().order_by("slug")
        if not include_inactive:
            qs = qs.filter(is_active=True)

        map_qs = GameMapPool.objects.select_related("game").order_by("game__slug", "map_name")
        if not include_inactive:
            map_qs = map_qs.filter(game__is_active=True)

        results = []
        summary = {"total_games": 0, "total_fields": 0, "missing": 0, "empty": 0, "ok": 0}

        for game in qs:
            summary["total_games"] += 1
            game_entry = {
                "game_id": game.id,
                "game_slug": game.slug,
                "game_name": game.name,
                "fields": [],
                "maps": [],
            }

            for field_name in IMAGE_FIELDS:
                field_obj = getattr(game, field_name, None)
                row = _audit_field(field_name, field_obj, include_head)
                summary["total_fields"] += 1
                summary[row["status"] if row["status"] in summary else "missing"] += 1
                if row["status"] in ("ok", "empty", "missing"):
                    summary[row["status"]] += 1 if row["status"] not in ("ok", "empty", "missing") else 0
                game_entry["fields"].append(row)

            results.append(game_entry)

        for mp in map_qs:
            # Find existing game entry or create a placeholder
            entry = next(
                (e for e in results if e["game_id"] == mp.game_id), None
            )
            if entry is None:
                entry = {
                    "game_id": mp.game_id,
                    "game_slug": mp.game.slug,
                    "game_name": mp.game.name,
                    "fields": [],
                    "maps": [],
                }
                results.append(entry)

            row = _audit_field("image", mp.image, include_head)
            row["map_name"] = mp.map_name
            row["map_code"] = mp.map_code
            summary["total_fields"] += 1
            entry["maps"].append(row)

        # Recount properly
        summary["ok"] = 0
        summary["empty"] = 0
        summary["missing"] = 0
        for entry in results:
            for row in entry["fields"] + entry["maps"]:
                s = row["status"]
                if s == "ok":
                    summary["ok"] += 1
                elif s == "empty":
                    summary["empty"] += 1
                else:
                    summary["missing"] += 1

        if json_output:
            data = {
                "summary": summary,
                "games": results if not only_missing else [
                    {**e, "fields": [f for f in e["fields"] if f["status"] == "missing"],
                     "maps": [m for m in e["maps"] if m["status"] == "missing"]}
                    for e in results
                    if any(f["status"] == "missing" for f in e["fields"])
                    or any(m["status"] == "missing" for m in e["maps"])
                ],
            }
            self.stdout.write(json.dumps(data, indent=2, default=str))
            return

        # Human-readable output
        any_missing = False
        for entry in results:
            field_rows = entry["fields"]
            map_rows = entry["maps"]
            if only_missing:
                field_rows = [f for f in field_rows if f["status"] == "missing"]
                map_rows = [m for m in map_rows if m["status"] == "missing"]
            if only_missing and not field_rows and not map_rows:
                continue

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"\n{entry['game_name']} (slug={entry['game_slug']} id={entry['game_id']})"
                )
            )

            for row in field_rows:
                self._write_field_row(row)
                if row["status"] == "missing":
                    any_missing = True

            if map_rows:
                self.stdout.write("  Maps:")
                for row in map_rows:
                    label = f"    [{row.get('map_code','?')}] {row.get('map_name','?')} :: {row['field']}"
                    self._write_field_row(row, prefix=label)
                    if row["status"] == "missing":
                        any_missing = True

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Summary: {summary['total_games']} games | "
                f"{summary['total_fields']} fields | "
                f"ok={summary['ok']} empty={summary['empty']} missing={summary['missing']}"
            )
        )

        if any_missing:
            self.stdout.write(self.style.WARNING(
                "\nAction required: upload missing assets to production storage or "
                "clear broken DB references with:\n"
                "  python manage.py clear_broken_game_images --apply"
            ))
            sys.exit(1)

    def _write_field_row(self, row: dict, prefix: str = "") -> None:
        status = row["status"]
        field = row["field"]
        name = row["db_name"] or "(empty)"
        url = row["url"] or "(no url)"
        head = f" HTTP={row['http_status']}" if row["http_status"] is not None else ""

        if not prefix:
            prefix = f"  {field}"

        if status == "ok":
            self.stdout.write(
                self.style.SUCCESS(f"{prefix}: ok | {name}{head}")
            )
        elif status == "empty":
            self.stdout.write(f"{prefix}: (empty)")
        else:
            self.stdout.write(
                self.style.ERROR(f"{prefix}: MISSING | db={name} | url={url}{head}")
            )
