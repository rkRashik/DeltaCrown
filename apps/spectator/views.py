"""
Spectator Views

Phase G: Spectator Live Views

Read-only view layer for tournament spectators. Orchestrates existing services:
- Leaderboards (Phase E)
- Matches (Phase 4)
- Real-time updates (Module 2.6)

All views follow IDs-only discipline (no PII in responses).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.db.models import Count, Q

from apps.tournaments.models import Tournament, Match, Registration
from apps.leaderboards.services import LeaderboardService


def _enrich_leaderboard_entries(entries):
    """Resolve team/player names for leaderboard entries in-place."""
    if not entries:
        return
    team_ids = [e.get('team_id') or e.get('team_id') for e in entries if e.get('team_id')]
    user_ids = [e.get('participant_id') for e in entries if e.get('participant_id') and not e.get('team_id')]

    team_names = {}
    if team_ids:
        try:
            from apps.organizations.models import Team as OrgTeam
            team_names = dict(OrgTeam.objects.filter(id__in=team_ids).values_list('id', 'name'))
        except Exception:
            pass

    user_names = {}
    if user_ids:
        try:
            from apps.accounts.models import User
            user_names = dict(User.objects.filter(id__in=user_ids).values_list('id', 'username'))
        except Exception:
            pass

    for entry in entries:
        if entry.get('team_id') and entry['team_id'] in team_names:
            entry['display_name'] = team_names[entry['team_id']]
        elif entry.get('participant_id') and entry['participant_id'] in user_names:
            entry['display_name'] = user_names[entry['participant_id']]
        else:
            entry.setdefault('display_name', None)


# Drafts and tournaments awaiting approval are never public; the directory only
# lists events a spectator can actually open.
_DIRECTORY_STATUSES = (Tournament.REGISTRATION_OPEN, Tournament.LIVE)
_HIDDEN_STATUSES = (Tournament.DRAFT, Tournament.PENDING_APPROVAL)


def _public_tournament_or_404(tournament_id):
    tournament = get_object_or_404(Tournament.objects.filter(is_deleted=False), id=tournament_id)
    if tournament.status in _HIDDEN_STATUSES:
        raise Http404("Tournament not found")
    return tournament


@require_http_methods(["GET"])
def tournament_list_view(request):
    """
    Tournament list page - spectator entry point.

    GET /spectator/

    Lists public tournaments that are open for registration or live. Live events
    link to the public spectate page; registration-open events link to the
    public tournament page.

    Context:
        tournament_data (list): dicts with ``tournament``, ``participant_count``
        and ``url`` (the canonical public page for that tournament)
    """
    tournaments = (
        Tournament.objects.filter(is_deleted=False, status__in=_DIRECTORY_STATUSES)
        .select_related('game')
        .annotate(
            participant_count=Count(
                'registrations',
                filter=Q(registrations__status=Registration.CONFIRMED, registrations__is_deleted=False),
            )
        )
        .order_by('-tournament_start', '-id')
    )

    tournament_data = []
    for tournament in tournaments:
        route = 'tournaments:spectate' if tournament.status == Tournament.LIVE else 'tournaments:detail'
        tournament_data.append({
            'tournament': tournament,
            'participant_count': tournament.participant_count,
            'url': reverse(route, kwargs={'slug': tournament.slug}),
        })

    return render(request, 'spectator/tournament_list.html', {'tournament_data': tournament_data})


@require_http_methods(["GET"])
def tournament_spectator_view(request, tournament_id):
    """
    Legacy spectator page: GET /spectator/tournaments/<int:tournament_id>/

    The ID-based spectator page was replaced by the public tournament pages.
    Redirects to the live/completed spectate page, or to the tournament page
    otherwise. Drafts and pending tournaments return 404.
    """
    tournament = _public_tournament_or_404(tournament_id)
    if tournament.status in (Tournament.LIVE, Tournament.COMPLETED):
        return redirect('tournaments:spectate', slug=tournament.slug)
    return redirect('tournaments:detail', slug=tournament.slug)


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
    
    # Resolve team/player names for leaderboard entries
    _enrich_leaderboard_entries(leaderboard_entries)

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
    Legacy match page: GET /spectator/matches/<int:match_id>/

    Redirects to the public match page. Matches of draft/pending tournaments
    return 404.
    """
    match = get_object_or_404(
        Match.objects.select_related('tournament'),
        id=match_id,
        is_deleted=False,
        tournament__is_deleted=False,
    )
    if match.tournament.status in _HIDDEN_STATUSES:
        raise Http404("Match not found")
    return redirect('tournaments:match_detail', slug=match.tournament.slug, match_id=match.id)


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
