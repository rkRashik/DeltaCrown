"""
Pytest fixtures for user_profile tests.

Handles:
- UserProfile auto-creation for ALL test users (via signals)
- Privacy settings auto-creation
- Test data builders
"""
import pytest
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

User = get_user_model()


@pytest.fixture(scope="function", autouse=True)
def auto_create_user_profiles(db):
    """
    Automatically create UserProfile AND PrivacySettings for ALL users created in tests.
    
    Fix for: AttributeError: 'User' object has no attribute 'profile'
    
    This signal-based approach works for both:
    - Direct User.objects.create_user() calls in tests
    - Fixture-based user creation
    """
    from apps.user_profile.models_main import UserProfile, PrivacySettings
    
    def create_profile_for_user(sender, instance, created, **kwargs):
        """Signal handler to auto-create UserProfile + PrivacySettings"""
        if created:
            # Use get_or_create to avoid conflicts with production signals
            profile, profile_created = UserProfile.objects.get_or_create(
                user=instance,
                defaults={
                    'display_name': instance.username,
                }
            )
            
            # Only create PrivacySettings if it doesn't exist
            if not hasattr(profile, 'privacy_settings'):
                PrivacySettings.objects.get_or_create(user_profile=profile)
    
    # Connect signal for test duration
    post_save.connect(create_profile_for_user, sender=User, dispatch_uid="test_auto_profile")
    
    yield
    
    # Disconnect after test
    post_save.disconnect(create_profile_for_user, sender=User, dispatch_uid="test_auto_profile")


@pytest.fixture
def user(db):
    """
    Create a test user WITH UserProfile (via auto_create_user_profiles signal).
    
    Note: Profile creation is automatic via signal handler above.
    """
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def user_with_privacy(user):
    """
    Create a test user WITH UserProfile AND PrivacySettings.
    
    Fix for: PrivacySettings.DoesNotExist errors in tests
    """
    from apps.user_profile.models_main import PrivacySettings
    from apps.user_profile.utils import get_user_profile_safe
    
    user_profile = get_user_profile_safe(user)
    privacy_settings, _ = PrivacySettings.objects.get_or_create(user_profile=user_profile)
    
    return user


@pytest.fixture
def authenticated_client(client, user):
    """
    Django test client with authenticated user.
    """
    client.force_login(user)
    return client


# ============================================================================
# Game Fixtures (for GameProfile/GamePassport tests)
# ============================================================================

@pytest.fixture(autouse=True)
def ensure_common_games(db):
    """
    Ensure common Game instances exist for ALL user_profile tests.
    
    This fixture runs automatically before each test function that uses the database.
    It creates Game instances that tests expect when calling:
        GamePassportService.create_passport(game='valorant', ...)
    """
    from apps.games.models import Game
    
    common_games = [
        ('valorant', 'VALORANT', 'VAL', 'FPS'),
        ('cs2', 'Counter-Strike 2', 'CS2', 'FPS'),
        ('mlbb', 'Mobile Legends: Bang Bang', 'MLBB', 'MOBA'),
        ('lol', 'League of Legends', 'LOL', 'MOBA'),
        ('dota2', 'Dota 2', 'DOTA', 'MOBA'),
    ]
    
    created_games = []
    for slug, name, short_code, category in common_games:
        game, created = Game.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'display_name': name,
                'short_code': short_code,
                'is_active': True,
                'category': category,
            }
        )
        created_games.append(game)
        if created:
            print(f"✅ Created game: {slug}")
        else:
            print(f"♻️ Reused existing game: {slug}")
    
    print(f"📦 Total games in DB: {Game.objects.count()}")
    print(f"📋 Game slugs: {list(Game.objects.values_list('slug', flat=True))}")
    
    yield
    
    # Don't delete - let pytest handle cleanup


