"""
Tests for GameConfigService

Module: 2.2 - Game Configurations & Custom Fields (Backend Only)
Source Documents:
- Documents/ExecutionPlan/Core/BACKEND_ONLY_BACKLOG.md (Module 2.2)
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (Testing Standards)

Description:
Comprehensive tests for game configuration service layer.
Tests cover get, create/update, validation, and tournament enforcement.

Coverage Target: ≥80% for GameConfigService
Test Count Target: 25+ tests
"""

import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.tournaments.models.tournament import Game
from apps.tournaments.services.game_config_service import GameConfigService

User = get_user_model()


@pytest.fixture
def staff_user(db):
    """Create a staff user for permission tests."""
    user = User.objects.create_user(
        username='staffuser',
        email='staff@example.com',
        password='testpass123'
    )
    user.is_staff = True
    user.is_superuser = True  # Bypass group-based is_staff signal
    user.save()
    return user


@pytest.fixture
def regular_user(db):
    """Create a regular user for permission tests."""
    return User.objects.create_user(
        username='regularuser',
        email='user@example.com',
        password='testpass123',
        is_staff=False
    )


@pytest.fixture
def game(db):
    """Create a sample game for testing."""
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        default_team_size=5,
        profile_id_field='riot_id',
        default_result_type='score',
        is_active=True,
        game_config={}  # Empty config
    )


@pytest.fixture
def game_with_config(db):
    """Create a game with existing config."""
    return Game.objects.create(
        name='CS2',
        slug='cs2',
        default_team_size=5,
        profile_id_field='steam_id',
        default_result_type='score',
        is_active=True,
        game_config={
            "schema_version": "1.0",
            "allowed_formats": ["single_elimination", "double_elimination"],
            "team_size_range": [5, 5],
            "custom_field_schemas": [],
            "match_settings": {"default_best_of": 3, "available_maps": ["Mirage", "Dust2"]}
        }
    )


# ============================================================================
# Test: get_config
# ============================================================================

@pytest.mark.django_db
class TestGetConfig:
    """Test GameConfigService.get_config()"""
    
    def test_get_config_returns_existing_config(self, game_with_config):
        """Should return existing game_config from database."""
        config = GameConfigService.get_config(game_with_config.id)
        
        assert config['schema_version'] == '1.0'
        assert config['allowed_formats'] == ['single_elimination', 'double_elimination']
        assert config['team_size_range'] == [5, 5]
        assert config['match_settings']['default_best_of'] == 3
    
    def test_get_config_returns_default_for_empty_config(self, game):
        """Should return DEFAULT_SCHEMA if game_config is empty."""
        config = GameConfigService.get_config(game.id)
        
        assert config['schema_version'] == '1.0'
        assert 'single_elimination' in config['allowed_formats']
        assert config['team_size_range'] == [1, 5]
        assert config['match_settings']['default_best_of'] == 1
    
    def test_get_config_raises_for_nonexistent_game(self):
        """Should raise Game.DoesNotExist for invalid game_id."""
        with pytest.raises(Game.DoesNotExist):
            GameConfigService.get_config(game_id=99999)
    
    def test_get_config_raises_for_inactive_game(self, game):
        """Should raise Game.DoesNotExist for inactive game."""
        game.is_active = False
        game.save()
        
        with pytest.raises(Game.DoesNotExist):
            GameConfigService.get_config(game.id)


# ============================================================================
# Test: create_or_update_config
# ============================================================================

