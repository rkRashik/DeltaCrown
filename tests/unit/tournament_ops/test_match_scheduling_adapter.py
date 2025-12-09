"""
Unit Tests for MatchSchedulingAdapter - Phase 7, Epic 7.2

Tests for MatchSchedulingAdapter ORM access layer.

Test Coverage:
- Retrieving matches requiring scheduling
- Updating match schedules (single and bulk)
- Fetching stage time windows
- Conflict detection
- Audit logging

Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock

from apps.tournament_ops.adapters.match_scheduling_adapter import MatchSchedulingAdapter
from apps.tournament_ops.dtos.scheduling import MatchSchedulingItemDTO


@pytest.fixture
def adapter():
    """Create MatchSchedulingAdapter instance."""
    return MatchSchedulingAdapter()


@pytest.mark.django_db
class TestGetMatchesRequiringScheduling:
    """Tests for get_matches_requiring_scheduling method."""
    
    def test_get_all_matches(self, adapter):
        """Test retrieving all schedulable matches."""
        from apps.tournaments.models import Tournament, TournamentStage, Match
        from apps.games.models import Game
        
        # Create test data
        game = Game.objects.create(name="Test Game", slug="test-game")
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=game,
            max_teams=8
        )
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        match = Match.objects.create(
            tournament=tournament,
            stage=stage,
            round_number=1,
            match_number=1,
            state='pending'
        )
        
        # Get matches
        matches = adapter.get_matches_requiring_scheduling()
        
        assert len(matches) >= 1
        match_dto = next((m for m in matches if m.match_id == match.id), None)
        assert match_dto is not None
        assert match_dto.tournament_name == "Test Tournament"
        assert match_dto.stage_name == "Group Stage"
    
    def test_filter_by_tournament(self, adapter):
        """Test filtering matches by tournament_id."""
        from apps.tournaments.models import Tournament, TournamentStage, Match
        from apps.games.models import Game
        
        game = Game.objects.create(name="Test Game", slug="test-game")
        tournament1 = Tournament.objects.create(
            name="Tournament 1",
            game=game,
            max_teams=8
        )
        tournament2 = Tournament.objects.create(
            name="Tournament 2",
            game=game,
            max_teams=8
        )
        
        stage1 = TournamentStage.objects.create(
            tournament=tournament1,
            name="Stage 1",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        stage2 = TournamentStage.objects.create(
            tournament=tournament2,
            name="Stage 2",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        match1 = Match.objects.create(
            tournament=tournament1,
            stage=stage1,
            round_number=1,
            match_number=1,
            state='pending'
        )
        match2 = Match.objects.create(
            tournament=tournament2,
            stage=stage2,
            round_number=1,
            match_number=1,
            state='pending'
        )
        
        # Filter by tournament1
        matches = adapter.get_matches_requiring_scheduling(tournament_id=tournament1.id)
        
        match_ids = [m.match_id for m in matches]
        assert match1.id in match_ids
        assert match2.id not in match_ids
    
    def test_filter_unscheduled_only(self, adapter):
        """Test filtering for unscheduled matches only."""
        from apps.tournaments.models import Tournament, TournamentStage, Match
        from apps.games.models import Game
        
        game = Game.objects.create(name="Test Game", slug="test-game")
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=game,
            max_teams=8
        )
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        # Unscheduled match
        match1 = Match.objects.create(
            tournament=tournament,
            stage=stage,
            round_number=1,
            match_number=1,
            state='pending',
            scheduled_time=None
        )
        
        # Scheduled match
        match2 = Match.objects.create(
            tournament=tournament,
            stage=stage,
            round_number=1,
            match_number=2,
            state='scheduled',
            scheduled_time=datetime.now(timezone.utc) + timedelta(days=1)
        )
        
        # Get unscheduled only
        matches = adapter.get_matches_requiring_scheduling(unscheduled_only=True)
        
        match_ids = [m.match_id for m in matches]
        assert match1.id in match_ids
        assert match2.id not in match_ids


@pytest.mark.django_db
class TestUpdateMatchSchedule:
    """Tests for update_match_schedule method."""
    
    def test_update_schedule_success(self, adapter):
        """Test successfully updating a match schedule."""
        from apps.tournaments.models import Tournament, TournamentStage, Match
        from apps.games.models import Game
        
        game = Game.objects.create(name="Test Game", slug="test-game")
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=game,
            max_teams=8
        )
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        match = Match.objects.create(
            tournament=tournament,
            stage=stage,
            round_number=1,
            match_number=1,
            state='pending'
        )
        
        scheduled_time = datetime.now(timezone.utc) + timedelta(days=2)
        
        # Update schedule
        result = adapter.update_match_schedule(
            match.id,
            scheduled_time,
            999
        )
        
        # Verify result DTO
        assert isinstance(result, MatchSchedulingItemDTO)
        assert result.match_id == match.id
        assert result.scheduled_time == scheduled_time
        
        # Verify database updated
        match.refresh_from_db()
        assert match.scheduled_time == scheduled_time
    
    def test_update_schedule_match_not_found(self, adapter):
        """Test updating non-existent match raises ValueError."""
        scheduled_time = datetime.now(timezone.utc) + timedelta(days=2)
        
        with pytest.raises(ValueError, match="Match 99999 not found"):
            adapter.update_match_schedule(99999, scheduled_time, 999)
    
    def test_update_schedule_invalid_state(self, adapter):
        """Test updating match in non-schedulable state raises ValueError."""
        from apps.tournaments.models import Tournament, TournamentStage, Match
        from apps.games.models import Game
        
        game = Game.objects.create(name="Test Game", slug="test-game")
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=game,
            max_teams=8
        )
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        # Match already completed
        match = Match.objects.create(
            tournament=tournament,
            stage=stage,
            round_number=1,
            match_number=1,
            state='completed'
        )
        
        scheduled_time = datetime.now(timezone.utc) + timedelta(days=2)
        
        with pytest.raises(ValueError, match="cannot be rescheduled"):
            adapter.update_match_schedule(match.id, scheduled_time, 999)


@pytest.mark.django_db
class TestBulkUpdateMatchSchedule:
    """Tests for bulk_update_match_schedule method."""
    
    def test_bulk_shift_success(self, adapter):
        """Test successfully bulk shifting matches in a stage."""
        from apps.tournaments.models import Tournament, TournamentStage, Match
        from apps.games.models import Game
        
        game = Game.objects.create(name="Test Game", slug="test-game")
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=game,
            max_teams=8
        )
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        
        # Create scheduled matches
        match1 = Match.objects.create(
            tournament=tournament,
            stage=stage,
            round_number=1,
            match_number=1,
            state='scheduled',
            scheduled_time=base_time
        )
        match2 = Match.objects.create(
            tournament=tournament,
            stage=stage,
            round_number=1,
            match_number=2,
            state='scheduled',
            scheduled_time=base_time + timedelta(hours=1)
        )
        
        # Bulk shift by 30 minutes
        result = adapter.bulk_update_match_schedule(stage.id, 30, 999)
        
        # Verify result
        assert result['shifted_count'] == 2
        assert match1.id in result['match_ids']
        assert match2.id in result['match_ids']
        
        # Verify database updated
        match1.refresh_from_db()
        match2.refresh_from_db()
        
        assert match1.scheduled_time == base_time + timedelta(minutes=30)
        assert match2.scheduled_time == base_time + timedelta(hours=1, minutes=30)
    
    def test_bulk_shift_negative_delta(self, adapter):
        """Test bulk shifting matches earlier (negative delta)."""
        from apps.tournaments.models import Tournament, TournamentStage, Match
        from apps.games.models import Game
        
        game = Game.objects.create(name="Test Game", slug="test-game")
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=game,
            max_teams=8
        )
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        
        match = Match.objects.create(
            tournament=tournament,
            stage=stage,
            round_number=1,
            match_number=1,
            state='scheduled',
            scheduled_time=base_time
        )
        
        # Shift earlier by 60 minutes
        result = adapter.bulk_update_match_schedule(stage.id, -60, 999)
        
        assert result['shifted_count'] == 1
        
        match.refresh_from_db()
        assert match.scheduled_time == base_time - timedelta(hours=1)


@pytest.mark.django_db
class TestGetStageTimeWindow:
    """Tests for get_stage_time_window method."""
    
    def test_get_time_window_basic(self, adapter):
        """Test retrieving stage time window."""
        from apps.tournaments.models import Tournament, TournamentStage
        from apps.games.models import Game
        
        game = Game.objects.create(name="Test Game", slug="test-game")
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=game,
            max_teams=8
        )
        
        start = datetime(2025, 12, 15, 9, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 17, 18, 0, 0, tzinfo=timezone.utc)
        
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            start_date=start,
            end_date=end
        )
        
        result = adapter.get_stage_time_window(stage.id)
        
        assert result['start_date'] == start
        assert result['end_date'] == end
        assert 'blackout_periods' in result
    
    def test_get_time_window_not_found(self, adapter):
        """Test retrieving time window for non-existent stage."""
        with pytest.raises(ValueError, match="Stage 99999 not found"):
            adapter.get_stage_time_window(99999)


@pytest.mark.django_db
class TestConflictDetection:
    """Tests for get_conflicts_for_match method."""
    
    def test_detect_team_conflict(self, adapter):
        """Test detecting team scheduling conflict."""
        from apps.tournaments.models import Tournament, TournamentStage, Match, TournamentParticipant
        from apps.games.models import Game
        from apps.teams.models import Team
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.create_user(username='owner', email='owner@test.com')
        
        game = Game.objects.create(name="Test Game", slug="test-game")
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=game,
            max_teams=8
        )
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        team1 = Team.objects.create(name="Team Alpha", owner=user)
        participant1 = TournamentParticipant.objects.create(
            tournament=tournament,
            team=team1,
            status='confirmed'
        )
        
        # Existing scheduled match with team1
        match1 = Match.objects.create(
            tournament=tournament,
            stage=stage,
            round_number=1,
            match_number=1,
            state='scheduled',
            scheduled_time=datetime(2025, 12, 15, 14, 0, 0, tzinfo=timezone.utc),
            participant1=participant1
        )
        
        # New match also with team1
        match2 = Match.objects.create(
            tournament=tournament,
            stage=stage,
            round_number=1,
            match_number=2,
            state='pending',
            participant1=participant1
        )
        
        # Detect conflict (overlapping time)
        proposed_time = datetime(2025, 12, 15, 14, 30, 0, tzinfo=timezone.utc)
        
        conflicts = adapter.get_conflicts_for_match(match2.id, proposed_time, 60)
        
        # Should detect team conflict
        assert len(conflicts) > 0
        team_conflicts = [c for c in conflicts if c.conflict_type == 'team_conflict']
        assert len(team_conflicts) > 0
        assert team_conflicts[0].severity == 'warning'
    
    def test_no_conflicts(self, adapter):
        """Test no conflicts when time slots don't overlap."""
        from apps.tournaments.models import Tournament, TournamentStage, Match
        from apps.games.models import Game
        
        game = Game.objects.create(name="Test Game", slug="test-game")
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=game,
            max_teams=8
        )
        stage = TournamentStage.objects.create(
            tournament=tournament,
            name="Group Stage",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        match = Match.objects.create(
            tournament=tournament,
            stage=stage,
            round_number=1,
            match_number=1,
            state='pending'
        )
        
        # Propose time in the future with no other matches
        proposed_time = datetime.now(timezone.utc) + timedelta(days=5)
        
        conflicts = adapter.get_conflicts_for_match(match.id, proposed_time, 60)
        
        # Should have no conflicts
        assert len(conflicts) == 0
