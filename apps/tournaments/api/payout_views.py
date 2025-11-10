"""
Prize Payout & Refund API Views

Organizer/Admin endpoints for processing payouts and refunds.

Related Planning:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md#module-52
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md#section-6
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-001-service-layer

Module: apps.tournaments.api.payout_views
Implements: phase_5:module_5_2:milestone_3
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from apps.tournaments.models import Tournament
from apps.tournaments.services.payout_service import PayoutService
from apps.tournaments.api.payout_serializers import (
    PayoutRequestSerializer,
    RefundRequestSerializer,
    PayoutResponseSerializer,
    RefundResponseSerializer,
    ReconciliationResponseSerializer,
)
from apps.tournaments.api.permissions import IsOrganizerOrAdmin

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsOrganizerOrAdmin])
def process_payouts(request, tournament_id):
    """
    Process prize payouts for a completed tournament.
    
    POST /api/tournaments/{tournament_id}/payouts/
    
    Permissions: Organizer or Admin only
    
    Request Body:
        {
            "dry_run": false,
            "notes": "Optional processing notes"
        }
    
    Response (200 OK):
        {
            "tournament_id": 123,
            "created_transaction_ids": [10, 11, 12],
            "count": 3,
            "mode": "payout",
            "idempotent": true
        }
    
    Error Responses:
        400: Invalid distribution config or prize pool not set
        409: Tournament not COMPLETED or no TournamentResult
        500: Unexpected error
    """
    # Validate request
    serializer = PayoutRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    dry_run = serializer.validated_data.get('dry_run', False)
    notes = serializer.validated_data.get('notes', '')
    
    # Get tournament and verify permissions
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Check permissions (IsOrganizerOrAdmin handles this, but double-check for organizer)
    if not (request.user.is_staff or tournament.organizer == request.user):
        return Response(
            {"detail": "You must be the tournament organizer or an admin."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Dry run mode (validation only)
    if dry_run:
        try:
            # Validate preconditions without processing
            if tournament.status != Tournament.COMPLETED:
                return Response(
                    {
                        "detail": f"Tournament must be COMPLETED for payouts. Current status: {tournament.status}",
                        "error_code": "tournament_not_completed"
                    },
                    status=status.HTTP_409_CONFLICT
                )
            
            # Check for TournamentResult
            if not hasattr(tournament, 'result'):
                return Response(
                    {
                        "detail": "Tournament has no result record. Run winner determination first.",
                        "error_code": "no_tournament_result"
                    },
                    status=status.HTTP_409_CONFLICT
                )
            
            # Validate distribution exists
            if not tournament.prize_distribution or tournament.prize_distribution == {}:
                return Response(
                    {
                        "detail": "Tournament has no prize distribution configured.",
                        "error_code": "no_prize_distribution"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response(
                {
                    "tournament_id": tournament_id,
                    "dry_run": True,
                    "validation": "passed",
                    "message": "Payout processing would succeed."
                },
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            return Response(
                {"detail": str(e), "error_code": "validation_error"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Process payouts
    try:
        transaction_ids = PayoutService.process_payouts(
            tournament_id=tournament_id,
            processed_by=request.user
        )
        
        # Log success
        logger.info(
            f"Payouts processed for tournament {tournament_id} by {request.user.username}. "
            f"Created {len(transaction_ids)} transactions."
        )
        if notes:
            logger.info(f"Payout notes: {notes}")
        
        # Build response
        response_data = {
            "tournament_id": tournament_id,
            "created_transaction_ids": transaction_ids,
            "count": len(transaction_ids),
            "mode": "payout",
            "idempotent": True  # Service layer handles idempotency
        }
        
        response_serializer = PayoutResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    except ValidationError as e:
        error_msg = str(e)
        
        # Determine appropriate status code based on error message
        if "not found" in error_msg.lower():
            return Response(
                {"detail": error_msg, "error_code": "tournament_not_found"},
                status=status.HTTP_404_NOT_FOUND
            )
        elif "must be completed" in error_msg.lower() or "no result record" in error_msg.lower():
            return Response(
                {"detail": error_msg, "error_code": "tournament_not_completed"},
                status=status.HTTP_409_CONFLICT
            )
        else:
            return Response(
                {"detail": error_msg, "error_code": "validation_error"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Exception as e:
        logger.error(
            f"Unexpected error processing payouts for tournament {tournament_id}: {e}",
            exc_info=True
        )
        return Response(
            {"detail": "An unexpected error occurred.", "error_code": "internal_error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsOrganizerOrAdmin])
def process_refunds(request, tournament_id):
    """
    Process refunds for a cancelled tournament.
    
    POST /api/tournaments/{tournament_id}/refunds/
    
    Permissions: Organizer or Admin only
    
    Request Body:
        {
            "dry_run": false,
            "notes": "Optional processing notes"
        }
    
    Response (200 OK):
        {
            "tournament_id": 123,
            "created_transaction_ids": [20, 21, 22],
            "count": 3,
            "mode": "refund",
            "idempotent": true
        }
    
    Error Responses:
        400: Invalid request
        409: Tournament not CANCELLED
        500: Unexpected error
    """
    # Validate request
    serializer = RefundRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    dry_run = serializer.validated_data.get('dry_run', False)
    notes = serializer.validated_data.get('notes', '')
    
    # Get tournament and verify permissions
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Check permissions
    if not (request.user.is_staff or tournament.organizer == request.user):
        return Response(
            {"detail": "You must be the tournament organizer or an admin."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Dry run mode (validation only)
    if dry_run:
        try:
            # Validate preconditions without processing
            if tournament.status != Tournament.CANCELLED:
                return Response(
                    {
                        "detail": f"Tournament must be CANCELLED for refunds. Current status: {tournament.status}",
                        "error_code": "tournament_not_cancelled"
                    },
                    status=status.HTTP_409_CONFLICT
                )
            
            return Response(
                {
                    "tournament_id": tournament_id,
                    "dry_run": True,
                    "validation": "passed",
                    "message": "Refund processing would succeed."
                },
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            return Response(
                {"detail": str(e), "error_code": "validation_error"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Process refunds
    try:
        transaction_ids = PayoutService.process_refunds(
            tournament_id=tournament_id,
            processed_by=request.user
        )
        
        # Log success
        logger.info(
            f"Refunds processed for tournament {tournament_id} by {request.user.username}. "
            f"Created {len(transaction_ids)} transactions."
        )
        if notes:
            logger.info(f"Refund notes: {notes}")
        
        # Build response
        response_data = {
            "tournament_id": tournament_id,
            "created_transaction_ids": transaction_ids,
            "count": len(transaction_ids),
            "mode": "refund",
            "idempotent": True
        }
        
        response_serializer = RefundResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    except ValidationError as e:
        error_msg = str(e)
        
        # Determine appropriate status code
        if "not found" in error_msg.lower():
            return Response(
                {"detail": error_msg, "error_code": "tournament_not_found"},
                status=status.HTTP_404_NOT_FOUND
            )
        elif "must be cancelled" in error_msg.lower():
            return Response(
                {"detail": error_msg, "error_code": "tournament_not_cancelled"},
                status=status.HTTP_409_CONFLICT
            )
        else:
            return Response(
                {"detail": error_msg, "error_code": "validation_error"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Exception as e:
        logger.error(
            f"Unexpected error processing refunds for tournament {tournament_id}: {e}",
            exc_info=True
        )
        return Response(
            {"detail": "An unexpected error occurred.", "error_code": "internal_error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsOrganizerOrAdmin])
def verify_reconciliation(request, tournament_id):
    """
    Verify payout reconciliation for a tournament.
    
    GET /api/tournaments/{tournament_id}/payouts/verify/
    
    Permissions: Organizer or Admin only
    
    Response (200 OK):
        {
            "tournament_id": 123,
            "ok": true,
            "details": {
                "expected": {"1st": "500.00", "2nd": "300.00", "3rd": "200.00"},
                "actual": {"1st": "500.00", "2nd": "300.00", "3rd": "200.00"},
                "missing": [],
                "duplicates": []
            }
        }
    
    Error Responses:
        404: Tournament not found
        500: Unexpected error
    """
    # Get tournament and verify permissions
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Check permissions
    if not (request.user.is_staff or tournament.organizer == request.user):
        return Response(
            {"detail": "You must be the tournament organizer or an admin."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Call service method
        is_valid, report = PayoutService.verify_payout_reconciliation(tournament_id)
        
        # Transform report to match API contract
        response_data = {
            "tournament_id": tournament_id,
            "ok": is_valid,
            "details": {
                "expected": report.get('expected_placements', {}),
                "actual": report.get('completed_payouts', {}),
                "missing": report.get('missing_payouts', []),
                "amount_mismatches": report.get('amount_mismatches', []),
                "duplicates": report.get('duplicate_checks', []),
                "failed_transactions": report.get('failed_transactions', [])
            }
        }
        
        response_serializer = ReconciliationResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    except ValidationError as e:
        return Response(
            {"detail": str(e), "error_code": "validation_error"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.error(
            f"Unexpected error verifying reconciliation for tournament {tournament_id}: {e}",
            exc_info=True
        )
        return Response(
            {"detail": "An unexpected error occurred.", "error_code": "internal_error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
