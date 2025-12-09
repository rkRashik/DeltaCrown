"""
Organizer Staffing Views - Phase 7, Epic 7.3

API views for tournament staff and referee management.

Architecture:
- Uses TournamentOpsService façade only (no direct model access)
- Organizer-facing endpoints
- Request validation via serializers
- Permission checks for tournament organizers

Reference: Phase 7, Epic 7.3 - Staff & Referee Role System
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.tournament_ops.services.tournament_ops_service import TournamentOpsService
from apps.api.serializers.organizer_staffing_serializers import (
    StaffRoleSerializer,
    TournamentStaffAssignmentSerializer,
    AssignStaffRequestSerializer,
    MatchRefereeAssignmentSerializer,
    AssignRefereeRequestSerializer,
    AssignRefereeResponseSerializer,
    StaffLoadSerializer,
    RemoveStaffResponseSerializer,
)


# Service instance
tournament_ops = TournamentOpsService()


@extend_schema(
    summary="Get all available staff roles",
    description="Returns all staff roles with their capabilities",
    responses={200: StaffRoleSerializer(many=True)},
    tags=["Organizer - Staff Management"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_staff_roles(request):
    """
    Get all available staff roles.
    
    Returns:
        200: List of staff roles
        
    Reference: Phase 7, Epic 7.3 - Staff Roles Endpoint
    """
    roles = tournament_ops.get_staff_roles()
    
    # Convert DTOs to dict for serialization
    roles_data = [
        {
            'role_id': role.role_id,
            'name': role.name,
            'code': role.code,
            'description': role.description,
            'capabilities': role.capabilities,
            'is_referee_role': role.is_referee_role,
            'created_at': role.created_at,
            'updated_at': role.updated_at,
        }
        for role in roles
    ]
    
    serializer = StaffRoleSerializer(roles_data, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Get tournament staff assignments",
    description="Returns all staff assigned to a tournament",
    parameters=[
        OpenApiParameter(
            name='tournament_id',
            type=int,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Tournament ID'
        ),
        OpenApiParameter(
            name='stage_id',
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Filter by stage ID'
        ),
        OpenApiParameter(
            name='role_code',
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Filter by role code'
        ),
        OpenApiParameter(
            name='is_active',
            type=bool,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Filter by active status (default: true)'
        ),
    ],
    responses={
        200: TournamentStaffAssignmentSerializer(many=True),
        400: {"description": "Invalid parameters"}
    },
    tags=["Organizer - Staff Management"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tournament_staff(request):
    """
    Get all staff assigned to a tournament.
    
    Query params:
        - tournament_id (required)
        - stage_id (optional)
        - role_code (optional)
        - is_active (optional, default True)
        
    Returns:
        200: List of staff assignments
        400: Invalid parameters
        
    Reference: Phase 7, Epic 7.3 - Get Staff Endpoint
    """
    tournament_id = request.query_params.get('tournament_id')
    if not tournament_id:
        return Response(
            {'error': 'tournament_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        tournament_id = int(tournament_id)
    except ValueError:
        return Response(
            {'error': 'tournament_id must be an integer'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Optional filters
    stage_id = request.query_params.get('stage_id')
    if stage_id:
        try:
            stage_id = int(stage_id)
        except ValueError:
            return Response(
                {'error': 'stage_id must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    role_code = request.query_params.get('role_code')
    
    is_active_param = request.query_params.get('is_active', 'true')
    is_active = is_active_param.lower() in ('true', '1', 'yes') if is_active_param else True
    
    # Get staff assignments
    assignments = tournament_ops.get_tournament_staff(
        tournament_id=tournament_id,
        stage_id=stage_id,
        role_code=role_code,
        is_active=is_active
    )
    
    # Convert DTOs to dict
    assignments_data = [
        _staff_assignment_to_dict(assignment)
        for assignment in assignments
    ]
    
    serializer = TournamentStaffAssignmentSerializer(assignments_data, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Assign staff to tournament",
    description="Assigns a user with a specific role to a tournament",
    parameters=[
        OpenApiParameter(
            name='tournament_id',
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
            description='Tournament ID'
        ),
    ],
    request=AssignStaffRequestSerializer,
    responses={
        201: TournamentStaffAssignmentSerializer,
        400: {"description": "Validation error"},
    },
    tags=["Organizer - Staff Management"]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_staff(request, tournament_id):
    """
    Assign a staff member to a tournament.
    
    Args:
        tournament_id: Tournament ID (from URL)
        
    Request body:
        - user_id: User to assign
        - role_code: Role code
        - stage_id: Optional stage ID
        - notes: Optional notes
        
    Returns:
        201: Created staff assignment
        400: Validation error
        
    Reference: Phase 7, Epic 7.3 - Assign Staff Endpoint
    """
    serializer = AssignStaffRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        assignment = tournament_ops.assign_tournament_staff(
            tournament_id=tournament_id,
            user_id=serializer.validated_data['user_id'],
            role_code=serializer.validated_data['role_code'],
            assigned_by_user_id=request.user.id,
            stage_id=serializer.validated_data.get('stage_id'),
            notes=serializer.validated_data.get('notes', '')
        )
        
        assignment_data = _staff_assignment_to_dict(assignment)
        response_serializer = TournamentStaffAssignmentSerializer(assignment_data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Remove staff from tournament",
    description="Deactivates a staff assignment",
    parameters=[
        OpenApiParameter(
            name='assignment_id',
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
            description='Staff assignment ID'
        ),
    ],
    responses={
        200: RemoveStaffResponseSerializer,
        400: {"description": "Cannot remove staff with active duties"},
        404: {"description": "Assignment not found"},
    },
    tags=["Organizer - Staff Management"]
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_staff(request, assignment_id):
    """
    Remove a staff member from a tournament.
    
    Args:
        assignment_id: Staff assignment ID (from URL)
        
    Returns:
        200: Updated staff assignment (is_active=False)
        400: Cannot remove (active duties)
        404: Assignment not found
        
    Reference: Phase 7, Epic 7.3 - Remove Staff Endpoint
    """
    try:
        assignment = tournament_ops.remove_tournament_staff(
            assignment_id=assignment_id
        )
        
        response_data = {
            'assignment': _staff_assignment_to_dict(assignment),
            'message': f'Staff member {assignment.username} removed from tournament'
        }
        
        serializer = RemoveStaffResponseSerializer(response_data)
        return Response(serializer.data)
        
    except ValueError as e:
        error_msg = str(e)
        if 'not found' in error_msg.lower():
            return Response(
                {'error': error_msg},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {'error': error_msg},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Get match referee assignments",
    description="Returns all referees assigned to a match",
    parameters=[
        OpenApiParameter(
            name='match_id',
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
            description='Match ID'
        ),
    ],
    responses={200: MatchRefereeAssignmentSerializer(many=True)},
    tags=["Organizer - Referee Management"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_match_referees(request, match_id):
    """
    Get all referees assigned to a match.
    
    Args:
        match_id: Match ID (from URL)
        
    Returns:
        200: List of referee assignments
        
    Reference: Phase 7, Epic 7.3 - Get Match Referees Endpoint
    """
    assignments = tournament_ops.get_match_referees(match_id=match_id)
    
    assignments_data = [
        _referee_assignment_to_dict(assignment)
        for assignment in assignments
    ]
    
    serializer = MatchRefereeAssignmentSerializer(assignments_data, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Assign referee to match",
    description="Assigns a referee to a specific match",
    parameters=[
        OpenApiParameter(
            name='match_id',
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
            description='Match ID'
        ),
    ],
    request=AssignRefereeRequestSerializer,
    responses={
        201: AssignRefereeResponseSerializer,
        400: {"description": "Validation error"},
    },
    tags=["Organizer - Referee Management"]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_referee(request, match_id):
    """
    Assign a referee to a match.
    
    Args:
        match_id: Match ID (from URL)
        
    Request body:
        - staff_assignment_id: Staff assignment ID (must be referee)
        - is_primary: Whether this is primary referee
        - notes: Optional notes
        - check_load: Whether to check load (default True)
        
    Returns:
        201: Created referee assignment (with optional warning)
        400: Validation error
        
    Reference: Phase 7, Epic 7.3 - Assign Referee Endpoint
    """
    serializer = AssignRefereeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        assignment, warning = tournament_ops.assign_match_referee(
            match_id=match_id,
            staff_assignment_id=serializer.validated_data['staff_assignment_id'],
            assigned_by_user_id=request.user.id,
            is_primary=serializer.validated_data.get('is_primary', False),
            notes=serializer.validated_data.get('notes', ''),
            check_load=serializer.validated_data.get('check_load', True)
        )
        
        response_data = {
            'assignment': _referee_assignment_to_dict(assignment),
            'warning': warning
        }
        
        response_serializer = AssignRefereeResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Remove referee from match",
    description="Removes a referee assignment from a match",
    parameters=[
        OpenApiParameter(
            name='assignment_id',
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
            description='Referee assignment ID'
        ),
    ],
    responses={
        204: {"description": "Referee removed successfully"},
        404: {"description": "Assignment not found"},
    },
    tags=["Organizer - Referee Management"]
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def unassign_referee(request, assignment_id):
    """
    Remove a referee from a match.
    
    Args:
        assignment_id: Referee assignment ID (from URL)
        
    Returns:
        204: No content (success)
        404: Assignment not found
        
    Reference: Phase 7, Epic 7.3 - Unassign Referee Endpoint
    """
    try:
        tournament_ops.unassign_match_referee(
            referee_assignment_id=assignment_id
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    summary="Calculate staff workload",
    description="Returns workload summary for all staff in a tournament",
    parameters=[
        OpenApiParameter(
            name='tournament_id',
            type=int,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Tournament ID'
        ),
        OpenApiParameter(
            name='stage_id',
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Filter by stage ID'
        ),
    ],
    responses={
        200: StaffLoadSerializer(many=True),
        400: {"description": "Invalid parameters"}
    },
    tags=["Organizer - Staff Management"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_staff_load(request):
    """
    Calculate workload for all staff in a tournament.
    
    Query params:
        - tournament_id (required)
        - stage_id (optional)
        
    Returns:
        200: List of staff load summaries
        400: Invalid parameters
        
    Reference: Phase 7, Epic 7.3 - Staff Load Endpoint
    """
    tournament_id = request.query_params.get('tournament_id')
    if not tournament_id:
        return Response(
            {'error': 'tournament_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        tournament_id = int(tournament_id)
    except ValueError:
        return Response(
            {'error': 'tournament_id must be an integer'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    stage_id = request.query_params.get('stage_id')
    if stage_id:
        try:
            stage_id = int(stage_id)
        except ValueError:
            return Response(
                {'error': 'stage_id must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Calculate load
    loads = tournament_ops.calculate_staff_load(
        tournament_id=tournament_id,
        stage_id=stage_id
    )
    
    loads_data = [
        {
            'staff_assignment': _staff_assignment_to_dict(load.staff_assignment),
            'total_matches_assigned': load.total_matches_assigned,
            'upcoming_matches': load.upcoming_matches,
            'completed_matches': load.completed_matches,
            'concurrent_matches': load.concurrent_matches,
            'is_overloaded': load.is_overloaded,
            'load_percentage': load.load_percentage,
        }
        for load in loads
    ]
    
    serializer = StaffLoadSerializer(loads_data, many=True)
    return Response(serializer.data)


# Helper functions to convert DTOs to dict

def _staff_assignment_to_dict(assignment):
    """Convert TournamentStaffAssignmentDTO to dict."""
    return {
        'assignment_id': assignment.assignment_id,
        'tournament_id': assignment.tournament_id,
        'tournament_name': assignment.tournament_name,
        'user_id': assignment.user_id,
        'username': assignment.username,
        'user_email': assignment.user_email,
        'role': {
            'role_id': assignment.role.role_id,
            'name': assignment.role.name,
            'code': assignment.role.code,
            'description': assignment.role.description,
            'capabilities': assignment.role.capabilities,
            'is_referee_role': assignment.role.is_referee_role,
            'created_at': assignment.role.created_at,
            'updated_at': assignment.role.updated_at,
        },
        'is_active': assignment.is_active,
        'stage_id': assignment.stage_id,
        'stage_name': assignment.stage_name,
        'assigned_by_user_id': assignment.assigned_by_user_id,
        'assigned_by_username': assignment.assigned_by_username,
        'assigned_at': assignment.assigned_at,
        'notes': assignment.notes,
    }


def _referee_assignment_to_dict(assignment):
    """Convert MatchRefereeAssignmentDTO to dict."""
    return {
        'assignment_id': assignment.assignment_id,
        'match_id': assignment.match_id,
        'tournament_id': assignment.tournament_id,
        'stage_id': assignment.stage_id,
        'round_number': assignment.round_number,
        'match_number': assignment.match_number,
        'staff_assignment': _staff_assignment_to_dict(assignment.staff_assignment),
        'is_primary': assignment.is_primary,
        'assigned_by_user_id': assignment.assigned_by_user_id,
        'assigned_by_username': assignment.assigned_by_username,
        'assigned_at': assignment.assigned_at,
        'notes': assignment.notes,
    }
