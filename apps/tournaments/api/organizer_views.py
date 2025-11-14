"""
Organizer Dashboard API Views (Module 2.5 Step 2)

Backend-only REST API endpoints for tournament organizers.
Provides aggregated statistics and participant management.

Planning References:
- BACKEND_ONLY_BACKLOG.md lines 250-279 (Module 2.5)
- PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md lines 1366-1418 (Organizer Dashboard backend)
- PART_2.2_SERVICES_INTEGRATION.md (Service layer integration patterns)
- 02_TECHNICAL_STANDARDS.md lines 750-900 (DRF patterns, IDs-only discipline)

ADRs:
- ADR-001: Service Layer Pattern (business logic in DashboardService)
- ADR-002: API Design (REST conventions, pagination, filtering)
- ADR-004: IDs-only discipline (no nested objects in responses)
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from decimal import Decimal
from typing import Dict, Any, Optional

from apps.tournaments.services.dashboard_service import DashboardService
from apps.tournaments.models.tournament import Tournament


class ParticipantPagination(PageNumberPagination):
    """
    Custom pagination for participant breakdown endpoint.
    
    Source: 02_TECHNICAL_STANDARDS.md (API pagination patterns)
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organizer_stats(request):
    """
    GET /api/organizer/dashboard/stats/
    
    Returns organizer-wide summary statistics.
    
    Query Parameters:
        None
    
    Response (200 OK):
        {
            "organizer_id": 42,
            "total_tournaments": 15,
            "active_tournaments": 3,
            "total_participants": 247,
            "total_revenue": 125000.50,
            "average_rating": 4.8,
            "pending_actions": {
                "pending_payments": 5,
                "open_disputes": 2,
                "pending_approvals": 1
            }
        }
    
    Permissions:
        - Must be authenticated
        - Returns stats for requesting user as organizer
        - Staff can view any organizer's stats (future enhancement)
    
    Source:
        - BACKEND_ONLY_BACKLOG.md line 254
        - PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md lines 1404-1418
    """
    user = request.user
    
    try:
        stats = DashboardService.get_organizer_stats(organizer_id=user.id)
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to fetch organizer stats: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tournament_health(request, tournament_id: int):
    """
    GET /api/organizer/tournaments/{id}/health/
    
    Returns health metrics for a specific tournament.
    
    Path Parameters:
        tournament_id (int): Tournament ID
    
    Response (200 OK):
        {
            "tournament_id": 123,
            "payments": {
                "pending": 5,
                "verified": 12,
                "rejected": 1
            },
            "disputes": {
                "open": 2,
                "under_review": 1,
                "resolved": 8
            },
            "completion_rate": 0.75,
            "registration_progress": 0.85
        }
    
    Response (403 Forbidden):
        {
            "error": "User {user_id} is not authorized to view tournament {tournament_id} health"
        }
    
    Response (404 Not Found):
        {
            "error": "Tournament with id={tournament_id} not found"
        }
    
    Permissions:
        - Must be authenticated
        - Must be tournament organizer OR staff
    
    Source:
        - BACKEND_ONLY_BACKLOG.md line 255
        - PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md lines 1404-1418
    """
    user = request.user
    
    try:
        health = DashboardService.get_tournament_health(
            tournament_id=tournament_id,
            requesting_user_id=user.id
        )
        return Response(health, status=status.HTTP_200_OK)
        
    except Tournament.DoesNotExist:
        return Response(
            {"error": f"Tournament with id={tournament_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except PermissionDenied as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to fetch tournament health: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def participant_breakdown(request, tournament_id: int):
    """
    GET /api/organizer/tournaments/{id}/participants/
    
    Returns paginated participant list with filtering and ordering.
    
    Path Parameters:
        tournament_id (int): Tournament ID
    
    Query Parameters:
        game (str, optional): Filter by game slug
        payment_status (str, optional): Filter by payment status (pending/verified/rejected)
        check_in_status (str, optional): Filter by check-in (CHECKED_IN/NOT_CHECKED_IN)
        search (str, optional): Search by participant name
        ordering (str, optional): Sort field (±registration_date, ±participant_id)
        page (int, optional): Page number (default: 1)
        page_size (int, optional): Items per page (default: 20, max: 100)
    
    Response (200 OK):
        {
            "count": 47,
            "results": [
                {
                    "participant_id": 331,
                    "participant_type": "solo",
                    "registration_id": 89,
                    "registration_date": "2025-11-10T14:32:00Z",
                    "payment_status": "verified",
                    "check_in_status": "CHECKED_IN",
                    "match_stats": {
                        "matches_played": 5,
                        "wins": 3,
                        "losses": 2
                    }
                },
                ...
            ]
        }
    
    Response (403 Forbidden):
        {
            "error": "User {user_id} is not authorized to view tournament {tournament_id} participants"
        }
    
    Response (404 Not Found):
        {
            "error": "Tournament with id={tournament_id} not found"
        }
    
    Permissions:
        - Must be authenticated
        - Must be tournament organizer OR staff
    
    IDs-Only Discipline:
        - Returns participant_id, registration_id (integers)
        - No nested user/team objects
        - Frontend fetches details via separate endpoints
    
    Source:
        - BACKEND_ONLY_BACKLOG.md line 256
        - PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md lines 1404-1418
        - 02_TECHNICAL_STANDARDS.md (pagination, filtering patterns)
    """
    user = request.user
    
    # Extract query parameters
    filters = {}
    if request.query_params.get('game'):
        filters['game'] = request.query_params['game']
    if request.query_params.get('payment_status'):
        filters['payment_status'] = request.query_params['payment_status']
    if request.query_params.get('check_in_status'):
        filters['check_in_status'] = request.query_params['check_in_status']
    if request.query_params.get('search'):
        filters['search'] = request.query_params['search']
    
    ordering = request.query_params.get('ordering', '-registration_date')
    
    # Pagination params
    try:
        page_size = int(request.query_params.get('page_size', 20))
        page_size = min(page_size, 100)  # Max 100 items per page
    except (ValueError, TypeError):
        page_size = 20
    
    try:
        offset = int(request.query_params.get('page', 1))
        offset = max((offset - 1) * page_size, 0)
    except (ValueError, TypeError):
        offset = 0
    
    try:
        breakdown = DashboardService.get_participant_breakdown(
            tournament_id=tournament_id,
            requesting_user_id=user.id,
            filters=filters,
            ordering=ordering,
            limit=page_size,
            offset=offset
        )
        return Response(breakdown, status=status.HTTP_200_OK)
        
    except Tournament.DoesNotExist:
        return Response(
            {"error": f"Tournament with id={tournament_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except PermissionDenied as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to fetch participant breakdown: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
