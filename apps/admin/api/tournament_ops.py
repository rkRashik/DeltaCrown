"""
Admin Tournament Operations API (Phase E Section 9)

Staff-only read-only inspection endpoints for tournament operations:
- Payment verification tracking
- Match state and winner tracking
- Dispute resolution tracking

All responses are IDs-only (no PII: no emails, names, phone numbers).
Reason fields use enum codes (not free text) for consistency.
Used for debugging, monitoring, and support operations.

Source: Phase E Section 9 requirements
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.tournaments.models import Tournament, Payment, Match, Dispute


@api_view(['GET'])
@permission_classes([IsAdminUser])
def tournament_payments(request, tournament_id):
    """
    GET /api/admin/tournaments/<id>/payments/
    
    List all payment verification statuses for a tournament.
    
    Response Shape (IDs only, no PII):
    {
        "tournament_id": 123,
        "payment_count": 50,
        "status_breakdown": {
            "pending": 5,
            "submitted": 10,
            "verified": 30,
            "rejected": 3,
            "refunded": 2
        },
        "payments": [
            {
                "payment_id": 456,
                "registration_id": 789,
                "payment_method": "bkash",
                "amount": "500.00",
                "status": "verified",
                "transaction_id": "TXN123456",
                "reference_number": "REF789",
                "submitted_at": "2025-01-15T10:30:00Z",
                "verified_at": "2025-01-15T11:00:00Z",
                "verified_by_id": 1
            }
        ]
    }
    
    Query Parameters:
    - status (optional): Filter by payment status (pending|submitted|verified|rejected|refunded)
    - limit (optional): Max results (default 100, max 500)
    - offset (optional): Pagination offset (default 0)
    
    Permissions: IsAdminUser (staff only)
    Rate Limit: None (internal admin use)
    
    Example:
        GET /api/admin/tournaments/123/payments/?status=verified&limit=50
    """
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Query parameters
    status_filter = request.query_params.get('status', None)
    limit = min(int(request.query_params.get('limit', 100)), 500)
    offset = int(request.query_params.get('offset', 0))
    
    # Build queryset
    payments_qs = Payment.objects.filter(
        registration__tournament=tournament
    ).select_related('registration')
    
    if status_filter:
        payments_qs = payments_qs.filter(status=status_filter)
    
    # Status breakdown (all payments regardless of filter)
    all_payments = Payment.objects.filter(registration__tournament=tournament)
    status_breakdown = {
        'pending': all_payments.filter(status=Payment.PENDING).count(),
        'submitted': all_payments.filter(status=Payment.SUBMITTED).count(),
        'verified': all_payments.filter(status=Payment.VERIFIED).count(),
        'rejected': all_payments.filter(status=Payment.REJECTED).count(),
        'refunded': all_payments.filter(status=Payment.REFUNDED).count(),
    }
    
    # Paginate
    total_count = payments_qs.count()
    payments_page = payments_qs.order_by('-submitted_at')[offset:offset+limit]
    
    # Serialize (IDs only, no PII)
    payments_data = [
        {
            'payment_id': p.id,
            'registration_id': p.registration_id,
            'payment_method': p.payment_method,
            'amount': str(p.amount),
            'status': p.status,
            'transaction_id': p.transaction_id,
            'reference_number': p.reference_number,
            'submitted_at': p.submitted_at.isoformat() if p.submitted_at else None,
            'verified_at': p.verified_at.isoformat() if p.verified_at else None,
            'verified_by_id': p.verified_by_id,
            'file_type': p.file_type,
            'has_payment_proof': bool(p.payment_proof),
        }
        for p in payments_page
    ]
    
    return Response({
        'tournament_id': tournament.id,
        'payment_count': total_count,
        'status_breakdown': status_breakdown,
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': total_count,
            'has_more': (offset + limit) < total_count,
        },
        'payments': payments_data,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def tournament_matches(request, tournament_id):
    """
    GET /api/admin/tournaments/<id>/matches/
    
    List all match states and winner tracking for a tournament.
    
    Response Shape (IDs only, no PII):
    {
        "tournament_id": 123,
        "match_count": 15,
        "state_breakdown": {
            "scheduled": 5,
            "check_in": 2,
            "ready": 1,
            "live": 3,
            "pending_result": 1,
            "completed": 2,
            "disputed": 1,
            "forfeit": 0,
            "cancelled": 0
        },
        "matches": [
            {
                "match_id": 789,
                "round_number": 1,
                "match_number": 2,
                "state": "completed",
                "bracket_id": 456,
                "participant1_id": 101,
                "participant2_id": 102,
                "participant1_score": 13,
                "participant2_score": 7,
                "winner_id": 101,
                "loser_id": 102,
                "scheduled_time": "2025-01-15T14:00:00Z",
                "started_at": "2025-01-15T14:05:00Z",
                "completed_at": "2025-01-15T15:30:00Z",
                "has_disputes": true,
                "dispute_count": 1
            }
        ]
    }
    
    Query Parameters:
    - state (optional): Filter by match state (scheduled|check_in|ready|live|pending_result|completed|disputed|forfeit|cancelled)
    - round (optional): Filter by round number
    - limit (optional): Max results (default 100, max 500)
    - offset (optional): Pagination offset (default 0)
    
    Permissions: IsAdminUser (staff only)
    Rate Limit: None (internal admin use)
    
    Example:
        GET /api/admin/tournaments/123/matches/?state=completed&round=1&limit=50
    """
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Query parameters
    state_filter = request.query_params.get('state', None)
    round_filter = request.query_params.get('round', None)
    limit = min(int(request.query_params.get('limit', 100)), 500)
    offset = int(request.query_params.get('offset', 0))
    
    # Build queryset
    matches_qs = Match.objects.filter(
        tournament=tournament
    ).select_related('bracket').prefetch_related('disputes')
    
    if state_filter:
        matches_qs = matches_qs.filter(state=state_filter)
    if round_filter:
        matches_qs = matches_qs.filter(round_number=int(round_filter))
    
    # State breakdown (all matches regardless of filter)
    all_matches = Match.objects.filter(tournament=tournament)
    state_breakdown = {
        'scheduled': all_matches.filter(state=Match.SCHEDULED).count(),
        'check_in': all_matches.filter(state=Match.CHECK_IN).count(),
        'ready': all_matches.filter(state=Match.READY).count(),
        'live': all_matches.filter(state=Match.LIVE).count(),
        'pending_result': all_matches.filter(state=Match.PENDING_RESULT).count(),
        'completed': all_matches.filter(state=Match.COMPLETED).count(),
        'disputed': all_matches.filter(state=Match.DISPUTED).count(),
        'forfeit': all_matches.filter(state=Match.FORFEIT).count(),
        'cancelled': all_matches.filter(state=Match.CANCELLED).count(),
    }
    
    # Paginate
    total_count = matches_qs.count()
    matches_page = matches_qs.order_by('round_number', 'match_number')[offset:offset+limit]
    
    # Serialize (IDs only, no PII)
    matches_data = [
        {
            'match_id': m.id,
            'round_number': m.round_number,
            'match_number': m.match_number,
            'state': m.state,
            'bracket_id': m.bracket_id,
            'participant1_id': m.participant1_id,
            'participant2_id': m.participant2_id,
            'participant1_score': m.participant1_score,
            'participant2_score': m.participant2_score,
            'winner_id': m.winner_id,
            'loser_id': m.loser_id,
            'scheduled_time': m.scheduled_time.isoformat() if m.scheduled_time else None,
            'started_at': m.started_at.isoformat() if m.started_at else None,
            'completed_at': m.completed_at.isoformat() if m.completed_at else None,
            'participant1_checked_in': m.participant1_checked_in,
            'participant2_checked_in': m.participant2_checked_in,
            'has_disputes': m.disputes.exists(),
            'dispute_count': m.disputes.count(),
        }
        for m in matches_page
    ]
    
    return Response({
        'tournament_id': tournament.id,
        'match_count': total_count,
        'state_breakdown': state_breakdown,
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': total_count,
            'has_more': (offset + limit) < total_count,
        },
        'matches': matches_data,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def tournament_disputes(request, tournament_id):
    """
    GET /api/admin/tournaments/<id>/disputes/
    
    List all dispute resolution tracking for a tournament.
    
    Response Shape (IDs only, no PII):
    {
        "tournament_id": 123,
        "dispute_count": 8,
        "status_breakdown": {
            "open": 2,
            "under_review": 3,
            "resolved": 2,
            "escalated": 1
        },
        "disputes": [
            {
                "dispute_id": 999,
                "match_id": 789,
                "round_number": 2,
                "match_number": 1,
                "reason_code": "SCORE_MISMATCH",
                "status": "resolved",
                "initiated_by_id": 101,
                "resolved_by_id": 1,
                "final_participant1_score": 13,
                "final_participant2_score": 10,
                "has_evidence_screenshot": true,
                "has_evidence_video": false,
                "created_at": "2025-01-15T15:45:00Z",
                "resolved_at": "2025-01-15T16:30:00Z"
            }
        ]
    }
    
    Query Parameters:
    - status (optional): Filter by dispute status (open|under_review|resolved|escalated)
    - reason_code (optional): Filter by reason code (SCORE_MISMATCH|NO_SHOW|CHEATING|TECHNICAL_ISSUE|OTHER)
    - limit (optional): Max results (default 100, max 500)
    - offset (optional): Pagination offset (default 0)
    
    Permissions: IsAdminUser (staff only)
    Rate Limit: None (internal admin use)
    
    Note:
        reason_code uses enum constants for consistency. Full prose descriptions
        are available in Django admin interface (/admin/tournaments/dispute/).
    
    Example:
        GET /api/admin/tournaments/123/disputes/?status=open&limit=50
    """
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Query parameters
    status_filter = request.query_params.get('status', None)
    reason_code_filter = request.query_params.get('reason_code', None)
    limit = min(int(request.query_params.get('limit', 100)), 500)
    offset = int(request.query_params.get('offset', 0))
    
    # Build queryset
    disputes_qs = Dispute.objects.filter(
        match__tournament=tournament
    ).select_related('match')
    
    if status_filter:
        disputes_qs = disputes_qs.filter(status=status_filter)
    if reason_code_filter:
        disputes_qs = disputes_qs.filter(reason=reason_code_filter)
    
    # Status breakdown (all disputes regardless of filter)
    all_disputes = Dispute.objects.filter(match__tournament=tournament)
    status_breakdown = {
        'open': all_disputes.filter(status=Dispute.OPEN).count(),
        'under_review': all_disputes.filter(status=Dispute.UNDER_REVIEW).count(),
        'resolved': all_disputes.filter(status=Dispute.RESOLVED).count(),
        'escalated': all_disputes.filter(status=Dispute.ESCALATED).count(),
    }
    
    # Paginate
    total_count = disputes_qs.count()
    disputes_page = disputes_qs.order_by('-created_at')[offset:offset+limit]
    
    # Serialize (IDs only, no PII - use reason_code enum instead of free text)
    disputes_data = [
        {
            'dispute_id': d.id,
            'match_id': d.match_id,
            'round_number': d.match.round_number,
            'match_number': d.match.match_number,
            'reason_code': d.reason.upper() if d.reason else 'OTHER',  # Normalize to enum
            'status': d.status,
            'initiated_by_id': d.initiated_by_id,
            'resolved_by_id': d.resolved_by_id,
            'final_participant1_score': d.final_participant1_score,
            'final_participant2_score': d.final_participant2_score,
            'has_evidence_screenshot': bool(d.evidence_screenshot),
            'has_evidence_video': bool(d.evidence_video_url),
            'created_at': d.created_at.isoformat(),
            'resolved_at': d.resolved_at.isoformat() if d.resolved_at else None,
        }
        for d in disputes_page
    ]
    
    return Response({
        'tournament_id': tournament.id,
        'dispute_count': total_count,
        'status_breakdown': status_breakdown,
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': total_count,
            'has_more': (offset + limit) < total_count,
        },
        'disputes': disputes_data,
    }, status=status.HTTP_200_OK)
