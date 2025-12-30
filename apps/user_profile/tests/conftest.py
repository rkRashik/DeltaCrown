"""
Pytest fixtures for user_profile tests in apps/user_profile/tests/

This conftest is specifically for tests in the apps/ directory tree.
Separate from tests/user_profile/conftest.py which is for root-level tests.
"""
import pytest
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

User = get_user_model()


@pytest.fixture(scope="function", autouse=True)
def auto_create_user_profiles(db):
    """
    Automatically create UserProfile + PrivacySettings for test users.
    
    Uses signal-based approach to ensure consistency.
    """
    from apps.user_profile.models_main import UserProfile, PrivacySettings
    
    def create_profile_for_user(sender, instance, created, **kwargs):
        if created:
            # Use get_or_create to avoid conflicts with production signals
            profile, profile_created = UserProfile.objects.get_or_create(
                user=instance,
                defaults={'display_name': instance.username}
            )
            
            # Only create PrivacySettings if it doesn't exist
            if not hasattr(profile, 'privacy_settings'):
                PrivacySettings.objects.get_or_create(user_profile=profile)
    
    post_save.connect(create_profile_for_user, sender=User, dispatch_uid="test_auto_profile")
    yield
    post_save.disconnect(create_profile_for_user, sender=User, dispatch_uid="test_auto_profile")


@pytest.fixture
def ensure_common_games(request, db):
    """
    Ensure common Game instances AND GamePassportSchemas exist for tests.
    
    NOTE: NOT autouse anymore - tests must explicitly request this fixture.
    This avoids conflicts with Playwright tests that manage their own setup.
    
    Tests can then call: GamePassportService.create_passport(game='valorant', ...)
    """
    from apps.games.models import Game
    from apps.user_profile.models.game_passport_schema import GamePassportSchema
    
    games_config = [
        {
            'slug': 'valorant',
            'name': 'VALORANT',
            'short_code': 'VAL',
            'category': 'FPS',
            'schema': {
                'identity_fields': {
                    'riot_name': {'label': 'Riot ID', 'required': True, 'max_length': 16},
                    'tagline': {'label': 'Tagline', 'required': True, 'max_length': 5, 'pattern': r'^\d{4,5}$'}
                },
                'identity_format': '{riot_name}#{tagline}',
                'identity_key_format': '{riot_name_lower}#{tagline_lower}',
                'region_choices': [
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'LATAM', 'label': 'Latin America'},
                    {'value': 'BR', 'label': 'Brazil'},
                    {'value': 'KR', 'label': 'Korea'},
                    {'value': 'AP', 'label': 'Asia Pacific'},
                ],
                'region_required': False,
                'platform_specific': False,
            }
        },
        {
            'slug': 'cs2',
            'name': 'Counter-Strike 2',
            'short_code': 'CS2',
            'category': 'FPS',
            'schema': {
                'identity_fields': {
                    'steam_id64': {'label': 'Steam ID64', 'required': True, 'pattern': r'^\d{17}$'}
                },
                'identity_format': '{steam_id64}',
                'identity_key_format': '{steam_id64}',
                'region_required': False,
                'platform_specific': True,
            }
        },
        {
            'slug': 'mlbb',
            'name': 'Mobile Legends: Bang Bang',
            'short_code': 'MLBB',
            'category': 'MOBA',
            'schema': {
                'identity_fields': {
                    'numeric_id': {'label': 'Player ID', 'required': True, 'pattern': r'^\d{8,12}$'},
                    'zone_id': {'label': 'Server ID', 'required': True}
                },
                'identity_format': '{numeric_id}:{zone_id}',
                'identity_key_format': '{numeric_id}:{zone_id}',
                'region_choices': [
                    {'value': 'SEA', 'label': 'Southeast Asia'},
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'LATAM', 'label': 'Latin America'},
                ],
                'region_required': False,
                'platform_specific': False,
            }
        },
        {
            'slug': 'lol',
            'name': 'League of Legends',
            'short_code': 'LOL',
            'category': 'MOBA',
            'schema': {
                'identity_fields': {
                    'riot_name': {'label': 'Summoner Name', 'required': True, 'max_length': 16},
                    'tagline': {'label': 'Tagline', 'required': True, 'max_length': 5}
                },
                'identity_format': '{riot_name}#{tagline}',
                'identity_key_format': '{riot_name_lower}#{tagline_lower}',
                'region_required': False,
                'platform_specific': False,
            }
        },
        {
            'slug': 'dota2',
            'name': 'Dota 2',
            'short_code': 'DOTA',
            'category': 'MOBA',
            'schema': {
                'identity_fields': {
                    'steam_id64': {'label': 'Steam ID64', 'required': True, 'pattern': r'^\d{17}$'}
                },
                'identity_format': '{steam_id64}',
                'identity_key_format': '{steam_id64}',
                'region_required': False,
                'platform_specific': True,
            }
        },
    ]
    
    for config in games_config:
        # Create Game
        game, _ = Game.objects.get_or_create(
            slug=config['slug'],
            defaults={
                'name': config['name'],
                'display_name': config['name'],
                'short_code': config['short_code'],
                'is_active': True,
                'category': config['category'],
            }
        )
        
        # Create GamePassportSchema
        GamePassportSchema.objects.get_or_create(
            game=game,
            defaults=config['schema']
        )


@pytest.fixture
def user(db):
    """Create a test user with UserProfile (via auto_create_user_profiles signal)."""
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def authenticated_client(client, user):
    """Django test client with authenticated user."""
    client.force_login(user)
    return client
