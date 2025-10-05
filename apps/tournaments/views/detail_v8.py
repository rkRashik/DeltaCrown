"""
Tournament Detail V8 - Complete Rebuild
Premium, future-proof tournament detail page with real data
"""

from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.core.cache import cache

from apps.tournaments.models import (
    Tournament, 
    TournamentCapacity,
    TournamentFinance,
    TournamentSchedule,
    TournamentRules,
    TournamentMedia,
    Registration,
    Match
)
from apps.teams.models import Team
from apps.common.game_assets import get_game_data


def tournament_detail_v8(request: HttpRequest, slug: str) -> HttpResponse:
    """
    V8 Tournament Detail View - Complete Rebuild
    
    Features:
    - Optimized database queries with select_related and prefetch_related
    - Real-time data from database
    - User registration status
    - Match schedule and results
    - Team listings
    - Prize distribution
    - Complete tournament information
    - Responsive and accessible
    """
    
    # ==========================================
    # CORE TOURNAMENT DATA
    # ==========================================
    
    tournament = get_object_or_404(
        Tournament.objects.select_related(
            'organizer',
            'capacity',
            'finance',
            'schedule',
            'rules',
            'media'
        ).prefetch_related(
            Prefetch(
                'registrations',
                queryset=Registration.objects.select_related('user', 'team')
            ),
            Prefetch(
                'matches',
                queryset=Match.objects.select_related(
                    'team_a', 'team_b'
                ).order_by('start_at')
            )
        ),
        slug=slug
    )
    
    # ==========================================
    # GAME INFORMATION
    # ==========================================
    
    game_data = get_game_data(tournament.game)
    
    # ==========================================
    # USER REGISTRATION STATUS
    # ==========================================
    
    user_registration = None
    user_team = None
    can_register = False
    
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        # Check if user has registered
        user_registration = tournament.registrations.filter(
            user=request.user.profile
        ).select_related('team').first()
        
        if user_registration:
            user_team = user_registration.team
        
        # Check if user can register
        can_register = (
            tournament.registration_open and
            not user_registration and
            tournament.status == 'PUBLISHED'
        )
    
    # ==========================================
    # CAPACITY & REGISTRATION INFO
    # ==========================================
    
    capacity_info = {
        'total_slots': 0,
        'filled_slots': 0,
        'available_slots': 0,
        'fill_percentage': 0,
        'is_full': False
    }
    
    if hasattr(tournament, 'capacity') and tournament.capacity:
        approved_count = tournament.registrations.filter(status='CONFIRMED').count()
        
        if tournament.format == 'SOLO':
            total = tournament.capacity.max_teams or 0  # For solo, max_teams = max_participants
            filled = approved_count
        else:  # TEAM format
            total = tournament.capacity.max_teams or 0
            filled = tournament.registrations.filter(
                status='CONFIRMED',
                team__isnull=False
            ).values('team').distinct().count()
        
        capacity_info.update({
            'total_slots': total,
            'filled_slots': filled,
            'available_slots': max(0, total - filled),
            'fill_percentage': int((filled / total * 100)) if total > 0 else 0,
            'is_full': filled >= total if total > 0 else False
        })
    
    # ==========================================
    # PRIZE DISTRIBUTION
    # ==========================================
    
    prize_distribution = []
    
    if hasattr(tournament, 'finance') and tournament.finance:
        finance = tournament.finance
        
        # Get prizes from JSON field using the model's method
        prizes = []
        medals = ['🥇', '🥈', '🥉', '🏅', '🏅', '🏅', '🏅', '🏅']
        
        # Try to get up to 8 prize positions
        for position in range(1, 9):
            amount = finance.get_prize_for_position(position)
            if amount and amount > 0:
                suffix = 'st' if position == 1 else 'nd' if position == 2 else 'rd' if position == 3 else 'th'
                prizes.append({
                    'position': position,
                    'amount': amount,
                    'medal': medals[position - 1] if position <= len(medals) else '🏅',
                    'label': f'{position}{suffix} Place'
                })
        
        prize_distribution = prizes
    
    # ==========================================
    # SCHEDULE & TIMELINE
    # ==========================================
    
    timeline_events = []
    now = timezone.now()
    
    if hasattr(tournament, 'schedule') and tournament.schedule:
        schedule = tournament.schedule
        
        # Registration period
        if schedule.reg_open_at:
            timeline_events.append({
                'title': 'Registration Opens',
                'date': schedule.reg_open_at,
                'status': 'completed' if schedule.reg_open_at < now else 'upcoming',
                'icon': 'user-plus'
            })
        
        if schedule.reg_close_at:
            timeline_events.append({
                'title': 'Registration Closes',
                'date': schedule.reg_close_at,
                'status': 'completed' if schedule.reg_close_at < now else 'upcoming',
                'icon': 'user-check'
            })
        
        # Tournament dates
        if tournament.start_at:
            timeline_events.append({
                'title': 'Tournament Starts',
                'date': tournament.start_at,
                'status': 'completed' if tournament.start_at < now else 'upcoming',
                'icon': 'play-circle'
            })
        
        if tournament.end_at:
            timeline_events.append({
                'title': 'Tournament Ends',
                'date': tournament.end_at,
                'status': 'completed' if tournament.end_at < now else 'upcoming',
                'icon': 'flag-checkered'
            })
        
        # Check-in
        if schedule.start_at and schedule.check_in_open_mins:
            check_in_start = schedule.start_at - timezone.timedelta(minutes=schedule.check_in_open_mins)
            timeline_events.append({
                'title': 'Check-in Opens',
                'date': check_in_start,
                'status': 'completed' if check_in_start < now else 'upcoming',
                'icon': 'clipboard-check'
            })
    
    # Sort timeline by date
    timeline_events.sort(key=lambda x: x['date'])
    
    # ==========================================
    # REGISTERED TEAMS/PLAYERS
    # ==========================================
    
    participants = []
    
    if tournament.format == 'TEAM':
        # Get teams with their members
        team_registrations = tournament.registrations.filter(
            status='CONFIRMED',
            team__isnull=False
        ).select_related('team').prefetch_related('team__members')
        
        teams_dict = {}
        for reg in team_registrations:
            if reg.team_id not in teams_dict:
                teams_dict[reg.team_id] = {
                    'team': reg.team,
                    'members': []
                }
        
        # Get all team members
        for team_id, team_data in teams_dict.items():
            team = team_data['team']
            members = team.members.all()[:5]  # Show first 5 members
            team_data['members'] = members
            team_data['member_count'] = team.members.count()
        
        participants = list(teams_dict.values())
    else:
        # SOLO format - get individual players
        solo_registrations = tournament.registrations.filter(
            status='CONFIRMED'
        ).select_related('user')[:50]  # Limit to 50 for performance
        
        participants = [{'user': reg.user} for reg in solo_registrations]
    
    # ==========================================
    # UPCOMING MATCHES
    # ==========================================
    
    upcoming_matches = tournament.matches.filter(
        state__in=['SCHEDULED'],
        start_at__gte=now
    ).order_by('start_at')[:5]
    
    recent_matches = tournament.matches.filter(
        state='VERIFIED'
    ).order_by('-start_at')[:5]
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    stats = {
        'total_participants': 0,
        'total_matches': tournament.matches.count(),
        'completed_matches': tournament.matches.filter(state='VERIFIED').count(),
        'live_matches': tournament.matches.filter(state='REPORTED').count(),
    }
    
    if tournament.format == 'TEAM':
        stats['total_participants'] = len(participants)
    else:
        stats['total_participants'] = len(participants)
    
    # ==========================================
    # ORGANIZER INFO
    # ==========================================
    
    organizer_info = None
    if hasattr(tournament, 'organizer') and tournament.organizer:
        organizer = tournament.organizer
        organizer_info = {
            'name': organizer.user.get_full_name() or organizer.user.username,
            'email': organizer.user.email if organizer.user.email else None,
            'phone': getattr(organizer, 'phone_number', None),
            'website': getattr(organizer, 'website', None),
        }
    
    # ==========================================
    # RULES & REGULATIONS
    # ==========================================
    
    rules_data = None
    if hasattr(tournament, 'rules') and tournament.rules:
        rules_data = {
            'general': tournament.rules.general_rules,
            'format': tournament.rules.match_rules,
            'conduct': tournament.rules.penalty_rules,
            'scoring': tournament.rules.scoring_system,
        }
    
    # ==========================================
    # MEDIA & ASSETS
    # ==========================================
    
    media_data = None
    if hasattr(tournament, 'media') and tournament.media:
        media_data = {
            'banner': tournament.media.banner,
            'thumbnail': tournament.media.thumbnail,
            'rules_pdf': tournament.media.rules_pdf,
            'promotional_images': tournament.media.get_promotional_image_urls(),
            'social_media_image': tournament.media.social_media_image,
        }
    
    # ==========================================
    # REGISTRATION URL
    # ==========================================
    
    register_url = f"/tournaments/register-modern/{tournament.slug}/"
    
    # ==========================================
    # CONTEXT ASSEMBLY
    # ==========================================
    
    context = {
        # Core data
        'tournament': tournament,
        'game_data': game_data,
        
        # User status
        'user_registration': user_registration,
        'user_team': user_team,
        'can_register': can_register,
        'register_url': register_url,
        
        # Capacity
        'capacity_info': capacity_info,
        
        # Prizes
        'prize_distribution': prize_distribution,
        'total_prize_pool': sum(p['amount'] for p in prize_distribution),
        'prize_1st': int(float(sum(p['amount'] for p in prize_distribution)) * 0.5),
        'prize_2nd': int(float(sum(p['amount'] for p in prize_distribution)) * 0.3),
        'prize_3rd': int(float(sum(p['amount'] for p in prize_distribution)) * 0.2),
        
        # Timeline
        'timeline_events': timeline_events,
        
        # Participants
        'participants': participants,
        'participant_count': len(participants),
        
        # Matches
        'upcoming_matches': upcoming_matches,
        'recent_matches': recent_matches,
        
        # Stats
        'stats': stats,
        
        # Additional info
        'organizer_info': organizer_info,
        'rules_data': rules_data,
        'media_data': media_data,
        
        # Meta
        'now': now,
    }
    
    return render(request, 'tournaments/tournament_detail.html', context)
