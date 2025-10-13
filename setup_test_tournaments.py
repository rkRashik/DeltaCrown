#!/usr/bin/env python
"""
Setup Test Tournaments for Dynamic Registration Form Testing

This script creates test tournaments for each game to verify the
dynamic registration form system works correctly across all 8 games.

Usage:
    python setup_test_tournaments.py

Features:
    - Creates tournaments for all 8 games (VALORANT, CS2, Dota 2, MLBB, PUBG, Free Fire, eFootball, FC 26)
    - Mix of solo and team tournaments
    - Sets registration open
    - Creates all related models (Schedule, Finance, Capacity, Rules)
    - Prints URLs for testing

Author: DeltaCrown Development Team
Date: October 13, 2025
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

from apps.tournaments.models import Tournament
from apps.tournaments.models.core.tournament_schedule import TournamentSchedule
from apps.tournaments.models.core.tournament_finance import TournamentFinance
from apps.tournaments.models.core.tournament_capacity import TournamentCapacity
from apps.tournaments.models.tournament_rules import TournamentRules
from apps.user_profile.models import UserProfile

User = get_user_model()

# Test tournament configurations
TOURNAMENT_CONFIGS = [
    {
        'name': 'Test VALORANT Championship 2025',
        'game': 'valorant',
        'tournament_type': 'TEAM',
        'format': 'SINGLE_ELIM',
        'platform': 'ONLINE',
        'region': 'Bangladesh',
        'entry_fee': Decimal('500.00'),
        'prize_pool': Decimal('10000.00'),
        'max_teams': 16,
        'short_description': 'Test tournament for VALORANT dynamic registration. Team event with roles.',
    },
    {
        'name': 'Test CS2 Open Tournament',
        'game': 'cs2',
        'tournament_type': 'TEAM',
        'format': 'DOUBLE_ELIM',
        'platform': 'ONLINE',
        'region': 'South Asia',
        'entry_fee': Decimal('0.00'),  # Free entry
        'prize_pool': Decimal('5000.00'),
        'max_teams': 12,
        'short_description': 'Test tournament for CS2 dynamic registration. Free entry team event.',
    },
    {
        'name': 'Test Dota 2 Solo Championship',
        'game': 'dota2',
        'tournament_type': 'SOLO',
        'format': 'ROUND_ROBIN',
        'platform': 'ONLINE',
        'region': 'Bangladesh',
        'entry_fee': Decimal('200.00'),
        'prize_pool': Decimal('3000.00'),
        'max_teams': 20,  # Solo players
        'short_description': 'Test tournament for Dota 2 dynamic registration. Solo event.',
    },
    {
        'name': 'Test MLBB Mobile Cup',
        'game': 'mlbb',
        'tournament_type': 'TEAM',
        'format': 'GROUP_STAGE',
        'platform': 'ONLINE',
        'region': 'Bangladesh',
        'entry_fee': Decimal('300.00'),
        'prize_pool': Decimal('8000.00'),
        'max_teams': 16,
        'short_description': 'Test tournament for Mobile Legends dynamic registration. Team event.',
    },
    {
        'name': 'Test PUBG Battle Royale',
        'game': 'pubg',
        'tournament_type': 'TEAM',
        'format': 'SWISS',
        'platform': 'ONLINE',
        'region': 'South Asia',
        'entry_fee': Decimal('0.00'),  # Free
        'prize_pool': Decimal('15000.00'),
        'max_teams': 20,
        'short_description': 'Test tournament for PUBG dynamic registration. Free team event.',
    },
    {
        'name': 'Test Free Fire Solo League',
        'game': 'freefire',
        'tournament_type': 'SOLO',
        'format': 'SINGLE_ELIM',
        'platform': 'ONLINE',
        'region': 'Bangladesh',
        'entry_fee': Decimal('100.00'),
        'prize_pool': Decimal('2000.00'),
        'max_teams': 32,  # Solo players
        'short_description': 'Test tournament for Free Fire dynamic registration. Solo event.',
    },
    {
        'name': 'Test eFootball Tournament',
        'game': 'efootball',
        'tournament_type': 'SOLO',
        'format': 'HYBRID',
        'platform': 'ONLINE',
        'region': 'Global',
        'entry_fee': Decimal('150.00'),
        'prize_pool': Decimal('5000.00'),
        'max_teams': 24,
        'short_description': 'Test tournament for eFootball dynamic registration. Solo event.',
    },
    {
        'name': 'Test FC 26 Championship',
        'game': 'fc26',
        'tournament_type': 'SOLO',
        'format': 'SINGLE_ELIM',
        'platform': 'ONLINE',
        'region': 'Bangladesh',
        'entry_fee': Decimal('250.00'),
        'prize_pool': Decimal('6000.00'),
        'max_teams': 16,
        'short_description': 'Test tournament for FC 26 dynamic registration. Solo event.',
    },
]


def get_or_create_organizer():
    """Get or create an organizer user for tournaments"""
    try:
        # Try to get existing superuser
        user = User.objects.filter(is_superuser=True).first()
        if user:
            profile = UserProfile.objects.get_or_create(user=user)[0]
            return profile
        
        # Create test organizer if no superuser exists
        user = User.objects.create_user(
            username='test_organizer',
            email='organizer@deltacrown.com',
            password='testpass123'
        )
        profile = UserProfile.objects.create(user=user)
        return profile
    except Exception as e:
        print(f"⚠️  Warning: Could not get/create organizer: {e}")
        return None


def create_tournament(config):
    """Create a tournament with all related models"""
    
    # Get organizer
    organizer = get_or_create_organizer()
    
    # Create base slug
    base_slug = slugify(config['name'])
    slug = base_slug
    
    # Check if tournament already exists
    if Tournament.objects.filter(slug=slug).exists():
        print(f"⚠️  Tournament '{config['name']}' already exists. Skipping...")
        return Tournament.objects.get(slug=slug)
    
    try:
        # Create tournament
        tournament = Tournament.objects.create(
            name=config['name'],
            slug=slug,
            game=config['game'],
            tournament_type=config['tournament_type'],
            format=config['format'],
            platform=config['platform'],
            region=config['region'],
            status='PUBLISHED',  # Make it visible
            short_description=config['short_description'],
            organizer=organizer,
            language='en',
        )
        
        # Create Schedule (Registration open for next 30 days)
        now = timezone.now()
        schedule = TournamentSchedule.objects.create(
            tournament=tournament,
            reg_open_at=now,
            reg_close_at=now + timedelta(days=30),
            start_at=now + timedelta(days=35),
            end_at=now + timedelta(days=37),
            check_in_open_mins=120,  # Check-in opens 2 hours before start
            check_in_close_mins=15,  # Check-in closes 15 mins before start
        )
        
        # Create Finance
        finance = TournamentFinance.objects.create(
            tournament=tournament,
            entry_fee_bdt=config['entry_fee'],
            prize_pool_bdt=config['prize_pool'],
            currency='BDT',
            payment_required=(config['entry_fee'] > 0),
            payment_deadline_hours=48,
            prize_distribution={
                '1st': '50%',
                '2nd': '30%',
                '3rd': '20%',
            }
        )
        
        # Create Capacity
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            max_teams=config['max_teams'],
            min_teams=4,
            current_teams=0,
            allow_waitlist=True,
            waitlist_limit=5,
        )
        
        # Create Rules
        rules = TournamentRules.objects.create(
            tournament=tournament,
            general_rules='<p>Standard tournament rules apply. Be respectful and follow fair play guidelines.</p>',
            eligibility_requirements='<p>Open to all players. Must be 13+ years old.</p>',
            match_rules='<p>Standard match rules. No cheating, hacking, or exploiting.</p>',
            require_discord=True,
            require_game_id=True,
            min_age=13,
        )
        
        print(f"✅ Created: {config['name']} ({config['game']})")
        print(f"   Type: {config['tournament_type']}, Format: {config['format']}")
        print(f"   Entry Fee: ৳{config['entry_fee']}, Prize Pool: ৳{config['prize_pool']}")
        print(f"   Slots: {config['max_teams']}")
        print(f"   Registration URL: http://localhost:8000/tournaments/register-modern/{slug}/")
        print()
        
        return tournament
        
    except Exception as e:
        print(f"❌ Error creating {config['name']}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main script execution"""
    print("=" * 80)
    print("DYNAMIC REGISTRATION FORM - TEST TOURNAMENT SETUP")
    print("=" * 80)
    print()
    
    print(f"🎯 Creating {len(TOURNAMENT_CONFIGS)} test tournaments...")
    print()
    
    created_tournaments = []
    
    for config in TOURNAMENT_CONFIGS:
        tournament = create_tournament(config)
        if tournament:
            created_tournaments.append(tournament)
    
    print("=" * 80)
    print(f"✅ SETUP COMPLETE: {len(created_tournaments)}/{len(TOURNAMENT_CONFIGS)} tournaments created")
    print("=" * 80)
    print()
    
    if created_tournaments:
        print("📋 TEST URLS:")
        print("-" * 80)
        for tournament in created_tournaments:
            print(f"• {tournament.get_game_display():<30} → /tournaments/register-modern/{tournament.slug}/")
        print()
        
        print("🧪 TESTING CHECKLIST:")
        print("-" * 80)
        print("[ ] Test VALORANT team registration with role assignments")
        print("[ ] Test CS2 team registration (free entry)")
        print("[ ] Test Dota 2 solo registration")
        print("[ ] Test MLBB team registration")
        print("[ ] Test PUBG team registration (free entry)")
        print("[ ] Test Free Fire solo registration")
        print("[ ] Test eFootball solo registration")
        print("[ ] Test FC 26 solo registration")
        print()
        print("[ ] Verify dynamic field rendering for each game")
        print("[ ] Verify validation for game-specific fields (Riot ID, Steam ID, etc.)")
        print("[ ] Verify auto-fill from profile data")
        print("[ ] Verify roster management for team events")
        print("[ ] Verify form submission")
        print()
        
        print("🚀 NEXT STEPS:")
        print("-" * 80)
        print("1. Start development server: python manage.py runserver")
        print("2. Visit http://localhost:8000/tournaments/")
        print("3. Click on any test tournament")
        print("4. Click 'Register Now' button")
        print("5. Test the dynamic registration form")
        print()
        
        print("📝 NOTES:")
        print("-" * 80)
        print("• All tournaments have registration open for 30 days")
        print("• Mix of free and paid tournaments")
        print("• Mix of solo and team tournaments")
        print("• Each game has unique field requirements")
        print("• Test with a logged-in user account")
        print()
    else:
        print("❌ No tournaments were created. Check errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
