"""
Management command to create achievement type definitions.
This defines all the achievement categories and their earning logic.

Usage:
    python manage.py create_achievement_types
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates achievement type definitions for the DeltaCrown platform'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🏆 DELTACROWN ACHIEVEMENT SYSTEM'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Achievement Categories
        self.stdout.write('\n📊 ACHIEVEMENT CATEGORIES:\n')
        
        categories = {
            '🎯 TOURNAMENT ACHIEVEMENTS': [
                {
                    'name': 'First Blood',
                    'description': 'Won your first tournament',
                    'emoji': '🥇',
                    'rarity': 'common',
                    'trigger': 'tournament_win_count >= 1',
                },
                {
                    'name': 'Triple Crown',
                    'description': 'Won 3 tournaments',
                    'emoji': '👑',
                    'rarity': 'rare',
                    'trigger': 'tournament_win_count >= 3',
                },
                {
                    'name': 'Champion',
                    'description': 'Won 10 tournaments',
                    'emoji': '🏆',
                    'rarity': 'epic',
                    'trigger': 'tournament_win_count >= 10',
                },
                {
                    'name': 'Legend',
                    'description': 'Won 25 tournaments',
                    'emoji': '⭐',
                    'rarity': 'legendary',
                    'trigger': 'tournament_win_count >= 25',
                },
                {
                    'name': 'Perfect Run',
                    'description': 'Won a tournament without losing a match',
                    'emoji': '💯',
                    'rarity': 'epic',
                    'trigger': 'undefeated_tournament_win',
                },
                {
                    'name': 'Comeback King',
                    'description': 'Won a tournament after being in loser\'s bracket',
                    'emoji': '🔄',
                    'rarity': 'rare',
                    'trigger': 'losers_bracket_tournament_win',
                },
            ],
            
            '💰 ECONOMIC ACHIEVEMENTS': [
                {
                    'name': 'First Earnings',
                    'description': 'Earned your first DeltaCoin',
                    'emoji': '💵',
                    'rarity': 'common',
                    'trigger': 'total_earnings >= 1',
                },
                {
                    'name': 'Big Spender',
                    'description': 'Spent 1,000 DeltaCoins',
                    'emoji': '💸',
                    'rarity': 'rare',
                    'trigger': 'total_spent >= 1000',
                },
                {
                    'name': 'Whale',
                    'description': 'Accumulated 10,000 DeltaCoins',
                    'emoji': '🐋',
                    'rarity': 'epic',
                    'trigger': 'current_balance >= 10000',
                },
                {
                    'name': 'Mogul',
                    'description': 'Total lifetime earnings exceeded 50,000 DC',
                    'emoji': '💎',
                    'rarity': 'legendary',
                    'trigger': 'lifetime_earnings >= 50000',
                },
            ],
            
            '👥 SOCIAL ACHIEVEMENTS': [
                {
                    'name': 'Influencer',
                    'description': 'Gained 100 followers',
                    'emoji': '🌟',
                    'rarity': 'rare',
                    'trigger': 'follower_count >= 100',
                },
                {
                    'name': 'Celebrity',
                    'description': 'Gained 500 followers',
                    'emoji': '✨',
                    'rarity': 'epic',
                    'trigger': 'follower_count >= 500',
                },
                {
                    'name': 'Icon',
                    'description': 'Gained 1,000 followers',
                    'emoji': '🎖️',
                    'rarity': 'legendary',
                    'trigger': 'follower_count >= 1000',
                },
                {
                    'name': 'Team Player',
                    'description': 'Joined your first team',
                    'emoji': '🤝',
                    'rarity': 'common',
                    'trigger': 'team_membership_count >= 1',
                },
            ],
            
            '🎮 PARTICIPATION ACHIEVEMENTS': [
                {
                    'name': 'Rookie',
                    'description': 'Participated in your first tournament',
                    'emoji': '🎮',
                    'rarity': 'common',
                    'trigger': 'tournament_participation_count >= 1',
                },
                {
                    'name': 'Veteran',
                    'description': 'Participated in 10 tournaments',
                    'emoji': '🎯',
                    'rarity': 'rare',
                    'trigger': 'tournament_participation_count >= 10',
                },
                {
                    'name': 'Grinder',
                    'description': 'Participated in 50 tournaments',
                    'emoji': '⚡',
                    'rarity': 'epic',
                    'trigger': 'tournament_participation_count >= 50',
                },
                {
                    'name': 'Competitor',
                    'description': 'Participated in 100 tournaments',
                    'emoji': '🔥',
                    'rarity': 'legendary',
                    'trigger': 'tournament_participation_count >= 100',
                },
            ],
            
            '🏅 PLACEMENT ACHIEVEMENTS': [
                {
                    'name': 'Runner Up',
                    'description': 'Placed 2nd in a tournament',
                    'emoji': '🥈',
                    'rarity': 'common',
                    'trigger': 'tournament_placement == 2',
                },
                {
                    'name': 'Bronze Medalist',
                    'description': 'Placed 3rd in a tournament',
                    'emoji': '🥉',
                    'rarity': 'common',
                    'trigger': 'tournament_placement == 3',
                },
                {
                    'name': 'Consistent',
                    'description': 'Placed in top 3 five times',
                    'emoji': '📈',
                    'rarity': 'rare',
                    'trigger': 'top_3_placements >= 5',
                },
            ],
            
            '✅ VERIFICATION ACHIEVEMENTS': [
                {
                    'name': 'Verified',
                    'description': 'Completed KYC verification',
                    'emoji': '✅',
                    'rarity': 'rare',
                    'trigger': 'kyc_verified == True',
                },
                {
                    'name': 'Multi-Game Master',
                    'description': 'Added game profiles for 3+ games',
                    'emoji': '🎲',
                    'rarity': 'rare',
                    'trigger': 'game_profile_count >= 3',
                },
                {
                    'name': 'Social Butterfly',
                    'description': 'Connected 3+ social media accounts',
                    'emoji': '🦋',
                    'rarity': 'common',
                    'trigger': 'social_link_count >= 3',
                },
            ],
            
            '🌟 SPECIAL ACHIEVEMENTS': [
                {
                    'name': 'Early Adopter',
                    'description': 'Joined DeltaCrown in the first month',
                    'emoji': '🚀',
                    'rarity': 'legendary',
                    'trigger': 'registration_date <= 2025-12-01',
                },
                {
                    'name': 'Certified',
                    'description': 'Earned your first tournament certificate',
                    'emoji': '📜',
                    'rarity': 'rare',
                    'trigger': 'certificate_count >= 1',
                },
                {
                    'name': 'Streak Keeper',
                    'description': 'Participated in 5 consecutive weeks',
                    'emoji': '🔗',
                    'rarity': 'epic',
                    'trigger': 'weekly_participation_streak >= 5',
                },
                {
                    'name': 'Underdog',
                    'description': 'Won a tournament as the lowest seed',
                    'emoji': '🐕',
                    'rarity': 'legendary',
                    'trigger': 'lowest_seed_tournament_win',
                },
            ],
        }
        
        # Display all achievement definitions
        total_achievements = 0
        for category, achievements in categories.items():
            self.stdout.write(f'\n{category}')
            self.stdout.write('-' * 60)
            for ach in achievements:
                rarity_icons = {
                    'common': '⚪',
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟡',
                }
                rarity_icon = rarity_icons.get(ach['rarity'], '⚪')
                self.stdout.write(
                    f"  {ach['emoji']} {ach['name']} {rarity_icon}"
                )
                self.stdout.write(
                    f"     {ach['description']}"
                )
                self.stdout.write(
                    self.style.WARNING(f"     Trigger: {ach['trigger']}")
                )
                total_achievements += 1
        
        self.stdout.write(f'\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Total Achievement Types: {total_achievements}'
        ))
        
        # Rarity Distribution
        self.stdout.write('\n\n📊 RARITY DISTRIBUTION:\n')
        rarity_counts = {'common': 0, 'rare': 0, 'epic': 0, 'legendary': 0}
        for category, achievements in categories.items():
            for ach in achievements:
                rarity_counts[ach['rarity']] += 1
        
        for rarity, count in rarity_counts.items():
            percentage = (count / total_achievements) * 100
            self.stdout.write(
                f"  {rarity.upper()}: {count} ({percentage:.1f}%)"
            )
        
        # Implementation Guide
        self.stdout.write('\n\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('\n📘 IMPLEMENTATION GUIDE\n'))
        self.stdout.write('=' * 60)
        
        self.stdout.write('''
These achievement definitions should be implemented in:

1. apps/user_profile/signals.py
   - Create achievement_earned signal
   - Add signal handlers for automatic awarding

2. apps/user_profile/services/achievement_service.py
   - check_and_award_achievements(user) function
   - Individual check functions for each trigger type

3. Connect to relevant models:
   - Tournament model: post_save signal for tournament wins
   - Wallet model: post_save signal for earnings/balance
   - Follow model: post_save signal for follower count
   - TeamMembership: post_save signal for team joins
   - GameProfile: post_save signal for multi-game master
   - SocialLink: post_save signal for social butterfly

4. Manual award via admin:
   - Add "Award Achievement" action in user admin

Example Implementation:
----------------------
from apps.user_profile.models import Achievement

def check_tournament_achievements(user):
    """Check and award tournament-related achievements"""
    win_count = user.tournament_wins.count()
    
    # First Blood
    if win_count >= 1 and not user.achievements.filter(name='First Blood').exists():
        Achievement.objects.create(
            user=user,
            name='First Blood',
            description='Won your first tournament',
            emoji='🥇',
            rarity='common',
            context={'wins': win_count}
        )
    
    # Triple Crown
    if win_count >= 3 and not user.achievements.filter(name='Triple Crown').exists():
        Achievement.objects.create(
            user=user,
            name='Triple Crown',
            description='Won 3 tournaments',
            emoji='👑',
            rarity='rare',
            context={'wins': win_count}
        )
    
    # ... and so on for all achievements

Signal Connection:
-----------------
from django.db.models.signals import post_save
from apps.tournaments.models import TournamentResult

@receiver(post_save, sender=TournamentResult)
def check_achievements_on_tournament_complete(sender, instance, created, **kwargs):
    if instance.placement == 1:  # Winner
        check_tournament_achievements(instance.player)
        check_economic_achievements(instance.player)
        check_participation_achievements(instance.player)
''')
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(
            '\n✅ Achievement system definitions created!'
        ))
        self.stdout.write(self.style.WARNING(
            '\n⚠️  Next Steps:'
        ))
        self.stdout.write('   1. Implement achievement_service.py')
        self.stdout.write('   2. Connect signals to models')
        self.stdout.write('   3. Test achievement awarding')
        self.stdout.write('   4. Deploy and monitor\n')
