"""
Management command: replay completed matches through the CP ranking pipeline.

Use this to backfill Crown Points for completed matches that were never
processed (e.g., matches completed before the event handler was wired).

Usage:
    python manage.py backfill_match_cp              # Process all completed matches
    python manage.py backfill_match_cp --dry-run    # Preview without applying
    python manage.py backfill_match_cp --reset      # Reset all CP to 0 then replay
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.tournaments.models import Match
from apps.organizations.models import TeamRanking
from apps.organizations.services.match_integration import MatchResultIntegrator
from apps.organizations.services.ranking_service import compute_global_ranks

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Replay completed matches through the CP ranking pipeline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without applying any changes.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset all TeamRanking CP to 0 and streaks before replaying.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        reset = options["reset"]

        matches = (
            Match.objects.filter(
                state="COMPLETED",
                winner_id__isnull=False,
                loser_id__isnull=False,
            )
            .order_by("updated_at", "id")
            .only("id", "winner_id", "loser_id", "tournament_id")
        )

        count = matches.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No completed matches to backfill."))
            return

        self.stdout.write(f"Found {count} completed match(es) to process.")

        if dry_run:
            for m in matches:
                self.stdout.write(
                    f"  [DRY-RUN] Match {m.id}: winner={m.winner_id} loser={m.loser_id}"
                )
            self.stdout.write(self.style.WARNING("Dry-run complete. No changes made."))
            return

        if reset:
            self.stdout.write("Resetting all TeamRanking CP / streaks ...")
            TeamRanking.objects.all().update(
                current_cp=0,
                season_cp=0,
                all_time_cp=0,
                tier="ROOKIE",
                streak_count=0,
                is_hot_streak=False,
                global_rank=None,
            )
            self.stdout.write(self.style.WARNING("All rankings reset to zero."))

        ok = 0
        failed = 0
        for m in matches.iterator():
            result = MatchResultIntegrator.process_match_result(
                winner_team_id=m.winner_id,
                loser_team_id=m.loser_id,
                match_id=m.id,
                is_tournament_match=bool(m.tournament_id),
            )
            if result.success and result.vnext_processed:
                ok += 1
            else:
                failed += 1
                self.stderr.write(
                    f"  FAILED Match {m.id}: {result.error_message or 'unknown'}"
                )

        compute_global_ranks()

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete: {ok} processed, {failed} failed, "
                f"global ranks recomputed."
            )
        )
