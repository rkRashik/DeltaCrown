"""
Management command to backfill broken knockout Match records.

Repairs Match rows created before the P0-1/P0-2 fixes:
  - Sets bracket FK from BracketNode.bracket where Match.bracket is NULL.
  - Sets scheduled_time from tournament.tournament_start where NULL.

Safe to run multiple times (idempotent).

Usage:
    python manage.py backfill_knockout_bracket_fk
    python manage.py backfill_knockout_bracket_fk --dry-run
    python manage.py backfill_knockout_bracket_fk --tournament-id 42
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = "Backfill bracket FK and scheduled_time on knockout Match records created before P0 fixes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without modifying the database.",
        )
        parser.add_argument(
            "--tournament-id",
            type=int,
            default=None,
            help="Limit backfill to a single tournament.",
        )

    def handle(self, *args, **options):
        from apps.tournaments.models.match import Match

        dry_run = options["dry_run"]
        tournament_id = options["tournament_id"]
        prefix = "[DRY RUN] " if dry_run else ""

        # ── Phase 1: bracket FK backfill ────────────────────────────
        qs = Match.objects.filter(
            bracket__isnull=True,
            bracket_node__isnull=False,
        )
        if tournament_id:
            qs = qs.filter(tournament_id=tournament_id)

        qs = qs.select_related("bracket_node__bracket")

        bracket_fixed = 0
        bracket_errors = []

        self.stdout.write(f"{prefix}Phase 1: Scanning matches with NULL bracket FK …")

        for match in qs.iterator():
            node_bracket = getattr(getattr(match, "bracket_node", None), "bracket", None)
            if node_bracket is None:
                bracket_errors.append(match.id)
                continue

            if not dry_run:
                with transaction.atomic():
                    match.bracket = node_bracket
                    match.save(update_fields=["bracket"])

            bracket_fixed += 1
            self.stdout.write(
                f"  {prefix}Match {match.id} → bracket={node_bracket.id}"
            )

        # ── Phase 2: scheduled_time backfill ────────────────────────
        qs2 = Match.objects.filter(scheduled_time__isnull=True)
        if tournament_id:
            qs2 = qs2.filter(tournament_id=tournament_id)

        qs2 = qs2.select_related("tournament")

        time_fixed = 0

        self.stdout.write(f"\n{prefix}Phase 2: Scanning matches with NULL scheduled_time …")

        for match in qs2.iterator():
            fallback = getattr(match.tournament, "tournament_start", None) or timezone.now()
            if not dry_run:
                with transaction.atomic():
                    match.scheduled_time = fallback
                    match.save(update_fields=["scheduled_time"])

            time_fixed += 1
            self.stdout.write(
                f"  {prefix}Match {match.id} → scheduled_time={fallback}"
            )

        # ── Summary ─────────────────────────────────────────────────
        self.stdout.write(f"\n{prefix}Done.")
        self.stdout.write(f"  bracket FK fixed: {bracket_fixed}")
        if bracket_errors:
            self.stderr.write(
                f"  bracket FK errors (no node.bracket): {bracket_errors}"
            )
        self.stdout.write(f"  scheduled_time fixed: {time_fixed}")
