"""
Game Rules Engine for scoring, winner determination, and result validation.

This engine provides game-agnostic logic for:
- Scoring match results based on configured rules
- Determining winners from match payloads
- Validating match result schemas

Phase 2, Epic 2.1: Game Rules Engine
Reference: SMART_REG_AND_RULES_PART_3.md, ARCH_PLAN_PART_1.md
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from apps.tournament_ops.dtos.common import ValidationResult

logger = logging.getLogger("games.rules_engine")


class GameRulesEngine:
    """
    Centralized rules engine for game-specific scoring and validation.

    This engine loads configuration from GameScoringRule and GameMatchResultSchema
    models and applies them to match payloads.

    Usage:
        engine = GameRulesEngine()
        score = engine.score_match("valorant", match_payload)
        winner_team_id = engine.determine_winner("valorant", match_payload)
        validation = engine.validate_result_schema("valorant", match_payload)
    """

    def score_match(self, game_slug: str, match_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a match based on the game's configured scoring rules.

        Args:
            game_slug: Game identifier (e.g., "valorant", "pubg-mobile")
            match_payload: Match result data submitted

        Returns:
            dict with scoring breakdown:
            {
                "total_score": 100,
                "breakdown": {"kills": 50, "placement": 50},
                "rule_type": "points_accumulation"
            }

        Raises:
            ValueError: If game not found or scoring rules missing
        """
        from apps.games.models import Game, GameScoringRule

        try:
            game = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            raise ValueError(f"Game '{game_slug}' not found")

        # Get active scoring rule (highest priority)
        scoring_rule = (
            GameScoringRule.objects.filter(game=game, is_active=True)
            .order_by("-priority")
            .first()
        )

        if not scoring_rule:
            # Default to win/loss if no rules configured
            logger.warning(f"No scoring rules for {game_slug}, defaulting to win/loss")
            return self._score_win_loss(match_payload)

        # Dispatch to appropriate scoring logic
        if scoring_rule.rule_type == "win_loss":
            return self._score_win_loss(match_payload)
        elif scoring_rule.rule_type == "points_accumulation":
            return self._score_points_accumulation(match_payload, scoring_rule.config)
        elif scoring_rule.rule_type == "placement_order":
            return self._score_placement_order(match_payload, scoring_rule.config)
        elif scoring_rule.rule_type == "time_based":
            return self._score_time_based(match_payload, scoring_rule.config)
        else:
            logger.error(f"Unknown rule type: {scoring_rule.rule_type}")
            raise ValueError(f"Unknown scoring rule type: {scoring_rule.rule_type}")

    def determine_winner(
        self, game_slug: str, match_payload: Dict[str, Any]
    ) -> Optional[int]:
        """
        Determine the winning team ID from match results.

        Args:
            game_slug: Game identifier
            match_payload: Match result data

        Returns:
            Team ID of winner, or None if draw/no winner

        Logic:
        1. Check for explicit "winner_team_id" field
        2. Otherwise, score match and compare
        """
        # Explicit winner field takes precedence
        if "winner_team_id" in match_payload:
            return match_payload["winner_team_id"]

        # Score-based winner determination
        scoring_result = self.score_match(game_slug, match_payload)

        # For multi-team matches, payload should have team_scores
        if "team_scores" in match_payload:
            team_scores = match_payload["team_scores"]
            if not team_scores:
                return None

            # Find highest score
            max_score = max(team_scores.values())
            winners = [
                team_id for team_id, score in team_scores.items() if score == max_score
            ]

            # Return winner if unique, None if tie
            return winners[0] if len(winners) == 1 else None

        # For 1v1 matches with explicit team_a/team_b scores
        team_a_score = match_payload.get("team_a_score", 0)
        team_b_score = match_payload.get("team_b_score", 0)

        if team_a_score > team_b_score:
            return match_payload.get("team_a_id")
        elif team_b_score > team_a_score:
            return match_payload.get("team_b_id")
        else:
            return None  # Draw

    def validate_result_schema(
        self, game_slug: str, match_payload: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate match result against game's configured schema.

        Args:
            game_slug: Game identifier
            match_payload: Match result data to validate

        Returns:
            ValidationResult with is_valid, errors list

        Validation checks:
        - Required fields present
        - Field types correct (int, str, bool, etc.)
        - Values within allowed ranges/enums
        """
        from apps.games.models import Game, GameMatchResultSchema

        try:
            game = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            return ValidationResult(
                is_valid=False, errors=[f"Game '{game_slug}' not found"]
            )

        # Get all schema definitions for this game
        schemas = GameMatchResultSchema.objects.filter(game=game)

        if not schemas.exists():
            # No schema defined - accept anything (lenient mode)
            logger.warning(f"No result schema defined for {game_slug}")
            return ValidationResult(is_valid=True, errors=[])

        errors = []

        for schema in schemas:
            field_name = schema.field_name
            field_value = match_payload.get(field_name)

            # Check required fields
            if schema.is_required and field_value is None:
                errors.append(f"Required field '{field_name}' missing")
                continue

            # Skip validation if field not present and not required
            if field_value is None:
                continue

            # Type validation
            type_error = self._validate_field_type(
                field_name, field_value, schema.field_type, schema.validation
            )
            if type_error:
                errors.append(type_error)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    # =========================================================================
    # Private scoring methods
    # =========================================================================

    def _score_win_loss(self, match_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simple binary win/loss scoring."""
        # Check both is_win (boolean) and winner_team_id (explicit winner)
        is_win = match_payload.get("is_win", False)
        winner_team_id = match_payload.get("winner_team_id")
        won = is_win or (winner_team_id is not None)
        return {
            "total_score": 1 if won else 0,
            "breakdown": {"win": 1 if won else 0},
            "rule_type": "win_loss",
        }

    def _score_points_accumulation(
        self, match_payload: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Points-based scoring (e.g., kills + assists + objectives).

        Config format:
        {
            "point_fields": {
                "kills": 1,
                "assists": 0.5,
                "objectives": 2
            }
        }
        """
        point_fields = config.get("point_fields", {})
        breakdown = {}
        total = 0

        for field_name, point_value in point_fields.items():
            field_count = match_payload.get(field_name, 0)
            points = field_count * point_value
            breakdown[field_name] = points
            total += points

        return {
            "total_score": total,
            "breakdown": breakdown,
            "rule_type": "points_accumulation",
        }

    def _score_placement_order(
        self, match_payload: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Placement-based scoring (Battle Royale).

        Config format:
        {
            "placement_points": [10, 6, 4, 2, 1]  # Points for 1st, 2nd, 3rd, etc.
        }
        """
        placement = match_payload.get("placement", 0)
        placement_points = config.get("placement_points", [])

        # Placement is 1-indexed (1st place = index 0)
        if 1 <= placement <= len(placement_points):
            points = placement_points[placement - 1]
        else:
            points = 0  # Out of configured range

        return {
            "total_score": points,
            "breakdown": {"placement": points},
            "rule_type": "placement_order",
        }

    def _score_time_based(
        self, match_payload: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Time-based scoring (racing, speedruns).

        Config format:
        {
            "time_field": "completion_time_seconds",
            "lower_is_better": true
        }
        """
        time_field = config.get("time_field", "completion_time")
        time_value = match_payload.get(time_field, 0)

        return {
            "total_score": time_value,
            "breakdown": {time_field: time_value},
            "rule_type": "time_based",
        }

    # =========================================================================
    # Private validation methods
    # =========================================================================

    def _validate_field_type(
        self,
        field_name: str,
        field_value: Any,
        expected_type: str,
        validation_rules: Dict[str, Any],
    ) -> Optional[str]:
        """
        Validate field type and constraints.

        Returns error message if invalid, None if valid.
        """
        # Type checking
        if expected_type == "integer":
            if not isinstance(field_value, int):
                return f"Field '{field_name}' must be an integer, got {type(field_value).__name__}"

            # Range validation
            if "min" in validation_rules and field_value < validation_rules["min"]:
                return f"Field '{field_name}' must be >= {validation_rules['min']}"
            if "max" in validation_rules and field_value > validation_rules["max"]:
                return f"Field '{field_name}' must be <= {validation_rules['max']}"

        elif expected_type == "decimal":
            if not isinstance(field_value, (int, float, Decimal)):
                return f"Field '{field_name}' must be a number, got {type(field_value).__name__}"

            # Range validation
            if "min" in validation_rules and field_value < validation_rules["min"]:
                return f"Field '{field_name}' must be >= {validation_rules['min']}"
            if "max" in validation_rules and field_value > validation_rules["max"]:
                return f"Field '{field_name}' must be <= {validation_rules['max']}"

        elif expected_type == "text":
            if not isinstance(field_value, str):
                return f"Field '{field_name}' must be a string, got {type(field_value).__name__}"

            # Length validation
            if "max_length" in validation_rules and len(field_value) > validation_rules["max_length"]:
                return f"Field '{field_name}' exceeds max length {validation_rules['max_length']}"

        elif expected_type == "boolean":
            if not isinstance(field_value, bool):
                return f"Field '{field_name}' must be a boolean, got {type(field_value).__name__}"

        elif expected_type == "enum":
            choices = validation_rules.get("choices", [])
            if field_value not in choices:
                return f"Field '{field_name}' must be one of {choices}, got '{field_value}'"

        elif expected_type == "json":
            if not isinstance(field_value, (dict, list)):
                return f"Field '{field_name}' must be a JSON object/array, got {type(field_value).__name__}"

        return None  # Valid
