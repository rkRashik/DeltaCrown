"""
Tests for team registration permission validation.

Tests the backend enforcement that only authorized team members
(owner, manager, or members with explicit permission) can register
teams for tournaments.

Related:
- Documents/ExecutionPlan/FrontEnd/Core/MODULE_TOURNAMENT_REGISTRATION_ALIGNMENT.md
- apps/tournaments/services/registration_service.py::_validate_team_registration_permission
- apps/teams/models/_legacy.py::TeamMembership.can_register_tournaments
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Registration
from apps.tournaments.services import RegistrationService
from apps.teams.models import Team, TeamMembership
from apps.user_profile.models import UserProfile

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def game():
    """Create a game object"""
    from apps.tournaments.models import Game
    game, _ = Game.objects.get_or_create(
        slug='valorant',
        defaults={
            'name': 'Valorant',
            'is_active': True
        }
    )
    return game


@pytest.fixture
def organizer_user():
    """Create tournament organizer user"""
    user = User.objects.create_user(
        username='tournament_organizer',
        email='organizer@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def tournament(game, organizer_user):
    """Create a team tournament"""
    return Tournament.objects.create(
        name="Test Team Tournament",
        slug="test-team-tournament",
        game=game,
        organizer=organizer_user,
        participation_type=Tournament.TEAM,
        max_participants=16,
        status=Tournament.REGISTRATION_OPEN,
        registration_start=timezone.now() - timedelta(days=1),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=14)
    )


@pytest.fixture
def owner_user():
    """Create team owner user"""
    user = User.objects.create_user(
        username='team_owner',
        email='owner@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def manager_user():
    """Create team manager user"""
    user = User.objects.create_user(
        username='team_manager',
        email='manager@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def authorized_player_user():
    """Create player with explicit registration permission"""
    user = User.objects.create_user(
        username='authorized_player',
        email='player@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def regular_player_user():
    """Create regular player without registration permission"""
    user = User.objects.create_user(
        username='regular_player',
        email='regular@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def non_member_user():
    """Create user who is not a team member"""
    user = User.objects.create_user(
        username='non_member',
        email='nonmember@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def team(owner_user, manager_user, authorized_player_user, regular_player_user):
    """Create a team with various membership roles"""
    team = Team.objects.create(
        name="Test Esports Team",
        tag="TEST",
        game="valorant",
        captain=owner_user.profile
    )
    
    # Owner membership (automatic via ensure_captain_membership)
    team.ensure_captain_membership()
    
    # Manager membership
    TeamMembership.objects.create(
        team=team,
        profile=manager_user.profile,
        role=TeamMembership.Role.MANAGER,
        status=TeamMembership.Status.ACTIVE
    )
    
    # Authorized player (explicitly granted permission)
    authorized_membership = TeamMembership.objects.create(
        team=team,
        profile=authorized_player_user.profile,
        role=TeamMembership.Role.PLAYER,
        status=TeamMembership.Status.ACTIVE
    )
    # Manually grant permission (simulating explicit grant by owner/manager)
    # Use direct database update to bypass save() which calls update_permission_cache()
    TeamMembership.objects.filter(pk=authorized_membership.pk).update(
        can_register_tournaments=True
    )
    
    # Regular player (no special permissions)
    TeamMembership.objects.create(
        team=team,
        profile=regular_player_user.profile,
        role=TeamMembership.Role.PLAYER,
        status=TeamMembership.Status.ACTIVE
    )
    
    return team


class TestTeamRegistrationPermissions:
    """Test team registration permission enforcement"""
    
    def test_owner_can_register_team(self, tournament, team, owner_user):
        """Team owner should be able to register team"""
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=owner_user,
            team_id=team.id
        )
        
        assert registration is not None
        assert registration.tournament == tournament
        assert registration.team_id == team.id
        assert registration.user is None  # Team registrations have null user
        assert registration.status == Registration.PENDING
    
    def test_manager_can_register_team(self, tournament, team, manager_user):
        """Team manager should be able to register team"""
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=manager_user,
            team_id=team.id
        )
        
        assert registration is not None
        assert registration.tournament == tournament
        assert registration.team_id == team.id
        assert registration.user is None  # Team registrations have null user
    
    def test_authorized_player_can_register_team(self, tournament, team, authorized_player_user):
        """Player with explicit permission should be able to register team"""
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=authorized_player_user,
            team_id=team.id
        )
        
        assert registration is not None
        assert registration.tournament == tournament
        assert registration.team_id == team.id
        assert registration.user is None  # Team registrations have null user
    
    def test_regular_player_cannot_register_team(self, tournament, team, regular_player_user):
        """Regular player without permission should not be able to register team"""
        with pytest.raises(ValidationError) as exc_info:
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=regular_player_user,
                team_id=team.id
            )
        
        error_message = str(exc_info.value)
        assert "do not have permission" in error_message
        assert "register" in error_message
        assert "tournament" in error_message.lower()
    
    def test_non_member_cannot_register_team(self, tournament, team, non_member_user):
        """User who is not a team member should not be able to register team"""
        with pytest.raises(ValidationError) as exc_info:
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=non_member_user,
                team_id=team.id
            )
        
        error_message = str(exc_info.value)
        assert "not an active member" in error_message
    
    def test_permission_check_before_duplicate_check(self, tournament, team, owner_user, regular_player_user):
        """Permission check should run before duplicate registration check"""
        # Owner registers team first
        RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=owner_user,
            team_id=team.id
        )
        
        # Regular player tries to register same team (should fail on permission, not duplicate)
        with pytest.raises(ValidationError) as exc_info:
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=regular_player_user,
                team_id=team.id
            )
        
        error_message = str(exc_info.value)
        # Should fail on permission, not "already registered"
        assert "do not have permission" in error_message
    
    def test_invalid_team_id_returns_clear_error(self, tournament, owner_user):
        """Invalid team ID should return clear error message"""
        with pytest.raises(ValidationError) as exc_info:
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=owner_user,
                team_id=99999  # Non-existent team
            )
        
        error_message = str(exc_info.value)
        assert "not found" in error_message or "does not exist" in error_message.lower()
    
    def test_solo_tournament_rejects_team_registration(self, game, owner_user, team, organizer_user):
        """Solo tournament should reject team registrations regardless of permission"""
        solo_tournament = Tournament.objects.create(
            name="Solo Tournament",
            slug="solo-tournament",
            game=game,
            organizer=organizer_user,
            participation_type=Tournament.SOLO,
            max_participants=32,
            status=Tournament.REGISTRATION_OPEN,
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=14)
        )
        
        with pytest.raises(ValidationError) as exc_info:
            RegistrationService.register_participant(
                tournament_id=solo_tournament.id,
                user=owner_user,
                team_id=team.id
            )
        
        error_message = str(exc_info.value)
        assert "solo" in error_message.lower()


class TestOneTeamPerGameConstraint:
    """Test one active team per game per player constraint"""
    
    def test_player_can_register_one_team_per_game(self, game, owner_user, organizer_user):
        """Player should be able to register different teams for different games"""
        # Create Valorant team
        valorant_team = Team.objects.create(
            name="Valorant Team",
            tag="VAL",
            game="valorant",
            captain=owner_user.profile
        )
        valorant_team.ensure_captain_membership()
        
        # Create CS2 team (different game)
        cs2_team = Team.objects.create(
            name="CS2 Team",
            tag="CS2",
            game="cs2",
            captain=owner_user.profile
        )
        cs2_team.ensure_captain_membership()
        
        # Create tournaments for both games
        valorant_tournament = Tournament.objects.create(
            name="Valorant Tournament",
            slug="val-tournament",
            game=game,
            organizer=organizer_user,
            participation_type=Tournament.TEAM,
            max_participants=16,
            status=Tournament.REGISTRATION_OPEN,
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=14)
        )
        
        from apps.tournaments.models import Game as TournamentGame
        cs2_game, _ = TournamentGame.objects.get_or_create(
            slug='cs2',
            defaults={'name': 'Counter-Strike 2', 'is_active': True}
        )
        
        cs2_tournament = Tournament.objects.create(
            name="CS2 Tournament",
            slug="cs2-tournament",
            game=cs2_game,
            organizer=organizer_user,
            participation_type=Tournament.TEAM,
            max_participants=16,
            status=Tournament.REGISTRATION_OPEN,
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=14)
        )
        
        # Should be able to register both teams (different games)
        val_registration = RegistrationService.register_participant(
            tournament_id=valorant_tournament.id,
            user=owner_user,
            team_id=valorant_team.id
        )
        
        cs2_registration = RegistrationService.register_participant(
            tournament_id=cs2_tournament.id,
            user=owner_user,
            team_id=cs2_team.id
        )
        
        assert val_registration.team_id == valorant_team.id
        assert cs2_registration.team_id == cs2_team.id


class TestTeamRegistrationIntegration:
    """Integration tests for complete team registration flow"""
    
    def test_complete_team_registration_flow(self, tournament, team, owner_user):
        """Test complete registration flow from eligibility check to creation"""
        # Check eligibility first
        RegistrationService.check_eligibility(
            tournament=tournament,
            user=owner_user,
            team_id=team.id
        )
        
        # Register team
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=owner_user,
            team_id=team.id,
            registration_data={
                'team_roster': ['Player1', 'Player2', 'Player3', 'Player4', 'Player5'],
                'notes': 'Excited to compete!'
            }
        )
        
        assert registration.tournament == tournament
        assert registration.team_id == team.id
        assert registration.user is None  # Team registrations have null user
        assert registration.status == Registration.PENDING
        assert registration.registration_data['notes'] == 'Excited to compete!'
    
    def test_permission_persists_after_role_change(self, tournament, team, regular_player_user):
        """Test that permission changes when role is updated"""
        # Initially regular player cannot register
        with pytest.raises(ValidationError):
            RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=regular_player_user,
                team_id=team.id
            )
        
        # Promote to manager
        membership = TeamMembership.objects.get(
            team=team,
            profile=regular_player_user.profile
        )
        membership.role = TeamMembership.Role.MANAGER
        membership.save()
        
        # Refresh from DB to get updated permissions
        membership.refresh_from_db()
        
        # Now should be able to register
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=regular_player_user,
            team_id=team.id
        )
        
        assert registration.user is None  # Team registrations have null user
        assert registration.team_id == team.id
