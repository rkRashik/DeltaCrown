"""Seed competitive seasons and snapshot current rankings into history."""
from datetime import datetime, timezone as _tz
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed competitive seasons (S1, S2, S3) and snapshot current rankings'

    def handle(self, *args, **options):
        from apps.leaderboards.models import Season, LeaderboardSnapshot
        from apps.organizations.models import Team, TeamRanking
        from apps.organizations.choices import TeamStatus

        seasons_data = [
            {
                'season_id': 'S1-2025',
                'name': 'Season 1',
                'start_date': datetime(2025, 9, 1, tzinfo=_tz.utc),
                'end_date': datetime(2025, 12, 31, 23, 59, 59, tzinfo=_tz.utc),
                'is_active': False,
            },
            {
                'season_id': 'S2-2026',
                'name': 'Season 2',
                'start_date': datetime(2026, 1, 1, tzinfo=_tz.utc),
                'end_date': datetime(2026, 2, 28, 23, 59, 59, tzinfo=_tz.utc),
                'is_active': False,
            },
            {
                'season_id': 'S3-2026',
                'name': 'Season 3',
                'start_date': datetime(2026, 3, 1, tzinfo=_tz.utc),
                'end_date': datetime(2026, 8, 31, 23, 59, 59, tzinfo=_tz.utc),
                'is_active': True,
            },
        ]

        for sd in seasons_data:
            obj, created = Season.objects.update_or_create(
                season_id=sd['season_id'],
                defaults=sd,
            )
            status = 'CREATED' if created else 'UPDATED'
            self.stdout.write(f'  {status}: {obj.name} ({obj.season_id}) active={obj.is_active}')

        now = timezone.now()
        active = Season.objects.filter(is_active=True).first()
        if not active:
            self.stdout.write(self.style.WARNING('No active season found'))
            return

        rankings = TeamRanking.objects.select_related('team').filter(
            team__status=TeamStatus.ACTIVE,
            team__visibility='PUBLIC',
        ).order_by('-current_cp')

        created_count = 0
        for idx, r in enumerate(rankings, start=1):
            _, created = LeaderboardSnapshot.objects.update_or_create(
                date=now.date(),
                leaderboard_type='seasonal',
                team=r.team,
                defaults={
                    'rank': r.global_rank or idx,
                    'points': r.current_cp or 0,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Snapshotted {created_count} rankings for {active.name} ({now.date()})'
        ))
