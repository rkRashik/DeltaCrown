"""
Unit tests for SchemaValidationAdapter - Phase 6, Epic 6.4

Tests schema validation and GameRulesEngine integration with mocks.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4 (Schema Validation)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from apps.tournament_ops.adapters.schema_validation_adapter import SchemaValidationAdapter
from apps.tournament_ops.dtos import ResultVerificationResultDTO


class TestValidatePayload:
    """Test validate_payload() method."""
    
    def test_validate_payload_returns_valid_for_matching_schema(self):
        """Validate payload returns valid result for matching schema."""
        # Arrange
        adapter = SchemaValidationAdapter()
        payload = {
            'winner_team_id': 5,
            'loser_team_id': 6,
            'score': '13-7',
            'map': 'Haven',
        }
        
        # Mock get_match_result_schema to return a schema
        with patch.object(adapter, 'get_match_result_schema') as mock_get_schema:
            mock_get_schema.return_value = {
                'type': 'object',
                'required': ['winner_team_id', 'loser_team_id'],
                'properties': {
                    'winner_team_id': {'type': 'integer'},
                    'loser_team_id': {'type': 'integer'},
                    'score': {'type': 'string'},
                    'map': {'type': 'string'},
                }
            }
            
            # Act
            result = adapter.validate_payload('valorant', payload)
        
        # Assert
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.calculated_scores['winner_team_id'] == 5
        assert result.calculated_scores['loser_team_id'] == 6
        assert result.metadata['game_slug'] == 'valorant'
    
    def test_validate_payload_flags_missing_required_fields(self):
        """Validate payload flags missing required fields."""
        # Arrange
        adapter = SchemaValidationAdapter()
        payload = {
            'winner_team_id': 10,
            # Missing loser_team_id
        }
        
        with patch.object(adapter, 'get_match_result_schema') as mock_get_schema:
            mock_get_schema.return_value = {
                'type': 'object',
                'required': ['winner_team_id', 'loser_team_id'],
                'properties': {
                    'winner_team_id': {'type': 'integer'},
                    'loser_team_id': {'type': 'integer'},
                }
            }
            
            # Act
            result = adapter.validate_payload('csgo', payload)
        
        # Assert
        assert result.is_valid is False
        assert any('loser_team_id' in error for error in result.errors)
    
    def test_validate_payload_flags_invalid_field_types(self):
        """Validate payload flags invalid field types."""
        # Arrange
        adapter = SchemaValidationAdapter()
        payload = {
            'winner_team_id': 'not_an_integer',  # Should be integer
            'loser_team_id': 20,
        }
        
        with patch.object(adapter, 'get_match_result_schema') as mock_get_schema:
            mock_get_schema.return_value = {
                'type': 'object',
                'required': ['winner_team_id', 'loser_team_id'],
                'properties': {
                    'winner_team_id': {'type': 'integer'},
                    'loser_team_id': {'type': 'integer'},
                }
            }
            
            # Act
            result = adapter.validate_payload('valorant', payload)
        
        # Assert
        assert result.is_valid is False
        assert any('winner_team_id' in error and 'integer' in error for error in result.errors)
    
    def test_validate_payload_populates_calculated_scores_from_rules_engine(self):
        """Validate payload populates calculated_scores from GameRulesEngine (or basic extraction)."""
        # Arrange
        adapter = SchemaValidationAdapter()
        payload = {
            'winner_team_id': 15,
            'loser_team_id': 16,
            'score': '16-14',
            'map': 'Dust2',
            'duration_seconds': 2400,
        }
        
        with patch.object(adapter, 'get_match_result_schema') as mock_get_schema:
            mock_get_schema.return_value = {
                'type': 'object',
                'required': ['winner_team_id', 'loser_team_id'],
                'properties': {
                    'winner_team_id': {'type': 'integer'},
                    'loser_team_id': {'type': 'integer'},
                    'score': {'type': 'string'},
                    'map': {'type': 'string'},
                    'duration_seconds': {'type': 'integer'},
                }
            }
            
            # Act
            result = adapter.validate_payload('csgo', payload)
        
        # Assert
        assert result.is_valid is True
        assert result.calculated_scores['winner_team_id'] == 15
        assert result.calculated_scores['loser_team_id'] == 16
        assert result.calculated_scores['winner_score'] == 16
        assert result.calculated_scores['loser_score'] == 14
        assert result.calculated_scores['map'] == 'Dust2'
        assert result.calculated_scores['duration_seconds'] == 2400
    
    def test_validate_payload_sets_is_valid_false_when_rules_engine_fails(self):
        """Validate payload sets is_valid=False when business rules fail."""
        # Arrange
        adapter = SchemaValidationAdapter()
        payload = {
            'winner_team_id': 25,
            'loser_team_id': 25,  # Same as winner (business rule violation)
        }
        
        with patch.object(adapter, 'get_match_result_schema') as mock_get_schema:
            mock_get_schema.return_value = {
                'type': 'object',
                'required': ['winner_team_id', 'loser_team_id'],
                'properties': {
                    'winner_team_id': {'type': 'integer'},
                    'loser_team_id': {'type': 'integer'},
                }
            }
            
            # Act
            result = adapter.validate_payload('valorant', payload)
        
        # Assert
        assert result.is_valid is False
        assert any('cannot be the same' in error for error in result.errors)
    
    def test_validate_payload_handles_missing_schema_gracefully(self):
        """Validate payload handles missing schema gracefully."""
        # Arrange
        adapter = SchemaValidationAdapter()
        payload = {
            'winner_team_id': 30,
            'loser_team_id': 31,
        }
        
        # Mock get_match_result_schema to return None (schema missing)
        with patch.object(adapter, 'get_match_result_schema') as mock_get_schema:
            mock_get_schema.return_value = {}
            
            # Act
            result = adapter.validate_payload('unknown_game', payload)
        
        # Assert
        assert result.is_valid is False
        assert any('Missing match result schema' in error for error in result.errors)
        assert result.metadata['game_slug'] == 'unknown_game'
    
    def test_validate_payload_sets_metadata_fields(self):
        """Validate payload sets metadata fields correctly."""
        # Arrange
        adapter = SchemaValidationAdapter()
        payload = {
            'winner_team_id': 35,
            'loser_team_id': 36,
            'score': '13-9',
        }
        
        with patch.object(adapter, 'get_match_result_schema') as mock_get_schema:
            mock_get_schema.return_value = {
                'type': 'object',
                'required': ['winner_team_id', 'loser_team_id'],
                'properties': {
                    'winner_team_id': {'type': 'integer'},
                    'loser_team_id': {'type': 'integer'},
                    'score': {'type': 'string'},
                },
                'version': '2.1',
            }
            
            # Act
            result = adapter.validate_payload('csgo', payload)
        
        # Assert
        assert result.metadata['game_slug'] == 'csgo'
        assert result.metadata['validation_method'] == 'jsonschema_with_rules_engine'
        assert result.metadata['schema_version'] == '2.1'
    
    def test_validate_payload_flags_winner_score_lower_than_loser(self):
        """Validate payload warns when winner score is lower than loser score."""
        # Arrange
        adapter = SchemaValidationAdapter()
        payload = {
            'winner_team_id': 40,
            'loser_team_id': 41,
            'score': '10-12',  # Winner has lower score (suspicious)
        }
        
        with patch.object(adapter, 'get_match_result_schema') as mock_get_schema:
            mock_get_schema.return_value = {
                'type': 'object',
                'required': ['winner_team_id', 'loser_team_id'],
                'properties': {
                    'winner_team_id': {'type': 'integer'},
                    'loser_team_id': {'type': 'integer'},
                    'score': {'type': 'string'},
                }
            }
            
            # Act
            result = adapter.validate_payload('valorant', payload)
        
        # Assert
        assert result.is_valid is True  # Still valid, just warning
        assert any('should be higher than loser' in warning for warning in result.warnings)
    
    def test_validate_payload_handles_enum_validation(self):
        """Validate payload validates enum fields correctly."""
        # Arrange
        adapter = SchemaValidationAdapter()
        payload = {
            'winner_team_id': 45,
            'loser_team_id': 46,
            'map': 'InvalidMap',  # Not in enum
        }
        
        with patch.object(adapter, 'get_match_result_schema') as mock_get_schema:
            mock_get_schema.return_value = {
                'type': 'object',
                'required': ['winner_team_id', 'loser_team_id'],
                'properties': {
                    'winner_team_id': {'type': 'integer'},
                    'loser_team_id': {'type': 'integer'},
                    'map': {'type': 'string', 'enum': ['Bind', 'Haven', 'Split', 'Ascent']},
                }
            }
            
            # Act
            result = adapter.validate_payload('valorant', payload)
        
        # Assert
        assert result.is_valid is False
        assert any('map' in error and 'must be one of' in error for error in result.errors)


class TestGetMatchResultSchema:
    """Test get_match_result_schema() method."""
    
    def test_get_match_result_schema_returns_basic_schema_when_game_not_found(self):
        """Get match result schema returns basic schema when game not found."""
        # Arrange
        adapter = SchemaValidationAdapter()
        
        # Mock Game model to return None
        with patch('apps.tournament_ops.adapters.schema_validation_adapter.Game') as mock_game:
            mock_game.objects.filter.return_value.first.return_value = None
            
            # Act
            schema = adapter.get_match_result_schema('nonexistent_game')
        
        # Assert
        assert schema['required'] == ['winner_team_id', 'loser_team_id']
        assert 'winner_team_id' in schema['properties']
        assert 'loser_team_id' in schema['properties']


class TestArchitectureCompliance:
    """Test architecture compliance."""
    
    def test_schema_validation_adapter_uses_method_level_imports(self):
        """SchemaValidationAdapter must use method-level ORM imports only."""
        import inspect
        from apps.tournament_ops.adapters import schema_validation_adapter
        
        source = inspect.getsource(schema_validation_adapter)
        
        # Should not contain module-level ORM imports
        lines_before_class = source.split('class SchemaValidationAdapter')[0]
        assert 'from apps.games.models import' not in lines_before_class
        assert 'from apps.tournaments.models import' not in lines_before_class
        
        # Method-level imports in get_match_result_schema are OK
        # (They're inside methods, not at module level)
