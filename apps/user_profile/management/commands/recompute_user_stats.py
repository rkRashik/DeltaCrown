"""
Management command to recompute user tournament stats.

Usage:
    python manage.py recompute_user_stats --dry-run
    python manage.py recompute_user_stats --limit 100
    python manage.py recompute_user_stats --user-id 42
    python manage.py recompute_user_stats  # recompute all
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.user_profile.services.tournament_stats import TournamentStatsService
from apps.user_profile.models_main import UserProfile
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Recompute tournament & team stats for user profiles"

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
            help='Maximum number of users to process (default: all)',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            default=None,
            help='Recompute stats for specific user ID only',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        user_id = options['user_id']

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))

        # Single user mode
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                self.stdout.write(f"Processing user_id={user_id} ({user.username})")
                
                if not dry_run:
                    stats = TournamentStatsService.recompute_user_stats(user_id)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ Updated: matches={stats.matches_played}/{stats.matches_won}, "
                            f"tournaments={stats.tournaments_played}/{stats.tournaments_won}"
                        )
                    )
                else:
                    self.stdout.write(f"  Would recompute stats for user_id={user_id}")
                
                return
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ User {user_id} not found"))
                return
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ User {user_id} has no profile"))
                return

        # Batch mode: all users with profiles
        queryset = UserProfile.objects.select_related('user').all()
        total_profiles = queryset.count()

        if total_profiles == 0:
            self.stdout.write(self.style.SUCCESS('✅ No user profiles found'))
            return

        self.stdout.write(f"Found {total_profiles} user profiles")

        if limit:
            queryset = queryset[:limit]
            self.stdout.write(f"Processing {limit} profiles (limited)")

        success_count = 0
        error_count = 0

        for profile in queryset:
            try:
                if not dry_run:
                    stats = TournamentStatsService.recompute_user_stats(profile.user_id)
                    success_count += 1
                    self.stdout.write(
                        f"  ✅ {profile.user.username}: "
                        f"matches={stats.matches_played}/{stats.matches_won}, "
                        f"tournaments={stats.tournaments_played}/{stats.tournaments_won}"
                    )
                else:
                    self.stdout.write(f"  Would recompute stats for {profile.user.username}")
                    success_count += 1
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  ❌ {profile.user.username} failed: {e}")
                )
                logger.exception(f"Failed to recompute stats for user_id={profile.user_id}")

        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully processed: {success_count}"))
        if error_count:
            self.stdout.write(self.style.ERROR(f"❌ Errors: {error_count}"))
        self.stdout.write("="*50)
