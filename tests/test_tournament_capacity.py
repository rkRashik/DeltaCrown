"""
Tests for TournamentCapacity Model

Comprehensive test suite for the capacity management system.
Tests all features including validation, properties, and methods.

Author: DeltaCrown Development Team
Date: October 3, 2025
"""

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.tournaments.models import Tournament
from apps.tournaments.models.core import TournamentCapacity


@pytest.mark.django_db
class TestTournamentCapacityCreation:
    """Test capacity model creation and basic validation"""
    
    def test_create_capacity_basic(self):
        """Test creating a basic capacity configuration"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            min_team_size=5,
            max_team_size=7,
            registration_mode=TournamentCapacity.MODE_OPEN
        )
        
        assert capacity.tournament == tournament
        assert capacity.slot_size == 16
        assert capacity.max_teams == 16
        assert capacity.min_team_size == 5
        assert capacity.max_team_size == 7
        assert capacity.current_registrations == 0
    
    def test_create_solo_tournament_capacity(self):
        """Test creating capacity for 1v1 tournament"""
        tournament = Tournament.objects.create(
            name="1v1 Tournament",
            game="efootball",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=32,
            max_teams=32,
            min_team_size=1,
            max_team_size=1
        )
        
        assert capacity.is_solo_tournament
        assert capacity.requires_full_squad
    
    def test_one_to_one_relationship(self):
        """Test that tournament can only have one capacity"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16
        )
        
        # Attempting to create another should raise error
        with pytest.raises(Exception):  # IntegrityError
            TournamentCapacity.objects.create(
                tournament=tournament,
                slot_size=32,
                max_teams=32
            )


@pytest.mark.django_db
class TestTournamentCapacityValidation:
    """Test validation rules for capacity configuration"""
    
    def test_min_team_size_cannot_exceed_max(self):
        """Test that min_team_size must be <= max_team_size"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            min_team_size=10,  # Invalid: more than max
            max_team_size=5
        )
        
        with pytest.raises(ValidationError) as exc_info:
            capacity.save()
        
        assert 'min_team_size' in exc_info.value.message_dict
    
    def test_max_teams_cannot_exceed_slot_size(self):
        """Test that max_teams must be <= slot_size"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity(
            tournament=tournament,
            slot_size=16,
            max_teams=32,  # Invalid: more than slots
            min_team_size=5,
            max_team_size=7
        )
        
        with pytest.raises(ValidationError) as exc_info:
            capacity.save()
        
        assert 'max_teams' in exc_info.value.message_dict
    
    def test_minimum_slot_size_validation(self):
        """Test that tournament must have at least 2 slots"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity(
            tournament=tournament,
            slot_size=1,  # Invalid: too small
            max_teams=1
        )
        
        with pytest.raises(ValidationError) as exc_info:
            capacity.save()
        
        assert 'slot_size' in exc_info.value.message_dict
    
    def test_current_registrations_validation(self):
        """Test that current_registrations can't exceed max_teams"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16
        )
        
        # Try to set invalid registration count
        capacity.current_registrations = 20
        
        with pytest.raises(ValidationError) as exc_info:
            capacity.save()
        
        assert 'current_registrations' in exc_info.value.message_dict


@pytest.mark.django_db
class TestTournamentCapacityProperties:
    """Test computed properties of capacity model"""
    
    def test_is_full_when_empty(self):
        """Test is_full returns False when no registrations"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16
        )
        
        assert not capacity.is_full
    
    def test_is_full_when_at_capacity(self):
        """Test is_full returns True when at max_teams"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=16
        )
        
        assert capacity.is_full
    
    def test_available_slots_calculation(self):
        """Test available_slots returns correct remaining count"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=10
        )
        
        assert capacity.available_slots == 6
    
    def test_available_slots_never_negative(self):
        """Test available_slots returns 0 when over capacity"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=16,
            waitlist_enabled=True
        )
        
        # Use update() to bypass validation for waitlist scenario
        TournamentCapacity.objects.filter(pk=capacity.pk).update(current_registrations=18)
        capacity.refresh_from_db()
        
        assert capacity.available_slots == 0
    
    def test_registration_progress_percent(self):
        """Test registration_progress_percent calculation"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=8
        )
        
        assert capacity.registration_progress_percent == 50.0
    
    def test_can_accept_registrations_open_mode(self):
        """Test can_accept_registrations in OPEN mode"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            registration_mode=TournamentCapacity.MODE_OPEN
        )
        
        assert capacity.can_accept_registrations
    
    def test_can_accept_registrations_invite_mode(self):
        """Test can_accept_registrations in INVITE mode"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            registration_mode=TournamentCapacity.MODE_INVITE
        )
        
        assert not capacity.can_accept_registrations
    
    def test_can_accept_registrations_full_with_waitlist(self):
        """Test can_accept_registrations when full but waitlist enabled"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=16,
            waitlist_enabled=True
        )
        
        assert capacity.can_accept_registrations
    
    def test_is_solo_tournament_property(self):
        """Test is_solo_tournament identification"""
        tournament = Tournament.objects.create(
            name="1v1 Tournament",
            game="efootball",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=32,
            max_teams=32,
            min_team_size=1,
            max_team_size=1
        )
        
        assert capacity.is_solo_tournament
    
    def test_requires_full_squad_property(self):
        """Test requires_full_squad when min == max"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            min_team_size=5,
            max_team_size=5  # Exactly 5 required
        )
        
        assert capacity.requires_full_squad


@pytest.mark.django_db
class TestTournamentCapacityMethods:
    """Test action methods of capacity model"""
    
    def test_increment_registrations(self):
        """Test incrementing registration count"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=5
        )
        
        capacity.increment_registrations()
        assert capacity.current_registrations == 6
        
        capacity.increment_registrations(3)
        assert capacity.current_registrations == 9
    
    def test_increment_registrations_validation(self):
        """Test increment_registrations raises error when exceeding max"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=15,
            waitlist_enabled=False
        )
        
        with pytest.raises(ValidationError):
            capacity.increment_registrations(5)
    
    def test_decrement_registrations(self):
        """Test decrementing registration count"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=10
        )
        
        capacity.decrement_registrations()
        assert capacity.current_registrations == 9
        
        capacity.decrement_registrations(5)
        assert capacity.current_registrations == 4
    
    def test_decrement_registrations_never_negative(self):
        """Test decrement_registrations stops at 0"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=2
        )
        
        capacity.decrement_registrations(5)
        assert capacity.current_registrations == 0
    
    def test_validate_team_size_valid(self):
        """Test validate_team_size with valid size"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            min_team_size=5,
            max_team_size=7
        )
        
        is_valid, message = capacity.validate_team_size(6)
        assert is_valid
        assert message == 'Team size is valid'
    
    def test_validate_team_size_too_small(self):
        """Test validate_team_size with too few players"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            min_team_size=5,
            max_team_size=7
        )
        
        is_valid, message = capacity.validate_team_size(3)
        assert not is_valid
        assert 'at least 5' in message
    
    def test_validate_team_size_too_large(self):
        """Test validate_team_size with too many players"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            min_team_size=5,
            max_team_size=7
        )
        
        is_valid, message = capacity.validate_team_size(10)
        assert not is_valid
        assert 'cannot exceed 7' in message


