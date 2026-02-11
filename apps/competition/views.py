"""
Competition App Views

Phase 3A-C: Thin views that delegate to services layer.
All business logic resides in MatchReportService and VerificationService.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.db.models import Q

from django.conf import settings
from apps.competition.models import MatchReport, GameRankingConfig, Challenge, Bounty
from apps.competition.services import MatchReportService, VerificationService, ChallengeService, BountyService
from apps.organizations.models import Team


@login_required
def match_report_form(request):
    """
    Display match report submission form (GET) or handle submission (POST)
    """
    # Get user's teams (teams where user is OWNER or ADMIN)
    user_teams = Team.objects.filter(
        vnext_memberships__user=request.user,
        vnext_memberships__status='ACTIVE',
        vnext_memberships__role__in=['OWNER', 'MANAGER']
    ).distinct()
    
    # Get all teams for opponent selection
    all_teams = Team.objects.filter(status='ACTIVE').order_by('name')
    
    # Get supported games
    games = GameRankingConfig.objects.all().order_by('game_id')
    
    # Pre-fill team1 if provided in query params
    team1_id = request.GET.get('team1')
    
    if request.method == 'POST':
        try:
            # Extract form data
            team1_id = request.POST.get('team1')
            team2_id = request.POST.get('team2')
            game_id = request.POST.get('game_id')
            result = request.POST.get('result')
            match_type = request.POST.get('match_type', 'RANKED')
            played_at_str = request.POST.get('played_at')
            evidence_url = request.POST.get('evidence_url', '').strip()
            evidence_file = request.FILES.get('evidence_file')
            
            # Parse played_at
            played_at = timezone.datetime.fromisoformat(played_at_str)
            if timezone.is_naive(played_at):
                played_at = timezone.make_aware(played_at)
            
            # Get team objects
            team1 = get_object_or_404(Team, id=team1_id)
            team2 = get_object_or_404(Team, id=team2_id)
            
            # Submit via service
            match_report = MatchReportService.submit_match_report(
                submitted_by=request.user,
                team1=team1,
                team2=team2,
                game_id=game_id,
                result=result,
                played_at=played_at,
                match_type=match_type,
                evidence_url=evidence_url if evidence_url else None,
                evidence_file=evidence_file,
            )
            
            messages.success(request, f"Match report submitted successfully! Awaiting confirmation from {team2.name}.")
            return redirect('competition:match_report_detail', match_id=match_report.id)
            
        except (PermissionDenied, ValidationError) as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Failed to submit match report: {str(e)}")
    
    context = {
        'user_teams': user_teams,
        'all_teams': all_teams,
        'games': games,
        'team1_id': team1_id,
    }
    return render(request, 'competition/match_report_form.html', context)


@login_required
def match_report_detail(request, match_id):
    """
    Display details of a specific match report
    """
    match_report = get_object_or_404(
        MatchReport.objects.select_related('team1', 'team2', 'submitted_by', 'verification'),
        id=match_id
    )
    
    # Check if user can confirm/dispute (must be team2 member)
    can_confirm_or_dispute = match_report.team2.memberships.filter(
        user=request.user,
        status='ACTIVE'
    ).exists()
    
    # Check if user is team1 member (reporter)
    is_reporter = match_report.team1.memberships.filter(
        user=request.user,
        status='ACTIVE'
    ).exists()
    
    context = {
        'match_report': match_report,
        'can_confirm_or_dispute': can_confirm_or_dispute and match_report.verification.status == 'PENDING',
        'is_reporter': is_reporter,
    }
    return render(request, 'competition/match_report_detail.html', context)


@login_required
def match_report_list(request):
    """
    List all match reports for user's teams
    """
    # Get user's teams
    user_teams = request.user.teams.filter(
        teammembership__status='ACTIVE'
    ).distinct()
    
    # Get all reports involving user's teams
    match_reports = MatchReport.objects.filter(
        Q(team1__in=user_teams) | Q(team2__in=user_teams)
    ).select_related('team1', 'team2', 'verification').order_by('-submitted_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        match_reports = match_reports.filter(verification__status=status_filter)
    
    context = {
        'match_reports': match_reports,
        'status_filter': status_filter,
    }
    return render(request, 'competition/match_report_list.html', context)


@login_required
def match_report_confirm(request, match_id):
    """
    Confirm a match report (POST only)
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method")
        return redirect('competition:match_report_detail', match_id=match_id)
    
    try:
        verification = VerificationService.confirm_match(request.user, match_id)
        messages.success(request, "Match confirmed successfully!")
    except (PermissionDenied, ValidationError) as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Failed to confirm match: {str(e)}")
    
    return redirect('competition:match_report_detail', match_id=match_id)


