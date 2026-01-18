#!/usr/bin/env python
"""Test Career Tab AJAX API for game switching"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.accounts.models import User
from apps.user_profile.models import UserProfile
from django.test import RequestFactory
from apps.user_profile.views.public_profile_views import career_tab_data_api

# Get test user
print("Testing Career Tab AJAX API...")

# Find a user with multiple real games
from apps.games.models import Game
from apps.user_profile.models import GameProfile

# Check what games exist
all_games = list(Game.objects.values_list('slug', flat=True)[:15])
print(f"Available games in DB: {all_games}")

valorant = Game.objects.filter(slug='valorant').first()
ea_fc = Game.objects.filter(slug='ea-fc').first()

if not valorant:
    print("WARNING: Valorant not found, using first available game")
    valorant = Game.objects.first()

if not valorant:
    print("ERROR: No games found in database")
    exit(1)

# Try to find a user with game profiles for these games
user = None
for gp in GameProfile.objects.select_related('user', 'game')[:20]:
    # Find user with at least 1 game profile
    user_games = GameProfile.objects.filter(user=gp.user).count()
    if user_games >= 1:
        user = gp.user
        break

if not user:
    print("ERROR: No users with game profiles found")
    exit(1)

username = user.username

print(f"\nUser: @{username}")

# Get linked games
game_profiles = GameProfile.objects.filter(user=user)
print(f"Linked games: {game_profiles.count()}")

if game_profiles.count() == 0:
    print("ERROR: No GameProfile for test user")
    exit(1)

# Test API for each game
factory = RequestFactory()

for gp in game_profiles:
    game_slug = gp.game
    print(f"\n{'='*60}")
    print(f"Testing game: {game_slug}")
    print(f"{'='*60}")
    
    # Create mock request
    request = factory.get(f'/@{username}/career-data/?game={game_slug}')
    request.user = user
    
    # Call API
    response = career_tab_data_api(request, username)
    
    if response.status_code != 200:
        print(f"ERROR: API returned status {response.status_code}")
        print(response.content.decode())
        continue
    
    # Parse JSON
    data = json.loads(response.content.decode())
    
    # Validate structure
    print("\n1. GAME structure:")
    if 'game' in data:
        print(f"   ✓ game.slug: {data['game'].get('slug')}")
        print(f"   ✓ game.name: {data['game'].get('name')}")
        print(f"   ✓ game.logo_url: {data['game'].get('logo_url')}")
        print(f"   ✓ game.banner_url: {data['game'].get('banner_url')}")
    else:
        print("   ✗ MISSING 'game' key")
    
    print("\n2. PASSPORT structure:")
    if 'passport' in data:
        print(f"   ✓ in_game_name: {data['passport'].get('in_game_name')}")
        print(f"   ✓ rank_name: {data['passport'].get('rank_name')}")
    else:
        print("   ✗ MISSING 'passport' key")
    
    print("\n3. IDENTITY_META_LINE:")
    print(f"   {data.get('identity_meta_line', 'MISSING')}")
    
    print("\n4. STANDING structure:")
    if 'standing' in data:
        print(f"   ✓ label: {data['standing'].get('label')}")
        print(f"   ✓ value: {data['standing'].get('value')}")
        print(f"   ✓ icon_url: {data['standing'].get('icon_url')}")
        print(f"   ✓ secondary: {data['standing'].get('secondary')}")
    else:
        print("   ✗ MISSING 'standing' key")
    
    print("\n5. STAT_TILES:")
    if 'stat_tiles' in data:
        tiles = data['stat_tiles']
        print(f"   Count: {len(tiles)}")
        for tile in tiles:
            print(f"   - {tile.get('label')}: {tile.get('value')} (color: {tile.get('color_class')})")
    else:
        print("   ✗ MISSING 'stat_tiles' key")
    
    print("\n6. ROLE_CARD:")
    if 'role_card' in data:
        role = data['role_card']
        if role:
            print(f"   ✓ title: {role.get('title')}")
            print(f"   ✓ icon_class: {role.get('icon_class')}")
        else:
            print("   (null - no role set)")
    else:
        print("   ✗ MISSING 'role_card' key")
    
    print("\n7. AFFILIATION_HISTORY:")
    if 'affiliation_history' in data:
        print(f"   Count: {len(data['affiliation_history'])}")
    else:
        print("   ✗ MISSING 'affiliation_history' key")
    
    print("\n8. MATCH_HISTORY:")
    if 'match_history' in data:
        print(f"   Count: {len(data['match_history'])}")
    else:
        print("   ✗ MISSING 'match_history' key")

print("\n" + "="*60)
print("✓ API Test Complete")
print("="*60)
