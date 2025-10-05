# apps/tournaments/api_views.py
"""
Enhanced API Views for Tournament Details
Provides comprehensive data for modern frontend
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.apps import apps
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q

Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
Match = apps.get_model("tournaments", "Match")
Team = apps.get_model("teams", "Team")


@api_view(['GET'])
def tournament_teams(request, slug):
    """
    Get all registered teams for a tournament.
    Returns team info with players if available.
    
    Query Params:
        - status: Filter by registration status (PENDING, CONFIRMED, REJECTED)
        - search: Search team names
        - page: Page number for pagination
        - limit: Items per page (default 20, max 100)
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Check cache
    cache_key = f"tournament_teams_{slug}_{request.GET.urlencode()}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)
    
    # Get registrations
    registrations = Registration.objects.filter(
        tournament=tournament
    ).select_related('user', 'team').prefetch_related(
        'team__members'
    )
    
    # Filter by status
    reg_status = request.GET.get('status', 'CONFIRMED')
    if reg_status:
        registrations = registrations.filter(status=reg_status)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        registrations = registrations.filter(
            Q(team__name__icontains=search) |
            Q(user__user__username__icontains=search)
        )
    
    # Pagination
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 20)), 100)
    start = (page - 1) * limit
    end = start + limit
    
    total_count = registrations.count()
    registrations = registrations[start:end]
    
    # Build response
    teams_data = []
    for reg in registrations:
        team_data = {
            'registration_id': reg.id,
            'status': reg.status,
            'registered_at': reg.created_at.isoformat() if hasattr(reg, 'created_at') else None,
            'checked_in': getattr(reg, 'checked_in', False),
            'team': None,
            'captain': None,
        }
        
        # Team info
        if reg.team:
            team = reg.team
            team_data['team'] = {
                'id': team.id,
                'name': team.name,
                'tag': getattr(team, 'tag', ''),
                'logo': team.logo.url if hasattr(team, 'logo') and team.logo else None,
                'member_count': team.members.count() if hasattr(team, 'members') else 0,
                'members': []
            }
            
            # Team members
            if hasattr(team, 'members'):
                for member in team.members.all()[:10]:  # Limit to 10
                    member_data = {
                        'id': member.id,
                        'username': member.user.username if hasattr(member, 'user') else 'Unknown',
                        'avatar': member.profile_picture.url if hasattr(member, 'profile_picture') and member.profile_picture else None,
                        'role': getattr(member, 'role', 'Member'),
                    }
                    team_data['team']['members'].append(member_data)
        
        # Captain info (solo player)
        elif reg.user:
            user_profile = reg.user
            team_data['captain'] = {
                'id': user_profile.id,
                'username': user_profile.user.username if hasattr(user_profile, 'user') else 'Unknown',
                'avatar': user_profile.profile_picture.url if hasattr(user_profile, 'profile_picture') and user_profile.profile_picture else None,
                'display_name': getattr(user_profile, 'display_name', ''),
            }
        
        teams_data.append(team_data)
    
    response_data = {
        'tournament': {
            'slug': tournament.slug,
            'title': tournament.title,
        },
        'teams': teams_data,
        'pagination': {
            'page': page,
            'limit': limit,
            'total_count': total_count,
            'total_pages': (total_count + limit - 1) // limit,
            'has_next': end < total_count,
            'has_previous': page > 1,
        },
        'filters': {
            'status': reg_status,
            'search': search,
        }
    }
    
    # Cache for 2 minutes
    cache.set(cache_key, response_data, 120)
    
    return Response(response_data)


