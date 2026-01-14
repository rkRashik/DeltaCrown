"""
Management command to backfill SocialLink model from legacy UserProfile fields.

UP.2 C2 CLEANUP - Legacy Social Links Removal
Date: 2026-01-15

This command migrates data from deprecated UserProfile fields to SocialLink model:
- youtube_link → SocialLink(platform='youtube')
- twitch_link → SocialLink(platform='twitch')
- twitter → SocialLink(platform='twitter')
- facebook → SocialLink(platform='facebook')
- instagram → SocialLink(platform='instagram')
- tiktok → SocialLink(platform='tiktok')
- discord_id → SocialLink(platform='discord', handle=discord_id)

SAFETY:
- Does NOT overwrite existing SocialLink entries (logs conflicts)
- Skips empty/blank fields
- Skips placeholder URLs (containing '@username')
- Normalizes URLs (adds https:// if missing)
- Reports all changes for audit trail

Run: python manage.py backfill_social_links
Dry run: python manage.py backfill_social_links --dry-run
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile, SocialLink
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = 'Backfill SocialLink model from legacy UserProfile social fields'
    
    # Placeholder URLs to skip
    PLACEHOLDERS = [
        'https://youtube.com/@username',
        'https://www.youtube.com/@username',
        'https://tiktok.com/@username',
        'https://www.tiktok.com/@username',
        'https://twitter.com/username',
        'https://x.com/username',
        'https://twitch.tv/username',
        'https://www.twitch.tv/username',
        'https://facebook.com/username',
        'https://www.facebook.com/username',
        'https://instagram.com/username',
        'https://www.instagram.com/username',
    ]
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed per-user migration logs',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('UP.2 C2 CLEANUP - Social Links Backfill'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made\n'))
        
        # Statistics tracking
        stats = {
            'users_processed': 0,
            'users_with_legacy_data': 0,
            'migrated': {
                'youtube': 0,
                'twitch': 0,
                'twitter': 0,
                'facebook': 0,
                'instagram': 0,
                'tiktok': 0,
                'discord': 0,
            },
            'skipped_empty': {
                'youtube': 0,
                'twitch': 0,
                'twitter': 0,
                'facebook': 0,
                'instagram': 0,
                'tiktok': 0,
                'discord': 0,
            },
            'skipped_placeholder': {
                'youtube': 0,
                'twitch': 0,
                'twitter': 0,
                'facebook': 0,
                'instagram': 0,
                'tiktok': 0,
                'discord': 0,
            },
            'conflicts': [],
            'errors': [],
        }
        
        # Platform field mapping
        platform_map = {
            'youtube': 'youtube_link',
            'twitch': 'twitch_link',
            'twitter': 'twitter',
            'facebook': 'facebook',
            'instagram': 'instagram',
            'tiktok': 'tiktok',
        }
        
        # Process all user profiles
        profiles = UserProfile.objects.select_related('user').all()
        total_profiles = profiles.count()
        
        self.stdout.write(f'Processing {total_profiles} user profiles...\n')
        
        for idx, profile in enumerate(profiles, 1):
            stats['users_processed'] += 1
            username = profile.user.username
            user_had_legacy_data = False
            
            if verbose:
                self.stdout.write(f'[{idx}/{total_profiles}] Processing @{username}...')
            
            # Process URL-based platforms
            for platform, field_name in platform_map.items():
                url = getattr(profile, field_name, '').strip()
                
                if not url:
                    stats['skipped_empty'][platform] += 1
                    continue
                
                user_had_legacy_data = True
                
                # Normalize URL
                if not url.startswith(('http://', 'https://')):
                    url = f'https://{url}'
                
                # Check for placeholder
                if url.lower() in [p.lower() for p in self.PLACEHOLDERS] or '@username' in url.lower():
                    stats['skipped_placeholder'][platform] += 1
                    if verbose:
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠️  Skipped {platform} placeholder: {url}'
                        ))
                    continue
                
                # Check for existing SocialLink
                existing = SocialLink.objects.filter(user=profile.user, platform=platform).first()
                
                if existing:
                    # Conflict: existing SocialLink differs from legacy
                    if existing.url != url:
                        conflict_msg = (
                            f'@{username} - {platform}: '
                            f'SocialLink has "{existing.url}", legacy has "{url}"'
                        )
                        stats['conflicts'].append(conflict_msg)
                        if verbose:
                            self.stdout.write(self.style.WARNING(
                                f'  ⚠️  CONFLICT: {conflict_msg}'
                            ))
                    else:
                        if verbose:
                            self.stdout.write(f'  ✓ {platform} already synced')
                    continue
                
                # Migrate to SocialLink
                if not dry_run:
                    try:
                        SocialLink.objects.create(
                            user=profile.user,
                            platform=platform,
                            url=url,
                            handle=''
                        )
                        stats['migrated'][platform] += 1
                        if verbose:
                            self.stdout.write(self.style.SUCCESS(
                                f'  ✅ Migrated {platform}: {url}'
                            ))
                    except Exception as e:
                        error_msg = f'@{username} - {platform}: {str(e)}'
                        stats['errors'].append(error_msg)
                        self.stdout.write(self.style.ERROR(f'  ❌ ERROR: {error_msg}'))
                else:
                    stats['migrated'][platform] += 1
                    if verbose:
                        self.stdout.write(self.style.SUCCESS(
                            f'  [DRY RUN] Would migrate {platform}: {url}'
                        ))
            
            # Process Discord (handle field)
            discord_id = profile.discord_id.strip()
            if discord_id:
                user_had_legacy_data = True
                existing = SocialLink.objects.filter(user=profile.user, platform='discord').first()
                
                if existing:
                    # Check if handle differs
                    if existing.handle != discord_id:
                        conflict_msg = (
                            f'@{username} - discord: '
                            f'SocialLink has handle "{existing.handle}", legacy has "{discord_id}"'
                        )
                        stats['conflicts'].append(conflict_msg)
                        if verbose:
                            self.stdout.write(self.style.WARNING(
                                f'  ⚠️  CONFLICT: {conflict_msg}'
                            ))
                    else:
                        if verbose:
                            self.stdout.write(f'  ✓ discord already synced')
                else:
                    # Migrate Discord handle only (no URL)
                    if not dry_run:
                        try:
                            SocialLink.objects.create(
                                user=profile.user,
                                platform='discord',
                                url='',
                                handle=discord_id
                            )
                            stats['migrated']['discord'] += 1
                            if verbose:
                                self.stdout.write(self.style.SUCCESS(
                                    f'  ✅ Migrated discord handle: {discord_id}'
                                ))
                        except Exception as e:
                            error_msg = f'@{username} - discord: {str(e)}'
                            stats['errors'].append(error_msg)
                            self.stdout.write(self.style.ERROR(f'  ❌ ERROR: {error_msg}'))
                    else:
                        stats['migrated']['discord'] += 1
                        if verbose:
                            self.stdout.write(self.style.SUCCESS(
                                f'  [DRY RUN] Would migrate discord handle: {discord_id}'
                            ))
            else:
                stats['skipped_empty']['discord'] += 1
            
            if user_had_legacy_data:
                stats['users_with_legacy_data'] += 1
        
        # Print summary report
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('BACKFILL SUMMARY'))
        self.stdout.write('=' * 80)
        
        self.stdout.write(f'\nUsers processed: {stats["users_processed"]}')
        self.stdout.write(f'Users with legacy data: {stats["users_with_legacy_data"]}')
        
        self.stdout.write('\n--- Migrated ---')
        for platform, count in stats['migrated'].items():
            if count > 0:
                self.stdout.write(self.style.SUCCESS(f'  {platform}: {count}'))
        
        total_migrated = sum(stats['migrated'].values())
        self.stdout.write(self.style.SUCCESS(f'  TOTAL: {total_migrated}'))
        
        self.stdout.write('\n--- Skipped (Empty) ---')
        for platform, count in stats['skipped_empty'].items():
            if count > 0:
                self.stdout.write(f'  {platform}: {count}')
        
        self.stdout.write('\n--- Skipped (Placeholder) ---')
        for platform, count in stats['skipped_placeholder'].items():
            if count > 0:
                self.stdout.write(self.style.WARNING(f'  {platform}: {count}'))
        
        if stats['conflicts']:
            self.stdout.write('\n' + self.style.WARNING('--- CONFLICTS (existing SocialLink differs) ---'))
            for conflict in stats['conflicts']:
                self.stdout.write(self.style.WARNING(f'  ⚠️  {conflict}'))
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  {len(stats["conflicts"])} conflicts detected. '
                'Existing SocialLink data was NOT overwritten.'
            ))
        
        if stats['errors']:
            self.stdout.write('\n' + self.style.ERROR('--- ERRORS ---'))
            for error in stats['errors']:
                self.stdout.write(self.style.ERROR(f'  ❌ {error}'))
        
        self.stdout.write('\n' + '=' * 80)
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\nDRY RUN COMPLETE - No changes were made to the database.'
            ))
            self.stdout.write('Run without --dry-run to apply changes.')
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ BACKFILL COMPLETE - Migrated {total_migrated} social links'
            ))
            
            if stats['conflicts']:
                self.stdout.write(self.style.WARNING(
                    f'\n⚠️  {len(stats["conflicts"])} conflicts require manual review'
                ))
        
        self.stdout.write('=' * 80 + '\n')
