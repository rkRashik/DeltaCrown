"""
Tournament Dashboard API Endpoints
=====================================
RESTful API endpoints for the participant dashboard.

Endpoints:
- GET /api/tournaments/{slug}/bracket/ - Bracket structure and match tree
- GET /api/tournaments/{slug}/matches/ - Match list with optional team filter
- GET /api/tournaments/{slug}/news/ - Tournament news and announcements
- GET /api/tournaments/{slug}/statistics/ - Team statistics and leaderboard
"""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum, Case, When, IntegerField, F
from django.utils import timezone

from apps.tournaments.models import Tournament, Registration, Match
from apps.teams.models import Team


@login_required
def bracket_api(request, slug):
    """
    GET /api/tournaments/{slug}/bracket/
    
    Returns bracket structure with match tree for knockout/elimination tournaments.
    
    Response:
    {
        "bracket_type": "single_elimination|double_elimination|swiss",
        "rounds": [
            {
                "round_number": 1,
                "round_name": "Quarter Finals",
                "matches": [
                    {
                        "match_id": 123,
                        "team1": {"id": 1, "name": "Team A", "score": 2},
                        "team2": {"id": 2, "name": "Team B", "score": 1},
                        "winner": 1,
                        "status": "completed",
                        "scheduled_time": "2025-01-15T18:00:00Z"
                    }
                ]
            }
        ]
    }
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Check if user is registered
    try:
        registration = Registration.objects.get(
            tournament=tournament,
            team__players=request.user
        )
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Not registered for this tournament'}, status=403)
    
    # Get all matches for this tournament
    matches = Match.objects.filter(
        tournament=tournament
    ).select_related('team1', 'team2').order_by('round', 'scheduled_time')
    
    # Build bracket structure
    bracket = {
        'bracket_type': tournament.format if hasattr(tournament, 'format') else 'single_elimination',
        'rounds': []
    }
    
    # Group matches by round
    rounds_dict = {}
    for match in matches:
        round_num = match.round if hasattr(match, 'round') else 1
        
        if round_num not in rounds_dict:
            rounds_dict[round_num] = {
                'round_number': round_num,
                'round_name': _get_round_name(round_num, matches.count()),
                'matches': []
            }
        
        match_data = {
            'match_id': match.id,
            'team1': {
                'id': match.team1.id if match.team1 else None,
                'name': match.team1.name if match.team1 else 'TBD',
                'score': match.team1_score or 0
            } if match.team1 else None,
            'team2': {
                'id': match.team2.id if match.team2 else None,
                'name': match.team2.name if match.team2 else 'TBD',
                'score': match.team2_score or 0
            } if match.team2 else None,
            'winner': match.winner.id if match.winner else None,
            'status': match.status,
            'scheduled_time': match.scheduled_time.isoformat() if match.scheduled_time else None
        }
        
        rounds_dict[round_num]['matches'].append(match_data)
    
    # Convert dict to sorted list
    bracket['rounds'] = sorted(rounds_dict.values(), key=lambda x: x['round_number'])
    
    return JsonResponse(bracket)


@login_required
def matches_api(request, slug):
    """
    GET /api/tournaments/{slug}/matches/?team_id={team_id}&status={status}
    
    Returns list of matches with optional filters.
    
    Query Parameters:
    - team_id: Filter by team ID (shows matches involving this team)
    - status: Filter by match status (upcoming, live, completed)
    
    Response:
    {
        "matches": [
            {
                "id": 123,
                "team1": {"id": 1, "name": "Team A", "logo": "..."},
                "team2": {"id": 2, "name": "Team B", "logo": "..."},
                "team1_score": 2,
                "team2_score": 1,
                "status": "completed",
                "scheduled_time": "2025-01-15T18:00:00Z",
                "round": 1,
                "is_my_match": true
            }
        ],
        "total": 10
    }
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Check if user is registered
    try:
        registration = Registration.objects.get(
            tournament=tournament,
            team__players=request.user
        )
        user_team = registration.team
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Not registered for this tournament'}, status=403)
    
    # Base queryset
    matches = Match.objects.filter(
        tournament=tournament
    ).select_related('team1', 'team2', 'winner')
    
    # Apply filters
    team_id = request.GET.get('team_id')
    if team_id:
        matches = matches.filter(Q(team1_id=team_id) | Q(team2_id=team_id))
    
    status_filter = request.GET.get('status')
    if status_filter:
        matches = matches.filter(status=status_filter)
    
    # Order by scheduled time
    matches = matches.order_by('-scheduled_time')
    
    # Build response
    matches_data = []
    for match in matches:
        is_my_match = (match.team1_id == user_team.id) or (match.team2_id == user_team.id)
        
        match_data = {
            'id': match.id,
            'team1': {
                'id': match.team1.id if match.team1 else None,
                'name': match.team1.name if match.team1 else 'TBD',
                'logo': match.team1.logo.url if match.team1 and match.team1.logo else None
            } if match.team1 else None,
            'team2': {
                'id': match.team2.id if match.team2 else None,
                'name': match.team2.name if match.team2 else 'TBD',
                'logo': match.team2.logo.url if match.team2 and match.team2.logo else None
            } if match.team2 else None,
            'team1_score': match.team1_score or 0,
            'team2_score': match.team2_score or 0,
            'status': match.status,
            'scheduled_time': match.scheduled_time.isoformat() if match.scheduled_time else None,
            'round': match.round if hasattr(match, 'round') else 1,
            'is_my_match': is_my_match
        }
        
        matches_data.append(match_data)
    
    return JsonResponse({
        'matches': matches_data,
        'total': len(matches_data)
    })


