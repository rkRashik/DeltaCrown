"""
Tests for TeamMembership model.

Coverage:
- TeamMembership creation
- UniqueConstraint: team+user where status=ACTIVE
- UniqueConstraint: is_tournament_captain=True (one per team)
- Role and roster slot validation
- Helper methods: get_permission_list, can_manage_roster, requires_game_passport

Performance: This file should run in <4 seconds.
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.organizations.models import TeamMembership
from apps.organizations.choices import (
    MembershipStatus,
    MembershipRole,
    RosterSlot,
)
from apps.organizations.tests.factories import (
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)

User = get_user_model()


@pytest.mark.django_db
class TestTeamMembership:
    """Test suite for TeamMembership model."""
    
    def test_create_membership(self):
        """Test creating a team membership with required fields."""
        team = TeamFactory.create()
        user = UserFactory.create()
        
        membership = TeamMembership.objects.create(
            team=team,
            user=user,
            status=MembershipStatus.ACTIVE,
            role=MembershipRole.PLAYER,
        )
        
        assert membership.pk is not None
        assert membership.team == team
        assert membership.user == user
        assert membership.status == MembershipStatus.ACTIVE
    
    def test_unique_constraint_team_user_active(self):
        """Test that a user can only have one ACTIVE membership per team."""
        team = TeamFactory.create()
        user = UserFactory.create()
        
        # Create first ACTIVE membership
        TeamMembershipFactory.create(
            team=team,
            user=user,
            status=MembershipStatus.ACTIVE,
        )
        
        # Attempting to create second ACTIVE membership for same team+user should fail
        with pytest.raises(IntegrityError):
            TeamMembership.objects.create(
                team=team,
                user=user,
                status=MembershipStatus.ACTIVE,
                role=MembershipRole.SUBSTITUTE,
            )
    
    def test_multiple_memberships_different_statuses_allowed(self):
        """Test that user can have multiple memberships if not all ACTIVE."""
        team = TeamFactory.create()
        user = UserFactory.create()
        
        # Create ACTIVE membership
        membership1 = TeamMembershipFactory.create(
            team=team,
            user=user,
            status=MembershipStatus.ACTIVE,
        )
        
        # Create INACTIVE membership (should be allowed)
        membership2 = TeamMembershipFactory.create(
            team=team,
            user=user,
            status=MembershipStatus.INACTIVE,
        )
        
        assert membership1.pk != membership2.pk
        assert TeamMembership.objects.filter(team=team, user=user).count() == 2
    
    def test_unique_constraint_tournament_captain(self):
        """Test that only one ACTIVE member can be tournament captain per team."""
        team = TeamFactory.create()
        
        # Create first tournament captain
        TeamMembershipFactory.create_captain(
            team=team,
            status=MembershipStatus.ACTIVE,
        )
        
        # Attempting to create second ACTIVE tournament captain should fail
        with pytest.raises(IntegrityError):
            TeamMembership.objects.create(
                team=team,
                user=UserFactory.create(),
                status=MembershipStatus.ACTIVE,
                role=MembershipRole.OWNER,
                is_tournament_captain=True,
            )
    
    def test_multiple_captains_different_statuses_allowed(self):
        """Test that multiple captains allowed if not all ACTIVE."""
        team = TeamFactory.create()
        
        # Create ACTIVE captain
        captain1 = TeamMembershipFactory.create_captain(
            team=team,
            status=MembershipStatus.ACTIVE,
        )
        
        # Create INACTIVE captain (should be allowed)
        captain2 = TeamMembershipFactory.create_captain(
            team=team,
            status=MembershipStatus.INACTIVE,
        )
        
        assert captain1.pk != captain2.pk
    
    def test_role_choices_validation(self):
        """Test that only valid role choices are accepted."""
        membership = TeamMembershipFactory.create(role=MembershipRole.COACH)
        
        assert membership.role == MembershipRole.COACH
        assert membership.role in [choice[0] for choice in MembershipRole.choices]
    
    def test_roster_slot_nullable(self):
        """Test that roster_slot can be null (for non-playing roles)."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.COACH,
            roster_slot=None,  # Coaches don't need roster slots
        )
        
        assert membership.roster_slot is None
    
    def test_roster_slot_choices_validation(self):
        """Test that only valid roster slot choices are accepted."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.PLAYER,
            roster_slot=RosterSlot.SUBSTITUTE,
        )
        
        assert membership.roster_slot == RosterSlot.SUBSTITUTE
    
    def test_str_representation(self):
        """Test string representation of TeamMembership."""
        team = TeamFactory.create(name="G2 Esports")
        user = UserFactory.create(username="m3c")
        membership = TeamMembershipFactory.create(
            team=team,
            user=user,
            role=MembershipRole.PLAYER,
        )
        
        expected = f"m3c - PLAYER on G2 Esports"
        assert str(membership) == expected
    
    def test_get_permission_list_owner(self):
        """Test that OWNER role gets all permissions."""
        membership = TeamMembershipFactory.create(role=MembershipRole.OWNER)
        
        permissions = membership.get_permission_list()
        
        assert "ALL" in permissions
        assert len(permissions) == 1  # Just "ALL"
    
    def test_get_permission_list_manager(self):
        """Test that MANAGER role gets specific permissions."""
        membership = TeamMembershipFactory.create(role=MembershipRole.MANAGER)
        
        permissions = membership.get_permission_list()
        
        # Managers can do most things except delete team
        assert "register_tournaments" in permissions
        assert "edit_roster" in permissions
        assert "edit_team" in permissions  # Canonical name (not edit_team_info)
        assert "schedule_scrims" in permissions
        assert "edit_toc" in permissions
        assert "ALL" not in permissions  # Not owner
    
    def test_get_permission_list_coach(self):
        """Test that COACH role gets limited permissions."""
        membership = TeamMembershipFactory.create(role=MembershipRole.COACH)
        
        permissions = membership.get_permission_list()
        
        assert "edit_toc" in permissions
        assert "schedule_scrims" in permissions
        assert "view_analytics" in permissions
        assert "edit_roster" not in permissions  # Coaches can't edit roster
    
    def test_get_permission_list_player(self):
        """Test that PLAYER role gets minimal permissions."""
        membership = TeamMembershipFactory.create(role=MembershipRole.PLAYER)
        
        permissions = membership.get_permission_list()
        
        assert "view_dashboard" in permissions
        assert "register_tournaments" not in permissions  # Players can't register
        assert "edit_roster" not in permissions  # Players can't edit roster
    
    def test_can_manage_roster_owner(self):
        """Test that OWNER can manage roster."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        
        assert membership.can_manage_roster() is True
    
    def test_can_manage_roster_manager(self):
        """Test that MANAGER can manage roster."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.MANAGER,
            status=MembershipStatus.ACTIVE,
        )
        
        assert membership.can_manage_roster() is True
    
    def test_can_manage_roster_coach_cannot(self):
        """Test that COACH cannot manage roster."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.COACH,
            status=MembershipStatus.ACTIVE,
        )
        
        assert membership.can_manage_roster() is False
    
    def test_can_manage_roster_inactive_cannot(self):
        """Test that INACTIVE members cannot manage roster."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.OWNER,
            status=MembershipStatus.INACTIVE,  # Not active
        )
        
        assert membership.can_manage_roster() is False
    
    def test_requires_game_passport_player_starter(self):
        """Test that PLAYER in STARTER slot requires game passport."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.PLAYER,
            roster_slot=RosterSlot.STARTER,
        )
        
        assert membership.requires_game_passport() is True
    
    def test_requires_game_passport_substitute(self):
        """Test that SUBSTITUTE in SUBSTITUTE slot requires game passport."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.SUBSTITUTE,
            roster_slot=RosterSlot.SUBSTITUTE,
        )
        
        assert membership.requires_game_passport() is True
    
    def test_requires_game_passport_coach_does_not(self):
        """Test that COACH does not require game passport."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.COACH,
            roster_slot=RosterSlot.COACH,
        )
        
        assert membership.requires_game_passport() is False
    
    def test_requires_game_passport_analyst_does_not(self):
        """Test that ANALYST does not require game passport."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.ANALYST,
            roster_slot=None,  # Analysts typically don't have roster slots
        )
        
        assert membership.requires_game_passport() is False
    
    def test_can_check_in_tournaments_captain(self):
        """Test that tournament captain can check in."""
        membership = TeamMembershipFactory.create_captain()
        
        assert membership.can_check_in_tournaments() is True
    
    def test_can_check_in_tournaments_owner(self):
        """Test that OWNER can check in (even if not captain)."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.OWNER,
            is_tournament_captain=False,
        )
        
        assert membership.can_check_in_tournaments() is True
    
    def test_can_check_in_tournaments_manager(self):
        """Test that MANAGER can check in."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.MANAGER,
            is_tournament_captain=False,
        )
        
        assert membership.can_check_in_tournaments() is True
    
    def test_can_check_in_tournaments_player_cannot(self):
        """Test that regular PLAYER cannot check in (unless captain)."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.PLAYER,
            is_tournament_captain=False,
        )
        
        assert membership.can_check_in_tournaments() is False
    
    def test_joined_at_auto_set(self):
        """Test that joined_at timestamp is automatically set."""
        membership = TeamMembershipFactory.create()
        
        assert membership.joined_at is not None
    
    def test_left_at_nullable(self):
        """Test that left_at is nullable (for active members)."""
        membership = TeamMembershipFactory.create(status=MembershipStatus.ACTIVE)
        
        assert membership.left_at is None
    
    def test_player_role_field_for_game_specific_role(self):
        """Test that player_role field can store game-specific role info."""
        membership = TeamMembershipFactory.create(
            role=MembershipRole.PLAYER,
            player_role="Duelist",  # Valorant-specific role
        )
        
        assert membership.player_role == "Duelist"
    
    def test_is_tournament_captain_defaults_to_false(self):
        """Test that is_tournament_captain defaults to False."""
        membership = TeamMembershipFactory.create()
        
        assert membership.is_tournament_captain is False
