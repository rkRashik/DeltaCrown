from collections import defaultdict
from dataclasses import dataclass
from typing import List, Tuple

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction


@dataclass
class DupeGroup:
    key: Tuple[str, str]  # (game, normalized_name_or_tag)
    ids: List[int]


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


class Command(BaseCommand):
    """
    Audit (and optionally fix) case-insensitive duplicates for Team name/tag per game.

    Usage:
      python manage.py audit_uniqueness            # dry-run, prints duplicates if any
      python manage.py audit_uniqueness --fix      # attempts to auto-fix (non-destructive)
      python manage.py audit_uniqueness --dry-run  # explicit dry-run
    """

    help = "Audit (and optionally fix) case-insensitive duplicates for Team name/tag per game."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Attempt to auto-fix duplicates by appending a numeric suffix to name/tag.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without writing any changes (default unless --fix is passed).",
        )

    def handle(self, *args, **opts):
        Team = apps.get_model("teams", "Team")

        # If migrations haven't run yet, bail early
        if not hasattr(Team, "name_ci") or not hasattr(Team, "tag_ci"):
            self.stderr.write(self.style.ERROR("Team.name_ci / Team.tag_ci not found — apply migrations first."))
            return  # don't return ints

        # Build maps: (game, normalized value) -> [ids]
        by_name = defaultdict(list)
        by_tag = defaultdict(list)

        qs = Team.objects.all().only("id", "name", "tag", "game")
        for t in qs.iterator(chunk_size=500):
            by_name[(str(t.game or ""), _norm(t.name))].append(t.id)
            by_tag[(str(t.game or ""), _norm(t.tag))].append(t.id)

        name_dupes: List[DupeGroup] = [
            DupeGroup(k, v) for k, v in by_name.items() if _norm(k[1]) and len(v) > 1
        ]
        tag_dupes: List[DupeGroup] = [
            DupeGroup(k, v) for k, v in by_tag.items() if _norm(k[1]) and len(v) > 1
        ]

        if not name_dupes and not tag_dupes:
            self.stdout.write(self.style.SUCCESS("No case-insensitive duplicates found for Team name/tag."))
            return

        self.stdout.write(self.style.WARNING("Duplicates detected:"))
        for grp in name_dupes:
            self.stdout.write(f"- NAME {grp.key} => ids={grp.ids}")
        for grp in tag_dupes:
            self.stdout.write(f"- TAG  {grp.key} => ids={grp.ids}")

        # Stop here in dry-run mode (default)
        if not opts.get("fix", False):
            self.stdout.write(self.style.SUCCESS("\nRe-run with --fix to attempt auto-resolution (non-destructive)."))
            return

        # Fix strategy (preserve the FIRST row's casing as canonical):
        #   Names: Alpha, alpha, ALPHA  -> keep first as 'Alpha', change others to 'Alpha-2', 'Alpha-3', ...
        #   Tags:  ALP, alp, Alp       -> keep first as 'ALP',   change others to 'ALP2', 'ALP3', ...
        with transaction.atomic():
            # Fix names
            for grp in name_dupes:
                ids_sorted = sorted(grp.ids)
                rows = list(Team.objects.filter(id__in=ids_sorted).only("id", "name").order_by("id"))
                if not rows:
                    continue

                # First row's original casing becomes canonical base
                base_display = (rows[0].name or "").strip()
                seen_norm = { _norm(base_display) } if base_display else set()
                suffix = 1

                # Keep first as-is; fix subsequent with canonical base
                for team in rows[1:]:
                    current = (team.name or "").strip()
                    if not current:
                        continue
                    low = _norm(current)
                    if low not in seen_norm:
                        seen_norm.add(low)
                        continue
                    suffix += 1
                    team.name = f"{base_display}-{suffix}"
                    team.save(update_fields=["name"])
                    self.stdout.write(self.style.NOTICE(f"Adjusted name id={team.id} -> {team.name}"))

            # Fix tags
            for grp in tag_dupes:
                ids_sorted = sorted(grp.ids)
                rows = list(Team.objects.filter(id__in=ids_sorted).only("id", "tag").order_by("id"))
                if not rows:
                    continue

                base_display = (rows[0].tag or "").strip()
                seen_norm = { _norm(base_display) } if base_display else set()
                suffix = 1

                for team in rows[1:]:
                    current = (team.tag or "").strip()
                    if not current:
                        continue
                    low = _norm(current)
                    if low not in seen_norm:
                        seen_norm.add(low)
                        continue
                    suffix += 1
                    team.tag = f"{base_display}{suffix}"
                    team.save(update_fields=["tag"])
                    self.stdout.write(self.style.NOTICE(f"Adjusted tag  id={team.id} -> {team.tag}"))

        self.stdout.write(self.style.SUCCESS("Auto-fix complete. Re-run without --fix to verify duplicates are gone."))
