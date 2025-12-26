"""Debug test to verify Game creation in test database."""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_game_creation_debug():
    """Verify Game objects are created by fixture."""
    from apps.games.models import Game
    
    # Check if games exist
    games = Game.objects.all()
    print(f"\nGames in DB: {games.count()}")
    for game in games:
        print(f"  - {game.slug}: {game.name}")
    
    # Try to get valorant
    try:
        val = Game.objects.get(slug='valorant')
        print(f"SUCCESS: Found valorant: {val.name}")
        assert val is not None
    except Game.DoesNotExist:
        print(f"ERROR: valorant not found!")
        print(f"Available slugs: {list(Game.objects.values_list('slug', flat=True))}")
        raise


@pytest.mark.django_db
def test_game_passport_service_simple():
    """Simple test for GamePassportService with debugging."""
    from apps.games.models import Game
    from apps.user_profile.services.game_passport_service import GamePassportService
    
    # Verify Game exists
    games_count = Game.objects.count()
    print(f"\nGames before test: {games_count}")
    print(f"Slugs: {list(Game.objects.values_list('slug', flat=True))}")
    
    assert games_count > 0, "No games in database!"
    
    # Create user
    user = User.objects.create_user(username='testplayer', email='test@test.com')
    print(f"SUCCESS: Created user: {user.username}")
    
    # Try to create passport
    try:
        passport = GamePassportService.create_passport(
            user=user,
            game='valorant',
            in_game_name='TestPlayer#1234',
            actor_user_id=user.id
        )
        print(f"SUCCESS: Created passport: {passport}")
        assert passport is not None
    except Exception as e:
        print(f"ERROR: {e}")
        raise
