"""
Management command to bootstrap TeamRanking rows for all active teams.

Ensures every ACTIVE team has a TeamRanking record (0 CP, ROOKIE tier).
Idempotent — safe to run multiple times. Skips teams that already have a ranking.

Usage:
    python manage.py bootstrap_team_rankings
    python manage.py bootstrap_team_rankings --dry-run
    python manage.py bootstrap_team_rankings --check
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organizations.models import Team, TeamRanking


class Command(BaseCommand):
    help = 'Bootstrap TeamRanking rows for all ACTIVE teams that lack one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without writing to the database',
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Only run the integrity check (teams vs rankings count)',
        )

    def handle(self, *args, **options):
        if options['check']:
            self._integrity_check()
            return

        active_teams = Team.objects.filter(status='ACTIVE')
        existing_ids = set(
            TeamRanking.objects.filter(
                team_id__in=active_teams.values_list('id', flat=True)
            ).values_list('team_id', flat=True)
        )

        missing = [t for t in active_teams if t.id not in existing_ids]

        if not missing:
            self.stdout.write(self.style.SUCCESS(
                f'All {active_teams.count()} active teams already have rankings. Nothing to do.'
            ))
            self._integrity_check()
            return

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                f'[DRY RUN] Would create {len(missing)} TeamRanking rows:'
            ))
            for team in missing:
                self.stdout.write(f'  - {team.name} (id={team.id})')
            return

        rows = [TeamRanking(team=team) for team in missing]
        with transaction.atomic():
            TeamRanking.objects.bulk_create(rows, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(
            f'Created {len(rows)} TeamRanking rows (0 CP, ROOKIE).'
        ))

        # Compute global rank positions
        from apps.organizations.services.ranking_service import compute_global_ranks
        ranked = compute_global_ranks()
        self.stdout.write(self.style.SUCCESS(f'Global ranks assigned for {ranked} teams.'))

        self._integrity_check()

    def _integrity_check(self):
        active_count = Team.objects.filter(status='ACTIVE').count()
        ranking_count = TeamRanking.objects.filter(team__status='ACTIVE').count()

        if active_count == ranking_count:
            self.stdout.write(self.style.SUCCESS(
                f'[INTEGRITY OK] {active_count} active teams, {ranking_count} rankings — 100% coverage.'
            ))
        else:
            gap = active_count - ranking_count
            self.stdout.write(self.style.ERROR(
                f'[INTEGRITY FAIL] {active_count} active teams, {ranking_count} rankings — {gap} missing.'
            ))
