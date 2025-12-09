"""
Tests for GroupStageService (Epic 3.2)

Tests the 5 core methods:
- create_groups
- assign_participant
- auto_balance_groups
- generate_group_matches
- calculate_group_standings
"""

import pytest
from decimal import Decimal
from datetime import timedelta
from django.core.exceptions import ValidationError
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
class TestCreateGroups:
    """Tests for create_groups method."""
    
    def test_create_groups_creates_correct_number(self, tournament):
        """Should create N groups with correct names."""
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=4,
            group_size=4,
            advancement_count_per_group=2,
        )
        
        assert stage.num_groups == 4
        assert stage.group_size == 4
        
        groups = Group.objects.filter(tournament=tournament)
        assert groups.count() == 4
        assert list(groups.values_list('name', flat=True).order_by('display_order')) == [
            "Group A", "Group B", "Group C", "Group D"
        ]
    
    def test_create_groups_enforces_group_size(self, tournament):
        """Should raise error if group_size < 2."""
        with pytest.raises(ValidationError, match="Group size must be at least 2"):
            GroupStageService.create_groups(
                tournament_id=tournament.id,
                num_groups=2,
                group_size=1,
            )
    
    def test_create_groups_enforces_advancement_count(self, tournament):
        """Should raise error if advancement_count > group_size."""
        with pytest.raises(ValidationError, match="Advancement count"):
            GroupStageService.create_groups(
                tournament_id=tournament.id,
                num_groups=2,
                group_size=4,
                advancement_count_per_group=5,  # More than group_size - should fail
            )


@pytest.mark.django_db
class TestAssignParticipant:
    """Tests for assign_participant method."""
    
    def test_assign_participant_to_specific_group(self, tournament):
        """Should assign participant to specified group."""
        team = Team.objects.create(
            name="Team Alpha",
            tag="TA",
            slug="team-alpha",
            game=tournament.game.slug,
        )
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
        )
        
        group_a = Group.objects.get(tournament=tournament, name="Group A")
        
        standing = GroupStageService.assign_participant(
            stage_id=stage.id,
            participant_id=team.id,
            group_id=group_a.id,
            is_team=True,
        )
        
        assert standing.team_id == team.id
        assert standing.group == group_a
    
    def test_assign_participant_auto_assigns(self, tournament):
        """Should auto-assign to first available group."""
        team = Team.objects.create(
            name="Team A",
            slug="team-a",
            game=tournament.game.slug,
        )
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
        )
        
        standing = GroupStageService.assign_participant(
            stage_id=stage.id,
            participant_id=team.id,
            is_team=True,
        )
        
        # Should go to Group A (first group)
        assert standing.group.name == "Group A"
    
    def test_assign_participant_enforces_capacity(self, tournament):
        """Should raise error when group is full."""
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 4)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=1,
            group_size=2,
            advancement_count_per_group=1,  # Must be less than group_size
        )
        
        group = Group.objects.get(tournament=tournament)
        
        # Fill the group
        GroupStageService.assign_participant(stage.id, teams[0].id, group.id, is_team=True)
        GroupStageService.assign_participant(stage.id, teams[1].id, group.id, is_team=True)
        
        # Should fail on third assignment
        with pytest.raises(ValidationError, match="is already full"):
            GroupStageService.assign_participant(stage.id, teams[2].id, group.id, is_team=True)
    
    def test_assign_participant_prevents_duplicates(self, tournament):
        """Should raise error if participant already assigned."""
        team = Team.objects.create(
            name="Team A",
            slug="team-a",
            game=tournament.game.slug,
        )
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
        )
        
        GroupStageService.assign_participant(stage.id, team.id, is_team=True)
        
        with pytest.raises(ValidationError, match="already assigned"):
            GroupStageService.assign_participant(stage.id, team.id, is_team=True)


@pytest.mark.django_db
class TestAutoBalanceGroups:
    """Tests for auto_balance_groups method."""
    
    def test_auto_balance_groups_distributes_evenly(self, tournament):
        """Should distribute 8 participants across 2 groups using snake seeding."""
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 9)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
        )
        
        participant_ids = [t.id for t in teams]  # Seeded best to worst
        
        assignments = GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=participant_ids,
            is_team=True,
        )
        
        # Should have 2 groups
        assert len(assignments) == 2
        
        # Each group should have 4 participants
        for group_id, participants in assignments.items():
            assert len(participants) == 4
        
        # Snake seeding: A=[1,4,5,8], B=[2,3,6,7]
        groups = list(Group.objects.filter(tournament=tournament).order_by('display_order'))
        group_a, group_b = groups[0], groups[1]
        
        assert set(assignments[group_a.id]) == {teams[0].id, teams[3].id, teams[4].id, teams[7].id}
        assert set(assignments[group_b.id]) == {teams[1].id, teams[2].id, teams[5].id, teams[6].id}
    
    def test_auto_balance_groups_handles_uneven_distribution(self, tournament):
        """Should handle uneven participant counts."""
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 8)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=3,
            group_size=4,
        )
        
        participant_ids = [t.id for t in teams]  # 7 participants, 3 groups
        
        assignments = GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=participant_ids,
            is_team=True,
        )
        
        total_assigned = sum(len(p) for p in assignments.values())
        assert total_assigned == 7


