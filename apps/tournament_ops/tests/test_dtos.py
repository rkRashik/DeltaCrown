"""
Unit tests for TournamentOps DTOs.

Tests DTO serialization, validation, and from_model() conversion WITHOUT
requiring Django ORM or database access. All tests use fake objects and dicts.

Phase: 1 (Core Foundation)
Epic: 1.3 (DTO Layer with Validation)
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from apps.tournament_ops.dtos.tournament import TournamentDTO
from apps.tournament_ops.dtos.team import TeamDTO
from apps.tournament_ops.dtos.user import UserProfileDTO
from apps.tournament_ops.dtos.match import MatchDTO
from apps.tournament_ops.dtos.registration import RegistrationDTO
from apps.tournament_ops.dtos.payment import PaymentResultDTO
from apps.tournament_ops.dtos.eligibility import EligibilityResultDTO
from apps.tournament_ops.dtos.stage import StageDTO
from apps.tournament_ops.dtos.game_identity import GamePlayerIdentityConfigDTO


class FakeTournamentModel:
    """Fake tournament model for testing from_model()."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeGameModel:
    """Fake game model with slug attribute."""

    def __init__(self, slug: str):
        self.slug = slug


# =============================================================================
# TournamentDTO Tests
# =============================================================================


def test_tournament_dto_from_model_with_orm_like_object():
    """Test TournamentDTO.from_model() with an ORM-like object."""
    fake_game = FakeGameModel(slug="valorant")
    fake_tournament = FakeTournamentModel(
        id=1,
        name="Summer Championship",
        game=fake_game,
        stage="registration",
        team_size=5,
        max_teams=16,
        status="active",
        start_time=datetime(2025, 6, 1, 10, 0),
        ruleset={"overtime": True},
    )

    dto = TournamentDTO.from_model(fake_tournament)

    assert dto.id == 1
    assert dto.name == "Summer Championship"
    assert dto.game_slug == "valorant"
    assert dto.stage == "registration"
    assert dto.team_size == 5
    assert dto.max_teams == 16
    assert dto.status == "active"
    assert dto.start_time == datetime(2025, 6, 1, 10, 0)
    assert dto.ruleset == {"overtime": True}


def test_tournament_dto_from_model_with_dict():
    """Test TournamentDTO.from_model() with a dict."""
    fake_tournament = {
        "id": 2,
        "name": "Winter Cup",
        "game": {"slug": "csgo"},
        "stage": "active",
        "team_size": 5,
        "max_teams": 8,
        "status": "completed",
        "start_time": datetime(2025, 12, 1, 14, 0),
        "ruleset": {},
    }

    dto = TournamentDTO.from_model(fake_tournament)

    assert dto.id == 2
    assert dto.name == "Winter Cup"
    assert dto.game_slug == "csgo"
    assert dto.team_size == 5
    assert dto.max_teams == 8


def test_tournament_dto_validation_success():
    """Test TournamentDTO.validate() with valid data."""
    dto = TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="registration",
        team_size=5,
        max_teams=16,
        status="active",
        start_time=datetime(2025, 6, 1, 10, 0),
        ruleset={},
    )

    errors = dto.validate()
    assert errors == []


def test_tournament_dto_validation_failures():
    """Test TournamentDTO.validate() with invalid data."""
    dto = TournamentDTO(
        id=1,
        name="",  # Empty name
        game_slug="",  # Empty game_slug
        stage="registration",
        team_size=0,  # Invalid team_size
        max_teams=-1,  # Invalid max_teams
        status="active",
        start_time=None,  # Missing start_time
        ruleset={},
    )

    errors = dto.validate()
    assert "name cannot be empty" in errors
    assert "game_slug cannot be empty" in errors
    assert "team_size must be greater than 0" in errors
    assert "max_teams must be greater than 0" in errors
    assert "start_time is required" in errors


