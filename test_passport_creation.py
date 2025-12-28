"""
Test passport creation to see actual error
"""
from django.contrib.auth import get_user_model
from apps.games.models import Game
from apps.user_profile.services.game_passport_service import GamePassportService

User = get_user_model()

# Get first user
user = User.objects.first()
print(f"Testing with user: {user.username}")

# Get Valorant
game = Game.objects.get(name='Valorant')
print(f"Testing with game: {game.name} (slug: {game.slug})")

# Try to create passport
try:
    passport = GamePassportService.create_passport(
        user=user,
        game=game.slug,
        ign='TestPlayer',
        discriminator='#NA1',
        platform='PC',
        region='AP',
        visibility='PUBLIC',
        metadata={'rank': 'gold_1'},
        request_ip='127.0.0.1'
    )
    print(f"✓ SUCCESS: Created passport with ID {passport.id}")
    print(f"  IGN: {passport.ign}")
    print(f"  Discriminator: {passport.discriminator}")
    print(f"  Platform: {passport.platform}")
    print(f"  Region: {passport.region}")
    
except Exception as e:
    print(f"✗ ERROR: {type(e).__name__}")
    print(f"  Message: {e}")
    import traceback
    print(f"\nFull traceback:")
    traceback.print_exc()