@pytest.mark.django_db
class TestGenerateGroupMatches:
    """Tests for generate_group_matches method."""
    
    def test_generate_group_matches_all_pairings(self, tournament):
        """Should generate all unique pairings within each group."""
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 9)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
        )
        
        # Assign 4 participants to each group
        GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        match_count = GroupStageService.generate_group_matches(stage.id)
        
        # 2 groups × (4 participants choose 2) = 2 × 6 = 12 matches
        assert match_count == 12
        
        matches = Match.objects.filter(tournament=tournament)
        assert matches.count() == 12
    
    def test_generate_group_matches_no_cross_group(self, tournament):
        """Should only create matches within groups, not across groups."""
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 9)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
        )
        
        # Group A: 1,4,5,8  Group B: 2,3,6,7 (snake seeding)
        GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        GroupStageService.generate_group_matches(stage.id)
        
        groups = list(Group.objects.filter(tournament=tournament).order_by('display_order'))
        group_a = groups[0]
        
        # Get all matches for Group A
        group_a_matches = Match.objects.filter(
            tournament=tournament,
            lobby_info__group_id=group_a.id,
        )
        
        # Get the actual Group A standings to determine which teams are in Group A
        group_a_standings = GroupStanding.objects.filter(group=group_a)
        group_a_participants = set(s.team_id for s in group_a_standings)
        
        for match in group_a_matches:
            assert match.participant1_id in group_a_participants
            assert match.participant2_id in group_a_participants


@pytest.mark.django_db
class TestCalculateGroupStandings:
    """Tests for calculate_group_standings method."""
    
    def test_calculate_group_standings_basic_points(self, tournament):
        """Should calculate points correctly based on match results."""
        # Create 3 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", game=tournament.game.slug)
            for i in range(1, 4)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=1,
            group_size=3,
        )
        
        group = Group.objects.get(tournament=tournament)
        
        # Assign 3 participants
        GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        # Create completed matches
        # Team 0 beats Team 1
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=teams[0].id,
            participant2_id=teams[1].id,
            participant1_score=2,
            participant2_score=1,
            winner_id=teams[0].id,
            loser_id=teams[1].id,
            state=Match.COMPLETED,
            lobby_info={"group_id": group.id},
        )
        
        # Team 0 beats Team 2
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=2,
            participant1_id=teams[0].id,
            participant2_id=teams[2].id,
            participant1_score=3,
            participant2_score=0,
            winner_id=teams[0].id,
            loser_id=teams[2].id,
            state=Match.COMPLETED,
            lobby_info={"group_id": group.id},
        )
        
        # Team 1 beats Team 2
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=3,
            participant1_id=teams[1].id,
            participant2_id=teams[2].id,
            participant1_score=2,
            participant2_score=1,
            winner_id=teams[1].id,
            loser_id=teams[2].id,
            state=Match.COMPLETED,
            lobby_info={"group_id": group.id},
        )
        
        standings = GroupStageService.calculate_group_standings(stage.id)
        
        group_standings = standings[group.id]
        
        # Team 0: 2 wins = 6 points (rank 1)
        # Team 1: 1 win = 3 points (rank 2)
        # Team 2: 0 wins = 0 points (rank 3)
        assert group_standings[0]["participant_id"] == teams[0].id
        assert group_standings[0]["points"] == Decimal('6')
        assert group_standings[0]["rank"] == 1
        
        assert group_standings[1]["participant_id"] == teams[1].id
        assert group_standings[1]["points"] == Decimal('3')
        assert group_standings[1]["rank"] == 2
        
        assert group_standings[2]["participant_id"] == teams[2].id
        assert group_standings[2]["points"] == Decimal('0')
        assert group_standings[2]["rank"] == 3
    
    def test_calculate_group_standings_tiebreaker(self, tournament):
        """Should use wins and goal_diff as tiebreakers when points are equal."""
        # Create 3 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", game=tournament.game.slug)
            for i in range(1, 4)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=1,
            group_size=3,
        )
        
        group = Group.objects.get(tournament=tournament)
        
        GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        # Create matches resulting in 2 teams with same points
        # Team 0 beats Team 2 (big win)
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=teams[0].id,
            participant2_id=teams[2].id,
            participant1_score=5,
            participant2_score=0,
            winner_id=teams[0].id,
            loser_id=teams[2].id,
            state=Match.COMPLETED,
            lobby_info={"group_id": group.id},
        )
        
        # Team 1 beats Team 2 (small win)
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=2,
            participant1_id=teams[1].id,
            participant2_id=teams[2].id,
            participant1_score=1,
            participant2_score=0,
            winner_id=teams[1].id,
            loser_id=teams[2].id,
            state=Match.COMPLETED,
            lobby_info={"group_id": group.id},
        )
        
        # Team 0 vs Team 1: close match (Team 0 wins)
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=3,
            participant1_id=teams[0].id,
            participant2_id=teams[1].id,
            participant1_score=2,
            participant2_score=1,
            winner_id=teams[0].id,
            loser_id=teams[1].id,
            state=Match.COMPLETED,
            lobby_info={"group_id": group.id},
        )
        
        standings = GroupStageService.calculate_group_standings(stage.id)
        group_standings = standings[group.id]
        
        # Team 0: 2 wins = 6 points, goal_diff = +6 (7 for, 1 against)
        # Team 1: 1 win, 1 loss = 3 points, goal_diff = 0 (2 for, 2 against)
        # Team 2: 2 losses = 0 points, goal_diff = -6 (0 for, 6 against)
        assert group_standings[0]["participant_id"] == teams[0].id
        assert group_standings[0]["points"] == Decimal('6')
        assert group_standings[0]["goal_diff"] == 6  # 7 for, 1 against
        assert group_standings[0]["rank"] == 1
        
        assert group_standings[1]["participant_id"] == teams[1].id
        assert group_standings[1]["points"] == Decimal('3')
        assert group_standings[1]["goal_diff"] == 0  # 2 for, 2 against
        assert group_standings[1]["rank"] == 2
        assert group_standings[1]["rank"] == 2


