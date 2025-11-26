# apps/user_profile/management/commands/test_xp_system.py
"""
Test the XP and badge awarding system

Usage:
    python manage.py test_xp_system <username>
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from apps.user_profile.services import award_xp, award_badge, check_level_up, XPService
from apps.user_profile.models import Badge, UserBadge

User = get_user_model()


class Command(BaseCommand):
    help = 'Test XP and badge system for a user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to test with')
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset user XP and badges before testing'
        )

    def handle(self, *args, **options):
        username = options['username']
        reset = options.get('reset', False)
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found")
        
        # Ensure user has a profile
        from apps.user_profile.models import UserProfile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'display_name': user.username}
        )
        if created:
            self.stdout.write(self.style.WARNING(f'Created UserProfile for {username}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n=== Testing XP System for {username} ===\n'))
        
        # Reset if requested
        if reset:
            profile.xp = 0
            profile.level = 0
            profile.pinned_badges = []
            profile.save()
            UserBadge.objects.filter(user=user).delete()
            self.stdout.write(self.style.WARNING('✓ Reset user XP and badges\n'))
        
        # Show current state
        self.stdout.write(f'Current Level: {profile.level}')
        self.stdout.write(f'Current XP: {profile.xp}')
        self.stdout.write(f'Badges Earned: {UserBadge.objects.filter(user=user).count()}\n')
        
        # Test 1: Award XP
        self.stdout.write(self.style.HTTP_INFO('Test 1: Award XP'))
        result = award_xp(user, 150, reason='Test XP award')
        self.stdout.write(f'  ✓ Awarded {result["xp_awarded"]} XP')
        self.stdout.write(f'  New Total: {result["new_total"]} XP')
        self.stdout.write(f'  Level: {result["old_level"]} → {result["new_level"]}')
        if result['leveled_up']:
            self.stdout.write(self.style.SUCCESS('  🎉 LEVEL UP!'))
        self.stdout.write('')
        
        # Test 2: Award badge directly
        self.stdout.write(self.style.HTTP_INFO('Test 2: Award Badge'))
        try:
            badge = Badge.objects.get(slug='tournament-debut')
            user_badge = award_badge(user, badge, context={'test': True})
            if user_badge:
                self.stdout.write(f'  ✓ Awarded badge: {badge.icon} {badge.name}')
                self.stdout.write(f'  XP Reward: +{badge.xp_reward} XP')
            else:
                self.stdout.write(self.style.WARNING('  Badge already earned'))
        except Badge.DoesNotExist:
            self.stdout.write(self.style.ERROR('  ✗ Tournament Debut badge not found'))
        self.stdout.write('')
        
        # Test 3: Check all badge criteria
        self.stdout.write(self.style.HTTP_INFO('Test 3: Check Badge Eligibility'))
        badges = Badge.objects.filter(is_active=True)[:5]
        for badge in badges:
            eligible, progress = XPService.check_badge_criteria(user, badge)
            status = '✓ ELIGIBLE' if eligible else '✗ Not eligible'
            self.stdout.write(f'  {badge.icon} {badge.name}: {status}')
            if progress:
                self.stdout.write(f'    {progress}')
        self.stdout.write('')
        
        # Test 4: Profile helper methods
        self.stdout.write(self.style.HTTP_INFO('Test 4: Profile Helper Methods'))
        self.stdout.write(f'  XP to next level: {profile.xp_to_next_level}')
        self.stdout.write(f'  Level progress: {profile.level_progress_percentage:.1f}%')
        self.stdout.write('')
        
        # Test 5: Pin/unpin badges
        self.stdout.write(self.style.HTTP_INFO('Test 5: Pin Badge'))
        user_badges = UserBadge.objects.filter(user=user)[:3]
        for ub in user_badges:
            pinned = profile.pin_badge(ub.badge)
            if pinned:
                self.stdout.write(f'  ✓ Pinned: {ub.badge.icon} {ub.badge.name}')
            else:
                self.stdout.write(f'  ✗ Could not pin: {ub.badge.icon} {ub.badge.name}')
        self.stdout.write(f'  Pinned badges: {len(profile.pinned_badges)}/5')
        self.stdout.write('')
        
        # Final summary
        profile.refresh_from_db()
        self.stdout.write(self.style.SUCCESS('\n=== Final State ==='))
        self.stdout.write(f'Level: {profile.level}')
        self.stdout.write(f'XP: {profile.xp}')
        self.stdout.write(f'Badges: {UserBadge.objects.filter(user=user).count()}')
        self.stdout.write(f'Pinned: {len(profile.pinned_badges)}')
        
        # Show all earned badges
        earned_badges = UserBadge.objects.filter(user=user).select_related('badge')
        if earned_badges:
            self.stdout.write('\nEarned Badges:')
            for ub in earned_badges:
                pinned_mark = '📌' if ub.is_pinned else '  '
                self.stdout.write(f'  {pinned_mark} {ub.badge.icon} {ub.badge.name} ({ub.badge.rarity})')
        
        self.stdout.write(self.style.SUCCESS('\n✓ XP system test complete!\n'))
