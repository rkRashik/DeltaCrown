"""
Organizer Match Scheduling Views - Phase 7, Epic 7.2

DRF views for organizer manual scheduling workflows.

Architecture:
- Uses TournamentOpsService façade (no direct service imports)
- Organizer-only permissions (tournament_organizer or admin)
- Returns scheduling items, slots, and bulk operation results

Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.api.serializers.organizer_scheduling_serializers import (
    MatchSchedulingItemSerializer,
    ManualSchedulingRequestSerializer,
    BulkShiftRequestSerializer,
    SchedulingSlotSerializer,
    BulkShiftResultSerializer,
    SchedulingAssignmentResponseSerializer,
)
from apps.tournament_ops.services.tournament_ops_service import TournamentOpsService


class OrganizerSchedulingView(APIView):
    """
    Organizer manual scheduling endpoints.
    
    GET: List matches requiring scheduling
    POST: Manually assign a match to a time slot
    
    Permissions: tournament_organizer or admin
    
    Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        List matches requiring scheduling.
        
        Query params:
            - tournament_id: Filter by tournament (optional)
            - stage_id: Filter by stage (optional)
            - unscheduled_only: Only unscheduled matches (optional, default false)
            - with_conflicts: Only matches with conflicts (optional, default false)
            
        Returns:
            200: List of MatchSchedulingItemDTO objects
            400: Invalid query parameters
            403: Not a tournament organizer
        """
        # Check organizer permissions (simplified for now)
        # In production, verify user is organizer of tournament
        if not (request.user.is_staff or self._is_tournament_organizer(request.user)):
            return Response(
                {'error': 'Must be tournament organizer or admin'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Parse query params
        tournament_id = request.query_params.get('tournament_id')
        stage_id = request.query_params.get('stage_id')
        unscheduled_only = request.query_params.get('unscheduled_only', 'false').lower() == 'true'
        with_conflicts = request.query_params.get('with_conflicts', 'false').lower() == 'true'
        
        # Validate IDs if provided
        try:
            if tournament_id:
                tournament_id = int(tournament_id)
            if stage_id:
                stage_id = int(stage_id)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid tournament_id or stage_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build filters
        filters = {
            'unscheduled_only': unscheduled_only,
            'with_conflicts': with_conflicts,
        }
        
        # Get scheduling items via TournamentOpsService
        service = TournamentOpsService()
        try:
            matches = service.list_matches_for_scheduling(
                tournament_id=tournament_id,
                stage_id=stage_id,
                filters=filters
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Serialize response
        serializer = MatchSchedulingItemSerializer(matches, many=True)
        return Response({
            'count': len(matches),
            'matches': serializer.data
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """
        Manually assign a match to a time slot.
        
        Request body:
            - match_id: int (required)
            - scheduled_time: datetime (required)
            - skip_conflict_check: bool (optional, default false)
            
        Returns:
            200: Assignment successful with conflicts warnings
            400: Invalid request data
            403: Not a tournament organizer
            404: Match not found
        """
        # Check organizer permissions
        if not (request.user.is_staff or self._is_tournament_organizer(request.user)):
            return Response(
                {'error': 'Must be tournament organizer or admin'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate request data
        serializer = ManualSchedulingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract validated data
        match_id = serializer.validated_data['match_id']
        scheduled_time = serializer.validated_data['scheduled_time']
        skip_conflict_check = serializer.validated_data.get('skip_conflict_check', False)
        
        # Schedule match via TournamentOpsService
        service = TournamentOpsService()
        try:
            result = service.schedule_match_manually(
                match_id=match_id,
                scheduled_time=scheduled_time,
                assigned_by_user_id=request.user.id,
                skip_conflict_check=skip_conflict_check
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Serialize response
        response_serializer = SchedulingAssignmentResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    def _is_tournament_organizer(self, user) -> bool:
        """
        Check if user is a tournament organizer.
        
        In production, this would check tournament-specific permissions.
        For now, simplified to staff check.
        """
        # TODO: Implement proper tournament organizer check
        return user.is_staff


class OrganizerBulkShiftView(APIView):
    """
    Organizer bulk shift endpoint.
    
    POST: Bulk shift all matches in a stage by a time delta
    
    Permissions: tournament_organizer or admin
    
    Reference: Phase 7, Epic 7.2 - Bulk Operations
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Bulk shift all scheduled matches in a stage.
        
        Request body:
            - stage_id: int (required)
            - delta_minutes: int (required, ±10080 max)
            
        Returns:
            200: Bulk shift successful with results
            400: Invalid request data
            403: Not a tournament organizer
            500: Bulk shift failed
        """
        # Check organizer permissions
        if not (request.user.is_staff or self._is_tournament_organizer(request.user)):
            return Response(
                {'error': 'Must be tournament organizer or admin'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate request data
        serializer = BulkShiftRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract validated data
        stage_id = serializer.validated_data['stage_id']
        delta_minutes = serializer.validated_data['delta_minutes']
        
        # Bulk shift via TournamentOpsService
        service = TournamentOpsService()
        try:
            result = service.bulk_shift_matches(
                stage_id=stage_id,
                delta_minutes=delta_minutes,
                assigned_by_user_id=request.user.id
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Serialize response
        result_serializer = BulkShiftResultSerializer(result)
        return Response(result_serializer.data, status=status.HTTP_200_OK)
    
    def _is_tournament_organizer(self, user) -> bool:
        """Check if user is a tournament organizer."""
        return user.is_staff


class OrganizerSchedulingSlotsView(APIView):
    """
    Organizer scheduling slots endpoint.
    
    GET: Generate available time slots for a stage
    
    Permissions: tournament_organizer or admin
    
    Reference: Phase 7, Epic 7.2 - Time Slot Generation
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Generate available scheduling slots for a stage.
        
        Query params:
            - stage_id: int (required)
            - slot_duration_minutes: int (optional, uses game default)
            - interval_minutes: int (optional, default 15)
            
        Returns:
            200: List of SchedulingSlotDTO objects
            400: Invalid query parameters
            403: Not a tournament organizer
        """
        # Check organizer permissions
        if not (request.user.is_staff or self._is_tournament_organizer(request.user)):
            return Response(
                {'error': 'Must be tournament organizer or admin'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Parse query params
        stage_id = request.query_params.get('stage_id')
        slot_duration_minutes = request.query_params.get('slot_duration_minutes')
        interval_minutes = request.query_params.get('interval_minutes', '15')
        
        # Validate required params
        if not stage_id:
            return Response(
                {'error': 'stage_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse and validate
        try:
            stage_id = int(stage_id)
            if slot_duration_minutes:
                slot_duration_minutes = int(slot_duration_minutes)
            else:
                slot_duration_minutes = None
            interval_minutes = int(interval_minutes)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid parameter values'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate slots via TournamentOpsService
        service = TournamentOpsService()
        try:
            slots = service.generate_scheduling_slots(
                stage_id=stage_id,
                slot_duration_minutes=slot_duration_minutes,
                interval_minutes=interval_minutes
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Serialize response
        serializer = SchedulingSlotSerializer(slots, many=True)
        return Response({
            'count': len(slots),
            'slots': serializer.data
        }, status=status.HTTP_200_OK)
    
    def _is_tournament_organizer(self, user) -> bool:
        """Check if user is a tournament organizer."""
        return user.is_staff
