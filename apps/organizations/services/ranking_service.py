"""
RankingService - Service layer for Crown Point calculations and tier updates.

Crown Points (CP) are the platform's unified ranking currency. Teams and
Organizations earn CP through match victories, tournament placements, and
community achievements.

Performance Targets (p95 latency):
- Tier calculation (pure math): <5ms, 0 queries
- Match result application: <100ms, ≤5 queries
- Full ranking recomputation: <200ms, ≤10 queries (async via Celery for bulk)

Async Boundaries:
- Bulk ranking recomputation (Phase 4+) will use Celery tasks
- Real-time match results processed synchronously (<100ms)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .exceptions import (
    NotFoundError,
    ValidationError,
    RankingServiceError,
)


# ============================================================================
# DATA TRANSFER OBJECTS (DTOs)
# ============================================================================

@dataclass
class RankingSnapshot:
    """
    Current ranking state for display.
    
    Used by: leaderboards, user_profile (rank badges), team dashboards.
    """
    entity_id: int  # Team or Organization ID
    entity_type: str  # 'TEAM' or 'ORGANIZATION'
    crown_points: int
    tier: str  # UNRANKED, BRONZE, SILVER, GOLD, PLATINUM, DIAMOND, MASTER, GRANDMASTER
    rank_position: int  # Global rank (1-based)
    percentile: float  # 0.0-100.0
    matches_played: int
    win_rate: float  # 0.0-100.0
    last_match_date: Optional[str]  # ISO 8601 format


@dataclass
class MatchResultDelta:
    """
    CP changes from a single match result.
    
    Used by: economy (post-match rewards), notifications (rank up alerts).
    """
    winner_cp_gain: int
    loser_cp_loss: int
    winner_new_tier: str
    loser_new_tier: str
    winner_tier_changed: bool
    loser_tier_changed: bool


# ============================================================================
# RANKINGSERVICE - PUBLIC API
# ============================================================================

class RankingService:
    """
    Unified service layer for Crown Point calculations and tier management.
    
    Crown Points Mechanics:
    - Win: +100 CP (base), scaled by opponent tier difference
    - Loss: -25 CP (base), scaled by opponent tier difference
    - Tier brackets: BRONZE (0-999), SILVER (1000-2499), GOLD (2500-4999), etc.
    
    Thread Safety: All methods are thread-safe (no shared mutable state).
    """
    
    # ========================================================================
    # TIER CALCULATIONS (PURE FUNCTIONS)
    # ========================================================================
    
    @staticmethod
    def calculate_tier(crown_points: int) -> str:
        """
        Convert Crown Points to tier bracket.
        
        Tier Brackets (DCRS v1.0 specification):
        - CROWN: 80,000+ CP (Top 1% globally, elite professional teams)
        - ASCENDANT: 40,000+ CP (Top 5%, semi-professional teams)
        - DIAMOND: 15,000+ CP (Top 15%, highly competitive)
        - PLATINUM: 5,000+ CP (Top 30%, competitive)
        - GOLD: 1,500+ CP (Top 50%, established teams)
        - SILVER: 500+ CP (Active teams with match history)
        - BRONZE: 50+ CP (New teams, initial placement)
        - UNRANKED: <50 CP (Inactive or brand-new teams)
        
        Args:
            crown_points: Current CP total (integer, can be negative for defensive coding)
        
        Returns:
            Tier string matching RankingTier.choices (uppercase)
        
        Performance Notes:
            - Target: <1ms (pure math, no DB queries, O(1) complexity)
            - Zero allocations (returns constant strings)
        
        Business Rules:
            - Negative CP treated as 0 (defensive coding for data integrity issues)
            - None treated as 0 (handles uninitialized rankings gracefully)
            - Tier boundaries are inclusive on lower bound (e.g., 50 CP = BRONZE)
        
        Example:
            tier = RankingService.calculate_tier(cp=15000)
            # Returns "DIAMOND"
            
            tier = RankingService.calculate_tier(cp=-100)
            # Returns "UNRANKED" (defensive: treats negative as 0)
        """
        from ..choices import RankingTier
        
        # Defensive: Handle None or negative CP
        if crown_points is None or crown_points < 0:
            crown_points = 0
        
        # Tier calculation (descending order for efficiency)
        if crown_points >= 80000:
            return RankingTier.CROWN
        elif crown_points >= 40000:
            return RankingTier.ASCENDANT
        elif crown_points >= 15000:
            return RankingTier.DIAMOND
        elif crown_points >= 5000:
            return RankingTier.PLATINUM
        elif crown_points >= 1500:
            return RankingTier.GOLD
        elif crown_points >= 500:
            return RankingTier.SILVER
        elif crown_points >= 50:
            return RankingTier.BRONZE
        else:
            return RankingTier.UNRANKED
    
    @staticmethod
    def calculate_cp_delta(
        result: str,
        opponent_tier: str,
        streak: int
    ) -> int:
        """
        Calculate CP gain/loss from match result (PURE FUNCTION).
        
        Formula Design (DCRS v1.0):
        
        1. BASE CP by result:
           - WIN: +100 CP
           - LOSS: -30 CP
           - DRAW: +10 CP (small participation reward)
        
        2. OPPONENT TIER WEIGHTING (scales base CP):
           Beating stronger opponents gives more CP, losing to weaker opponents hurts more.
           
           Tier values (for weighting calculation):
           - UNRANKED: 0
           - BRONZE: 1
           - SILVER: 2
           - GOLD: 3
           - PLATINUM: 4
           - DIAMOND: 5
           - ASCENDANT: 6
           - CROWN: 7
           
           Multiplier = 1.0 + (opponent_tier_value - your_tier_value) * 0.15
           - If opponent 1 tier higher: 1.15x CP
           - If opponent 2 tiers higher: 1.30x CP
           - If opponent 1 tier lower: 0.85x CP
           
           Note: We only have opponent_tier, not player's tier. For simplicity,
           opponent_tier_value is used directly as a percentage bonus/penalty.
           Higher tier opponents give more CP (WIN) or less CP loss (LOSS).
        
        3. HOT STREAK BONUS (only applies to wins):
           - Streak 3-5: +10% CP
           - Streak 6-9: +20% CP
           - Streak 10+: +30% CP (capped to prevent farming)
        
        4. CP FLOOR/CEILING:
           - Minimum WIN gain: +50 CP (prevents exploitation)
           - Maximum WIN gain: +300 CP (prevents inflation)
           - Minimum LOSS penalty: -10 CP (prevents frustration)
           - Maximum LOSS penalty: -100 CP (prevents rage-quit incentive)
        
        Args:
            result: Match result ('WIN', 'LOSS', 'DRAW')
            opponent_tier: Opponent's tier string (e.g., 'GOLD', 'DIAMOND')
            streak: Current win streak count (0+ integer)
        
        Returns:
            CP delta as signed integer (positive for gains, negative for losses)
        
        Raises:
            ValidationError: If result or opponent_tier invalid, or streak < 0
        
        Performance Notes:
            - Target: <1ms (pure math, zero DB queries)
            - O(1) complexity
        
        Business Rules:
            - DRAW results ignore streak bonus (small fixed reward)
            - Streak bonus capped at 30% to prevent win-trading farms
            - Opponent tier weighting simulates ELO-like matchmaking fairness
        
        Example:
            # GOLD team beats DIAMOND opponent (underdog win) with 5-game streak
            delta = RankingService.calculate_cp_delta(
                result='WIN',
                opponent_tier='DIAMOND',
                streak=5
            )
            # Base: 100, Tier bonus: +30% (DIAMOND=5 * 6% = 30%), Streak: +10%
            # Formula: 100 * 1.30 * 1.10 = 143 CP
        """
        from ..choices import RankingTier
        
        # Input validation
        valid_results = {'WIN', 'LOSS', 'DRAW'}
        if result not in valid_results:
            raise ValidationError(
                message=f"Invalid match result: {result}",
                error_code="INVALID_MATCH_RESULT",
                details={"result": result, "valid_results": list(valid_results)}
            )
        
        valid_tiers = {
            RankingTier.UNRANKED, RankingTier.BRONZE, RankingTier.SILVER,
            RankingTier.GOLD, RankingTier.PLATINUM, RankingTier.DIAMOND,
            RankingTier.ASCENDANT, RankingTier.CROWN
        }
        if opponent_tier not in valid_tiers:
            raise ValidationError(
                message=f"Invalid opponent tier: {opponent_tier}",
                error_code="INVALID_OPPONENT_TIER",
                details={"opponent_tier": opponent_tier, "valid_tiers": [str(t) for t in valid_tiers]}
            )
        
        if streak < 0:
            raise ValidationError(
                message=f"Streak count cannot be negative: {streak}",
                error_code="INVALID_STREAK_COUNT",
                details={"streak": streak}
            )
        
        # Step 1: Base CP by result
        if result == 'WIN':
            base_cp = 100
        elif result == 'LOSS':
            base_cp = -30
        else:  # DRAW
            base_cp = 10
        
        # Step 2: Opponent tier weighting
        tier_values = {
            RankingTier.UNRANKED: 0,
            RankingTier.BRONZE: 1,
            RankingTier.SILVER: 2,
            RankingTier.GOLD: 3,
            RankingTier.PLATINUM: 4,
            RankingTier.DIAMOND: 5,
            RankingTier.ASCENDANT: 6,
            RankingTier.CROWN: 7
        }
        opponent_value = tier_values[opponent_tier]
        
        # Tier multiplier: Higher tier opponents = more CP (simplified model)
        # Each tier level adds 6% bonus/penalty
        tier_multiplier = 1.0 + (opponent_value * 0.06)
        
        # Apply tier weighting
        cp_delta = base_cp * tier_multiplier
        
        # Step 3: Hot streak bonus (only for wins)
        if result == 'WIN' and streak >= 3:
            if streak >= 10:
                streak_multiplier = 1.30  # +30% (capped)
            elif streak >= 6:
                streak_multiplier = 1.20  # +20%
            else:  # 3-5 streak
                streak_multiplier = 1.10  # +10%
            
            cp_delta *= streak_multiplier
        
        # Step 4: Apply floor/ceiling constraints
        if result == 'WIN':
            # Clamp win gains between 50 and 300 CP
            cp_delta = max(50, min(300, int(cp_delta)))
        elif result == 'LOSS':
            # Clamp loss penalties between -100 and -10 CP
            cp_delta = max(-100, min(-10, int(cp_delta)))
        else:  # DRAW
            # Fixed small reward (10 CP, no clamping needed)
            cp_delta = 10
        
        return int(cp_delta)
    
    # ========================================================================
    # MATCH RESULT APPLICATION
    # ========================================================================
    
    @staticmethod
    def apply_match_result(
        winner_team_id: int,
        loser_team_id: int,
        *,
        match_id: Optional[int] = None,
        is_tournament_match: bool = False
    ) -> MatchResultDelta:
        """
        Process match result and update team rankings.
        
        Updates:
        1. Winner team CP (increase)
        2. Loser team CP (decrease)
        3. Both teams' tiers (if thresholds crossed)
        4. Both teams' match history counters
        5. Organization aggregate rankings (if applicable)
        
        Args:
            winner_team_id: Winning team primary key
            loser_team_id: Losing team primary key
            match_id: Match record ID for audit trail (optional)
            is_tournament_match: Tournament matches may have bonus multipliers
        
        Returns:
            MatchResultDelta DTO with CP changes and tier updates
        
        Raises:
            NotFoundError: If either team_id does not exist
            ValidationError: If winner_team_id == loser_team_id
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Uses select_for_update() for atomic CP updates
            - Tournament matches trigger additional org ranking update
        
        Async Boundaries:
            - Notification dispatch (rank up alerts) via Celery (Phase 4+)
            - Leaderboard cache invalidation async (Phase 5+)
        
        Example:
            delta = RankingService.apply_match_result(
                winner_team_id=42,
                loser_team_id=99,
                match_id=12345,
                is_tournament_match=True
            )
            if delta.winner_tier_changed:
                send_notification(f"Congrats! Ranked up to {delta.winner_new_tier}")
        """
        from django.db import transaction
        from apps.organizations.models import Team, TeamRanking
        
        # Input validation: Cannot play against self
        if winner_team_id == loser_team_id:
            raise ValidationError(
                message="Winner and loser cannot be the same team",
                error_code="INVALID_MATCH_PARTICIPANTS",
                details={"winner_team_id": winner_team_id, "loser_team_id": loser_team_id}
            )
        
        # Atomic transaction: Lock both rankings to prevent race conditions
        with transaction.atomic():
            # Query 1-2: Load both team rankings with row locks (select_for_update)
            # Order by ID to prevent deadlocks (consistent lock ordering)
            team_ids = sorted([winner_team_id, loser_team_id])
            
            try:
                rankings = {
                    r.team_id: r
                    for r in TeamRanking.objects.select_for_update().filter(
                        team_id__in=team_ids
                    ).select_related('team')
                }
            except Exception as e:
                raise NotFoundError(
                    message="Failed to load team rankings",
                    error_code="RANKING_NOT_FOUND",
                    details={"team_ids": team_ids, "error": str(e)}
                )
            
            # Verify both rankings exist
            if winner_team_id not in rankings:
                raise NotFoundError(
                    message=f"Winner team ranking not found: {winner_team_id}",
                    error_code="RANKING_NOT_FOUND",
                    details={"team_id": winner_team_id}
                )
            
            if loser_team_id not in rankings:
                raise NotFoundError(
                    message=f"Loser team ranking not found: {loser_team_id}",
                    error_code="RANKING_NOT_FOUND",
                    details={"team_id": loser_team_id}
                )
            
            winner_ranking = rankings[winner_team_id]
            loser_ranking = rankings[loser_team_id]
            
            # Capture old state for DTO
            winner_old_tier = winner_ranking.tier
            loser_old_tier = loser_ranking.tier
            
            # Calculate CP deltas for winner (WIN against opponent)
            winner_delta = RankingService.calculate_cp_delta(
                result='WIN',
                opponent_tier=loser_ranking.tier,
                streak=winner_ranking.streak_count
            )
            
            # Calculate CP deltas for loser (LOSS against opponent)
            loser_delta = RankingService.calculate_cp_delta(
                result='LOSS',
                opponent_tier=winner_ranking.tier,
                streak=loser_ranking.streak_count  # Loser's streak (will be reset)
            )
            
            # Apply CP changes with floor at 0
            winner_ranking.current_cp = max(0, winner_ranking.current_cp + winner_delta)
            loser_ranking.current_cp = max(0, loser_ranking.current_cp + loser_delta)
            
            # Update all-time high watermarks
            winner_ranking.all_time_cp = max(
                winner_ranking.all_time_cp,
                winner_ranking.current_cp
            )
            loser_ranking.all_time_cp = max(
                loser_ranking.all_time_cp,
                loser_ranking.current_cp
            )
            
            # Update season CP (simple addition for now)
            winner_ranking.season_cp += winner_delta
            loser_ranking.season_cp = max(0, loser_ranking.season_cp + loser_delta)
            
            # Update streaks: Winner increments, loser resets
            winner_ranking.streak_count += 1
            loser_ranking.streak_count = 0
            
            # Update hot streak flags (3+ wins)
            winner_ranking.is_hot_streak = winner_ranking.streak_count >= 3
            loser_ranking.is_hot_streak = False  # Lost, so no streak
            
            # Recalculate tiers based on new CP
            winner_ranking.tier = RankingService.calculate_tier(winner_ranking.current_cp)
            loser_ranking.tier = RankingService.calculate_tier(loser_ranking.current_cp)
            
            # Determine if tier changed
            winner_tier_changed = (winner_ranking.tier != winner_old_tier)
            loser_tier_changed = (loser_ranking.tier != loser_old_tier)
            
            # Query 3-4: Save both rankings
            winner_ranking.save(update_fields=[
                'current_cp', 'season_cp', 'all_time_cp', 'tier',
                'streak_count', 'is_hot_streak', 'last_activity_date'
            ])
            loser_ranking.save(update_fields=[
                'current_cp', 'season_cp', 'all_time_cp', 'tier',
                'streak_count', 'is_hot_streak', 'last_activity_date'
            ])
            
            # TODO (Phase 4+): Update organization aggregate rankings if applicable
            # TODO (Phase 4+): Emit signal for rank-up notifications
            # TODO (Phase 5+): Invalidate leaderboard cache
            
            # Return DTO with match result details
            return MatchResultDelta(
                winner_cp_gain=winner_delta,
                loser_cp_loss=abs(loser_delta),  # Return as positive for display
                winner_new_tier=winner_ranking.tier,
                loser_new_tier=loser_ranking.tier,
                winner_tier_changed=winner_tier_changed,
                loser_tier_changed=loser_tier_changed
            )
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    # ========================================================================
    # RANKING RECOMPUTATION (MAINTENANCE)
    # ========================================================================
    
    @staticmethod
    def recompute_team_ranking(team_id: int) -> RankingSnapshot:
        """
        Recalculate team ranking from match history (admin tool).
        
        This method recomputes crown_points by replaying all match results.
        Only used for:
        - Data integrity repairs (CP corruption detected)
        - Historical match result corrections (admin overrides)
        - Migration from legacy system (Phase 3)
        
        Args:
            team_id: Team primary key
        
        Returns:
            RankingSnapshot DTO with updated values
        
        Raises:
            NotFoundError: If team_id does not exist
        
        Performance Notes:
            - Target: <200ms (p95), ≤10 queries
            - Fetches all team matches via prefetch_related
            - For bulk recomputation, use Celery task (Phase 4+)
        
        Async Boundaries:
            - Bulk recomputation (all teams) MUST use Celery
            - Single team recomputation OK synchronously
        
        Example:
            snapshot = RankingService.recompute_team_ranking(team_id=42)
            print(f"Recalculated: {snapshot.crown_points} CP, {snapshot.tier}")
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    @staticmethod
    def recompute_organization_ranking(organization_id: int) -> RankingSnapshot:
        """
        Recalculate organization aggregate ranking from team CPs.
        
        Organization CP = Average of top 3 team CPs (per game).
        This method recalculates from current team rankings.
        
        Args:
            organization_id: Organization primary key
        
        Returns:
            RankingSnapshot DTO with updated aggregate values
        
        Raises:
            NotFoundError: If organization_id does not exist
            ValidationError: If organization has <3 teams (min for ranking)
        
        Performance Notes:
            - Target: <200ms (p95), ≤10 queries
            - Queries all organization teams and their rankings
            - Aggregates top 3 teams per game
        
        Business Rules:
            - Requires minimum 3 teams for ranking eligibility
            - Inactive/disbanded teams excluded from calculation
            - Tournament temporary teams excluded
        
        Example:
            snapshot = RankingService.recompute_organization_ranking(org_id=42)
            print(f"Org rank: {snapshot.rank_position}, {snapshot.crown_points} CP")
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    # ========================================================================
    # RANKING QUERIES
    # ========================================================================
    
    @staticmethod
    def get_team_ranking(team_id: int) -> RankingSnapshot:
        """
        Retrieve current team ranking state.
        
        Args:
            team_id: Team primary key
        
        Returns:
            RankingSnapshot DTO with current values
        
        Raises:
            NotFoundError: If team_id does not exist
        
        Performance Notes:
            - Target: <50ms (p95), ≤3 queries
            - Computes rank_position via COUNT(*) with CP filter
            - Percentile calculated from total teams in game
        
        Example:
            ranking = RankingService.get_team_ranking(team_id=42)
            template_context['tier_badge'] = ranking.tier
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    @staticmethod
    def get_organization_ranking(organization_id: int) -> RankingSnapshot:
        """
        Retrieve current organization aggregate ranking.
        
        Args:
            organization_id: Organization primary key
        
        Returns:
            RankingSnapshot DTO with aggregate values
        
        Raises:
            NotFoundError: If organization_id does not exist
        
        Performance Notes:
            - Target: <50ms (p95), ≤3 queries
            - Queries OrganizationRanking model (pre-computed)
        
        Example:
            ranking = RankingService.get_organization_ranking(org_id=42)
            leaderboard_entry['org_tier'] = ranking.tier
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    @staticmethod
    def get_leaderboard(
        *,
        entity_type: str = 'TEAM',
        game_id: Optional[int] = None,
        region: Optional[str] = None,
        limit: int = 100
    ) -> List[RankingSnapshot]:
        """
        Retrieve top-ranked entities for leaderboard display.
        
        Args:
            entity_type: 'TEAM' or 'ORGANIZATION'
            game_id: Filter by game (None for global leaderboard)
            region: Filter by region (None for all regions)
            limit: Maximum results to return (default 100, max 1000)
        
        Returns:
            List of RankingSnapshot DTOs sorted by CP descending
        
        Raises:
            ValidationError: If entity_type invalid or limit > 1000
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Uses indexed ORDER BY crown_points DESC
            - Pagination via LIMIT/OFFSET (Phase 4+)
        
        Caching Strategy:
            - Phase 5+: Cache top 1000 entries per game (5-minute TTL)
            - Invalidate on CP updates (async)
        
        Example:
            top_teams = RankingService.get_leaderboard(
                entity_type='TEAM',
                game_id=1,
                region='BD',
                limit=50
            )
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
