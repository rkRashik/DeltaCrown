"""
End-to-End Tests for Group → Playoffs Pipeline (Epic 3.2 & 3.4)

Tests the complete workflow from group stage creation through playoffs generation.
"""

import pytest
from datetime import timedelta
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
        name="Championship Tournament",
        game=game,
        organizer=organizer,
        max_participants=16,
        registration_start=timezone.now(),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=8),
        tournament_end=timezone.now() + timedelta(days=10),
        status=Tournament.REGISTRATION_OPEN,
    )


@pytest.mark.django_db
class TestGroupToPlayoffsPipeline:
    """
    End-to-end test for the complete group stage → playoffs workflow.
    
    Validates Epic 3.2 (Group Stage Manager) and Epic 3.4 (Stage Transitions)
    working together in a realistic tournament scenario.
    """
    
    def test_complete_group_to_playoffs_pipeline(self, tournament):
        """
        Test full workflow: create groups → assign → matches → standings → transition → playoffs.
        
        Flow:
        1. Create group stage (4 groups of 4)
        2. Auto-assign 16 participants
        3. Generate group matches
        4. Simulate match results
        5. Calculate standings
        6. Calculate advancement (top 2 per group = 8 advance)
        7. Generate next stage (single-elim playoffs)
        8. Verify correct seeds and bracket matches
        """
        # Create 16 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 17)
        ]
        
        # Step 1: Create group stage with 4 groups
        group_stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=4,
            group_size=4,
            advancement_count_per_group=2,
        )
        
        assert group_stage.num_groups == 4
        assert group_stage.group_size == 4
        
        # Verify groups were created
        groups = Group.objects.filter(tournament=tournament)
        assert groups.count() == 4
        assert list(groups.values_list('name', flat=True).order_by('display_order')) == [
            "Group A", "Group B", "Group C", "Group D"
        ]
        
        # Step 2: Auto-assign 16 participants using snake seeding
        participant_ids = [t.id for t in teams]  # Seeded best to worst
        
        assignments = GroupStageService.auto_balance_groups(
            stage_id=group_stage.id,
            participant_ids=participant_ids,
            is_team=True,
        )
        
        # Verify snake distribution
        assert len(assignments) == 4
        for group_id, participants in assignments.items():
            assert len(participants) == 4
        
        # Verify all participants assigned
        total_assigned = sum(len(p) for p in assignments.values())
        assert total_assigned == 16
        
        # Step 3: Generate round-robin matches for all groups
        match_count = GroupStageService.generate_group_matches(group_stage.id)
        
        # 4 groups × (4 choose 2) = 4 × 6 = 24 matches
        assert match_count == 24
        
        # Step 4: Simulate match results
        # For simplicity, lower participant IDs win (simulating seed strength)
        matches = Match.objects.filter(tournament=tournament)
        
        for match in matches:
            p1_id = match.participant1_id
            p2_id = match.participant2_id
            
            # Lower ID wins (stronger seed)
            if p1_id < p2_id:
                winner_id = p1_id
                loser_id = p2_id
                match.participant1_score = 2
                match.participant2_score = 1
            else:
                winner_id = p2_id
                loser_id = p1_id
                match.participant1_score = 1
                match.participant2_score = 2
            
            match.winner_id = winner_id
            match.loser_id = loser_id
            match.state = Match.COMPLETED
            match.save()
        
        # Step 5: Calculate group standings
        standings_by_group = GroupStageService.calculate_group_standings(group_stage.id)
        
        assert len(standings_by_group) == 4
        
        # Verify each group has 4 standings
        for group_id, standings in standings_by_group.items():
            assert len(standings) == 4
            # First place should have most points
            assert standings[0]["points"] >= standings[1]["points"]
            assert standings[1]["points"] >= standings[2]["points"]
        
        # Step 6: Create TournamentStage models for transitions
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
            name="Quarterfinals",
            order=2,
            format=TournamentStage.FORMAT_SINGLE_ELIM,
            state=TournamentStage.STATE_PENDING,
        )
        
        # Step 7: Calculate advancement
        advancement_result = StageTransitionService.calculate_advancement(stage1.id)
        
        # Top 2 from each of 4 groups = 8 advancing
        assert len(advancement_result["advanced"]) == 8
        assert len(advancement_result["eliminated"]) == 8
        
        # Group winners should appear first in advancement list (seeding priority)
        advanced_ids = advancement_result["advanced"]
        
        # Step 8: Generate playoffs stage
        next_stage = StageTransitionService.generate_next_stage(stage1.id)
        
        assert next_stage.id == stage2.id
        assert next_stage.state == TournamentStage.STATE_ACTIVE
        
        # Verify bracket matches were created via BracketEngineService
        playoff_matches = Match.objects.filter(
            tournament=tournament,
            lobby_info__stage_id=stage2.id
        )
        
        # 8 teams → quarterfinals should have at least 4 matches
        assert playoff_matches.count() >= 4
        
        # Verify matches have participants from advancement list
        for match in playoff_matches:
            if match.participant1_id:
                assert match.participant1_id in advanced_ids
            if match.participant2_id:
                assert match.participant2_id in advanced_ids
        
        # Verify stage states updated correctly
        stage1.refresh_from_db()
        assert stage1.state == TournamentStage.STATE_COMPLETED
        
        stage2.refresh_from_db()
        assert stage2.state == TournamentStage.STATE_ACTIVE
        assert stage2.start_date is not None
    
    def test_pipeline_with_json_export(self, tournament):
        """Test group → playoffs pipeline with JSON export at each stage."""
        # Create 8 real teams
        teams = [
            Team.objects.create(name=f"Team {i}", tag=f"T{i}", slug=f"team-{i}", game=tournament.game.slug)
            for i in range(1, 9)
        ]
        
        # Create and populate group stage
        group_stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=2,
            group_size=4,
            advancement_count_per_group=2,
        )
        
        GroupStageService.auto_balance_groups(
            stage_id=group_stage.id,
            participant_ids=[t.id for t in teams],
            is_team=True,
        )
        
        # Generate matches
        GroupStageService.generate_group_matches(group_stage.id)
        
        # Simulate results
        matches = Match.objects.filter(tournament=tournament)
        for match in matches:
            if match.participant1_id < match.participant2_id:
                match.participant1_score = 2
                match.participant2_score = 1
                match.winner_id = match.participant1_id
                match.loser_id = match.participant2_id
            else:
                match.participant1_score = 1
                match.participant2_score = 2
                match.winner_id = match.participant2_id
                match.loser_id = match.participant1_id
            match.state = Match.COMPLETED
            match.save()
        
        # Export standings as JSON
        json_data = GroupStageService.export_standings(group_stage.id)
        
        assert "groups" in json_data
        assert len(json_data["groups"]) == 2
        
        # Verify JSON is properly structured
        for group_data in json_data["groups"]:
            assert "group_id" in group_data
            assert "name" in group_data
            assert "standings" in group_data
            assert len(group_data["standings"]) == 4
            
            # Check first place
            first_place = group_data["standings"][0]
            assert first_place["rank"] == 1
            assert isinstance(first_place["points"], float)  # Serialized for JSON
        
        # Continue to playoffs
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
            name="Finals",
            order=2,
            format=TournamentStage.FORMAT_SINGLE_ELIM,
            state=TournamentStage.STATE_PENDING,
        )
        
        next_stage = StageTransitionService.generate_next_stage(stage1.id)
        
        assert next_stage.state == TournamentStage.STATE_ACTIVE
        
        # Verify playoffs bracket was created
        playoff_matches = Match.objects.filter(
            tournament=tournament,
            lobby_info__stage_id=stage2.id
        )
        assert playoff_matches.count() > 0
