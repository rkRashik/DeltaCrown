"""
Competition Service - Phase 9 Service Layer

Provides unified interface for rankings, leaderboards, and competition features.
This service abstracts competition logic and enforces query budgets.

Phase 17: Unified on Crown Points (organizations.TeamRanking) as the single
source of truth.  The legacy competition snapshot tables are deprecated but
not removed — this service now reads exclusively from the CP system.
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


# ── Game lineup size lookup ─────────────────────────────────────────────────
_GAME_LINEUP_SIZES: dict = {
    'valorant': 5, 'cs2': 5, 'counter-strike 2': 5,
    'dota 2': 5, 'dota2': 5, 'league of legends': 5,
    'pubg': 4, 'pubg mobile': 4,
    'apex legends': 3, 'fortnite': 3, 'rocket league': 3,
    'efootball': 5, 'call of duty': 5,
    'rainbow six': 5, 'overwatch 2': 5,
}


def _lineup_size(game_name: Optional[str]) -> int:
    """Return the standard roster display size for a game."""
    if not game_name:
        return 5
    key = game_name.lower().strip()
    for pattern, size in _GAME_LINEUP_SIZES.items():
        if pattern in key:
            return size
    return 5


def _membership_sort_key(m) -> int:
    """Sort key: tournament captain first, then owner, manager, starter players, etc."""
    if getattr(m, 'is_tournament_captain', False):
        return 0
    role = (getattr(m, 'role', '') or '').upper()
    if role == 'OWNER':
        return 1
    if role == 'MANAGER':
        return 2
    slot = (getattr(m, 'roster_slot', '') or '').upper()
    if role == 'PLAYER' and slot == 'STARTER':
        return 3
    if role == 'PLAYER':
        return 4
    if role in ('COACH', 'SUBSTITUTE'):
        return 5
    return 6


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
    team_logo_url: Optional[str] = None
    team_tag: Optional[str] = None
    activity_score: int = 0
    team_banner_url: Optional[str] = None
    game_name: Optional[str] = None
    roster_avatars: Optional[List[dict]] = None
    
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

        Phase 17: Reads from organizations_ranking (Crown Points)
        instead of the deprecated competition snapshot tables.
        """
        from django.db.models import Value, IntegerField
        from django.db.models.functions import Coalesce
        from apps.organizations.choices import TeamStatus

        cache_key = f'competition:global_rankings:{tier}:{verified_only}:{limit}:{offset}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        from apps.organizations.models import TeamMembership
        from apps.games.models import Game

        # Build game name lookup (cheap — usually <10 games)
        game_names = {}
        try:
            game_names = {g.id: g.display_name or g.name for g in Game.objects.filter(is_active=True)}
        except Exception:
            pass

        queryset = Team.objects.filter(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
        ).select_related('organization', 'ranking').prefetch_related(
            Prefetch(
                'vnext_memberships',
                queryset=TeamMembership.objects.filter(status='ACTIVE').select_related('user__profile').only(
                    'id', 'team_id', 'display_name', 'roster_image',
                    'role', 'roster_slot', 'is_tournament_captain',
                    'user__id', 'user__username', 'user__profile__avatar',
                ),
                to_attr='active_roster',
            )
        ).annotate(
            display_score=Coalesce('ranking__current_cp', Value(0)),
            display_tier=Coalesce('ranking__tier', Value('ROOKIE')),
            display_rank=Coalesce('ranking__global_rank', Value(None, output_field=IntegerField())),
            display_activity=Coalesce('ranking__activity_score', Value(0)),
        )

        if tier and tier in ['THE_CROWN', 'LEGEND', 'MASTER', 'ELITE', 'CHALLENGER', 'ROOKIE']:
            queryset = queryset.filter(display_tier=tier)

        queryset = queryset.order_by('-display_score', '-created_at')
        total_count = queryset.count()
        paginated = queryset[offset:offset + limit]

        entries = []
        for idx, team in enumerate(paginated, start=offset + 1):
            org = team.organization
            # Build roster avatar list (max 5)
            game_name_for_team = game_names.get(team.game_id)
            lineup_size = _lineup_size(game_name_for_team)
            sorted_roster = sorted(getattr(team, 'active_roster', []), key=_membership_sort_key)
            roster = []
            for m in sorted_roster[:lineup_size]:
                avatar = None
                if m.roster_image:
                    avatar = m.roster_image.url
                elif hasattr(m, 'user') and hasattr(m.user, 'profile') and m.user.profile.avatar:
                    avatar = m.user.profile.avatar.url
                roster.append({'name': m.display_name or m.user.username, 'avatar_url': avatar})

            entry = RankingEntry(
                rank=team.display_rank if team.display_rank else idx,
                team_id=team.id,
                team_name=team.name,
                team_slug=team.slug,
                team_url='',
                organization_id=org.id if org else None,
                organization_name=org.name if org else None,
                score=team.display_score,
                tier=team.display_tier,
                confidence_level='STABLE',
                is_independent=(org is None),
                team_logo_url=team.logo.url if team.logo else None,
                team_tag=team.tag,
                activity_score=team.display_activity,
                team_banner_url=team.banner.url if team.banner else None,
                game_name=game_name_for_team,
                roster_avatars=roster or None,
            )
            entries.append(entry)

        response = RankingsResponse(
            entries=entries,
            total_count=total_count,
            tier_filter=tier,
            is_global=True,
            query_count=2,
        )
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

        Phase 17: Reads from organizations_ranking (Crown Points)
        instead of the deprecated competition snapshot tables.
        """
        from django.db.models import Value, IntegerField
        from django.db.models.functions import Coalesce
        from apps.organizations.choices import TeamStatus

        try:
            game_id_int = int(game_id)
        except (ValueError, TypeError):
            return RankingsResponse(entries=[], total_count=0, query_count=1)

        cache_key = f'competition:game_rankings:{game_id}:{tier}:{verified_only}:{limit}:{offset}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        from apps.organizations.models import TeamMembership
        from apps.games.models import Game

        # Get game name for this specific game
        game_name_str = None
        try:
            g = Game.objects.filter(id=game_id_int, is_active=True).values_list('display_name', 'name').first()
            if g:
                game_name_str = g[0] or g[1]
        except Exception:
            pass

        queryset = Team.objects.filter(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            game_id=game_id_int,
        ).select_related('organization', 'ranking').prefetch_related(
            Prefetch(
                'vnext_memberships',
                queryset=TeamMembership.objects.filter(status='ACTIVE').select_related('user__profile').only(
                    'id', 'team_id', 'display_name', 'roster_image',
                    'role', 'roster_slot', 'is_tournament_captain',
                    'user__id', 'user__username', 'user__profile__avatar',
                ),
                to_attr='active_roster',
            )
        ).annotate(
            display_score=Coalesce('ranking__current_cp', Value(0)),
            display_tier=Coalesce('ranking__tier', Value('ROOKIE')),
            display_rank=Coalesce('ranking__global_rank', Value(None, output_field=IntegerField())),
            display_activity=Coalesce('ranking__activity_score', Value(0)),
        )

        if tier and tier in ['THE_CROWN', 'LEGEND', 'MASTER', 'ELITE', 'CHALLENGER', 'ROOKIE']:
            queryset = queryset.filter(display_tier=tier)

        queryset = queryset.order_by('-display_score', '-created_at', 'name')
        total_count = queryset.count()
        paginated = queryset[offset:offset + limit]

        lineup_size = _lineup_size(game_name_str)
        entries = []
        for idx, team in enumerate(paginated, start=offset + 1):
            org = team.organization
            # Build roster with captain-first sorting and game-specific lineup size
            sorted_roster = sorted(getattr(team, 'active_roster', []), key=_membership_sort_key)
            roster = []
            for m in sorted_roster[:lineup_size]:
                avatar = None
                if m.roster_image:
                    avatar = m.roster_image.url
                elif hasattr(m, 'user') and hasattr(m.user, 'profile') and m.user.profile.avatar:
                    avatar = m.user.profile.avatar.url
                roster.append({'name': m.display_name or m.user.username, 'avatar_url': avatar})

            entry = RankingEntry(
                rank=team.display_rank if team.display_rank else idx,
                team_id=team.id,
                team_name=team.name,
                team_slug=team.slug,
                team_url='',
                organization_id=org.id if org else None,
                organization_name=org.name if org else None,
                score=team.display_score,
                tier=team.display_tier,
                confidence_level='STABLE',
                is_independent=(org is None),
                team_logo_url=team.logo.url if team.logo else None,
                team_tag=team.tag,
                activity_score=team.display_activity,
                team_banner_url=team.banner.url if team.banner else None,
                game_name=game_name_str,
                roster_avatars=roster or None,
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
        cache.set(cache_key, response, CompetitionService.GAME_RANKINGS_CACHE_TIMEOUT)
        return response
    
    @staticmethod
    def get_team_rank(team_id: int, game_id: Optional[str] = None) -> Dict:
        """
        Get rank information for a specific team.

        Phase 17: Reads from organizations_ranking (Crown Points).
        game_id filter is accepted but ignored (CP is cross-game).
        """
        from apps.organizations.models import TeamRanking

        cache_key = f'competition:team_rank:{team_id}:{game_id or "global"}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            ranking = TeamRanking.objects.get(team_id=team_id)
        except TeamRanking.DoesNotExist:
            cache.set(cache_key, None, CompetitionService.TEAM_RANK_CACHE_TIMEOUT)
            return None

        result = {
            'rank': ranking.global_rank,
            'tier': ranking.tier,
            'score': ranking.current_cp,
            'confidence_level': 'STABLE',
            'is_global': True,
        }
        cache.set(cache_key, result, CompetitionService.TEAM_RANK_CACHE_TIMEOUT)
        return result
    
    @staticmethod
    def get_org_empire_score(org_id: int) -> Dict:
        """
        Get aggregated "Empire Score" for an organization.

        Phase 17: Reads from organizations_ranking (Crown Points).
        """
        from apps.organizations.models import TeamRanking

        cache_key = f'competition:org_empire:{org_id}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        rankings = (
            TeamRanking.objects
            .filter(team__organization_id=org_id, team__status='ACTIVE')
            .select_related('team')
            .order_by('-current_cp')
        )

        if not rankings.exists():
            result = {'total_score': 0, 'team_count': 0, 'top_tier': 'ROOKIE', 'teams': []}
            cache.set(cache_key, result, CompetitionService.TEAM_RANK_CACHE_TIMEOUT)
            return result

        teams_list = [
            {
                'team_id': r.team.id,
                'team_name': r.team.name,
                'team_slug': r.team.slug,
                'score': r.current_cp,
                'tier': r.tier,
                'rank': r.global_rank,
            }
            for r in rankings
        ]

        result = {
            'total_score': sum(t['score'] for t in teams_list),
            'team_count': len(teams_list),
            'top_tier': teams_list[0]['tier'] if teams_list else 'ROOKIE',
            'teams': teams_list,
        }
        cache.set(cache_key, result, CompetitionService.TEAM_RANK_CACHE_TIMEOUT)
        return result
    
    @staticmethod
    def get_user_team_highlights(user_id: int) -> Dict:
        """
        Get ranking highlights for teams where user is a member.

        Phase 17: Reads from organizations_ranking (Crown Points).
        """
        from apps.organizations.models import TeamMembership, TeamRanking

        memberships = TeamMembership.objects.filter(
            user_id=user_id,
            status='ACTIVE',
        ).select_related('team', 'team__ranking')

        teams_data = []
        best_rank = None

        for membership in memberships:
            team = membership.team
            try:
                ranking = team.ranking
                rank = ranking.global_rank
                tier = ranking.tier
                score = ranking.current_cp
                if rank is not None and (best_rank is None or rank < best_rank):
                    best_rank = rank
            except TeamRanking.DoesNotExist:
                rank = None
                tier = 'ROOKIE'
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
