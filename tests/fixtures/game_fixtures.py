"""
Test fixtures for Game Passport testing (GP-2E)
Provides minimal game + schema setup for comprehensive testing
"""
import pytest
from apps.games.models import Game
from apps.user_profile.models import GamePassportSchema


@pytest.fixture
def valorant_game(db):
    """Create Valorant game with full passport schema"""
    game = Game.objects.create(
        name='Valorant',
        slug='valorant',
        display_name='VALORANT™',
        short_code='VAL',
        category='FPS',
        game_type='TEAM_VS_TEAM',
        platforms=['PC'],
        is_active=True,
        is_passport_supported=True,
    )
    
    GamePassportSchema.objects.create(
        game=game,
        identity_format="{riot_name}#{tagline}",
        identity_key_format="{riot_name}#{tagline}",
        region_choices=[
            {"value": "americas", "label": "Americas"},
            {"value": "europe", "label": "Europe"},
            {"value": "asia-pacific", "label": "Asia-Pacific"},
            {"value": "korea", "label": "Korea"},
            {"value": "latam", "label": "LATAM"},
            {"value": "br", "label": "Brazil"}
        ],
        region_required=True,
        rank_choices=[
            {"value": "iron", "label": "Iron"},
            {"value": "bronze", "label": "Bronze"},
            {"value": "silver", "label": "Silver"},
            {"value": "gold", "label": "Gold"},
            {"value": "platinum", "label": "Platinum"},
            {"value": "diamond", "label": "Diamond"},
            {"value": "ascendant", "label": "Ascendant"},
            {"value": "immortal", "label": "Immortal"},
            {"value": "radiant", "label": "Radiant"}
        ],
        identity_fields={
            "riot_name": True,
            "tagline": True
        },
    )
    
    return game


@pytest.fixture
def cs2_game(db):
    """Create CS2 game with full passport schema"""
    game = Game.objects.create(
        name='Counter-Strike 2',
        slug='cs2',
        display_name='Counter-Strike 2',
        short_code='CS2',
        category='FPS',
        game_type='TEAM_VS_TEAM',
        platforms=['PC'],
        is_active=True,
        is_passport_supported=True,
    )
    
    GamePassportSchema.objects.create(
        game=game,
        identity_format="{steam_id64}",
        identity_key_format="{steam_id64}",
        region_choices=[],  # CS2 is global, no regions
        region_required=False,
        rank_choices=[
            {"value": "silver", "label": "Silver"},
            {"value": "gold_nova", "label": "Gold Nova"},
            {"value": "master_guardian", "label": "Master Guardian"},
            {"value": "legendary_eagle", "label": "Legendary Eagle"},
            {"value": "supreme", "label": "Supreme Master First Class"},
            {"value": "global_elite", "label": "Global Elite"}
        ],
        identity_fields={
            "steam_id64": True
        },
    )
    
    return game


@pytest.fixture
def mlbb_game(db):
    """Create MLBB game with full passport schema"""
    game = Game.objects.create(
        name='Mobile Legends Bang Bang',
        slug='mlbb',
        display_name='Mobile Legends: Bang Bang',
        short_code='MLBB',
        category='MOBA',
        game_type='TEAM_VS_TEAM',
        platforms=['Mobile'],
        is_active=True,
        is_passport_supported=True,
    )
    
    GamePassportSchema.objects.create(
        game=game,
        identity_format="{mlbb_id}({zone_id})",
        identity_key_format="{mlbb_id}({zone_id})",
        region_choices=[
            {"value": "sea", "label": "Southeast Asia"},
            {"value": "na", "label": "North America"},
            {"value": "eu", "label": "Europe"},
            {"value": "latam", "label": "Latin America"},
            {"value": "sa", "label": "South Asia"}
        ],
        region_required=True,
        rank_choices=[
            {"value": "warrior", "label": "Warrior"},
            {"value": "elite", "label": "Elite"},
            {"value": "master", "label": "Master"},
            {"value": "grandmaster", "label": "Grandmaster"},
            {"value": "epic", "label": "Epic"},
            {"value": "legend", "label": "Legend"},
            {"value": "mythic", "label": "Mythic"},
            {"value": "mythical_glory", "label": "Mythical Glory"}
        ],
        identity_fields={
            "mlbb_id": True,
            "zone_id": True
        },
    )
    
    return game


@pytest.fixture
def all_supported_games(valorant_game, cs2_game, mlbb_game):
    """Fixture providing all 3 test games"""
    return [valorant_game, cs2_game, mlbb_game]


@pytest.fixture
def unsupported_game(db):
    """Create a game WITHOUT passport support for filtering tests"""
    return Game.objects.create(
        name='Unsupported Test Game',
        slug='unsupported_test_game',
        display_name='Unsupported Game',
        short_code='UG',
        category='OTHER',
        game_type='TEAM_VS_TEAM',
        platforms=['PC'],
        is_active=True,
        is_passport_supported=False,  # Not passport-supported
    )
