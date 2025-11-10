# Implements: Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md#section-5-bracket-models
# Implements: Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md#section-6-bracket-service
# Implements: Documents/ExecutionPlan/PHASE_4_IMPLEMENTATION_PLAN.md#module-41

"""
Tournament API - Bracket ViewSet

REST API for tournament bracket generation and management.

Module: 4.1 - Bracket Generation API
Phase: 4 - Tournament Live Operations

Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Bracket Models)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Bracket Service)
- Documents/ExecutionPlan/PHASE_4_IMPLEMENTATION_PLAN.md (Module 4.1 Scope)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.bracket import Bracket
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.api.serializers import (
    BracketGenerationSerializer,
    BracketSerializer,
    BracketDetailSerializer
)
from apps.tournaments.api.permissions import IsOrganizerOrAdmin
from apps.tournaments.realtime.utils import broadcast_bracket_generated


class BracketViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for tournament brackets.
    
    Endpoints:
    - GET /api/brackets/ - List all brackets
    - GET /api/brackets/{id}/ - Bracket detail with nodes
    - POST /api/tournaments/{tournament_id}/generate-bracket/ - Generate bracket (organizer only)
    - POST /api/brackets/{id}/regenerate/ - Regenerate bracket (organizer only, before start)
    - GET /api/brackets/{id}/visualization/ - Get bracket visualization data
    
    Permissions:
    - Read endpoints: Public (authenticated or anonymous)
    - Generate/Regenerate: Organizer or Admin only
    
    Module: 4.1 - Bracket Generation API
    Source: PHASE_4_IMPLEMENTATION_PLAN.md Section 2.1
    """
    
    queryset = Bracket.objects.all().select_related('tournament')
    serializer_class = BracketSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'retrieve':
            return BracketDetailSerializer
        elif self.action == 'generate_bracket':
            return BracketGenerationSerializer
        return BracketSerializer
    
    @action(detail=False, methods=['post'], url_path=r'(?P<tournament_id>[^/.]+)/generate',
            permission_classes=[IsOrganizerOrAdmin])
    def generate_bracket(self, request, tournament_id=None):
        """
        Generate bracket for tournament.
        
        POST /api/tournaments/brackets/{tournament_id}/generate/
        
        Request body:
        {
            "bracket_format": "single-elimination",  // optional, defaults to tournament.format
            "seeding_method": "random",              // optional: slot-order, random, manual, ranked
            "participant_ids": []                     // optional: manual participant selection
        }
        
        Permissions:
        - Must be tournament organizer or admin
        - Tournament must not have started
        - Existing bracket must not be finalized
        
        Returns:
        - 201 Created: Bracket generated successfully
        - 400 Bad Request: Invalid parameters or validation error
        - 403 Forbidden: Not organizer/admin
        - 404 Not Found: Tournament not found
        
        WebSocket Event: Broadcasts 'bracket_generated' to tournament_{id} channel
        
        Source: PHASE_4_IMPLEMENTATION_PLAN.md Module 4.1
        """
        # Fetch tournament
        tournament = get_object_or_404(Tournament, id=tournament_id)
        
        # Check permission (organizer or admin)
        if not self._is_organizer_or_admin(request.user, tournament):
            return Response(
                {"detail": "You must be the tournament organizer or admin to generate brackets."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate tournament hasn't started
        if tournament.status == 'live' or (tournament.tournament_start and tournament.tournament_start < timezone.now()):
            return Response(
                {"detail": "Cannot generate bracket for tournaments that have already started."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate request data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract parameters
        bracket_format = serializer.validated_data.get('bracket_format')
        # If no format specified, use tournament format (convert underscores to hyphens)
        if not bracket_format:
            bracket_format = tournament.format.replace('_', '-')
        seeding_method = serializer.validated_data.get('seeding_method', 'slot-order')
        participant_ids = serializer.validated_data.get('participant_ids')
        
        # Build participants list if manual IDs provided
        participants = None
        if participant_ids:
            # TODO: Fetch participants from registration service
            # For now, let BracketService fetch confirmed participants
            pass
        
        try:
            # Generate bracket via service
            bracket = BracketService.generate_bracket(
                tournament_id=tournament.id,
                bracket_format=bracket_format,
                seeding_method=seeding_method,
                participants=participants
            )
            
            # Broadcast WebSocket event
            try:
                broadcast_bracket_generated(
                    tournament_id=tournament.id,
                    bracket_data={
                        'bracket_id': bracket.id,
                        'tournament_id': tournament.id,
                        'tournament_name': tournament.name,
                        'format': bracket.format,
                        'seeding_method': bracket.seeding_method,
                        'total_rounds': bracket.total_rounds,
                        'total_matches': bracket.total_matches,
                        'generated_at': bracket.generated_at.isoformat(),
                        'generated_by': request.user.id,
                    }
                )
            except Exception as e:
                # Log error but don't fail the request
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Failed to broadcast bracket_generated event: {e}",
                    exc_info=True,
                    extra={'tournament_id': tournament.id, 'bracket_id': bracket.id}
                )
            
            # Return bracket details
            response_serializer = BracketDetailSerializer(bracket)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except DjangoValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Bracket generation failed for tournament {tournament_id}: {e}",
                exc_info=True,
                extra={'tournament_id': tournament_id, 'user_id': request.user.id}
            )
            return Response(
                {"detail": f"Bracket generation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsOrganizerOrAdmin])
    def regenerate(self, request, pk=None):
        """
        Regenerate existing bracket (before tournament starts).
        
        POST /api/brackets/{id}/regenerate/
        
        Request body:
        {
            "seeding_method": "random",  // optional: change seeding
            "force": false               // optional: force regeneration (deletes matches)
        }
        
        Permissions:
        - Must be tournament organizer or admin
        - Tournament must not have started
        - Bracket must not be finalized
        
        Returns:
        - 200 OK: Bracket regenerated
        - 400 Bad Request: Tournament started or invalid params
        - 403 Forbidden: Not organizer/admin
        - 404 Not Found: Bracket not found
        
        Source: PHASE_4_IMPLEMENTATION_PLAN.md Module 4.1
        """
        bracket = self.get_object()
        tournament = bracket.tournament
        
        # Check permission
        if not self._is_organizer_or_admin(request.user, tournament):
            return Response(
                {"detail": "You must be the tournament organizer or admin to regenerate brackets."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if finalized
        if bracket.is_finalized:
            return Response(
                {"detail": "Cannot regenerate finalized bracket. Unfinalize it first or use force=true."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if tournament started
        if tournament.status == 'live' or (tournament.tournament_start and tournament.tournament_start < timezone.now()):
            return Response(
                {"detail": "Cannot regenerate bracket for tournaments that have already started."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        seeding_method = request.data.get('seeding_method')
        force = request.data.get('force', False)
        
        try:
            # Regenerate bracket
            if force:
                # Delete and regenerate
                bracket = BracketService.recalculate_bracket(
                    tournament_id=tournament.id,
                    force=True
                )
            else:
                # Regenerate with new seeding
                bracket = BracketService.generate_bracket(
                    tournament_id=tournament.id,
                    seeding_method=seeding_method
                )
            
            # Broadcast regeneration event
            try:
                broadcast_bracket_generated(
                    tournament_id=tournament.id,
                    bracket_data={
                        'bracket_id': bracket.id,
                        'tournament_id': tournament.id,
                        'tournament_name': tournament.name,
                        'format': bracket.format,
                        'seeding_method': bracket.seeding_method,
                        'total_rounds': bracket.total_rounds,
                        'total_matches': bracket.total_matches,
                        'regenerated_at': timezone.now().isoformat(),
                        'regenerated_by': request.user.id,
                        'is_regeneration': True,
                    }
                )
            except Exception:
                pass  # Silently fail WebSocket broadcast
            
            response_serializer = BracketDetailSerializer(bracket)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except DjangoValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], url_path='visualization')
    def visualization(self, request, pk=None):
        """
        Get bracket visualization data.
        
        GET /api/brackets/{id}/visualization/
        
        Returns bracket structure optimized for frontend rendering.
        
        Returns:
        - 200 OK: Visualization data
        - 404 Not Found: Bracket not found
        
        Source: MODULE_1.5_COMPLETION_STATUS.md BracketService.get_bracket_visualization_data()
        """
        bracket = self.get_object()
        
        try:
            visualization_data = BracketService.get_bracket_visualization_data(bracket.id)
            return Response(visualization_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": f"Failed to generate visualization: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _is_organizer_or_admin(self, user, tournament):
        """Check if user is tournament organizer or admin."""
        if user.is_staff or user.is_superuser:
            return True
        return tournament.organizer_id == user.id
