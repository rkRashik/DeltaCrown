"""
Management command to backfill public_id for existing UserProfile records.

Usage:
    python manage.py backfill_public_ids --dry-run
    python manage.py backfill_public_ids --limit 100
    python manage.py backfill_public_ids  # backfill all
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.user_profile.models_main import UserProfile
from apps.user_profile.services.public_id import PublicIDGenerator
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill public_id for UserProfile records missing it"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of profiles to backfill (default: all)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        # Find profiles without public_id
        queryset = UserProfile.objects.filter(public_id__isnull=True)
        total_missing = queryset.count()

        if total_missing == 0:
            self.stdout.write(self.style.SUCCESS('✅ All profiles already have public_id'))
            return

        self.stdout.write(f"Found {total_missing} profiles without public_id")

        if limit:
            queryset = queryset[:limit]
            self.stdout.write(f"Processing {limit} profiles (limited)")

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
            for profile in queryset:
                self.stdout.write(f"  Would assign public_id to user_id={profile.user_id}")
            return

        # Backfill
        success_count = 0
        error_count = 0

        for profile in queryset:
            try:
                with transaction.atomic():
                    # Re-check in case another process assigned it
                    profile.refresh_from_db()
                    if profile.public_id:
                        self.stdout.write(f"  ⏭️  user_id={profile.user_id} already has public_id")
                        continue

                    # Generate and assign
                    public_id = PublicIDGenerator.generate_public_id()
                    profile.public_id = public_id
                    profile.save(update_fields=['public_id', 'updated_at'])
                    
                    success_count += 1
                    self.stdout.write(f"  ✅ user_id={profile.user_id} → {public_id}")
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  ❌ user_id={profile.user_id} failed: {e}")
                )
                logger.exception(f"Failed to backfill public_id for user_id={profile.user_id}")

        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully backfilled: {success_count}"))
        if error_count:
            self.stdout.write(self.style.ERROR(f"❌ Errors: {error_count}"))
        self.stdout.write("="*50)
