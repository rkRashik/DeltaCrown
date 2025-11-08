# Implements: Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md#section-3.4-match-app
# Implements: Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md#section-4.4-match-models
# Implements: Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-001
# Implements: Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-003
# Implements: Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-007

"""
Tournament API - Match Views

REST API for match management and scheduling.

Module: 4.3 - Match Management & Scheduling API
Phase: 4 - Tournament Live Operations

Source Documents:
- Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md (Match App Architecture)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Match Models & Service)
- Documents/ExecutionPlan/PHASE_4_IMPLEMENTATION_PLAN.md (Module 4.3 Scope)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-001, ADR-003, ADR-007)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-005: Security Model)

Architecture Decisions:
- ADR-001: Service layer pattern - All business logic in MatchService
- ADR-003: Soft delete support (queryset filtering)
- ADR-007: WebSocket integration for real-time updates
- ADR-005: Security model (JWT authentication, role-based access)

Endpoints:
- GET /api/matches/ - List matches (filterable, paginated)
- GET /api/matches/{id}/ - Retrieve match detail
- PATCH /api/matches/{id}/ - Update match (schedule, stream_url)
- POST /api/matches/{id}/start/ - Start match (→ LIVE state)
- POST /api/matches/bulk-schedule/ - Bulk schedule matches
- POST /api/matches/{id}/assign-coordinator/ - Assign coordinator
- PATCH /api/matches/{id}/lobby/ - Update lobby info
"""

import logging
from typing import Dict, Any

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from apps.tournaments.models import Match, Tournament
from apps.tournaments.services.match_service import MatchService
from apps.tournaments.api.match_serializers import (
    MatchListSerializer,
    MatchSerializer,
    MatchUpdateSerializer,
    LobbyInfoSerializer,
    BulkScheduleSerializer,
    CoordinatorAssignmentSerializer,
    MatchStartSerializer,
)
from apps.tournaments.api.permissions import (
    IsOrganizerOrAdmin,
    IsMatchParticipant,
)

# Module 2.4: Audit logging
from apps.tournaments.security.audit import audit_event, AuditAction

logger = logging.getLogger(__name__)


class MatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for tournament matches.
    
    Endpoints:
    - GET /api/matches/ - List all matches (filterable, paginated, ordered)
    - GET /api/matches/{id}/ - Match detail with full data
    - PATCH /api/matches/{id}/ - Update match (organizer only)
    - POST /api/matches/{id}/start/ - Start match (organizer only)
    - POST /api/matches/bulk-schedule/ - Bulk schedule (organizer only)
    - POST /api/matches/{id}/assign-coordinator/ - Assign coordinator (organizer only)
    - PATCH /api/matches/{id}/lobby/ - Update lobby info (organizer only)
    
    Permissions:
    - List/Retrieve: Public (authenticated or anonymous)
    - Update/Start/Bulk/Coordinator/Lobby: Organizer or Admin only
    - Participants can view their own matches (via IsMatchParticipant)
    
    Filtering:
    - tournament: Filter by tournament ID
    - bracket: Filter by bracket ID
    - state: Filter by match state
    - scheduled_time__gte: Filter by scheduled time (after)
    - scheduled_time__lte: Filter by scheduled time (before)
    
    Ordering:
    - created_at (default: newest first)
    - scheduled_time (matches with schedule first)
    - round_number (bracket progression)
    - state (by state priority)
    
    Module: 4.3 - Match Management & Scheduling API
    Source: PHASE_4_IMPLEMENTATION_PLAN.md Module 4.3
    """
    
    queryset = Match.objects.filter(is_deleted=False).select_related(
        'tournament',
        'bracket'
    )
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        'tournament': ['exact'],
        'bracket': ['exact'],
        'state': ['exact'],
        'scheduled_time': ['gte', 'lte'],
    }
    ordering_fields = ['created_at', 'scheduled_time', 'round_number', 'state']
    ordering = ['-created_at']  # Default: newest first
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return MatchListSerializer
        elif self.action == 'partial_update':
            return MatchUpdateSerializer
        elif self.action == 'start_match':
            return MatchStartSerializer
        elif self.action == 'bulk_schedule':
            return BulkScheduleSerializer
        elif self.action == 'assign_coordinator':
            return CoordinatorAssignmentSerializer
        elif self.action == 'update_lobby':
            return LobbyInfoSerializer
        return MatchSerializer
    
    def get_permissions(self):
        """
        Set permissions based on action.
        
        - List/Retrieve: Public (IsAuthenticatedOrReadOnly)
        - Update/Start/Bulk/Coordinator/Lobby: Organizer or Admin only
        """
        if self.action in ['partial_update', 'start_match', 'bulk_schedule', 
                           'assign_coordinator', 'update_lobby']:
            return [IsOrganizerOrAdmin()]
        elif self.action == 'retrieve':
            # Participants can view their own matches
            return [IsAuthenticatedOrReadOnly(), IsMatchParticipant()]
        return [IsAuthenticatedOrReadOnly()]
    
    # =========================
    # Standard CRUD
    # =========================
    
    def list(self, request, *args, **kwargs):
        """
        List matches with filtering, ordering, and pagination.
        
        GET /api/matches/
        
        Query Parameters:
        - tournament: Filter by tournament ID
        - bracket: Filter by bracket ID
        - state: Filter by match state
        - scheduled_time__gte: After date (ISO 8601)
        - scheduled_time__lte: Before date (ISO 8601)
        - ordering: Sort order (created_at, scheduled_time, round_number, state)
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20, max: 100)
        
        Returns:
        - 200 OK: Paginated match list
        
        Example:
            GET /api/matches/?tournament=123&state=LIVE&ordering=round_number
        """
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve match detail with full data.
        
        GET /api/matches/{id}/
        
        Returns:
        - 200 OK: Match detail
        - 404 Not Found: Match not found
        
        Permissions:
        - Public (authenticated or anonymous)
        - Match participants have guaranteed access
        """
        return super().retrieve(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Update match fields (scheduled_time, stream_url).
        
        PATCH /api/matches/{id}/
        
        Request Body:
        {
            "scheduled_time": "2025-11-15T14:00:00Z",  // optional
            "stream_url": "https://twitch.tv/..."     // optional
        }
        
        Permissions:
        - Organizer or Admin only
        
        Validation:
        - Cannot update completed/cancelled matches
        - scheduled_time must be in future
        
        Returns:
        - 200 OK: Match updated
        - 400 Bad Request: Validation error
        - 403 Forbidden: Not organizer/admin
        - 404 Not Found: Match not found
        
        Audit Log: Records schedule changes (Module 2.4)
        """
        match = self.get_object()
        
        # Audit log: match schedule update
        if 'scheduled_time' in request.data:
            audit_event(
                user=request.user,
                action=AuditAction.MATCH_SCHEDULE,
                meta={
                    'match_id': match.id,
                    'tournament_id': match.tournament_id,
                    'old_scheduled_time': match.scheduled_time.isoformat() if match.scheduled_time else None,
                    'new_scheduled_time': request.data['scheduled_time'],
                }
            )
        
        return super().partial_update(request, *args, **kwargs)
    
    # =========================
    # Match State Transition
    # =========================
    
    @action(detail=True, methods=['post'], url_path='start',
            permission_classes=[IsOrganizerOrAdmin])
    def start_match(self, request, pk=None):
        """
        Start match (transition to LIVE state via MatchService).
        
        POST /api/matches/{id}/start/
        
        Request Body: {}  (empty body)
        
        Permissions:
        - Organizer or Admin only
        
        Validation:
        - Match must be in READY state
        - Check-in must be complete (if enabled)
        
        Side Effects:
        - Match state → LIVE
        - started_at timestamp set
        - WebSocket broadcast: match_started event (Module 2.3)
        - Audit log: match started (Module 2.4)
        
        Returns:
        - 200 OK: Match started successfully
        - 400 Bad Request: Invalid state or validation error
        - 403 Forbidden: Not organizer/admin
        - 404 Not Found: Match not found
        
        Example Response:
        {
            "id": 123,
            "state": "LIVE",
            "started_at": "2025-11-15T14:05:00Z",
            ...
        }
        
        Source: PART_2.1_ARCHITECTURE_FOUNDATIONS.md Section 3.4 (State Machine)
        """
        match = self.get_object()
        
        # Validate via serializer
        serializer = self.get_serializer(data={}, context={'match': match})
        serializer.is_valid(raise_exception=True)
        
        try:
            # Start match via MatchService (ADR-001: Service layer pattern)
            # This will:
            # 1. Validate state transition (READY → LIVE)
            # 2. Set started_at timestamp
            # 3. Broadcast match_started WebSocket event (Module 2.3)
            with transaction.atomic():
                updated_match = MatchService.transition_to_live(match)
            
            # Module 2.4: Audit logging
            audit_event(
                user=request.user,
                action=AuditAction.MATCH_START,
                meta={
                    'match_id': match.id,
                    'tournament_id': match.tournament_id,
                    'round_number': match.round_number,
                    'match_number': match.match_number,
                    'participant1_id': match.participant1_id,
                    'participant2_id': match.participant2_id,
                }
            )
            
            # Return updated match
            output_serializer = MatchSerializer(updated_match)
            return Response(output_serializer.data, status=status.HTTP_200_OK)
            
        except (DjangoValidationError, ValueError) as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # =========================
    # Bulk Scheduling
    # =========================
    
    @action(detail=False, methods=['post'], url_path='bulk-schedule',
            permission_classes=[IsOrganizerOrAdmin])
    def bulk_schedule(self, request):
        """
        Bulk schedule multiple matches at once.
        
        POST /api/matches/bulk-schedule/
        
        Request Body:
        {
            "match_ids": [123, 124, 125],
            "scheduled_time": "2025-11-15T14:00:00Z"
        }
        
        Permissions:
        - Organizer or Admin only
        - User must be organizer of tournament containing all matches
        
        Validation:
        - All match IDs must exist
        - All matches must belong to same tournament
        - No duplicate IDs
        - No completed/cancelled matches
        - scheduled_time must be in future
        - Rate limit: max 100 matches per request
        
        Side Effects:
        - Updates scheduled_time for all matches
        - Recalculates check_in_deadline (if check-in enabled)
        - Audit log: bulk schedule (Module 2.4)
        
        Returns:
        - 200 OK: Matches scheduled successfully
        - 400 Bad Request: Validation error
        - 403 Forbidden: Not organizer/admin
        
        Example Response:
        {
            "scheduled_count": 3,
            "scheduled_time": "2025-11-15T14:00:00Z",
            "match_ids": [123, 124, 125]
        }
        
        Source: Module 4.3 Scope (bulk scheduling requirement)
        """
        # Validate via serializer (includes all business rules)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract validated data
        matches = serializer.validated_data['_matches']
        tournament = serializer.validated_data['_tournament']
        scheduled_time = serializer.validated_data['scheduled_time']
        match_ids = serializer.validated_data['match_ids']
        
        # Check permission (organizer of tournament)
        if not (request.user.is_staff or request.user.is_superuser or 
                tournament.organizer_id == request.user.id):
            return Response(
                {"detail": "You must be the tournament organizer or admin to bulk schedule matches."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Update all matches atomically
            with transaction.atomic():
                updated_count = 0
                for match in matches:
                    match.scheduled_time = scheduled_time
                    
                    # Recalculate check-in deadline if enabled (default 30 minutes before)
                    if tournament.enable_check_in:
                        check_in_minutes = 30  # Default check-in window
                        match.check_in_deadline = scheduled_time - timezone.timedelta(minutes=check_in_minutes)
                    
                    match.save(update_fields=['scheduled_time', 'check_in_deadline', 'updated_at'])
                    updated_count += 1
            
            # Module 2.4: Audit logging
            audit_event(
                user=request.user,
                action=AuditAction.MATCH_BULK_SCHEDULE,
                meta={
                    'tournament_id': tournament.id,
                    'match_ids': match_ids,
                    'scheduled_time': scheduled_time.isoformat(),
                    'count': updated_count,
                }
            )
            
            return Response(
                {
                    'scheduled_count': updated_count,
                    'scheduled_time': scheduled_time.isoformat(),
                    'match_ids': match_ids,
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(
                f"Bulk schedule failed: {e}",
                exc_info=True,
                extra={'tournament_id': tournament.id, 'match_ids': match_ids}
            )
            return Response(
                {"detail": f"Bulk schedule failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # =========================
    # Coordinator Assignment
    # =========================
    
    @action(detail=True, methods=['post'], url_path='assign-coordinator',
            permission_classes=[IsOrganizerOrAdmin])
    def assign_coordinator(self, request, pk=None):
        """
        Assign coordinator to match.
        
        POST /api/matches/{id}/assign-coordinator/
        
        Request Body:
        {
            "coordinator_id": 456
        }
        
        Permissions:
        - Organizer or Admin only
        
        Validation:
        - Coordinator user must exist
        - Match must not be completed/cancelled
        
        Side Effects:
        - Stores coordinator_id in lobby_info['coordinator_id']
        - Audit log: coordinator assignment (Module 2.4)
        
        Returns:
        - 200 OK: Coordinator assigned
        - 400 Bad Request: Validation error
        - 403 Forbidden: Not organizer/admin
        - 404 Not Found: Match or coordinator not found
        
        Example Response:
        {
            "id": 123,
            "lobby_info": {
                "coordinator_id": 456,
                "coordinator_assigned_at": "2025-11-15T14:00:00Z",
                ...
            },
            ...
        }
        
        Source: Module 4.3 Scope (coordinator assignment requirement)
        """
        match = self.get_object()
        
        # Validate via serializer
        serializer = self.get_serializer(data=request.data, context={'match': match})
        serializer.is_valid(raise_exception=True)
        
        coordinator_id = serializer.validated_data['coordinator_id']
        
        try:
            # Update lobby_info with coordinator assignment
            with transaction.atomic():
                if not match.lobby_info:
                    match.lobby_info = {}
                
                match.lobby_info['coordinator_id'] = coordinator_id
                match.lobby_info['coordinator_assigned_at'] = timezone.now().isoformat()
                match.lobby_info['coordinator_assigned_by'] = request.user.id
                
                match.save(update_fields=['lobby_info', 'updated_at'])
            
            # Module 2.4: Audit logging
            audit_event(
                user=request.user,
                action=AuditAction.MATCH_COORDINATOR_ASSIGN,
                meta={
                    'match_id': match.id,
                    'tournament_id': match.tournament_id,
                    'coordinator_id': coordinator_id,
                }
            )
            
            # Return updated match
            output_serializer = MatchSerializer(match)
            return Response(output_serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                f"Coordinator assignment failed: {e}",
                exc_info=True,
                extra={'match_id': match.id, 'coordinator_id': coordinator_id}
            )
            return Response(
                {"detail": f"Coordinator assignment failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # =========================
    # Lobby Info Management
    # =========================
    
    @action(detail=True, methods=['patch'], url_path='lobby',
            permission_classes=[IsOrganizerOrAdmin])
    def update_lobby(self, request, pk=None):
        """
        Update lobby_info JSONB field with validation.
        
        PATCH /api/matches/{id}/lobby/
        
        Request Body (game-specific):
        VALORANT:
        {
            "room_code": "VAL123",
            "region": "NA",
            "map": "Bind"  // optional
        }
        
        MLBB:
        {
            "room_id": "12345678",
            "room_password": "pass123",
            "draft_mode": "ranked"  // optional
        }
        
        EFOOTBALL:
        {
            "match_id": "EF456789",
            "lobby_code": "LB123"  // optional
        }
        
        PUBGM:
        {
            "room_id": "987654",
            "room_password": "pubg123",
            "map": "Erangel",
            "mode": "TPP"
        }
        
        Permissions:
        - Organizer or Admin only
        
        Validation:
        - At least one lobby identifier required
        - Schema validated via LobbyInfoSerializer
        - Match must not be completed/cancelled
        
        Side Effects:
        - Updates lobby_info JSONB field (merge with existing)
        - Audit log: lobby info update (Module 2.4)
        
        Returns:
        - 200 OK: Lobby info updated
        - 400 Bad Request: Validation error
        - 403 Forbidden: Not organizer/admin
        - 404 Not Found: Match not found
        
        Example Response:
        {
            "id": 123,
            "lobby_info": {
                "room_code": "VAL123",
                "region": "NA",
                "map": "Bind",
                "updated_at": "2025-11-15T14:00:00Z",
                "updated_by": 456
            },
            ...
        }
        
        Source: PART_2.2_SERVICES_INTEGRATION.md Section 4.4 (lobby_info JSONB)
        """
        match = self.get_object()
        
        # Check match state
        if match.state in [Match.COMPLETED, Match.CANCELLED, Match.FORFEIT]:
            return Response(
                {"detail": f"Cannot update lobby info for match in state: {match.get_state_display()}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate via serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Merge lobby info (preserve existing keys)
            with transaction.atomic():
                if not match.lobby_info:
                    match.lobby_info = {}
                
                # Update with new data (merge, not replace)
                lobby_data = serializer.validated_data
                match.lobby_info.update(lobby_data)
                
                # Add metadata
                match.lobby_info['updated_at'] = timezone.now().isoformat()
                match.lobby_info['updated_by'] = request.user.id
                
                match.save(update_fields=['lobby_info', 'updated_at'])
            
            # Module 2.4: Audit logging
            audit_event(
                user=request.user,
                action=AuditAction.MATCH_LOBBY_UPDATE,
                meta={
                    'match_id': match.id,
                    'tournament_id': match.tournament_id,
                    'lobby_fields_updated': list(lobby_data.keys()),
                }
            )
            
            # Return updated match
            output_serializer = MatchSerializer(match)
            return Response(output_serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                f"Lobby info update failed: {e}",
                exc_info=True,
                extra={'match_id': match.id}
            )
            return Response(
                {"detail": f"Lobby info update failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
