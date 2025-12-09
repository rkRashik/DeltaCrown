"""
Tests for Group Stage Serializers (Epic 3.2)
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.tournaments.models import (
    Tournament,
    GroupStage,
    Group,
    GroupStanding,
    Match,
    Game,
)
from apps.teams.models import Team
from apps.tournaments.services.group_stage_service import GroupStageService
from apps.tournaments.serializers import (
    StandingSerializer,
    GroupSerializer,
    GroupStageSerializer,
)

User = get_user_model()


@pytest.fixture
def game(db):
    """Create a test game."""
    return Game.objects.create(
        name="Test Game",
        slug="test-game",
        is_active=True,
    )


@pytest.fixture
def organizer(db):
    """Create a test organizer."""
    return User.objects.create_user(
        username="organizer",
        email="organizer@test.com",
        password="pass123"
    )


@pytest.fixture
def tournament(db, game, organizer):
    """Create a test tournament."""
    return Tournament.objects.create(
        name="Test Tournament",
        game=game,
        organizer=organizer,
        max_participants=16,
        registration_start=timezone.now(),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=8),
        tournament_end=timezone.now() + timedelta(days=10),
    )


@pytest.mark.django_db
class TestStandingSerializer:
    """Tests for StandingSerializer."""
    
    def test_serialize_standing(self, tournament):
        """Should serialize GroupStanding with all required fields."""
        team = Team.objects.create(
            name="Test Team",
            tag="TT",
            slug="test-team",
            game=tournament.game.slug,
        )
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=1,
            group_size=2,
            advancement_count_per_group=1,  # Must be less than group_size
        )
        
        group = Group.objects.get(tournament=tournament)
        
        standing = GroupStanding.objects.create(
            group=group,
            team_id=team.id,
            rank=1,
            points=9,
            matches_won=3,
            matches_drawn=0,
            matches_lost=0,
            goals_for=5,
            goals_against=1,
            goal_difference=4,
        )
        
        data = StandingSerializer.serialize(standing)
        
        assert data["participant_id"] == team.id
        assert data["participant_type"] == "team"
        assert data["rank"] == 1
        assert data["points"] == 9.0
        assert data["matches_won"] == 3
        assert data["matches_played"] == 3
        assert data["goal_difference"] == 4


@pytest.mark.django_db
class TestGroupSerializer:
    """Tests for GroupSerializer."""
    
    def test_serialize_group_with_standings(self, tournament):
        """Should serialize Group with standings included."""
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 5)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=1,
            group_size=4,
            advancement_count_per_group=2,
        )
        
        group = Group.objects.get(tournament=tournament)
        
        # Add participants
        GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        data = GroupSerializer.serialize(group, include_standings=True, include_matches=False)
        
        assert data["id"] == group.id
        assert data["name"] == "Group A"
        assert data["max_participants"] == 4
        assert data["current_participants"] == 4
        assert data["is_full"] is True
        assert "standings" in data
        assert len(data["standings"]) == 4
    
    def test_serialize_group_with_matches(self, tournament):
        """Should include upcoming matches when requested."""
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 4)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=1,
            group_size=3,
            advancement_count_per_group=2,
        )
        
        group = Group.objects.get(tournament=tournament)
        
        GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        GroupStageService.generate_group_matches(stage.id)
        
        data = GroupSerializer.serialize(group, include_standings=False, include_matches=True)
        
        assert "upcoming_matches" in data
        assert len(data["upcoming_matches"]) > 0
        
        match_data = data["upcoming_matches"][0]
        assert "id" in match_data
        assert "participant1_id" in match_data
        assert "state" in match_data


@pytest.mark.django_db
class TestGroupStageSerializer:
    """Tests for GroupStageSerializer."""
    
    def test_serialize_group_stage(self, tournament):
        """Should serialize complete GroupStage with all groups."""
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 17)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=4,
            group_size=4,
            advancement_count_per_group=2,
        )
        
        GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        data = GroupStageSerializer.serialize(stage)
        
        assert data["id"] == stage.id
        assert data["name"] == "Group Stage"
        assert data["num_groups"] == 4
        assert data["group_size"] == 4
        assert data["total_participants"] == 16
        assert data["total_advancing"] == 8
        assert len(data["groups"]) == 4
        
        # Check first group structure
        group_data = data["groups"][0]
        assert "id" in group_data
        assert "name" in group_data
        assert "standings" in group_data
    
    def test_serialize_for_drag_drop(self, tournament):
        """Should provide drag-drop optimized structure."""
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 5)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
            advancement_count_per_group=2,
        )
        
        # Assign only 4 participants (leaving 4 unassigned)
        GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        data = GroupStageSerializer.serialize_for_drag_drop(stage)
        
        assert data["stage_id"] == stage.id
        assert len(data["groups"]) == 2
        assert data["total_slots"] == 8
        assert data["slots_filled"] == 4
        assert data["can_auto_balance"] is False  # No unassigned in registrations
        
        # Check group structure
        group_data = data["groups"][0]
        assert "id" in group_data
        assert "name" in group_data
        assert "participants" in group_data
        assert "max_participants" in group_data
        assert "slots_remaining" in group_data
