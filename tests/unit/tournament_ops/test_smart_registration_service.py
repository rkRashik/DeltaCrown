"""
Unit tests for SmartRegistrationService (Phase 5).

Tests smart registration workflows with mocked adapters (no ORM):
- Draft creation
- Form generation
- Answer submission
- Rule evaluation
- Auto-processing

Reference: Documents/Modify_TournamentApp/Workplan/CLEANUP_AND_TESTING_PART_6.md §9.5
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from apps.tournament_ops.services.smart_registration_service import SmartRegistrationService
from apps.tournament_ops.dtos import (
    RegistrationDTO,
    RegistrationQuestionDTO,
    RegistrationRuleDTO,
    RegistrationDraftDTO,
    TournamentDTO,
    UserProfileDTO,
    GamePlayerIdentityConfigDTO,
)
from apps.tournament_ops.exceptions import InvalidRegistrationStateError


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_smart_reg_adapter():
    """Mock SmartRegistrationAdapter."""
    return Mock()


@pytest.fixture
def mock_registration_service():
    """Mock RegistrationService."""
    return Mock()


@pytest.fixture
def mock_team_adapter():
    """Mock TeamAdapter."""
    return Mock()


@pytest.fixture
def mock_user_adapter():
    """Mock UserAdapter."""
    return Mock()


@pytest.fixture
def mock_game_adapter():
    """Mock GameAdapter."""
    return Mock()


@pytest.fixture
def mock_tournament_adapter():
    """Mock TournamentAdapter."""
    return Mock()


@pytest.fixture
def mock_event_bus():
    """Mock EventBus."""
    with patch('apps.tournament_ops.services.smart_registration_service.get_event_bus') as mock:
        event_bus = Mock()
        mock.return_value = event_bus
        yield event_bus


@pytest.fixture
def smart_reg_service(
    mock_smart_reg_adapter,
    mock_registration_service,
    mock_team_adapter,
    mock_user_adapter,
    mock_game_adapter,
    mock_tournament_adapter,
    mock_event_bus,
):
    """Create SmartRegistrationService with mocked dependencies."""
    return SmartRegistrationService(
        smart_reg_adapter=mock_smart_reg_adapter,
        registration_service=mock_registration_service,
        team_adapter=mock_team_adapter,
        user_adapter=mock_user_adapter,
        game_adapter=mock_game_adapter,
        tournament_adapter=mock_tournament_adapter,
    )


@pytest.fixture
def sample_tournament_dto():
    """Sample TournamentDTO."""
    dto = TournamentDTO(
        id=100,
        name='Test Tournament',
        game_slug='valorant',
        stage='registration',
        team_size=5,
        max_teams=16,
        status='open',
        start_time=datetime.now() + timedelta(days=7),
        ruleset={},
    )
    # Add game_id as dynamic attribute for testing
    dto.game_id = 1
    return dto


@pytest.fixture
def sample_registration_dto():
    """Sample RegistrationDTO."""
    return RegistrationDTO(
        id=1,
        tournament_id=100,
        team_id=5,
        user_id=10,
        answers={},
        status='submitted',
    )


@pytest.fixture
def sample_questions():
    """Sample registration questions."""
    return [
        RegistrationQuestionDTO(
            id=1,
            slug='rank',
            text='What is your rank?',
            type='select',
            scope='player',
            is_required=True,
            order=1,
            config={'options': ['Iron', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Immortal', 'Radiant']},
        ),
        RegistrationQuestionDTO(
            id=2,
            slug='discord',
            text='Discord username',
            type='text',
            scope='player',
            is_required=False,
            order=2,
            config={},
        ),
    ]


# ==============================================================================
# create_draft_registration() Tests
# ==============================================================================


def test_create_draft_registration_creates_draft_and_publishes_event(
    smart_reg_service,
    mock_smart_reg_adapter,
    mock_tournament_adapter,
    mock_event_bus,
    sample_tournament_dto,
):
    """Test creating a draft creates record and publishes event."""
    # Arrange
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto
    
    draft_dto = RegistrationDraftDTO(
        id=1,
        uuid='abc-123',
        registration_number='VCT-2025-001234',
        user_id=10,
        tournament_id=100,
        team_id=None,
        form_data={},
        auto_filled_fields=[],
        locked_fields=[],
        current_step='player_info',
        completion_percentage=0,
        submitted=False,
        registration_id=None,
        created_at=datetime.now(),
        last_saved_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=7),
    )
    mock_smart_reg_adapter.create_draft.return_value = draft_dto
    
    # Act
    result = smart_reg_service.create_draft_registration(
        tournament_id=100,
        user_id=10,
        team_id=None,
    )
    
    # Assert
    assert result.uuid == 'abc-123'
    assert result.registration_number == 'VCT-2025-001234'
    mock_smart_reg_adapter.create_draft.assert_called_once()
    mock_event_bus.publish.assert_called_once()
    
    # Verify event
    event = mock_event_bus.publish.call_args[0][0]
    assert event.name == 'RegistrationDraftCreatedEvent'
    assert event.payload['draft_uuid'] == 'abc-123'


# ==============================================================================
# get_registration_form() Tests
# ==============================================================================


def test_get_registration_form_merges_questions_and_autofill(
    smart_reg_service,
    mock_smart_reg_adapter,
    mock_tournament_adapter,
    mock_user_adapter,
    mock_game_adapter,
    sample_tournament_dto,
    sample_questions,
):
    """Test form generation merges questions with auto-fill data."""
    # Arrange
    mock_tournament_adapter.get_tournament.return_value = sample_tournament_dto
    mock_smart_reg_adapter.get_questions_for_tournament.return_value = sample_questions
    
    user_profile = UserProfileDTO(
        email='user@example.com',
        email_verified=True,
        phone='123456789',
        phone_verified=False,
        discord='user#1234',
        riot_id='Player#TAG',
        steam_id=None,
        pubg_mobile_id=None,
        age=None,
        region=None,
    )
    mock_user_adapter.get_profile_data.return_value = user_profile
    
    game_configs = [
        GamePlayerIdentityConfigDTO(
            field_name='riot_id',
            display_label='Riot ID',
            validation_pattern=r'^[\w]+#[\w]+$',
            is_required=True,
            is_immutable=False,
            help_text='Your Valorant Riot ID',
            placeholder='Player#TAG',
        )
    ]
    mock_game_adapter.get_identity_fields.return_value = game_configs
    
    # Act
    result = smart_reg_service.get_registration_form(
        tournament_id=100,
        user_id=10,
        team_id=None,
    )
    
    # Assert
    assert len(result['questions']) == 2
    assert 'email' in result['auto_fill_data']
    assert result['auto_fill_data']['email'] == 'user@example.com'
    assert 'email' in result['locked_fields']  # Email is verified


# ==============================================================================
# submit_answers() Tests
# ==============================================================================


def test_submit_answers_validates_and_saves(
    smart_reg_service,
    mock_smart_reg_adapter,
    mock_registration_service,
    mock_event_bus,
    sample_registration_dto,
    sample_questions,
):
    """Test submitting answers validates and saves via adapter."""
    # Arrange
    mock_registration_service.get_registration.return_value = sample_registration_dto
    mock_smart_reg_adapter.get_questions_for_tournament.return_value = sample_questions
    
    answers = {
        'rank': 'Diamond',
        'discord': 'player#1234',
    }
    
    # Act
    result = smart_reg_service.submit_answers(
        registration_id=1,
        answers=answers,
    )
    
    # Assert
    assert result.id == 1
    mock_smart_reg_adapter.save_answers.assert_called_once_with(1, answers)
    mock_event_bus.publish.assert_called_once()
    
    event = mock_event_bus.publish.call_args[0][0]
    assert event.name == 'RegistrationAnswersSubmittedEvent'


def test_submit_answers_raises_if_required_missing(
    smart_reg_service,
    mock_smart_reg_adapter,
    mock_registration_service,
    sample_registration_dto,
    sample_questions,
):
    """Test submitting answers without required field raises error."""
    # Arrange
    mock_registration_service.get_registration.return_value = sample_registration_dto
    mock_smart_reg_adapter.get_questions_for_tournament.return_value = sample_questions
    
    answers = {
        'discord': 'player#1234',
        # Missing 'rank' (required)
    }
    
    # Act & Assert
    with pytest.raises(InvalidRegistrationStateError) as exc_info:
        smart_reg_service.submit_answers(registration_id=1, answers=answers)
    
    assert 'required' in str(exc_info.value).lower()


def test_submit_answers_validates_type(
    smart_reg_service,
    mock_smart_reg_adapter,
    mock_registration_service,
    sample_registration_dto,
):
    """Test answer validation checks type constraints."""
    # Arrange
    mock_registration_service.get_registration.return_value = sample_registration_dto
    
    questions = [
        RegistrationQuestionDTO(
            id=1,
            slug='age',
            text='Age',
            type='number',
            scope='player',
            is_required=True,
            order=1,
            config={'min': 13, 'max': 100},
        )
    ]
    mock_smart_reg_adapter.get_questions_for_tournament.return_value = questions
    
    answers = {'age': 10}  # Below minimum
    
    # Act & Assert
    with pytest.raises(InvalidRegistrationStateError) as exc_info:
        smart_reg_service.submit_answers(registration_id=1, answers=answers)
    
    assert 'at least 13' in str(exc_info.value)


# ==============================================================================
# evaluate_registration() Tests
# ==============================================================================


def test_evaluate_registration_auto_approves_when_rule_matches(
    smart_reg_service,
    mock_smart_reg_adapter,
    mock_registration_service,
    mock_user_adapter,
    mock_event_bus,
    sample_registration_dto,
):
    """Test evaluation auto-approves when approval rule matches."""
    # Arrange
    mock_registration_service.get_registration.return_value = sample_registration_dto
    mock_smart_reg_adapter.get_answers.return_value = {'rank': 'Radiant'}
    
    user_profile = UserProfileDTO(
        email='user@example.com',
        email_verified=True,
        phone='123456789',
        phone_verified=True,
        discord=None,
        riot_id=None,
        steam_id=None,
        pubg_mobile_id=None,
        age=None,
        region=None,
    )
    mock_user_adapter.get_profile_data.return_value = user_profile
    
    rule = RegistrationRuleDTO(
        id=1,
        tournament_id=100,
        name='Auto-approve Radiant players',
        rule_type='auto_approve',
        condition={'rank': 'Radiant', 'email_verified': True},
        priority=1,
        is_active=True,
        reason_template='Auto-approved (verified Radiant player)',
    )
    mock_smart_reg_adapter.get_rules_for_tournament.return_value = [rule]
    
    # Act
    result = smart_reg_service.evaluate_registration(registration_id=1)
    
    # Assert
    assert result.status == 'auto_approved'
    mock_event_bus.publish.assert_called_once()
    
    event = mock_event_bus.publish.call_args[0][0]
    assert event.name == 'RegistrationAutoApprovedEvent'
    assert event.payload['rule_id'] == 1


def test_evaluate_registration_auto_rejects_when_reject_rule_matches(
    smart_reg_service,
    mock_smart_reg_adapter,
    mock_registration_service,
    mock_user_adapter,
    mock_event_bus,
    sample_registration_dto,
):
    """Test evaluation auto-rejects when rejection rule matches."""
    # Arrange
    mock_registration_service.get_registration.return_value = sample_registration_dto
    mock_smart_reg_adapter.get_answers.return_value = {'rank': 'Iron', 'age': 12}
    
    user_profile = UserProfileDTO(
        email='user@example.com',
        email_verified=False,
        phone='123456789',
        phone_verified=False,
        discord=None,
        riot_id=None,
        steam_id=None,
        pubg_mobile_id=None,
        age=None,
        region=None,
    )
    mock_user_adapter.get_profile_data.return_value = user_profile
    
    rule = RegistrationRuleDTO(
        id=2,
        tournament_id=100,
        name='Reject underage unverified',
        rule_type='auto_reject',
        condition={'age': {'lte': 12}},
        priority=1,
        is_active=True,
        reason_template='Registration rejected (age requirement not met)',
    )
    mock_smart_reg_adapter.get_rules_for_tournament.return_value = [rule]
    
    # Act
    result = smart_reg_service.evaluate_registration(registration_id=1)
    
    # Assert
    assert result.status == 'rejected'
    mock_event_bus.publish.assert_called_once()
    
    event = mock_event_bus.publish.call_args[0][0]
    assert event.name == 'RegistrationAutoRejectedEvent'


def test_evaluate_registration_flags_for_review_when_no_rule_matches(
    smart_reg_service,
    mock_smart_reg_adapter,
    mock_registration_service,
    mock_user_adapter,
    mock_event_bus,
    sample_registration_dto,
):
    """Test evaluation flags for review when no rules match."""
    # Arrange
    mock_registration_service.get_registration.return_value = sample_registration_dto
    mock_smart_reg_adapter.get_answers.return_value = {'rank': 'Gold'}
    
    user_profile = UserProfileDTO(
        email='user@example.com',
        email_verified=True,
        phone='123456789',
        phone_verified=False,
        discord=None,
        riot_id=None,
        steam_id=None,
        pubg_mobile_id=None,
        age=None,
        region=None,
    )
    mock_user_adapter.get_profile_data.return_value = user_profile
    
    # No matching rules
    mock_smart_reg_adapter.get_rules_for_tournament.return_value = []
    
    # Act
    result = smart_reg_service.evaluate_registration(registration_id=1)
    
    # Assert
    assert result.status == 'needs_review'
    mock_event_bus.publish.assert_called_once()
    
    event = mock_event_bus.publish.call_args[0][0]
    assert event.name == 'RegistrationFlaggedForReviewEvent'
    assert event.payload['rule_id'] is None


# ==============================================================================
# auto_process_registration() Tests
# ==============================================================================


def test_auto_process_registration_happy_path(
    smart_reg_service,
    mock_smart_reg_adapter,
    mock_registration_service,
    mock_user_adapter,
    mock_event_bus,
    sample_registration_dto,
    sample_questions,
):
    """Test auto-processing creates registration, saves answers, and evaluates."""
    # Arrange
    mock_registration_service.create_registration.return_value = sample_registration_dto
    mock_registration_service.get_registration.return_value = sample_registration_dto
    mock_smart_reg_adapter.get_questions_for_tournament.return_value = sample_questions
    mock_smart_reg_adapter.get_answers.return_value = {'rank': 'Diamond'}
    
    user_profile = UserProfileDTO(
        email='user@example.com',
        email_verified=True,
        phone='123456789',
        phone_verified=True,
        discord=None,
        riot_id=None,
        steam_id=None,
        pubg_mobile_id=None,
        age=None,
        region=None,
    )
    mock_user_adapter.get_profile_data.return_value = user_profile
    
    rule = RegistrationRuleDTO(
        id=1,
        tournament_id=100,
        name='Auto-approve Diamond+',
        rule_type='auto_approve',
        condition={'rank': {'in': ['Diamond', 'Immortal', 'Radiant']}},
        priority=1,
        is_active=True,
    )
    mock_smart_reg_adapter.get_rules_for_tournament.return_value = [rule]
    
    # Act
    registration, decision = smart_reg_service.auto_process_registration(
        tournament_id=100,
        user_id=10,
        team_id=None,
        answers={'rank': 'Diamond', 'discord': 'player#1234'},
    )
    
    # Assert
    assert registration.id == 1
    assert decision == 'auto_approved'
    mock_registration_service.create_registration.assert_called_once()
    mock_smart_reg_adapter.save_answers.assert_called_once()


def test_auto_process_registration_rejected(
    smart_reg_service,
    mock_smart_reg_adapter,
    mock_registration_service,
    mock_user_adapter,
    mock_event_bus,
    sample_registration_dto,
    sample_questions,
):
    """Test auto-processing with rejection rule."""
    # Arrange
    mock_registration_service.create_registration.return_value = sample_registration_dto
    mock_registration_service.get_registration.return_value = sample_registration_dto
    mock_smart_reg_adapter.get_questions_for_tournament.return_value = sample_questions
    mock_smart_reg_adapter.get_answers.return_value = {'rank': 'Iron'}
    
    user_profile = UserProfileDTO(
        email='user@example.com',
        email_verified=False,
        phone='123456789',
        phone_verified=False,
        discord=None,
        riot_id=None,
        steam_id=None,
        pubg_mobile_id=None,
        age=None,
        region=None,
    )
    mock_user_adapter.get_profile_data.return_value = user_profile
    
    rule = RegistrationRuleDTO(
        id=2,
        tournament_id=100,
        name='Reject unverified low-rank',
        rule_type='auto_reject',
        condition={'rank': 'Iron', 'email_verified': False},
        priority=1,
        is_active=True,
    )
    mock_smart_reg_adapter.get_rules_for_tournament.return_value = [rule]
    
    # Act
    registration, decision = smart_reg_service.auto_process_registration(
        tournament_id=100,
        user_id=10,
        team_id=None,
        answers={'rank': 'Iron'},
    )
    
    # Assert
    assert decision == 'auto_rejected'
