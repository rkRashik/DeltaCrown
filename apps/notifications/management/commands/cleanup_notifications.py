"""
Management command to cleanup old notifications.
Can be run manually or via cron as an alternative to Celery Beat.
"""
from django.core.management.base import BaseCommand
from apps.notifications.tasks import cleanup_old_notifications


class Command(BaseCommand):
    help = 'Cleanup old read notifications (default: older than 90 days)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to keep notifications (default: 90)'
        )

    def handle(self, *args, **options):
        days_to_keep = options['days']
        
        self.stdout.write(f'Cleaning up notifications older than {days_to_keep} days...')
        
        try:
            result = cleanup_old_notifications(days_to_keep=days_to_keep)
            
            if result['status'] == 'success':
                deleted_count = result.get('deleted_count', 0)
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully deleted {deleted_count} old notification{'' if deleted_count == 1 else 's'}"
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"Failed: {result.get('error', 'Unknown error')}"
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
