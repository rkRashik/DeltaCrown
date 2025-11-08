"""
Check-in API Views

Provides RESTful endpoints for:
- Single check-in (POST)
- Undo check-in (POST)
- Bulk check-in (POST - organizer only)
- Check-in status (GET)

Author: DeltaCrown Development Team
Date: November 8, 2025
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError, PermissionDenied
from django.shortcuts import get_object_or_404

from apps.tournaments.models import Registration
from apps.tournaments.services.checkin_service import CheckinService
from .serializers import (
    CheckinRequestSerializer,
    UndoCheckinRequestSerializer,
    BulkCheckinSerializer,
    CheckinStatusSerializer,
    CheckinResponseSerializer,
    BulkCheckinResponseSerializer,
)


class CheckinViewSet(viewsets.GenericViewSet):
    """
    ViewSet for tournament check-in operations.
    
    Endpoints:
    - POST /api/tournaments/checkin/{registration_id}/ - Check in
    - POST /api/tournaments/checkin/{registration_id}/undo/ - Undo check-in
    - POST /api/tournaments/checkin/bulk/ - Bulk check-in (organizer)
    - GET /api/tournaments/checkin/{registration_id}/status/ - Get status
    """
    
    queryset = Registration.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'registration_id'
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'check_in':
            return CheckinRequestSerializer
        elif self.action == 'undo':
            return UndoCheckinRequestSerializer
        elif self.action == 'bulk':
            return BulkCheckinSerializer
        elif self.action == 'status':
            return CheckinStatusSerializer
        return CheckinRequestSerializer
    
    @action(detail=True, methods=['post'], url_path='check-in')
    def check_in(self, request, registration_id=None):
        """
        Check in a registration.
        
        Permissions:
        - Registration owner (player/team captain)
        - Tournament organizer
        - Superuser
        """
        serializer = CheckinRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Perform check-in via service
            registration = CheckinService.check_in(
                registration_id=int(registration_id),
                actor=request.user
            )
            
            # Broadcast WebSocket event
            self._broadcast_checkin_event(registration, checked_in=True)
            
            # Return response
            response_data = {
                'success': True,
                'message': 'Successfully checked in',
                'registration': CheckinStatusSerializer(
                    registration,
                    context={'request': request}
                ).data
            }
            
            return Response(
                response_data,
                status=status.HTTP_200_OK
            )
            
        except Registration.DoesNotExist:
            return Response(
                {'error': 'Registration not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Check-in failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def undo(self, request, registration_id=None):
        """
        Undo check-in for a registration.
        
        Permissions:
        - Registration owner (within undo window)
        - Tournament organizer (anytime)
        - Superuser (anytime)
        """
        serializer = UndoCheckinRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reason = serializer.validated_data.get('reason', None)
        
        try:
            # Perform undo via service
            registration = CheckinService.undo_check_in(
                registration_id=int(registration_id),
                actor=request.user,
                reason=reason
            )
            
            # Broadcast WebSocket event
            self._broadcast_checkin_event(registration, checked_in=False)
            
            # Return response
            response_data = {
                'success': True,
                'message': 'Check-in successfully undone',
                'registration': CheckinStatusSerializer(
                    registration,
                    context={'request': request}
                ).data
            }
            
            return Response(
                response_data,
                status=status.HTTP_200_OK
            )
            
        except Registration.DoesNotExist:
            return Response(
                {'error': 'Registration not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Undo check-in failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """
        Bulk check-in multiple registrations.
        
        Permissions:
        - Tournament organizer (for all registrations)
        - Superuser
        
        Request body:
        {
            "registration_ids": [1, 2, 3, ...]
        }
        
        Response:
        {
            "success": [{id: 1}, ...],
            "skipped": [{id: 2, reason: "..."}, ...],
            "errors": [{id: 3, reason: "..."}, ...],
            "summary": {
                "total_requested": 10,
                "successful": 7,
                "skipped": 2,
                "failed": 1
            }
        }
        """
        serializer = BulkCheckinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        registration_ids = serializer.validated_data['registration_ids']
        
        try:
            # Perform bulk check-in via service
            results = CheckinService.bulk_check_in(
                registration_ids=registration_ids,
                actor=request.user
            )
            
            # Broadcast WebSocket events for successful check-ins
            for success_item in results['success']:
                try:
                    registration = Registration.objects.select_related('tournament').get(
                        id=success_item['id']
                    )
                    self._broadcast_checkin_event(registration, checked_in=True)
                except Exception:
                    pass  # Don't fail bulk operation if WebSocket fails
            
            # Return response
            response_serializer = BulkCheckinResponseSerializer(results)
            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK
            )
            
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Bulk check-in failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def status(self, request, registration_id=None):
        """
        Get check-in status for a registration.
        
        Permissions:
        - Any authenticated user can view
        """
        registration = get_object_or_404(
            Registration.objects.select_related(
                'tournament',
                'user',
                'team',
                'checked_in_by'
            ),
            id=registration_id
        )
        
        serializer = CheckinStatusSerializer(
            registration,
            context={'request': request}
        )
        
        return Response(serializer.data)
    
    # ========================
    # Private Helper Methods
    # ========================
    
    def _broadcast_checkin_event(self, registration: Registration, checked_in: bool):
        """
        Broadcast check-in event via WebSocket.
        
        Args:
            registration: Registration instance
            checked_in: True for check-in, False for undo
        """
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            
            # Determine event type
            event_type = 'registration_checked_in' if checked_in else 'registration_checkin_reverted'
            
            # Prepare payload
            payload = {
                'type': event_type,
                'tournament_id': registration.tournament_id,
                'registration_id': registration.id,
                'checked_in': checked_in,
                'checked_in_at': registration.checked_in_at.isoformat() if registration.checked_in_at else None,
                # Note: checked_in_by field not yet in Registration model
            }
            
            # Broadcast to tournament group
            group_name = f'tournament_{registration.tournament_id}'
            async_to_sync(channel_layer.group_send)(
                group_name,
                payload
            )
            
        except Exception as e:
            # Log error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to broadcast check-in event: {e}")
