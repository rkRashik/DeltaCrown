"""
Team Directory View

Provides a browseable, filterable listing of public teams.
Supports ?filter=recruiting to show only recruiting teams.

Phase 11: Premium dark theme team directory.
"""
from django.db.models import Count, Q
from django.shortcuts import render
from django.core.cache import cache

from apps.organizations.models.team import Team
from apps.organizations.choices import TeamStatus
from apps.organizations.services.recruitment_discovery import (
    active_recruitment_positions_prefetch,
    build_recruitment_summary,
    get_available_player_summaries,
)
from apps.games.models import Game
from apps.common.seo import breadcrumb_schema, build_seo


def team_directory(request):
    """
    Public team directory with optional filter.

    Query params:
    - filter: 'recruiting' | 'all' (default: 'all')
    - game: game slug to filter by game
    - region: region string to filter
    - q: search query (team name or tag)
    - sort: 'newest' | 'name' | 'members' (default: 'newest')
    """
    active_filter = request.GET.get('filter', 'all')
    game_filter = request.GET.get('game', '')
    region_filter = request.GET.get('region', '')
    platform_filter = request.GET.get('platform', '')
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'newest')
    is_recruiting_filter = active_filter == 'recruiting'

    # Base queryset: active, public teams only
    teams = (
        Team.objects
        .filter(status=TeamStatus.ACTIVE, visibility='PUBLIC')
        .select_related('organization')
        .annotate(member_count=Count('vnext_memberships', distinct=True))
    )

    # Apply filters
    if is_recruiting_filter:
        teams = teams.filter(is_recruiting=True).prefetch_related(
            active_recruitment_positions_prefetch()
        )

    if game_filter:
        try:
            game = Game.objects.get(slug=game_filter, is_active=True)
            teams = teams.filter(game_id=game.id)
        except Game.DoesNotExist:
            pass

    if region_filter:
        teams = teams.filter(region__icontains=region_filter)

    if platform_filter:
        if is_recruiting_filter:
            teams = teams.filter(
                Q(platform__icontains=platform_filter) |
                Q(recruitment_positions__platform__icontains=platform_filter)
            ).distinct()
        else:
            teams = teams.filter(platform__icontains=platform_filter)

    if search_query:
        teams = teams.filter(
            Q(name__icontains=search_query) |
            Q(tag__icontains=search_query)
        )

    # Apply sort
    if sort_by == 'name':
        teams = teams.order_by('name')
    elif sort_by == 'members':
        teams = teams.order_by('-member_count', '-created_at')
    else:  # newest (default)
        teams = teams.order_by('-created_at')

    # Limit to 100
    teams = teams[:100]

    # Public sidebar/header data — cache for 5 min to drop ~5 queries per page paint.
    def _directory_facets():
        total = Team.objects.filter(status=TeamStatus.ACTIVE, visibility='PUBLIC').count()
        recruiting = Team.objects.filter(
            status=TeamStatus.ACTIVE, visibility='PUBLIC', is_recruiting=True
        ).count()
        regions_qs = list(
            Team.objects.filter(status=TeamStatus.ACTIVE, visibility='PUBLIC')
            .values_list('region', flat=True).distinct().order_by('region')
        )
        platforms_qs = list(
            Team.objects.filter(status=TeamStatus.ACTIVE, visibility='PUBLIC')
            .values_list('platform', flat=True).distinct().order_by('platform')
        )
        return {
            'total_teams': total,
            'recruiting_count': recruiting,
            'regions': [r for r in regions_qs if r],
            'platforms': [p for p in platforms_qs if p],
        }
    facets = cache.get_or_set('orgs:team_directory:facets:v2', _directory_facets, 300)
    total_teams = facets['total_teams']
    recruiting_count = facets['recruiting_count']
    regions = facets['regions']
    platforms = facets['platforms']

    # Single fetch of active games — feeds both the filter pills and the
    # per-team game_obj lookup (was 2 duplicated DB hits).
    active_games = list(Game.objects.filter(is_active=True).order_by('display_name'))
    game_map = {game.id: game for game in active_games}

    # Annotate teams with game info via wrapper dicts
    team_list = []
    open_role_count = 0
    for team in teams:
        recruitment_summary = (
            build_recruitment_summary(team)
            if is_recruiting_filter and team.is_recruiting
            else None
        )
        if recruitment_summary:
            open_role_count += recruitment_summary.get('open_role_count', 0)
        team_list.append({
            'team': team,
            'game_obj': game_map.get(team.game_id),
            'recruitment_summary': recruitment_summary,
        })

    available_players = get_available_player_summaries(limit=8) if is_recruiting_filter else []

    context = {
        'teams': team_list,
        'total_teams': total_teams,
        'recruiting_count': recruiting_count,
        'recruiting_result_count': len(team_list),
        'open_role_count': open_role_count,
        'is_recruiting_filter': is_recruiting_filter,
        'active_filter': active_filter,
        'game_filter': game_filter,
        'region_filter': region_filter,
        'platform_filter': platform_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'active_games': active_games,
        'regions': regions,
        'platforms': platforms,
        'available_players': available_players,
        'lft_teasers': available_players,
        'seo': build_seo(
            title='Find Team - Scouting Grounds | DeltaCrown' if is_recruiting_filter else 'Esports Team Directory | DeltaCrown',
            description=(
                'Find DeltaCrown teams recruiting now. Filter by game, region, platform, and apply from each team page.'
                if is_recruiting_filter
                else 'Browse public DeltaCrown esports teams by game, region, recruiting status, and organization across Bangladesh and South Asia.'
            ),
            path='/teams/directory/',
            noindex=bool(search_query or active_filter != 'all' or sort_by != 'newest' or platform_filter),
            schema=breadcrumb_schema([('Home', '/'), ('Teams', '/teams/'), ('Directory', '/teams/directory/')]),
        ),
    }

    return render(request, 'organizations/teams/team_directory.html', context)