def test_tournament_dto_to_dict():
    """Test TournamentDTO.to_dict() serialization."""
    dto = TournamentDTO(
        id=1,
        name="Test Tournament",
        game_slug="valorant",
        stage="registration",
        team_size=5,
        max_teams=16,
        status="active",
        start_time=datetime(2025, 6, 1, 10, 0),
        ruleset={"overtime": True},
    )

    data = dto.to_dict()
    assert data["name"] == "Test Tournament"
    assert data["game_slug"] == "valorant"
    assert data["team_size"] == 5


# =============================================================================
# TeamDTO Tests
# =============================================================================


def test_team_dto_from_model():
    """Test TeamDTO.from_model() with fake team object."""
    fake_team = FakeTournamentModel(
        id=10,
        name="Team Alpha",
        captain_id=100,
        captain_name="Captain Alice",
        member_ids=[100, 101, 102],
        member_names=["Alice", "Bob", "Charlie"],
        game=FakeGameModel(slug="valorant"),
        is_verified=True,
        logo_url="https://example.com/logo.png",
    )

    dto = TeamDTO.from_model(fake_team)

    assert dto.id == 10
    assert dto.name == "Team Alpha"
    assert dto.captain_id == 100
    assert dto.member_ids == [100, 101, 102]
    assert dto.game == "valorant"


def test_team_dto_validation_success():
    """Test TeamDTO.validate() with valid data."""
    dto = TeamDTO(
        id=10,
        name="Team Alpha",
        captain_id=100,
        captain_name="Alice",
        member_ids=[100, 101, 102],
        member_names=["Alice", "Bob", "Charlie"],
        game="valorant",
        is_verified=True,
        logo_url=None,
    )

    errors = dto.validate()
    assert errors == []


def test_team_dto_validation_failures():
    """Test TeamDTO.validate() with invalid data."""
    dto = TeamDTO(
        id=10,
        name="",  # Empty name
        captain_id=999,  # Not in member_ids
        captain_name="Alice",
        member_ids=[100, 101],
        member_names=["Alice", "Bob", "Charlie"],  # Mismatched length
        game="",  # Empty game
        is_verified=False,
        logo_url=None,
    )

    errors = dto.validate()
    assert "name cannot be empty" in errors
    assert "game cannot be empty" in errors
    assert "captain_id must be in member_ids" in errors
    assert "member_ids and member_names must have same length" in errors


# =============================================================================
# PaymentResultDTO Tests
# =============================================================================


def test_payment_result_dto_validation_success():
    """Test PaymentResultDTO.validate() with successful payment."""
    dto = PaymentResultDTO(
        success=True, transaction_id="txn_12345", error=None
    )

    errors = dto.validate()
    assert errors == []


def test_payment_result_dto_validation_failure():
    """Test PaymentResultDTO.validate() with failed payment."""
    dto = PaymentResultDTO(
        success=False, transaction_id=None, error="Insufficient funds"
    )

    errors = dto.validate()
    assert errors == []


def test_payment_result_dto_validation_inconsistent_success():
    """Test PaymentResultDTO.validate() with inconsistent success state."""
    # Success=True but no transaction_id
    dto1 = PaymentResultDTO(success=True, transaction_id=None, error=None)
    errors1 = dto1.validate()
    assert "Successful payment must have transaction_id" in errors1

    # Success=True but has error
    dto2 = PaymentResultDTO(
        success=True, transaction_id="txn_123", error="Some error"
    )
    errors2 = dto2.validate()
    assert "Successful payment should not have error message" in errors2

    # Success=False but no error
    dto3 = PaymentResultDTO(success=False, transaction_id=None, error=None)
    errors3 = dto3.validate()
    assert "Failed payment must have error message" in errors3


# =============================================================================
# EligibilityResultDTO Tests
# =============================================================================


def test_eligibility_result_dto_validation_eligible():
    """Test EligibilityResultDTO.validate() with eligible result."""
    dto = EligibilityResultDTO(is_eligible=True, reasons=[])

    errors = dto.validate()
    assert errors == []