@login_required
def match_report_dispute(request, match_id):
    """
    Dispute a match report (POST only)
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method")
        return redirect('competition:match_report_detail', match_id=match_id)
    
    reason = request.POST.get('dispute_reason', '').strip()
    
    try:
        verification = VerificationService.dispute_match(request.user, match_id, reason)
        messages.success(request, "Match disputed successfully. Admins will review.")
    except (PermissionDenied, ValidationError) as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Failed to dispute match: {str(e)}")
    
    return redirect('competition:match_report_detail', match_id=match_id)


def ranking_about(request):
    """
    Display ranking system documentation (Phase 3A-D)
    
    Public page explaining how ranking scores are calculated,
    what counts (verified matches, tournaments), and how
    tiers and confidence levels work.
    
    This page is always available (no feature flag check) as it's
    documentation, but gracefully handles missing schema.
    """
    try:
        # Get all active game configs to show in docs
        game_configs = GameRankingConfig.objects.filter(is_active=True).order_by('game_name')
        
        # Get sample tier thresholds from first config
        sample_config = game_configs.first()
        tier_thresholds = sample_config.tier_thresholds if sample_config else {}
    except Exception:
        # Schema not ready or database error - show generic docs
        game_configs = []
        tier_thresholds = {
            'DIAMOND': 2000,
            'PLATINUM': 1200,
            'GOLD': 600,
            'SILVER': 250,
            'BRONZE': 100,
            'UNRANKED': 0
        }
    
    context = {
        'game_configs': game_configs,
        'tier_thresholds': tier_thresholds,
    }
    
    return render(request, 'competition/ranking_about.html', context)


# ═══════════════════════════════════════════════════════════════════════════
#  Challenge & Bounty Pages (Phase 10)
# ═══════════════════════════════════════════════════════════════════════════

def challenge_hub(request):
    """
    Public challenge hub — browse open challenges, filter by game.
    """
    from apps.games.models import Game

    game_slug = request.GET.get('game')
    game = None
    if game_slug:
        try:
            game = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            pass

    open_challenges = ChallengeService.get_open_challenges(game=game, limit=50)
    games = Game.objects.filter(is_active=True).order_by('name')

    context = {
        'challenges': open_challenges,
        'games': games,
        'selected_game': game,
        'page_title': 'Challenge Hub',
    }
    return render(request, 'competition/challenge_hub.html', context)


def challenge_detail_page(request, reference_code):
    """
    Challenge detail page.
    """
    challenge = get_object_or_404(
        Challenge.objects.select_related(
            'challenger_team', 'challenged_team', 'game', 'created_by'
        ),
        reference_code=reference_code,
    )

    context = {
        'challenge': challenge,
        'page_title': f'Challenge {challenge.reference_code}',
    }
    return render(request, 'competition/challenge_detail.html', context)


def bounty_board(request):
    """
    Public bounty board — browse active bounties, filter by game/type.
    """
    from apps.games.models import Game

    game_slug = request.GET.get('game')
    game = None
    if game_slug:
        try:
            game = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            pass

    active_bounties = BountyService.get_active_bounties(game=game, limit=50)
    games = Game.objects.filter(is_active=True).order_by('name')

    context = {
        'bounties': active_bounties,
        'games': games,
        'selected_game': game,
        'page_title': 'Bounty Board',
    }
    return render(request, 'competition/bounty_board.html', context)
