"""
Epic 8.5 DTO Tests - Analytics DTOs validation and tier calculations.

Tests for UserAnalyticsDTO, TeamAnalyticsDTO, LeaderboardEntryDTO, SeasonDTO,
AnalyticsQueryDTO, and TierBoundaries helper.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from apps.tournament_ops.dtos.analytics import (
    UserAnalyticsDTO,
    TeamAnalyticsDTO,
    LeaderboardEntryDTO,
    SeasonDTO,
    AnalyticsQueryDTO,
    TierBoundaries,
)


class TestTierBoundaries:
    """Test tier calculation logic."""
    
    def test_bronze_tier_lower_bound(self):
        """ELO 0 should be Bronze."""
        assert TierBoundaries.calculate_tier(0) == "bronze"
    
    def test_bronze_tier_upper_bound(self):
        """ELO 1199 should be Bronze."""
        assert TierBoundaries.calculate_tier(1199) == "bronze"
    
    def test_silver_tier_lower_bound(self):
        """ELO 1200 should be Silver."""
        assert TierBoundaries.calculate_tier(1200) == "silver"
    
    def test_silver_tier_upper_bound(self):
        """ELO 1599 should be Silver."""
        assert TierBoundaries.calculate_tier(1599) == "silver"
    
    def test_gold_tier_bounds(self):
        """Gold tier: 1600-1999."""
        assert TierBoundaries.calculate_tier(1600) == "gold"
        assert TierBoundaries.calculate_tier(1999) == "gold"
    
    def test_diamond_tier_bounds(self):
        """Diamond tier: 2000-2399."""
        assert TierBoundaries.calculate_tier(2000) == "diamond"
        assert TierBoundaries.calculate_tier(2399) == "diamond"
    
    def test_crown_tier_lower_bound(self):
        """ELO 2400+ should be Crown."""
        assert TierBoundaries.calculate_tier(2400) == "crown"
        assert TierBoundaries.calculate_tier(3000) == "crown"


class TestUserAnalyticsDTO:
    """Test UserAnalyticsDTO validation and serialization."""
    
    def test_valid_user_analytics_dto(self):
        """Valid DTO should pass validation."""
        dto = UserAnalyticsDTO(
            user_id=1,
            game_slug="valorant",
            mmr_snapshot=1500,
            elo_snapshot=1500,
            win_rate=Decimal("65.5"),
            kda_ratio=Decimal("1.25"),
            matches_last_7d=10,
            matches_last_30d=50,
            win_rate_7d=Decimal("70.0"),
            win_rate_30d=Decimal("65.0"),
            current_streak=3,
            longest_win_streak=7,
            tier="gold",
            percentile_rank=Decimal("75.5"),
            recalculated_at=datetime.now(),
        )
        dto.validate()  # Should not raise
    
    def test_invalid_win_rate(self):
        """Win rate > 100 should fail validation."""
        dto = UserAnalyticsDTO(
            user_id=1,
            game_slug="valorant",
            elo_snapshot=1500,
            win_rate=Decimal("150.0"),  # Invalid
            tier="gold",
            percentile_rank=Decimal("50.0"),
            recalculated_at=datetime.now(),
        )
        with pytest.raises(ValueError, match="win_rate must be between 0 and 100"):
            dto.validate()
    
    def test_invalid_tier(self):
        """Invalid tier should fail validation."""
        dto = UserAnalyticsDTO(
            user_id=1,
            game_slug="valorant",
            elo_snapshot=1500,
            win_rate=Decimal("50.0"),
            tier="platinum",  # Invalid tier
            percentile_rank=Decimal("50.0"),
            recalculated_at=datetime.now(),
        )
        with pytest.raises(ValueError, match="tier must be one of"):
            dto.validate()


class TestTeamAnalyticsDTO:
    """Test TeamAnalyticsDTO validation."""
    
    def test_valid_team_analytics_dto(self):
        """Valid DTO should pass validation."""
        dto = TeamAnalyticsDTO(
            team_id=1,
            game_slug="csgo",
            elo_snapshot=1800,
            elo_volatility=Decimal("15.5"),
            avg_member_skill=Decimal("1750.0"),
            win_rate=Decimal("55.0"),
            win_rate_7d=Decimal("60.0"),
            win_rate_30d=Decimal("55.0"),
            synergy_score=Decimal("75.0"),
            activity_score=Decimal("80.0"),
            matches_last_7d=8,
            matches_last_30d=35,
            tier="gold",
            percentile_rank=Decimal("65.0"),
            recalculated_at=datetime.now(),
        )
        dto.validate()  # Should not raise
    
    def test_invalid_synergy_score(self):
        """Synergy score > 100 should fail validation."""
        dto = TeamAnalyticsDTO(
            team_id=1,
            game_slug="csgo",
            elo_snapshot=1800,
            win_rate=Decimal("50.0"),
            synergy_score=Decimal("150.0"),  # Invalid
            activity_score=Decimal("50.0"),
            tier="gold",
            percentile_rank=Decimal("50.0"),
            recalculated_at=datetime.now(),
        )
        with pytest.raises(ValueError, match="synergy_score must be between 0 and 100"):
            dto.validate()


class TestLeaderboardEntryDTO:
    """Test LeaderboardEntryDTO validation."""
    
    def test_valid_leaderboard_entry(self):
        """Valid entry should pass validation."""
        dto = LeaderboardEntryDTO(
            leaderboard_type="game_user",
            rank=1,
            reference_id=123,
            game_slug="lol",
            score=2500,
            wins=50,
            losses=10,
            win_rate=Decimal("83.33"),
            payload={"tier": "crown", "percentile": 99.5},
            computed_at=datetime.now(),
        )
        dto.validate()  # Should not raise
    
    def test_invalid_rank(self):
        """Rank <= 0 should fail validation."""
        dto = LeaderboardEntryDTO(
            leaderboard_type="game_user",
            rank=0,  # Invalid
            reference_id=123,
            score=2500,
            win_rate=Decimal("50.0"),
        )
        with pytest.raises(ValueError, match="rank must be positive"):
            dto.validate()


class TestSeasonDTO:
    """Test SeasonDTO validation."""
    
    def test_valid_season(self):
        """Valid season should pass validation."""
        now = datetime.now()
        dto = SeasonDTO(
            season_id="S1-2024",
            name="Season 1 - 2024",
            start_date=now,
            end_date=now + timedelta(days=90),
            is_active=True,
            decay_rules={"enabled": True, "decay_percentage": 5.0},
        )
        dto.validate()  # Should not raise
    
    def test_invalid_date_range(self):
        """Start date >= end date should fail validation."""
        now = datetime.now()
        dto = SeasonDTO(
            season_id="S1-2024",
            name="Season 1",
            start_date=now,
            end_date=now - timedelta(days=1),  # Invalid
            is_active=True,
            decay_rules={},
        )
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            dto.validate()


class TestAnalyticsQueryDTO:
    """Test AnalyticsQueryDTO validation."""
    
    def test_valid_query(self):
        """Valid query should pass validation."""
        dto = AnalyticsQueryDTO(
            game_slug="valorant",
            tier="gold",
            min_elo=1600,
            max_elo=1999,
            limit=50,
            offset=0,
            order_by="-elo_snapshot",
        )
        dto.validate()  # Should not raise
    
    def test_invalid_elo_range(self):
        """Min ELO > Max ELO should fail validation."""
        dto = AnalyticsQueryDTO(
            min_elo=2000,
            max_elo=1500,  # Invalid range
        )
        with pytest.raises(ValueError, match="min_elo cannot be greater than max_elo"):
            dto.validate()
    
    def test_invalid_order_by(self):
        """Invalid order_by field should fail validation."""
        dto = AnalyticsQueryDTO(
            order_by="invalid_field",
        )
        with pytest.raises(ValueError, match="order_by must be one of"):
            dto.validate()
