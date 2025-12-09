"""
Staffing Adapter Tests - Phase 7, Epic 7.3

Tests for StaffingAdapter data access layer.

Reference: Phase 7, Epic 7.3 - Staff & Referee Role System
"""

import pytest
from datetime import datetime

from apps.tournaments.models import StaffRole, TournamentStaffAssignment, MatchRefereeAssignment
from apps.tournament_ops.adapters.staffing_adapter import StaffingAdapter


@pytest.mark.django_db
class TestStaffingAdapter:
    """Test suite for StaffingAdapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create StaffingAdapter instance."""
        return StaffingAdapter()
    
    @pytest.fixture
    def sample_role(self, db):
        """Create a sample staff role."""
        return StaffRole.objects.create(
            name="Head Admin",
            code="HEAD_ADMIN",
            description="Main tournament administrator",
            capabilities={
                "can_schedule": True,
                "can_resolve_disputes": True,
                "can_finalize_results": True
            },
            is_referee_role=False
        )
    
    @pytest.fixture
    def referee_role(self, db):
        """Create a referee role."""
        return StaffRole.objects.create(
            name="Referee",
            code="REFEREE",
            description="Match referee",
            capabilities={
                "can_referee_matches": True
            },
            is_referee_role=True
        )
    
    # ========================================================================
    # Staff Role Tests
    # ========================================================================
    
    def test_get_staff_roles_all(self, adapter, sample_role, referee_role):
        """Test get_staff_roles returns all roles."""
        roles = adapter.get_staff_roles()
        
        assert len(roles) == 2
        role_codes = [r.code for r in roles]
        assert "HEAD_ADMIN" in role_codes
        assert "REFEREE" in role_codes
    
    def test_get_staff_roles_filter_referee(self, adapter, sample_role, referee_role):
        """Test get_staff_roles filters by is_referee_role."""
        roles = adapter.get_staff_roles(is_referee_role=True)
        
        assert len(roles) == 1
        assert roles[0].code == "REFEREE"
        assert roles[0].is_referee_role is True
    
    def test_get_staff_role_by_code(self, adapter, sample_role):
        """Test get_staff_role_by_code returns correct role."""
        role_dto = adapter.get_staff_role_by_code("HEAD_ADMIN")
        
        assert role_dto is not None
        assert role_dto.code == "HEAD_ADMIN"
        assert role_dto.name == "Head Admin"
    
    def test_get_staff_role_by_code_not_found(self, adapter):
        """Test get_staff_role_by_code returns None if not found."""
        role_dto = adapter.get_staff_role_by_code("NONEXISTENT")
        
        assert role_dto is None
    
    # ========================================================================
    # Staff Assignment Tests
    # ========================================================================
    
    def test_assign_staff_to_tournament(self, adapter, sample_role, django_user_model, tournament):
        """Test assign_staff_to_tournament creates assignment."""
        user = django_user_model.objects.create(username="staff_user")
        assigner = django_user_model.objects.create(username="organizer")
        
        assignment_dto = adapter.assign_staff_to_tournament(
            tournament_id=tournament.id,
            user_id=user.id,
            role_code="HEAD_ADMIN",
            assigned_by_user_id=assigner.id
        )
        
        assert assignment_dto is not None
        assert assignment_dto.tournament_id == tournament.id
        assert assignment_dto.user_id == user.id
        assert assignment_dto.role.code == "HEAD_ADMIN"
        assert assignment_dto.is_active is True
        
        # Verify DB record
        assert TournamentStaffAssignment.objects.count() == 1
    
    def test_assign_staff_duplicate_raises_error(
        self,
        adapter,
        sample_role,
        django_user_model,
        tournament
    ):
        """Test assigning same user/role twice raises error."""
        user = django_user_model.objects.create(username="staff_user")
        assigner = django_user_model.objects.create(username="organizer")
        
        # First assignment
        adapter.assign_staff_to_tournament(
            tournament_id=tournament.id,
            user_id=user.id,
            role_code="HEAD_ADMIN",
            assigned_by_user_id=assigner.id
        )
        
        # Second assignment (should fail)
        with pytest.raises(ValueError, match="already assigned"):
            adapter.assign_staff_to_tournament(
                tournament_id=tournament.id,
                user_id=user.id,
                role_code="HEAD_ADMIN",
                assigned_by_user_id=assigner.id
            )
    
    def test_get_staff_assignments_for_tournament(
        self,
        adapter,
        sample_role,
        django_user_model,
        tournament
    ):
        """Test get_staff_assignments_for_tournament returns assignments."""
        user = django_user_model.objects.create(username="staff_user")
        assigner = django_user_model.objects.create(username="organizer")
        
        adapter.assign_staff_to_tournament(
            tournament_id=tournament.id,
            user_id=user.id,
            role_code="HEAD_ADMIN",
            assigned_by_user_id=assigner.id
        )
        
        assignments = adapter.get_staff_assignments_for_tournament(
            tournament_id=tournament.id
        )
        
        assert len(assignments) == 1
        assert assignments[0].tournament_id == tournament.id
    
    def test_update_staff_assignment_status(
        self,
        adapter,
        sample_role,
        django_user_model,
        tournament
    ):
        """Test update_staff_assignment_status changes active status."""
        user = django_user_model.objects.create(username="staff_user")
        assigner = django_user_model.objects.create(username="organizer")
        
        assignment = adapter.assign_staff_to_tournament(
            tournament_id=tournament.id,
            user_id=user.id,
            role_code="HEAD_ADMIN",
            assigned_by_user_id=assigner.id
        )
        
        # Update to inactive
        updated = adapter.update_staff_assignment_status(
            assignment_id=assignment.assignment_id,
            is_active=False
        )
        
        assert updated.is_active is False
    
    # ========================================================================
    # Referee Assignment Tests
    # ========================================================================
    
    def test_assign_referee_to_match(
        self,
        adapter,
        referee_role,
        django_user_model,
        tournament,
        match
    ):
        """Test assign_referee_to_match creates assignment."""
        referee_user = django_user_model.objects.create(username="referee_user")
        assigner = django_user_model.objects.create(username="organizer")
        
        # Create staff assignment first
        staff_assignment = adapter.assign_staff_to_tournament(
            tournament_id=tournament.id,
            user_id=referee_user.id,
            role_code="REFEREE",
            assigned_by_user_id=assigner.id
        )
        
        # Assign to match
        ref_assignment = adapter.assign_referee_to_match(
            match_id=match.id,
            staff_assignment_id=staff_assignment.assignment_id,
            assigned_by_user_id=assigner.id,
            is_primary=True
        )
        
        assert ref_assignment is not None
        assert ref_assignment.match_id == match.id
        assert ref_assignment.is_primary is True
        
        # Verify DB record
        assert MatchRefereeAssignment.objects.count() == 1
    
    def test_get_referee_assignments_for_match(
        self,
        adapter,
        referee_role,
        django_user_model,
        tournament,
        match
    ):
        """Test get_referee_assignments_for_match returns assignments."""
        referee_user = django_user_model.objects.create(username="referee_user")
        assigner = django_user_model.objects.create(username="organizer")
        
        staff_assignment = adapter.assign_staff_to_tournament(
            tournament_id=tournament.id,
            user_id=referee_user.id,
            role_code="REFEREE",
            assigned_by_user_id=assigner.id
        )
        
        adapter.assign_referee_to_match(
            match_id=match.id,
            staff_assignment_id=staff_assignment.assignment_id,
            assigned_by_user_id=assigner.id
        )
        
        assignments = adapter.get_referee_assignments_for_match(match_id=match.id)
        
        assert len(assignments) == 1
        assert assignments[0].match_id == match.id
    
    def test_unassign_referee_from_match(
        self,
        adapter,
        referee_role,
        django_user_model,
        tournament,
        match
    ):
        """Test unassign_referee_from_match removes assignment."""
        referee_user = django_user_model.objects.create(username="referee_user")
        assigner = django_user_model.objects.create(username="organizer")
        
        staff_assignment = adapter.assign_staff_to_tournament(
            tournament_id=tournament.id,
            user_id=referee_user.id,
            role_code="REFEREE",
            assigned_by_user_id=assigner.id
        )
        
        ref_assignment = adapter.assign_referee_to_match(
            match_id=match.id,
            staff_assignment_id=staff_assignment.assignment_id,
            assigned_by_user_id=assigner.id
        )
        
        # Unassign
        adapter.unassign_referee_from_match(
            referee_assignment_id=ref_assignment.assignment_id
        )
        
        # Verify removed
        assert MatchRefereeAssignment.objects.count() == 0
    
    # ========================================================================
    # Staff Load Tests
    # ========================================================================
    
    def test_calculate_staff_load(
        self,
        adapter,
        referee_role,
        django_user_model,
        tournament,
        match
    ):
        """Test calculate_staff_load returns load summaries."""
        referee_user = django_user_model.objects.create(username="referee_user")
        assigner = django_user_model.objects.create(username="organizer")
        
        staff_assignment = adapter.assign_staff_to_tournament(
            tournament_id=tournament.id,
            user_id=referee_user.id,
            role_code="REFEREE",
            assigned_by_user_id=assigner.id
        )
        
        adapter.assign_referee_to_match(
            match_id=match.id,
            staff_assignment_id=staff_assignment.assignment_id,
            assigned_by_user_id=assigner.id
        )
        
        loads = adapter.calculate_staff_load(tournament_id=tournament.id)
        
        assert len(loads) == 1
        assert loads[0].total_matches_assigned >= 1


# Fixtures for database objects

@pytest.fixture
def tournament(db, django_user_model, game):
    """Create a test tournament."""
    from apps.tournaments.models import Tournament
    organizer = django_user_model.objects.create(username="organizer")
    return Tournament.objects.create(
        name="Test Tournament",
        game=game,
        organizer=organizer,
        status="PUBLISHED"
    )


@pytest.fixture
def match(db, tournament, stage):
    """Create a test match."""
    from apps.tournaments.models import Match
    return Match.objects.create(
        tournament=tournament,
        stage=stage,
        round_number=1,
        match_number=1,
        status="SCHEDULED"
    )


@pytest.fixture
def stage(db, tournament):
    """Create a test stage."""
    from apps.tournaments.models import Stage
    return Stage.objects.create(
        tournament=tournament,
        name="Bracket",
        stage_type="SINGLE_ELIMINATION",
        order=1
    )


@pytest.fixture
def game(db):
    """Create a test game."""
    from apps.games.models import Game
    return Game.objects.create(
        name="Test Game",
        slug="test-game"
    )
