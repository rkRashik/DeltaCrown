"""
Management command to distribute tournament payouts.
Can be run manually or via cron as an alternative to Celery Beat.
"""
from django.core.management.base import BaseCommand
from apps.teams.tasks import distribute_tournament_payouts


class Command(BaseCommand):
    help = 'Distribute coin payouts to tournament winners'

    def add_arguments(self, parser):
        parser.add_argument(
            'tournament_id',
            type=int,
            help='Tournament ID to distribute payouts for'
        )

    def handle(self, *args, **options):
        tournament_id = options['tournament_id']
        
        self.stdout.write(f'Distributing payouts for tournament {tournament_id}...')
        
        try:
            result = distribute_tournament_payouts(tournament_id)
            
            if result['status'] == 'success':
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully distributed payouts"
                ))
                
                for payout in result.get('payouts', []):
                    self.stdout.write(
                        f"  {payout['place']}: {payout['team']} - {payout['amount']} coins"
                    )
                
                self.stdout.write(f"Deduplication key: {result.get('dedup_key', 'N/A')}")
                
            elif result['status'] == 'already_distributed':
                self.stdout.write(self.style.WARNING(
                    'Payouts already distributed for this tournament'
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"Failed: {result.get('error', 'Unknown error')}"
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
