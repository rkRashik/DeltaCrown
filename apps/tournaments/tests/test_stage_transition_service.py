"""
Tests for StageTransitionService (Epic 3.4)

Tests the 2 core methods:
- calculate_advancement
- generate_next_stage
"""

import pytest
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.tournaments.models import (
    Tournament,
    TournamentStage,
    GroupStage,
    Group,
    GroupStanding,
    Match,
    Game,
)
from apps.teams.models import Team
from apps.tournaments.services.group_stage_service import GroupStageService
from apps.tournaments.services.stage_transition_service import StageTransitionService

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
        name="Multi-Stage Tournament",
        game=game,
        organizer=organizer,
        max_participants=16,
        registration_start=timezone.now(),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=8),
        tournament_end=timezone.now() + timedelta(days=10),
    )


@pytest.mark.django_db
class TestCalculateAdvancement:
    """Tests for calculate_advancement method."""
    
    def test_calculate_advancement_top_n_per_group(self, tournament):
        """Should advance top 2 from each group correctly."""
        # Create 8 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 9)
        ]
        
        # Create group stage
        group_stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
            advancement_count_per_group=2,
        )
        
        # Create TournamentStage linked to GroupStage
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            order=1,
            format=TournamentStage.FORMAT_ROUND_ROBIN,
            advancement_criteria=TournamentStage.ADVANCEMENT_TOP_N_PER_GROUP,
            state=TournamentStage.STATE_COMPLETED,
            group_stage=group_stage,
        )
        
        # Assign participants
        GroupStageService.auto_balance_groups(
            stage_id=group_stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        # Manually set standings for Group A and Group B
        groups = list(Group.objects.filter(tournament=tournament).order_by('display_order'))
        group_a, group_b = groups[0], groups[1]
        
        # Group A: team[0] (6pts), team[3] (3pts), team[4] (1pt), team[7] (0pts)
        GroupStanding.objects.filter(group=group_a, team_id=teams[0].id).update(rank=1, points=6, matches_won=2)
        GroupStanding.objects.filter(group=group_a, team_id=teams[3].id).update(rank=2, points=3, matches_won=1)
        GroupStanding.objects.filter(group=group_a, team_id=teams[4].id).update(rank=3, points=1, matches_won=0)
        GroupStanding.objects.filter(group=group_a, team_id=teams[7].id).update(rank=4, points=0, matches_won=0)
        
        # Group B: team[1] (6pts), team[2] (3pts), team[5] (1pt), team[6] (0pts)
        GroupStanding.objects.filter(group=group_b, team_id=teams[1].id).update(rank=1, points=6, matches_won=2)
        GroupStanding.objects.filter(group=group_b, team_id=teams[2].id).update(rank=2, points=3, matches_won=1)
        GroupStanding.objects.filter(group=group_b, team_id=teams[5].id).update(rank=3, points=1, matches_won=0)
        GroupStanding.objects.filter(group=group_b, team_id=teams[6].id).update(rank=4, points=0, matches_won=0)
        
        result = StageTransitionService.calculate_advancement(stage.id)
        
        # Should advance: Group winners (teams[0], teams[1]), then runners-up (teams[3], teams[2])
        assert set(result["advanced"]) == {teams[0].id, teams[1].id, teams[3].id, teams[2].id}
        assert set(result["eliminated"]) == {teams[4].id, teams[7].id, teams[5].id, teams[6].id}
        
        # Check seeding order: group winners first
        assert result["advanced"][:2] == [teams[0].id, teams[1].id] or result["advanced"][:2] == [teams[1].id, teams[0].id]
    
    def test_calculate_advancement_top_n_overall(self, tournament):
        """Should advance top 4 overall across all groups."""
        # Create 8 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 9)
        ]
        
        group_stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
            advancement_count_per_group=2,
        )
        
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            order=1,
            format=TournamentStage.FORMAT_ROUND_ROBIN,
            advancement_criteria=TournamentStage.ADVANCEMENT_TOP_N,
            advancement_count=4,
            state=TournamentStage.STATE_COMPLETED,
            group_stage=group_stage,
        )
        
        GroupStageService.auto_balance_groups(
            stage_id=group_stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        groups = list(Group.objects.filter(tournament=tournament).order_by('display_order'))
        group_a, group_b = groups[0], groups[1]
        
        # Set uneven points (some group winners stronger than others)
        # Group A: teams[0] (9pts), teams[3] (6pts), teams[4] (3pts), teams[7] (0pts)
        GroupStanding.objects.filter(group=group_a, team_id=teams[0].id).update(rank=1, points=9, matches_won=3, goal_difference=5)
        GroupStanding.objects.filter(group=group_a, team_id=teams[3].id).update(rank=2, points=6, matches_won=2, goal_difference=3)
        GroupStanding.objects.filter(group=group_a, team_id=teams[4].id).update(rank=3, points=3, matches_won=1, goal_difference=0)
        GroupStanding.objects.filter(group=group_a, team_id=teams[7].id).update(rank=4, points=0, matches_won=0, goal_difference=-2)
        
        # Group B: teams[1] (6pts), teams[2] (6pts), teams[5] (1pt), teams[6] (0pts)
        GroupStanding.objects.filter(group=group_b, team_id=teams[1].id).update(rank=1, points=6, matches_won=2, goal_difference=2)
        GroupStanding.objects.filter(group=group_b, team_id=teams[2].id).update(rank=2, points=6, matches_won=2, goal_difference=1)
        GroupStanding.objects.filter(group=group_b, team_id=teams[5].id).update(rank=3, points=1, matches_won=0, goal_difference=-1)
        GroupStanding.objects.filter(group=group_b, team_id=teams[6].id).update(rank=4, points=0, matches_won=0, goal_difference=-3)
        
        result = StageTransitionService.calculate_advancement(stage.id)
        
        # Top 4 overall by points: teams[0] (9), teams[3] (6), teams[1] (6), teams[2] (6)
        # Tiebreakers: teams[3] has better goal_diff than teams[1], teams[1] better than teams[2]
        assert set(result["advanced"]) == {teams[0].id, teams[3].id, teams[1].id, teams[2].id}
        assert set(result["eliminated"]) == {teams[4].id, teams[7].id, teams[5].id, teams[6].id}
    
    def test_calculate_advancement_all(self, tournament):
        """Should advance all participants."""
        # Create 8 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 9)
        ]
        
        group_stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
        )
        
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            order=1,
            format=TournamentStage.FORMAT_ROUND_ROBIN,
            advancement_criteria=TournamentStage.ADVANCEMENT_ALL,
            state=TournamentStage.STATE_COMPLETED,
            group_stage=group_stage,
        )
        
        GroupStageService.auto_balance_groups(
            stage_id=group_stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        result = StageTransitionService.calculate_advancement(stage.id)
        
        assert len(result["advanced"]) == 8
        assert len(result["eliminated"]) == 0


@pytest.mark.django_db
class TestGenerateNextStage:
    """Tests for generate_next_stage method."""
    
    def test_generate_next_stage_creates_elim_bracket(self, tournament):
        """Should create single-elim bracket from group stage results."""
        # Create 8 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 9)
        ]
        
        # Create group stage
        group_stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
            advancement_count_per_group=2,
        )
        
        stage1 = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            order=1,
            format=TournamentStage.FORMAT_ROUND_ROBIN,
            advancement_criteria=TournamentStage.ADVANCEMENT_TOP_N_PER_GROUP,
            state=TournamentStage.STATE_COMPLETED,
            group_stage=group_stage,
        )
        
        stage2 = TournamentStage.objects.create(
            tournament=tournament,
            name="Playoffs",
            order=2,
            format=TournamentStage.FORMAT_SINGLE_ELIM,
            state=TournamentStage.STATE_PENDING,
        )
        
        # Assign and rank participants
        GroupStageService.auto_balance_groups(
            stage_id=group_stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        groups = list(Group.objects.filter(tournament=tournament).order_by('display_order'))
        GroupStanding.objects.filter(group=groups[0], team_id=teams[0].id).update(rank=1, points=6)
        GroupStanding.objects.filter(group=groups[0], team_id=teams[3].id).update(rank=2, points=3)
        GroupStanding.objects.filter(group=groups[1], team_id=teams[1].id).update(rank=1, points=6)
        GroupStanding.objects.filter(group=groups[1], team_id=teams[2].id).update(rank=2, points=3)
        
        # Generate next stage
        next_stage = StageTransitionService.generate_next_stage(stage1.id)
        
        assert next_stage.id == stage2.id
        assert next_stage.state == TournamentStage.STATE_ACTIVE
        
        # Should create matches (placeholder for MVP)
        matches = Match.objects.filter(tournament=tournament, lobby_info__stage_id=stage2.id)
        assert matches.count() > 0
    
    def test_generate_next_stage_marks_states(self, tournament):
        """Should update current stage to completed and next to active."""
        # Create 4 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 5)
        ]
        
        group_stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=1,
            group_size=4,
            advancement_count_per_group=4,
        )
        
        stage1 = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            order=1,
            format=TournamentStage.FORMAT_ROUND_ROBIN,
            advancement_criteria=TournamentStage.ADVANCEMENT_ALL,
            state=TournamentStage.STATE_COMPLETED,
            group_stage=group_stage,
        )
        
        stage2 = TournamentStage.objects.create(
            tournament=tournament,
            name="Finals",
            order=2,
            format=TournamentStage.FORMAT_SINGLE_ELIM,
            state=TournamentStage.STATE_PENDING,
        )
        
        GroupStageService.auto_balance_groups(
            stage_id=group_stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        next_stage = StageTransitionService.generate_next_stage(stage1.id)
        
        next_stage.refresh_from_db()
        assert next_stage.state == TournamentStage.STATE_ACTIVE
        assert next_stage.start_date is not None
    
    def test_generate_next_stage_creates_group_stage(self, tournament):
        """Should create another group stage if next format is round_robin."""
        # Create 16 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 17)
        ]
        
        # Stage 1: Qualifying groups
        group_stage1 = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=4,
            group_size=4,
            advancement_count_per_group=2,
        )
        
        stage1 = TournamentStage.objects.create(
            tournament=tournament,
            name="Qualifying",
            order=1,
            format=TournamentStage.FORMAT_ROUND_ROBIN,
            advancement_criteria=TournamentStage.ADVANCEMENT_TOP_N_PER_GROUP,
            state=TournamentStage.STATE_COMPLETED,
            group_stage=group_stage1,
        )
        
        # Stage 2: Main groups (round-robin with GroupStage)
        stage2 = TournamentStage.objects.create(
            tournament=tournament,
            name="Main Stage",
            order=2,
            format=TournamentStage.FORMAT_ROUND_ROBIN,
            state=TournamentStage.STATE_PENDING,
        )
        
        # Assign 16 participants
        GroupStageService.auto_balance_groups(
            stage_id=group_stage1.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        # Rank top 2 per group
        groups = Group.objects.filter(tournament=tournament).order_by('display_order')
        for idx, group in enumerate(groups):
            standings = GroupStanding.objects.filter(group=group).order_by('id')
            for rank, standing in enumerate(standings[:2], start=1):
                standing.rank = rank
                standing.points = 6 - rank
                standing.save()
        
        # Capture group IDs before generating next stage (QuerySet would re-evaluate later)
        old_group_ids = list(groups.values_list('id', flat=True))
        
        next_stage = StageTransitionService.generate_next_stage(stage1.id)
        
        # Should create GroupStage for stage2
        stage2.refresh_from_db()
        assert stage2.group_stage is not None
        assert stage2.state == TournamentStage.STATE_ACTIVE
        
        # Should have created groups
        new_groups = Group.objects.filter(tournament=tournament).exclude(
            id__in=old_group_ids
        )
        assert new_groups.count() > 0
    
    def test_generate_next_stage_final_stage(self, tournament):
        """Should return None when no next stage exists."""
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Finals",
            order=1,
            format=TournamentStage.FORMAT_SINGLE_ELIM,
            advancement_criteria=TournamentStage.ADVANCEMENT_TOP_N,
            advancement_count=1,
            state=TournamentStage.STATE_COMPLETED,
        )
        
        # No stage with order=2
        result = StageTransitionService.generate_next_stage(stage.id)
        
        assert result is None
    
    def test_generate_next_stage_requires_completion(self, tournament):
        """Should raise error if current stage not completed."""
        stage1 = TournamentStage.objects.create(
            tournament=tournament,
            name="Stage 1",
            order=1,
            format=TournamentStage.FORMAT_ROUND_ROBIN,
            state=TournamentStage.STATE_ACTIVE,  # Not completed
        )
        
        TournamentStage.objects.create(
            tournament=tournament,
            name="Stage 2",
            order=2,
            format=TournamentStage.FORMAT_SINGLE_ELIM,
            state=TournamentStage.STATE_PENDING,
        )
        
        with pytest.raises(ValidationError, match="must be completed"):
            StageTransitionService.generate_next_stage(stage1.id)


