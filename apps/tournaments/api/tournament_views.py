"""
Tournament API - ViewSet for Tournament CRUD

DRF ViewSet implementing full CRUD operations for tournaments.

Module: 2.1 - Tournament Creation & Management (Backend Only)
Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Tournament Service)
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md (API Standards)

Endpoints:
- GET    /api/tournaments/              List tournaments (public, filterable)
- POST   /api/tournaments/              Create tournament (authenticated)
- GET    /api/tournaments/{id}/         Retrieve tournament detail (public)
- PATCH  /api/tournaments/{id}/         Update tournament (organizer/staff, DRAFT only)
- PUT    /api/tournaments/{id}/         Full update (organizer/staff, DRAFT only)
- POST   /api/tournaments/{id}/publish/ Publish tournament (organizer/staff)
- POST   /api/tournaments/{id}/cancel/  Cancel tournament (organizer/staff)

Architecture Decisions:
- ADR-001: Service Layer Pattern - ViewSet delegates to TournamentService
- ADR-002: API Design Patterns - RESTful, consistent responses
- ADR-006: Permission System - IsAuthenticatedOrReadOnly for list/retrieve
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db.models import Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.api.tournament_serializers import (
    TournamentListSerializer,
    TournamentDetailSerializer,
    TournamentCreateSerializer,
    TournamentUpdateSerializer,
    TournamentPublishSerializer,
    TournamentCancelSerializer,
)
from apps.tournaments.services.tournament_service import TournamentService


class TournamentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for tournament CRUD operations.
    
    Permissions:
    - List/Retrieve: Public (no authentication required)
    - Create: Authenticated users (becomes organizer)
    - Update: Organizer or staff only (DRAFT status only)
    - Publish/Cancel: Organizer or staff only
    
    Filters:
    - status: Filter by tournament status (draft, published, live, etc.)
    - game: Filter by game ID
    - organizer: Filter by organizer user ID
    - search: Search name, description
    
    Ordering:
    - created_at (default: newest first)
    - tournament_start
    - prize_pool
    - participant_count
    """
    
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'game', 'organizer', 'format', 'participation_type', 'is_official']
    search_fields = ['name', 'description', 'game__name']
    ordering_fields = ['created_at', 'tournament_start', 'prize_pool', 'registration_start']
    ordering = ['-created_at']  # Default: newest first
    
    def get_queryset(self):
        """
        Get base queryset with optimized queries.
        
        - Excludes soft-deleted tournaments
        - Select related: game, organizer (for detail views)
        - Annotate: participant_count (for list views)
        - Filter: Hide DRAFT tournaments unless user is organizer/staff
        """
        qs = Tournament.objects.filter(is_deleted=False)
        
        # Select related for performance
        qs = qs.select_related('game', 'organizer')
        
        # Annotate participant count
        qs = qs.annotate(
            participant_count=Count(
                'registrations',
                filter=Q(registrations__status='confirmed')
            )
        )
        
        # Hide DRAFT tournaments unless user is organizer or staff
        user = self.request.user
        if not user.is_authenticated or not user.is_staff:
            # Anonymous or regular users: hide DRAFT tournaments unless organizer
            if user.is_authenticated:
                qs = qs.filter(
                    Q(status__in=['published', 'registration_open', 'registration_closed', 'live', 'completed', 'archived'])
                    | Q(organizer=user)
                )
            else:
                # Anonymous: only show public statuses
                qs = qs.filter(
                    status__in=['published', 'registration_open', 'registration_closed', 'live', 'completed', 'archived']
                )
        
        # Staff can see all tournaments (no additional filter)
        
        return qs
    
    def get_serializer_class(self):
        """
        Return appropriate serializer for each action.
        
        - list: TournamentListSerializer (lightweight)
        - retrieve: TournamentDetailSerializer (full fields)
        - create: TournamentCreateSerializer (input validation)
        - update/partial_update: TournamentUpdateSerializer (partial updates)
        - publish: TournamentPublishSerializer (action)
        - cancel: TournamentCancelSerializer (action with reason)
        """
        if self.action == 'list':
            return TournamentListSerializer
        elif self.action == 'create':
            return TournamentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TournamentUpdateSerializer
        elif self.action == 'publish':
            return TournamentPublishSerializer
        elif self.action == 'cancel':
            return TournamentCancelSerializer
        else:
            return TournamentDetailSerializer
    
    def perform_create(self, serializer):
        """
        Create tournament with current user as organizer.
        
        Delegates to TournamentService.create_tournament() via serializer.
        """
        serializer.save()
    
    def perform_update(self, serializer):
        """
        Update tournament (DRAFT only, organizer/staff only).
        
        Delegates to TournamentService.update_tournament() via serializer.
        Permission check is done in the service layer.
        """
        serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrReadOnly])
    def publish(self, request, pk=None):
        """
        Publish tournament (DRAFT → PUBLISHED/REGISTRATION_OPEN).
        
        POST /api/tournaments/{id}/publish/
        
        Permissions:
        - Organizer or staff only
        
        State Transitions:
        - DRAFT → PUBLISHED (if registration_start > now)
        - DRAFT → REGISTRATION_OPEN (if registration_start <= now)
        
        Returns:
        - 200: Tournament published successfully
        - 400: Validation error (invalid status, incomplete config)
        - 403: Permission denied (not organizer/staff)
        - 404: Tournament not found
        """
        tournament = self.get_object()
        
        # Check permission (organizer or staff)
        if tournament.organizer != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Only the organizer or staff can publish this tournament'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Publish via serializer (delegates to TournamentService)
        serializer = self.get_serializer(tournament, data={})
        serializer.is_valid(raise_exception=True)
        published_tournament = serializer.save()
        
        # Return detail serializer response
        response_serializer = TournamentDetailSerializer(published_tournament)
        return Response(
            {
                'message': f'Tournament published successfully (status: {published_tournament.get_status_display()})',
                'tournament': response_serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrReadOnly])
    def cancel(self, request, pk=None):
        """
        Cancel tournament (soft delete).
        
        POST /api/tournaments/{id}/cancel/
        Body: {"reason": "Optional cancellation reason"}
        
        Permissions:
        - Organizer or staff only
        
        State Transitions:
        - Any status (except COMPLETED/ARCHIVED) → CANCELLED
        
        Side Effects:
        - Soft deletes tournament (is_deleted=True)
        - Creates audit version with cancellation reason
        - TODO: Notify participants, process refunds, cancel matches
        
        Returns:
        - 200: Tournament cancelled successfully
        - 400: Validation error (COMPLETED/ARCHIVED cannot be cancelled)
        - 403: Permission denied (not organizer/staff)
        - 404: Tournament not found
        """
        tournament = self.get_object()
        
        # Check permission (organizer or staff)
        if tournament.organizer != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Only the organizer or staff can cancel this tournament'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cancel via serializer (delegates to TournamentService)
        serializer = self.get_serializer(tournament, data=request.data)
        serializer.is_valid(raise_exception=True)
        cancelled_tournament = serializer.save()
        
        # Return detail serializer response
        response_serializer = TournamentDetailSerializer(cancelled_tournament)
        return Response(
            {
                'message': 'Tournament cancelled successfully',
                'tournament': response_serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    def list(self, request, *args, **kwargs):
        """
        List tournaments with filters.
        
        GET /api/tournaments/?status=published&game=1&search=valorant
        
        Returns paginated list of tournaments (TournamentListSerializer).
        """
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve tournament detail.
        
        GET /api/tournaments/{id}/
        
        Returns full tournament details (TournamentDetailSerializer).
        """
        return super().retrieve(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """
        Create tournament (authenticated users only).
        
        POST /api/tournaments/
        Body: {name, game_id, format, max_participants, dates, ...}
        
        Returns:
        - 201: Tournament created successfully (DRAFT status)
        - 400: Validation error
        - 401: Authentication required
        """
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """
        Full update tournament (DRAFT only, organizer/staff only).
        
        PUT /api/tournaments/{id}/
        Body: {all fields required}
        
        Returns:
        - 200: Tournament updated successfully
        - 400: Validation error (invalid status, incomplete data)
        - 403: Permission denied (not organizer/staff, or status != DRAFT)
        - 404: Tournament not found
        """
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partial update tournament (DRAFT only, organizer/staff only).
        
        PATCH /api/tournaments/{id}/
        Body: {partial fields}
        
        Returns:
        - 200: Tournament updated successfully
        - 400: Validation error (invalid status, invalid fields)
        - 403: Permission denied (not organizer/staff, or status != DRAFT)
        - 404: Tournament not found
        """
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete tournament (NOT ALLOWED - use cancel action instead).
        
        DELETE /api/tournaments/{id}/
        
        Returns:
        - 405: Method not allowed (use POST /api/tournaments/{id}/cancel/ instead)
        """
        return Response(
            {
                'error': 'DELETE method not allowed. Use POST /api/tournaments/{id}/cancel/ instead.',
                'detail': 'Tournaments should be cancelled (soft delete) rather than hard deleted.'
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
