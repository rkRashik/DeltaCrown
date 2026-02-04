"""
Team Rankings Views
===================
Leaderboards for game-specific and global team rankings.
"""

from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from apps.teams.models.ranking import TeamGameRanking
from apps.teams.constants import RankingConstants
from apps.games.models import Game


def game_leaderboard_view(request, game_slug):
    """
    Per-game leaderboard view.
    
    Shows teams ranked by ELO for a specific game with division badges.
    
    Args:
        request: HTTP request
        game_slug: Game identifier (e.g., 'valorant', 'cs2')
    """
    game = get_object_or_404(Game, slug=game_slug, is_active=True)
    
    # Get rankings for this game
    rankings = TeamGameRanking.objects.filter(
        game=game_slug
    ).select_related('team').order_by('-elo_rating')
    
    # Pagination
    paginator = Paginator(rankings, 50)  # 50 teams per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Add rank numbers
    start_rank = (page_obj.number - 1) * paginator.per_page + 1
    for idx, ranking in enumerate(page_obj.object_list):
        ranking.rank = start_rank + idx
    
    context = {
        'game': game,
        'page_obj': page_obj,
        'rankings': page_obj.object_list,
        'total_teams': paginator.count,
        'page_title': f'{game.display_name} Leaderboard',
    }
    
    return render(request, 'teams/_legacy/rankings/game_leaderboard.html', context)


def global_leaderboard_view(request):
    """
    Global cross-game leaderboard.
    
    Shows top teams across all games ranked by global ELO.
    """
    # Get unique teams with their best global ELO
    # DISTINCT ON requires matching ORDER BY - so fetch all then sort in Python
    rankings = TeamGameRanking.objects.select_related(
        'team'
    ).order_by('team_id', '-global_elo').distinct('team_id')
    
    # Sort by global ELO descending and limit to top 100
    rankings = sorted(rankings, key=lambda r: r.global_elo, reverse=True)[:100]
    
    # Pagination
    paginator = Paginator(rankings, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Add rank numbers
    start_rank = (page_obj.number - 1) * paginator.per_page + 1
    for idx, ranking in enumerate(page_obj.object_list):
        ranking.rank = start_rank + idx
    
    # Get all active games for filtering
    games = Game.objects.filter(is_active=True).order_by('display_name')
    
    context = {
        'page_obj': page_obj,
        'rankings': page_obj.object_list,
        'total_teams': paginator.count,
        'page_title': 'Global Team Rankings',
        'games': games,
    }
    
    return render(request, 'teams/_legacy/rankings/global_leaderboard.html', context)


def get_division_info(elo_rating):
    """
    Helper to get division info from ELO rating.
    
    Returns dict with division name, color, and icon.
    """
    thresholds = RankingConstants.DIVISION_THRESHOLDS
    
    for division, min_elo in sorted(thresholds.items(), key=lambda x: x[1], reverse=True):
        if elo_rating >= min_elo:
            return {
                'name': division.title(),
                'color': _get_division_color(division),
                'icon': _get_division_icon(division),
            }
    
    return {
        'name': 'Bronze',
        'color': '#cd7f32',
        'icon': '🥉',
    }


def _get_division_color(division):
    """Get hex color for division badge."""
    colors = {
        'BRONZE': '#cd7f32',
        'SILVER': '#c0c0c0',
        'GOLD': '#ffd700',
        'PLATINUM': '#e5e4e2',
        'DIAMOND': '#b9f2ff',
        'MASTER': '#9966cc',
        'GRANDMASTER': '#ff4500',
    }
    return colors.get(division, '#cd7f32')


def _get_division_icon(division):
    """Get emoji icon for division."""
    icons = {
        'BRONZE': '🥉',
        'SILVER': '🥈',
        'GOLD': '🥇',
        'PLATINUM': '💎',
        'DIAMOND': '💠',
        'MASTER': '👑',
        'GRANDMASTER': '⭐',
    }
    return icons.get(division, '🥉')
