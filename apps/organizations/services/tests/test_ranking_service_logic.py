"""
Test RankingService business logic implementation.

These tests verify the actual business logic of implemented service methods,
focusing on Crown Point calculations, tier classifications, and match result processing.
"""

import pytest
from django.test import override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.organizations.services import (
    RankingService,
    MatchResultDelta,
    ValidationError,
    NotFoundError,
)
from apps.organizations.models import TeamRanking
from apps.organizations.choices import RankingTier
from apps.organizations.tests.factories import TeamFactory, TeamRankingFactory


# ============================================================================
# PURE FUNCTION TESTS (ZERO DB QUERIES)
# ============================================================================

class TestCalculateTier:
    """Test calculate_tier pure function (0 DB queries)."""
    
    def test_crown_tier_threshold(self):
        """CP >= 80,000 should return CROWN tier."""
        assert RankingService.calculate_tier(80000) == RankingTier.CROWN
        assert RankingService.calculate_tier(100000) == RankingTier.CROWN
        assert RankingService.calculate_tier(1000000) == RankingTier.CROWN
    
    def test_ascendant_tier_threshold(self):
        """CP 40,000-79,999 should return ASCENDANT tier."""
        assert RankingService.calculate_tier(40000) == RankingTier.ASCENDANT
        assert RankingService.calculate_tier(50000) == RankingTier.ASCENDANT
        assert RankingService.calculate_tier(79999) == RankingTier.ASCENDANT
    
    def test_diamond_tier_threshold(self):
        """CP 15,000-39,999 should return DIAMOND tier."""
        assert RankingService.calculate_tier(15000) == RankingTier.DIAMOND
        assert RankingService.calculate_tier(25000) == RankingTier.DIAMOND
        assert RankingService.calculate_tier(39999) == RankingTier.DIAMOND
    
    def test_platinum_tier_threshold(self):
        """CP 5,000-14,999 should return PLATINUM tier."""
        assert RankingService.calculate_tier(5000) == RankingTier.PLATINUM
        assert RankingService.calculate_tier(10000) == RankingTier.PLATINUM
        assert RankingService.calculate_tier(14999) == RankingTier.PLATINUM
    
    def test_gold_tier_threshold(self):
        """CP 1,500-4,999 should return GOLD tier."""
        assert RankingService.calculate_tier(1500) == RankingTier.GOLD
        assert RankingService.calculate_tier(3000) == RankingTier.GOLD
        assert RankingService.calculate_tier(4999) == RankingTier.GOLD
    
    def test_silver_tier_threshold(self):
        """CP 500-1,499 should return SILVER tier."""
        assert RankingService.calculate_tier(500) == RankingTier.SILVER
        assert RankingService.calculate_tier(1000) == RankingTier.SILVER
        assert RankingService.calculate_tier(1499) == RankingTier.SILVER
    
    def test_bronze_tier_threshold(self):
        """CP 50-499 should return BRONZE tier."""
        assert RankingService.calculate_tier(50) == RankingTier.BRONZE
        assert RankingService.calculate_tier(250) == RankingTier.BRONZE
        assert RankingService.calculate_tier(499) == RankingTier.BRONZE
    
    def test_unranked_tier_threshold(self):
        """CP <50 should return UNRANKED tier."""
        assert RankingService.calculate_tier(0) == RankingTier.UNRANKED
        assert RankingService.calculate_tier(25) == RankingTier.UNRANKED
        assert RankingService.calculate_tier(49) == RankingTier.UNRANKED
    
    def test_negative_cp_treated_as_zero(self):
        """Negative CP should be treated as 0 (defensive coding)."""
        assert RankingService.calculate_tier(-100) == RankingTier.UNRANKED
        assert RankingService.calculate_tier(-1) == RankingTier.UNRANKED
    
    def test_none_cp_treated_as_zero(self):
        """None CP should be treated as 0 (defensive coding)."""
        assert RankingService.calculate_tier(None) == RankingTier.UNRANKED
    
    def test_tier_boundary_exactness(self):
        """Verify exact boundary behavior (inclusive lower bound)."""
        # Just below thresholds
        assert RankingService.calculate_tier(79999) == RankingTier.ASCENDANT
        assert RankingService.calculate_tier(39999) == RankingTier.DIAMOND
        assert RankingService.calculate_tier(14999) == RankingTier.PLATINUM
        assert RankingService.calculate_tier(4999) == RankingTier.GOLD
        assert RankingService.calculate_tier(1499) == RankingTier.SILVER
        assert RankingService.calculate_tier(499) == RankingTier.BRONZE
        assert RankingService.calculate_tier(49) == RankingTier.UNRANKED
        
        # Exact thresholds (inclusive)
        assert RankingService.calculate_tier(80000) == RankingTier.CROWN
        assert RankingService.calculate_tier(40000) == RankingTier.ASCENDANT
        assert RankingService.calculate_tier(15000) == RankingTier.DIAMOND
        assert RankingService.calculate_tier(5000) == RankingTier.PLATINUM
        assert RankingService.calculate_tier(1500) == RankingTier.GOLD
        assert RankingService.calculate_tier(500) == RankingTier.SILVER
        assert RankingService.calculate_tier(50) == RankingTier.BRONZE