@pytest.mark.django_db
class TestTournamentCapacityHelpers:
    """Test helper methods and utilities"""
    
    def test_get_capacity_display_not_full(self):
        """Test capacity display when slots available"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=10
        )
        
        display = capacity.get_capacity_display()
        assert '10/16' in display
        assert '6 slots remaining' in display
    
    def test_get_capacity_display_full(self):
        """Test capacity display when full"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=16
        )
        
        display = capacity.get_capacity_display()
        assert 'FULL' in display
        assert '16/16' in display
    
    def test_clone_for_tournament(self):
        """Test cloning capacity for another tournament"""
        tournament1 = Tournament.objects.create(
            name="Original Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity1 = TournamentCapacity.objects.create(
            tournament=tournament1,
            slot_size=16,
            max_teams=16,
            min_team_size=5,
            max_team_size=7,
            registration_mode=TournamentCapacity.MODE_APPROVAL,
            current_registrations=10
        )
        
        tournament2 = Tournament.objects.create(
            name="New Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity2 = capacity1.clone_for_tournament(tournament2)
        
        assert capacity2.tournament == tournament2
        assert capacity2.slot_size == capacity1.slot_size
        assert capacity2.max_teams == capacity1.max_teams
        assert capacity2.min_team_size == capacity1.min_team_size
        assert capacity2.max_team_size == capacity1.max_team_size
        assert capacity2.registration_mode == capacity1.registration_mode
        assert capacity2.current_registrations == 0  # New tournament
    
    def test_to_dict(self):
        """Test converting capacity to dictionary"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            min_team_size=5,
            max_team_size=7,
            current_registrations=8
        )
        
        data = capacity.to_dict()
        
        assert data['slot_size'] == 16
        assert data['max_teams'] == 16
        assert data['current_registrations'] == 8
        assert data['is_full'] is False
        assert data['available_slots'] == 8
        assert data['progress_percent'] == 50.0
        assert 'registration_mode' in data
        assert 'can_accept_registrations' in data
    
    def test_str_representation(self):
        """Test string representation of capacity"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=8
        )
        
        str_repr = str(capacity)
        assert 'Test Tournament' in str_repr
        assert 'Capacity' in str_repr
        assert '8/16' in str_repr


@pytest.mark.django_db
class TestRegistrationModes:
    """Test different registration modes"""
    
    def test_open_mode_behavior(self):
        """Test OPEN registration mode allows registrations"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            registration_mode=TournamentCapacity.MODE_OPEN
        )
        
        assert capacity.can_accept_registrations
        assert capacity.get_registration_mode_display() == 'Open Registration'
    
    def test_approval_mode_behavior(self):
        """Test APPROVAL registration mode"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            registration_mode=TournamentCapacity.MODE_APPROVAL
        )
        
        assert capacity.can_accept_registrations
        assert capacity.get_registration_mode_display() == 'Approval Required'
    
    def test_invite_mode_behavior(self):
        """Test INVITE registration mode blocks registrations"""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="upcoming"
        )
        
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            slot_size=16,
            max_teams=16,
            registration_mode=TournamentCapacity.MODE_INVITE
        )
        
        assert not capacity.can_accept_registrations
        assert capacity.get_registration_mode_display() == 'Invite Only'
