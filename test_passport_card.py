#!/usr/bin/env python
"""Test Career Tab with passport_card output"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.accounts.models import User
from apps.user_profile.models import GameProfile
from apps.user_profile.services.career_tab_service import CareerTabService

# Find any user with passport
gp = GameProfile.objects.select_related('user', 'game').first()
if not gp:
    print("ERROR: No GameProfile records found")
    exit(1)

test_user = gp.user
game = gp.game
# Skip UserProfile due to DB schema issue
# user_profile = test_user.profile

print(f"Testing CareerTabService with:")
print(f"  User: @{test_user.username}")
print(f"  Game: {game.slug}")
print(f"\n{'='*60}\n")

# Get passport card view
passport_card = CareerTabService.get_passport_card_view(gp, game)

print("PASSPORT CARD OUTPUT:")
print(json.dumps(passport_card, indent=2, default=str))

# Test identity mapping with metadata
print(f"\n{'='*60}")
print("METADATA ANALYSIS:")
print(f"  passport.metadata = {gp.metadata}")
print(f"  identity_key = {getattr(gp, 'identity_key', 'N/A')}")
print(f"  in_game_name = {gp.in_game_name}")

# Show what would happen with PUBG metadata
print(f"\n{'='*60}")
print("PUBG EXAMPLE (if metadata had character_id):")
fake_metadata = {'character_id': '1234567890', 'server': 'ASIA'}
print(f"  metadata = {fake_metadata}")
print(f"  Would show: Character ID = 1234567890")

# Show what would happen with Free Fire metadata
print(f"\nFREE FIRE EXAMPLE (if metadata had player_id):")
fake_metadata = {'player_id': '987654321', 'server': 'Global'}
print(f"  metadata = {fake_metadata}")
print(f"  Would show: Player ID = 987654321")