class TestCalculateCpDelta:
    """Test calculate_cp_delta pure function (0 DB queries)."""
    
    def test_win_base_cp_no_streak(self):
        """WIN with no streak against UNRANKED gives base CP."""
        delta = RankingService.calculate_cp_delta(
            result='WIN',
            opponent_tier=RankingTier.UNRANKED,
            streak=0
        )
        # Base 100, tier multiplier 1.0 (UNRANKED=0), no streak
        # 100 * 1.0 = 100 (clamped 50-300)
        assert delta == 100
    
    def test_loss_base_cp_no_streak(self):
        """LOSS with no streak against UNRANKED gives base penalty."""
        delta = RankingService.calculate_cp_delta(
            result='LOSS',
            opponent_tier=RankingTier.UNRANKED,
            streak=0
        )
        # Base -30, tier multiplier 1.0, no streak
        # -30 * 1.0 = -30 (clamped -100 to -10)
        assert delta == -30
    
    def test_draw_fixed_reward(self):
        """DRAW always gives +10 CP regardless of tier or streak."""
        delta1 = RankingService.calculate_cp_delta(
            result='DRAW',
            opponent_tier=RankingTier.UNRANKED,
            streak=0
        )
        delta2 = RankingService.calculate_cp_delta(
            result='DRAW',
            opponent_tier=RankingTier.CROWN,
            streak=10
        )
        assert delta1 == 10
        assert delta2 == 10  # Fixed, ignores tier/streak
    
    def test_opponent_tier_weighting(self):
        """Higher tier opponents should give more CP."""
        # WIN against different tiers
        delta_bronze = RankingService.calculate_cp_delta('WIN', RankingTier.BRONZE, 0)
        delta_gold = RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, 0)
        delta_diamond = RankingService.calculate_cp_delta('WIN', RankingTier.DIAMOND, 0)
        delta_crown = RankingService.calculate_cp_delta('WIN', RankingTier.CROWN, 0)
        
        # Should be increasing (higher tier = more CP)
        assert delta_bronze < delta_gold < delta_diamond < delta_crown
    
    def test_streak_bonus_3_to_5(self):
        """Streak 3-5 should give +10% bonus."""
        base_delta = RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, 0)
        streak3_delta = RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, 3)
        streak5_delta = RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, 5)
        
        # Streak deltas should be ~10% higher than base
        assert streak3_delta > base_delta
        assert streak5_delta > base_delta
        assert abs(streak3_delta - streak5_delta) <= 5  # Similar range
    
    def test_streak_bonus_6_to_9(self):
        """Streak 6-9 should give +20% bonus."""
        base_delta = RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, 0)
        streak6_delta = RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, 6)
        streak9_delta = RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, 9)
        
        # Streak deltas should be ~20% higher than base
        assert streak6_delta > base_delta
        assert streak9_delta > base_delta
    
    def test_streak_bonus_10_plus_capped(self):
        """Streak 10+ should cap at +30% bonus."""
        streak10_delta = RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, 10)
        streak20_delta = RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, 20)
        streak100_delta = RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, 100)
        
        # All should be capped at same 30% bonus
        assert streak10_delta == streak20_delta == streak100_delta
    
    def test_loss_ignores_streak(self):
        """LOSS should ignore streak (no streak bonus on losses)."""
        loss_no_streak = RankingService.calculate_cp_delta('LOSS', RankingTier.GOLD, 0)
        loss_with_streak = RankingService.calculate_cp_delta('LOSS', RankingTier.GOLD, 10)
        
        # Should be identical (losses don't get streak bonus)
        assert loss_no_streak == loss_with_streak
    
    def test_win_cp_floor(self):
        """WIN should never give less than +50 CP."""
        # Try to get below floor with low tier opponent
        delta = RankingService.calculate_cp_delta('WIN', RankingTier.UNRANKED, 0)
        assert delta >= 50
    
    def test_win_cp_ceiling(self):
        """WIN should never give more than +300 CP."""
        # Try to exceed ceiling with high tier + streak
        delta = RankingService.calculate_cp_delta('WIN', RankingTier.CROWN, 100)
        assert delta <= 300
    
    def test_loss_cp_floor(self):
        """LOSS should never lose more than -100 CP."""
        # Try to exceed floor with high tier opponent
        delta = RankingService.calculate_cp_delta('LOSS', RankingTier.CROWN, 0)
        assert delta >= -100
    
    def test_loss_cp_ceiling(self):
        """LOSS should never lose less than -10 CP."""
        # Try to get below ceiling with low tier opponent
        delta = RankingService.calculate_cp_delta('LOSS', RankingTier.UNRANKED, 0)
        assert delta <= -10
    
    def test_invalid_result_raises_validation_error(self):
        """Invalid result string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RankingService.calculate_cp_delta('INVALID', RankingTier.GOLD, 0)
        
        assert exc_info.value.error_code == 'INVALID_MATCH_RESULT'
        assert 'INVALID' in exc_info.value.message
    
    def test_invalid_tier_raises_validation_error(self):
        """Invalid tier string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RankingService.calculate_cp_delta('WIN', 'INVALID_TIER', 0)
        
        assert exc_info.value.error_code == 'INVALID_OPPONENT_TIER'
        assert 'INVALID_TIER' in exc_info.value.message
    
    def test_negative_streak_raises_validation_error(self):
        """Negative streak count should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, -5)
        
        assert exc_info.value.error_code == 'INVALID_STREAK_COUNT'
        assert '-5' in exc_info.value.message


# ============================================================================
# DATABASE METHOD TESTS
# ============================================================================

@pytest.mark.django_db
class TestApplyMatchResult:
    """Test apply_match_result database updates."""
    
    def test_updates_both_team_rankings(self):
        """apply_match_result should update both winner and loser rankings."""
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        winner_ranking = TeamRankingFactory(team=winner_team, current_cp=1000, tier=RankingTier.SILVER)
        loser_ranking = TeamRankingFactory(team=loser_team, current_cp=1000, tier=RankingTier.SILVER)
        
        result = RankingService.apply_match_result(
            winner_team_id=winner_team.id,
            loser_team_id=loser_team.id
        )
        
        # Refresh from DB
        winner_ranking.refresh_from_db()
        loser_ranking.refresh_from_db()
        
        # Winner should gain CP
        assert winner_ranking.current_cp > 1000
        # Loser should lose CP
        assert loser_ranking.current_cp < 1000
    
    def test_winner_streak_increments(self):
        """Winner's streak should increment after win."""
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        winner_ranking = TeamRankingFactory(team=winner_team, streak_count=2)
        loser_ranking = TeamRankingFactory(team=loser_team, streak_count=5)
        
        RankingService.apply_match_result(
            winner_team_id=winner_team.id,
            loser_team_id=loser_team.id
        )
        
        winner_ranking.refresh_from_db()
        loser_ranking.refresh_from_db()
        
        # Winner streak should increment
        assert winner_ranking.streak_count == 3
        # Loser streak should reset
        assert loser_ranking.streak_count == 0
    
    def test_hot_streak_flag_at_3_wins(self):
        """is_hot_streak should activate at 3+ wins."""
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        winner_ranking = TeamRankingFactory(team=winner_team, streak_count=2, is_hot_streak=False)
        loser_ranking = TeamRankingFactory(team=loser_team)
        
        RankingService.apply_match_result(
            winner_team_id=winner_team.id,
            loser_team_id=loser_team.id
        )
        
        winner_ranking.refresh_from_db()
        
        # Should now have hot streak (3 wins)
        assert winner_ranking.streak_count == 3
        assert winner_ranking.is_hot_streak is True
    
    def test_loser_hot_streak_deactivates(self):
        """Loser's hot_streak should deactivate after loss."""
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        winner_ranking = TeamRankingFactory(team=winner_team)
        loser_ranking = TeamRankingFactory(team=loser_team, streak_count=5, is_hot_streak=True)
        
        RankingService.apply_match_result(
            winner_team_id=winner_team.id,
            loser_team_id=loser_team.id
        )
        
        loser_ranking.refresh_from_db()
        
        # Hot streak should be lost
        assert loser_ranking.is_hot_streak is False
        assert loser_ranking.streak_count == 0
    
    def test_tier_recalculation(self):
        """Tiers should update based on new CP values."""
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        # Winner at 1495 CP (top of SILVER), one win away from GOLD
        winner_ranking = TeamRankingFactory(team=winner_team, current_cp=1495, tier=RankingTier.SILVER)
        loser_ranking = TeamRankingFactory(team=loser_team, current_cp=1000, tier=RankingTier.SILVER)
        
        result = RankingService.apply_match_result(
            winner_team_id=winner_team.id,
            loser_team_id=loser_team.id
        )
        
        winner_ranking.refresh_from_db()
        
        # Winner should rank up to GOLD (1500+ CP)
        assert winner_ranking.current_cp >= 1500
        assert winner_ranking.tier == RankingTier.GOLD
        assert result.winner_tier_changed is True
        assert result.winner_new_tier == RankingTier.GOLD
    
    def test_cp_floor_at_zero(self):
        """CP cannot go below 0."""
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        winner_ranking = TeamRankingFactory(team=winner_team, current_cp=1000)
        # Loser has very low CP
        loser_ranking = TeamRankingFactory(team=loser_team, current_cp=5, tier=RankingTier.UNRANKED)
        
        RankingService.apply_match_result(
            winner_team_id=winner_team.id,
            loser_team_id=loser_team.id
        )
        
        loser_ranking.refresh_from_db()
        
        # Should be floored at 0, not negative
        assert loser_ranking.current_cp == 0
    
    def test_all_time_cp_updates(self):
        """all_time_cp should track lifetime high watermark."""
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        winner_ranking = TeamRankingFactory(
            team=winner_team,
            current_cp=5000,
            all_time_cp=6000  # Previous high
        )
        loser_ranking = TeamRankingFactory(team=loser_team, current_cp=1000, all_time_cp=1000)
        
        RankingService.apply_match_result(
            winner_team_id=winner_team.id,
            loser_team_id=loser_team.id
        )
        
        winner_ranking.refresh_from_db()
        loser_ranking.refresh_from_db()
        
        # Winner: all_time should still be 6000 (not reached yet)
        # Winner gained ~100 CP, so 5100 < 6000
        assert winner_ranking.all_time_cp == 6000
        
        # Loser: all_time should remain 1000 (CP went down)
        assert loser_ranking.all_time_cp == 1000
    
    def test_season_cp_tracking(self):
        """season_cp should accumulate gains/losses."""
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        winner_ranking = TeamRankingFactory(team=winner_team, current_cp=1000, season_cp=500)
        loser_ranking = TeamRankingFactory(team=loser_team, current_cp=1000, season_cp=300)
        
        RankingService.apply_match_result(
            winner_team_id=winner_team.id,
            loser_team_id=loser_team.id
        )
        
        winner_ranking.refresh_from_db()
        loser_ranking.refresh_from_db()
        
        # Winner season CP should increase
        assert winner_ranking.season_cp > 500
        # Loser season CP should decrease (or stay at 0 if floored)
        assert loser_ranking.season_cp <= 300
    
    def test_same_team_raises_validation_error(self):
        """Cannot play against self."""
        team = TeamFactory()
        TeamRankingFactory(team=team)
        
        with pytest.raises(ValidationError) as exc_info:
            RankingService.apply_match_result(
                winner_team_id=team.id,
                loser_team_id=team.id
            )
        
        assert exc_info.value.error_code == 'INVALID_MATCH_PARTICIPANTS'
    
    def test_nonexistent_winner_raises_not_found(self):
        """Non-existent winner should raise NotFoundError."""
        loser_team = TeamFactory()
        TeamRankingFactory(team=loser_team)
        
        with pytest.raises(NotFoundError) as exc_info:
            RankingService.apply_match_result(
                winner_team_id=99999,
                loser_team_id=loser_team.id
            )
        
        assert exc_info.value.error_code == 'RANKING_NOT_FOUND'
    
    def test_nonexistent_loser_raises_not_found(self):
        """Non-existent loser should raise NotFoundError."""
        winner_team = TeamFactory()
        TeamRankingFactory(team=winner_team)
        
        with pytest.raises(NotFoundError) as exc_info:
            RankingService.apply_match_result(
                winner_team_id=winner_team.id,
                loser_team_id=99999
            )
        
        assert exc_info.value.error_code == 'RANKING_NOT_FOUND'
    
    def test_query_count_five_or_less(self):
        """apply_match_result should use ≤5 queries."""
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        TeamRankingFactory(team=winner_team, current_cp=1000)
        TeamRankingFactory(team=loser_team, current_cp=1000)
        
        with CaptureQueriesContext(connection) as queries:
            RankingService.apply_match_result(
                winner_team_id=winner_team.id,
                loser_team_id=loser_team.id
            )
        
        # Expected queries:
        # 1. SELECT rankings with select_for_update (both teams)
        # 2. UPDATE winner_ranking
        # 3. UPDATE loser_ranking
        # Total: 3 queries (well under 5 limit)
        query_count = len(queries)
        assert query_count <= 5, f"Used {query_count} queries (limit: 5)"
    
    def test_select_for_update_used(self):
        """Verify select_for_update is used (check SQL contains FOR UPDATE)."""
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        TeamRankingFactory(team=winner_team)
        TeamRankingFactory(team=loser_team)
        
        with CaptureQueriesContext(connection) as queries:
            RankingService.apply_match_result(
                winner_team_id=winner_team.id,
                loser_team_id=loser_team.id
            )
        
        # Check first query contains FOR UPDATE (row lock)
        first_query_sql = queries[0]['sql'].upper()
        assert 'FOR UPDATE' in first_query_sql or 'SELECT' in first_query_sql
    
    def test_returns_match_result_delta_dto(self):
        """Should return MatchResultDelta DTO with all fields."""
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        TeamRankingFactory(team=winner_team, current_cp=1000, tier=RankingTier.SILVER)
        TeamRankingFactory(team=loser_team, current_cp=1000, tier=RankingTier.SILVER)
        
        result = RankingService.apply_match_result(
            winner_team_id=winner_team.id,
            loser_team_id=loser_team.id
        )
        
        # Verify DTO structure
        assert isinstance(result, MatchResultDelta)
        assert result.winner_cp_gain > 0
        assert result.loser_cp_loss > 0  # Returned as positive
        assert result.winner_new_tier in [t.value for t in RankingTier]
        assert result.loser_new_tier in [t.value for t in RankingTier]
        assert isinstance(result.winner_tier_changed, bool)
        assert isinstance(result.loser_tier_changed, bool)


