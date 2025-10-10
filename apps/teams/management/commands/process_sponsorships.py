"""
Management command to expire sponsors and promotions.
Can be run manually or via cron as an alternative to Celery Beat.
"""
from django.core.management.base import BaseCommand
from apps.teams.tasks import expire_sponsors_task, process_scheduled_promotions_task


class Command(BaseCommand):
    help = 'Expire sponsors and process scheduled promotions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sponsors-only',
            action='store_true',
            help='Only process sponsor expiration'
        )
        parser.add_argument(
            '--promotions-only',
            action='store_true',
            help='Only process promotions'
        )

    def handle(self, *args, **options):
        sponsors_only = options.get('sponsors_only', False)
        promotions_only = options.get('promotions_only', False)
        
        # If neither flag is set, process both
        process_both = not sponsors_only and not promotions_only
        
        if sponsors_only or process_both:
            self.stdout.write('Processing sponsor expirations...')
            try:
                result = expire_sponsors_task()
                if result['status'] == 'success':
                    self.stdout.write(self.style.SUCCESS(
                        f"Successfully processed sponsors: {result.get('expired_count', 0)} expired"
                    ))
                else:
                    self.stdout.write(self.style.ERROR(f"Failed: {result.get('error')}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing sponsors: {str(e)}"))
        
        if promotions_only or process_both:
            self.stdout.write('Processing scheduled promotions...')
            try:
                result = process_scheduled_promotions_task()
                if result['status'] == 'success':
                    self.stdout.write(self.style.SUCCESS(
                        f"Successfully processed promotions: "
                        f"{result.get('activated_count', 0)} activated, "
                        f"{result.get('expired_count', 0)} expired"
                    ))
                else:
                    self.stdout.write(self.style.ERROR(f"Failed: {result.get('error')}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing promotions: {str(e)}"))
