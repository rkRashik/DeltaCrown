# Implements: Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#api-views
# Implements: Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md#registration-api
# Implements: Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md#rest-api-layer

"""
Tournament API - ViewSets

DRF viewsets for tournament registration endpoints.

Source Documents:
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (API Views)
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (Registration API)
- Documents/Planning/PART_2.3_REALTIME_SECURITY.md (Security & Permissions)
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md (API Standards)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from apps.tournaments.models.registration import Registration
from apps.tournaments.api.serializers import (
    RegistrationSerializer,
    RegistrationDetailSerializer,
    RegistrationCancelSerializer
)
from apps.tournaments.api.permissions import IsOwnerOrOrganizer
from apps.tournaments.services.registration_service import RegistrationService


class RegistrationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for tournament registrations.
    
    Endpoints:
    - GET /api/registrations/ - List user's registrations
    - POST /api/registrations/ - Create new registration
    - GET /api/registrations/{id}/ - Registration detail
    - DELETE /api/registrations/{id}/ - Cancel registration
    - POST /api/registrations/{id}/cancel/ - Cancel with reason
    
    Permissions:
    - Authentication required for all endpoints
    - Users can only see/modify their own registrations
    - Tournament organizers can see all registrations for their tournaments
    - Staff users have full access
    
    Source: PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md Section 4
    """
    
    permission_classes = [IsAuthenticated, IsOwnerOrOrganizer]
    
    def get_queryset(self):
        """
        Return registrations based on user role.
        
        - Regular users: Their own registrations
        - Staff users: All registrations
        - Organizers: Registrations for their tournaments
        
        Source: PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md Section 4.1
        """
        user = self.request.user
        
        # Staff users see all
        if user.is_staff:
            return Registration.objects.all().select_related(
                'tournament',
                'tournament__game',
                'user'
            ).prefetch_related('tournament__registrations')
        
        # Regular users see only their own registrations
        return Registration.objects.filter(
            user=user
        ).select_related(
            'tournament',
            'tournament__game',
            'user'
        ).prefetch_related('tournament__registrations')
    
    def get_serializer_class(self):
        """
        Use detailed serializer for retrieve/list, basic for create.
        
        Source: PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md Section 4.2
        """
        if self.action in ['retrieve', 'list']:
            return RegistrationDetailSerializer
        return RegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create a new registration.
        
        POST /api/registrations/
        
        Request Body:
            {
                "tournament_slug": "summer-valorant-cup-2025",  // OR tournament_id
                "team_id": 123,  // Optional, required for team tournaments
                "registration_data": {  // Optional additional data
                    "discord_username": "player#1234",
                    "notes": "Looking forward to competing!"
                }
            }
        
        Response (201 Created):
            {
                "id": 456,
                "tournament_name": "Summer Valorant Cup 2025",
                "tournament_slug": "summer-valorant-cup-2025",
                "status": "pending",
                "status_display": "Pending",
                "registered_at": "2025-01-15T10:30:00Z",
                "registration_data": {...},
                "team_id": 123
            }
        
        Source: PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.1
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Serializer.create() calls RegistrationService.register_participant()
        registration = serializer.save()
        
        # Broadcast WebSocket event
        self._broadcast_registration_created(registration)
        
        # Return created registration
        response_serializer = RegistrationDetailSerializer(registration)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """
        Cancel a registration (soft delete).
        
        DELETE /api/registrations/{id}/
        
        Delegates to RegistrationService.cancel_registration()
        
        Response (204 No Content):
            (empty body)
        
        Source: PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.2
        """
        registration = self.get_object()
        
        try:
            # Call service layer for cancellation
            RegistrationService.cancel_registration(
                registration_id=registration.id,
                user=request.user,
                reason="Cancelled via API"
            )
            
            # Broadcast WebSocket event
            self._broadcast_registration_cancelled(registration)
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except DjangoValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_with_reason(self, request, pk=None):
        """
        Cancel a registration with a reason.
        
        POST /api/registrations/{id}/cancel/
        
        Request Body:
            {
                "reason": "Schedule conflict - cannot attend"
            }
        
        Response (200 OK):
            {
                "id": 456,
                "status": "cancelled",
                "status_display": "Cancelled",
                "cancellation_reason": "Schedule conflict - cannot attend"
            }
        
        Source: PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.2
        """
        registration = self.get_object()
        
        # Validate cancellation request
        serializer = RegistrationCancelSerializer(
            data=request.data,
            context={'registration': registration}
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            # Call service layer
            cancelled_registration = RegistrationService.cancel_registration(
                registration_id=registration.id,
                user=request.user,
                reason=serializer.validated_data.get('reason', '')
            )
            
            # Broadcast WebSocket event
            self._broadcast_registration_cancelled(cancelled_registration)
            
            # Return updated registration
            response_serializer = RegistrationDetailSerializer(cancelled_registration)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        except DjangoValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _broadcast_registration_created(self, registration):
        """
        Broadcast registration_created event to WebSocket clients.
        
        Sends event to tournament room so spectators/players can see
        real-time registration updates.
        
        Source: PART_2.3_REALTIME_SECURITY.md Section 4
        """
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            # Broadcast to tournament room
            async_to_sync(channel_layer.group_send)(
                f"tournament_{registration.tournament.id}",
                {
                    "type": "registration.created",
                    "registration_id": registration.id,
                    "tournament_id": registration.tournament.id,
                    "user_id": registration.user.id if registration.user else None,
                    "team_id": registration.team_id,
                    "status": registration.status,
                    "participant_name": registration.user.username if registration.user else f"Team {registration.team_id}",
                    "timestamp": registration.registered_at.isoformat() if registration.registered_at else None,
                }
            )
    
    def _broadcast_registration_cancelled(self, registration):
        """
        Broadcast registration_cancelled event to WebSocket clients.
        
        Source: PART_2.3_REALTIME_SECURITY.md Section 4
        """
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            # Broadcast to tournament room
            async_to_sync(channel_layer.group_send)(
                f"tournament_{registration.tournament.id}",
                {
                    "type": "registration.cancelled",
                    "registration_id": registration.id,
                    "tournament_id": registration.tournament.id,
                    "user_id": registration.user.id if registration.user else None,
                    "team_id": registration.team_id,
                    "participant_name": registration.user.username if registration.user else f"Team {registration.team_id}",
                    "timestamp": timezone.now().isoformat(),
                }
            )