@api_view(['GET'])
def tournament_matches(request, slug):
    """
    Get all matches for a tournament.
    Includes schedule, results, and bracket position if applicable.
    
    Query Params:
        - status: Filter by match status (SCHEDULED, LIVE, COMPLETED, CANCELLED)
        - round: Filter by round number
        - date: Filter by date (YYYY-MM-DD)
        - page: Page number
        - limit: Items per page
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Check cache
    cache_key = f"tournament_matches_{slug}_{request.GET.urlencode()}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)
    
    # Get matches
    matches = Match.objects.filter(
        tournament=tournament
    ).select_related(
        'team1', 'team2'
    ).order_by('round_number', 'match_number', 'scheduled_time')
    
    # Filter by status
    match_status = request.GET.get('status', '')
    if match_status:
        matches = matches.filter(status=match_status)
    
    # Filter by round
    round_num = request.GET.get('round', '')
    if round_num:
        try:
            matches = matches.filter(round_number=int(round_num))
        except ValueError:
            pass
    
    # Filter by date
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            from datetime import datetime
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            matches = matches.filter(scheduled_time__date=date)
        except ValueError:
            pass
    
    # Pagination
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 20)), 100)
    start = (page - 1) * limit
    end = start + limit
    
    total_count = matches.count()
    matches = matches[start:end]
    
    # Build response
    matches_data = []
    for match in matches:
        match_data = {
            'id': match.id,
            'match_number': getattr(match, 'match_number', 0),
            'round_number': getattr(match, 'round_number', 1),
            'round_name': getattr(match, 'round_name', f'Round {match.round_number}'),
            'status': getattr(match, 'status', 'SCHEDULED'),
            'scheduled_time': match.scheduled_time.isoformat() if hasattr(match, 'scheduled_time') and match.scheduled_time else None,
            'start_time': match.start_time.isoformat() if hasattr(match, 'start_time') and match.start_time else None,
            'end_time': match.end_time.isoformat() if hasattr(match, 'end_time') and match.end_time else None,
            'bracket_position': getattr(match, 'bracket_position', None),
            'team1': None,
            'team2': None,
            'winner': None,
            'scores': {
                'team1': getattr(match, 'team1_score', 0),
                'team2': getattr(match, 'team2_score', 0),
            },
            'best_of': getattr(match, 'best_of', 1),
            'stream_url': getattr(match, 'stream_url', ''),
        }
        
        # Team 1 info
        if match.team1:
            team = match.team1
            match_data['team1'] = {
                'id': team.id,
                'name': team.name,
                'tag': getattr(team, 'tag', ''),
                'logo': team.logo.url if hasattr(team, 'logo') and team.logo else None,
            }
        
        # Team 2 info
        if match.team2:
            team = match.team2
            match_data['team2'] = {
                'id': team.id,
                'name': team.name,
                'tag': getattr(team, 'tag', ''),
                'logo': team.logo.url if hasattr(team, 'logo') and team.logo else None,
            }
        
        # Winner info
        if hasattr(match, 'winner') and match.winner:
            match_data['winner'] = match.winner.id
        
        matches_data.append(match_data)
    
    response_data = {
        'tournament': {
            'slug': tournament.slug,
            'title': tournament.title,
            'format': getattr(tournament, 'format_type', 'single-elimination'),
        },
        'matches': matches_data,
        'pagination': {
            'page': page,
            'limit': limit,
            'total_count': total_count,
            'total_pages': (total_count + limit - 1) // limit,
            'has_next': end < total_count,
            'has_previous': page > 1,
        },
        'filters': {
            'status': match_status,
            'round': round_num,
            'date': date_str,
        }
    }
    
    # Cache for 1 minute (matches update frequently)
    cache.set(cache_key, response_data, 60)
    
    return Response(response_data)


@api_view(['GET'])
def tournament_leaderboard(request, slug):
    """
    Get tournament leaderboard/standings.
    Shows team rankings, points, wins/losses, etc.
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Check cache
    cache_key = f"tournament_leaderboard_{slug}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)
    
    # Get registrations with match stats
    registrations = Registration.objects.filter(
        tournament=tournament,
        status='CONFIRMED'
    ).select_related('team', 'user')
    
    # Calculate standings
    standings = []
    for reg in registrations:
        team_id = reg.team.id if reg.team else None
        team_name = reg.team.name if reg.team else (reg.user.user.username if reg.user else 'Unknown')
        
        # Get match statistics
        if team_id:
            wins = Match.objects.filter(
                tournament=tournament,
                winner_id=team_id,
                status='COMPLETED'
            ).count()
            
            losses = Match.objects.filter(
                Q(team1_id=team_id) | Q(team2_id=team_id),
                tournament=tournament,
                status='COMPLETED'
            ).exclude(winner_id=team_id).count()
            
            total_matches = wins + losses
        else:
            wins = losses = total_matches = 0
        
        # Calculate points (3 for win, 0 for loss - adjust as needed)
        points = wins * 3
        
        standing = {
            'team_id': team_id,
            'team_name': team_name,
            'team_logo': reg.team.logo.url if reg.team and hasattr(reg.team, 'logo') and reg.team.logo else None,
            'points': points,
            'wins': wins,
            'losses': losses,
            'total_matches': total_matches,
            'win_rate': round((wins / total_matches * 100) if total_matches > 0 else 0, 1),
        }
        
        standings.append(standing)
    
    # Sort by points, then wins, then win rate
    standings.sort(key=lambda x: (x['points'], x['wins'], x['win_rate']), reverse=True)
    
    # Add rank
    for idx, standing in enumerate(standings, 1):
        standing['rank'] = idx
    
    response_data = {
        'tournament': {
            'slug': tournament.slug,
            'title': tournament.title,
        },
        'standings': standings,
        'last_updated': timezone.now().isoformat(),
    }
    
    # Cache for 2 minutes
    cache.set(cache_key, response_data, 120)
    
    return Response(response_data)


