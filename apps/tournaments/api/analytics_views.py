"""
Tournament Analytics API Views

Read-only analytics endpoints for tournament metrics and reporting.

Module: 5.4 - Analytics & Reports
Source Documents:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md#module-54
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md#AnalyticsService
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md (ADR-001: Service Layer)

Implements:
- Organizer analytics (tournament metrics)
- Participant analytics (player statistics)
- CSV export with streaming (memory-bounded)

Privacy Policy:
- Display names only (no emails, no usernames)
- Registration IDs preferred over user IDs in payloads

Performance:
- 500ms warning threshold for slow queries
- Streaming CSV to avoid memory limits
"""

import logging
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.analytics_service import AnalyticsService
from apps.tournaments.api.permissions import IsOrganizerOrAdmin
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organizer_analytics(request, tournament_id):
    """
    Get analytics metrics for tournament organizers.
    
    **Endpoint:** `GET /api/tournaments/analytics/organizer/<tournament_id>/`
    
    **Permissions:**
    - Tournament organizer OR admin user
    - Anonymous users: 401 Unauthorized
    - Authenticated but not authorized: 403 Forbidden
    
    **Response (200 OK):**
    ```json
    {
        "tournament_id": 123,
        "total_participants": 16,
        "checked_in_count": 14,
        "check_in_rate": 0.8750,
        "total_matches": 15,
        "completed_matches": 10,
        "disputed_matches": 1,
        "dispute_rate": 0.0667,
        "avg_match_duration_minutes": 32.5432,
        "prize_pool_total": "5000.00",
        "prizes_distributed": "3500.00",
        "prizes_awarded_count": 3,
        "registration_opened_at": "2025-10-01T08:00:00Z",
        "tournament_started_at": "2025-11-01T10:00:00Z",
        "concluded_at": "2025-11-01T18:30:00Z"
    }
    ```
    
    **Error Responses:**
    - 401: User not authenticated
    - 403: User is not organizer or admin
    - 404: Tournament not found
    - 500: Server error
    
    Module: 5.4 - Analytics & Reports
    """
    from django.http import Http404
    
    try:
        # Get tournament and check permissions
        tournament = get_object_or_404(Tournament, id=tournament_id)
        
        # IsOrganizerOrAdmin permission class handles the check
        # Manual check for clarity (redundant with decorator but explicit)
        if not (request.user.is_staff or request.user.is_superuser or 
                tournament.organizer_id == request.user.id):
            return JsonResponse(
                {'error': 'Permission denied. You must be the tournament organizer or an admin.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Calculate analytics using service layer
        analytics_data = AnalyticsService.calculate_organizer_analytics(tournament_id)
        
        logger.info(
            f"Organizer analytics retrieved: tournament={tournament_id}, "
            f"user={request.user.id}"
        )
        
        return JsonResponse(analytics_data, status=status.HTTP_200_OK)
        
    except Http404:
        logger.warning(f"Tournament not found: id={tournament_id}")
        return JsonResponse(
            {'error': f'Tournament with id {tournament_id} not found.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(
            f"Error retrieving organizer analytics: tournament={tournament_id}, "
            f"error={str(e)}",
            exc_info=True
        )
        return JsonResponse(
            {'error': 'An error occurred while retrieving analytics.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def participant_analytics(request, user_id):
    """
    Get analytics metrics for tournament participants.
    
    **Endpoint:** `GET /api/tournaments/analytics/participant/<user_id>/`
    
    **Permissions:**
    - Requesting user must be viewing their own stats OR be an admin
    - Anonymous users: 401 Unauthorized
    - Authenticated but viewing others' stats: 403 Forbidden
    
    **Response (200 OK):**
    ```json
    {
        "user_id": 456,
        "tournaments_played": 5,
        "tournaments_won": 1,
        "runner_up_count": 2,
        "third_place_count": 1,
        "best_placement": "1st",
        "total_matches": 23,
        "matches_won": 15,
        "matches_lost": 8,
        "win_rate": 0.6522,
        "total_prizes_won": "2500.00"
    }
    ```
    
    **Error Responses:**
    - 401: User not authenticated
    - 403: User trying to view another user's stats (not admin)
    - 404: User not found
    - 500: Server error
    
    Module: 5.4 - Analytics & Reports
    """
    from django.http import Http404
    
    try:
        # Permission check: self or admin only
        if not (request.user.is_staff or request.user.is_superuser or 
                request.user.id == user_id):
            return JsonResponse(
                {'error': 'Permission denied. You can only view your own statistics.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify user exists
        user = get_object_or_404(User, id=user_id)
        
        # Calculate analytics using service layer
        analytics_data = AnalyticsService.calculate_participant_analytics(user_id)
        
        logger.info(
            f"Participant analytics retrieved: user={user_id}, "
            f"requested_by={request.user.id}"
        )
        
        return JsonResponse(analytics_data, status=status.HTTP_200_OK)
        
    except Http404:
        logger.warning(f"User not found: id={user_id}")
        return JsonResponse(
            {'error': f'User with id {user_id} not found.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(
            f"Error retrieving participant analytics: user={user_id}, "
            f"error={str(e)}",
            exc_info=True
        )
        return JsonResponse(
            {'error': 'An error occurred while retrieving analytics.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_tournament_csv(request, tournament_id):
    """
    Export tournament data as CSV with streaming (memory-bounded).
    
    **Endpoint:** `GET /api/tournaments/analytics/export/<tournament_id>/?format=csv`
    
    **Permissions:**
    - Tournament organizer OR admin user
    - Anonymous users: 401 Unauthorized
    - Authenticated but not authorized: 403 Forbidden
    
    **Response (200 OK):**
    - Content-Type: text/csv; charset=utf-8
    - Content-Disposition: attachment; filename="tournament_<id>_export.csv"
    - Streaming iterator (memory-bounded)
    - UTF-8 BOM for Excel compatibility
    
    **CSV Columns (12):**
    1. registration_id
    2. participant_name (display name, no PII)
    3. team_name (if team registration)
    4. status
    5. checked_in
    6. placement
    7. matches_played
    8. matches_won
    9. win_rate
    10. prize_amount
    11. payment_status
    12. registered_at
    
    **Privacy Policy:**
    - Display names only (NO emails, NO usernames)
    - Registration IDs used instead of user IDs
    
    **Error Responses:**
    - 401: User not authenticated
    - 403: User is not organizer or admin
    - 404: Tournament not found
    - 500: Server error
    
    Module: 5.4 - Analytics & Reports
    """
    from django.http import Http404
    
    try:
        # Get tournament and check permissions
        tournament = get_object_or_404(Tournament, id=tournament_id)
        
        # IsOrganizerOrAdmin permission class handles the check
        # Manual check for clarity (redundant with decorator but explicit)
        if not (request.user.is_staff or request.user.is_superuser or 
                tournament.organizer_id == request.user.id):
            return JsonResponse(
                {'error': 'Permission denied. You must be the tournament organizer or an admin.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create streaming response with CSV generator
        csv_generator = AnalyticsService.export_tournament_csv(tournament_id)
        
        response = StreamingHttpResponse(
            csv_generator,
            content_type='text/csv; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="tournament_{tournament_id}_export.csv"'
        
        logger.info(
            f"CSV export started: tournament={tournament_id}, "
            f"user={request.user.id}"
        )
        
        return response
        
    except Http404:
        logger.warning(f"Tournament not found for CSV export: id={tournament_id}")
        return JsonResponse(
            {'error': f'Tournament with id {tournament_id} not found.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(
            f"Error exporting tournament CSV: tournament={tournament_id}, "
            f"error={str(e)}",
            exc_info=True
        )
        return JsonResponse(
            {'error': 'An error occurred while exporting tournament data.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
