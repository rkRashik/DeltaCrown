"""
Unit Tests for TeamStatsService

Phase 8, Epic 8.3: Team Stats & Ranking System
Tests for team stats business logic and ELO calculations.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from apps.tournament_ops.services import TeamStatsService
from apps.tournament_ops.dtos import (
    TeamStatsDTO,
    TeamRankingDTO,
    TeamMatchStatsUpdateDTO,
)


class MockTeamStatsAdapter:
    """Mock adapter for testing service layer."""
    
    def __init__(self):
        self.stats_storage = {}
        self.call_log = []
    
    def get_team_stats(self, team_id, game_slug):
        self.call_log.append(("get_team_stats", team_id, game_slug))
        key = (team_id, game_slug)
        return self.stats_storage.get(key)
    
    def get_all_team_stats(self, team_id):
        self.call_log.append(("get_all_team_stats", team_id))
        return [dto for key, dto in self.stats_storage.items() if key[0] == team_id]
    
    def increment_stats_for_match(self, team_id, game_slug, is_winner, is_draw):
        self.call_log.append(("increment_stats", team_id, game_slug, is_winner, is_draw))
        # Return mock DTO
        return TeamStatsDTO(
            team_id=team_id,
            game_slug=game_slug,
            matches_played=1,
            matches_won=1 if is_winner else 0,
            matches_lost=0 if (is_winner or is_draw) else 1,
            matches_drawn=1 if is_draw else 0,
            tournaments_played=0,
            tournaments_won=0,
            win_rate=Decimal("100.00" if is_winner else "0.00"),
            last_match_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    
    def get_stats_by_game(self, game_slug, limit):
        self.call_log.append(("get_stats_by_game", game_slug, limit))
        return []
    
    def increment_tournament_participation(self, team_id, game_slug, is_winner):
        self.call_log.append(("increment_tournament", team_id, game_slug, is_winner))
        return TeamStatsDTO(
            team_id=team_id,
            game_slug=game_slug,
            matches_played=0,
            matches_won=0,
            matches_lost=0,
            matches_drawn=0,
            tournaments_played=1,
            tournaments_won=1 if is_winner else 0,
            win_rate=Decimal("0.00"),
            last_match_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


class MockTeamRankingAdapter:
    """Mock adapter for ranking operations."""
    
    def __init__(self):
        self.rankings = {}
        self.call_log = []
    
    def get_team_ranking(self, team_id, game_slug):
        self.call_log.append(("get_team_ranking", team_id, game_slug))
        key = (team_id, game_slug)
        return self.rankings.get(key)
    
    def create_or_update_ranking(self, team_id, game_slug, elo_rating=1200):
        self.call_log.append(("create_or_update_ranking", team_id, game_slug, elo_rating))
        ranking = TeamRankingDTO(
            team_id=team_id,
            game_slug=game_slug,
            elo_rating=elo_rating,
            peak_elo=elo_rating,
            games_played=0,
            wins=0,
            losses=0,
            draws=0,
            rank=None,
            last_updated=datetime.now(),
            created_at=datetime.now(),
        )
        self.rankings[(team_id, game_slug)] = ranking
        return ranking
    
    def update_elo_rating(self, team_id, game_slug, elo_change, is_winner, is_draw):
        self.call_log.append(("update_elo_rating", team_id, game_slug, elo_change, is_winner, is_draw))
        current = self.rankings.get((team_id, game_slug))
        new_elo = (current.elo_rating if current else 1200) + elo_change
        
        ranking = TeamRankingDTO(
            team_id=team_id,
            game_slug=game_slug,
            elo_rating=new_elo,
            peak_elo=max(new_elo, current.peak_elo if current else new_elo),
            games_played=(current.games_played if current else 0) + 1,
            wins=(current.wins if current else 0) + (1 if is_winner else 0),
            losses=(current.losses if current else 0) + (1 if not is_winner and not is_draw else 0),
            draws=(current.draws if current else 0) + (1 if is_draw else 0),
            rank=None,
            last_updated=datetime.now(),
            created_at=current.created_at if current else datetime.now(),
        )
        self.rankings[(team_id, game_slug)] = ranking
        return ranking
    
    def get_rankings_by_game(self, game_slug, limit):
        self.call_log.append(("get_rankings_by_game", game_slug, limit))
        return [dto for key, dto in self.rankings.items() if key[1] == game_slug][:limit]
    
    def recalculate_ranks_for_game(self, game_slug):
        self.call_log.append(("recalculate_ranks", game_slug))
        return 0


class TestTeamStatsService:
    """Test suite for TeamStatsService."""
    
    @pytest.fixture
    def service(self):
        """Create service with mock adapters."""
        stats_adapter = MockTeamStatsAdapter()
        ranking_adapter = MockTeamRankingAdapter()
        return TeamStatsService(
            team_stats_adapter=stats_adapter,
            team_ranking_adapter=ranking_adapter,
        )
    
    # =========================================================================
    # ELO Calculation Tests (Core Algorithm Verification)
    # =========================================================================
    
    def test_calculate_elo_change_even_match_win(self, service):
        """Test ELO calculation for evenly matched teams (winner)."""
        # Both teams at 1200 ELO, expected score = 0.5
        # Win gives Actual = 1.0
        # Change = 32 * (1.0 - 0.5) = 16
        elo_change = service.calculate_elo_change(
            team_rating=1200,
            opponent_rating=1200,
            is_winner=True,
            is_draw=False,
        )
        
        assert elo_change == 16
    
    def test_calculate_elo_change_even_match_loss(self, service):
        """Test ELO calculation for evenly matched teams (loser)."""
        # Change = 32 * (0.0 - 0.5) = -16
        elo_change = service.calculate_elo_change(
            team_rating=1200,
            opponent_rating=1200,
            is_winner=False,
            is_draw=False,
        )
        
        assert elo_change == -16
    
    def test_calculate_elo_change_even_match_draw(self, service):
        """Test ELO calculation for evenly matched teams (draw)."""
        # Change = 32 * (0.5 - 0.5) = 0
        elo_change = service.calculate_elo_change(
            team_rating=1200,
            opponent_rating=1200,
            is_winner=False,
            is_draw=True,
        )
        
        assert elo_change == 0
    
    def test_calculate_elo_change_underdog_wins(self, service):
        """Test ELO calculation when underdog (lower rated) wins."""
        # Team 1000 beats Team 1400
        # Expected = 1 / (1 + 10^((1400-1000)/400)) = 1 / (1 + 10) ≈ 0.091
        # Change = 32 * (1.0 - 0.091) ≈ 29
        elo_change = service.calculate_elo_change(
            team_rating=1000,
            opponent_rating=1400,
            is_winner=True,
            is_draw=False,
        )
        
        assert elo_change >= 28 and elo_change <= 30  # Allow rounding variance
    
    def test_calculate_elo_change_favorite_loses(self, service):
        """Test ELO calculation when favorite (higher rated) loses."""
        # Team 1400 loses to Team 1000
        # Expected = 1 / (1 + 10^((1000-1400)/400)) = 1 / (1 + 0.1) ≈ 0.909
        # Change = 32 * (0.0 - 0.909) ≈ -29
        elo_change = service.calculate_elo_change(
            team_rating=1400,
            opponent_rating=1000,
            is_winner=False,
            is_draw=False,
        )
        
        assert elo_change <= -28 and elo_change >= -30
    
    def test_calculate_elo_change_favorite_wins_small_gain(self, service):
        """Test favorite wins against underdog (small ELO gain)."""
        # Team 1400 beats Team 1000
        # Expected ≈ 0.909, Actual = 1.0
        # Change = 32 * (1.0 - 0.909) ≈ 3
        elo_change = service.calculate_elo_change(
            team_rating=1400,
            opponent_rating=1000,
            is_winner=True,
            is_draw=False,
        )
        
        assert elo_change >= 2 and elo_change <= 4
    
    def test_calculate_elo_change_extreme_mismatch(self, service):
        """Test ELO calculation with extreme rating difference."""
        # Team 2000 beats Team 800
        # Expected ≈ 0.99 (very high), Actual = 1.0
        # Change ≈ 0 (minimal gain for expected win)
        elo_change = service.calculate_elo_change(
            team_rating=2000,
            opponent_rating=800,
            is_winner=True,
            is_draw=False,
        )
        
        assert elo_change >= 0 and elo_change <= 1
    
    # =========================================================================
    # Service Method Tests
    # =========================================================================
    
    def test_update_stats_for_match(self, service):
        """Test update_stats_for_match updates both stats and ranking."""
        # Create initial ranking for both teams
        service.team_ranking_adapter.create_or_update_ranking(1, "valorant", 1200)
        service.team_ranking_adapter.create_or_update_ranking(2, "valorant", 1200)
        
        update_dto = TeamMatchStatsUpdateDTO(
            team_id=1,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            opponent_team_id=2,
            opponent_elo=1200,
            match_id=100,
        )
        
        result = service.update_stats_for_match(update_dto)
        
        assert "stats" in result
        assert "ranking" in result
        assert "elo_change" in result
        assert result["elo_change"] == 16  # Even match win
    
    def test_update_stats_for_match_creates_ranking_if_missing(self, service):
        """Test update_stats_for_match creates ranking if none exists."""
        update_dto = TeamMatchStatsUpdateDTO(
            team_id=1,
            game_slug="valorant",
            is_winner=True,
            is_draw=False,
            opponent_team_id=2,
            opponent_elo=1200,
            match_id=100,
        )
        
        result = service.update_stats_for_match(update_dto)
        
        # Should create ranking with default ELO
        assert result["ranking"].elo_rating == 1216  # 1200 + 16
    
    def test_get_team_stats(self, service):
        """Test get_team_stats delegates to adapter."""
        service.get_team_stats(1, "valorant")
        
        assert ("get_team_stats", 1, "valorant") in service.team_stats_adapter.call_log
    
    def test_get_all_team_stats(self, service):
        """Test get_all_team_stats delegates to adapter."""
        service.get_all_team_stats(1)
        
        assert ("get_all_team_stats", 1) in service.team_stats_adapter.call_log
    
    def test_get_team_ranking(self, service):
        """Test get_team_ranking delegates to adapter."""
        service.get_team_ranking(1, "valorant")
        
        assert ("get_team_ranking", 1, "valorant") in service.team_ranking_adapter.call_log
    
    def test_get_top_teams_by_elo(self, service):
        """Test get_top_teams_by_elo delegates to adapter."""
        service.get_top_teams_by_elo("valorant", limit=50)
        
        assert ("get_rankings_by_game", "valorant", 50) in service.team_ranking_adapter.call_log
    
    def test_record_tournament_completion(self, service):
        """Test record_tournament_completion increments counters."""
        service.record_tournament_completion(1, "valorant", is_winner=True)
        
        assert ("increment_tournament", 1, "valorant", True) in service.team_stats_adapter.call_log
    
    def test_recalculate_all_ranks(self, service):
        """Test recalculate_all_ranks delegates to adapter."""
        service.recalculate_all_ranks("valorant")
        
        assert ("recalculate_ranks", "valorant") in service.team_ranking_adapter.call_log