@pytest.mark.django_db
class TestSwissAdvancement:
    """Tests for Swiss → Top Cut advancement (Epic 3.4 requirement)."""
    
    def test_swiss_advancement_top_n(self, tournament):
        """Should advance top N from Swiss standings."""
        # Create 8 real teams
        teams = [
            Team.objects.create(name=f"Swiss Team {i}", tag=f"ST{i}", game=tournament.game.slug)
            for i in range(1, 9)
        ]
        
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Swiss Rounds",
            order=1,
            format=TournamentStage.FORMAT_SWISS,
            advancement_criteria=TournamentStage.ADVANCEMENT_TOP_N,
            advancement_count=4,
            state=TournamentStage.STATE_COMPLETED,
        )
        
        # Create Swiss matches with results
        # Team 0: 2 wins
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=teams[0].id,
            participant2_id=teams[4].id,
            participant1_score=2,
            participant2_score=1,
            winner_id=teams[0].id,
            loser_id=teams[4].id,
            state=Match.COMPLETED,
            lobby_info={"stage_id": stage.id},
        )
        Match.objects.create(
            tournament=tournament,
            round_number=2,
            match_number=1,
            participant1_id=teams[0].id,
            participant2_id=teams[5].id,
            participant1_score=2,
            participant2_score=0,
            winner_id=teams[0].id,
            loser_id=teams[5].id,
            state=Match.COMPLETED,
            lobby_info={"stage_id": stage.id},
        )
        
        # Team 1: 1 win, 1 loss
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=2,
            participant1_id=teams[1].id,
            participant2_id=teams[6].id,
            participant1_score=1,
            participant2_score=0,
            winner_id=teams[1].id,
            loser_id=teams[6].id,
            state=Match.COMPLETED,
            lobby_info={"stage_id": stage.id},
        )
        Match.objects.create(
            tournament=tournament,
            round_number=2,
            match_number=2,
            participant1_id=teams[1].id,
            participant2_id=teams[7].id,
            participant1_score=0,
            participant2_score=1,
            winner_id=teams[7].id,
            loser_id=teams[1].id,
            state=Match.COMPLETED,
            lobby_info={"stage_id": stage.id},
        )
        
        # Team 2: 1 win
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=3,
            participant1_id=teams[2].id,
            participant2_id=teams[4].id,
            participant1_score=2,
            participant2_score=1,
            winner_id=teams[2].id,
            loser_id=teams[4].id,
            state=Match.COMPLETED,
            lobby_info={"stage_id": stage.id},
        )
        
        # Team 3: 1 win
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=4,
            participant1_id=teams[3].id,
            participant2_id=teams[5].id,
            participant1_score=1,
            participant2_score=0,
            winner_id=teams[3].id,
            loser_id=teams[5].id,
            state=Match.COMPLETED,
            lobby_info={"stage_id": stage.id},
        )
        
        result = StageTransitionService.calculate_advancement(stage.id)
        
        # Top 4 should be: teams[0] (2pts), then tie at 1pt each
        assert len(result["advanced"]) == 4
        assert teams[0].id in result["advanced"]  # Clear winner with 2 points
    
    def test_swiss_advancement_tiebreaker(self, tournament):
        """Should use score differential for tiebreakers in Swiss."""
        # Create 4 real teams
        teams = [
            Team.objects.create(name=f"Tiebreak Team {i}", tag=f"TB{i}", game=tournament.game.slug)
            for i in range(1, 5)
        ]
        
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Swiss Rounds",
            order=1,
            format=TournamentStage.FORMAT_SWISS,
            advancement_criteria=TournamentStage.ADVANCEMENT_TOP_N,
            advancement_count=2,
            state=TournamentStage.STATE_COMPLETED,
        )
        
        # Both participants have 1 win, but different score margins
        # Team 0: Big win
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=teams[0].id,
            participant2_id=teams[2].id,
            participant1_score=13,
            participant2_score=0,
            winner_id=teams[0].id,
            loser_id=teams[2].id,
            state=Match.COMPLETED,
            lobby_info={"stage_id": stage.id},
        )
        
        # Team 1: Small win
        Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=2,
            participant1_id=teams[1].id,
            participant2_id=teams[3].id,
            participant1_score=1,
            participant2_score=0,
            winner_id=teams[1].id,
            loser_id=teams[3].id,
            state=Match.COMPLETED,
            lobby_info={"stage_id": stage.id},
        )
        
        result = StageTransitionService.calculate_advancement(stage.id)
        
        # Team 0 should rank higher due to better score differential
        assert result["advanced"][0] == teams[0].id


