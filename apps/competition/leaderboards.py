"""Leaderboard views for competition app (Phase 9 - Service Layer)."""
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from apps.competition.models import GameRankingConfig
from apps.competition.services.competition_service import CompetitionService


def leaderboard_global(request):
    """
    Global leaderboard showing all teams ranked by global_score.
    
    Phase 9: Uses CompetitionService for data retrieval.
    
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
    
    # Use service layer
    response = CompetitionService.get_global_rankings(
        tier=tier_filter if tier_filter else None,
        verified_only=verified_only,
        limit=100,
        offset=0
    )
    
    # Get user's team highlights if authenticated
    user_highlights = None
    if request.user.is_authenticated:
        user_highlights = CompetitionService.get_user_team_highlights(request.user.id)
    
    context = {
        'rankings': response,
        'entries': response.entries,
        'total_count': response.total_count,
        'tier_filter': tier_filter,
        'verified_only': verified_only,
        'available_tiers': ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'UNRANKED'],
        'is_global': True,
        'user_highlights': user_highlights,
        'query_count': response.query_count,
    }
    
    return render(request, 'competition/leaderboards/leaderboard_global.html', context)


def leaderboard_game(request, game_id):
    """
    Per-game leaderboard showing teams ranked by game-specific score.
    
    Phase 9: Uses CompetitionService for data retrieval.
    
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
    
    # Use service layer
    response = CompetitionService.get_game_rankings(
        game_id=game_id,
        tier=tier_filter if tier_filter else None,
        verified_only=verified_only,
        limit=100,
        offset=0
    )
    
    # Get user's team highlights if authenticated
    user_highlights = None
    if request.user.is_authenticated:
        user_highlights = CompetitionService.get_user_team_highlights(request.user.id)
    
    context = {
        'rankings': response,
        'entries': response.entries,
        'total_count': response.total_count,
        'game_config': game_config,
        'game_id': game_id,
        'tier_filter': tier_filter,
        'verified_only': verified_only,
        'available_tiers': ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'UNRANKED'],
        'is_global': False,
        'user_highlights': user_highlights,
        'query_count': response.query_count,
    }
    
    return render(request, 'competition/leaderboards/leaderboard_game.html', context)
