"""
Team Directory View

Provides a browseable, filterable listing of public teams.
Supports ?filter=recruiting to show only recruiting teams.

Phase 11: Premium dark theme team directory.
"""
from django.db.models import Count, Q
from django.shortcuts import render

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

    # Get counts for header
    total_teams = Team.objects.filter(
        status=TeamStatus.ACTIVE, visibility='PUBLIC'
    ).count()
    recruiting_count = Team.objects.filter(
        status=TeamStatus.ACTIVE, visibility='PUBLIC', is_recruiting=True
    ).count()

    # Active games for filter pills
    active_games = Game.objects.filter(is_active=True).order_by('display_name')

    # Unique regions for filter
    regions = (
        Team.objects
        .filter(status=TeamStatus.ACTIVE, visibility='PUBLIC')
        .values_list('region', flat=True)
        .distinct()
        .order_by('region')
    )
    regions = [r for r in regions if r]

    # Build game lookup for template (game_id -> Game obj)
    game_map = {}
    try:
        for game in Game.objects.filter(is_active=True):
            game_map[game.id] = game
    except Exception:
        pass

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
