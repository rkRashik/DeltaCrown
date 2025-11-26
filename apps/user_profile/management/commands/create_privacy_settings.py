# apps/user_profile/management/commands/create_privacy_settings.py
"""
Management command to create PrivacySettings and VerificationRecord 
for existing UserProfile instances.

Usage:
    python manage.py create_privacy_settings
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.user_profile.models import UserProfile, PrivacySettings, VerificationRecord


class Command(BaseCommand):
    help = 'Create PrivacySettings and VerificationRecord for existing UserProfiles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating anything',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Creating Privacy Settings & Verification Records'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be made\n'))
        
        # Get all user profiles
        profiles = UserProfile.objects.all()
        total_profiles = profiles.count()
        
        self.stdout.write(f'\nFound {total_profiles} user profiles\n')
        
        # Count existing records
        existing_privacy = PrivacySettings.objects.count()
        existing_verification = VerificationRecord.objects.count()
        
        self.stdout.write(f'Existing PrivacySettings: {existing_privacy}')
        self.stdout.write(f'Existing VerificationRecords: {existing_verification}\n')
        
        # Calculate what needs to be created
        profiles_needing_privacy = profiles.exclude(
            privacy_settings__isnull=False
        ).count()
        
        profiles_needing_verification = profiles.exclude(
            verification_record__isnull=False
        ).count()
        
        self.stdout.write(self.style.WARNING(
            f'\nProfiles needing PrivacySettings: {profiles_needing_privacy}'
        ))
        self.stdout.write(self.style.WARNING(
            f'Profiles needing VerificationRecord: {profiles_needing_verification}\n'
        ))
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                '\n✓ Dry run complete. Use without --dry-run to create records.'
            ))
            return
        
        # Create records
        privacy_created = 0
        verification_created = 0
        
        with transaction.atomic():
            for profile in profiles:
                # Create PrivacySettings if doesn't exist
                privacy, created = PrivacySettings.objects.get_or_create(
                    user_profile=profile,
                    defaults={
                        # Profile Visibility (default: all public except sensitive data)
                        'show_real_name': False,
                        'show_phone': False,
                        'show_email': False,
                        'show_age': True,
                        'show_gender': True,
                        'show_country': True,
                        'show_address': False,
                        # Gaming & Activity
                        'show_game_ids': True,
                        'show_match_history': True,
                        'show_teams': True,
                        'show_achievements': True,
                        # Economy & Inventory
                        'show_inventory_value': False,
                        'show_level_xp': True,
                        # Social
                        'show_social_links': True,
                        # Interaction Permissions
                        'allow_team_invites': True,
                        'allow_friend_requests': True,
                        'allow_direct_messages': True,
                    }
                )
                if created:
                    privacy_created += 1
                
                # Create VerificationRecord if doesn't exist
                verification, created = VerificationRecord.objects.get_or_create(
                    user_profile=profile,
                    defaults={'status': 'unverified'}
                )
                if created:
                    verification_created += 1
                
                # Progress indicator
                if (privacy_created + verification_created) % 100 == 0:
                    self.stdout.write('.', ending='')
                    self.stdout.flush()
        
        self.stdout.write('\n')
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Created {privacy_created} PrivacySettings records'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'✓ Created {verification_created} VerificationRecord records'
        ))
        
        # Final counts
        final_privacy = PrivacySettings.objects.count()
        final_verification = VerificationRecord.objects.count()
        
        self.stdout.write(f'\nFinal counts:')
        self.stdout.write(f'  PrivacySettings: {final_privacy} (was {existing_privacy})')
        self.stdout.write(f'  VerificationRecords: {final_verification} (was {existing_verification})')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Migration complete!\n'))
