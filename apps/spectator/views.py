"""
Spectator Views

Phase G: Spectator Live Views

Read-only view layer for tournament spectators. Orchestrates existing services:
- Leaderboards (Phase E)
- Matches (Phase 4)
- Real-time updates (Module 2.6)

All views follow IDs-only discipline (no PII in responses).
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.db.models import Q

from apps.tournaments.models import Tournament, Match, Registration
from apps.leaderboards.services import LeaderboardService


@require_http_methods(["GET"])
def tournament_list_view(request):
    """
    Tournament list page - spectator entry point.
    
    GET /spectator/
    
    Displays all active tournaments for spectators to choose from.
    
    Context:
        tournaments (QuerySet): Active tournaments (registration_open, ongoing, in_progress)
    """
    # Get active tournaments
    tournaments = Tournament.objects.filter(
        stage__in=['REGISTRATION', 'ONGOING', 'IN_PROGRESS']
    ).select_related('game').order_by('-start_time')
    
    # Get participant counts
    tournament_data = []
    for tournament in tournaments:
        participant_count = Registration.objects.filter(
            tournament=tournament,
            status='confirmed'
        ).count()
        
        tournament_data.append({
            'tournament': tournament,
            'participant_count': participant_count,
        })
    
    context = {
        'tournament_data': tournament_data,
    }
    
    return render(request, 'spectator/tournament_list.html', context)


@require_http_methods(["GET"])
def tournament_spectator_view(request, tournament_id):
    """
    Tournament spectator page.
    
    GET /spectator/tournaments/<int:tournament_id>/
    
    Displays:
    - Tournament metadata (IDs only)
    - Current leaderboard (top 20 entries)
    - Live/upcoming matches
    - WebSocket connection info for real-time updates
    
    Context:
        tournament_id (int): Tournament ID
        game_code (str): Game identifier
        stage (str): Tournament stage (REGISTRATION, ONGOING, COMPLETED)
        status (str): Tournament status
        start_time (datetime): Scheduled start time
        end_time (datetime): Scheduled end time
        leaderboard_entries (list): List of dicts with rank, participant_id, team_id, points
        matches (list): List of dicts with match_id, round, status, scheduled_time
        ws_tournament_url (str): WebSocket URL for tournament updates
    
    IDs-Only Discipline:
        - Returns only IDs (no display names, usernames, emails)
        - Client must resolve names via /api/profiles/, /api/teams/, etc.
    """
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Get leaderboard data (Phase E service)
    leaderboard_service = LeaderboardService()
    leaderboard_entries = leaderboard_service.get_leaderboard(
        leaderboard_type='tournament',
        tournament_id=tournament_id,
        limit=20  # Top 20 for spectator view
    )
    
    # Get live/upcoming matches
    matches = Match.objects.filter(
        tournament_id=tournament_id
    ).filter(
        Q(status='scheduled') | Q(status='in_progress')
    ).order_by('scheduled_time', 'round').values(
        'id',
        'round',
        'bracket_position',
        'status',
        'scheduled_time',
        'participant1_id',
        'participant2_id',
        'participant1_score',
        'participant2_score'
    )[:10]  # Limit to 10 matches
    
    # Build WebSocket URL for tournament channel
    ws_scheme = 'wss' if request.is_secure() else 'ws'
    ws_host = request.get_host()
    ws_tournament_url = f"{ws_scheme}://{ws_host}/ws/tournament/{tournament_id}/"
    
    context = {
        'tournament_id': tournament.id,
        'game_code': tournament.game,
        'stage': tournament.stage,
        'status': tournament.status,
        'start_time': tournament.start_time,
        'end_time': tournament.end_time,
        'leaderboard_entries': leaderboard_entries,
        'matches': list(matches),
        'ws_tournament_url': ws_tournament_url,
    }
    
    return render(request, 'spectator/tournament_detail.html', context)


@require_http_methods(["GET"])
def tournament_leaderboard_fragment(request, tournament_id):
    """
    Leaderboard fragment for htmx partial refresh.
    
    GET /spectator/tournaments/<int:tournament_id>/leaderboard/fragment/
    
    Returns rendered partial template with latest leaderboard data.
    Used by htmx for auto-refresh (every 10s).
    
    Response:
        Rendered HTML fragment (templates/spectator/_leaderboard_table.html)
    """
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Get fresh leaderboard data
    leaderboard_service = LeaderboardService()
    leaderboard_entries = leaderboard_service.get_leaderboard(
        leaderboard_type='tournament',
        tournament_id=tournament_id,
        limit=20
    )
    
    context = {
        'tournament_id': tournament.id,
        'leaderboard_entries': leaderboard_entries,
    }
    
    return render(request, 'spectator/_leaderboard_table.html', context)


@require_http_methods(["GET"])
def tournament_matches_fragment(request, tournament_id):
    """
    Matches fragment for htmx partial refresh.
    
    GET /spectator/tournaments/<int:tournament_id>/matches/fragment/
    
    Returns rendered partial template with latest match list.
    Used by htmx for auto-refresh (every 15s).
    
    Response:
        Rendered HTML fragment (templates/spectator/_match_list.html)
    """
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Get fresh match data
    matches = Match.objects.filter(
        tournament_id=tournament_id
    ).filter(
        Q(status='scheduled') | Q(status='in_progress')
    ).order_by('scheduled_time', 'round').values(
        'id',
        'round',
        'bracket_position',
        'status',
        'scheduled_time',
        'participant1_id',
        'participant2_id',
        'participant1_score',
        'participant2_score'
    )[:10]
    
    context = {
        'tournament_id': tournament.id,
        'matches': list(matches),
    }
    
    return render(request, 'spectator/_match_list.html', context)


@require_http_methods(["GET"])
def match_spectator_view(request, match_id):
    """
    Match spectator page.
    
    GET /spectator/matches/<int:match_id>/
    
    Displays:
    - Match metadata (IDs only)
    - Live scoreboard
    - Participant/team IDs
    - WebSocket connection info for real-time score updates
    
    Context:
        match_id (int): Match ID
        tournament_id (int): Parent tournament ID
        round (int): Bracket round number
        status (str): Match status (scheduled, in_progress, completed)
        scheduled_time (datetime): Match start time
        participant1_id (int): First participant/team ID
        participant2_id (int): Second participant/team ID
        participant1_score (int): First participant score
        participant2_score (int): Second participant score
        ws_match_url (str): WebSocket URL for match updates
    
    IDs-Only Discipline:
        - Returns only IDs (no participant names)
        - Client must resolve names via external APIs
    """
    match = get_object_or_404(
        Match.objects.select_related('tournament'),
        id=match_id
    )
    
    # Build WebSocket URL for match channel
    ws_scheme = 'wss' if request.is_secure() else 'ws'
    ws_host = request.get_host()
    ws_match_url = f"{ws_scheme}://{ws_host}/ws/tournament/{match.tournament_id}/"
    
    context = {
        'match_id': match.id,
        'tournament_id': match.tournament_id,
        'round': match.round,
        'bracket_position': match.bracket_position,
        'status': match.status,
        'scheduled_time': match.scheduled_time,
        'participant1_id': match.participant1_id,
        'participant2_id': match.participant2_id,
        'participant1_score': match.participant1_score or 0,
        'participant2_score': match.participant2_score or 0,
        'ws_match_url': ws_match_url,
    }
    
    return render(request, 'spectator/match_detail.html', context)


@require_http_methods(["GET"])
def match_scoreboard_fragment(request, match_id):
    """
    Scoreboard fragment for htmx partial refresh.
    
    GET /spectator/matches/<int:match_id>/scoreboard/fragment/
    
    Returns rendered partial template with latest scoreboard.
    Used by htmx as fallback when WebSocket unavailable.
    
    Response:
        Rendered HTML fragment (templates/spectator/_scoreboard.html)
    """
    match = get_object_or_404(Match, id=match_id)
    
    context = {
        'match_id': match.id,
        'tournament_id': match.tournament_id,
        'status': match.status,
        'participant1_id': match.participant1_id,
        'participant2_id': match.participant2_id,
        'participant1_score': match.participant1_score or 0,
        'participant2_score': match.participant2_score or 0,
    }
    
    return render(request, 'spectator/_scoreboard.html', context)
