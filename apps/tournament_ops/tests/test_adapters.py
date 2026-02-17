"""
Unit tests for TournamentOps service adapters.

Tests verify that adapters:
1. Call domain services correctly
2. Convert models to DTOs properly
3. Raise appropriate exceptions
4. Maintain architecture boundaries (no cross-domain model imports)

All domain services are mocked - no database dependencies.

Reference: CLEANUP_AND_TESTING_PART_6.md - §9.1 (Adapter Testing)
"""

import pytest
from types import SimpleNamespace
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import uuid

from apps.tournament_ops.adapters.team_adapter import TeamAdapter
from apps.tournament_ops.adapters.user_adapter import UserAdapter
from apps.tournament_ops.adapters.game_adapter import GameAdapter
from apps.tournament_ops.adapters.economy_adapter import EconomyAdapter

from apps.tournament_ops.dtos import (
    TeamDTO,
    UserProfileDTO,
    ValidationResult,
)
from apps.tournament_ops.exceptions import (
    TeamNotFoundError,
    UserNotFoundError,
    GameConfigNotFoundError,
    PaymentFailedError,
)


def _fake_team(**overrides):
    """Build a SimpleNamespace fake team (no vnext_memberships → from_model
    uses the simple-attribute path)."""
    defaults = dict(
        id=1, name="Test Team", tag="TST", slug="test-team",
        game="valorant", captain_id=100, captain_name="Captain",
        member_ids=[100, 101, 102], member_names=["Captain", "M1", "M2"],
        is_verified=True, is_active=True, logo_url=None,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ============================================================================
# TEAM ADAPTER TESTS
# ============================================================================


class TestTeamAdapter:
    """Test TeamAdapter implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = TeamAdapter()

    @patch('apps.organizations.services.compat.get_team_by_any_id')
    def test_get_team_returns_dto(self, mock_get_team):
        """Test get_team() calls get_team_by_any_id and returns TeamDTO."""
        # Arrange
        mock_get_team.return_value = _fake_team()

        # Act
        result = self.adapter.get_team(team_id=1)

        # Assert
        assert isinstance(result, TeamDTO)
        assert result.id == 1
        assert result.name == "Test Team"
        assert result.game == "valorant"
        assert result.captain_id == 100
        assert len(result.member_ids) == 3
        mock_get_team.assert_called_once_with(1)

    @patch('apps.organizations.services.compat.get_team_by_any_id')
    def test_get_team_not_found_raises_exception(self, mock_get_team):
        """Test get_team() raises TeamNotFoundError when team doesn't exist."""
        # Arrange
        mock_get_team.return_value = None

        # Act & Assert
        with pytest.raises(TeamNotFoundError, match="Team 999 not found"):
            self.adapter.get_team(team_id=999)

    @patch('apps.organizations.services.compat.get_team_by_any_id')
    def test_list_team_members_returns_member_ids(self, mock_get_team):
        """Test list_team_members() returns list of member IDs."""
        # Arrange
        mock_get_team.return_value = _fake_team(
            member_ids=[100, 101, 102, 103],
            member_names=["Cap", "M1", "M2", "M3"],
        )

        # Act
        result = self.adapter.list_team_members(team_id=1)

        # Assert
        assert result == [100, 101, 102, 103]
        assert len(result) == 4

    @patch('apps.organizations.services.compat.get_team_by_any_id')
    def test_validate_membership_true_for_member(self, mock_get_team):
        """Test validate_membership() returns True when user is team member."""
        # Arrange
        mock_get_team.return_value = _fake_team()

        # Act
        result = self.adapter.validate_membership(team_id=1, user_id=101)

        # Assert
        assert result is True

    @patch('apps.organizations.services.compat.get_team_by_any_id')
    def test_validate_membership_false_for_non_member(self, mock_get_team):
        """Test validate_membership() returns False when user is not team member."""
        # Arrange
        mock_get_team.return_value = _fake_team()

        # Act
        result = self.adapter.validate_membership(team_id=1, user_id=999)

        # Assert
        assert result is False

    @patch('apps.games.services.game_service.GameService')
    @patch('apps.organizations.services.compat.get_team_by_any_id')
    def test_validate_team_eligibility_success(self, mock_get_team, mock_game_service):
        """Test validate_team_eligibility() returns valid when all checks pass."""
        # Arrange
        mock_get_team.return_value = _fake_team(
            member_ids=[100, 101, 102, 103, 104],
            member_names=["C", "M1", "M2", "M3", "M4"],
        )

        mock_game = Mock()
        mock_game.slug = "valorant"
        mock_game.name = "Valorant"
        mock_game_service.get_game_by_id.return_value = mock_game

        # Act
        result = self.adapter.validate_team_eligibility(
            team_id=1,
            game_id=1,
            required_team_size=5,
            tournament_id=1
        )

        # Assert
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0

    @patch('apps.games.services.game_service.GameService')
    @patch('apps.organizations.services.compat.get_team_by_any_id')
    def test_validate_team_eligibility_fails_on_unverified_team(
        self, mock_get_team, mock_game_service
    ):
        """Test validate_team_eligibility() fails when team is not verified."""
        # Arrange
        mock_get_team.return_value = _fake_team(
            is_verified=False,
            member_ids=[100, 101, 102, 103, 104],
            member_names=["C", "M1", "M2", "M3", "M4"],
        )

        mock_game = Mock()
        mock_game.slug = "valorant"
        mock_game_service.get_game_by_id.return_value = mock_game

        # Act
        result = self.adapter.validate_team_eligibility(
            team_id=1,
            game_id=1,
            required_team_size=5,
            tournament_id=1
        )

        # Assert
        assert result.is_valid is False
        assert "Team must be verified to register for tournaments" in result.errors

    @patch('apps.games.services.game_service.GameService')
    @patch('apps.organizations.services.compat.get_team_by_any_id')
    def test_validate_team_eligibility_fails_on_insufficient_members(
        self, mock_get_team, mock_game_service
    ):
        """Test validate_team_eligibility() fails when team size too small."""
        # Arrange
        mock_get_team.return_value = _fake_team()  # 3 members by default

        mock_game = Mock()
        mock_game.slug = "valorant"
        mock_game_service.get_game_by_id.return_value = mock_game

        # Act
        result = self.adapter.validate_team_eligibility(
            team_id=1,
            game_id=1,
            required_team_size=5,
            tournament_id=1
        )

        # Assert
        assert result.is_valid is False
        assert any("has" in err and "members but tournament requires" in err for err in result.errors)

    @patch('apps.organizations.services.compat.get_team_by_any_id')
    def test_check_tournament_permission_true_for_captain(self, mock_get_team):
        """Test check_tournament_permission() returns True for team captain."""
        # Arrange
        mock_get_team.return_value = _fake_team()

        # Act
        result = self.adapter.check_tournament_permission(user_id=100, team_id=1)

        # Assert
        assert result is True

    @patch('apps.organizations.services.compat.get_team_by_any_id')
    def test_check_tournament_permission_false_for_non_captain(self, mock_get_team):
        """Test check_tournament_permission() returns False for non-captain."""
        # Arrange
        mock_get_team.return_value = _fake_team()

        # Act
        result = self.adapter.check_tournament_permission(user_id=101, team_id=1)

        # Assert
        assert result is False

    @patch('apps.organizations.models.Team.objects')
    def test_check_health_returns_true_when_accessible(self, mock_team_objects):
        """Test check_health() returns True when Team model is accessible."""
        # Arrange
        mock_team_objects.exists.return_value = True

        # Act
        result = self.adapter.check_health()

        # Assert
        assert result is True
        mock_team_objects.exists.assert_called_once()

    @patch('apps.organizations.models.Team.objects')
    def test_check_health_returns_false_on_exception(self, mock_team_objects):
        """Test check_health() returns False when database error occurs."""
        # Arrange
        mock_team_objects.exists.side_effect = Exception("DB connection failed")

        # Act
        result = self.adapter.check_health()

        # Assert
        assert result is False


# ============================================================================
# USER ADAPTER TESTS
# ============================================================================


class TestUserAdapter:
    """Test UserAdapter implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = UserAdapter()

    @patch.object(UserProfileDTO, 'from_model')
    @patch('apps.user_profile.models.UserProfile.objects')
    def test_get_user_profile_returns_dto(self, mock_profile_objects, mock_from_model):
        """Test get_user_profile() fetches UserProfile and returns DTO."""
        # Arrange
        mock_profile_objects.select_related.return_value.get.return_value = Mock()

        expected_dto = UserProfileDTO(
            email="test@example.com", email_verified=True,
            phone=None, phone_verified=False, discord=None,
            game_ids={}, age=25, region="US",
        )
        mock_from_model.return_value = expected_dto

        # Act
        result = self.adapter.get_user_profile(user_id=1)

        # Assert
        assert isinstance(result, UserProfileDTO)
        assert result.email == "test@example.com"
        assert result.email_verified is True
        assert result.age == 25
        assert result.region == "US"
        mock_profile_objects.select_related.assert_called_once_with('user')

    @patch('apps.user_profile.models.UserProfile.objects')
    def test_get_user_profile_not_found_raises_exception(self, mock_profile_objects):
        """Test get_user_profile() raises UserNotFoundError when user doesn't exist."""
        # Arrange
        from apps.user_profile.models import UserProfile
        mock_profile_objects.select_related.return_value.get.side_effect = \
            UserProfile.DoesNotExist

        # Act & Assert
        with pytest.raises(UserNotFoundError, match="User 999 not found"):
            self.adapter.get_user_profile(user_id=999)

    @patch.object(UserAdapter, 'get_user_profile')
    def test_is_user_eligible_true_for_verified_user(self, mock_get_profile):
        """Test is_user_eligible() returns True for verified user."""
        # Arrange
        mock_get_profile.return_value = UserProfileDTO(
            email="test@example.com", email_verified=True,
            phone=None, phone_verified=False, discord=None,
            game_ids={}, age=25, region="US",
        )

        # Act
        result = self.adapter.is_user_eligible(user_id=1, tournament_id=1)

        # Assert
        assert result is True

    @patch.object(UserAdapter, 'get_user_profile')
    def test_is_user_eligible_false_for_unverified_email(self, mock_get_profile):
        """Test is_user_eligible() returns False when email not verified."""
        # Arrange
        mock_get_profile.return_value = UserProfileDTO(
            email="test@example.com", email_verified=False,
            phone=None, phone_verified=False, discord=None,
            game_ids={}, age=25, region="US",
        )

        # Act
        result = self.adapter.is_user_eligible(user_id=1, tournament_id=1)

        # Assert
        assert result is False

    @patch.object(UserAdapter, 'get_user_profile')
    def test_is_user_eligible_false_when_user_not_found(self, mock_get_profile):
        """Test is_user_eligible() returns False when user doesn't exist."""
        # Arrange
        mock_get_profile.side_effect = UserNotFoundError("User 999 not found")

        # Act
        result = self.adapter.is_user_eligible(user_id=999, tournament_id=1)

        # Assert
        assert result is False

    def test_is_user_banned_returns_false(self):
        """Test is_user_banned() returns False (placeholder implementation)."""
        # Act
        result = self.adapter.is_user_banned(user_id=1)

        # Assert
        assert result is False  # Phase 1: always returns False

    @patch('apps.user_profile.models.UserProfile.objects')
    def test_check_health_returns_true_when_accessible(self, mock_profile_objects):
        """Test check_health() returns True when UserProfile model is accessible."""
        # Arrange
        mock_profile_objects.exists.return_value = True

        # Act
        result = self.adapter.check_health()

        # Assert
        assert result is True
        mock_profile_objects.exists.assert_called_once()

    @patch('apps.user_profile.models.UserProfile.objects')
    def test_check_health_returns_false_on_exception(self, mock_profile_objects):
        """Test check_health() returns False when database error occurs."""
        # Arrange
        mock_profile_objects.exists.side_effect = Exception("DB connection failed")

        # Act
        result = self.adapter.check_health()

        # Assert
        assert result is False


# ============================================================================
# GAME ADAPTER TESTS
# ============================================================================


class TestGameAdapter:
    """Test GameAdapter implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = GameAdapter()

    @patch('apps.games.services.game_service.GameService')
    def test_get_game_config_returns_dict(self, mock_service_class):
        """Test get_game_config() calls GameService and returns config dict."""
        # Arrange
        mock_game = Mock()
        mock_game.id = 1
        mock_game.slug = "valorant"
        mock_game.name = "Valorant"
        mock_game.description = "5v5 tactical shooter"
        mock_game.is_active = True

        mock_service_class.get_game.return_value = mock_game

        # Act
        result = self.adapter.get_game_config(game_slug="valorant")

        # Assert
        assert isinstance(result, dict)
        assert result['slug'] == "valorant"
        assert result['name'] == "Valorant"
        assert result['is_active'] is True
        mock_service_class.get_game.assert_called_once_with("valorant")

    @patch('apps.games.services.game_service.GameService')
    def test_get_game_config_raises_error_when_not_found(self, mock_service_class):
        """Test get_game_config() raises GameConfigNotFoundError when game doesn't exist."""
        # Arrange
        mock_service_class.get_game.return_value = None

        # Act & Assert
        with pytest.raises(GameConfigNotFoundError, match="Game 'unknown' not found"):
            self.adapter.get_game_config(game_slug="unknown")

    @patch('apps.games.services.game_service.game_service')
    def test_get_identity_fields_returns_list_of_dtos(self, mock_game_service):
        """Test get_identity_fields() calls GameService and returns GamePlayerIdentityConfigDTO list."""
        # Arrange
        from apps.tournament_ops.dtos.game_identity import GamePlayerIdentityConfigDTO

        # Mock GamePlayerIdentityConfig model instances
        mock_identity_config = Mock()
        mock_identity_config.field_name = "riot_id"
        mock_identity_config.display_name = "Riot ID"
        mock_identity_config.field_type = "text"
        mock_identity_config.is_required = True
        mock_identity_config.validation_regex = r"^[a-zA-Z0-9]+#[a-zA-Z0-9]+$"
        mock_identity_config.help_text = "Your Riot ID (e.g., Player#NA1)"
        mock_identity_config.placeholder = "Player#NA1"
        mock_identity_config.is_immutable = False

        mock_game_service.get_player_identity_config.return_value = [mock_identity_config]

        # Act
        result = self.adapter.get_identity_fields(game_slug="valorant")

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        # Result is dict for backward compatibility
        assert result[0]['field_name'] == "riot_id"
        assert result[0]['display_label'] == "Riot ID"
        assert result[0]['is_required'] is True
        assert result[0]['is_immutable'] is False
        mock_game_service.get_player_identity_config.assert_called_once_with("valorant")

    @patch('apps.games.services.validation_service.GameValidationService')
    def test_validate_game_identity_success(self, mock_validation_service_class):
        """Test validate_game_identity() delegates to GameValidationService and returns True for valid data."""
        # Arrange
        from apps.tournament_ops.dtos.common import ValidationResult

        mock_validation_service = Mock()
        mock_validation_service_class.return_value = mock_validation_service

        # Mock successful validation
        validation_result = ValidationResult(is_valid=True, errors=[])
        mock_validation_service.validate_identity.return_value = validation_result

        identity_payload = {"riot_id": "Player123#NA1"}

        # Act
        result = self.adapter.validate_game_identity(
            game_slug="valorant",
            identity_payload=identity_payload
        )

        # Assert
        assert result is True
        mock_validation_service.validate_identity.assert_called_once_with(
            "valorant", identity_payload
        )

    @patch('apps.games.services.validation_service.GameValidationService')
    def test_validate_game_identity_fails_on_missing_required_field(
        self, mock_validation_service_class
    ):
        """Test validate_game_identity() returns False when required field missing."""
        # Arrange
        from apps.tournament_ops.dtos.common import ValidationResult

        mock_validation_service = Mock()
        mock_validation_service_class.return_value = mock_validation_service

        # Mock validation failure
        validation_result = ValidationResult(
            is_valid=False,
            errors=["Missing required field: riot_id"]
        )
        mock_validation_service.validate_identity.return_value = validation_result

        identity_payload = {}  # MISSING REQUIRED FIELD

        # Act
        result = self.adapter.validate_game_identity(
            game_slug="valorant",
            identity_payload=identity_payload
        )

        # Assert
        assert result is False
        mock_validation_service.validate_identity.assert_called_once_with(
            "valorant", identity_payload
        )

    @patch('apps.games.services.validation_service.GameValidationService')
    def test_validate_game_identity_fails_on_regex_mismatch(
        self, mock_validation_service_class
    ):
        """Test validate_game_identity() returns False when regex validation fails."""
        # Arrange
        from apps.tournament_ops.dtos.common import ValidationResult

        mock_validation_service = Mock()
        mock_validation_service_class.return_value = mock_validation_service

        # Mock validation failure due to regex mismatch
        validation_result = ValidationResult(
            is_valid=False,
            errors=["Field 'riot_id' does not match required pattern"]
        )
        mock_validation_service.validate_identity.return_value = validation_result

        identity_payload = {"riot_id": "InvalidFormat"}  # MISSING #TAG

        # Act
        result = self.adapter.validate_game_identity(
            game_slug="valorant",
            identity_payload=identity_payload
        )

        # Assert
        assert result is False
        mock_validation_service.validate_identity.assert_called_once_with(
            "valorant", identity_payload
        )
    @patch('apps.games.services.game_service.GameService')
    def test_get_supported_formats_returns_list(self, mock_service_class):
        """Test get_supported_formats() returns list of format strings."""
        # Arrange
        mock_game = Mock()
        mock_game.id = 1
        mock_game.slug = "valorant"
        mock_game.is_active = True

        mock_service_class.get_game.return_value = mock_game

        # Act
        result = self.adapter.get_supported_formats(game_slug="valorant")

        # Assert
        assert isinstance(result, list)
        assert 'single_elimination' in result
        assert 'double_elimination' in result
        assert len(result) > 0

    @patch('apps.games.services.game_service.game_service')
    def test_get_scoring_rules_returns_dict_from_service(self, mock_game_service):
        """Test get_scoring_rules() delegates to GameService and returns scoring config dict."""
        # Arrange
        mock_rule = Mock()
        mock_rule.rule_type = "win_loss"
        mock_rule.config = {'points_per_win': 3, 'points_per_draw': 1, 'points_per_loss': 0}
        mock_rule.description = "Standard 3-1-0 scoring"
        mock_rule.priority = 1
        
        mock_game_service.get_scoring_rules.return_value = [mock_rule]

        # Act
        result = self.adapter.get_scoring_rules(game_slug="valorant")

        # Assert
        assert isinstance(result, dict)
        assert result['rule_type'] == "win_loss"
        assert result['config'] == {'points_per_win': 3, 'points_per_draw': 1, 'points_per_loss': 0}
        assert result['priority'] == 1
        mock_game_service.get_scoring_rules.assert_called_once_with("valorant")

    @patch('apps.games.services.game_service.game_service')
    def test_get_identity_fields_raises_game_config_not_found(self, mock_game_service):
        """Test get_identity_fields() raises GameConfigNotFoundError when game doesn't exist."""
        # Arrange
        from apps.tournament_ops.exceptions import GameConfigNotFoundError

        mock_game_service.get_player_identity_config.side_effect = GameConfigNotFoundError("Game 'unknown' not found")

        # Act & Assert
        with pytest.raises(GameConfigNotFoundError, match="Game 'unknown' not found"):
            self.adapter.get_identity_fields(game_slug="unknown")

    @patch('apps.games.services.validation_service.GameValidationService')
    def test_validate_game_identity_returns_false_on_value_error(
        self, mock_validation_service_class
    ):
        """Test validate_game_identity() returns False when service raises ValueError."""
        # Arrange
        mock_validation_service = Mock()
        mock_validation_service_class.return_value = mock_validation_service
        mock_validation_service.validate_identity.side_effect = ValueError("Invalid config")

        identity_payload = {"riot_id": "Player123#NA1"}

        # Act
        result = self.adapter.validate_game_identity(
            game_slug="valorant",
            identity_payload=identity_payload
        )

        # Assert
        assert result is False

    @patch('apps.games.services.game_service.game_service')
    def test_get_identity_fields_returns_empty_list_when_no_config(self, mock_game_service):
        """Test get_identity_fields() returns empty list when game has no identity config."""
        # Arrange
        mock_game_service.get_player_identity_config.return_value = []

        # Act
        result = self.adapter.get_identity_fields(game_slug="valorant")

        # Assert
        assert isinstance(result, list)
        assert len(result) == 0
        mock_game_service.get_player_identity_config.assert_called_once_with("valorant")

    @patch('apps.games.models.Game.objects')
    def test_check_health_returns_true_when_accessible(self, mock_game_objects):
        """Test check_health() returns True when Game model is accessible."""
        # Arrange
        mock_game_objects.exists.return_value = True

        # Act
        result = self.adapter.check_health()

        # Assert
        assert result is True
        mock_game_objects.exists.assert_called_once()

    @patch('apps.games.models.Game.objects')
    def test_check_health_returns_false_on_exception(self, mock_game_objects):
        """Test check_health() returns False when database error occurs."""
        # Arrange
        mock_game_objects.exists.side_effect = Exception("DB connection failed")

        # Act
        result = self.adapter.check_health()

        # Assert
        assert result is False


# ============================================================================
# ECONOMY ADAPTER TESTS
# ============================================================================


class TestEconomyAdapter:
    """Test EconomyAdapter implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = EconomyAdapter()

    @patch('apps.economy.services.debit')
    @patch.object(EconomyAdapter, '_resolve_profile')
    def test_charge_registration_fee_returns_transaction_dict(
        self, mock_resolve, mock_debit
    ):
        """Test charge_registration_fee() calls debit and returns dict."""
        # Arrange
        mock_resolve.return_value = Mock()
        mock_debit.return_value = {
            'wallet_id': 42,
            'balance_after': 900,
            'transaction_id': 77,
            'idempotency_key': 'reg-fee-1-10',
        }

        # Act
        result = self.adapter.charge_registration_fee(
            user_id=1,
            tournament_id=10,
            amount=100,
            currency="DC"
        )

        # Assert
        assert isinstance(result, dict)
        assert result['user_id'] == 1
        assert result['amount'] == 100
        assert result['currency'] == "DC"
        assert result['status'] == 'completed'
        assert result['transaction_id'] == '77'
        assert result['metadata']['tournament_id'] == 10
        mock_debit.assert_called_once()

    def test_charge_registration_fee_raises_error_on_negative_amount(self):
        """Test charge_registration_fee() raises PaymentFailedError for negative amount."""
        # Act & Assert
        with pytest.raises(PaymentFailedError, match="Invalid amount"):
            self.adapter.charge_registration_fee(
                user_id=1,
                tournament_id=10,
                amount=-50,
                currency="DC"
            )

    @patch('apps.economy.services.debit')
    @patch.object(EconomyAdapter, '_resolve_profile')
    def test_charge_raises_insufficient_funds(self, mock_resolve, mock_debit):
        """Test charge_registration_fee() maps InsufficientFunds to PaymentFailedError."""
        # Arrange
        mock_resolve.return_value = Mock()
        mock_debit.side_effect = Exception("InsufficientFunds: not enough DC")

        # Act & Assert
        with pytest.raises(PaymentFailedError, match="Insufficient"):
            self.adapter.charge_registration_fee(
                user_id=1, tournament_id=10, amount=100
            )

    @patch('apps.economy.services.credit')
    @patch.object(EconomyAdapter, '_resolve_profile')
    def test_refund_registration_fee_returns_transaction_dict(
        self, mock_resolve, mock_credit
    ):
        """Test refund_registration_fee() calls credit and returns dict."""
        # Arrange
        mock_resolve.return_value = Mock()
        mock_credit.return_value = {
            'wallet_id': 42,
            'balance_after': 1100,
            'transaction_id': 78,
            'idempotency_key': 'refund-1-10',
        }

        # Act
        result = self.adapter.refund_registration_fee(
            user_id=1,
            tournament_id=10,
            amount=100,
            currency="DC",
            reason="Tournament cancelled"
        )

        # Assert
        assert isinstance(result, dict)
        assert result['user_id'] == 1
        assert result['amount'] == 100
        assert result['currency'] == "DC"
        assert result['status'] == 'refunded'
        assert result['metadata']['reason'] == "Tournament cancelled"
        mock_credit.assert_called_once()

    def test_refund_registration_fee_raises_error_on_negative_amount(self):
        """Test refund_registration_fee() raises PaymentFailedError for negative amount."""
        # Act & Assert
        with pytest.raises(PaymentFailedError, match="Invalid refund amount"):
            self.adapter.refund_registration_fee(
                user_id=1,
                tournament_id=10,
                amount=-50,
                currency="DC"
            )

    @patch('apps.economy.services.get_balance')
    @patch.object(EconomyAdapter, '_resolve_profile')
    def test_get_balance_returns_balance_dict(self, mock_resolve, mock_get_bal):
        """Test get_balance() returns user balance data from economy service."""
        # Arrange
        mock_resolve.return_value = Mock()
        mock_get_bal.return_value = 5000

        # Act
        result = self.adapter.get_balance(user_id=1)

        # Assert
        assert isinstance(result, dict)
        assert result['user_id'] == 1
        assert result['balance'] == 5000
        assert result['currency'] == "DC"

    @patch('apps.economy.models.DeltaCrownTransaction.objects')
    def test_verify_payment_returns_true_for_existing_txn(self, mock_txn_objects):
        """Test verify_payment() returns True when transaction exists."""
        # Arrange
        mock_txn_objects.filter.return_value.exists.return_value = True

        # Act
        result = self.adapter.verify_payment("42")

        # Assert
        assert result is True
        mock_txn_objects.filter.assert_called_once_with(pk=42)

    def test_verify_payment_returns_false_for_non_numeric_id(self):
        """Test verify_payment() returns False for non-numeric transaction ID."""
        # Act
        result = self.adapter.verify_payment("not-a-number")

        # Assert
        assert result is False

    @patch('apps.economy.models.DeltaCrownWallet.objects')
    def test_check_health_returns_true_when_accessible(self, mock_wallet_objects):
        """Test check_health() returns True when DeltaCrownWallet is accessible."""
        # Arrange
        mock_wallet_objects.exists.return_value = True

        # Act
        result = self.adapter.check_health()

        # Assert
        assert result is True

    @patch('apps.economy.models.DeltaCrownWallet.objects')
    def test_check_health_returns_false_on_exception(self, mock_wallet_objects):
        """Test check_health() returns False when database error occurs."""
        # Arrange
        mock_wallet_objects.exists.side_effect = Exception("DB connection failed")

        # Act
        result = self.adapter.check_health()

        # Assert
        assert result is False


# ============================================================================
# ARCHITECTURE GUARD TESTS
# ============================================================================


class TestArchitectureGuards:
    """
    Test that adapters maintain architecture boundaries.
    
    These tests verify the critical rule:
    NO CROSS-DOMAIN MODEL IMPORTS in apps.tournament_ops.adapters.*
    
    Adapters must ONLY:
    - Import domain services (TeamService, GameService, etc.)
    - Import domain exceptions
    - Return DTOs (never ORM models)
    """

    def test_team_adapter_no_cross_domain_model_imports(self):
        """Verify TeamAdapter doesn't import models from other domains."""
        import inspect
        from apps.tournament_ops.adapters import team_adapter
        
        source = inspect.getsource(team_adapter)
        
        # Should NOT import Team model at module level
        # (method-level imports are OK for health checks)
        assert "from apps.teams.models import Team" not in source
        assert "from apps.teams.models._legacy import Team" not in source.split("def check_health")[0]
        
        # Should use organizations compat layer or service functions
        assert "get_team_by_any_id" in source or "TeamService" in source
        
        # Should import TeamDTO
        assert "TeamDTO" in source

    def test_user_adapter_no_cross_domain_model_imports(self):
        """Verify UserAdapter doesn't import models from other domains."""
        import inspect
        from apps.tournament_ops.adapters import user_adapter
        
        source = inspect.getsource(user_adapter)
        
        # Module-level check (before first method definition)
        module_level_imports = source.split("class UserAdapter")[0]
        
        # Should NOT import UserProfile model at module level
        assert "from apps.user_profile.models import UserProfile" not in module_level_imports
        
        # Should import UserProfileDTO
        assert "UserProfileDTO" in source

    def test_game_adapter_no_cross_domain_model_imports(self):
        """Verify GameAdapter doesn't import models from other domains."""
        import inspect
        from apps.tournament_ops.adapters import game_adapter
        
        source = inspect.getsource(game_adapter)
        
        # Module-level check
        module_level_imports = source.split("class GameAdapter")[0]
        
        # Should NOT import Game model at module level
        assert "from apps.games.models import Game\n" not in module_level_imports
        
        # Should import GameService
        assert "GameService" in source

    def test_economy_adapter_no_cross_domain_model_imports(self):
        """Verify EconomyAdapter doesn't import models from other domains."""
        import inspect
        from apps.tournament_ops.adapters import economy_adapter
        
        source = inspect.getsource(economy_adapter)
        
        # Get just the imports section (before class definition)
        imports_section = source.split("class EconomyAdapter")[0]
        
        # Count actual import statements (not docstring references)
        import_lines = [line.strip() for line in imports_section.split('\n') 
                       if line.strip().startswith('from') or line.strip().startswith('import')]
        
        # Should NOT have "from apps.economy.models import" in actual import statements
        economy_model_imports = [line for line in import_lines 
                                if "from apps.economy.models import" in line]
        
        assert len(economy_model_imports) == 0, \
            f"Found economy model imports: {economy_model_imports}"

    def test_all_adapters_return_dtos_not_models(self):
        """
        Verify all adapter implementations don't return ORM models directly.
        
        This is a heuristic check - we scan adapter source code for model imports.
        """
        import inspect
        from apps.tournament_ops.adapters import (
            team_adapter,
            user_adapter,
            game_adapter,
            economy_adapter
        )
        
        adapters = [team_adapter, user_adapter, game_adapter, economy_adapter]
        
        for adapter_module in adapters:
            source = inspect.getsource(adapter_module)
            
            # Should not return ORM models in method signatures
            # We check for common Django model patterns
            assert "-> Team:" not in source, f"{adapter_module} returns Team model"
            assert "-> Game:" not in source, f"{adapter_module} returns Game model"
            assert "-> UserProfile:" not in source, f"{adapter_module} returns UserProfile model"
            
            # Should have DTO imports/usages
            assert "DTO" in source, f"{adapter_module} should use DTOs"
