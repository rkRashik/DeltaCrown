from django.contrib.auth import get_user_model
from apps.user_profile.models import GameProfile

User = get_user_model()
user = User.objects.first()

# Check existing passports
passports = GameProfile.objects.filter(user=user)
print(f"User {user.username} has {passports.count()} passports")
for p in passports:
    print(f"  - {p.game.name}: {p.ign}")
    
# Delete all to test fresh
if passports.exists():
    print(f"\nDeleting {passports.count()} passports...")
    passports.delete()
    print("Done")