@api_view(['GET'])
def tournament_registration_status(request, slug):
    """
    Get current user's registration status for a tournament.
    Requires authentication.
    """
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    tournament = get_object_or_404(Tournament, slug=slug)
    
    try:
        user_profile = request.user.userprofile
    except AttributeError:
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get registration
    registration = Registration.objects.filter(
        tournament=tournament,
        user=user_profile
    ).select_related('team').first()
    
    if not registration:
        return Response({
            'registered': False,
            'can_register': True,  # Add logic to check if registration is open
            'message': 'Not registered for this tournament'
        })
    
    # Build response
    response_data = {
        'registered': True,
        'registration': {
            'id': registration.id,
            'status': registration.status,
            'registered_at': registration.created_at.isoformat() if hasattr(registration, 'created_at') else None,
            'checked_in': getattr(registration, 'checked_in', False),
            'team': None,
        }
    }
    
    # Team info
    if registration.team:
        team = registration.team
        response_data['registration']['team'] = {
            'id': team.id,
            'name': team.name,
            'tag': getattr(team, 'tag', ''),
            'logo': team.logo.url if hasattr(team, 'logo') and team.logo else None,
        }
    
    return Response(response_data)


@api_view(['GET'])
def featured_tournaments(request):
    """
    Get featured tournaments for the hub page.
    Returns tournaments marked as featured or most popular recent ones.
    """
    # Check cache
    cache_key = "featured_tournaments"
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)
    
    # Get featured tournaments
    tournaments = Tournament.objects.filter(
        status__in=['PUBLISHED', 'RUNNING']
    ).select_related('game').order_by('-created_at')[:6]
    
    # Optimize queryset for schedule/capacity/finance access
    from apps.tournaments.utils.schedule_helpers import optimize_queryset_for_schedule
    from apps.tournaments.utils.capacity_helpers import optimize_queryset_for_capacity
    from apps.tournaments.utils.finance_helpers import optimize_queryset_for_finance
    
    tournaments = optimize_queryset_for_schedule(tournaments)
    tournaments = optimize_queryset_for_capacity(tournaments)
    tournaments = optimize_queryset_for_finance(tournaments)
    
    # Build response
    tournaments_data = []
    for t in tournaments:
        from apps.tournaments.utils.schedule_helpers import get_schedule_context
        from apps.tournaments.utils.capacity_helpers import get_capacity_context
        from apps.tournaments.utils.finance_helpers import get_finance_context
        
        schedule = get_schedule_context(t)
        capacity = get_capacity_context(t)
        finance = get_finance_context(t)
        
        tournament_data = {
            'slug': t.slug,
            'title': t.title,
            'short_desc': getattr(t, 'short_desc', ''),
            'banner': t.banner_image.url if hasattr(t, 'banner_image') and t.banner_image else None,
            'game': {
                'name': t.game.name if t.game else 'Unknown',
                'slug': t.game.slug if t.game else '',
                'icon': t.game.icon.url if t.game and hasattr(t.game, 'icon') and t.game.icon else None,
            },
            'status': getattr(t, 'status', 'DRAFT'),
            'schedule': schedule,
            'capacity': capacity,
            'finance': finance,
        }
        
        tournaments_data.append(tournament_data)
    
    response_data = {
        'tournaments': tournaments_data,
        'count': len(tournaments_data),
    }
    
    # Cache for 5 minutes
    cache.set(cache_key, response_data, 300)
    
    return Response(response_data)


@api_view(['GET'])
def tournament_live_stats(request, slug):
    """
    Get live tournament statistics for real-time updates.
    Returns current participant count, views, status, etc.
    
    Used by frontend JavaScript to poll for live updates every 30 seconds.
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Get participant count
    participants_count = Registration.objects.filter(
        tournament=tournament,
        status='CONFIRMED'
    ).count()
    
    # Get views count (if available)
    views_count = getattr(tournament, 'views_count', 0)
    
    # Get prize pool (if dynamic)
    prize_pool = getattr(tournament, 'prize_pool_amount', 0)
    
    # Get current status
    current_status = getattr(tournament, 'status', 'DRAFT')
    status_display = tournament.get_status_display() if hasattr(tournament, 'get_status_display') else current_status
    
    # Build response
    response_data = {
        'participants': participants_count,
        'views': views_count,
        'prize_pool': prize_pool,
        'status': current_status,
        'status_display': status_display,
        'last_updated': timezone.now().isoformat(),
    }
    
    # Add capacity info if available
    if hasattr(tournament, 'max_teams') and tournament.max_teams:
        response_data['capacity'] = {
            'current': participants_count,
            'max': tournament.max_teams,
            'percentage': (participants_count / tournament.max_teams * 100) if tournament.max_teams > 0 else 0,
            'spots_left': max(0, tournament.max_teams - participants_count)
        }
    
    return Response(response_data)
