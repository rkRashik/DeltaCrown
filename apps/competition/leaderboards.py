"""Leaderboard views for competition app (Phase 3A-E)."""
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from apps.competition.models import (
    TeamGlobalRankingSnapshot,
    TeamGameRankingSnapshot,
    GameRankingConfig,
)


def leaderboard_global(request):
    """
    Global leaderboard showing all teams ranked by global_score.
    
    Query params:
    - tier: Filter by tier (DIAMOND, PLATINUM, GOLD, SILVER, BRONZE, UNRANKED)
    - verified_only: Show only teams with STABLE/ESTABLISHED confidence (1/0)
    """
    # Check if competition app is enabled
    if not getattr(settings, 'COMPETITION_APP_ENABLED', False):
        return render(request, 'competition/leaderboards/unavailable.html', {
            'message': 'Rankings are temporarily unavailable. Please check back later.'
        })
    
    # Get filter params
    tier_filter = request.GET.get('tier', '').upper()
    verified_only = request.GET.get('verified_only') == '1'
    
    # Build queryset
    queryset = TeamGlobalRankingSnapshot.objects.select_related('team').order_by('global_rank')
    
    if tier_filter and tier_filter in ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'UNRANKED']:
        queryset = queryset.filter(global_tier=tier_filter)
    
    if verified_only:
        # Filter to teams that have at least one game snapshot with STABLE or ESTABLISHED confidence
        queryset = queryset.filter(
            team__game_ranking_snapshots__confidence_level__in=['STABLE', 'ESTABLISHED']
        ).distinct()
    
    # Paginate or limit (first 100 for performance)
    snapshots = queryset[:100]
    
    context = {
        'snapshots': snapshots,
        'tier_filter': tier_filter,
        'verified_only': verified_only,
        'available_tiers': ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'UNRANKED'],
        'is_global': True,
    }
    
    return render(request, 'competition/leaderboards/leaderboard_global.html', context)


def leaderboard_game(request, game_id):
    """
    Per-game leaderboard showing teams ranked by game-specific score.
    
    Query params:
    - tier: Filter by tier
    - verified_only: Show only teams with STABLE/ESTABLISHED confidence
    - season_id: (Optional) Filter by season (not yet implemented)
    """
    # Check if competition app is enabled
    if not getattr(settings, 'COMPETITION_APP_ENABLED', False):
        return render(request, 'competition/leaderboards/unavailable.html', {
            'message': 'Rankings are temporarily unavailable. Please check back later.'
        })
    
    # Get game config
    game_config = get_object_or_404(GameRankingConfig, game_id=game_id)
    
    # Get filter params
    tier_filter = request.GET.get('tier', '').upper()
    verified_only = request.GET.get('verified_only') == '1'
    
    # Build queryset
    queryset = TeamGameRankingSnapshot.objects.filter(
        game_id=game_id
    ).select_related('team').order_by('rank')
    
    if tier_filter and tier_filter in ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'UNRANKED']:
        queryset = queryset.filter(tier=tier_filter)
    
    if verified_only:
        queryset = queryset.filter(
            Q(confidence_level='STABLE') | Q(confidence_level='ESTABLISHED')
        )
    
    # Paginate or limit
    snapshots = queryset[:100]
    
    context = {
        'snapshots': snapshots,
        'game_config': game_config,
        'game_id': game_id,
        'tier_filter': tier_filter,
        'verified_only': verified_only,
        'available_tiers': ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'UNRANKED'],
        'is_global': False,
    }
    
    return render(request, 'competition/leaderboards/leaderboard_game.html', context)
