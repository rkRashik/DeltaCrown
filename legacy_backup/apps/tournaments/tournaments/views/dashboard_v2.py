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
    user_profile = getattr(request.user, 'profile', None)
    if not user_profile:
        # Create a user profile if it doesn't exist
        from apps.user_profile.models import UserProfile
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    registration = None
    team = None
    
    # Check for team registration first
    team_registration = Registration.objects.select_related('team').filter(
        tournament=tournament,
        team__memberships__profile=user_profile,
        team__memberships__status='ACTIVE'
    ).first()
    
    if team_registration:
        registration = team_registration
        team = registration.team
    else:
        # Check for solo registration
        solo_registration = Registration.objects.filter(
            tournament=tournament,
            user=user_profile
        ).first()
        
        if solo_registration:
            registration = solo_registration
            team = None
    
    # If no registration found, redirect to detail page
    if not registration:
        return redirect('tournaments:detail', slug=slug)
    
    # Check if user is captain (only for team tournaments)
    is_captain = False
    if team and hasattr(team, 'captain'):
        is_captain = (team.captain == user_profile)
    
    # Can check-in if tournament allows and hasn't started
    can_checkin = (
        tournament.status in ['PUBLISHED', 'RUNNING'] and
        not getattr(registration, 'checked_in', False) and
        (is_captain if team else True)  # Solo players can always check themselves in
    )
    
    # Get team players (only for team tournaments)
    team_players = []
    if team:
        team_players = [membership.profile for membership in team.members[:10]]
    
    # Get quick stats
    if team:
        # Team tournament stats
        team_matches = Match.objects.filter(
            Q(team_a=team) | Q(team_b=team),
            tournament=tournament
        )
        
        wins = team_matches.filter(winner_team=team).count()
        total_matches = team_matches.exclude(winner_team__isnull=True).count()
        losses = total_matches - wins
        
        # Calculate rank (simple: count teams with more wins)
        teams_with_more_wins = Team.objects.filter(
            team_registrations__tournament=tournament
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
    else:
        # Solo tournament stats - matches are between individual users
        # For now, set default values since solo match structure might be different
        wins = 0
        losses = 0
        total_matches = 0
        rank = 1
    
    # Points (simple: 3 per win)
    points = wins * 3
    
    # Win rate
    win_rate = round((wins / total_matches * 100) if total_matches > 0 else 0, 1)
    
    # Average score (placeholder)
    avg_score = round((wins * 2 + losses) / max(total_matches, 1), 1)
    
    # Win streak (consecutive wins)
    win_streak = 0
    upcoming_matches_count = 0
    
    if team:
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
        # Provide lightweight tournament dict plus raw object for legacy uses
        'tournament': {
            'name': tournament.name,
            'title': tournament.name,  # legacy alias still used in templates
            'slug': tournament.slug,
            'icon': getattr(tournament, 'icon', None),
            'game_name': tournament.game.title() if tournament.game else 'Esports',
            'format': tournament.format if tournament.format else 'Tournament',
            'region': getattr(tournament, 'region', 'Global'),
            'status': tournament.status,
        },
        'raw_tournament': tournament,  # direct model access (has .title property alias now)
        'team': {
            'id': team.id if team else None,
            'name': team.name if team else user_profile.user.username,
            'logo': team.logo if team and hasattr(team, 'logo') else None,
            'players': [
                {
                    'username': p.user.username if hasattr(p, 'user') else str(p),
                    'is_captain': (p == team.captain if team and hasattr(team, 'captain') else False)
                }
                for p in team_players
            ] if team else [{'username': user_profile.user.username, 'is_captain': True}],
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
    
    return render(request, 'tournaments/war-room.html', {
        'ctx': ctx,
        'tournament': tournament  # Direct access for templates expecting tournament.title
    })
