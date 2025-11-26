# apps/user_profile/management/commands/create_starter_badges.py
from django.core.management.base import BaseCommand
from apps.user_profile.models import Badge


class Command(BaseCommand):
    help = 'Create starter achievement badges for the platform'

    def handle(self, *args, **options):
        badges_data = [
            # Tournament Achievements
            {
                'name': 'Tournament Debut',
                'slug': 'tournament-debut',
                'description': 'Participated in your first tournament',
                'icon': '🎮',
                'color': '#3498db',
                'category': 'tournament',
                'rarity': 'common',
                'xp_reward': 50,
                'criteria': {'type': 'tournament_participation', 'threshold': 1},
                'order': 10
            },
            {
                'name': 'First Victory',
                'slug': 'first-victory',
                'description': 'Won your first tournament match',
                'icon': '🏆',
                'color': '#f39c12',
                'category': 'tournament',
                'rarity': 'rare',
                'xp_reward': 100,
                'criteria': {'type': 'match_wins', 'threshold': 1},
                'order': 20
            },
            {
                'name': 'Champion',
                'slug': 'champion',
                'description': 'Won a tournament championship',
                'icon': '👑',
                'color': '#f39c12',
                'category': 'tournament',
                'rarity': 'epic',
                'xp_reward': 500,
                'criteria': {'type': 'tournament_wins', 'threshold': 1},
                'order': 30
            },
            {
                'name': 'Tournament Veteran',
                'slug': 'tournament-veteran',
                'description': 'Participated in 50+ tournaments',
                'icon': '⚔️',
                'color': '#e74c3c',
                'category': 'tournament',
                'rarity': 'epic',
                'xp_reward': 1000,
                'criteria': {'type': 'tournament_participation', 'threshold': 50},
                'order': 40
            },
            {
                'name': 'Triple Crown',
                'slug': 'triple-crown',
                'description': 'Won 3 tournament championships',
                'icon': '🔱',
                'color': '#9b59b6',
                'category': 'tournament',
                'rarity': 'legendary',
                'xp_reward': 2000,
                'criteria': {'type': 'tournament_wins', 'threshold': 3},
                'order': 50
            },
            
            # Community Achievements
            {
                'name': 'Verified Player',
                'slug': 'verified-player',
                'description': 'Completed KYC verification',
                'icon': '✅',
                'color': '#27ae60',
                'category': 'milestone',
                'rarity': 'common',
                'xp_reward': 100,
                'criteria': {'type': 'kyc_verified'},
                'order': 100
            },
            {
                'name': 'Team Captain',
                'slug': 'team-captain',
                'description': 'Created and manage a team',
                'icon': '👨‍✈️',
                'color': '#3498db',
                'category': 'community',
                'rarity': 'rare',
                'xp_reward': 150,
                'criteria': {'type': 'team_created'},
                'order': 110
            },
            {
                'name': 'Content Creator',
                'slug': 'content-creator',
                'description': 'Linked streaming platform and went live',
                'icon': '🎬',
                'color': '#9b59b6',
                'category': 'community',
                'rarity': 'rare',
                'xp_reward': 200,
                'criteria': {'type': 'stream_active'},
                'order': 120
            },
            
            # Economy Achievements
            {
                'name': 'First Withdrawal',
                'slug': 'first-withdrawal',
                'description': 'Completed your first prize withdrawal',
                'icon': '💰',
                'color': '#27ae60',
                'category': 'achievement',
                'rarity': 'rare',
                'xp_reward': 150,
                'criteria': {'type': 'withdrawals', 'threshold': 1},
                'order': 200
            },
            {
                'name': 'Big Earner',
                'slug': 'big-earner',
                'description': 'Earned 10,000+ DeltaCoins lifetime',
                'icon': '💎',
                'color': '#f39c12',
                'category': 'achievement',
                'rarity': 'epic',
                'xp_reward': 500,
                'criteria': {'type': 'lifetime_earnings', 'threshold': 10000},
                'order': 210
            },
            
            # Game-Specific Achievements
            {
                'name': 'PUBG Mobile Master',
                'slug': 'pubgm-master',
                'description': 'Won 10+ PUBG Mobile tournaments',
                'icon': '🎯',
                'color': '#e67e22',
                'category': 'achievement',
                'rarity': 'epic',
                'xp_reward': 750,
                'criteria': {'type': 'tournament_wins', 'threshold': 10, 'game': 'pubg-mobile'},
                'order': 300
            },
            {
                'name': 'Free Fire Legend',
                'slug': 'freefire-legend',
                'description': 'Won 10+ Free Fire tournaments',
                'icon': '🔥',
                'color': '#e74c3c',
                'category': 'achievement',
                'rarity': 'epic',
                'xp_reward': 750,
                'criteria': {'type': 'tournament_wins', 'threshold': 10, 'game': 'free-fire'},
                'order': 310
            },
            {
                'name': 'VALORANT Champion',
                'slug': 'valorant-champion',
                'description': 'Won 10+ VALORANT tournaments',
                'icon': '⚡',
                'color': '#e74c3c',
                'category': 'achievement',
                'rarity': 'epic',
                'xp_reward': 750,
                'criteria': {'type': 'tournament_wins', 'threshold': 10, 'game': 'valorant'},
                'order': 320
            },
            
            # Milestone Achievements
            {
                'name': 'Level 10',
                'slug': 'level-10',
                'description': 'Reached level 10',
                'icon': '🌟',
                'color': '#3498db',
                'category': 'milestone',
                'rarity': 'common',
                'xp_reward': 0,  # No XP for level-based badges
                'criteria': {'type': 'level', 'threshold': 10},
                'order': 400
            },
            {
                'name': 'Level 25',
                'slug': 'level-25',
                'description': 'Reached level 25',
                'icon': '⭐',
                'color': '#f39c12',
                'category': 'milestone',
                'rarity': 'rare',
                'xp_reward': 0,
                'criteria': {'type': 'level', 'threshold': 25},
                'order': 410
            },
            {
                'name': 'Level 50',
                'slug': 'level-50',
                'description': 'Reached level 50',
                'icon': '💫',
                'color': '#9b59b6',
                'category': 'milestone',
                'rarity': 'epic',
                'xp_reward': 0,
                'criteria': {'type': 'level', 'threshold': 50},
                'order': 420
            },
            {
                'name': 'Level 100',
                'slug': 'level-100',
                'description': 'Reached level 100',
                'icon': '🌠',
                'color': '#e74c3c',
                'category': 'milestone',
                'rarity': 'legendary',
                'xp_reward': 0,
                'criteria': {'type': 'level', 'threshold': 100},
                'order': 430
            },
            
            # Special Event Badges
            {
                'name': 'Early Adopter',
                'slug': 'early-adopter',
                'description': 'Joined DeltaCrown in the first month',
                'icon': '🚀',
                'color': '#3498db',
                'category': 'special',
                'rarity': 'legendary',
                'xp_reward': 500,
                'criteria': {'type': 'registration_date', 'before': '2024-12-31'},
                'order': 500,
                'is_hidden': True
            },
            {
                'name': 'Beta Tester',
                'slug': 'beta-tester',
                'description': 'Participated in platform beta testing',
                'icon': '🧪',
                'color': '#9b59b6',
                'category': 'special',
                'rarity': 'legendary',
                'xp_reward': 1000,
                'criteria': {'type': 'manual_award'},
                'order': 510,
                'is_active': False,  # Only awarded manually
                'is_hidden': True
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for badge_data in badges_data:
            badge, created = Badge.objects.update_or_create(
                slug=badge_data['slug'],
                defaults=badge_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created badge: {badge.icon} {badge.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated badge: {badge.icon} {badge.name}')
                )
        
        self.stdout.write('\n')
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Badge creation complete: {created_count} created, {updated_count} updated'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'📊 Total badges: {Badge.objects.count()}'
            )
        )
