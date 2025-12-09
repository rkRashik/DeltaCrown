"""
Match Operations API Views - Phase 7, Epic 7.4

DRF views for Match Operations Command Center (MOCC).

Architecture:
- Uses TournamentOpsService façade only
- No direct model access
- Permission checks in service layer

Reference: Phase 7, Epic 7.4 - Match Operations API
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tournament_ops.services import TournamentOpsService
from apps.api.serializers.organizer_match_ops_serializers import (
    MatchOpsActionResultSerializer,
    MatchModeratorNoteSerializer,
    MatchTimelineEventSerializer,
    MatchOpsDashboardItemSerializer,
    MarkMatchLiveRequestSerializer,
    PauseMatchRequestSerializer,
    ResumeMatchRequestSerializer,
    ForceCompleteMatchRequestSerializer,
    AddMatchNoteRequestSerializer,
    OverrideMatchResultRequestSerializer,
)


tournament_ops = TournamentOpsService()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_match_live(request):
    """
    Mark a match as LIVE (in progress).
    
    POST /api/organizer/match-ops/mark-live/
    
    Request Body:
        {
            "match_id": int,
            "tournament_id": int
        }
    
    Response:
        MatchOpsActionResultSerializer
    
    Permissions:
        - User must be tournament staff with can_modify_matches
    
    Reference: Phase 7, Epic 7.4 - Live Match Control
    """
    serializer = MarkMatchLiveRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = tournament_ops.mark_match_live(
            match_id=serializer.validated_data['match_id'],
            tournament_id=serializer.validated_data['tournament_id'],
            operator_user_id=request.user.id
        )
        
        response_serializer = MatchOpsActionResultSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pause_match(request):
    """
    Pause a live match.
    
    POST /api/organizer/match-ops/pause/
    
    Request Body:
        {
            "match_id": int,
            "tournament_id": int,
            "reason": str (optional)
        }
    
    Response:
        MatchOpsActionResultSerializer
    
    Permissions:
        - User must be tournament staff with can_pause
    
    Reference: Phase 7, Epic 7.4 - Match Control
    """
    serializer = PauseMatchRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = tournament_ops.pause_match(
            match_id=serializer.validated_data['match_id'],
            tournament_id=serializer.validated_data['tournament_id'],
            operator_user_id=request.user.id,
            reason=serializer.validated_data.get('reason')
        )
        
        response_serializer = MatchOpsActionResultSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resume_match(request):
    """
    Resume a paused match.
    
    POST /api/organizer/match-ops/resume/
    
    Request Body:
        {
            "match_id": int,
            "tournament_id": int
        }
    
    Response:
        MatchOpsActionResultSerializer
    
    Permissions:
        - User must be tournament staff with can_resume
    
    Reference: Phase 7, Epic 7.4 - Match Control
    """
    serializer = ResumeMatchRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = tournament_ops.resume_match(
            match_id=serializer.validated_data['match_id'],
            tournament_id=serializer.validated_data['tournament_id'],
            operator_user_id=request.user.id
        )
        
        response_serializer = MatchOpsActionResultSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def force_complete_match(request):
    """
    Force-complete a match (admin action).
    
    POST /api/organizer/match-ops/force-complete/
    
    Request Body:
        {
            "match_id": int,
            "tournament_id": int,
            "reason": str (required),
            "result_data": object (optional)
        }
    
    Response:
        MatchOpsActionResultSerializer
    
    Permissions:
        - User must be tournament staff with can_force_complete
    
    Reference: Phase 7, Epic 7.4 - Admin Operations
    """
    serializer = ForceCompleteMatchRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = tournament_ops.force_complete_match(
            match_id=serializer.validated_data['match_id'],
            tournament_id=serializer.validated_data['tournament_id'],
            operator_user_id=request.user.id,
            reason=serializer.validated_data['reason'],
            result_data=serializer.validated_data.get('result_data')
        )
        
        response_serializer = MatchOpsActionResultSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_match_note(request):
    """
    Add a moderator note to a match.
    
    POST /api/organizer/match-ops/add-note/
    
    Request Body:
        {
            "match_id": int,
            "tournament_id": int,
            "content": str
        }
    
    Response:
        MatchModeratorNoteSerializer
    
    Permissions:
        - User must be tournament staff with can_add_note
    
    Reference: Phase 7, Epic 7.4 - Staff Communication
    """
    serializer = AddMatchNoteRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        note = tournament_ops.add_match_note(
            match_id=serializer.validated_data['match_id'],
            tournament_id=serializer.validated_data['tournament_id'],
            author_user_id=request.user.id,
            content=serializer.validated_data['content']
        )
        
        response_serializer = MatchModeratorNoteSerializer(note)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_match_timeline(request, match_id):
    """
    Get aggregated timeline of match events.
    
    GET /api/organizer/match-ops/timeline/<match_id>/
    
    Query Parameters:
        limit: int (default 50)
    
    Response:
        List[MatchTimelineEventSerializer]
    
    Reference: Phase 7, Epic 7.4 - Match Timeline
    """
    limit = int(request.query_params.get('limit', 50))
    
    try:
        timeline = tournament_ops.get_match_timeline(
            match_id=match_id,
            limit=limit
        )
        
        serializer = MatchTimelineEventSerializer(timeline, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def override_match_result(request):
    """
    Override match result (admin action).
    
    POST /api/organizer/match-ops/override-result/
    
    Request Body:
        {
            "match_id": int,
            "tournament_id": int,
            "new_result_data": object,
            "reason": str
        }
    
    Response:
        MatchOpsActionResultSerializer
    
    Permissions:
        - User must be tournament staff with can_override_result
    
    Reference: Phase 7, Epic 7.4 - Result Override
    """
    serializer = OverrideMatchResultRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = tournament_ops.override_match_result(
            match_id=serializer.validated_data['match_id'],
            tournament_id=serializer.validated_data['tournament_id'],
            operator_user_id=request.user.id,
            new_result_data=serializer.validated_data['new_result_data'],
            reason=serializer.validated_data['reason']
        )
        
        response_serializer = MatchOpsActionResultSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_operations_dashboard(request, tournament_id):
    """
    Get match operations dashboard for tournament.
    
    GET /api/organizer/match-ops/dashboard/<tournament_id>/
    
    Query Parameters:
        status_filter: str (optional - LIVE, PENDING, etc.)
    
    Response:
        List[MatchOpsDashboardItemSerializer]
    
    Reference: Phase 7, Epic 7.4 - Operations Dashboard
    """
    status_filter = request.query_params.get('status_filter')
    
    try:
        dashboard = tournament_ops.view_match_operations_dashboard(
            tournament_id=tournament_id,
            user_id=request.user.id,
            status_filter=status_filter
        )
        
        serializer = MatchOpsDashboardItemSerializer(dashboard, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )
