"""
Tournament Integration Views for Teams

Handles team tournament registration, ranking display, and related features.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Q, Prefetch
from django.apps import apps
from django.core.paginator import Paginator

from apps.teams.services.tournament_registration import TournamentRegistrationService
from apps.teams.services.ranking_calculator import TeamRankingCalculator


def _get_user_profile(user):
    """Helper to get UserProfile from User."""
    if not user or not user.is_authenticated:
        return None
    try:
        return user.profile
    except AttributeError:
        UserProfile = apps.get_model('user_profile', 'UserProfile')
        try:
            return UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return None


@login_required
@require_http_methods(["GET", "POST"])
def tournament_registration_view(request, team_slug, tournament_slug):
    """
    Team tournament registration page.
    Shows registration form and validation status.
    """
    Team = apps.get_model('teams', 'Team')
    Tournament = apps.get_model('tournaments', 'Tournament')
    
    team = get_object_or_404(Team, slug=team_slug)
    tournament = get_object_or_404(Tournament, slug=tournament_slug)
    
    profile = _get_user_profile(request.user)
    
    # Check if user is captain
    if not profile or team.captain != profile:
        messages.error(request, "Only team captain can register for tournaments")
        return redirect('teams:detail', slug=team_slug)
    
    service = TournamentRegistrationService(team, tournament)
    
    if request.method == 'POST':
        # Handle registration submission
        payment_reference = request.POST.get('payment_reference', '')
        payment_method = request.POST.get('payment_method', '')
        
        result = service.register_team(
            captain_profile=profile,
            payment_reference=payment_reference,
            payment_method=payment_method
        )
        
        if result['success']:
            messages.success(request, result['message'])
            if result['validation']['valid']:
                messages.success(request, "✅ Roster validation passed!")
            else:
                messages.warning(request, "⚠️ Roster has validation issues that need to be resolved")
            
            return redirect('teams:tournament_registration_status', 
                          team_slug=team_slug, 
                          registration_id=result['registration'].id)
        else:
            messages.error(request, result.get('error', 'Registration failed'))
            if 'reasons' in result:
                for reason in result['reasons']:
                    messages.error(request, f"• {reason}")
    
    # Check registration eligibility
    eligibility = service.can_register()
    
    # Get existing registration if any
    TeamTournamentRegistration = apps.get_model('teams', 'TeamTournamentRegistration')
    existing_registration = TeamTournamentRegistration.objects.filter(
        team=team,
        tournament=tournament
    ).first()
    
    # Get team roster
    TeamMembership = apps.get_model('teams', 'TeamMembership')
    roster = TeamMembership.objects.filter(
        team=team,
        status=TeamMembership.Status.ACTIVE
    ).select_related('profile__user').order_by(
        '-role',  # Captain first
        'joined_at'
    )
    
    # Get pending invites
    pending_invites = team.invites.filter(status='PENDING').count()
    
    # Get game requirements
    from apps.teams.game_config import GAME_CONFIGS
    game_config = GAME_CONFIGS.get(team.game, {})
    
    context = {
        'team': team,
        'tournament': tournament,
        'eligibility': eligibility,
        'existing_registration': existing_registration,
        'roster': roster,
        'roster_count': roster.count(),
        'pending_invites_count': pending_invites,
        'game_config': game_config,
        'min_roster_size': game_config.get('team_size', 5),
        'max_roster_size': game_config.get('team_size', 5) + game_config.get('max_substitutes', 3),
    }
    
    return render(request, 'teams/tournament_registration.html', context)


@login_required
def tournament_registration_status_view(request, team_slug, registration_id):
    """
    View registration status and details.
    """
    Team = apps.get_model('teams', 'Team')
    TeamTournamentRegistration = apps.get_model('teams', 'TeamTournamentRegistration')
    
    team = get_object_or_404(Team, slug=team_slug)
    registration = get_object_or_404(
        TeamTournamentRegistration,
        id=registration_id,
        team=team
    )
    
    profile = _get_user_profile(request.user)
    
    # Check if user is team member
    is_member = team.has_member(profile)
    is_captain = profile == team.captain
    
    if not is_member and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this registration")
        return redirect('teams:detail', slug=team_slug)
    
    # Get roster from snapshot
    roster_snapshot = registration.roster_snapshot.get('roster', [])
    
    # Get participation records
    participations = registration.participations.all().select_related('player')
    
    # Get lock history
    lock_history = registration.lock_history.all()[:10]
    
    context = {
        'team': team,
        'registration': registration,
        'tournament': registration.tournament,
        'roster_snapshot': roster_snapshot,
        'participations': participations,
        'lock_history': lock_history,
        'is_captain': is_captain,
        'is_member': is_member,
    }
    
    return render(request, 'teams/tournament_registration_status.html', context)


@login_required
@require_POST
def cancel_tournament_registration(request, team_slug, registration_id):
    """
    Cancel tournament registration (captain only).
    """
    Team = apps.get_model('teams', 'Team')
    TeamTournamentRegistration = apps.get_model('teams', 'TeamTournamentRegistration')
    
    team = get_object_or_404(Team, slug=team_slug)
    registration = get_object_or_404(
        TeamTournamentRegistration,
        id=registration_id,
        team=team
    )
    
    profile = _get_user_profile(request.user)
    
    # Check if user is captain
    if profile != team.captain:
        return JsonResponse({
            'error': 'Only captain can cancel registration'
        }, status=403)
    
    # Can only cancel pending registrations
    if registration.status != 'pending':
        return JsonResponse({
            'error': f'Cannot cancel registration with status: {registration.status}'
        }, status=400)
    
    registration.status = 'cancelled'
    registration.save(update_fields=['status'])
    
    messages.success(request, "Tournament registration cancelled")
    
    return JsonResponse({
        'success': True,
        'message': 'Registration cancelled successfully'
    })


def team_ranking_view(request, game=None):
    """
    Team ranking leaderboard page.
    Shows rankings filtered by game and region.
    """
    # Get filters from query params
    game_filter = request.GET.get('game', game)
    region_filter = request.GET.get('region', '')
    page = request.GET.get('page', 1)
    
    # Get leaderboard
    leaderboard = TeamRankingCalculator.get_leaderboard(
        game=game_filter,
        region=region_filter,
        limit=100
    )
    
    # Paginate
    paginator = Paginator(leaderboard, 25)
    page_obj = paginator.get_page(page)
    
    # Get available games
    Team = apps.get_model('teams', 'Team')
    available_games = Team.objects.filter(
        is_active=True
    ).values_list('game', flat=True).distinct()
    
    # Get available regions
    available_regions = Team.objects.filter(
        is_active=True,
        region__isnull=False
    ).exclude(region='').values_list('region', flat=True).distinct()
    
    context = {
        'leaderboard': page_obj,
        'game_filter': game_filter,
        'region_filter': region_filter,
        'available_games': available_games,
        'available_regions': available_regions,
    }
    
    return render(request, 'teams/ranking_leaderboard.html', context)


def team_ranking_detail_view(request, team_slug):
    """
    Detailed ranking breakdown for a specific team.
    """
    Team = apps.get_model('teams', 'Team')
    
    team = get_object_or_404(Team, slug=team_slug)
    
    calculator = TeamRankingCalculator(team)
    
    # Get full calculation
    calculation = calculator.calculate_full_ranking()
    
    # Get rank position
    rank_info = calculator.get_rank_position(game=team.game)
    
    # Get breakdown if exists
    breakdown_obj = None
    if hasattr(team, 'ranking_breakdown'):
        breakdown_obj = team.ranking_breakdown
        detailed_breakdown = breakdown_obj.get_detailed_breakdown()
        recent_changes = breakdown_obj.get_recent_changes(limit=10)
    else:
        detailed_breakdown = None
        recent_changes = []
    
    # Get recent history
    TeamRankingHistory = apps.get_model('teams', 'TeamRankingHistory')
    history = TeamRankingHistory.objects.filter(
        team=team
    ).order_by('-created_at')[:20]
    
    # Get team achievements
    TeamAchievement = apps.get_model('teams', 'TeamAchievement')
    achievements = TeamAchievement.objects.filter(
        team=team
    ).select_related('tournament').order_by('-year', 'placement')
    
    context = {
        'team': team,
        'calculation': calculation,
        'rank_info': rank_info,
        'breakdown': detailed_breakdown,
        'recent_changes': recent_changes,
        'history': history,
        'achievements': achievements,
        'breakdown_obj': breakdown_obj,
    }
    
    return render(request, 'teams/ranking_detail.html', context)


@login_required
def team_tournaments_view(request, team_slug):
    """
    View all tournament registrations for a team.
    Shows past, current, and upcoming tournaments.
    """
    Team = apps.get_model('teams', 'Team')
    
    team = get_object_or_404(Team, slug=team_slug)
    
    profile = _get_user_profile(request.user)
    
    # Check if user is team member
    is_member = team.has_member(profile)
    is_captain = profile == team.captain
    
    if not is_member and not request.user.is_staff:
        messages.error(request, "You don't have permission to view team tournaments")
        return redirect('teams:detail', slug=team_slug)
    
    # Get registrations
    service = TournamentRegistrationService(team, None)
    registrations = service.get_team_registrations(team)
    
    # Separate by status
    pending_registrations = [r for r in registrations if r['status'] == 'pending']
    confirmed_registrations = [r for r in registrations if r['status'] in ['approved', 'confirmed']]
    cancelled_registrations = [r for r in registrations if r['status'] in ['cancelled', 'rejected']]
    
    # Get available tournaments for registration
    Tournament = apps.get_model('tournaments', 'Tournament')
    from django.utils import timezone
    
    available_tournaments = Tournament.objects.filter(
        game=team.game,
        status__in=['PUBLISHED', 'RUNNING'],
        reg_close_at__gt=timezone.now()
    ).exclude(
        id__in=[r['tournament']['id'] for r in registrations]
    )
    
    context = {
        'team': team,
        'pending_registrations': pending_registrations,
        'confirmed_registrations': confirmed_registrations,
        'cancelled_registrations': cancelled_registrations,
        'available_tournaments': available_tournaments,
        'is_captain': is_captain,
        'is_member': is_member,
    }
    
    return render(request, 'teams/tournaments_list.html', context)


@require_POST
def trigger_ranking_recalculation(request, team_slug):
    """
    Manually trigger ranking recalculation (admin or captain).
    """
    Team = apps.get_model('teams', 'Team')
    
    team = get_object_or_404(Team, slug=team_slug)
    
    profile = _get_user_profile(request.user)
    
    # Check permissions
    if profile != team.captain and not request.user.is_staff:
        return JsonResponse({
            'error': 'Permission denied'
        }, status=403)
    
    calculator = TeamRankingCalculator(team)
    result = calculator.update_ranking(
        reason="Manual recalculation triggered",
        admin_user=request.user if request.user.is_staff else None
    )
    
    if result['success']:
        return JsonResponse({
            'success': True,
            'message': 'Ranking recalculated successfully',
            'old_total': result['old_total'],
            'new_total': result['new_total'],
            'points_change': result['points_change']
        })
    else:
        return JsonResponse({
            'error': 'Recalculation failed'
        }, status=500)
