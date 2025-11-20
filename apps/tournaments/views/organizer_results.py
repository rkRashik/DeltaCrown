"""
Sprint 8: Organizer Result Approval Views

FE-T-015: Organizer Result Approval Dashboard

Handles organizer-side result confirmation and approval.
Backend API: apps/tournaments/api/result_views.py (confirm_result endpoint)
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.urls import reverse

from apps.tournaments.models import Match, Tournament
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker


class PendingResultsView(LoginRequiredMixin, ListView):
    """
    FE-T-015: Organizer Pending Results Dashboard
    
    Shows all matches in PENDING_RESULT state that need organizer confirmation.
    Includes side-by-side score comparison and approve/reject/override actions.
    
    URL: /tournaments/organizer/<slug>/pending-results/
    Template: tournaments/organizer/pending_results.html
    
    Access: Tournament organizers and staff only
    """
    
    model = Match
    template_name = 'tournaments/organizer/pending_results.html'
    context_object_name = 'pending_matches'
    paginate_by = 20
    
    def get_tournament(self):
        """Get tournament and validate organizer access."""
        slug = self.kwargs.get('slug')
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Check permissions
        checker = StaffPermissionChecker(tournament, self.request.user)
        if not checker.can_manage_brackets():
            raise PermissionError("You don't have permission to manage match results.")
        
        return tournament
    
    def get_queryset(self):
        """Get all matches awaiting confirmation."""
        tournament = self.get_tournament()
        
        return Match.objects.filter(
            tournament=tournament,
            state=Match.PENDING_RESULT,
            is_deleted=False
        ).select_related(
            'tournament',
            'tournament__game'
        ).order_by('-updated_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        
        context['tournament'] = tournament
        context['checker'] = StaffPermissionChecker(tournament, self.request.user)
        
        # Stats
        context['pending_count'] = self.get_queryset().count()
        context['total_matches'] = Match.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).count()
        
        return context


@login_required
@require_POST
def confirm_match_result(request, slug, match_id):
    """
    Confirm/approve match result as organizer.
    
    URL: POST /tournaments/organizer/<slug>/confirm-result/<match_id>/
    
    Accepts the result as submitted by participants.
    Backend API: POST /api/tournaments/matches/{id}/confirm-result/
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    match = get_object_or_404(
        Match.objects.select_related('tournament'),
        id=match_id,
        tournament=tournament,
        is_deleted=False
    )
    
    # Check permissions
    checker = StaffPermissionChecker(tournament, request.user)
    if not checker.can_manage_brackets():
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to confirm match results.'
        }, status=403)
    
    # Validate state
    if match.state != Match.PENDING_RESULT:
        return JsonResponse({
            'success': False,
            'error': f'Cannot confirm result for a {match.get_state_display()} match.'
        }, status=400)
    
    # TODO: Call backend API POST /api/tournaments/matches/{id}/confirm-result/
    # For now, mock the success response
    
    return JsonResponse({
        'success': True,
        'message': 'Match result confirmed successfully.',
        'match_id': match.id,
        'new_state': 'completed'
    })


@login_required
@require_POST
def reject_match_result(request, slug, match_id):
    """
    Reject match result and request resubmission.
    
    URL: POST /tournaments/organizer/<slug>/reject-result/<match_id>/
    
    Rejects the submitted result, requiring participants to resubmit.
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    match = get_object_or_404(
        Match.objects.select_related('tournament'),
        id=match_id,
        tournament=tournament,
        is_deleted=False
    )
    
    # Check permissions
    checker = StaffPermissionChecker(tournament, request.user)
    if not checker.can_manage_brackets():
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to reject match results.'
        }, status=403)
    
    # Validate state
    if match.state != Match.PENDING_RESULT:
        return JsonResponse({
            'success': False,
            'error': f'Cannot reject result for a {match.get_state_display()} match.'
        }, status=400)
    
    # Get rejection reason
    reason = request.POST.get('reason', '').strip()
    if not reason:
        return JsonResponse({
            'success': False,
            'error': 'Rejection reason is required.'
        }, status=400)
    
    # TODO: Implement rejection logic
    # - Reset match to LIVE state
    # - Clear scores
    # - Notify participants
    # - Store rejection reason in metadata
    
    return JsonResponse({
        'success': True,
        'message': 'Match result rejected. Participants will be notified to resubmit.',
        'match_id': match.id,
        'new_state': 'live'
    })


@login_required
@require_POST
def override_match_result(request, slug, match_id):
    """
    Override match result with organizer-specified scores.
    
    URL: POST /tournaments/organizer/<slug>/override-result/<match_id>/
    
    Organizer manually sets the final scores, bypassing participant submission.
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    match = get_object_or_404(
        Match.objects.select_related('tournament'),
        id=match_id,
        tournament=tournament,
        is_deleted=False
    )
    
    # Check permissions
    checker = StaffPermissionChecker(tournament, request.user)
    if not checker.can_manage_brackets():
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to override match results.'
        }, status=403)
    
    # Validate state
    if match.state not in [Match.PENDING_RESULT, Match.LIVE]:
        return JsonResponse({
            'success': False,
            'error': f'Cannot override result for a {match.get_state_display()} match.'
        }, status=400)
    
    # Extract scores
    try:
        participant1_score = int(request.POST.get('participant1_score', 0))
        participant2_score = int(request.POST.get('participant2_score', 0))
        reason = request.POST.get('reason', '').strip()
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid score values.'
        }, status=400)
    
    # Validate scores
    if participant1_score < 0 or participant2_score < 0:
        return JsonResponse({
            'success': False,
            'error': 'Scores cannot be negative.'
        }, status=400)
    
    if participant1_score == participant2_score:
        return JsonResponse({
            'success': False,
            'error': 'Tie games are not allowed.'
        }, status=400)
    
    if not reason:
        return JsonResponse({
            'success': False,
            'error': 'Override reason is required.'
        }, status=400)
    
    # TODO: Call backend API or use MatchService to update scores
    # - Update match scores
    # - Set state to COMPLETED
    # - Store override metadata (who, when, why)
    # - Update bracket progression
    
    return JsonResponse({
        'success': True,
        'message': 'Match result overridden successfully.',
        'match_id': match.id,
        'participant1_score': participant1_score,
        'participant2_score': participant2_score,
        'winner_id': match.participant1_id if participant1_score > participant2_score else match.participant2_id,
        'new_state': 'completed'
    })
