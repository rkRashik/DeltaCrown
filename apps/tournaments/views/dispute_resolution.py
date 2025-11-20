"""
Dispute Resolution Views for Tournament Organizers

Handles dispute resolution workflow including:
- Viewing dispute details with evidence
- Resolving disputes with multiple decision types
- Audit trail for dispute history

Related to:
- FE-T-017: Dispute History View
- FE-T-025: Dispute Resolution UI
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction

from apps.tournaments.models import Tournament
from apps.tournaments.models.match import Match, Dispute
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker

logger = logging.getLogger(__name__)


@require_POST
@transaction.atomic
def resolve_dispute(request, slug, dispute_id):
    """
    Resolve a dispute with one of several decision types.
    
    POST /tournaments/organizer/<slug>/resolve-dispute/<dispute_id>/
    
    Request Body (JSON):
    {
        "decision": "ACCEPT_A" | "ACCEPT_B" | "OVERRIDE" | "REJECT",
        "resolution_notes": "Reason for decision",
        "final_score_a": 10,  # Required if decision == OVERRIDE
        "final_score_b": 8    # Required if decision == OVERRIDE
    }
    
    Decision Types:
    - ACCEPT_A: Accept Participant A's claim, set them as winner
    - ACCEPT_B: Accept Participant B's claim, set them as winner
    - OVERRIDE: Manually set scores based on evidence review
    - REJECT: Reject dispute, keep original result
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    
    # Permission check
    if not checker.can_resolve_disputes():
        return JsonResponse({
            'status': 'error',
            'message': 'You do not have permission to resolve disputes.'
        }, status=403)
    
    dispute = get_object_or_404(Dispute, id=dispute_id, match__tournament=tournament)
    match = dispute.match
    
    # Parse request data
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    
    decision = data.get('decision')
    resolution_notes = data.get('resolution_notes', '').strip()
    
    if not decision:
        return JsonResponse({
            'status': 'error',
            'message': 'Decision type is required'
        }, status=400)
    
    if not resolution_notes:
        return JsonResponse({
            'status': 'error',
            'message': 'Resolution notes are required'
        }, status=400)
    
    # TODO: Replace with actual backend API call to /api/matches/{id}/resolve-dispute/
    # For now, implement logic directly
    
    try:
        if decision == 'ACCEPT_A':
            # Accept Participant A's claim - set A as winner
            match.winner_id = match.participant1_id
            match.loser_id = match.participant2_id
            match.status = 'COMPLETED'
            
        elif decision == 'ACCEPT_B':
            # Accept Participant B's claim - set B as winner
            match.winner_id = match.participant2_id
            match.loser_id = match.participant1_id
            match.status = 'COMPLETED'
            
        elif decision == 'OVERRIDE':
            # Manual score override
            final_score_a = data.get('final_score_a')
            final_score_b = data.get('final_score_b')
            
            if final_score_a is None or final_score_b is None:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Both scores are required for override decision'
                }, status=400)
            
            try:
                final_score_a = int(final_score_a)
                final_score_b = int(final_score_b)
            except (ValueError, TypeError):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Scores must be valid integers'
                }, status=400)
            
            if final_score_a < 0 or final_score_b < 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Scores cannot be negative'
                }, status=400)
            
            if final_score_a == final_score_b:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Scores cannot be tied'
                }, status=400)
            
            # Update scores and set winner
            match.participant1_score = final_score_a
            match.participant2_score = final_score_b
            
            if final_score_a > final_score_b:
                match.winner_id = match.participant1_id
                match.loser_id = match.participant2_id
            else:
                match.winner_id = match.participant2_id
                match.loser_id = match.participant1_id
            
            match.status = 'COMPLETED'
            
            # Store final scores in dispute record
            dispute.final_participant1_score = final_score_a
            dispute.final_participant2_score = final_score_b
            
        elif decision == 'REJECT':
            # Reject dispute, keep original result
            match.status = 'COMPLETED'
            
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid decision type: {decision}'
            }, status=400)
        
        # Update match
        match.save(update_fields=[
            'participant1_score', 'participant2_score',
            'winner_id', 'loser_id', 'status', 'updated_at'
        ])
        
        # Update dispute record
        dispute.status = Dispute.RESOLVED
        dispute.resolved_by_id = request.user.id
        dispute.resolved_at = timezone.now()
        dispute.resolution_notes = f"[{decision}] {resolution_notes}"
        dispute.save(update_fields=[
            'status', 'resolved_by_id', 'resolved_at', 'resolution_notes',
            'final_participant1_score', 'final_participant2_score', 'updated_at'
        ])
        
        logger.info(
            f"Dispute {dispute.id} resolved by {request.user.username} "
            f"with decision {decision} for match {match.id}"
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Dispute resolved successfully',
            'decision': decision,
            'match_status': match.status
        })
        
    except Exception as e:
        logger.error(f"Error resolving dispute {dispute_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while resolving the dispute'
        }, status=500)


@require_POST
def update_dispute_status(request, slug, dispute_id):
    """
    Update dispute status (e.g., mark as under review).
    
    POST /tournaments/organizer/<slug>/update-dispute-status/<dispute_id>/
    
    Request Body (JSON):
    {
        "status": "open" | "under_review" | "escalated"
    }
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    
    # Permission check
    if not checker.can_resolve_disputes():
        return JsonResponse({
            'status': 'error',
            'message': 'You do not have permission to update dispute status.'
        }, status=403)
    
    dispute = get_object_or_404(Dispute, id=dispute_id, match__tournament=tournament)
    
    # Parse request data
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    
    new_status = data.get('status')
    
    if new_status not in dict(Dispute.STATUS_CHOICES).keys():
        return JsonResponse({
            'status': 'error',
            'message': f'Invalid status: {new_status}'
        }, status=400)
    
    dispute.status = new_status
    dispute.save(update_fields=['status', 'updated_at'])
    
    logger.info(
        f"Dispute {dispute.id} status updated to {new_status} "
        f"by {request.user.username}"
    )
    
    return JsonResponse({
        'status': 'success',
        'message': f'Dispute status updated to {dispute.get_status_display()}',
        'new_status': new_status
    })
