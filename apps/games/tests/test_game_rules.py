"""
Test suite for Phase 2 Game Rules Engine.

Tests cover:
- GameMatchResultSchema model validation
- GameScoringRule model validation
- GameRulesEngine scoring and validation
- GameValidationService identity and registration validation
- GameService configuration getters

Phase 2, Epic 2.1-2.3: Game Configuration and Rules Engine
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.games.models import (
    Game,
    GameMatchResultSchema,
    GameScoringRule,
    GameTournamentConfig,
    GamePlayerIdentityConfig,
)
from apps.games.services.rules_engine import GameRulesEngine
from apps.games.services.validation_service import GameValidationService
from apps.games.services.game_service import game_service
from apps.tournament_ops.dtos.common import ValidationResult
from apps.tournament_ops.dtos.user import UserProfileDTO
from apps.tournament_ops.dtos.team import TeamDTO


class GameMatchResultSchemaModelTests(TestCase):
    """Test GameMatchResultSchema model validation."""

    def setUp(self):
        self.game = Game.objects.create(
            slug="test-game",
            name="Test Game",
            display_name="Test Game",
            is_active=True,
        )

    def test_create_integer_field_schema(self):
        """Test creating integer field schema."""
        schema = GameMatchResultSchema.objects.create(
            game=self.game,
            field_name="kills",
            display_label="Kills",
            field_type="integer",
            validation={"min": 0, "max": 100},
            is_required=True,
        )
        self.assertEqual(schema.field_name, "kills")
        self.assertEqual(schema.field_type, "integer")
        self.assertTrue(schema.is_required)

    def test_enum_requires_choices_validation(self):
        """Test that enum type requires choices in validation."""
        schema = GameMatchResultSchema(
            game=self.game,
            field_name="map_name",
            display_label="Map",
            field_type="enum",
            validation={},  # Missing choices
            is_required=True,
        )
        with self.assertRaises(ValidationError) as ctx:
            schema.clean()
        self.assertIn("choices", str(ctx.exception))

    def test_min_max_validation(self):
        """Test that min <= max for numeric types."""
        schema = GameMatchResultSchema(
            game=self.game,
            field_name="score",
            display_label="Score",
            field_type="integer",
            validation={"min": 100, "max": 50},  # Invalid: min > max
            is_required=True,
        )
        with self.assertRaises(ValidationError) as ctx:
            schema.clean()
        self.assertIn("min", str(ctx.exception).lower())

    def test_unique_field_name_per_game(self):
        """Test unique_together constraint on (game, field_name)."""
        GameMatchResultSchema.objects.create(
            game=self.game,
            field_name="kills",
            display_label="Kills",
            field_type="integer",
        )
        with self.assertRaises(Exception):  # IntegrityError
            GameMatchResultSchema.objects.create(
                game=self.game,
                field_name="kills",  # Duplicate
                display_label="Kills 2",
                field_type="integer",
            )


class GameScoringRuleModelTests(TestCase):
    """Test GameScoringRule model validation."""

    def setUp(self):
        self.game = Game.objects.create(
            slug="test-game",
            name="Test Game",
            display_name="Test Game",
            is_active=True,
        )

    def test_create_win_loss_rule(self):
        """Test creating win/loss scoring rule."""
        rule = GameScoringRule.objects.create(
            game=self.game,
            rule_type="win_loss",
            config={},
            description="Simple win/loss scoring",
            is_active=True,
            priority=10,
        )
        self.assertEqual(rule.rule_type, "win_loss")
        self.assertTrue(rule.is_active)

    def test_points_accumulation_requires_point_fields(self):
        """Test that points_accumulation requires point_fields in config."""
        rule = GameScoringRule(
            game=self.game,
            rule_type="points_accumulation",
            config={},  # Missing point_fields
            is_active=True,
        )
        with self.assertRaises(ValidationError) as ctx:
            rule.clean()
        self.assertIn("point_fields", str(ctx.exception))

    def test_placement_order_requires_placement_points(self):
        """Test that placement_order requires placement_points in config."""
        rule = GameScoringRule(
            game=self.game,
            rule_type="placement_order",
            config={},  # Missing placement_points
            is_active=True,
        )
        with self.assertRaises(ValidationError) as ctx:
            rule.clean()
        self.assertIn("placement_points", str(ctx.exception))

    def test_valid_points_accumulation_config(self):
        """Test valid points_accumulation config."""
        rule = GameScoringRule(
            game=self.game,
            rule_type="points_accumulation",
            config={"point_fields": {"kills": 1, "assists": 0.5}},
            is_active=True,
        )
        rule.clean()  # Should not raise

    def test_priority_ordering(self):
        """Test rules ordered by priority descending."""
        GameScoringRule.objects.create(
            game=self.game, rule_type="win_loss", priority=5, is_active=True
        )
        GameScoringRule.objects.create(
            game=self.game, rule_type="points_accumulation", priority=10, is_active=True,
            config={"point_fields": {"kills": 1}}
        )
        GameScoringRule.objects.create(
            game=self.game, rule_type="placement_order", priority=1, is_active=True,
            config={"placement_points": [10, 6, 4]}
        )

        rules = list(GameScoringRule.objects.filter(game=self.game))
        # Should be ordered by priority descending
        self.assertEqual(rules[0].priority, 10)
        self.assertEqual(rules[1].priority, 5)
        self.assertEqual(rules[2].priority, 1)


class GameRulesEngineTests(TestCase):
    """Test GameRulesEngine scoring and validation."""

    def setUp(self):
        self.game = Game.objects.create(
            slug="test-game",
            name="Test Game",
            display_name="Test Game",
            is_active=True,
        )
        self.engine = GameRulesEngine()

    def test_score_match_win_loss(self):
        """Test win/loss scoring."""
        GameScoringRule.objects.create(
            game=self.game,
            rule_type="win_loss",
            config={},
            is_active=True,
            priority=10,
        )

        result = self.engine.score_match("test-game", {"is_win": True})
        self.assertEqual(result["total_score"], 1)
        self.assertEqual(result["rule_type"], "win_loss")

        result = self.engine.score_match("test-game", {"is_win": False})
        self.assertEqual(result["total_score"], 0)

    def test_score_match_points_accumulation(self):
        """Test points accumulation scoring."""
        GameScoringRule.objects.create(
            game=self.game,
            rule_type="points_accumulation",
            config={"point_fields": {"kills": 1, "assists": 0.5, "deaths": -0.25}},
            is_active=True,
            priority=10,
        )

        payload = {"kills": 10, "assists": 6, "deaths": 4}
        result = self.engine.score_match("test-game", payload)
        
        # 10*1 + 6*0.5 + 4*(-0.25) = 10 + 3 - 1 = 12
        self.assertEqual(result["total_score"], 12)
        self.assertEqual(result["breakdown"]["kills"], 10)
        self.assertEqual(result["breakdown"]["assists"], 3)
        self.assertEqual(result["breakdown"]["deaths"], -1)

    def test_score_match_placement_order(self):
        """Test placement-based scoring."""
        GameScoringRule.objects.create(
            game=self.game,
            rule_type="placement_order",
            config={"placement_points": [10, 6, 4, 2, 1]},
            is_active=True,
            priority=10,
        )

        result = self.engine.score_match("test-game", {"placement": 1})
        self.assertEqual(result["total_score"], 10)

        result = self.engine.score_match("test-game", {"placement": 3})
        self.assertEqual(result["total_score"], 4)

        result = self.engine.score_match("test-game", {"placement": 10})
        self.assertEqual(result["total_score"], 0)  # Out of range

    def test_score_match_time_based(self):
        """Test time-based scoring."""
        GameScoringRule.objects.create(
            game=self.game,
            rule_type="time_based",
            config={},
            is_active=True,
            priority=10,
        )

        result = self.engine.score_match("test-game", {"completion_time": 125.5})
        self.assertEqual(result["total_score"], 125.5)

    def test_determine_winner_explicit_field(self):
        """Test winner determination from explicit field."""
        winner_id = self.engine.determine_winner(
            "test-game", {"winner_team_id": 42}
        )
        self.assertEqual(winner_id, 42)

    def test_determine_winner_score_comparison(self):
        """Test winner determination from score comparison."""
        winner_id = self.engine.determine_winner(
            "test-game", {"team_a_id": 10, "team_a_score": 13, "team_b_score": 9}
        )
        self.assertEqual(winner_id, 10)

        winner_id = self.engine.determine_winner(
            "test-game", {"team_b_id": 20, "team_a_score": 5, "team_b_score": 13}
        )
        self.assertEqual(winner_id, 20)

    def test_determine_winner_draw(self):
        """Test draw detection."""
        winner_id = self.engine.determine_winner(
            "test-game", {"team_a_score": 10, "team_b_score": 10}
        )
        self.assertIsNone(winner_id)

    def test_validate_result_schema_required_fields(self):
        """Test schema validation for required fields."""
        GameMatchResultSchema.objects.create(
            game=self.game,
            field_name="rounds_won",
            field_type="integer",
            is_required=True,
        )

        result = self.engine.validate_result_schema("test-game", {})
        self.assertFalse(result.is_valid)
        self.assertTrue(any("required" in err.lower() for err in result.errors))

        result = self.engine.validate_result_schema("test-game", {"rounds_won": 13})
        self.assertTrue(result.is_valid)

    def test_validate_result_schema_integer_type(self):
        """Test schema validation for integer type."""
        GameMatchResultSchema.objects.create(
            game=self.game,
            field_name="kills",
            field_type="integer",
            is_required=False,
        )

        result = self.engine.validate_result_schema("test-game", {"kills": "abc"})
        self.assertFalse(result.is_valid)
        self.assertTrue(any("integer" in err.lower() for err in result.errors))

        result = self.engine.validate_result_schema("test-game", {"kills": 42})
        self.assertTrue(result.is_valid)

    def test_validate_result_schema_integer_range(self):
        """Test schema validation for integer ranges."""
        GameMatchResultSchema.objects.create(
            game=self.game,
            field_name="placement",
            field_type="integer",
            validation={"min": 1, "max": 20},
        )

        result = self.engine.validate_result_schema("test-game", {"placement": 0})
        self.assertFalse(result.is_valid)

        result = self.engine.validate_result_schema("test-game", {"placement": 25})
        self.assertFalse(result.is_valid)

        result = self.engine.validate_result_schema("test-game", {"placement": 10})
        self.assertTrue(result.is_valid)

    def test_validate_result_schema_enum(self):
        """Test schema validation for enum fields."""
        GameMatchResultSchema.objects.create(
            game=self.game,
            field_name="map_name",
            field_type="enum",
            validation={"choices": ["Haven", "Bind", "Split", "Ascent"]},
        )

        result = self.engine.validate_result_schema("test-game", {"map_name": "Invalid"})
        self.assertFalse(result.is_valid)

        result = self.engine.validate_result_schema("test-game", {"map_name": "Haven"})
        self.assertTrue(result.is_valid)

    def test_validate_result_schema_no_schema_lenient(self):
        """Test that no schema = accept anything."""
        result = self.engine.validate_result_schema("test-game", {"any_field": "any_value"})
        self.assertTrue(result.is_valid)


class GameValidationServiceTests(TestCase):
    """Test GameValidationService."""

    def setUp(self):
        self.game = Game.objects.create(
            slug="valorant",
            name="VALORANT",
            display_name="VALORANT",
            is_active=True,
        )
        self.validator = GameValidationService()

    def test_validate_identity_required_fields(self):
        """Test identity validation for required fields."""
        GamePlayerIdentityConfig.objects.create(
            game=self.game,
            field_name="riot_id",
            display_name="Riot ID",
            is_required=True,
            validation_regex=r"^[a-zA-Z0-9]+#[a-zA-Z0-9]+$",
        )

        result = self.validator.validate_identity("valorant", {})
        self.assertFalse(result.is_valid)
        self.assertTrue(any("required" in err.lower() for err in result.errors))

        result = self.validator.validate_identity("valorant", {"riot_id": "Player#1234"})
        self.assertTrue(result.is_valid)

    def test_validate_identity_regex(self):
        """Test identity validation regex matching."""
        GamePlayerIdentityConfig.objects.create(
            game=self.game,
            field_name="riot_id",
            display_name="Riot ID",
            is_required=True,
            validation_regex=r"^[a-zA-Z0-9]+#[a-zA-Z0-9]+$",
        )

        result = self.validator.validate_identity("valorant", {"riot_id": "Invalid Riot ID"})
        self.assertFalse(result.is_valid)

        result = self.validator.validate_identity("valorant", {"riot_id": "ValidName#1234"})
        self.assertTrue(result.is_valid)

    def test_validate_registration_email_verification(self):
        """Test registration validation for email verification."""
        GameTournamentConfig.objects.create(
            game=self.game,
            require_verified_email=True,
        )

        user_dto = UserProfileDTO(
            email="test@example.com",
            email_verified=False,
            phone=None,
            phone_verified=False,
            discord=None,
            riot_id=None,
            steam_id=None,
            pubg_mobile_id=None,
            age=None,
            region=None,
        )
        team_dto = TeamDTO(
            id=1,
            name="Test Team",
            captain_id=1,
            captain_name="Captain",
            member_ids=[1],
            member_names=["Member1"],
            game="valorant",
            is_verified=True,
            logo_url=None,
        )

        result = self.validator.validate_registration("valorant", user_dto, team_dto, {})
        self.assertFalse(result.is_eligible)
        self.assertTrue(any("email" in reason.lower() for reason in result.reasons))

    def test_validate_registration_team_size(self):
        """Test registration validation for team size."""
        GameTournamentConfig.objects.create(
            game=self.game,
            min_team_size=5,
            max_team_size=5,
        )

        user_dto = UserProfileDTO(
            email="test@example.com",
            email_verified=True,
            phone=None,
            phone_verified=False,
            discord=None,
            riot_id=None,
            steam_id=None,
            pubg_mobile_id=None,
            age=None,
            region=None,
        )
        team_dto = TeamDTO(
            id=1,
            name="Test Team",
            captain_id=1,
            captain_name="Captain",
            member_ids=[1, 2, 3],
            member_names=["Member1", "Member2", "Member3"],
            game="valorant",
            is_verified=True,
            logo_url=None,
        )

        result = self.validator.validate_registration("valorant", user_dto, team_dto, {})
        self.assertFalse(result.is_eligible)
        self.assertTrue(any("size" in reason.lower() for reason in result.reasons))

    def test_validate_match_result_delegates_to_engine(self):
        """Test that validate_match_result delegates to GameRulesEngine."""
        GameMatchResultSchema.objects.create(
            game=self.game,
            field_name="rounds_won",
            field_type="integer",
            is_required=True,
        )

        result = self.validator.validate_match_result("valorant", {})
        self.assertFalse(result.is_valid)

        result = self.validator.validate_match_result("valorant", {"rounds_won": 13})
        self.assertTrue(result.is_valid)


class GameServiceTests(TestCase):
    """Test GameService configuration getters."""

    def setUp(self):
        self.game = Game.objects.create(
            slug="test-game",
            name="Test Game",
            display_name="Test Game",
            is_active=True,
        )

    def test_get_player_identity_config(self):
        """Test get_player_identity_config method."""
        GamePlayerIdentityConfig.objects.create(
            game=self.game,
            field_name="player_id",
            display_name="Player ID",
            order=1,
        )

        configs = game_service.get_player_identity_config("test-game")
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0].field_name, "player_id")

    def test_get_scoring_rules(self):
        """Test get_scoring_rules method."""
        GameScoringRule.objects.create(
            game=self.game,
            rule_type="win_loss",
            priority=10,
            is_active=True,
        )
        GameScoringRule.objects.create(
            game=self.game,
            rule_type="points_accumulation",
            config={"point_fields": {"kills": 1}},
            priority=5,
            is_active=True,
        )

        rules = game_service.get_scoring_rules("test-game")
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0].priority, 10)  # Highest priority first

    def test_get_match_schema(self):
        """Test get_match_schema method."""
        GameMatchResultSchema.objects.create(
            game=self.game,
            field_name="kills",
            field_type="integer",
        )
        GameMatchResultSchema.objects.create(
            game=self.game,
            field_name="deaths",
            field_type="integer",
        )

        schemas = game_service.get_match_schema("test-game")
        self.assertEqual(len(schemas), 2)
        # Ordered by field_name
        self.assertEqual(schemas[0].field_name, "deaths")
        self.assertEqual(schemas[1].field_name, "kills")

    def test_get_methods_raise_on_invalid_game(self):
        """Test that getter methods raise ValueError for invalid game."""
        with self.assertRaises(ValueError):
            game_service.get_player_identity_config("invalid-game")

        with self.assertRaises(ValueError):
            game_service.get_scoring_rules("invalid-game")

        with self.assertRaises(ValueError):
            game_service.get_match_schema("invalid-game")