@pytest.mark.django_db
class TestExportStandings:
    """Tests for export_standings method (Epic 3.2 requirement)."""
    
    def test_export_standings_json_structure(self, tournament):
        """Should return frontend-friendly JSON structure."""
        # Create 8 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", game=tournament.game.slug)
            for i in range(1, 9)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
        )
        
        GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        json_data = GroupStageService.export_standings(stage.id)
        
        assert "groups" in json_data
        assert len(json_data["groups"]) == 2
        
        # Check structure of first group
        group_data = json_data["groups"][0]
        assert "group_id" in group_data
        assert "name" in group_data
        assert "standings" in group_data
        
        # Check standings structure
        if group_data["standings"]:
            standing = group_data["standings"][0]
            assert "participant_id" in standing
            assert "rank" in standing
            assert "points" in standing
            assert "wins" in standing
            assert "tiebreaker" in standing
    
    def test_export_standings_ordering(self, tournament):
        """Should maintain correct rank ordering in export."""
        # Create 3 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", game=tournament.game.slug)
            for i in range(1, 4)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=1,
            group_size=3,
        )
        
        group = Group.objects.get(tournament=tournament)
        
        GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        # Create matches with clear winner
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=teams[0].id,
            participant2_id=teams[1].id,
            participant1_score=3,
            participant2_score=0,
            winner_id=teams[0].id,
            loser_id=teams[1].id,
            state=Match.COMPLETED,
            lobby_info={"group_id": group.id},
        )
        
        json_data = GroupStageService.export_standings(stage.id)
        standings = json_data["groups"][0]["standings"]
        
        # First place should have the winning team
        assert standings[0]["participant_id"] == teams[0].id
        assert standings[0]["rank"] == 1
        assert isinstance(standings[0]["points"], (int, float))  # Check it's numeric
    
    def test_export_standings_numeric_serialization(self, tournament):
        """Should ensure all numeric fields are JSON-serializable."""
        import json
        
        # Create 2 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", game=tournament.game.slug)
            for i in range(1, 3)
        ]
        
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=1,
            group_size=2,
            advancement_count_per_group=1,  # Must be less than group_size
        )
        
        GroupStageService.auto_balance_groups(
            stage_id=stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        json_data = GroupStageService.export_standings(stage.id)
        
        # Should be JSON-serializable (no Decimal objects)
        try:
            json.dumps(json_data)
        except TypeError as e:
            pytest.fail(f"Export is not JSON-serializable: {e}")
