#!/usr/bin/env python
"""Find users with multiple game passports for Career Tab testing."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.accounts.models import User
from apps.user_profile.models import GameProfile

# Find users with 2+ passports
users_with_passports = {}
for gp in GameProfile.objects.select_related('user', 'game'):  # FIXED: user not user_profile__user
    username = gp.user.username
    if username not in users_with_passports:
        users_with_passports[username] = []
    users_with_passports[username].append(gp.game.slug)

# Filter users with 2+ games
multi_passport = {u: games for u, games in users_with_passports.items() if len(games) >= 2}

print(f"Found {len(multi_passport)} users with 2+ passports:")
for username, games in sorted(multi_passport.items(), key=lambda x: -len(x[1]))[:10]:
    print(f"  @{username} - {len(games)} games: {', '.join(games)}")

# Check rkrashik specifically
if 'rkrashik' in users_with_passports:
    print(f"\n@rkrashik has {len(users_with_passports['rkrashik'])} passports: {', '.join(users_with_passports['rkrashik'])}")
else:
    print("\n@rkrashik NOT found")
    
# Suggest test user
if multi_passport:
    test_user = list(multi_passport.keys())[0]
    print(f"\nRECOMMENDED TEST USER: @{test_user}")
    print(f"Test URL: http://localhost:8001/@{test_user}/")
