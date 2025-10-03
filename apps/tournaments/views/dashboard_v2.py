"""
Tournament Dashboard View - Phase 4
Participant dashboard for registered tournament users
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Q, Count, F
from django.utils import timezone

from ..models import Tournament, Registration, Match
from apps.teams.models import Team


@login_required
def tournament_dashboard_v2(request, slug):
    """
    Dashboard for registered participants.
    Shows bracket, matches, news, calendar, and statistics.
    """
    tournament = get_object_or_404(
        Tournament.objects.select_related('settings'),
        slug=slug
    )
    
    # Check if user is registered for this tournament
    try:
        registration = Registration.objects.select_related('team').get(
            tournament=tournament,
            team__players=request.user
        )
        team = registration.team
    except Registration.DoesNotExist:
        # Not registered - redirect to detail page
        return redirect('tournaments:detail', slug=slug)
    
    # Check if user is captain
    is_captain = (team.captain == request.user if hasattr(team, 'captain') else False)
    
    # Can check-in if tournament allows and hasn't started
    can_checkin = (
        tournament.status in ['registration', 'upcoming'] and
        not getattr(registration, 'checked_in', False) and
        is_captain
    )
    
    # Get team players
    team_players = team.players.all()[:10]  # Limit to 10 players
    
    # Get quick stats
    team_matches = Match.objects.filter(
        Q(team_a=team) | Q(team_b=team),
        tournament=tournament
    )
    
    wins = team_matches.filter(winner_team=team).count()
    total_matches = team_matches.exclude(winner_team__isnull=True).count()
    losses = total_matches - wins
    
    # Calculate rank (simple: count teams with more wins)
    teams_with_more_wins = Team.objects.filter(
        registrations__tournament=tournament
    ).annotate(
        team_wins=Count(
            'matches_as_a',
            filter=Q(matches_as_a__winner_team_id=F('id'), matches_as_a__tournament=tournament)
        ) + Count(
            'matches_as_b',
            filter=Q(matches_as_b__winner_team_id=F('id'), matches_as_b__tournament=tournament)
        )
    ).filter(team_wins__gt=wins).count()
    
    rank = teams_with_more_wins + 1
    
    # Points (simple: 3 per win)
    points = wins * 3
    
    # Win rate
    win_rate = round((wins / total_matches * 100) if total_matches > 0 else 0, 1)
    
    # Average score (placeholder)
    avg_score = round((wins * 2 + losses) / max(total_matches, 1), 1)
    
    # Win streak (consecutive wins)
    win_streak = 0
    recent_matches = team_matches.order_by('-id')[:10]
    for match in recent_matches:
        if hasattr(match, 'winner_team_id') and match.winner_team_id == team.id:
            win_streak += 1
        else:
            break
    
    # Upcoming matches count
    upcoming_matches_count = team_matches.filter(
        winner_team__isnull=True
    ).count()
    
    # Unread news count (placeholder - we'll implement news model later)
    unread_news_count = 0
    
    # Build context
    ctx = {
        'tournament': {
            'title': tournament.title,
            'slug': tournament.slug,
            'icon': tournament.icon if hasattr(tournament, 'icon') else None,
            'game_name': getattr(tournament, 'game_name', 'Esports'),
            'format': getattr(tournament, 'format', 'Tournament'),
            'region': getattr(tournament, 'region', 'Bangladesh'),
            'status': getattr(tournament, 'status', 'upcoming'),
        },
        'team': {
            'id': team.id,
            'name': team.name,
            'logo': team.logo if hasattr(team, 'logo') else None,
            'players': [
                {
                    'username': p.username,
                    'is_captain': (p == team.captain if hasattr(team, 'captain') else False)
                }
                for p in team_players
            ],
            'checked_in': getattr(registration, 'checked_in', False),
        },
        'is_captain': is_captain,
        'can_checkin': can_checkin,
        'stats': {
            'wins': wins,
            'losses': losses,
            'rank': rank,
            'points': points,
            'win_rate': win_rate,
            'matches_played': total_matches,
            'avg_score': avg_score,
            'win_streak': win_streak,
        },
        'upcoming_matches_count': upcoming_matches_count,
        'unread_news_count': unread_news_count,
    }
    
    return render(request, 'tournaments/dashboard.html', {'ctx': ctx})
