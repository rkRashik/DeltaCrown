# apps/accounts/management/commands/process_account_deletions.py
"""
Management command to process pending account deletions.

Usage:
    python manage.py process_account_deletions
    
This should be run daily via cron/scheduler:
    0 2 * * * cd /path/to/project && python manage.py process_account_deletions
"""
from django.core.management.base import BaseCommand
from apps.accounts.deletion_services import process_pending_deletions


class Command(BaseCommand):
    help = 'Process account deletion requests that have reached their scheduled_for date'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No actual deletions will occur'))
            # TODO: Implement dry-run logic if needed
            return
        
        self.stdout.write('Processing pending account deletions...')
        
        result = process_pending_deletions()
        
        self.stdout.write(self.style.SUCCESS(
            f"\nProcessed: {result['processed']} accounts"
        ))
        
        if result['failed'] > 0:
            self.stdout.write(self.style.ERROR(
                f"Failed: {result['failed']} accounts"
            ))
        
        if result['results']:
            self.stdout.write('\nDetails:')
            for item in result['results']:
                if item['status'] == 'success':
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ User {item['user_id']}: {item['message']}"
                    ))
                else:
                    self.stdout.write(self.style.ERROR(
                        f"  ✗ User {item['user_id']}: {item['message']}"
                    ))
        else:
            self.stdout.write('No pending deletions found.')