@pytest.mark.django_db
class TestBracketEngineIntegration:
    """Tests for BracketEngineService integration (Epic 3.4 requirement)."""
    
    def test_generate_next_stage_calls_bracket_engine(self, tournament):
        """Should delegate to BracketEngineService for bracket generation."""
        # Create 4 real teams
        teams = [
            Team.objects.create(name=f"Bracket Team {i}", tag=f"BT{i}", game=tournament.game.slug)
            for i in range(1, 5)
        ]
        
        group_stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=1,
            group_size=4,
            advancement_count_per_group=4,
        )
        
        stage1 = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            order=1,
            format=TournamentStage.FORMAT_ROUND_ROBIN,
            advancement_criteria=TournamentStage.ADVANCEMENT_ALL,
            state=TournamentStage.STATE_COMPLETED,
            group_stage=group_stage,
        )
        
        stage2 = TournamentStage.objects.create(
            tournament=tournament,
            name="Playoffs",
            order=2,
            format=TournamentStage.FORMAT_SINGLE_ELIM,
            state=TournamentStage.STATE_PENDING,
        )
        
        GroupStageService.auto_balance_groups(
            stage_id=group_stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        # Generate next stage (should call BracketEngineService)
        next_stage = StageTransitionService.generate_next_stage(stage1.id)
        
        # Should have created matches via bracket engine
        matches = Match.objects.filter(tournament=tournament, lobby_info__stage_id=stage2.id)
        assert matches.count() > 0  # Bracket engine should create matches
    
    def test_bracket_generation_match_count(self, tournament):
        """Should generate correct number of matches via BracketEngineService."""
        # Create 8 real teams
        teams = [
            Team.objects.create(name=f"Count Team {i}", tag=f"CT{i}", game=tournament.game.slug)
            for i in range(1, 9)
        ]
        
        group_stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
            advancement_count_per_group=2,
        )
        
        stage1 = TournamentStage.objects.create(
            tournament=tournament,
            name="Groups",
            order=1,
            format=TournamentStage.FORMAT_ROUND_ROBIN,
            advancement_criteria=TournamentStage.ADVANCEMENT_TOP_N_PER_GROUP,
            state=TournamentStage.STATE_COMPLETED,
            group_stage=group_stage,
        )
        
        stage2 = TournamentStage.objects.create(
            tournament=tournament,
            name="Semifinals",
            order=2,
            format=TournamentStage.FORMAT_SINGLE_ELIM,
            state=TournamentStage.STATE_PENDING,
        )
        
        GroupStageService.auto_balance_groups(
            stage_id=group_stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        # Manually set group standings
        groups = list(Group.objects.filter(tournament=tournament).order_by('display_order'))
        GroupStanding.objects.filter(group=groups[0], team_id=teams[0].id).update(rank=1, points=6)
        GroupStanding.objects.filter(group=groups[0], team_id=teams[3].id).update(rank=2, points=3)
        GroupStanding.objects.filter(group=groups[1], team_id=teams[1].id).update(rank=1, points=6)
        GroupStanding.objects.filter(group=groups[1], team_id=teams[2].id).update(rank=2, points=3)
        
        next_stage = StageTransitionService.generate_next_stage(stage1.id)
        
        # 4 teams advancing → single-elim should create semifinals (2 matches)
        matches = Match.objects.filter(tournament=tournament, lobby_info__stage_id=stage2.id)
        # BracketEngineService should handle this properly
        assert matches.count() >= 2