@login_required
def news_api(request, slug):
    """
    GET /api/tournaments/{slug}/news/?limit={limit}
    
    Returns tournament news and announcements.
    
    Query Parameters:
    - limit: Maximum number of news items to return (default: 10)
    
    Response:
    {
        "news": [
            {
                "id": 1,
                "title": "Tournament Starting Soon!",
                "content": "...",
                "created_at": "2025-01-15T12:00:00Z",
                "is_important": true
            }
        ],
        "total": 5
    }
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Check if user is registered
    try:
        Registration.objects.get(
            tournament=tournament,
            team__players=request.user
        )
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Not registered for this tournament'}, status=403)
    
    # Get news items
    limit = int(request.GET.get('limit', 10))
    
    # TODO: Implement TournamentNews model in future
    # For now, return empty news list
    news_data = []
    
    # Future implementation:
    # news_items = TournamentNews.objects.filter(
    #     tournament=tournament,
    #     is_published=True
    # ).order_by('-created_at')[:limit]
    # 
    # news_data = [
    #     {
    #         'id': item.id,
    #         'title': item.title,
    #         'content': item.content,
    #         'created_at': item.created_at.isoformat(),
    #         'is_important': getattr(item, 'is_important', False)
    #     }
    #     for item in news_items
    # ]
    
    return JsonResponse({
        'news': news_data,
        'total': len(news_data)
    })


@login_required
def statistics_api(request, slug):
    """
    GET /api/tournaments/{slug}/statistics/
    
    Returns team statistics and leaderboard.
    
    Response:
    {
        "my_team": {
            "rank": 3,
            "wins": 5,
            "losses": 2,
            "points": 15,
            "win_rate": 71.4
        },
        "leaderboard": [
            {
                "rank": 1,
                "team": {"id": 1, "name": "Team A"},
                "wins": 7,
                "losses": 0,
                "points": 21,
                "win_rate": 100.0
            }
        ]
    }
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Check if user is registered
    try:
        registration = Registration.objects.get(
            tournament=tournament,
            team__players=request.user
        )
        user_team = registration.team
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Not registered for this tournament'}, status=403)
    
    # Get all registrations with match statistics
    registrations = Registration.objects.filter(
        tournament=tournament,
        status='approved'
    ).select_related('team').annotate(
        total_matches=Count('team__matches_as_team1', distinct=True) + Count('team__matches_as_team2', distinct=True),
        wins=Count(
            Case(
                When(team__matches_as_team1__winner=F('team'), then=1),
                When(team__matches_as_team2__winner=F('team'), then=1),
                output_field=IntegerField()
            )
        ),
        losses=Count(
            Case(
                When(
                    Q(team__matches_as_team1__status='completed') & ~Q(team__matches_as_team1__winner=F('team')),
                    then=1
                ),
                When(
                    Q(team__matches_as_team2__status='completed') & ~Q(team__matches_as_team2__winner=F('team')),
                    then=1
                ),
                output_field=IntegerField()
            )
        )
    )
    
    # Calculate points and build leaderboard
    leaderboard = []
    my_team_stats = None
    
    for reg in registrations:
        points = reg.wins * 3  # 3 points per win
        total_games = reg.total_matches
        win_rate = (reg.wins / total_games * 100) if total_games > 0 else 0
        
        team_stats = {
            'team': {
                'id': reg.team.id,
                'name': reg.team.name
            },
            'wins': reg.wins,
            'losses': reg.losses,
            'points': points,
            'win_rate': round(win_rate, 1)
        }
        
        leaderboard.append(team_stats)
        
        if reg.team.id == user_team.id:
            my_team_stats = team_stats.copy()
    
    # Sort by points (wins), then by win rate
    leaderboard.sort(key=lambda x: (-x['points'], -x['win_rate']))
    
    # Add ranks
    for i, team in enumerate(leaderboard, 1):
        team['rank'] = i
        if my_team_stats and team['team']['id'] == user_team.id:
            my_team_stats['rank'] = i
    
    return JsonResponse({
        'my_team': my_team_stats,
        'leaderboard': leaderboard
    })


def _get_round_name(round_num, total_matches):
    """Helper to generate round names (Finals, Semi-Finals, etc.)"""
    round_names = {
        1: 'Finals',
        2: 'Semi-Finals',
        3: 'Quarter-Finals',
        4: 'Round of 16',
        5: 'Round of 32'
    }
    
    # For later rounds, just use "Round X"
    if round_num > 5:
        return f'Round {round_num}'
    
    return round_names.get(round_num, f'Round {round_num}')
