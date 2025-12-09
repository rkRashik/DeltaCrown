"""
Staffing Service Tests - Phase 7, Epic 7.3

Tests for StaffingService business logic.

Reference: Phase 7, Epic 7.3 - Staff & Referee Role System
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from apps.tournament_ops.services.staffing_service import StaffingService
from apps.tournament_ops.dtos.staffing import (
    StaffRoleDTO,
    TournamentStaffAssignmentDTO,
    MatchRefereeAssignmentDTO,
    StaffLoadDTO,
)


@pytest.fixture
def mock_staffing_adapter():
    """Mock StaffingAdapter for testing."""
    return Mock()


@pytest.fixture
def mock_event_bus():
    """Mock EventBus for testing."""
    return Mock()


@pytest.fixture
def staffing_service(mock_staffing_adapter, mock_event_bus):
    """Create StaffingService with mocks."""
    return StaffingService(
        staffing_adapter=mock_staffing_adapter,
        event_bus=mock_event_bus
    )


@pytest.fixture
def sample_role_dto():
    """Sample StaffRoleDTO for testing."""
    return StaffRoleDTO(
        role_id=1,
        name="Head Admin",
        code="HEAD_ADMIN",
        description="Main tournament administrator",
        capabilities={
            "can_schedule": True,
            "can_resolve_disputes": True,
            "can_finalize_results": True
        },
        is_referee_role=False,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_referee_role_dto():
    """Sample referee StaffRoleDTO for testing."""
    return StaffRoleDTO(
        role_id=2,
        name="Referee",
        code="REFEREE",
        description="Match referee",
        capabilities={
            "can_referee_matches": True
        },
        is_referee_role=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_staff_assignment_dto(sample_role_dto):
    """Sample TournamentStaffAssignmentDTO for testing."""
    return TournamentStaffAssignmentDTO(
        assignment_id=1,
        tournament_id=100,
        tournament_name="Test Tournament",
        user_id=50,
        username="admin_user",
        user_email="admin@test.com",
        role=sample_role_dto,
        is_active=True,
        stage_id=None,
        stage_name=None,
        assigned_by_user_id=1,
        assigned_by_username="organizer",
        assigned_at=datetime.now(),
        notes=""
    )


@pytest.fixture
def sample_referee_assignment_dto(sample_staff_assignment_dto):
    """Sample referee TournamentStaffAssignmentDTO for testing."""
    referee_role = StaffRoleDTO(
        role_id=2,
        name="Referee",
        code="REFEREE",
        description="Match referee",
        capabilities={"can_referee_matches": True},
        is_referee_role=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    return TournamentStaffAssignmentDTO(
        assignment_id=2,
        tournament_id=100,
        tournament_name="Test Tournament",
        user_id=51,
        username="referee_user",
        user_email="referee@test.com",
        role=referee_role,
        is_active=True,
        stage_id=None,
        stage_name=None,
        assigned_by_user_id=1,
        assigned_by_username="organizer",
        assigned_at=datetime.now(),
        notes=""
    )


# ============================================================================
# Staff Role Query Tests
# ============================================================================

def test_get_all_staff_roles(staffing_service, mock_staffing_adapter, sample_role_dto):
    """Test get_all_staff_roles returns all roles."""
    mock_staffing_adapter.get_staff_roles.return_value = [sample_role_dto]
    
    roles = staffing_service.get_all_staff_roles()
    
    assert len(roles) == 1
    assert roles[0].code == "HEAD_ADMIN"
    mock_staffing_adapter.get_staff_roles.assert_called_once()


def test_get_referee_roles(staffing_service, mock_staffing_adapter, sample_referee_role_dto):
    """Test get_referee_roles filters to referee roles only."""
    mock_staffing_adapter.get_staff_roles.return_value = [sample_referee_role_dto]
    
    roles = staffing_service.get_referee_roles()
    
    assert len(roles) == 1
    assert roles[0].is_referee_role is True
    mock_staffing_adapter.get_staff_roles.assert_called_once_with(is_referee_role=True)


def test_get_role_by_code(staffing_service, mock_staffing_adapter, sample_role_dto):
    """Test get_role_by_code returns correct role."""
    mock_staffing_adapter.get_staff_role_by_code.return_value = sample_role_dto
    
    role = staffing_service.get_role_by_code("HEAD_ADMIN")
    
    assert role.code == "HEAD_ADMIN"
    mock_staffing_adapter.get_staff_role_by_code.assert_called_once_with("HEAD_ADMIN")


# ============================================================================
# Tournament Staff Assignment Tests
# ============================================================================

def test_assign_staff_to_tournament_success(
    staffing_service,
    mock_staffing_adapter,
    mock_event_bus,
    sample_role_dto,
    sample_staff_assignment_dto
):
    """Test successful staff assignment."""
    mock_staffing_adapter.get_staff_role_by_code.return_value = sample_role_dto
    mock_staffing_adapter.assign_staff_to_tournament.return_value = sample_staff_assignment_dto
    
    assignment = staffing_service.assign_staff_to_tournament(
        tournament_id=100,
        user_id=50,
        role_code="HEAD_ADMIN",
        assigned_by_user_id=1
    )
    
    assert assignment.assignment_id == 1
    assert assignment.user_id == 50
    assert assignment.role.code == "HEAD_ADMIN"
    mock_event_bus.publish.assert_called_once()  # Event published


def test_assign_staff_invalid_role(staffing_service, mock_staffing_adapter):
    """Test assign_staff raises error for invalid role."""
    mock_staffing_adapter.get_staff_role_by_code.return_value = None
    
    with pytest.raises(ValueError, match="Invalid staff role"):
        staffing_service.assign_staff_to_tournament(
            tournament_id=100,
            user_id=50,
            role_code="INVALID_ROLE",
            assigned_by_user_id=1
        )


def test_remove_staff_from_tournament_success(
    staffing_service,
    mock_staffing_adapter,
    mock_event_bus,
    sample_staff_assignment_dto
):
    """Test successful staff removal."""
    sample_staff_assignment_dto.is_active = True
    updated_dto = sample_staff_assignment_dto
    updated_dto.is_active = False
    
    mock_staffing_adapter.get_staff_assignment_by_id.return_value = sample_staff_assignment_dto
    mock_staffing_adapter.get_referee_assignments_for_tournament.return_value = []
    mock_staffing_adapter.update_staff_assignment_status.return_value = updated_dto
    
    result = staffing_service.remove_staff_from_tournament(assignment_id=1)
    
    assert result.is_active is False
    mock_event_bus.publish.assert_called_once()  # Event published


def test_remove_staff_not_found(staffing_service, mock_staffing_adapter):
    """Test remove_staff raises error if assignment not found."""
    mock_staffing_adapter.get_staff_assignment_by_id.return_value = None
    
    with pytest.raises(ValueError, match="not found"):
        staffing_service.remove_staff_from_tournament(assignment_id=999)


def test_remove_staff_with_active_referee_assignments(
    staffing_service,
    mock_staffing_adapter,
    sample_referee_assignment_dto
):
    """Test remove_staff raises error if referee has active matches."""
    # Make this a referee assignment
    sample_referee_assignment_dto.role.is_referee_role = True
    
    # Mock referee has active match assignments
    mock_staffing_adapter.get_staff_assignment_by_id.return_value = sample_referee_assignment_dto
    mock_staffing_adapter.get_referee_assignments_for_tournament.return_value = [
        Mock(staff_assignment=Mock(assignment_id=2))
    ]
    
    with pytest.raises(ValueError, match="active referee assignments"):
        staffing_service.remove_staff_from_tournament(assignment_id=2)


def test_get_tournament_staff(staffing_service, mock_staffing_adapter, sample_staff_assignment_dto):
    """Test get_tournament_staff delegates to adapter."""
    mock_staffing_adapter.get_staff_assignments_for_tournament.return_value = [
        sample_staff_assignment_dto
    ]
    
    staff = staffing_service.get_tournament_staff(tournament_id=100)
    
    assert len(staff) == 1
    assert staff[0].tournament_id == 100
    mock_staffing_adapter.get_staff_assignments_for_tournament.assert_called_once()


# ============================================================================
# Match Referee Assignment Tests
# ============================================================================

def test_assign_referee_to_match_success(
    staffing_service,
    mock_staffing_adapter,
    mock_event_bus,
    sample_referee_assignment_dto
):
    """Test successful referee assignment to match."""
    match_ref_dto = Mock(
        assignment_id=10,
        match_id=200,
        tournament_id=100,
        stage_id=5,
        round_number=1,
        match_number=1,
        staff_assignment=sample_referee_assignment_dto,
        is_primary=True,
        assigned_by_user_id=1,
        assigned_by_username="organizer",
        assigned_at=datetime.now(),
        notes=""
    )
    
    mock_staffing_adapter.get_staff_assignment_by_id.return_value = sample_referee_assignment_dto
    mock_staffing_adapter.calculate_staff_load.return_value = []  # No load
    mock_staffing_adapter.assign_referee_to_match.return_value = match_ref_dto
    
    assignment, warning = staffing_service.assign_referee_to_match(
        match_id=200,
        staff_assignment_id=2,
        assigned_by_user_id=1,
        is_primary=True
    )
    
    assert assignment.match_id == 200
    assert assignment.is_primary is True
    assert warning is None  # No warning
    mock_event_bus.publish.assert_called_once()


def test_assign_referee_staff_not_found(staffing_service, mock_staffing_adapter):
    """Test assign_referee raises error if staff assignment not found."""
    mock_staffing_adapter.get_staff_assignment_by_id.return_value = None
    
    with pytest.raises(ValueError, match="not found"):
        staffing_service.assign_referee_to_match(
            match_id=200,
            staff_assignment_id=999,
            assigned_by_user_id=1
        )


def test_assign_referee_not_referee_role(
    staffing_service,
    mock_staffing_adapter,
    sample_staff_assignment_dto
):
    """Test assign_referee raises error if staff not referee role."""
    # Non-referee role
    sample_staff_assignment_dto.role.is_referee_role = False
    mock_staffing_adapter.get_staff_assignment_by_id.return_value = sample_staff_assignment_dto
    
    with pytest.raises(ValueError, match="not a referee role"):
        staffing_service.assign_referee_to_match(
            match_id=200,
            staff_assignment_id=1,
            assigned_by_user_id=1
        )


def test_assign_referee_inactive_staff(
    staffing_service,
    mock_staffing_adapter,
    sample_referee_assignment_dto
):
    """Test assign_referee raises error if staff assignment inactive."""
    sample_referee_assignment_dto.is_active = False
    mock_staffing_adapter.get_staff_assignment_by_id.return_value = sample_referee_assignment_dto
    
    with pytest.raises(ValueError, match="inactive"):
        staffing_service.assign_referee_to_match(
            match_id=200,
            staff_assignment_id=2,
            assigned_by_user_id=1
        )


def test_assign_referee_with_overload_warning(
    staffing_service,
    mock_staffing_adapter,
    sample_referee_assignment_dto
):
    """Test assign_referee returns warning when referee overloaded."""
    match_ref_dto = Mock(
        assignment_id=10,
        match_id=200,
        tournament_id=100,
        stage_id=5,
        round_number=1,
        match_number=1,
        staff_assignment=sample_referee_assignment_dto,
        is_primary=True,
        assigned_by_user_id=1,
        assigned_by_username="organizer",
        assigned_at=datetime.now(),
        notes=""
    )
    
    # Mock overloaded staff
    overloaded_load = Mock(
        is_overloaded=True,
        load_percentage=90.0,
        upcoming_matches=12
    )
    
    mock_staffing_adapter.get_staff_assignment_by_id.return_value = sample_referee_assignment_dto
    mock_staffing_adapter.calculate_staff_load.return_value = [
        Mock(staff_assignment=Mock(assignment_id=2), **vars(overloaded_load))
    ]
    mock_staffing_adapter.assign_referee_to_match.return_value = match_ref_dto
    
    assignment, warning = staffing_service.assign_referee_to_match(
        match_id=200,
        staff_assignment_id=2,
        assigned_by_user_id=1,
        check_load=True
    )
    
    assert warning is not None
    assert "overloaded" in warning.lower()


def test_unassign_referee_from_match(staffing_service, mock_staffing_adapter, mock_event_bus):
    """Test successful referee unassignment."""
    ref_assignment = Mock(
        assignment_id=10,
        match_id=200,
        tournament_id=100,
        staff_assignment=Mock(user_id=51, username="referee_user"),
        is_primary=True
    )
    
    mock_staffing_adapter.get_referee_assignments_for_tournament.return_value = [ref_assignment]
    
    staffing_service.unassign_referee_from_match(referee_assignment_id=10)
    
    mock_staffing_adapter.unassign_referee_from_match.assert_called_once_with(10)
    mock_event_bus.publish.assert_called_once()


def test_get_match_referees(staffing_service, mock_staffing_adapter):
    """Test get_match_referees delegates to adapter."""
    ref_assignment = Mock(match_id=200)
    mock_staffing_adapter.get_referee_assignments_for_match.return_value = [ref_assignment]
    
    referees = staffing_service.get_match_referees(match_id=200)
    
    assert len(referees) == 1
    assert referees[0].match_id == 200
    mock_staffing_adapter.get_referee_assignments_for_match.assert_called_once_with(200)


# ============================================================================
# Staff Load Management Tests
# ============================================================================

def test_calculate_staff_load(staffing_service, mock_staffing_adapter):
    """Test calculate_staff_load delegates to adapter."""
    load_dto = Mock(
        total_matches_assigned=8,
        upcoming_matches=5,
        is_overloaded=False,
        load_percentage=80.0
    )
    
    mock_staffing_adapter.calculate_staff_load.return_value = [load_dto]
    
    loads = staffing_service.calculate_staff_load(tournament_id=100)
    
    assert len(loads) == 1
    assert loads[0].total_matches_assigned == 8
    mock_staffing_adapter.calculate_staff_load.assert_called_once_with(
        tournament_id=100,
        stage_id=None
    )


def test_get_least_loaded_referee(
    staffing_service,
    mock_staffing_adapter,
    sample_referee_assignment_dto
):
    """Test get_least_loaded_referee returns referee with lowest load."""
    load1 = Mock(
        staff_assignment=Mock(assignment_id=1, **vars(sample_referee_assignment_dto)),
        load_percentage=80.0
    )
    load2 = Mock(
        staff_assignment=Mock(assignment_id=2, **vars(sample_referee_assignment_dto)),
        load_percentage=50.0  # Least loaded
    )
    
    mock_staffing_adapter.calculate_staff_load.return_value = [load1, load2]
    
    least_loaded = staffing_service.get_least_loaded_referee(tournament_id=100)
    
    # Should return second one (50% load)
    assert least_loaded is not None