def test_eligibility_result_dto_validation_ineligible():
    """Test EligibilityResultDTO.validate() with ineligible result."""
    dto = EligibilityResultDTO(
        is_eligible=False, reasons=["Age below minimum", "Banned from platform"]
    )

    errors = dto.validate()
    assert errors == []


def test_eligibility_result_dto_validation_inconsistent():
    """Test EligibilityResultDTO.validate() with inconsistent state."""
    # Eligible but has reasons
    dto1 = EligibilityResultDTO(is_eligible=True, reasons=["Some reason"])
    errors1 = dto1.validate()
    assert "Eligible result should not have ineligibility reasons" in errors1

    # Ineligible but no reasons
    dto2 = EligibilityResultDTO(is_eligible=False, reasons=[])
    errors2 = dto2.validate()
    assert "Ineligible result must have at least one reason" in errors2


# =============================================================================
# MatchDTO Tests
# =============================================================================


def test_match_dto_validation_success():
    """Test MatchDTO.validate() with valid data."""
    dto = MatchDTO(
        id=1,
        tournament_id=100,
        team_a_id=10,
        team_b_id=20,
        round_number=1,
        stage="semifinals",
        state="pending",
        scheduled_time=datetime(2025, 6, 1, 14, 0),
        result=None,
    )

    errors = dto.validate()
    assert errors == []


def test_match_dto_validation_failures():
    """Test MatchDTO.validate() with invalid data."""
    dto = MatchDTO(
        id=1,
        tournament_id=100,
        team_a_id=10,
        team_b_id=10,  # Same as team_a_id
        round_number=0,  # Invalid round_number
        stage="",  # Empty stage
        state="invalid_state",  # Invalid state
        scheduled_time=None,
        result=None,
    )

    errors = dto.validate()
    assert "round_number must be positive" in errors
    assert "team_a_id and team_b_id must be different" in errors
    assert "stage cannot be empty" in errors
    assert any("state must be one of" in err for err in errors)


def test_match_dto_validation_completed_without_result():
    """Test MatchDTO.validate() for completed match without result."""
    dto = MatchDTO(
        id=1,
        tournament_id=100,
        team_a_id=10,
        team_b_id=20,
        round_number=1,
        stage="finals",
        state="completed",
        scheduled_time=datetime(2025, 6, 1, 14, 0),
        result=None,  # Missing result for completed match
    )

    errors = dto.validate()
    assert "Completed match must have result" in errors


# =============================================================================
# RegistrationDTO Tests
# =============================================================================


def test_registration_dto_validation_success():
    """Test RegistrationDTO.validate() with valid data."""
    dto = RegistrationDTO(
        id=1,
        tournament_id=100,
        team_id=10,
        user_id=200,
        answers={"favorite_role": "Duelist"},
        status="approved",
    )

    errors = dto.validate()
    assert errors == []


def test_registration_dto_validation_failures():
    """Test RegistrationDTO.validate() with invalid data."""
    dto = RegistrationDTO(
        id=1,
        tournament_id=100,
        team_id=10,
        user_id=200,
        answers=None,  # Invalid answers
        status="invalid_status",  # Invalid status
    )

    errors = dto.validate()
    assert any("answers cannot be None" in err for err in errors)
    assert any("status must be one of" in err for err in errors)


# =============================================================================
# UserProfileDTO Tests
# =============================================================================


def test_user_profile_dto_validation_success():
    """Test UserProfileDTO.validate() with valid data."""
    dto = UserProfileDTO(
        email="test@example.com",
        email_verified=True,
        phone="+1234567890",
        phone_verified=True,
        discord="user#1234",
        riot_id="Player#NA1",
        steam_id="76561198000000000",
        pubg_mobile_id="5551234567",
        age=25,
        region="NA",
    )

    errors = dto.validate()
    assert errors == []


