"""
Competition Service - Phase 9 Service Layer

Provides unified interface for rankings, leaderboards, and competition features.
This service abstracts competition logic and enforces query budgets.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from django.db.models import QuerySet, Prefetch, Q
from django.core.cache import cache

from apps.competition.models import (
    TeamGlobalRankingSnapshot,
    TeamGameRankingSnapshot,
    GameRankingConfig,
)
from apps.organizations.models import Team, Organization


@dataclass
class RankingEntry:
    """Single ranking entry for display."""
    rank: int
    team_id: int
    team_name: str
    team_slug: str
    team_url: str
    organization_id: Optional[int]
    organization_name: Optional[str]
    score: int
    tier: str
    confidence_level: str
    is_independent: bool
    
    def __post_init__(self):
        """Calculate team URL based on team type."""
        if self.is_independent:
            self.team_url = f'/teams/{self.team_slug}/'
        elif self.organization_id:
            # For org teams, we'd need org slug - for now use team slug
            self.team_url = f'/teams/{self.team_slug}/'


@dataclass
class RankingsResponse:
    """Response container for rankings queries."""
    entries: List[RankingEntry]
    total_count: int
    game_id: Optional[str] = None
    tier_filter: Optional[str] = None
    is_global: bool = True
    query_count: int = 0


class CompetitionService:
    """
    Service layer for competition features.
    
    Phase 9: Competition is canonical for rankings.
    All ranking queries go through this service.
    """
    
    # Cache timeouts
    GLOBAL_RANKINGS_CACHE_TIMEOUT = 300  # 5 minutes
    GAME_RANKINGS_CACHE_TIMEOUT = 300    # 5 minutes
    TEAM_RANK_CACHE_TIMEOUT = 600        # 10 minutes
    
    @staticmethod
    def get_global_rankings(
        tier: Optional[str] = None,
        verified_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> RankingsResponse:
        """
        Get global rankings across all games.
        
        Phase 14 Fix: Now includes ALL PUBLIC ACTIVE teams, even with 0 points.
        Teams without snapshots appear as score=0, tier=UNRANKED.
        
        Args:
            tier: Filter by tier (DIAMOND, PLATINUM, GOLD, SILVER, BRONZE, UNRANKED)
            verified_only: Show only verified teams (STABLE/ESTABLISHED confidence)
            limit: Max results (default 100)
            offset: Pagination offset
            
        Returns:
            RankingsResponse with entries and metadata
        """
        from django.db.models import OuterRef, Subquery, IntegerField, CharField, Q, F, Value
        from django.db.models.functions import Coalesce
        from apps.organizations.choices import TeamStatus
        
        # Build cache key
        cache_key = f'competition:global_rankings:{tier}:{verified_only}:{limit}:{offset}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Phase 16: Start from ALL PUBLIC ACTIVE teams (not just snapshot table)
        # LEFT JOIN ranking snapshots to get score/tier/rank or default to 0/UNRANKED/NULL
        # This ensures brand new teams with 0 points appear in rankings
        
        # TeamGlobalRankingSnapshot fields: global_score, global_tier, global_rank, games_played
        queryset = Team.objects.filter(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC'
        ).select_related('organization').annotate(
            # Coalesce snapshot fields to defaults (snapshot may not exist for new teams)
            display_score=Coalesce('global_ranking_snapshot__global_score', Value(0)),
            display_tier=Coalesce('global_ranking_snapshot__global_tier', Value('UNRANKED')),
            display_rank=Coalesce('global_ranking_snapshot__global_rank', Value(None, output_field=IntegerField())),
            display_games_played=Coalesce('global_ranking_snapshot__games_played', Value(0)),
        )
        
        # Apply tier filter (AFTER annotation)
        if tier and tier in ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'UNRANKED']:
            queryset = queryset.filter(display_tier=tier)
        
        # Apply verified_only filter (games_played >= 5 considered stable)
        if verified_only:
            queryset = queryset.filter(display_games_played__gte=5)
        
        # Order by: score DESC, created_at DESC (tie-breaker for 0-point teams)
        queryset = queryset.order_by('-display_score', '-created_at')
        
        # Count total (before pagination)
        total_count = queryset.count()
        
        # Apply pagination
        paginated = queryset[offset:offset + limit]
        
        # Build entries with computed rank
        entries = []
        for idx, team in enumerate(paginated, start=offset + 1):
            org = team.organization
            
            # Derive confidence from games_played
            if team.display_games_played >= 20:
                confidence = 'STABLE'
            elif team.display_games_played >= 10:
                confidence = 'ESTABLISHED'
            elif team.display_games_played >= 1:
                confidence = 'PROVISIONAL'
            else:
                confidence = 'UNVERIFIED'
            
            entry = RankingEntry(
                rank=team.display_rank if team.display_rank else idx,  # Use DB rank or computed
                team_id=team.id,
                team_name=team.name,
                team_slug=team.slug,
                team_url='',  # Will be set in __post_init__
                organization_id=org.id if org else None,
                organization_name=org.name if org else None,
                score=team.display_score,
                tier=team.display_tier,
                confidence_level=confidence,
                is_independent=(org is None),
            )
            entries.append(entry)
        
        response = RankingsResponse(
            entries=entries,
            total_count=total_count,
            tier_filter=tier,
            is_global=True,
            query_count=2,  # 1 for queryset, 1 for count
        )
        
        # Cache result
        cache.set(cache_key, response, CompetitionService.GLOBAL_RANKINGS_CACHE_TIMEOUT)
        
        return response
    
    @staticmethod
    def get_game_rankings(
        game_id: str,
        tier: Optional[str] = None,
        verified_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> RankingsResponse:
        """
        Get rankings for a specific game.
        
        Phase 14 Fix: Now includes ALL PUBLIC ACTIVE teams for this game, even with 0 points.
        Teams without snapshots appear as score=0, tier=UNRANKED.
        
        Args:
            game_id: Game identifier (e.g., 'valorant', 'cs2')
            tier: Filter by tier
            verified_only: Show only verified teams
            limit: Max results
            offset: Pagination offset
            
        Returns:
            RankingsResponse with entries and metadata
        """
        from django.db.models import OuterRef, Subquery, IntegerField, CharField, Q, F, Value
        from django.db.models.functions import Coalesce
        from apps.organizations.choices import TeamStatus
        
        # Build cache key
        cache_key = f'competition:game_rankings:{game_id}:{tier}:{verified_only}:{limit}:{offset}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Phase 14: Start from ALL PUBLIC ACTIVE teams for this game
        # LEFT JOIN game ranking snapshots
        
        # Subquery to get game-specific snapshot
        game_snapshot_subq = TeamGameRankingSnapshot.objects.filter(
            team=OuterRef('pk'),
            game_id=game_id
        ).order_by('-snapshot_date')[:1]
        
        queryset = Team.objects.filter(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            game_id=game_id  # Filter by game
        ).annotate(
            # Annotate snapshot fields
            snapshot_score=Subquery(game_snapshot_subq.values('score')[:1], output_field=IntegerField()),
            snapshot_rank=Subquery(game_snapshot_subq.values('rank')[:1], output_field=IntegerField()),
            snapshot_tier=Subquery(game_snapshot_subq.values('tier')[:1], output_field=CharField()),
            snapshot_confidence=Subquery(game_snapshot_subq.values('confidence_level')[:1], output_field=CharField()),
            # Coalesce to defaults
            display_score=Coalesce('snapshot_score', Value(0)),
            display_tier=Coalesce('snapshot_tier', Value('UNRANKED')),
        ).select_related('organization')
        
        # Apply tier filter
        if tier and tier in ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'UNRANKED']:
            queryset = queryset.filter(display_tier=tier)
        
        # Apply verified_only filter
        if verified_only:
            queryset = queryset.filter(snapshot_confidence__in=['STABLE', 'ESTABLISHED'])
        
        # Order by: score DESC, created_at DESC, name ASC (final tie-breaker)
        queryset = queryset.order_by('-display_score', '-created_at', 'name')
        
        # Count total
        total_count = queryset.count()
        
        # Apply pagination
        paginated = queryset[offset:offset + limit]
        
        # Build entries with computed rank
        entries = []
        for idx, team in enumerate(paginated, start=offset + 1):
            org = team.organization
            
            # Use snapshot confidence or fallback to UNVERIFIED
            confidence = getattr(team, 'snapshot_confidence', None) or 'UNVERIFIED'
            
            entry = RankingEntry(
                rank=team.snapshot_rank if team.snapshot_rank else idx,
                team_id=team.id,
                team_name=team.name,
                team_slug=team.slug,
                team_url='',  # Set in __post_init__
                organization_id=org.id if org else None,
                organization_name=org.name if org else None,
                score=team.display_score,
                tier=team.display_tier,
                confidence_level=confidence,
                is_independent=(org is None),
            )
            entries.append(entry)
        
        response = RankingsResponse(
            entries=entries,
            total_count=total_count,
            game_id=game_id,
            tier_filter=tier,
            is_global=False,
            query_count=2,
        )
        
        # Cache result
        cache.set(cache_key, response, CompetitionService.GAME_RANKINGS_CACHE_TIMEOUT)
        
        return response
    
    @staticmethod
    def get_team_rank(team_id: int, game_id: Optional[str] = None) -> Dict:
        """
        Get rank information for a specific team.
        
        Args:
            team_id: Team ID
            game_id: Optional game filter (returns global rank if not provided)
            
        Returns:
            Dict with rank, tier, score, confidence_level
            Returns None if team not ranked
        """
        cache_key = f'competition:team_rank:{team_id}:{game_id or "global"}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        result = None
        
        if game_id:
            # Game-specific rank
            snapshot = TeamGameRankingSnapshot.objects.filter(
                team_id=team_id,
                game_id=game_id
            ).first()
            
            if snapshot:
                result = {
                    'rank': snapshot.rank,
                    'tier': snapshot.tier,
                    'score': snapshot.score,
                    'confidence_level': snapshot.confidence_level,
                    'game_id': game_id,
                    'is_global': False,
                }
        else:
            # Global rank
            snapshot = TeamGlobalRankingSnapshot.objects.filter(
                team_id=team_id
            ).first()
            
            if snapshot:
                result = {
                    'rank': snapshot.global_rank,
                    'tier': snapshot.global_tier,
                    'score': snapshot.global_score,
                    'confidence_level': snapshot.confidence_level,
                    'is_global': True,
                }
        
        # Cache result (even if None)
        cache.set(cache_key, result, CompetitionService.TEAM_RANK_CACHE_TIMEOUT)
        
        return result
    
    @staticmethod
    def get_org_empire_score(org_id: int) -> Dict:
        """
        Get aggregated "Empire Score" for an organization.
        
        Args:
            org_id: Organization ID
            
        Returns:
            Dict with total_score, team_count, top_tier
            Returns empty dict if org has no ranked teams
        """
        cache_key = f'competition:org_empire:{org_id}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Get all teams belonging to organization
        team_snapshots = TeamGlobalRankingSnapshot.objects.filter(
            team__organization_id=org_id
        ).select_related('team')
        
        if not team_snapshots.exists():
            result = {
                'total_score': 0,
                'team_count': 0,
                'top_tier': 'UNRANKED',
                'teams': [],
            }
            cache.set(cache_key, result, CompetitionService.TEAM_RANK_CACHE_TIMEOUT)
            return result
        
        # Aggregate scores
        total_score = sum(s.global_score for s in team_snapshots)
        team_count = team_snapshots.count()
        
        # Determine top tier (best tier among teams)
        tier_priority = {
            'DIAMOND': 5,
            'PLATINUM': 4,
            'GOLD': 3,
            'SILVER': 2,
            'BRONZE': 1,
            'UNRANKED': 0,
        }
        
        top_tier = 'UNRANKED'
        max_priority = 0
        
        for snapshot in team_snapshots:
            tier = snapshot.global_tier
            priority = tier_priority.get(tier, 0)
            if priority > max_priority:
                max_priority = priority
                top_tier = tier
        
        # Build team list
        teams = [
            {
                'team_id': s.team.id,
                'team_name': s.team.name,
                'team_slug': s.team.slug,
                'score': s.global_score,
                'tier': s.global_tier,
                'rank': s.global_rank,
            }
            for s in team_snapshots
        ]
        
        result = {
            'total_score': total_score,
            'team_count': team_count,
            'top_tier': top_tier,
            'teams': teams,
        }
        
        cache.set(cache_key, result, CompetitionService.TEAM_RANK_CACHE_TIMEOUT)
        
        return result
    
    @staticmethod
    def get_user_team_highlights(user_id: int) -> Dict:
        """
        Get ranking highlights for teams where user is a member.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with best_rank, teams list, total_teams
        """
        from apps.organizations.models import TeamMembership
        
        # Get teams where user is active member
        memberships = TeamMembership.objects.filter(
            user_id=user_id,
            status='ACTIVE'
        ).select_related('team').prefetch_related('team__global_ranking_snapshot')
        
        teams_data = []
        best_rank = None
        
        for membership in memberships:
            team = membership.team
            
            # Get team's global ranking
            try:
                snapshot = team.global_ranking_snapshot
                rank = snapshot.global_rank
                tier = snapshot.global_tier
                score = snapshot.global_score
                
                if best_rank is None or rank < best_rank:
                    best_rank = rank
            except (AttributeError, TeamGlobalRankingSnapshot.DoesNotExist):
                rank = None
                tier = 'UNRANKED'
                score = 0
            
            teams_data.append({
                'team_id': team.id,
                'team_name': team.name,
                'team_slug': team.slug,
                'rank': rank,
                'tier': tier,
                'score': score,
                'role': membership.role,
                'is_independent': team.organization_id is None,
            })
        
        return {
            'best_rank': best_rank,
            'teams': teams_data,
            'total_teams': len(teams_data),
        }
    
    @staticmethod
    def invalidate_team_rank_cache(team_id: int):
        """
        Invalidate cached ranking data for a team.
        Called after match verification or tournament completion.
        """
        from apps.organizations.services.cache_invalidation import safe_cache_delete_pattern
        # Invalidate all cache keys for this team
        safe_cache_delete_pattern(f'competition:team_rank:{team_id}:*')
        
        # Invalidate global/game rankings that might include this team
        safe_cache_delete_pattern('competition:global_rankings:*')
        safe_cache_delete_pattern('competition:game_rankings:*')
    
    @staticmethod
    def invalidate_org_cache(org_id: int):
        """Invalidate organization empire score cache."""
        cache.delete(f'competition:org_empire:{org_id}')