@pytest.fixture
def valorant_game(db):
    """VALORANT Game instance with GamePassportSchema."""
    from apps.games.models import Game
    from apps.user_profile.models_main import GamePassportSchema
    
    game, _ = Game.objects.get_or_create(
        slug='valorant',
        defaults={
            'name': 'VALORANT',
            'is_active': True,
            'display_name': 'VALORANT'
        }
    )
    
    # Create schema for passport validation
    GamePassportSchema.objects.get_or_create(
        game=game,
        defaults={
            'identity_fields': {
                'riot_name': {
                    'type': 'string',
                    'required': True,
                    'max_length': 50,
                    'label': 'Riot ID'
                },
                'tagline': {
                    'type': 'string',
                    'required': True,
                    'pattern': r'^\d{4,5}$',
                    'label': 'Tagline'
                }
            },
            'region_choices': ['NA', 'EU', 'LATAM', 'BR', 'KR', 'AP'],
            'platform_specific': False
        }
    )
    
    return game


@pytest.fixture
def cs2_game(db):
    """Counter-Strike 2 Game instance with GamePassportSchema."""
    from apps.games.models import Game
    from apps.user_profile.models_main import GamePassportSchema
    
    game, _ = Game.objects.get_or_create(
        slug='cs2',
        defaults={
            'name': 'Counter-Strike 2',
            'is_active': True,
            'display_name': 'CS2'
        }
    )
    
    GamePassportSchema.objects.get_or_create(
        game=game,
        defaults={
            'identity_fields': {
                'steam_id64': {
                    'type': 'string',
                    'required': True,
                    'pattern': r'^\d{17}$',
                    'label': 'Steam ID'
                }
            },
            'platform_specific': True
        }
    )
    
    return game


@pytest.fixture
def mlbb_game(db):
    """Mobile Legends: Bang Bang Game instance with GamePassportSchema."""
    from apps.games.models import Game
    from apps.user_profile.models_main import GamePassportSchema
    
    game, _ = Game.objects.get_or_create(
        slug='mlbb',
        defaults={
            'name': 'Mobile Legends: Bang Bang',
            'is_active': True,
            'display_name': 'MLBB'
        }
    )
    
    GamePassportSchema.objects.get_or_create(
        game=game,
        defaults={
            'identity_fields': {
                'player_id': {
                    'type': 'string',
                    'required': True,
                    'pattern': r'^\d{8,12}$',
                    'label': 'Player ID'
                },
                'server_id': {
                    'type': 'string',
                    'required': True,
                    'label': 'Server ID'
                }
            },
            'region_choices': ['SEA', 'NA', 'EU', 'LATAM'],
            'platform_specific': False
        }
    )
    
    return game


@pytest.fixture
def make_game(db):
    """
    Factory fixture for creating Game instances dynamically.
    
    Usage:
        game = make_game('valorant')
        game = make_game('cs2', name='Counter-Strike 2')
    """
    from apps.games.models import Game
    
    def _make_game(slug, name=None, is_active=True):
        game, _ = Game.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name or slug.upper(),
                'is_active': is_active,
                'display_name': name or slug.upper()
            }
        )
        return game
    
    return _make_game


@pytest.fixture
def make_passport(db):
    """
    Factory fixture for creating GameProfile/GamePassport with correct Game instances.
    
    Handles game string → Game instance conversion automatically.
    
    Usage:
        passport = make_passport(
            user_profile=profile,
            game='valorant',  # Can be string or Game instance
            identity={'riot_name': 'Player', 'tagline': '0001'}
        )
    """
    from apps.games.models import Game
    from apps.user_profile.services.game_passport_service import GamePassportService
    
    def _make_passport(user_profile, game, identity, **kwargs):
        # Convert string slug to Game instance
        if isinstance(game, str):
            game_instance = Game.objects.get(slug=game)
        else:
            game_instance = game
        
        service = GamePassportService()
        return service.create_passport(
            user_profile=user_profile,
            game=game_instance,
            identity=identity,
            **kwargs
        )
    
    return _make_passport
