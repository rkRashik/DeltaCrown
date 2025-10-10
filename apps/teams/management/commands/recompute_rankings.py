"""
Management command to recompute team rankings.
Can be run manually or via cron as an alternative to Celery Beat.
"""
from django.core.management.base import BaseCommand
from apps.teams.tasks import recompute_team_rankings


class Command(BaseCommand):
    help = 'Recompute team rankings after tournaments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tournament-id',
            type=int,
            help='Optional tournament ID to recalculate rankings for specific tournament'
        )

    def handle(self, *args, **options):
        tournament_id = options.get('tournament_id')
        
        self.stdout.write('Starting team ranking recalculation...')
        
        try:
            result = recompute_team_rankings(tournament_id=tournament_id)
            
            if result['status'] == 'success':
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully updated {result['updated_count']} teams"
                ))
                self.stdout.write(f"Deduplication key: {result.get('dedup_key', 'N/A')}")
            else:
                self.stdout.write(self.style.ERROR(
                    f"Failed: {result.get('error', 'Unknown error')}"
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