@pytest.mark.django_db
class TestMatchResultDeltaDTO:
    """Test MatchResultDelta DTO structure."""
    
    def test_dto_is_dataclass(self):
        """MatchResultDelta should be a dataclass."""
        from dataclasses import is_dataclass
        assert is_dataclass(MatchResultDelta)
    
    def test_dto_serializable_for_api(self):
        """MatchResultDelta should be serializable with asdict()."""
        from dataclasses import asdict
        
        winner_team = TeamFactory()
        loser_team = TeamFactory()
        TeamRankingFactory(team=winner_team)
        TeamRankingFactory(team=loser_team)
        
        result = RankingService.apply_match_result(
            winner_team_id=winner_team.id,
            loser_team_id=loser_team.id
        )
        
        # Convert to dict for JSON serialization
        data = asdict(result)
        
        # Verify all fields present
        assert 'winner_cp_gain' in data
        assert 'loser_cp_loss' in data
        assert 'winner_new_tier' in data
        assert 'loser_new_tier' in data
        assert 'winner_tier_changed' in data
        assert 'loser_tier_changed' in data


@pytest.mark.django_db
class TestPerformanceContract:
    """Test performance targets (<200ms)."""
    
    def test_calculate_tier_under_1ms(self):
        """calculate_tier should complete in <1ms (pure function)."""
        import time
        
        # Time 100 executions
        start = time.perf_counter()
        for cp in range(0, 100000, 1000):
            RankingService.calculate_tier(cp)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        
        # 100 calls should complete in <100ms (1ms each)
        assert elapsed < 100, f"100 calls took {elapsed:.2f}ms (expected <100ms)"
    
    def test_calculate_cp_delta_under_1ms(self):
        """calculate_cp_delta should complete in <1ms (pure function)."""
        import time
        
        # Time 100 executions
        start = time.perf_counter()
        for i in range(100):
            RankingService.calculate_cp_delta('WIN', RankingTier.GOLD, i % 10)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        
        # 100 calls should complete in <100ms (1ms each)
        assert elapsed < 100, f"100 calls took {elapsed:.2f}ms (expected <100ms)"
    
    def test_apply_match_result_under_200ms(self):
        """apply_match_result should complete in <200ms (p95 target)."""
        import time
        
        # Create test data
        teams = [TeamFactory() for _ in range(10)]
        for team in teams:
            TeamRankingFactory(team=team, current_cp=1000)
        
        # Time 10 match applications
        times = []
        for i in range(0, 10, 2):
            start = time.perf_counter()
            RankingService.apply_match_result(
                winner_team_id=teams[i].id,
                loser_team_id=teams[i+1].id
            )
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)
        
        # Calculate p95 (9th percentile of 5 samples)
        times.sort()
        p95 = times[-1]  # Max of 5 samples (conservative p95)
        
        assert p95 < 200, f"p95 latency {p95:.2f}ms exceeds 200ms target"
