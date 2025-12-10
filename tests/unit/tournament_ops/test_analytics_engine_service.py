"""
Epic 8.5 Service Tests - AnalyticsEngineService business logic.

Tests for analytics calculations, leaderboard generation, decay algorithms.
Uses mocks (NO ORM in service tests).
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from apps.tournament_ops.services.analytics_engine_service import AnalyticsEngineService
from apps.tournament_ops.dtos.analytics import (
    UserAnalyticsDTO,
    TeamAnalyticsDTO,
    LeaderboardEntryDTO,
    SeasonDTO,
)


class TestAnalyticsEngineService:
    """Test AnalyticsEngineService calculations."""
    
    @pytest.fixture
    def service(self):
        """Create service instance with mocked adapter."""
        with patch("apps.tournament_ops.services.analytics_engine_service.AnalyticsAdapter") as mock_adapter:
            yield AnalyticsEngineService(), mock_adapter.return_value
    
    def test_calculate_win_rate_normal(self, service):
        """Test win rate calculation with normal data."""
        svc, _ = service
        win_rate = svc._calculate_win_rate(wins=7, losses=3, draws=0)
        assert win_rate == Decimal("70.0")
    
    def test_calculate_win_rate_no_matches(self, service):
        """Test win rate with 0 matches."""
        svc, _ = service
        win_rate = svc._calculate_win_rate(wins=0, losses=0, draws=0)
        assert win_rate == Decimal("0.0")
    
    def test_calculate_win_rate_perfect(self, service):
        """Test win rate with 100% wins."""
        svc, _ = service
        win_rate = svc._calculate_win_rate(wins=10, losses=0, draws=0)
        assert win_rate == Decimal("100.0")
    
    def test_calculate_win_rate_with_draws(self, service):
        """Test win rate including draws."""
        svc, _ = service
        # 5 wins, 3 losses, 2 draws = 5/10 = 50%
        win_rate = svc._calculate_win_rate(wins=5, losses=3, draws=2)
        assert win_rate == Decimal("50.0")
    
    def test_calculate_current_streak_win(self, service):
        """Test current streak with wins."""
        svc, _ = service
        # Recent matches: W, W, W (most recent first)
        streak = svc._calculate_current_streak(recent_results=["W", "W", "W"])
        assert streak == 3
    
    def test_calculate_current_streak_loss(self, service):
        """Test current streak with losses."""
        svc, _ = service
        # Recent matches: L, L (most recent first)
        streak = svc._calculate_current_streak(recent_results=["L", "L"])
        assert streak == -2
    
    def test_calculate_current_streak_mixed(self, service):
        """Test current streak interrupted by loss."""
        svc, _ = service
        # Recent: W, W, L, W, W (most recent first)
        streak = svc._calculate_current_streak(recent_results=["W", "W", "L", "W", "W"])
        assert streak == 2  # Only most recent wins count
    
    def test_calculate_longest_win_streak(self, service):
        """Test longest win streak calculation."""
        svc, _ = service
        # W, W, W, L, W, W, W, W, L, W
        results = ["W", "W", "W", "L", "W", "W", "W", "W", "L", "W"]
        longest = svc._calculate_longest_win_streak(match_history=results)
        assert longest == 4  # Middle streak is longest
    
    def test_calculate_longest_win_streak_none(self, service):
        """Test longest win streak with no wins."""
        svc, _ = service
        longest = svc._calculate_longest_win_streak(match_history=["L", "L", "L"])
        assert longest == 0
    
    def test_estimate_user_elo_high_win_rate(self, service):
        """Test ELO estimation with high win rate."""
        svc, _ = service
        elo = svc._estimate_user_elo(
            win_rate=Decimal("80.0"),
            matches_played=50,
            avg_opponent_elo=1500,
        )
        # Should be above 1500 for 80% win rate
        assert elo > 1500
    
    def test_estimate_user_elo_low_win_rate(self, service):
        """Test ELO estimation with low win rate."""
        svc, _ = service
        elo = svc._estimate_user_elo(
            win_rate=Decimal("30.0"),
            matches_played=50,
            avg_opponent_elo=1500,
        )
        # Should be below 1500 for 30% win rate
        assert elo < 1500
    
    def test_calculate_user_percentile(self, service):
        """Test user percentile ranking."""
        svc, adapter = service
        
        # Mock adapter to return 100 total users
        adapter.count_user_snapshots.return_value = 100
        # Mock 25 users below this ELO
        adapter.count_user_snapshots.return_value = 25
        
        percentile = svc._calculate_user_percentile(
            user_elo=1600,
            game_slug="valorant",
        )
        # 25 below means 75th percentile
        assert percentile == Decimal("75.0")
    
    def test_calculate_elo_volatility_stable(self, service):
        """Test ELO volatility with stable ratings."""
        svc, _ = service
        # Small changes
        recent_elos = [1500, 1505, 1498, 1502, 1501]
        volatility = svc._calculate_elo_volatility(recent_elos)
        # Should have low volatility
        assert volatility < Decimal("10.0")
    
    def test_calculate_elo_volatility_volatile(self, service):
        """Test ELO volatility with big swings."""
        svc, _ = service
        # Large changes
        recent_elos = [1500, 1600, 1400, 1650, 1350]
        volatility = svc._calculate_elo_volatility(recent_elos)
        # Should have high volatility
        assert volatility > Decimal("50.0")
    
    def test_calculate_synergy_score_high(self, service):
        """Test synergy score with consistent performance."""
        svc, _ = service
        # Consistent individual performances
        individual_scores = [80, 85, 82, 83, 84]
        synergy = svc._calculate_synergy_score(
            team_win_rate=Decimal("70.0"),
            individual_scores=individual_scores,
        )
        # High consistency + good win rate = high synergy
        assert synergy > Decimal("70.0")
    
    def test_calculate_synergy_score_low(self, service):
        """Test synergy score with inconsistent performance."""
        svc, _ = service
        # Wildly inconsistent performances
        individual_scores = [90, 30, 85, 20, 95]
        synergy = svc._calculate_synergy_score(
            team_win_rate=Decimal("50.0"),
            individual_scores=individual_scores,
        )
        # Low consistency = low synergy
        assert synergy < Decimal("60.0")
    
    def test_calculate_activity_score_high(self, service):
        """Test activity score with frequent play."""
        svc, _ = service
        activity = svc._calculate_activity_score(
            matches_last_7d=15,
            matches_last_30d=60,
        )
        # 15 matches/week = high activity
        assert activity > Decimal("80.0")
    
    def test_calculate_activity_score_low(self, service):
        """Test activity score with infrequent play."""
        svc, _ = service
        activity = svc._calculate_activity_score(
            matches_last_7d=1,
            matches_last_30d=4,
        )
        # 1 match/week = low activity
        assert activity < Decimal("40.0")
    
    def test_apply_decay_no_decay_rules(self, service):
        """Test decay with no decay rules."""
        svc, _ = service
        original_elo = 1800
        decayed = svc._apply_decay(
            current_elo=original_elo,
            last_match_date=datetime.now() - timedelta(days=60),
            decay_rules={},
        )
        # No decay applied
        assert decayed == original_elo
    
    def test_apply_decay_within_grace_period(self, service):
        """Test decay within grace period."""
        svc, _ = service
        original_elo = 1800
        decayed = svc._apply_decay(
            current_elo=original_elo,
            last_match_date=datetime.now() - timedelta(days=10),  # Within 30-day grace
            decay_rules={"enabled": True, "grace_period_days": 30, "decay_percentage": 5.0},
        )
        # No decay yet
        assert decayed == original_elo
    
    def test_apply_decay_after_grace_period(self, service):
        """Test decay after grace period."""
        svc, _ = service
        original_elo = 1800
        decayed = svc._apply_decay(
            current_elo=original_elo,
            last_match_date=datetime.now() - timedelta(days=60),  # Past grace period
            decay_rules={"enabled": True, "grace_period_days": 30, "decay_percentage": 5.0},
        )
        # 5% decay applied
        assert decayed == 1710  # 1800 * 0.95
    
    def test_compute_user_analytics_integration(self, service):
        """Test compute_user_analytics end-to-end."""
        svc, adapter = service
        
        # Mock adapter responses
        adapter.get_user_match_history.return_value = [
            {"result": "W", "opponent_elo": 1500},
            {"result": "W", "opponent_elo": 1550},
            {"result": "L", "opponent_elo": 1600},
        ]
        adapter.count_user_snapshots.return_value = 100  # For percentile
        
        dto = svc.compute_user_analytics(user_id=1, game_slug="valorant")
        
        assert dto.user_id == 1
        assert dto.game_slug == "valorant"
        assert dto.win_rate == Decimal("66.67")  # 2/3 wins
        assert dto.current_streak == 2  # Last 2 are wins
        assert dto.tier in ["bronze", "silver", "gold", "diamond", "crown"]
    
    def test_generate_leaderboard_game_user(self, service):
        """Test generate_leaderboard for game_user type."""
        svc, adapter = service
        
        # Mock snapshots
        adapter.list_user_snapshots.return_value = [
            UserAnalyticsDTO(
                user_id=1, game_slug="valorant", elo_snapshot=2000,
                win_rate=Decimal("70.0"), tier="diamond", percentile_rank=Decimal("90.0"),
                recalculated_at=datetime.now(),
            ),
            UserAnalyticsDTO(
                user_id=2, game_slug="valorant", elo_snapshot=1800,
                win_rate=Decimal("65.0"), tier="gold", percentile_rank=Decimal("75.0"),
                recalculated_at=datetime.now(),
            ),
        ]
        
        entries = svc.generate_leaderboard(
            leaderboard_type="game_user",
            game_slug="valorant",
        )
        
        assert len(entries) == 2
        assert entries[0].rank == 1
        assert entries[0].reference_id == 1
        assert entries[0].score == 2000
        assert entries[1].rank == 2
        assert entries[1].reference_id == 2
    
    def test_generate_leaderboard_tier(self, service):
        """Test generate_leaderboard for tier type."""
        svc, adapter = service
        
        # Mock snapshots with different tiers
        adapter.list_user_snapshots.return_value = [
            UserAnalyticsDTO(
                user_id=1, game_slug="valorant", elo_snapshot=2400,
                tier="crown", percentile_rank=Decimal("99.0"),
                recalculated_at=datetime.now(),
            ),
            UserAnalyticsDTO(
                user_id=2, game_slug="valorant", elo_snapshot=2100,
                tier="diamond", percentile_rank=Decimal("85.0"),
                recalculated_at=datetime.now(),
            ),
            UserAnalyticsDTO(
                user_id=3, game_slug="valorant", elo_snapshot=1700,
                tier="gold", percentile_rank=Decimal("60.0"),
                recalculated_at=datetime.now(),
            ),
        ]
        
        entries = svc.generate_leaderboard(leaderboard_type="tier")
        
        # Should be ordered by tier (crown > diamond > gold)
        assert len(entries) == 3
        assert entries[0].payload["tier"] == "crown"
        assert entries[1].payload["tier"] == "diamond"
        assert entries[2].payload["tier"] == "gold"
