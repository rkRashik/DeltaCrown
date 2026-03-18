"""Leaderboard views for competition app (Phase 9 - Service Layer)."""
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from apps.competition.models import GameRankingConfig
from apps.competition.services.competition_service import CompetitionService
from apps.games.models import Game


# Tier display info for the tier explainer section (Crown Points system)
TIER_DETAILS = [
    {'name': 'The Crown', 'icon': 'fa-crown', 'icon_color': 'text-yellow-300', 'bg_class': 'bg-yellow-400/10', 'threshold': '30,000'},
    {'name': 'Legend', 'icon': 'fa-fire', 'icon_color': 'text-red-400', 'bg_class': 'bg-red-500/10', 'threshold': '8,000'},
    {'name': 'Master', 'icon': 'fa-gem', 'icon_color': 'text-blue-400', 'bg_class': 'bg-blue-500/10', 'threshold': '2,000'},
    {'name': 'Elite', 'icon': 'fa-medal', 'icon_color': 'text-cyan-400', 'bg_class': 'bg-cyan-500/10', 'threshold': '500'},
    {'name': 'Challenger', 'icon': 'fa-shield-alt', 'icon_color': 'text-orange-400', 'bg_class': 'bg-orange-500/10', 'threshold': '100'},
    {'name': 'Rookie', 'icon': 'fa-seedling', 'icon_color': 'text-slate-400', 'bg_class': 'bg-slate-500/10', 'threshold': '0'},
]


def _get_game_configs_with_colors(user=None):
    """Get all active GameRankingConfigs enriched with game color and icon info.

    Smart sorting:
    - Logged-in users with teams: their games first (primary team first)
    - Guests / users without teams: trending order (VAL, EFB, PUBG, FF, ...)
    Only returns configs whose game_id also appears in active Game entries OR
    the config itself is active (fallback for ranking-only games).
    """
    configs = list(GameRankingConfig.objects.filter(is_active=True).order_by('game_name'))

    # Build lookup from Game model (multiple keys per game for fuzzy matching)
    game_meta = {}
    try:
        for game in Game.objects.filter(is_active=True):
            icon_url = game.icon.url if game.icon else None
            logo_url = game.logo.url if game.logo else None
            meta = {
                'color': game.primary_color or '#64748b',
                'icon_url': icon_url or logo_url,   # fallback icon→logo
                'logo_url': logo_url,
                'display_name': game.display_name or game.name,
            }
            # Index by every plausible key
            for key in filter(None, [
                game.short_code.upper() if game.short_code else None,
                game.slug.upper() if game.slug else None,
                game.name.upper() if game.name else None,
            ]):
                game_meta[key] = meta
    except Exception:
        pass

    for config in configs:
        cid = config.game_id.upper()
        meta = game_meta.get(cid)
        # Secondary: try game_name as lookup key
        if not meta:
            meta = game_meta.get(config.game_name.upper())
        # Tertiary: prefix match (e.g. "PUBG" matches "PUBG MOBILE", "COD" matches "CODM")
        if not meta:
            for key, m in game_meta.items():
                if key.startswith(cid) or cid.startswith(key):
                    meta = m
                    break
        config.color = meta.get('color', '#64748b') if meta else '#64748b'
        config.icon_url = meta.get('icon_url') if meta else None
        config.logo_url = meta.get('logo_url') if meta else None
        config.display_name = meta.get('display_name', config.game_name) if meta else config.game_name

    # ── Smart sorting ──
    # Determine user's game priorities
    user_game_ids = []
    if user and user.is_authenticated:
        try:
            highlights = CompetitionService.get_user_team_highlights(user.id)
            if highlights and highlights.get('teams'):
                seen = set()
                for t in highlights['teams']:
                    # team dicts may have game_id
                    gid = t.get('game_id')
                    if gid and gid not in seen:
                        user_game_ids.append(gid)
                        seen.add(gid)
        except Exception:
            pass

    # Trending order fallback
    TRENDING_ORDER = ['VAL', 'EFB', 'PUBG', 'FF', 'CS2', 'DOTA2', 'LOL',
                      'APEX', 'COD', 'FORT', 'OW2', 'R6', 'RL']

    def sort_key(cfg):
        cid = cfg.game_id
        if cid in user_game_ids:
            return (0, user_game_ids.index(cid))
        if cid in TRENDING_ORDER:
            return (1, TRENDING_ORDER.index(cid))
        return (2, cfg.game_name)

    configs.sort(key=sort_key)
    return configs


PAGE_SIZE = 50


def _entries_to_json(entries):
    """Serialize RankingEntry list to JSON-safe dicts for AJAX load-more."""
    return [
        {
            'rank': e.rank,
            'team_name': e.team_name,
            'team_slug': e.team_slug,
            'team_url': e.team_url,
            'team_tag': e.team_tag or '',
            'team_logo_url': e.team_logo_url or '',
            'team_banner_url': e.team_banner_url or '',
            'organization_name': e.organization_name or '',
            'is_independent': e.is_independent,
            'score': e.score,
            'tier': e.tier,
            'activity_score': e.activity_score,
            'game_name': e.game_name or '',
            'roster_avatars': e.roster_avatars or [],
        }
        for e in entries
    ]


