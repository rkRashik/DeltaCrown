#!/usr/bin/env python
"""Find users with GameProfile data"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.accounts.models import User
from apps.user_profile.models import GameProfile

print("Finding users with GameProfile data...")
users_with_gp = User.objects.filter(
    game_profiles__isnull=False
).distinct()

print(f"\nFound {users_with_gp.count()} users with GameProfile:\n")

for user in users_with_gp[:10]:
    gp_count = GameProfile.objects.filter(user=user).count()
    print(f"  @{user.username} - {gp_count} game(s)")
