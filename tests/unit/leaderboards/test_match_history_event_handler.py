"""
Unit Tests for Match History Event Handlers

Phase 8, Epic 8.4: Match History Engine
Tests event handler integration for MatchCompletedEvent → history recording.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from apps.common.events import Event
from apps.core.events.events import MatchCompletedEvent
from apps.leaderboards.event_handlers import handle_match_completed_for_stats


@pytest.mark.django_db
class TestMatchHistoryEventHandler:
    """Test MatchCompletedEvent triggers match history recording."""
    
    @pytest.fixture
    def sample_user(self, django_user_model):
        """Create test user."""
        return django_user_model.objects.create_user(
            username="testplayer",
            email="test@example.com"
        )
    
    @pytest.fixture
    def sample_team(self):
        """Create test team."""
        from apps.organizations.models import Team
        return Team.objects.create(
            name="Test Team",
            tag="TST",
            game="valorant"
        )
    
    @pytest.fixture
    def sample_game(self):
        """Create test game."""
        from apps.tournaments.models import Game
        return Game.objects.create(
            name="Valorant",
            slug="valorant",
            icon="games/valorant.png"
        )
    
    @pytest.fixture
    def sample_tournament(self, sample_game, sample_user):
        """Create test tournament."""
        from apps.tournaments.models import Tournament
        return Tournament.objects.create(
            name="Test Tournament",
            game=sample_game,
            description="Test description",
            status="upcoming",
            organizer=sample_user,
            max_participants=16
        )
    
    @pytest.fixture
    def sample_match(self, sample_tournament, sample_user):
        """Create test user match."""
        from apps.tournaments.models import Match
        match = Match.objects.create(
            tournament=sample_tournament,
            participant1_id=sample_user.id,
            participant2_id=sample_user.id + 1,
            status="completed"
        )
        # Set participant1 to user (not team)
        match.participant1 = sample_user
        match.save()
        return match
    
    @pytest.fixture
    def sample_team_match(self, sample_tournament, sample_team):
        """Create test team match."""
        from apps.tournaments.models import Match
        from apps.organizations.models import Team
        
        # Create opponent team
        opponent_team = Team.objects.create(
            name="Opponent Team",
            captain=sample_team.captain,
            tag="OPP"
        )
        
        match = Match.objects.create(
            tournament=sample_tournament,
            participant1_id=sample_team.id,
            participant2_id=opponent_team.id,
            status="completed"
        )
        # Set participants to teams
        match.participant1 = sample_team
        match.participant2 = opponent_team
        match.save()
        return match
    
    def test_event_handler_records_user_match_history(
        self, sample_match, sample_user
    ):
        """Test event handler creates user match history entry."""
        # Create event
        event = MatchCompletedEvent(
            match_id=sample_match.id,
            winner_id=sample_match.participant1_id,
        )
        
        # Call handler
        with patch('apps.leaderboards.event_handlers.get_tournament_ops_service') as mock_service:
            mock_ops_service = Mock()
            mock_service.return_value = mock_ops_service
            
            # Mock user stats update (already tested in Epic 8.2)
            mock_ops_service.update_user_stats_from_match = Mock()
            
            # Mock match history recording
            mock_ops_service.record_user_match_history = Mock()
            
            handle_match_completed_for_stats(event)
            
            # Verify match history was recorded for both participants
            assert mock_ops_service.record_user_match_history.call_count == 2
            
            # Verify first call (participant1 - winner)
            call_kwargs = mock_ops_service.record_user_match_history.call_args_list[0][1]
            assert call_kwargs["user_id"] == sample_match.participant1_id
            assert call_kwargs["match_id"] == sample_match.id
            assert call_kwargs["is_winner"] is True
    
    def test_event_handler_records_team_match_history_with_elo(
        self, sample_team_match, sample_team
    ):
        """Test event handler creates team match history with ELO tracking."""
        # Create event
        event = MatchCompletedEvent(
            match_id=sample_team_match.id,
            winner_id=sample_team_match.participant1_id,
        )
        
        with patch('apps.leaderboards.event_handlers.get_tournament_ops_service') as mock_service:
            mock_ops_service = Mock()
            mock_service.return_value = mock_ops_service
            
            # Mock team stats/ranking retrieval
            mock_ranking = Mock()
            mock_ranking.elo_rating = 1520
            mock_ops_service.get_team_ranking.return_value = mock_ranking
            
            # Mock team stats update
            mock_ops_service.update_team_stats_from_match = Mock(return_value={
                'ranking': mock_ranking,
                'elo_change': 20
            })
            
            # Mock team history recording
            mock_ops_service.record_team_match_history = Mock()
            
            handle_match_completed_for_stats(event)
            
            # Verify team match history was recorded for both teams
            assert mock_ops_service.record_team_match_history.call_count == 2
            
            # Verify first call (team1 - winner)
            call_kwargs = mock_ops_service.record_team_match_history.call_args_list[0][1]
            assert call_kwargs["team_id"] == sample_team_match.participant1_id
            assert call_kwargs["match_id"] == sample_team_match.id
            assert call_kwargs["is_winner"] is True
            assert "elo_before" in call_kwargs
            assert "elo_change" in call_kwargs
    
    def test_event_handler_sets_had_dispute_flag(
        self, sample_match
    ):
        """Test event handler records had_dispute flag from match."""
        # Set dispute flag on match
        sample_match.had_dispute = True
        sample_match.save()
        
        event = MatchCompletedEvent(
            match_id=sample_match.id,
            winner_id=sample_match.participant1_id,
        )
        
        with patch('apps.leaderboards.event_handlers.get_tournament_ops_service') as mock_service:
            mock_ops_service = Mock()
            mock_service.return_value = mock_ops_service
            mock_ops_service.update_user_stats_from_match = Mock()
            mock_ops_service.record_user_match_history = Mock()
            
            handle_match_completed_for_stats(event)
            
            # Verify had_dispute flag passed
            call_kwargs = mock_ops_service.record_user_match_history.call_args_list[0][1]
            assert call_kwargs["had_dispute"] is True
    
    def test_event_handler_handles_draw_matches(
        self, sample_match
    ):
        """Test event handler correctly handles draw (no winner)."""
        event = MatchCompletedEvent(
            match_id=sample_match.id,
            winner_id=None,  # Draw
        )
        
        with patch('apps.leaderboards.event_handlers.get_tournament_ops_service') as mock_service:
            mock_ops_service = Mock()
            mock_service.return_value = mock_ops_service
            mock_ops_service.update_user_stats_from_match = Mock()
            mock_ops_service.record_user_match_history = Mock()
            
            handle_match_completed_for_stats(event)
            
            # Verify both participants recorded as not winner (draw)
            call_kwargs = mock_ops_service.record_user_match_history.call_args_list[0][1]
            assert call_kwargs["is_winner"] is False
            assert call_kwargs["is_draw"] is True