def leaderboard_global(request):
    """
    Global leaderboard showing all teams ranked by global_score.

    Phase 9: Uses CompetitionService for data retrieval.
    Phase 11: Redesigned with game selector tabs and premium theme.

    Query params:
    - tier: Filter by tier (THE_CROWN, LEGEND, MASTER, ELITE, CHALLENGER, ROOKIE)
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
    page = max(1, int(request.GET.get('page', '1') or '1'))
    offset = (page - 1) * PAGE_SIZE

    # Use service layer
    response = CompetitionService.get_global_rankings(
        tier=tier_filter if tier_filter else None,
        verified_only=verified_only,
        limit=PAGE_SIZE,
        offset=offset,
    )

    # Get user's team highlights if authenticated
    user_highlights = None
    user_teams_display = []
    if request.user.is_authenticated:
        user_highlights = CompetitionService.get_user_team_highlights(request.user.id)
        # Enrich with logo URLs for the My Teams panel
        if user_highlights and user_highlights.get('teams'):
            try:
                from apps.organizations.models import Team as OrgTeam
                _ids = [t['team_id'] for t in user_highlights['teams']]
                _logos = {t.id: t.logo.url if t.logo else None
                          for t in OrgTeam.objects.filter(id__in=_ids).only('id', 'logo')}
                for _t in user_highlights['teams']:
                    _t['logo_url'] = _logos.get(_t['team_id'])
                user_teams_display = user_highlights['teams']
            except Exception:
                pass

    # Compute max score for score bar width
    max_score = max((e.score for e in response.entries), default=1) or 1

    # Game configs for the game selector tabs
    game_configs = _get_game_configs_with_colors(user=request.user)

    # AJAX load-more: return JSON
    if request.GET.get('format') == 'json' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'entries': _entries_to_json(response.entries),
            'has_next_page': (offset + PAGE_SIZE) < response.total_count,
            'total_count': response.total_count,
            'page': page,
        })

    context = {
        'rankings': response,
        'entries': response.entries,
        'total_count': response.total_count,
        'tier_filter': tier_filter,
        'verified_only': verified_only,
        'available_tiers': ['THE_CROWN', 'LEGEND', 'MASTER', 'ELITE', 'CHALLENGER', 'ROOKIE'],
        'is_global': True,
        'user_highlights': user_highlights,
        'user_teams_display': user_teams_display,
        'query_count': response.query_count,
        'game_configs': game_configs,
        'max_score': max_score,
        'selected_game': None,
        'selected_game_name': None,
        'tier_details': TIER_DETAILS,
        'current_page': page,
        'has_next_page': (offset + PAGE_SIZE) < response.total_count,
        'has_prev_page': page > 1,
        'page_size': PAGE_SIZE,
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
    page = max(1, int(request.GET.get('page', '1') or '1'))
    offset = (page - 1) * PAGE_SIZE

    # Use service layer
    response = CompetitionService.get_game_rankings(
        game_id=game_id,
        tier=tier_filter if tier_filter else None,
        verified_only=verified_only,
        limit=PAGE_SIZE,
        offset=offset,
    )

    # Get user's team highlights if authenticated
    user_highlights = None
    user_teams_display = []
    if request.user.is_authenticated:
        user_highlights = CompetitionService.get_user_team_highlights(request.user.id)
        if user_highlights and user_highlights.get('teams'):
            try:
                from apps.organizations.models import Team as OrgTeam
                _ids = [t['team_id'] for t in user_highlights['teams']]
                _logos = {t.id: t.logo.url if t.logo else None
                          for t in OrgTeam.objects.filter(id__in=_ids).only('id', 'logo')}
                for _t in user_highlights['teams']:
                    _t['logo_url'] = _logos.get(_t['team_id'])
                user_teams_display = user_highlights['teams']
            except Exception:
                pass

    # Compute max score for score bar width
    max_score = max((e.score for e in response.entries), default=1) or 1

    # Game configs for the game selector tabs
    game_configs = _get_game_configs_with_colors(user=request.user)

    # AJAX load-more: return JSON
    if request.GET.get('format') == 'json' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'entries': _entries_to_json(response.entries),
            'has_next_page': (offset + PAGE_SIZE) < response.total_count,
            'total_count': response.total_count,
            'page': page,
        })

    context = {
        'rankings': response,
        'entries': response.entries,
        'total_count': response.total_count,
        'game_config': game_config,
        'game_id': game_id,
        'tier_filter': tier_filter,
        'verified_only': verified_only,
        'available_tiers': ['THE_CROWN', 'LEGEND', 'MASTER', 'ELITE', 'CHALLENGER', 'ROOKIE'],
        'is_global': False,
        'user_highlights': user_highlights,
        'user_teams_display': user_teams_display,
        'query_count': response.query_count,
        'game_configs': game_configs,
        'max_score': max_score,
        'selected_game': game_id,
        'selected_game_name': game_config.game_name,
        'tier_details': TIER_DETAILS,
        'current_page': page,
        'has_next_page': (offset + PAGE_SIZE) < response.total_count,
        'has_prev_page': page > 1,
        'page_size': PAGE_SIZE,
    }

    return render(request, 'competition/leaderboards/leaderboard_global.html', context)
