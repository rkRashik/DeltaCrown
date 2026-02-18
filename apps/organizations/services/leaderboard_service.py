"""
Leaderboard Service - Unified leaderboard compat layer for vNext and legacy teams.

This module provides a compatibility layer that merges leaderboard data from
both the vNext ranking system and the legacy team system. It returns a unified
leaderboard with proper team URL routing and consistent data format.

COMPATIBILITY: Supports both vNext and legacy teams simultaneously.
PERFORMANCE: Target p95 < 400ms, â‰¤5 queries for leaderboard page load.

Query Strategy:
- Query 1-2: vNext teams with rankings (select_related)
- Query 3-4: Legacy teams with ranking breakdown (select_related)
- Merge and sort in Python (negligible overhead)

Phase 4 - Task P4-T1
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Q, F
from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================================
# DATA TRANSFER OBJECTS
# ============================================================================

@dataclass
class LeaderboardEntry:
    """
    Unified leaderboard entry DTO for both vNext and legacy teams.
    
    This DTO provides a consistent interface for frontend rendering
    regardless of whether the team is vNext or legacy.
    """
    # Core identity
    team_id: int
    team_name: str
    team_slug: str
    
    # Ranking data
    crown_points: int  # vNext: current_cp, Legacy: total_points
    tier: str  # vNext: tier enum, Legacy: derived from points
    rank: int  # 1-based ranking position
    
    # Team metadata
    team_url: str  # Absolute URL to team profile
    logo_url: Optional[str]
    game_id: Optional[int]  # vNext uses game_id (int), legacy uses game (str)
    game_name: Optional[str]
    region: Optional[str]
    
    # System identifier
    is_vnext: bool  # True for vNext teams, False for legacy
    
    # Extended stats (optional)
    win_rate: Optional[float] = None
    matches_played: Optional[int] = None
    hot_streak: Optional[bool] = None


# ============================================================================
# LEADERBOARDSERVICE - PUBLIC API
# ============================================================================

class LeaderboardService:
    """
    Service for generating unified leaderboards from vNext and legacy systems.
    
    This service provides the compatibility layer that allows both systems
    to coexist during the migration period. It queries both databases,
    merges results, and provides a consistent DTO for frontend rendering.
    
    Thread Safety: All methods are thread-safe (no shared mutable state).
    """
    
    # ========================================================================
    # TIER CALCULATION (for legacy teams)
    # ========================================================================
    
    @staticmethod
    def calculate_legacy_tier(total_points: int) -> str:
        """
        Calculate tier for legacy teams based on total_points.
        
        Uses same tier thresholds as vNext for consistency.
        
        Args:
            total_points: Legacy team total_points value
        
        Returns:
            str: Tier name (CROWN, ASCENDANT, DIAMOND, etc.)
        """
        if total_points >= 80000:
            return 'CROWN'
        elif total_points >= 40000:
            return 'ASCENDANT'
        elif total_points >= 15000:
            return 'DIAMOND'
        elif total_points >= 5000:
            return 'PLATINUM'
        elif total_points >= 1500:
            return 'GOLD'
        elif total_points >= 500:
            return 'SILVER'
        elif total_points >= 50:
            return 'BRONZE'
        else:
            return 'UNRANKED'
    
    # ========================================================================
    # TEAM URL ROUTING
    # ========================================================================
    
    @staticmethod
    def get_team_url(team_id: int, team_slug: str, is_vnext: bool) -> str:
        """
        Get correct team profile URL based on system type.
        
        Args:
            team_id: Team primary key
            team_slug: Team URL slug
            is_vnext: True if vNext team, False if legacy
        
        Returns:
            str: Absolute URL path to team profile
        """
        if is_vnext:
            # vNext teams use: /teams/{slug}/ (organizations app)
            return f"/teams/{team_slug}/"
        else:
            # Legacy teams use: /teams/{slug}/ (teams app)
            # Same URL pattern, but different app handles it
            return f"/teams/{team_slug}/"
    
    # ========================================================================
    # vNEXT TEAM QUERIES
    # ========================================================================
    
    @staticmethod
    def get_vnext_teams(
        game_id: Optional[int] = None,
        region: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query vNext teams with rankings.
        
        Args:
            game_id: Filter by game ID
            region: Filter by region
            limit: Maximum results
        
        Returns:
            List of dicts with team and ranking data
        
        Performance:
            - Queries: 1-2 (team query + select_related ranking)
            - Uses index: organizations_ranking.current_cp DESC
        """
        from apps.organizations.models import Team as VNextTeam
        
        queryset = VNextTeam.objects.filter(
            status='ACTIVE'
        ).select_related('ranking', 'organization')
        
        # Filter by game
        if game_id is not None:
            queryset = queryset.filter(game_id=game_id)
        
        # Filter by region
        if region:
            queryset = queryset.filter(region__iexact=region)
        
        # Order by ranking
        queryset = queryset.order_by('-ranking__current_cp')[:limit]
        
        results = []
        for team in queryset:
            try:
                ranking = team.ranking
                results.append({
                    'team_id': team.id,
                    'team_name': team.name,
                    'team_slug': team.slug,
                    'crown_points': ranking.current_cp,
                    'tier': ranking.tier,
                    'logo_url': team.logo.url if team.logo else None,
                    'game_id': team.game_id,
                    'region': team.region,
                    'hot_streak': ranking.is_hot_streak,
                    'is_vnext': True
                })
            except Exception as e:
                logger.warning(
                    f"Error processing vNext team {team.id}: {e}",
                    exc_info=True
                )
                continue
        
        return results
    
    # ========================================================================
    # LEGACY TEAM QUERIES
    # ========================================================================
    
    @staticmethod
    def get_legacy_teams(
        game: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query legacy teams with ranking data.
        
        Args:
            game: Filter by game slug (legacy uses string)
            region: Filter by region
            limit: Maximum results
        
        Returns:
            List of dicts with team and ranking data
        
        Performance:
            - Queries: 1-2 (team query + select_related ranking_breakdown)
            - Uses index: teams_team.total_points DESC
        """
        try:
            from apps.organizations.models import Team as LegacyTeam
        except ImportError:
            logger.debug("Legacy Team model not available, skipping legacy teams")
            return []
        
        queryset = LegacyTeam.objects.filter(
            status='ACTIVE',
            total_points__gt=0  # Only teams with points
        ).select_related('ranking_breakdown')
        
        # Filter by game
        if game:
            queryset = queryset.filter(game=game)
        
        # Filter by region
        if region:
            queryset = queryset.filter(region__iexact=region)
        
        # Order by points
        queryset = queryset.order_by('-total_points')[:limit]
        
        results = []
        for team in queryset:
            try:
                # Calculate tier from total_points
                tier = LeaderboardService.calculate_legacy_tier(team.total_points)
                
                results.append({
                    'team_id': team.id,
                    'team_name': team.name,
                    'team_slug': team.slug,
                    'crown_points': team.total_points,
                    'tier': tier,
                    'logo_url': team.logo.url if team.logo else None,
                    'game_id': None,  # Legacy uses string game field
                    'game_name': team.game,
                    'region': team.region,
                    'hot_streak': False,  # Legacy doesn't track streaks
                    'is_vnext': False
                })
            except Exception as e:
                logger.warning(
                    f"Error processing legacy team {team.id}: {e}",
                    exc_info=True
                )
                continue
        
        return results
    
    # ========================================================================
    # UNIFIED LEADERBOARD
    # ========================================================================
    
    @staticmethod
    def get_unified_leaderboard(
        game_id: Optional[int] = None,
        game: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 100,
        include_legacy: bool = True
    ) -> List[LeaderboardEntry]:
        """
        Get unified leaderboard with both vNext and legacy teams.
        
        This is the main public API for leaderboard generation. It queries
        both systems, merges results, and returns a sorted list of entries.
        
        Args:
            game_id: Filter vNext teams by game ID
            game: Filter legacy teams by game slug
            region: Filter both by region (case-insensitive)
            limit: Total entries to return (split between systems)
            include_legacy: Include legacy teams (set False for vNext-only)
        
        Returns:
            List of LeaderboardEntry DTOs sorted by crown_points DESC
        
        Raises:
            None - Errors are logged, partial results returned
        
        Performance:
            - Queries: â‰¤4 (2 for vNext, 2 for legacy)
            - Target: p95 < 400ms
            - Merge overhead: O(n log n) sorting, typically <10ms
        
        Usage:
            # Get global leaderboard (both systems)
            entries = LeaderboardService.get_unified_leaderboard(limit=50)
            
            # Get game-specific leaderboard
            entries = LeaderboardService.get_unified_leaderboard(
                game_id=1,  # vNext game ID
                game="valorant",  # Legacy game slug
                limit=100
            )
            
            # Get vNext-only leaderboard
            entries = LeaderboardService.get_unified_leaderboard(
                game_id=1,
                include_legacy=False
            )
        """
        all_teams = []
        
        # Query vNext teams
        vnext_teams = LeaderboardService.get_vnext_teams(
            game_id=game_id,
            region=region,
            limit=limit
        )
        all_teams.extend(vnext_teams)
        
        logger.debug(f"Retrieved {len(vnext_teams)} vNext teams for leaderboard")
        
        # Query legacy teams (if enabled)
        if include_legacy:
            legacy_teams = LeaderboardService.get_legacy_teams(
                game=game,
                region=region,
                limit=limit
            )
            all_teams.extend(legacy_teams)
            logger.debug(f"Retrieved {len(legacy_teams)} legacy teams for leaderboard")
        
        # Sort by crown_points (descending)
        all_teams.sort(key=lambda t: t['crown_points'], reverse=True)
        
        # Limit to requested size
        all_teams = all_teams[:limit]
        
        # Convert to DTOs with rank assignment
        entries = []
        for rank, team_data in enumerate(all_teams, start=1):
            entry = LeaderboardEntry(
                # Core identity
                team_id=team_data['team_id'],
                team_name=team_data['team_name'],
                team_slug=team_data['team_slug'],
                
                # Ranking data
                crown_points=team_data['crown_points'],
                tier=team_data['tier'],
                rank=rank,
                
                # Team metadata
                team_url=LeaderboardService.get_team_url(
                    team_id=team_data['team_id'],
                    team_slug=team_data['team_slug'],
                    is_vnext=team_data['is_vnext']
                ),
                logo_url=team_data['logo_url'],
                game_id=team_data.get('game_id'),
                game_name=team_data.get('game_name'),
                region=team_data.get('region'),
                
                # System identifier
                is_vnext=team_data['is_vnext'],
                
                # Extended stats
                hot_streak=team_data.get('hot_streak', False)
            )
            entries.append(entry)
        
        logger.info(
            f"Generated unified leaderboard: {len(entries)} entries "
            f"(vNext: {sum(1 for e in entries if e.is_vnext)}, "
            f"Legacy: {sum(1 for e in entries if not e.is_vnext)})"
        )
        
        return entries
    
    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================
    
    @staticmethod
    def get_vnext_only_leaderboard(
        game_id: Optional[int] = None,
        region: Optional[str] = None,
        limit: int = 100
    ) -> List[LeaderboardEntry]:
        """
        Get vNext-only leaderboard (excludes legacy teams).
        
        Convenience method for vNext-specific rankings.
        """
        return LeaderboardService.get_unified_leaderboard(
            game_id=game_id,
            region=region,
            limit=limit,
            include_legacy=False
        )
    
    @staticmethod
    def format_for_template(entries: List[LeaderboardEntry]) -> List[Dict[str, Any]]:
        """
        Convert LeaderboardEntry DTOs to template-friendly dicts.
        
        Args:
            entries: List of LeaderboardEntry DTOs
        
        Returns:
            List of dicts with all fields as JSON-serializable types
        """
        return [
            {
                'team_id': e.team_id,
                'team_name': e.team_name,
                'team_slug': e.team_slug,
                'crown_points': e.crown_points,
                'tier': e.tier,
                'rank': e.rank,
                'team_url': e.team_url,
                'logo_url': e.logo_url,
                'game_id': e.game_id,
                'game_name': e.game_name,
                'region': e.region,
                'is_vnext': e.is_vnext,
                'hot_streak': e.hot_streak,
                'win_rate': e.win_rate,
                'matches_played': e.matches_played
            }
            for e in entries
        ]
