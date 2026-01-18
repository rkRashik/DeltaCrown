#!/usr/bin/env python
"""Find users with GameProfile data"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.accounts.models import User
from apps.user_profile.models import GameProfile

# Find all users with GameProfiles
users_with_profiles = User.objects.filter(game_profiles__isnull=False).distinct()

print(f"Found {users_with_profiles.count()} users with GameProfile data:\n")

for user in users_with_profiles[:20]:
    gp_count = GameProfile.objects.filter(user=user).count()
    games = ', '.join([gp.game.slug for gp in GameProfile.objects.filter(user=user).select_related('game')])
    print(f"  @{user.username} - {gp_count} game(s): {games}")

# Suggest best test user
if users_with_profiles.exists():
    # Find user with most games
    best_user = None
    max_games = 0
    for user in users_with_profiles:
        count = GameProfile.objects.filter(user=user).count()
        if count > max_games:
            max_games = count
            best_user = user
    
    print(f"\n{'='*60}")
    print(f"RECOMMENDED TEST USER: @{best_user.username}")
    print(f"Games: {max_games}")
    print(f"Test URL: http://localhost:8001/@{best_user.username}/")
    print(f"Career AJAX: /@{best_user.username}/career-data/?game=<slug>")
