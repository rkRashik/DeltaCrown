"""
Audit Log Views for Organizer API

Phase 7, Epic 7.5: Audit Log System
Provides REST API endpoints for audit log queries and export.

Endpoints:
    - GET /api/audit-logs/ - List audit logs with filters
    - GET /api/audit-logs/tournament/<id>/ - Tournament audit trail
    - GET /api/audit-logs/match/<id>/ - Match audit trail
    - GET /api/audit-logs/user/<id>/ - User audit trail
    - GET /api/audit-logs/export/ - Export audit logs as CSV
    - GET /api/audit-logs/activity/ - Recent activity feed
"""

import csv
from io import StringIO
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from apps.api.serializers.organizer_audit_log_serializers import (
    AuditLogSerializer,
    AuditLogFilterSerializer,
    AuditLogListResponseSerializer,
    AuditLogExportSerializer,
)


class AuditLogListView(APIView):
    """
    List audit logs with filtering and pagination.
    
    Phase 7, Epic 7.5: Organizer console audit log search.
    
    GET /api/audit-logs/
    
    Query Parameters:
        - user_id: Filter by user
        - action: Filter by exact action type
        - action_prefix: Filter by action prefix (e.g., 'result_')
        - tournament_id: Filter by tournament
        - match_id: Filter by match
        - start_date: Filter by timestamp >= start_date (ISO format)
        - end_date: Filter by timestamp <= end_date (ISO format)
        - has_state_change: Filter for state changes (true/false)
        - correlation_id: Filter by correlation ID
        - limit: Maximum results (default 100, max 1000)
        - offset: Pagination offset (default 0)
        - order_by: Sort field (default '-timestamp')
    
    Response:
        {
            "count": 42,
            "results": [
                {
                    "log_id": 123,
                    "username": "admin",
                    "action": "result_finalized",
                    "timestamp": "2025-12-10T10:30:00Z",
                    "tournament_id": 10,
                    "match_id": 42,
                    "before_state": {"status": "PENDING"},
                    "after_state": {"status": "FINALIZED"},
                    "has_state_change": true,
                    "changed_fields": ["status"]
                }
            ]
        }
    
    Architecture:
        - Uses TournamentOpsService façade only
        - No direct service or adapter imports
        - Returns DTOs serialized to JSON
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        List audit logs with filters.
        
        Args:
            request: DRF request with query parameters
            
        Returns:
            Response with paginated audit log list
        """
        # Validate query parameters
        filter_serializer = AuditLogFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response(
                filter_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert to DTO
        filters = filter_serializer.to_dto()
        
        # Get audit logs via façade
        from apps.tournament_ops.services import TournamentOpsService
        tournament_ops = TournamentOpsService()
        
        logs = tournament_ops.get_audit_logs(filters)
        total_count = tournament_ops.count_audit_logs(filters)
        
        # Serialize response
        log_serializers = [AuditLogSerializer.from_dto(log) for log in logs]
        response_data = {
            'count': total_count,
            'results': [s.data for s in log_serializers]
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class TournamentAuditTrailView(APIView):
    """
    Get audit trail for specific tournament.
    
    Phase 7, Epic 7.5: Per-tournament audit history.
    
    GET /api/audit-logs/tournament/<tournament_id>/
    
    Query Parameters:
        - limit: Maximum entries (default 100)
    
    Response:
        [
            {
                "log_id": 123,
                "username": "admin",
                "action": "result_finalized",
                ...
            }
        ]
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, tournament_id):
        """
        Get tournament audit trail.
        
        Args:
            request: DRF request
            tournament_id: Tournament ID
            
        Returns:
            Response with tournament audit logs
        """
        limit = int(request.query_params.get('limit', 100))
        
        # Get audit trail via façade
        from apps.tournament_ops.services import TournamentOpsService
        tournament_ops = TournamentOpsService()
        
        logs = tournament_ops.get_tournament_audit_trail(
            tournament_id=tournament_id,
            limit=limit
        )
        
        # Serialize
        log_serializers = [AuditLogSerializer.from_dto(log) for log in logs]
        
        return Response(
            [s.data for s in log_serializers],
            status=status.HTTP_200_OK
        )


class MatchAuditTrailView(APIView):
    """
    Get audit trail for specific match.
    
    Phase 7, Epic 7.5: Per-match audit history.
    
    GET /api/audit-logs/match/<match_id>/
    
    Query Parameters:
        - limit: Maximum entries (default 100)
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, match_id):
        """
        Get match audit trail.
        
        Args:
            request: DRF request
            match_id: Match ID
            
        Returns:
            Response with match audit logs
        """
        limit = int(request.query_params.get('limit', 100))
        
        # Get audit trail via façade
        from apps.tournament_ops.services import TournamentOpsService
        tournament_ops = TournamentOpsService()
        
        logs = tournament_ops.get_match_audit_trail(
            match_id=match_id,
            limit=limit
        )
        
        # Serialize
        log_serializers = [AuditLogSerializer.from_dto(log) for log in logs]
        
        return Response(
            [s.data for s in log_serializers],
            status=status.HTTP_200_OK
        )


class UserAuditTrailView(APIView):
    """
    Get audit trail for specific user.
    
    Phase 7, Epic 7.5: Per-user audit history.
    
    GET /api/audit-logs/user/<user_id>/
    
    Query Parameters:
        - limit: Maximum entries (default 100)
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        """
        Get user audit trail.
        
        Args:
            request: DRF request
            user_id: User ID
            
        Returns:
            Response with user audit logs
        """
        limit = int(request.query_params.get('limit', 100))
        
        # Get audit trail via façade
        from apps.tournament_ops.services import TournamentOpsService
        tournament_ops = TournamentOpsService()
        
        logs = tournament_ops.get_user_audit_trail(
            user_id=user_id,
            limit=limit
        )
        
        # Serialize
        log_serializers = [AuditLogSerializer.from_dto(log) for log in logs]
        
        return Response(
            [s.data for s in log_serializers],
            status=status.HTTP_200_OK
        )


class AuditLogExportView(APIView):
    """
    Export audit logs as CSV file.
    
    Phase 7, Epic 7.5: Compliance reporting / CSV export.
    
    GET /api/audit-logs/export/
    
    Query Parameters:
        Same as AuditLogListView (filtering parameters)
    
    Response:
        CSV file download with headers:
        - Log ID, User, Action, Timestamp, Tournament ID, Match ID,
          IP Address, Metadata, Before State, After State, Changed Fields
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Export audit logs as CSV.
        
        Args:
            request: DRF request with query parameters
            
        Returns:
            CSV file download response
        """
        # Validate query parameters
        filter_serializer = AuditLogFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response(
                filter_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert to DTO
        filters = filter_serializer.to_dto()
        
        # Get export data via façade
        from apps.tournament_ops.services import TournamentOpsService
        tournament_ops = TournamentOpsService()
        
        export_data = tournament_ops.export_audit_logs(filters)
        
        # Generate CSV
        output = StringIO()
        if export_data:
            # Get CSV headers from first row
            first_row = export_data[0].to_csv_row()
            fieldnames = list(first_row.keys())
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for row_dto in export_data:
                writer.writerow(row_dto.to_csv_row())
        
        # Create HTTP response with CSV
        csv_content = output.getvalue()
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_log_export.csv"'
        
        return response


class RecentActivityView(APIView):
    """
    Get recent audit activity for dashboard feed.
    
    Phase 7, Epic 7.5: Recent activity feed for organizer dashboard.
    
    GET /api/audit-logs/activity/
    
    Query Parameters:
        - tournament_id: Filter by tournament (optional)
        - user_id: Filter by user (optional)
        - limit: Maximum entries (default 20)
    
    Response:
        [
            {
                "log_id": 123,
                "username": "admin",
                "action": "result_finalized",
                "timestamp": "2025-12-10T10:30:00Z",
                ...
            }
        ]
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get recent audit activity.
        
        Args:
            request: DRF request with query parameters
            
        Returns:
            Response with recent audit log entries
        """
        tournament_id = request.query_params.get('tournament_id')
        user_id = request.query_params.get('user_id')
        limit = int(request.query_params.get('limit', 20))
        
        # Convert string IDs to integers
        if tournament_id:
            tournament_id = int(tournament_id)
        if user_id:
            user_id = int(user_id)
        
        # Get recent activity via façade
        from apps.tournament_ops.services import TournamentOpsService
        tournament_ops = TournamentOpsService()
        
        logs = tournament_ops.get_recent_audit_activity(
            tournament_id=tournament_id,
            user_id=user_id,
            limit=limit
        )
        
        # Serialize
        log_serializers = [AuditLogSerializer.from_dto(log) for log in logs]
        
        return Response(
            [s.data for s in log_serializers],
            status=status.HTTP_200_OK
        )


# Export views
__all__ = [
    'AuditLogListView',
    'TournamentAuditTrailView',
    'MatchAuditTrailView',
    'UserAuditTrailView',
    'AuditLogExportView',
    'RecentActivityView',
]
