"""
Schema Validation Adapter - Phase 6, Epic 6.4

Adapter for game-specific schema validation.

Architecture:
- Integrates with Phase 2 GameRulesEngine for match result validation
- Returns ResultVerificationResultDTO
- Method-level ORM imports only (no module-level imports)
- Handles schema validation, type checking, score calculation

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4 (Result Verification & Finalization)
"""

import logging
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from apps.tournament_ops.dtos import ResultVerificationResultDTO

logger = logging.getLogger(__name__)


@runtime_checkable
class SchemaValidationAdapterProtocol(Protocol):
    """
    Protocol for game-specific schema validation.
    
    Integrates with Phase 2 GameRulesEngine for match result validation.
    """
    
    def get_match_result_schema(self, game_slug: str) -> Dict[str, Any]:
        """
        Fetch JSON Schema for game's match result.
        
        Args:
            game_slug: Game identifier (e.g., 'valorant', 'csgo')
            
        Returns:
            JSON Schema dict
            
        Example for Valorant:
            {
              "type": "object",
              "required": ["winner_team_id", "loser_team_id", "score", "map"],
              "properties": {
                "winner_team_id": {"type": "integer"},
                "loser_team_id": {"type": "integer"},
                "score": {"type": "string", "pattern": "^\\d{1,2}-\\d{1,2}$"},
                "map": {"type": "string", "enum": ["Bind", "Haven", "Split", ...]},
              }
            }
        """
        ...
    
    def validate_payload(
        self,
        game_slug: str,
        payload: Dict[str, Any],
    ) -> ResultVerificationResultDTO:
        """
        Validate payload against schema.
        
        Args:
            game_slug: Game identifier
            payload: Match result data to validate
            
        Returns:
            ResultVerificationResultDTO with is_valid, errors, warnings
        """
        ...


