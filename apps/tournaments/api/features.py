"""
Tournament Features API Views
Provides endpoints for bracket data, match predictions, and interactive features
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from apps.tournaments.models import Tournament, Match, Registration


@api_view(['GET'])
@permission_classes([AllowAny])
def get_tournament_bracket(request, slug):
    """
    Get tournament bracket data with all matches organized by rounds
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Get all matches for this tournament
    matches = Match.objects.filter(tournament=tournament).select_related(
        'team_a', 'team_b', 'winner'
    ).order_by('round', 'match_number')
    
    # Organize matches by rounds
    rounds_dict = {}
    for match in matches:
        round_num = match.round or 1
        if round_num not in rounds_dict:
            rounds_dict[round_num] = {
                'name': f'Round {round_num}',
                'matches': []
            }
        
        match_data = {
            'id': match.id,
            'match_number': match.match_number,
            'status': match.status,
            'scheduled_time': match.scheduled_time.isoformat() if match.scheduled_time else None,
            'team_a': {
                'id': match.team_a.id,
                'name': match.team_a.name,
                'logo': match.team_a.logo.url if match.team_a and match.team_a.logo else None,
                'seed': getattr(match.team_a, 'seed', None)
            } if match.team_a else None,
            'team_b': {
                'id': match.team_b.id,
                'name': match.team_b.name,
                'logo': match.team_b.logo.url if match.team_b and match.team_b.logo else None,
                'seed': getattr(match.team_b, 'seed', None)
            } if match.team_b else None,
            'score_a': match.score_a,
            'score_b': match.score_b,
            'winner_id': match.winner.id if match.winner else None
        }
        
        rounds_dict[round_num]['matches'].append(match_data)
    
    # Convert to list and add round names
    rounds = []
    max_round = max(rounds_dict.keys()) if rounds_dict else 0
    
    for round_num in sorted(rounds_dict.keys()):
        round_data = rounds_dict[round_num]
        
        # Add descriptive names for key rounds
        if round_num == max_round:
            round_data['name'] = 'Finals'
        elif round_num == max_round - 1:
            round_data['name'] = 'Semi-Finals'
        elif round_num == max_round - 2:
            round_data['name'] = 'Quarter-Finals'
        
        rounds.append(round_data)
    
    return Response({
        'tournament': {
            'slug': tournament.slug,
            'name': tournament.name,
            'status': tournament.status
        },
        'rounds': rounds,
        'total_matches': matches.count(),
        'completed_matches': matches.filter(status='COMPLETED').count()
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_match_details(request, match_id):
    """
    Get detailed information about a specific match
    """
    match = get_object_or_404(Match, id=match_id)
    
    data = {
        'id': match.id,
        'match_number': match.match_number,
        'round': match.round,
        'status': match.status,
        'scheduled_time': match.scheduled_time.isoformat() if match.scheduled_time else None,
        'start_time': match.start_time.isoformat() if match.start_time else None,
        'end_time': match.end_time.isoformat() if match.end_time else None,
        'team_a': {
            'id': match.team_a.id,
            'name': match.team_a.name,
            'logo': match.team_a.logo.url if match.team_a.logo else None,
        } if match.team_a else None,
        'team_b': {
            'id': match.team_b.id,
            'name': match.team_b.name,
            'logo': match.team_b.logo.url if match.team_b.logo else None,
        } if match.team_b else None,
        'score_a': match.score_a,
        'score_b': match.score_b,
        'winner': {
            'id': match.winner.id,
            'name': match.winner.name
        } if match.winner else None,
        'stream_url': match.stream_url,
        'notes': match.notes
    }
    
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_match_to_calendar(request, match_id):
    """
    Generate calendar event data for a match
    """
    match = get_object_or_404(Match, id=match_id)
    
    if not match.scheduled_time:
        return Response(
            {'error': 'Match does not have a scheduled time'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Generate calendar data
    event_data = {
        'title': f'{match.team_a.name if match.team_a else "TBD"} vs {match.team_b.name if match.team_b else "TBD"}',
        'description': f'Tournament: {match.tournament.name}\nMatch #{match.match_number}',
        'start': match.scheduled_time.isoformat(),
        'end': (match.scheduled_time + timezone.timedelta(hours=2)).isoformat(),
        'location': 'Online',
        'url': request.build_absolute_uri(f'/tournaments/{match.tournament.slug}/')
    }
    
    return Response(event_data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_tournament_stats(request, slug):
    """
    Get live statistics for a tournament
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    registrations = Registration.objects.filter(tournament=tournament)
    matches = Match.objects.filter(tournament=tournament)
    
    stats = {
        'total_teams': registrations.filter(team__isnull=False).count(),
        'checked_in_teams': registrations.filter(team__isnull=False, status='CONFIRMED').count(),
        'total_matches': matches.count(),
        'completed_matches': matches.filter(status='COMPLETED').count(),
        'live_matches': matches.filter(status='LIVE').count(),
        'upcoming_matches': matches.filter(status='SCHEDULED').count(),
        'total_prize_pool': tournament.prize_pool or 0,
        'start_time': tournament.start_at.isoformat() if tournament.start_at else None,
        'status': tournament.status
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_participant_directory(request, slug):
    """
    Get list of all participating teams with their players
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    registrations = Registration.objects.filter(
        tournament=tournament,
        team__isnull=False
    ).select_related('team').prefetch_related('team__players')
    
    teams = []
    for reg in registrations:
        team = reg.team
        if not team:
            continue
            
        teams.append({
            'id': team.id,
            'name': team.name,
            'logo': team.logo.url if team.logo else None,
            'captain': team.captain.username if team.captain else None,
            'players': [
                {
                    'id': p.id,
                    'username': p.username,
                    'avatar': p.avatar.url if hasattr(p, 'avatar') and p.avatar else None
                }
                for p in team.players.all()
            ],
            'status': reg.status,
            'registration_date': reg.created_at.isoformat()
        })
    
    return Response({
        'tournament': tournament.name,
        'total_teams': len(teams),
        'teams': teams
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_team_stats(request, team_id):
    """
    Get detailed statistics for a specific team
    """
    from apps.teams.models import Team
    team = get_object_or_404(Team, id=team_id)
    
    # Get all matches for this team
    matches_as_a = Match.objects.filter(team_a=team)
    matches_as_b = Match.objects.filter(team_b=team)
    all_matches = (matches_as_a | matches_as_b).filter(status='COMPLETED')
    
    # Calculate stats
    total_matches = all_matches.count()
    wins = all_matches.filter(winner=team).count()
    losses = total_matches - wins
    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
    
    # Calculate total score
    total_score_for = 0
    total_score_against = 0
    
    for match in matches_as_a:
        if match.score_a is not None:
            total_score_for += match.score_a
            total_score_against += match.score_b or 0
    
    for match in matches_as_b:
        if match.score_b is not None:
            total_score_for += match.score_b
            total_score_against += match.score_a or 0
    
    avg_score = (total_score_for / total_matches) if total_matches > 0 else 0
    
    stats = {
        'team_id': team.id,
        'team_name': team.name,
        'logo': team.logo.url if team.logo else None,
        'total_matches': total_matches,
        'wins': wins,
        'losses': losses,
        'win_rate': round(win_rate, 1),
        'total_score_for': total_score_for,
        'total_score_against': total_score_against,
        'avg_score': round(avg_score, 1),
        'players_count': team.players.count()
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_head_to_head(request, team1_id, team2_id):
    """
    Get head-to-head statistics between two teams
    """
    from apps.teams.models import Team
    team1 = get_object_or_404(Team, id=team1_id)
    team2 = get_object_or_404(Team, id=team2_id)
    
    # Get all matches between these teams
    matches = Match.objects.filter(
        status='COMPLETED'
    ).filter(
        (Q(team_a=team1, team_b=team2) | Q(team_a=team2, team_b=team1))
    ).order_by('-scheduled_time')
    
    team1_wins = 0
    team2_wins = 0
    match_history = []
    
    for match in matches:
        if match.winner == team1:
            team1_wins += 1
        elif match.winner == team2:
            team2_wins += 1
        
        match_history.append({
            'id': match.id,
            'date': match.scheduled_time.isoformat() if match.scheduled_time else None,
            'tournament': match.tournament.name,
            'team_a': {
                'id': match.team_a.id,
                'name': match.team_a.name,
                'score': match.score_a
            },
            'team_b': {
                'id': match.team_b.id,
                'name': match.team_b.name,
                'score': match.score_b
            },
            'winner_id': match.winner.id if match.winner else None
        })
    
    return Response({
        'team1': {
            'id': team1.id,
            'name': team1.name,
            'wins': team1_wins
        },
        'team2': {
            'id': team2.id,
            'name': team2.name,
            'wins': team2_wins
        },
        'total_matches': matches.count(),
        'match_history': match_history
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_stream_data(request, slug):
    """
    Get live stream information for a tournament
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Check if there's a live match with stream
    live_match = Match.objects.filter(
        tournament=tournament,
        status='LIVE',
        stream_url__isnull=False
    ).first()
    
    if live_match and live_match.stream_url:
        stream_url = live_match.stream_url
    elif hasattr(tournament, 'stream_url') and tournament.stream_url:
        stream_url = tournament.stream_url
    else:
        stream_url = None
    
    # Simulate viewer count (in production, this would come from streaming platform API)
    import random
    viewer_count = random.randint(150, 5000) if stream_url else 0
    
    data = {
        'stream_url': stream_url,
        'viewer_count': viewer_count,
        'is_live': tournament.status == 'RUNNING' and stream_url is not None,
        'match': {
            'id': live_match.id,
            'teams': f'{live_match.team_a.name} vs {live_match.team_b.name}'
        } if live_match else None
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_chat_history(request, slug):
    """
    Get recent chat messages for a tournament
    """
    # In production, you'd query a ChatMessage model
    # For now, return placeholder data
    
    messages = [
        {
            'id': 1,
            'username': 'Player1',
            'team': 'Team Phoenix',
            'message': 'Good luck everyone!',
            'timestamp': timezone.now().isoformat(),
            'avatar': None
        }
    ]
    
    return Response({
        'messages': messages,
        'online_count': 42
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_match_prediction(request, match_id):
    """
    Submit a prediction for a match outcome
    """
    match = get_object_or_404(Match, id=match_id)
    
    predicted_winner_id = request.data.get('predicted_winner_id')
    
    if not predicted_winner_id:
        return Response(
            {'error': 'predicted_winner_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if match.status != 'SCHEDULED':
        return Response(
            {'error': 'Can only predict scheduled matches'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # In production, save to a MatchPrediction model
    # For now, return success
    
    return Response({
        'success': True,
        'match_id': match_id,
        'predicted_winner_id': predicted_winner_id,
        'message': 'Prediction submitted successfully'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_match_predictions(request, match_id):
    """
    Get prediction statistics for a match
    """
    match = get_object_or_404(Match, id=match_id)
    
    # In production, aggregate from MatchPrediction model
    # For now, return simulated data
    import random
    
    if not match.team_a or not match.team_b:
        return Response({
            'predictions': [],
            'total_predictions': 0
        })
    
    total = random.randint(50, 500)
    team_a_pct = random.randint(40, 60)
    team_b_pct = 100 - team_a_pct
    
    data = {
        'match_id': match.id,
        'total_predictions': total,
        'predictions': [
            {
                'team_id': match.team_a.id,
                'team_name': match.team_a.name,
                'votes': int(total * team_a_pct / 100),
                'percentage': team_a_pct
            },
            {
                'team_id': match.team_b.id,
                'team_name': match.team_b.name,
                'votes': int(total * team_b_pct / 100),
                'percentage': team_b_pct
            }
        ]
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_player_stats(request, slug):
    """
    Get player statistics leaderboard for a tournament
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Get all participating teams
    registrations = Registration.objects.filter(
        tournament=tournament,
        team__isnull=False
    ).select_related('team').prefetch_related('team__players')
    
    players_data = []
    for reg in registrations:
        team = reg.team
        if not team:
            continue
            
        for player in team.players.all():
            players_data.append({
                'id': player.id,
                'name': player.username,
                'team': team.name,
                'avatar': player.profile.avatar.url if hasattr(player, 'profile') and hasattr(player.profile, 'avatar') and player.profile.avatar else None,
                'is_online': False,  # In production, check online status
                'kills': 0,  # In production, aggregate from match stats
                'wins': 0,
                'mvp': 0
            })
    
    return Response({
        'tournament': tournament.name,
        'players': players_data[:20]  # Top 20
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_activities(request, slug):
    """
    Get live activity feed for a tournament
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    activities = []
    
    # Recent registrations
    recent_regs = Registration.objects.filter(
        tournament=tournament
    ).select_related('team', 'user').order_by('-created_at')[:5]
    
    for reg in recent_regs:
        name = reg.team.name if reg.team else reg.user.username if reg.user else 'Someone'
        activities.append({
            'type': 'registration',
            'message': f'{name} registered for the tournament',
            'timestamp': reg.created_at.isoformat()
        })
    
    # Recent matches
    recent_matches = Match.objects.filter(
        tournament=tournament,
        status__in=['COMPLETED', 'LIVE']
    ).order_by('-scheduled_time')[:5]
    
    for match in recent_matches:
        if match.status == 'LIVE':
            activities.append({
                'type': 'match',
                'message': f'LIVE: {match.team_a.name if match.team_a else "TBD"} vs {match.team_b.name if match.team_b else "TBD"}',
                'timestamp': timezone.now().isoformat()
            })
        elif match.status == 'COMPLETED' and match.winner:
            activities.append({
                'type': 'result',
                'message': f'{match.winner.name} won against {match.team_b.name if match.winner == match.team_a else match.team_a.name}',
                'timestamp': match.end_time.isoformat() if match.end_time else match.scheduled_time.isoformat()
            })
    
    # Sort by timestamp
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return Response({
        'activities': activities[:20],
        'new_count': 0
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_highlights(request, slug):
    """
    Get highlight reels for a tournament
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # In production, fetch from TournamentHighlight model
    # For now, return placeholder data
    highlights = []
    
    # Check if tournament has any completed matches
    completed_matches = Match.objects.filter(
        tournament=tournament,
        status='COMPLETED'
    ).order_by('-end_time')[:5]
    
    for match in completed_matches:
        if match.stream_url:
            highlights.append({
                'id': match.id,
                'title': f'{match.team_a.name if match.team_a else "TBD"} vs {match.team_b.name if match.team_b else "TBD"} - Highlights',
                'thumbnail': match.team_a.logo.url if match.team_a and match.team_a.logo else '/static/img/tournament_placeholder.jpg',
                'video_url': match.stream_url,
                'duration': '5:30',
                'views': 1250,
                'created_at': match.end_time.isoformat() if match.end_time else match.scheduled_time.isoformat()
            })
    
    return Response({
        'tournament': tournament.name,
        'highlights': highlights
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def track_share(request, slug):
    """
    Track social media shares (analytics)
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    platform = request.data.get('platform', 'unknown')
    
    # In production, save to analytics database
    # For now, just return success
    
    return Response({
        'success': True,
        'message': f'Share tracked for {platform}'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def download_schedule(request, slug):
    """
    Download tournament schedule as iCalendar file
    """
    from django.http import HttpResponse
    import io
    
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Create iCalendar content
    cal_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//DeltaCrown//Tournament Schedule//EN
X-WR-CALNAME:{tournament.name}
X-WR-TIMEZONE:Asia/Dhaka
"""
    
    matches = Match.objects.filter(
        tournament=tournament,
        scheduled_time__isnull=False
    ).order_by('scheduled_time')
    
    for match in matches:
        start = match.scheduled_time
        end = start + timezone.timedelta(hours=2)
        
        cal_content += f"""BEGIN:VEVENT
UID:match-{match.id}@deltacrown.com
DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}
DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}
DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}
SUMMARY:{match.team_a.name if match.team_a else 'TBD'} vs {match.team_b.name if match.team_b else 'TBD'}
DESCRIPTION:Tournament: {tournament.name}\\nMatch #{match.match_number}
LOCATION:Online
STATUS:CONFIRMED
END:VEVENT
"""
    
    cal_content += "END:VCALENDAR"
    
    response = HttpResponse(cal_content, content_type='text/calendar')
    response['Content-Disposition'] = f'attachment; filename="tournament-{slug}.ics"'
    
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def download_bracket(request, slug):
    """
    Download tournament bracket as PDF (placeholder)
    """
    from django.http import HttpResponse
    
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # In production, generate actual PDF with bracket
    # For now, return a simple response
    content = f"Tournament Bracket: {tournament.name}\n\nBracket visualization would be generated here."
    
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bracket-{slug}.pdf"'
    
    return response
