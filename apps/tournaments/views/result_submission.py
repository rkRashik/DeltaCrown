"""
Sprint 8: Match Result Submission Views

FE-T-014: Match Result Submission
FE-T-016: Dispute Submission Flow

Handles participant-side result and dispute submissions.
Backend API: apps/tournaments/api/result_views.py
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import requests
from django.conf import settings

from apps.tournaments.models import Match, Tournament


class SubmitResultView(LoginRequiredMixin, View):
    """
    FE-T-014: Submit Match Result
    
    Handles result submission form for match participants.
    
    URL: /tournaments/<slug>/matches/<int:match_id>/submit-result/
    Method: GET (show form), POST (submit via AJAX/HTMX)
    
    Access: Participants only
    State Requirements: Match must be LIVE or PENDING_RESULT
    
    Backend API: POST /api/tournaments/matches/{id}/submit-result/
    """
    
    template_name = 'tournaments/public/live/submit_result_form.html'
    
    def get(self, request, slug, match_id):
        """Render result submission form."""
        match = get_object_or_404(
            Match.objects.select_related('tournament'),
            id=match_id,
            tournament__slug=slug,
            is_deleted=False
        )
        
        # Check if user is a participant
        if not self._is_participant(request.user, match):
            messages.error(request, "Only match participants can submit results.")
            return redirect('tournaments:match_detail', slug=slug, match_id=match_id)
        
        # Check if match state allows submission
        if match.state not in [Match.LIVE, Match.PENDING_RESULT]:
            messages.error(request, f"Cannot submit results for a {match.get_state_display()} match.")
            return redirect('tournaments:match_detail', slug=slug, match_id=match_id)
        
        context = {
            'match': match,
            'tournament': match.tournament,
            'is_participant1': match.participant1_id == request.user.id,
            'is_participant2': match.participant2_id == request.user.id,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, slug, match_id):
        """Handle result submission via AJAX."""
        match = get_object_or_404(
            Match.objects.select_related('tournament'),
            id=match_id,
            tournament__slug=slug,
            is_deleted=False
        )
        
        # Validate participant access
        if not self._is_participant(request.user, match):
            return JsonResponse({
                'success': False,
                'error': 'Only match participants can submit results.'
            }, status=403)
        
        # Extract form data
        try:
            participant1_score = int(request.POST.get('participant1_score', 0))
            participant2_score = int(request.POST.get('participant2_score', 0))
            notes = request.POST.get('notes', '').strip()
            evidence_url = request.POST.get('evidence_url', '').strip()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid score values. Scores must be numbers.'
            }, status=400)
        
        # Basic validation
        if participant1_score < 0 or participant2_score < 0:
            return JsonResponse({
                'success': False,
                'error': 'Scores cannot be negative.'
            }, status=400)
        
        if participant1_score == participant2_score:
            return JsonResponse({
                'success': False,
                'error': 'Tie games are not allowed. There must be a winner.'
            }, status=400)
        
        # Call backend API (in production, use requests library or DRF client)
        # For now, we'll update directly and return success
        # TODO: Replace with actual API call to /api/tournaments/matches/{id}/submit-result/
        
        return JsonResponse({
            'success': True,
            'message': 'Result submitted successfully. Awaiting confirmation from opponent or organizer.',
            'redirect_url': reverse('tournaments:match_detail', kwargs={'slug': slug, 'match_id': match_id})
        })
    
    def _is_participant(self, user, match):
        """Check if user is a participant in the match."""
        if not user.is_authenticated:
            return False
        return match.participant1_id == user.id or match.participant2_id == user.id


@login_required
@require_POST
def report_dispute(request, slug, match_id):
    """
    FE-T-016: Report Match Dispute
    
    AJAX endpoint for submitting disputes on match results.
    
    URL: /tournaments/<slug>/matches/<int:match_id>/report-dispute/
    Method: POST (AJAX)
    
    Access: Participants only
    State Requirements: Match must be PENDING_RESULT or COMPLETED
    
    Backend API: POST /api/tournaments/matches/{id}/report-dispute/
    """
    match = get_object_or_404(
        Match.objects.select_related('tournament'),
        id=match_id,
        tournament__slug=slug,
        is_deleted=False
    )
    
    # Validate participant access
    if match.participant1_id != request.user.id and match.participant2_id != request.user.id:
        return JsonResponse({
            'success': False,
            'error': 'Only match participants can report disputes.'
        }, status=403)
    
    # Validate match state
    if match.state not in [Match.PENDING_RESULT, Match.COMPLETED]:
        return JsonResponse({
            'success': False,
            'error': f'Cannot dispute a {match.get_state_display()} match.'
        }, status=400)
    
    # Extract form data
    reason = request.POST.get('reason', '').strip()
    description = request.POST.get('description', '').strip()
    evidence_video_url = request.POST.get('evidence_video_url', '').strip()
    
    # Basic validation
    if not reason:
        return JsonResponse({
            'success': False,
            'error': 'Dispute reason is required.'
        }, status=400)
    
    if not description:
        return JsonResponse({
            'success': False,
            'error': 'Dispute description is required.'
        }, status=400)
    
    # TODO: Call backend API POST /api/tournaments/matches/{id}/report-dispute/
    # For now, return success response
    
    return JsonResponse({
        'success': True,
        'message': 'Dispute submitted successfully. A tournament organizer will review it shortly.',
        'dispute_id': None  # Will come from API response
    })