class SchemaValidationAdapter:
    """
    Concrete implementation of SchemaValidationAdapterProtocol.
    
    Phase 6.4 (Epic 6.4): Full integration with GameRulesEngine
    
    Performs:
    - Schema validation against GameMatchResultSchema
    - Type checking for all fields
    - Score calculation via GameRulesEngine
    - Business rule validation (winner != loser, valid map, etc.)
    
    Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4
    """
    
    def get_match_result_schema(self, game_slug: str) -> Dict[str, Any]:
        """
        Fetch match result schema for game from database.
        
        Integrates with Phase 2 GameMatchResultSchema model.
        Returns cached schema or fetches from DB.
        
        Args:
            game_slug: Game identifier
            
        Returns:
            JSON Schema dict
            
        Raises:
            No exception - returns basic schema if game not found
        """
        # Method-level import (no module-level ORM imports in tournament_ops)
        try:
            from apps.games.models import Game, GameMatchResultSchema
            
            # Fetch game
            game = Game.objects.filter(slug=game_slug).first()
            if not game:
                logger.warning(f"Game not found for slug: {game_slug}, using basic schema")
                return self._get_basic_schema()
            
            # Fetch schema
            schema_obj = GameMatchResultSchema.objects.filter(game=game).first()
            if not schema_obj or not schema_obj.schema:
                logger.warning(f"Schema not found for game: {game_slug}, using basic schema")
                return self._get_basic_schema()
            
            return schema_obj.schema
        except Exception as e:
            logger.error(f"Error fetching schema for game {game_slug}: {e}")
            return self._get_basic_schema()
    
    def validate_payload(
        self,
        game_slug: str,
        payload: Dict[str, Any],
    ) -> ResultVerificationResultDTO:
        """
        Validate payload against schema using GameRulesEngine.
        
        Full validation pipeline:
        1. Fetch schema for game
        2. Validate required fields
        3. Validate field types
        4. Validate business rules (winner != loser, valid enums)
        5. Calculate scores via GameRulesEngine (if available)
        6. Build ResultVerificationResultDTO with:
           - is_valid (True/False)
           - errors (list of validation errors)
           - warnings (list of soft issues)
           - calculated_scores (winner/loser team IDs, scores)
           - metadata (game_slug, validation method)
        
        Args:
            game_slug: Game identifier
            payload: Match result data to validate
            
        Returns:
            ResultVerificationResultDTO
            
        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4, validate_payload
        """
        errors = []
        warnings = []
        
        # Fetch schema
        schema = self.get_match_result_schema(game_slug)
        
        # If schema missing, return invalid
        if not schema or schema == self._get_basic_schema():
            if not schema.get('properties'):
                return ResultVerificationResultDTO.create_invalid(
                    errors=["Missing match result schema for game"],
                    metadata={'game_slug': game_slug, 'validation_method': 'schema_missing'}
                )
        
        # Validate required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in payload:
                errors.append(f"Missing required field: {field}")
        
        # Validate field types
        properties = schema.get('properties', {})
        for field, value in payload.items():
            if field in properties:
                field_schema = properties[field]
                type_error = self._validate_field_type(field, value, field_schema)
                if type_error:
                    errors.append(type_error)
        
        # Business rule validation
        business_errors, business_warnings = self._validate_business_rules(payload, properties)
        errors.extend(business_errors)
        warnings.extend(business_warnings)
        
        # Early return if validation failed
        if errors:
            return ResultVerificationResultDTO.create_invalid(
                errors=errors,
                warnings=warnings,
                metadata={
                    'game_slug': game_slug,
                    'validation_method': 'jsonschema',
                }
            )
        
        # Calculate scores
        calculated_scores = self._calculate_scores(game_slug, payload)
        
        # Check for calculation warnings
        if calculated_scores and calculated_scores.get('warnings'):
            warnings.extend(calculated_scores.pop('warnings'))
        
        return ResultVerificationResultDTO.create_valid(
            calculated_scores=calculated_scores,
            metadata={
                'game_slug': game_slug,
                'validation_method': 'jsonschema_with_rules_engine',
                'schema_version': schema.get('version', '1.0'),
            }
        )
    
    def _get_basic_schema(self) -> Dict[str, Any]:
        """
        Return basic fallback schema requiring winner/loser team IDs.
        
        Used when game schema not found in database.
        """
        return {
            "type": "object",
            "required": ["winner_team_id", "loser_team_id"],
            "properties": {
                "winner_team_id": {"type": "integer"},
                "loser_team_id": {"type": "integer"},
                "score": {"type": "string"},
                "map": {"type": "string"},
                "duration_seconds": {"type": "integer"},
            }
        }
    
    def _validate_field_type(
        self,
        field_name: str,
        value: Any,
        field_schema: Dict[str, Any],
    ) -> Optional[str]:
        """
        Validate field value against JSON Schema type.
        
        Args:
            field_name: Field name
            value: Field value
            field_schema: JSON Schema for field
            
        Returns:
            Error message if invalid, None if valid
        """
        expected_type = field_schema.get('type')
        if not expected_type:
            return None
        
        # Type mapping (JSON Schema type -> Python type)
        type_mapping = {
            'integer': int,
            'number': (int, float),
            'string': str,
            'boolean': bool,
            'array': list,
            'object': dict,
        }
        
        python_type = type_mapping.get(expected_type)
        if not python_type:
            return None
        
        if not isinstance(value, python_type):
            return f"Field '{field_name}' must be of type {expected_type}, got {type(value).__name__}"
        
        # Validate enum if present
        if 'enum' in field_schema:
            if value not in field_schema['enum']:
                return f"Field '{field_name}' must be one of {field_schema['enum']}, got '{value}'"
        
        # Validate pattern if present (for strings)
        if expected_type == 'string' and 'pattern' in field_schema:
            import re
            pattern = field_schema['pattern']
            if not re.match(pattern, value):
                return f"Field '{field_name}' does not match required pattern: {pattern}"
        
        return None
    
    def _validate_business_rules(
        self,
        payload: Dict[str, Any],
        properties: Dict[str, Any],
    ) -> tuple[list[str], list[str]]:
        """
        Validate business rules for match results.
        
        Rules:
        - winner_team_id != loser_team_id
        - Scores must be non-negative
        - Duration must be positive
        
        Args:
            payload: Match result payload
            properties: Schema properties
            
        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Rule: Winner != Loser
        winner_id = payload.get('winner_team_id')
        loser_id = payload.get('loser_team_id')
        if winner_id and loser_id and winner_id == loser_id:
            errors.append("winner_team_id and loser_team_id cannot be the same")
        
        # Rule: Score format validation (if present)
        score_str = payload.get('score')
        if score_str and isinstance(score_str, str):
            if '-' in score_str:
                parts = score_str.split('-')
                if len(parts) == 2:
                    try:
                        winner_score = int(parts[0])
                        loser_score = int(parts[1])
                        
                        # Negative score check
                        if winner_score < 0 or loser_score < 0:
                            errors.append("Scores cannot be negative")
                        
                        # Suspicious score check (very high scores)
                        if winner_score > 100 or loser_score > 100:
                            warnings.append(f"Unusually high score: {score_str}")
                        
                        # Winner should have higher score
                        if winner_score <= loser_score:
                            warnings.append(f"Winner score ({winner_score}) should be higher than loser score ({loser_score})")
                    except ValueError:
                        errors.append(f"Invalid score format: {score_str}")
        
        # Rule: Duration validation
        duration = payload.get('duration_seconds')
        if duration is not None:
            if not isinstance(duration, int):
                errors.append("duration_seconds must be an integer")
            elif duration < 0:
                errors.append("duration_seconds cannot be negative")
            elif duration < 60:
                warnings.append(f"Suspiciously short match duration: {duration}s")
            elif duration > 7200:  # 2 hours
                warnings.append(f"Suspiciously long match duration: {duration}s")
        
        return errors, warnings
    
    def _calculate_scores(
        self,
        game_slug: str,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate scores using GameRulesEngine (if available).
        
        Integrates with Phase 2 GameRulesEngine for score calculation.
        Falls back to basic extraction if rules engine not available.
        
        Args:
            game_slug: Game identifier
            payload: Match result payload
            
        Returns:
            Dictionary with:
            - winner_team_id
            - loser_team_id
            - winner_score
            - loser_score
            - map (optional)
            - duration_seconds (optional)
        """
        # Try to use GameRulesEngine (Phase 2 integration)
        try:
            from apps.games.services import GameRulesEngine
            
            engine = GameRulesEngine(game_slug)
            calculated = engine.calculate_match_scores(payload)
            
            # If engine returns scores, use them
            if calculated:
                return calculated
        except (ImportError, AttributeError, Exception) as e:
            # GameRulesEngine not available or method not implemented
            # Fall back to basic extraction
            logger.debug(f"GameRulesEngine not available for {game_slug}, using basic extraction: {e}")
        
        # Basic score extraction
        calculated_scores = {
            'winner_team_id': payload.get('winner_team_id'),
            'loser_team_id': payload.get('loser_team_id'),
            'winner_score': self._extract_winner_score(payload.get('score', '')),
            'loser_score': self._extract_loser_score(payload.get('score', '')),
        }
        
        # Add optional fields
        if 'map' in payload:
            calculated_scores['map'] = payload['map']
        if 'duration_seconds' in payload:
            calculated_scores['duration_seconds'] = payload['duration_seconds']
        
        return calculated_scores
    
    def _extract_winner_score(self, score_str: str) -> int:
        """
        Extract winner score from score string.
        
        Assumes format like "13-7" or "2-1".
        Returns 0 if parsing fails.
        """
        if not score_str or '-' not in score_str:
            return 0
        
        try:
            parts = score_str.split('-')
            return int(parts[0])
        except (ValueError, IndexError):
            return 0
    
    def _extract_loser_score(self, score_str: str) -> int:
        """
        Extract loser score from score string.
        
        Assumes format like "13-7" or "2-1".
        Returns 0 if parsing fails.
        """
        if not score_str or '-' not in score_str:
            return 0
        
        try:
            parts = score_str.split('-')
            return int(parts[1])
        except (ValueError, IndexError):
            return 0
