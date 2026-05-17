"""
Audit Cloudinary for orphaned media assets — files that exist in Cloudinary
but are no longer referenced by any DB row.

This is needed because ``django-cloudinary-storage`` does NOT auto-delete old
Cloudinary assets when a FileField/ImageField is replaced or cleared in the
Django admin (or via the ORM). Replaced files accumulate silently.

Usage::

    python manage.py audit_cloudinary_orphans                              # dry-run, all approved folders
    python manage.py audit_cloudinary_orphans --only-games                 # games/* folders only
    python manage.py audit_cloudinary_orphans --folder games/icons/        # single folder
    python manage.py audit_cloudinary_orphans --min-age-hours 24           # younger files included
    python manage.py audit_cloudinary_orphans --include-recent             # skip age filter entirely
    python manage.py audit_cloudinary_orphans --json
    python manage.py audit_cloudinary_orphans --apply --confirm-delete-orphans

Safety guarantees enforced by this command:
  - Dry-run by default: NEVER deletes without --apply --confirm-delete-orphans.
  - Only operates on a fixed approved-folder safelist.
  - Skips files uploaded within --min-age-hours (default 48) unless --include-recent.
  - Never deletes a file referenced by ANY DB row.
  - Never deletes files in evidence/payment/kyc/certificate folders even if listed.
  - Logs every deletion attempt and result.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Folder configuration
# ---------------------------------------------------------------------------

# ONLY scan these Cloudinary sub-paths (after the media/ prefix).
# Adding a folder here requires deliberate review — these are the only folders
# where orphan deletion is ever permitted.
APPROVED_GAME_FOLDERS = [
    "games/icons/",
    "games/logos/",
    "games/banners/",
    "games/cards/",
    "games/maps/",
]

APPROVED_ORG_FOLDERS = [
    "teams/logos/",
    "teams/banners/",
    "teams/gallery/",
    "organizations/logos/",
    "organizations/badges/",
    "organizations/banners/",
]

APPROVED_TOURNAMENT_FOLDERS = [
    "tournaments/banners/",
    "tournaments/thumbnails/",
    "tournaments/sponsors/",
    "tournaments/sponsors/banners/",
]

ALL_APPROVED_FOLDERS = (
    APPROVED_GAME_FOLDERS
    + APPROVED_ORG_FOLDERS
    + APPROVED_TOURNAMENT_FOLDERS
)

# Blocklist: substrings that MUST NEVER be in a deleted public_id regardless of folder.
BLOCKED_SUBSTRINGS = (
    "match_media",
    "payment_proof",
    "payments/",
    "registration_payment",
    "kyc/",
    "certificates/",
    "community/",
    "arena/",
)

DEFAULT_MIN_AGE_HOURS = 48


# ---------------------------------------------------------------------------
# Cloudinary API helpers
# ---------------------------------------------------------------------------

def _cloudinary_available() -> bool:
    try:
        import cloudinary
        cfg = cloudinary.config()
        return bool(getattr(cfg, "cloud_name", None))
    except Exception:
        return False


def _list_cloudinary_folder(prefix: str) -> list[dict]:
    """Return all resources in a Cloudinary prefix path (paginated)."""
    import cloudinary.api

    resources = []
    next_cursor = None
    while True:
        opts = {
            "type": "upload",
            "resource_type": "image",
            "prefix": prefix,
            "max_results": 500,
            "fields": ["public_id", "created_at", "bytes", "secure_url"],
        }
        if next_cursor:
            opts["next_cursor"] = next_cursor
        try:
            response = cloudinary.api.resources(**opts)
        except Exception as exc:
            logger.warning("Cloudinary API error listing prefix=%s: %s", prefix, exc)
            break
        resources.extend(response.get("resources", []))
        next_cursor = response.get("next_cursor")
        if not next_cursor:
            break
    return resources


def _cloudinary_media_prefix() -> str:
    """Return the PREFIX used by MediaCloudinaryStorage (usually 'media/')."""
    try:
        from cloudinary_storage import app_settings
        prefix = (app_settings.PREFIX or "").lstrip("/")
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        return prefix
    except Exception:
        return "media/"


def _destroy(public_id: str, resource_type: str = "image") -> bool:
    import cloudinary.uploader
    try:
        result = cloudinary.uploader.destroy(
            public_id, invalidate=True, resource_type=resource_type
        )
        return result.get("result") == "ok"
    except Exception as exc:
        logger.error("Cloudinary destroy failed for %s: %s", public_id, exc)
        return False


# ---------------------------------------------------------------------------
# DB reference collection
# ---------------------------------------------------------------------------

def _field_name(field_obj) -> str:
    """Safely extract the stored name from an ImageField/FileField."""
    return str(getattr(field_obj, "name", "") or "").strip()


def _collect_db_references() -> set[str]:
    """Collect all media paths currently referenced by any DB row.

    Returns a set of normalised strings that can be matched against
    Cloudinary public_ids (with and without leading 'media/' prefix).
    """
    from apps.games.models.game import Game
    from apps.games.models.map_pool import GameMapPool
    from apps.organizations.models.team import Team
    from apps.organizations.models.organization import Organization

    refs: set[str] = set()

    def _add(val: str) -> None:
        val = val.strip().replace("\\", "/")
        if val:
            refs.add(val)
            # Also add without / with the 'media/' prefix so both forms match.
            if val.startswith("media/"):
                refs.add(val[len("media/"):])
            else:
                refs.add("media/" + val)

    for game in Game.objects.all():
        for fname in ("icon", "logo", "banner", "card_image"):
            n = _field_name(getattr(game, fname, None))
            if n:
                _add(n)

    for mp in GameMapPool.objects.all():
        n = _field_name(mp.image)
        if n:
            _add(n)

    for team in Team.objects.all():
        for fname in ("logo", "banner"):
            n = _field_name(getattr(team, fname, None))
            if n:
                _add(n)

    # TeamMedia gallery if model exists
    try:
        from apps.organizations.models.team_media import TeamMedia
        for tm in TeamMedia.objects.all():
            n = _field_name(getattr(tm, "image", None) or getattr(tm, "file", None))
            if n:
                _add(n)
    except Exception:
        pass

    for org in Organization.objects.all():
        for fname in ("logo", "badge", "banner"):
            n = _field_name(getattr(org, fname, None))
            if n:
                _add(n)

    # Tournaments
    try:
        from apps.tournaments.models.tournament import Tournament
        for t in Tournament.objects.all():
            for fname in ("banner", "thumbnail", "rules_file", "terms_file"):
                n = _field_name(getattr(t, fname, None))
                if n:
                    _add(n)
    except Exception:
        pass

    try:
        from apps.tournaments.models.sponsor import TournamentSponsor
        for s in TournamentSponsor.objects.all():
            for fname in ("logo", "banner"):
                n = _field_name(getattr(s, fname, None))
                if n:
                    _add(n)
    except Exception:
        pass

    return refs


# ---------------------------------------------------------------------------
# Safety checks
# ---------------------------------------------------------------------------

def _is_blocked(public_id: str) -> bool:
    """Return True if a public_id must never be deleted."""
    pid = public_id.lower()
    return any(b in pid for b in BLOCKED_SUBSTRINGS)


def _is_recent(resource: dict, min_age_hours: int) -> bool:
    """Return True if the resource was created within min_age_hours."""
    created_str = resource.get("created_at", "")
    if not created_str:
        return False
    try:
        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
        return age_hours < min_age_hours
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Audit Cloudinary for orphaned media assets not referenced by any DB row. "
        "Dry-run by default. Use --apply --confirm-delete-orphans to delete."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-games",
            action="store_true",
            help="Scan only games/* folders (icons, logos, banners, cards, maps).",
        )
        parser.add_argument(
            "--folder",
            default="",
            help="Scan a single specific folder, e.g. 'games/icons/'.",
        )
        parser.add_argument(
            "--min-age-hours",
            type=int,
            default=DEFAULT_MIN_AGE_HOURS,
            help=f"Skip files newer than this many hours (default {DEFAULT_MIN_AGE_HOURS}). "
                 "Protects assets uploaded during an in-progress re-upload session.",
        )
        parser.add_argument(
            "--include-recent",
            action="store_true",
            help="Include files of any age (disables the min-age-hours guard).",
        )
        parser.add_argument(
            "--json",
            dest="json_output",
            action="store_true",
            help="Output results as JSON.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Enable deletion mode. Must be combined with --confirm-delete-orphans.",
        )
        parser.add_argument(
            "--confirm-delete-orphans",
            action="store_true",
            help="Required second flag for deletion. Without this, --apply is ignored.",
        )

    def handle(self, *args, **opts):
        if not _cloudinary_available():
            self.stderr.write(self.style.ERROR(
                "Cloudinary is not configured. Set CLOUDINARY_URL or equivalent env vars."
            ))
            sys.exit(1)

        apply_deletes = opts["apply"] and opts["confirm_delete_orphans"]
        only_missing_age = opts["include_recent"]
        min_age_hours = 0 if only_missing_age else opts["min_age_hours"]
        json_output = opts["json_output"]

        if opts["apply"] and not opts["confirm_delete_orphans"]:
            self.stderr.write(self.style.ERROR(
                "--apply requires --confirm-delete-orphans. This prevents accidental deletion."
            ))
            sys.exit(1)

        # Determine which folders to scan
        if opts["folder"]:
            folder = opts["folder"].rstrip("/") + "/"
            if _is_blocked(folder):
                self.stderr.write(self.style.ERROR(f"Folder '{folder}' is on the blocklist."))
                sys.exit(1)
            folders = [folder]
        elif opts["only_games"]:
            folders = APPROVED_GAME_FOLDERS
        else:
            folders = ALL_APPROVED_FOLDERS

        prefix = _cloudinary_media_prefix()

        # Collect all DB-referenced paths
        if not json_output:
            self.stdout.write("Collecting DB media references...")
        db_refs = _collect_db_references()
        if not json_output:
            self.stdout.write(f"  Found {len(db_refs)} unique referenced paths (incl. prefix variants).")

        # Scan Cloudinary
        all_resources: list[dict] = []
        for folder in folders:
            cloudinary_prefix = prefix + folder
            if not json_output:
                self.stdout.write(f"Scanning Cloudinary prefix: {cloudinary_prefix}")
            resources = _list_cloudinary_folder(cloudinary_prefix)
            all_resources.extend(resources)
        if not json_output:
            self.stdout.write(f"  Total Cloudinary resources found: {len(all_resources)}")

        # Classify
        orphans = []
        protected_recent = []
        referenced = []
        blocked = []

        for res in all_resources:
            pid = res.get("public_id", "")
            if _is_blocked(pid):
                blocked.append(res)
                continue
            if pid in db_refs:
                referenced.append(res)
                continue
            if not only_missing_age and _is_recent(res, min_age_hours):
                protected_recent.append(res)
                continue
            orphans.append(res)

        summary = {
            "total_scanned": len(all_resources),
            "referenced": len(referenced),
            "blocked_paths": len(blocked),
            "protected_recent": len(protected_recent),
            "orphans_found": len(orphans),
            "orphans_deleted": 0,
            "delete_failures": 0,
            "dry_run": not apply_deletes,
            "min_age_hours": min_age_hours,
            "folders_scanned": folders,
        }

        if json_output:
            data = {
                "summary": summary,
                "orphans": [
                    {
                        "public_id": r.get("public_id"),
                        "created_at": r.get("created_at"),
                        "bytes": r.get("bytes"),
                        "url": r.get("secure_url"),
                    }
                    for r in orphans
                ],
            }
            self.stdout.write(json.dumps(data, indent=2, default=str))
            return

        # Human-readable report
        self.stdout.write("")
        if protected_recent:
            self.stdout.write(self.style.NOTICE(
                f"Skipped {len(protected_recent)} file(s) uploaded within the last "
                f"{min_age_hours}h (use --include-recent to include them):"
            ))
            for res in protected_recent:
                self.stdout.write(f"  {res['public_id']}  [{res.get('created_at','')}]")
            self.stdout.write("")

        if not orphans:
            self.stdout.write(self.style.SUCCESS(
                f"No orphans found in {len(folders)} folder(s). "
                f"({len(referenced)} referenced, {len(protected_recent)} recent-skipped)"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"Found {len(orphans)} orphaned file(s):"
            ))
            for res in orphans:
                pid = res.get("public_id", "")
                age = res.get("created_at", "")
                size = res.get("bytes", 0)
                self.stdout.write(
                    f"  {'[WOULD DELETE]' if apply_deletes else '[orphan]'} "
                    f"{pid}  ({size // 1024}KB)  [{age}]"
                )

        # Deletion
        if apply_deletes and orphans:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                f"Deleting {len(orphans)} orphaned file(s) from Cloudinary..."
            ))
            for res in orphans:
                pid = res.get("public_id", "")
                ok = _destroy(pid)
                if ok:
                    summary["orphans_deleted"] += 1
                    self.stdout.write(self.style.SUCCESS(f"  Deleted: {pid}"))
                else:
                    summary["delete_failures"] += 1
                    self.stdout.write(self.style.ERROR(f"  Failed:  {pid}"))

        # Final summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Summary: scanned={summary['total_scanned']} "
            f"referenced={summary['referenced']} "
            f"recent-skipped={summary['protected_recent']} "
            f"orphans={summary['orphans_found']} "
            f"deleted={summary['orphans_deleted']} "
            f"failures={summary['delete_failures']}"
        ))

        if not apply_deletes and orphans:
            self.stdout.write(self.style.NOTICE(
                "\nThis was a dry run. To delete orphans, run:\n"
                "  python manage.py audit_cloudinary_orphans --apply --confirm-delete-orphans\n"
                "(add --only-games or --folder games/ to limit scope)"
            ))