def test_user_profile_dto_validation_failures():
    """Test UserProfileDTO.validate() with invalid data."""
    dto = UserProfileDTO(
        email="",  # Empty email
        email_verified=False,
        phone=None,
        phone_verified=False,
        discord=None,
        riot_id=None,
        steam_id=None,
        pubg_mobile_id=None,
        age=-5,  # Invalid age
        region=None,
    )

    errors = dto.validate()
    assert "email cannot be empty" in errors
    assert "age must be positive" in errors


# =============================================================================
# StageDTO Tests
# =============================================================================


def test_stage_dto_validation_success():
    """Test StageDTO.validate() with valid data."""
    dto = StageDTO(
        id=1,
        name="Group Stage",
        type="group",
        order=1,
        config={"groups": 4},
    )

    errors = dto.validate()
    assert errors == []


def test_stage_dto_validation_failures():
    """Test StageDTO.validate() with invalid data."""
    dto = StageDTO(
        id=1,
        name="",  # Empty name
        type="invalid_type",  # Invalid type
        order=0,  # Invalid order
        config=None,  # Invalid config
    )

    errors = dto.validate()
    assert "name cannot be empty" in errors
    assert any("type must be one of" in err for err in errors)
    assert "order must be positive" in errors
    assert any("config cannot be None" in err for err in errors)


# =============================================================================
# GamePlayerIdentityConfigDTO Tests
# =============================================================================


def test_game_identity_config_dto_validation_success():
    """Test GamePlayerIdentityConfigDTO.validate() with valid data."""
    dto = GamePlayerIdentityConfigDTO(
        field_name="riot_id",
        display_label="Riot ID",
        validation_pattern=r"^.+#.+$",
        is_required=True,
        is_immutable=False,
        help_text="Enter your Riot ID (e.g., Player#NA1)",
        placeholder="Player#NA1",
    )

    errors = dto.validate()
    assert errors == []


def test_game_identity_config_dto_validation_failures():
    """Test GamePlayerIdentityConfigDTO.validate() with invalid data."""
    dto = GamePlayerIdentityConfigDTO(
        field_name="",  # Empty field_name
        display_label="",  # Empty display_label
        validation_pattern=None,
        is_required=False,
        is_immutable=False,
        help_text="",  # Empty help_text
        placeholder="",
    )

    errors = dto.validate()
    assert "field_name cannot be empty" in errors
    assert "display_label cannot be empty" in errors
    assert "help_text cannot be empty" in errors


# =============================================================================
# Framework Independence Tests
# =============================================================================


def test_dtos_have_no_django_imports():
    """
    Verify that DTO modules do not import Django ORM models.

    This ensures DTOs remain framework-independent and can be used in
    non-Django contexts (CLIs, background workers, etc.).
    """
    import sys

    dto_modules = [
        "apps.tournament_ops.dtos.tournament",
        "apps.tournament_ops.dtos.team",
        "apps.tournament_ops.dtos.user",
        "apps.tournament_ops.dtos.match",
        "apps.tournament_ops.dtos.registration",
        "apps.tournament_ops.dtos.payment",
        "apps.tournament_ops.dtos.eligibility",
        "apps.tournament_ops.dtos.stage",
        "apps.tournament_ops.dtos.game_identity",
    ]

    for module_name in dto_modules:
        if module_name in sys.modules:
            module = sys.modules[module_name]
            # Check that no django.db or apps.* models are imported
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if hasattr(attr, "__module__"):
                    assert "django.db" not in attr.__module__, (
                        f"{module_name} imports {attr_name} from {attr.__module__}"
                    )
                    # Allow imports from apps.tournament_ops.dtos only
                    if "apps." in attr.__module__:
                        assert "apps.tournament_ops.dtos" in attr.__module__, (
                            f"{module_name} imports {attr_name} from {attr.__module__}"
                        )
