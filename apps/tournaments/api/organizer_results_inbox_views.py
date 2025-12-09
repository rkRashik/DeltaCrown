"""
Epic 7.1: Organizer Results Inbox API Views

DRF API views for organizer results inbox endpoints.

Views:
1. OrganizerResultsInboxView - List results inbox items with filters
2. OrganizerResultsInboxBulkActionView - Bulk finalize/reject submissions

Planning References:
- ROADMAP_AND_EPICS_PART_4.md Epic 7.1 (Results Inbox & Queue Management)
- FRONTEND_DEVELOPER_SUPPORT_PART_5.md (Organizer Console specs)
- CLEANUP_AND_TESTING_PART_6.md §9.7 (Results inbox acceptance criteria)

Architecture:
- Uses TournamentOpsService façade (no direct service access)
- No ORM imports (service layer handles data access)
- IDs-only discipline (returns submission_id, match_id, tournament_id)
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.utils.dateparse import parse_datetime
from typing import Dict, Any, List, Optional

from apps.tournament_ops.services.tournament_ops_service import TournamentOpsService
from apps.tournaments.api.organizer_results_inbox_serializers import (
    OrganizerReviewItemAPISerializer,
    BulkActionRequestSerializer,
    BulkActionResponseSerializer,
)


class ResultsInboxPagination(PageNumberPagination):
    """
    Custom pagination for results inbox endpoint.
    
    Source: 02_TECHNICAL_STANDARDS.md (API pagination patterns)
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrganizerResultsInboxView(APIView):
    """
    GET /api/v1/organizer/results-inbox/
    
    List results inbox items for organizer with filters and sorting.
    
    Query Parameters:
        - tournament_id (int, optional): Filter by tournament
        - status (str, optional): Comma-separated status values (pending,disputed,confirmed,finalized,rejected)
        - dispute_status (str, optional): Comma-separated dispute status values (open,under_review,escalated,resolved_*,dismissed)
        - date_from (ISO date, optional): Filter submissions from this date
        - date_to (ISO date, optional): Filter submissions to this date
        - ordering (str, optional): Sort by field (priority, created_at, age) - default: priority
        - page (int, optional): Page number
        - page_size (int, optional): Items per page (default: 20, max: 100)
    
    Response (200 OK):
        {
            "count": 42,
            "next": "http://example.com/api/v1/organizer/results-inbox/?page=2",
            "previous": null,
            "results": [
                {
                    "submission_id": 123,
                    "match_id": 456,
                    "tournament_id": 789,
                    "tournament_name": "Summer Championship 2025",
                    "status": "pending",
                    "dispute_status": null,
                    "created_at": "2025-12-09T10:30:00Z",
                    "auto_confirm_deadline": "2025-12-10T10:30:00Z",
                    "is_overdue": false,
                    "priority": 85,
                    "age_in_hours": 12.5
                },
                ...
            ]
        }
    
    Permissions:
        - Must be authenticated
        - Returns items for requesting user as organizer
    
    Source:
        - ROADMAP_AND_EPICS_PART_4.md Epic 7.1
        - FRONTEND_DEVELOPER_SUPPORT_PART_5.md (Organizer Console)
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = ResultsInboxPagination
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TournamentOpsService()
    
    def get(self, request):
        """
        List results inbox items with filters.
        
        Uses TournamentOpsService.list_results_inbox_for_organizer() façade.
        """
        organizer_user_id = request.user.id
        
        # Build filters dict from query params
        filters = self._build_filters(request.query_params)
        
        # Get items from service
        try:
            items = self.service.list_results_inbox_for_organizer(
                organizer_user_id=organizer_user_id,
                filters=filters
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve results inbox: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Apply ordering
        ordering = request.query_params.get('ordering', 'priority')
        items = self._apply_ordering(items, ordering)
        
        # Paginate results
        paginator = self.pagination_class()
        paginated_items = paginator.paginate_queryset(items, request)
        
        # Serialize
        serializer_data = [
            OrganizerReviewItemAPISerializer.from_dto(item)
            for item in paginated_items
        ]
        
        return paginator.get_paginated_response(serializer_data)
    
    def _build_filters(self, query_params) -> Dict[str, Any]:
        """
        Build filters dict from query parameters.
        
        Args:
            query_params: Django QueryDict from request
            
        Returns:
            Filters dict for service layer
        """
        filters = {}
        
        # Tournament ID filter
        if 'tournament_id' in query_params:
            try:
                filters['tournament_id'] = int(query_params['tournament_id'])
            except ValueError:
                pass  # Ignore invalid tournament_id
        
        # Status filter (comma-separated)
        if 'status' in query_params:
            status_list = [s.strip() for s in query_params['status'].split(',')]
            filters['status'] = status_list
        
        # Dispute status filter (comma-separated)
        if 'dispute_status' in query_params:
            dispute_status_list = [s.strip() for s in query_params['dispute_status'].split(',')]
            filters['dispute_status'] = dispute_status_list
        
        # Date range filters
        if 'date_from' in query_params:
            date_from = parse_datetime(query_params['date_from'])
            if date_from:
                filters['date_from'] = date_from
        
        if 'date_to' in query_params:
            date_to = parse_datetime(query_params['date_to'])
            if date_to:
                filters['date_to'] = date_to
        
        return filters
    
    def _apply_ordering(self, items: List, ordering: str) -> List:
        """
        Apply ordering to items list.
        
        Args:
            items: List of OrganizerReviewItemDTO
            ordering: Ordering field (priority, created_at, age, -priority, -created_at, -age)
            
        Returns:
            Sorted list
        """
        reverse = ordering.startswith('-')
        field = ordering.lstrip('-')
        
        if field == 'priority':
            return sorted(items, key=lambda x: x.priority, reverse=(not reverse))
        elif field == 'created_at':
            return sorted(items, key=lambda x: x.created_at, reverse=reverse)
        elif field == 'age':
            return sorted(items, key=lambda x: x.age_in_hours(), reverse=(not reverse))
        else:
            # Default to priority ordering
            return sorted(items, key=lambda x: x.priority, reverse=True)


class OrganizerResultsInboxBulkActionView(APIView):
    """
    POST /api/v1/organizer/results-inbox/bulk-action/
    
    Perform bulk actions on results inbox items (finalize or reject).
    
    Request Body:
        {
            "action": "finalize" | "reject",
            "submission_ids": [1, 2, 3],
            "notes": "optional notes (required for reject)"
        }
    
    Response (200 OK):
        {
            "processed": 3,
            "failed": [
                {
                    "submission_id": 2,
                    "error": "Submission not found or already finalized"
                }
            ],
            "items": [
                {
                    "submission_id": 1,
                    "match_id": 456,
                    "tournament_id": 789,
                    "status": "finalized",
                    ...
                },
                {
                    "submission_id": 3,
                    "match_id": 457,
                    "tournament_id": 789,
                    "status": "finalized",
                    ...
                }
            ]
        }
    
    Response (400 BAD REQUEST):
        {
            "error": "Validation error message"
        }
    
    Permissions:
        - Must be authenticated
        - Must be organizer of the tournament(s)
    
    Source:
        - ROADMAP_AND_EPICS_PART_4.md Epic 7.1
        - FRONTEND_DEVELOPER_SUPPORT_PART_5.md (Organizer Console)
    """
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TournamentOpsService()
    
    def post(self, request):
        """
        Perform bulk action on submissions.
        
        Uses TournamentOpsService.bulk_finalize_submissions() or
        bulk_reject_submissions() façades.
        """
        # Validate request
        serializer = BulkActionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        action = serializer.validated_data['action']
        submission_ids = serializer.validated_data['submission_ids']
        notes = serializer.validated_data.get('notes', '')
        resolved_by_user_id = request.user.id
        
        # Perform bulk action
        try:
            if action == 'finalize':
                result = self.service.bulk_finalize_submissions(
                    submission_ids=submission_ids,
                    resolved_by_user_id=resolved_by_user_id
                )
            elif action == 'reject':
                result = self.service.bulk_reject_submissions(
                    submission_ids=submission_ids,
                    resolved_by_user_id=resolved_by_user_id,
                    notes=notes
                )
            else:
                return Response(
                    {'error': f'Invalid action: {action}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {'error': f'Bulk action failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Serialize response
        response_data = {
            'processed': result['processed'],
            'failed': result['failed'],
            'items': [
                OrganizerReviewItemAPISerializer.from_dto(item)
                for item in result['items']
            ]
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
