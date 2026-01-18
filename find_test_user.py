"""
Find users with game passports
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.models import GameProfile

User = get_user_model()

print("\n" + "="*80)
print("Users with Game Passports")
print("="*80)

passports = GameProfile.objects.select_related('user', 'game').filter(
    visibility=GameProfile.VISIBILITY_PUBLIC,
    status=GameProfile.STATUS_ACTIVE
).order_by('user__username')[:20]

user_passport_map = {}
for passport in passports:
    username = passport.user.username
    if username not in user_passport_map:
        user_passport_map[username] = []
    user_passport_map[username].append(passport.game.slug)

for username, games in user_passport_map.items():
    print(f"\n✅ {username}")
    for game in games:
        print(f"   - {game}")

if not user_passport_map:
    print("\n⚠️  No users with game passports found!")
