"""Leaderboard views for competition app (Phase 9 - Service Layer)."""
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from apps.competition.models import GameRankingConfig
from apps.competition.services.competition_service import CompetitionService
from apps.games.models import Game


# Tier display info for the tier explainer section
TIER_DETAILS = [
    {'name': 'Diamond', 'icon': 'fa-gem', 'icon_color': 'text-blue-400', 'bg_class': 'bg-blue-500/10', 'threshold': '2000'},
    {'name': 'Platinum', 'icon': 'fa-medal', 'icon_color': 'text-cyan-400', 'bg_class': 'bg-cyan-500/10', 'threshold': '1500'},
    {'name': 'Gold', 'icon': 'fa-crown', 'icon_color': 'text-yellow-400', 'bg_class': 'bg-yellow-500/10', 'threshold': '1000'},
    {'name': 'Silver', 'icon': 'fa-shield-alt', 'icon_color': 'text-gray-400', 'bg_class': 'bg-gray-500/10', 'threshold': '600'},
    {'name': 'Bronze', 'icon': 'fa-dice-d6', 'icon_color': 'text-orange-400', 'bg_class': 'bg-orange-500/10', 'threshold': '300'},
    {'name': 'Unranked', 'icon': 'fa-minus', 'icon_color': 'text-slate-500', 'bg_class': 'bg-slate-500/10', 'threshold': '0'},
]


def _get_game_configs_with_colors():
    """Get all active GameRankingConfigs enriched with game color info."""
    configs = list(GameRankingConfig.objects.filter(is_active=True).order_by('game_name'))
    # Try to enrich with primary_color from Game model
    game_colors = {}
    try:
        games = Game.objects.filter(is_active=True).values_list('short_code', 'primary_color')
        game_colors = {code.upper(): color for code, color in games if code}
        # Also index by slug
        games_by_slug = Game.objects.filter(is_active=True).values_list('slug', 'primary_color')
        for slug, color in games_by_slug:
            if slug:
                game_colors[slug.upper()] = color
    except Exception:
        pass

    for config in configs:
        config.color = game_colors.get(config.game_id.upper(), '#64748b')
    return configs


def leaderboard_global(request):
    """
    Global leaderboard showing all teams ranked by global_score.

    Phase 9: Uses CompetitionService for data retrieval.
    Phase 11: Redesigned with game selector tabs and premium theme.

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

    # Compute max score for score bar width
    max_score = max((e.score for e in response.entries), default=1) or 1

    # Game configs for the game selector tabs
    game_configs = _get_game_configs_with_colors()

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
        'game_configs': game_configs,
        'max_score': max_score,
        'selected_game': None,
        'selected_game_name': None,
        'tier_details': TIER_DETAILS,
    }

    return render(request, 'competition/leaderboards/leaderboard_global.html', context)


def leaderboard_game(request, game_id):
    """
    Per-game leaderboard showing teams ranked by game-specific score.

    Phase 9: Uses CompetitionService for data retrieval.
    Phase 11: Redesigned with game selector tabs and premium theme.

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

    # Compute max score for score bar width
    max_score = max((e.score for e in response.entries), default=1) or 1

    # Game configs for the game selector tabs
    game_configs = _get_game_configs_with_colors()

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
        'game_configs': game_configs,
        'max_score': max_score,
        'selected_game': game_id,
        'selected_game_name': game_config.game_name,
        'tier_details': TIER_DETAILS,
    }

    return render(request, 'competition/leaderboards/leaderboard_global.html', context)
