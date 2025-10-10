"""
Management command to send daily notification digests.
Can be run manually or via cron as an alternative to Celery Beat.
"""
from django.core.management.base import BaseCommand
from apps.notifications.tasks import send_daily_digest


class Command(BaseCommand):
    help = 'Send daily notification digest emails to all users'

    def handle(self, *args, **options):
        self.stdout.write('Sending daily notification digests...')
        
        try:
            result = send_daily_digest()
            
            if result['status'] == 'success':
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully sent {result['sent_count']} digests"
                ))
                self.stdout.write(
                    f"Skipped {result['skipped_count']} users (no notifications or digest disabled)"
                )
            else:
                self.stdout.write(self.style.ERROR(
                    f"Failed: {result.get('error', 'Unknown error')}"
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
