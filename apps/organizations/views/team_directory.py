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
from apps.games.models import Game


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
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'newest')

    # Base queryset: active, public teams only
    teams = (
        Team.objects
        .filter(status=TeamStatus.ACTIVE, visibility='PUBLIC')
        .select_related('organization')
        .annotate(member_count=Count('vnext_memberships'))
    )

    # Apply filters
    if active_filter == 'recruiting':
        teams = teams.filter(is_recruiting=True)

    if game_filter:
        try:
            game = Game.objects.get(slug=game_filter, is_active=True)
            teams = teams.filter(game_id=game.id)
        except Game.DoesNotExist:
            pass

    if region_filter:
        teams = teams.filter(region__icontains=region_filter)

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
        return {
            'total_teams': total,
            'recruiting_count': recruiting,
            'regions': [r for r in regions_qs if r],
        }
    facets = cache.get_or_set('orgs:team_directory:facets:v1', _directory_facets, 300)
    total_teams = facets['total_teams']
    recruiting_count = facets['recruiting_count']
    regions = facets['regions']

    # Single fetch of active games — feeds both the filter pills and the
    # per-team game_obj lookup (was 2 duplicated DB hits).
    active_games = list(Game.objects.filter(is_active=True).order_by('display_name'))
    game_map = {game.id: game for game in active_games}

    # Annotate teams with game info via wrapper dicts
    team_list = []
    for team in teams:
        team_list.append({
            'team': team,
            'game_obj': game_map.get(team.game_id),
        })

    context = {
        'teams': team_list,
        'total_teams': total_teams,
        'recruiting_count': recruiting_count,
        'active_filter': active_filter,
        'game_filter': game_filter,
        'region_filter': region_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'active_games': active_games,
        'regions': regions,
    }

    return render(request, 'organizations/teams/team_directory.html', context)
