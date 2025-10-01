#!/usr/bin/env python
"""
Test script to verify:
1. Team members auto-fill with complete data (including game IDs)
2. 1v1 tournaments route to solo registration (not team)
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from apps.tournaments.models import Tournament
from apps.tournaments.views.helpers import register_url

User = get_user_model()

def test_team_auto_fill():
    """Test that team members include all data fields"""
    print("=" * 70)
    print("Test 1: Team Member Auto-Fill")
    print("=" * 70)
    
    client = Client()
    
    # Create test user
    try:
        user = User.objects.get(username='testcaptain')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testcaptain',
            email='captain@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Captain'
        )
    
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'display_name': 'Test Captain',
            'email': 'captain@test.com',
            'discord_id': 'testcaptain#1234',
            'riot_id': 'TestPlayer#NA1',
            'efootball_id': 'TestFootballer123',
            'phone': '+880 1234567890',
            'country': 'BD'
        }
    )
    
    client.force_login(user)
    
    # Test Valorant team data
    valorant_tournament = Tournament.objects.filter(game__iexact='valorant').first()
    if valorant_tournament:
        response = client.get(f'/tournaments/valorant/{valorant_tournament.slug}/')
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Check if team_members data structure is present
            team_members_in_context = response.context.get('team_members', []) if response.context else []
            checks = {
                'Team members passed to template': len(team_members_in_context) > 0 or 'team_members' in content,
                'Riot ID field present': 'riot_id' in content.lower() or 'player_1_riot_id' in content,
                'Discord ID field present': 'discord_id' in content.lower() or 'captain_discord' in content,
                'Auto-fill script present': 'teamMembers.forEach' in content or 'loadExistingTeamData' in content,
            }
            
            for check, passed in checks.items():
                status = "✓" if passed else "✗"
                print(f"  {status} {check}")
            
            # Check team_members structure if available
            if response.context and 'team_members' in response.context:
                team_members = response.context['team_members']
                if team_members and len(team_members) > 0:
                    first_member = team_members[0]
                    print(f"\n  Team member data structure:")
                    for key in ['name', 'email', 'riot_id', 'discord_id', 'phone', 'country']:
                        has_key = key in first_member
                        value = first_member.get(key, 'N/A') if has_key else 'Missing'
                        status = "✓" if has_key else "✗"
                        print(f"    {status} {key}: {value}")
                else:
                    print("  ⚠ No team members found (user may not have a team)")
        else:
            print(f"  ✗ Failed to load page (status {response.status_code})")
    else:
        print("  ⚠ No Valorant tournament found")
    
    print()

def test_1v1_routing():
    """Test that 1v1 tournaments route to solo registration"""
    print("=" * 70)
    print("Test 2: 1v1 Tournament Routing")
    print("=" * 70)
    
    # Test various 1v1 indicators
    test_cases = [
        {
            'name': '1v1 in tournament mode',
            'attrs': {'game': 'csgo', 'mode': '1v1', 'name': 'CS2 1v1 Tournament'},
            'expected': 'solo'
        },
        {
            'name': '1v1 in tournament name',
            'attrs': {'game': 'valorant', 'mode': '', 'name': 'Valorant 1v1 Championship'},
            'expected': 'solo'
        },
        {
            'name': 'solo keyword',
            'attrs': {'game': 'fc26', 'mode': 'solo', 'name': 'FC26 Solo Tournament'},
            'expected': 'solo'
        },
        {
            'name': 'team_size = 1',
            'attrs': {'game': 'mlbb', 'mode': '', 'name': 'MLBB Tournament', 'team_size': 1},
            'expected': 'solo'
        },
        {
            'name': '5v5 team tournament',
            'attrs': {'game': 'valorant', 'mode': '5v5', 'name': 'Valorant 5v5'},
            'expected': 'team'
        },
        {
            'name': '2v2 duo tournament',
            'attrs': {'game': 'efootball', 'mode': '2v2', 'name': 'eFootball Duo', 'team_size': 2},
            'expected': 'team'
        },
    ]
    
    for test in test_cases:
        # Create mock tournament object
        class MockTournament:
            def __init__(self, **kwargs):
                self.slug = 'test-tournament'
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        t = MockTournament(**test['attrs'])
        url = register_url(t)
        
        if test['expected'] == 'solo':
            is_solo = 'type=solo' in url or 'solo' in url.lower()
            is_team = 'valorant_register' in url or 'efootball_register' in url or 'type=team' in url
            passed = is_solo and not is_team
        else:  # team
            is_team = 'valorant_register' in url or 'efootball_register' in url or 'type=team' in url
            is_solo = 'type=solo' in url
            passed = is_team and not is_solo
        
        status = "✓" if passed else "✗"
        print(f"  {status} {test['name']}")
        print(f"      Attrs: {test['attrs']}")
        print(f"      Expected: {test['expected']}, Got URL: {url}")
        if not passed:
            print(f"      ❌ FAILED!")
        print()
    
    print()

def test_real_tournaments():
    """Test routing with real tournaments in database"""
    print("=" * 70)
    print("Test 3: Real Tournament Routing")
    print("=" * 70)
    
    tournaments = Tournament.objects.all()[:10]
    
    for t in tournaments:
        url = register_url(t)
        game = getattr(t, 'game', 'unknown')
        mode = getattr(t, 'mode', '')
        name = getattr(t, 'name', 'Untitled')
        
        # Detect type from URL
        if 'valorant_register' in url:
            detected_type = 'Valorant Team'
        elif 'efootball_register' in url:
            detected_type = 'eFootball Duo'
        elif 'type=solo' in url:
            detected_type = 'Solo'
        elif 'type=team' in url:
            detected_type = 'Team'
        else:
            detected_type = 'Unknown'
        
        print(f"  {name[:40]}")
        print(f"    Game: {game}, Mode: {mode}")
        print(f"    Detected: {detected_type}")
        print(f"    URL: {url}")
        print()

if __name__ == '__main__':
    test_team_auto_fill()
    test_1v1_routing()
    test_real_tournaments()
    
    print("=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)