@pytest.mark.django_db
class TestCreateOrUpdateConfig:
    """Test GameConfigService.create_or_update_config()"""
    
    def test_create_config_for_empty_game(self, game, staff_user):
        """Should create new config for game with empty config."""
        config_data = {
            "allowed_formats": ["single_elimination"],
            "team_size_range": [5, 5]
        }
        
        result = GameConfigService.create_or_update_config(
            game_id=game.id,
            config_data=config_data,
            user=staff_user
        )
        
        assert result['allowed_formats'] == ['single_elimination']
        assert result['team_size_range'] == [5, 5]
        assert result['schema_version'] == '1.0'  # From default
    
    def test_update_config_deep_merges_existing(self, game_with_config, staff_user):
        """Should deep merge updates into existing config."""
        config_data = {
            "match_settings": {"default_best_of": 5}
        }
        
        result = GameConfigService.create_or_update_config(
            game_id=game_with_config.id,
            config_data=config_data,
            user=staff_user
        )
        
        # match_settings.default_best_of updated
        assert result['match_settings']['default_best_of'] == 5
        # match_settings.available_maps preserved
        assert result['match_settings']['available_maps'] == ['Mirage', 'Dust2']
        # Other top-level keys preserved
        assert result['allowed_formats'] == ['single_elimination', 'double_elimination']
    
    def test_update_config_replaces_top_level_lists(self, game_with_config, staff_user):
        """Should replace top-level list values, not merge."""
        config_data = {
            "allowed_formats": ["round_robin"]
        }
        
        result = GameConfigService.create_or_update_config(
            game_id=game_with_config.id,
            config_data=config_data,
            user=staff_user
        )
        
        # Formats replaced, not merged
        assert result['allowed_formats'] == ['round_robin']
    
    def test_update_config_requires_staff_permission(self, game, regular_user):
        """Should raise PermissionError for non-staff user."""
        config_data = {"allowed_formats": ["single_elimination"]}
        
        with pytest.raises(PermissionError) as exc_info:
            GameConfigService.create_or_update_config(
                game_id=game.id,
                config_data=config_data,
                user=regular_user
            )
        
        assert 'Only staff' in str(exc_info.value)
    
    def test_update_config_validates_before_saving(self, game, staff_user):
        """Should validate config and raise ValidationError if invalid."""
        config_data = {
            "allowed_formats": ["invalid_format"]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            GameConfigService.create_or_update_config(
                game_id=game.id,
                config_data=config_data,
                user=staff_user
            )
        
        assert 'Invalid allowed_formats' in str(exc_info.value)
    
    def test_update_config_persists_to_database(self, game, staff_user):
        """Should save updated config to database."""
        config_data = {"team_size_range": [3, 7]}
        
        GameConfigService.create_or_update_config(
            game_id=game.id,
            config_data=config_data,
            user=staff_user
        )
        
        # Refresh from DB
        game.refresh_from_db()
        assert game.game_config['team_size_range'] == [3, 7]


# ============================================================================
# Test: _validate_config
# ============================================================================

@pytest.mark.django_db
class TestValidateConfig:
    """Test GameConfigService._validate_config()"""
    
    def test_validate_config_accepts_valid_config(self):
        """Should not raise for valid config."""
        config = {
            "schema_version": "1.0",
            "allowed_formats": ["single_elimination"],
            "team_size_range": [1, 5]
        }
        
        # Should not raise
        GameConfigService._validate_config(config)
    
    def test_validate_config_requires_schema_version(self):
        """Should raise if schema_version missing."""
        config = {
            "allowed_formats": ["single_elimination"],
            "team_size_range": [1, 5]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            GameConfigService._validate_config(config)
        
        assert 'schema_version' in str(exc_info.value)
    
    def test_validate_config_requires_allowed_formats(self):
        """Should raise if allowed_formats missing."""
        config = {
            "schema_version": "1.0",
            "team_size_range": [1, 5]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            GameConfigService._validate_config(config)
        
        assert 'allowed_formats' in str(exc_info.value)
    
    def test_validate_config_requires_team_size_range(self):
        """Should raise if team_size_range missing."""
        config = {
            "schema_version": "1.0",
            "allowed_formats": ["single_elimination"]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            GameConfigService._validate_config(config)
        
        assert 'team_size_range' in str(exc_info.value)
    
    def test_validate_config_rejects_empty_allowed_formats(self):
        """Should raise if allowed_formats is empty list."""
        config = {
            "schema_version": "1.0",
            "allowed_formats": [],
            "team_size_range": [1, 5]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            GameConfigService._validate_config(config)
        
        assert 'at least one format' in str(exc_info.value)
    
    def test_validate_config_rejects_invalid_formats(self):
        """Should raise if allowed_formats contains invalid format."""
        config = {
            "schema_version": "1.0",
            "allowed_formats": ["invalid_format", "single_elimination"],
            "team_size_range": [1, 5]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            GameConfigService._validate_config(config)
        
        assert 'invalid_format' in str(exc_info.value).lower()
    
    def test_validate_config_rejects_invalid_team_size_range(self):
        """Should raise if team_size_range not [min, max] with min <= max."""
        # Test: wrong length
        config = {
            "schema_version": "1.0",
            "allowed_formats": ["single_elimination"],
            "team_size_range": [1]
        }
        with pytest.raises(ValidationError):
            GameConfigService._validate_config(config)
        
        # Test: min > max
        config['team_size_range'] = [5, 3]
        with pytest.raises(ValidationError):
            GameConfigService._validate_config(config)
        
        # Test: negative values
        config['team_size_range'] = [-1, 5]
        with pytest.raises(ValidationError):
            GameConfigService._validate_config(config)
    
    def test_validate_config_validates_custom_field_schemas(self):
        """Should validate custom_field_schemas structure."""
        # Valid custom field schema
        config = {
            "schema_version": "1.0",
            "allowed_formats": ["single_elimination"],
            "team_size_range": [1, 5],
            "custom_field_schemas": [
                {"field_key": "discord_server", "field_type": "url"}
            ]
        }
        GameConfigService._validate_config(config)  # Should not raise
        
        # Invalid: missing field_key
        config['custom_field_schemas'] = [{"field_type": "url"}]
        with pytest.raises(ValidationError):
            GameConfigService._validate_config(config)
        
        # Invalid: invalid field_type
        config['custom_field_schemas'] = [
            {"field_key": "test", "field_type": "invalid_type"}
        ]
        with pytest.raises(ValidationError):
            GameConfigService._validate_config(config)


# ============================================================================
# Test: validate_tournament_against_config
# ============================================================================

@pytest.mark.django_db
class TestValidateTournamentAgainstConfig:
    """Test GameConfigService.validate_tournament_against_config()"""
    
    def test_validate_accepts_valid_format(self, game_with_config):
        """Should not raise for format in allowed_formats."""
        tournament_data = {"format": "single_elimination"}
        
        # Should not raise
        GameConfigService.validate_tournament_against_config(
            game_id=game_with_config.id,
            tournament_data=tournament_data
        )
    
    def test_validate_rejects_invalid_format(self, game_with_config):
        """Should raise ValidationError for format not in allowed_formats."""
        tournament_data = {"format": "round_robin"}  # Not in game's allowed_formats
        
        with pytest.raises(ValidationError) as exc_info:
            GameConfigService.validate_tournament_against_config(
                game_id=game_with_config.id,
                tournament_data=tournament_data
            )
        
        assert 'not allowed' in str(exc_info.value).lower()
    
    def test_validate_accepts_missing_format(self, game_with_config):
        """Should not raise if format not provided (will use default)."""
        tournament_data = {}
        
        # Should not raise
        GameConfigService.validate_tournament_against_config(
            game_id=game_with_config.id,
            tournament_data=tournament_data
        )


# ============================================================================
# Test: get_config_schema
# ============================================================================

@pytest.mark.django_db
class TestGetConfigSchema:
    """Test GameConfigService.get_config_schema()"""
    
    def test_get_config_schema_returns_json_schema(self, game):
        """Should return JSON Schema (draft-07) structure."""
        schema = GameConfigService.get_config_schema(game.id)
        
        assert schema['$schema'] == 'http://json-schema.org/draft-07/schema#'
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'required' in schema
    
    def test_get_config_schema_includes_game_name(self, game):
        """Should include game name in schema title."""
        schema = GameConfigService.get_config_schema(game.id)
        
        assert game.name in schema['title']
    
    def test_get_config_schema_defines_all_properties(self, game):
        """Should define all expected properties in schema."""
        schema = GameConfigService.get_config_schema(game.id)
        
        properties = schema['properties']
        assert 'schema_version' in properties
        assert 'allowed_formats' in properties
        assert 'team_size_range' in properties
        assert 'custom_field_schemas' in properties
        assert 'match_settings' in properties
    
    def test_get_config_schema_marks_required_fields(self, game):
        """Should mark required fields in schema."""
        schema = GameConfigService.get_config_schema(game.id)
        
        required = schema['required']
        assert 'schema_version' in required
        assert 'allowed_formats' in required
        assert 'team_size_range' in required


# ============================================================================
# Test: _deep_merge
# ============================================================================

class TestDeepMerge:
    """Test GameConfigService._deep_merge()"""
    
    def test_deep_merge_merges_nested_dicts(self):
        """Should recursively merge nested dictionaries."""
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        updates = {"a": {"b": 10}, "e": 4}
        
        result = GameConfigService._deep_merge(base, updates)
        
        assert result['a']['b'] == 10  # Updated
        assert result['a']['c'] == 2   # Preserved
        assert result['d'] == 3        # Preserved
        assert result['e'] == 4        # Added
    
    def test_deep_merge_replaces_non_dict_values(self):
        """Should replace non-dict values, not merge."""
        base = {"a": [1, 2, 3], "b": "hello"}
        updates = {"a": [4, 5], "b": "world"}
        
        result = GameConfigService._deep_merge(base, updates)
        
        assert result['a'] == [4, 5]
        assert result['b'] == "world"
    
    def test_deep_merge_does_not_mutate_base(self):
        """Should not modify base dict (returns copy)."""
        base = {"a": 1, "b": 2}
        updates = {"a": 10, "c": 3}
        
        result = GameConfigService._deep_merge(base, updates)
        
        assert base['a'] == 1  # Unchanged
        assert 'c' not in base
        assert result['a'] == 10
