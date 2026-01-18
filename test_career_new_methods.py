#!/usr/bin/env python
"""Test new Career Tab service methods"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.accounts.models import User
from apps.user_profile.models import UserProfile, GameProfile
from apps.games.models import Game
from apps.user_profile.services.career_tab_service import CareerTabService

print("Testing new Career Tab service methods...")

# Get test user
user = User.objects.get(username='testuser_phase9a7')
# Bypass profile_story column issue
user_profile = UserProfile.objects.only('id', 'user_id').get(user=user)

# Get game
game_profiles = GameProfile.objects.filter(user=user)
if not game_profiles.exists():
    print("ERROR: No GameProfile for testuser_phase9a7")
    exit(1)

game_profile = game_profiles.first()
print(f"GameProfile game field: {game_profile.game}")
try:
    # Try as FK first
    game = game_profile.game
except:
    # Fall back to slug lookup
    game = Game.objects.get(slug=game_profile.game)

print(f"\nUser: @{user.username}")
print(f"Game: {game.display_name} ({game.slug})")
print(f"IGN: {game_profile.in_game_name}")

# Test 1: get_game_category()
print("\n1. Testing get_game_category()...")
category = CareerTabService.get_game_category(game)
print(f"   Category: {category}")

# Test 2: get_identity_meta_line()
print("\n2. Testing get_identity_meta_line()...")
identity_line = CareerTabService.get_identity_meta_line(game_profile, game)
print(f"   Identity: {identity_line}")

# Test 3: get_role_card()
print("\n3. Testing get_role_card()...")
role_card = CareerTabService.get_role_card(game_profile, game)
if role_card:
    print(f"   Title: {role_card.get('title')}")
    print(f"   Icon: {role_card.get('icon_class')}")
else:
    print("   No role card (main_role not set)")

# Test 4: get_stat_tiles()
print("\n4. Testing get_stat_tiles()...")
achievements = CareerTabService.get_achievements(user_profile, game)
team_ranking = CareerTabService.get_team_ranking(user_profile, game)
stat_tiles = CareerTabService.get_stat_tiles(game_profile, game, achievements, team_ranking)
print(f"   Stat Tiles ({len(stat_tiles)}):")
for tile in stat_tiles:
    print(f"      {tile['label']}: {tile['value']} (color: {tile['color_class']})")

# Test 5: format_prize_amount()
print("\n5. Testing format_prize_amount()...")
test_amounts = [0, 500, 1200, 5000, 12000, 150000, 1500000]
for amount in test_amounts:
    formatted = CareerTabService.format_prize_amount(amount)
    print(f"   ${amount} → {formatted}")

print("\n✓ All tests passed!")
