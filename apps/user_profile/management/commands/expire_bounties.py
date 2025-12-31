# apps/user_profile/management/commands/expire_bounties.py
"""
Management command to expire open bounties past their expiry timestamp.

Usage:
    python manage.py expire_bounties [--batch-size=100] [--dry-run]

Designed to run via cron every 15 minutes:
    */15 * * * * cd /path/to/project && python manage.py expire_bounties

Design: 03a_bounty_system_design.md (Section 3: Expiry Mechanism)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.user_profile.services.bounty_service import expire_open_bounties


class Command(BaseCommand):
    help = 'Expire open bounties past their expiry timestamp and refund creators'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Maximum bounties to process per run (default: 100)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be expired without actually expiring'
        )
    
    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.WARNING(
            f'Starting bounty expiry task (batch_size={batch_size}, dry_run={dry_run})'
        ))
        self.stdout.write(f'Current time: {timezone.now()}')
        
        if dry_run:
            # Dry run: just count
            from apps.user_profile.models import Bounty, BountyStatus
            count = Bounty.objects.filter(
                status=BountyStatus.OPEN,
                expires_at__lte=timezone.now()
            ).count()
            
            self.stdout.write(self.style.SUCCESS(
                f'[DRY RUN] Would expire {count} bounties'
            ))
            return
        
        # Execute expiry
        result = expire_open_bounties(batch_size=batch_size)
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Bounty expiry task completed:'))
        self.stdout.write(f'  - Total found: {result["total_found"]}')
        self.stdout.write(f'  - Processed: {result["processed"]}')
        self.stdout.write(f'  - Failed: {result["failed"]}')
        self.stdout.write(f'  - Skipped: {result["skipped"]}')
        
        if result['failed'] > 0:
            self.stdout.write(self.style.ERROR(
                f'⚠️ {result["failed"]} bounties failed to expire (check logs)'
            ))
        
        if result['processed'] > 0:
            self.stdout.write(self.style.SUCCESS(
                f'✅ {result["processed"]} bounties expired and refunded'
            ))
