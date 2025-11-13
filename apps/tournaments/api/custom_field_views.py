"""
Custom Field API ViewSet

Module: 2.2 - Game Configurations & Custom Fields (Backend Only)
Source Documents:
- Documents/ExecutionPlan/BACKEND_ONLY_BACKLOG.md (Module 2.2)

Description:
REST API endpoints for tournament custom fields management.
Nested under tournaments: /api/tournaments/{tournament_id}/custom-fields/

Endpoints:
- POST /api/tournaments/{tournament_id}/custom-fields/ - Create custom field
- GET /api/tournaments/{tournament_id}/custom-fields/ - List custom fields
- GET /api/tournaments/{tournament_id}/custom-fields/{id}/ - Retrieve custom field
- PATCH /api/tournaments/{tournament_id}/custom-fields/{id}/ - Update custom field
- DELETE /api/tournaments/{tournament_id}/custom-fields/{id}/ - Delete custom field

Architecture Decisions:
- ADR-001: Service Layer Pattern - Delegates to CustomFieldService
- ADR-009: API Security - Organizer/staff only for CRUD, public read for published tournaments
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.tournaments.models.tournament import CustomField, Tournament
from apps.tournaments.api.custom_field_serializers import (
    CustomFieldListSerializer,
    CustomFieldDetailSerializer,
    CustomFieldCreateSerializer,
    CustomFieldUpdateSerializer
)
from apps.tournaments.services.custom_field_service import CustomFieldService


class CustomFieldViewSet(viewsets.ModelViewSet):
    """
    ViewSet for tournament custom fields management.
    
    Provides CRUD operations for custom fields, nested under tournaments.
    Permissions: organizer/staff for write operations, public read for published tournaments.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """
        Filter custom fields by tournament.
        
        Returns only custom fields for the tournament specified in the URL.
        """
        tournament_id = self.kwargs.get('tournament_pk')
        if tournament_id:
            return CustomField.objects.filter(tournament_id=tournament_id).order_by('order', 'field_name')
        return CustomField.objects.none()
    
    def get_serializer_class(self):
        """Return serializer class based on action."""
        if self.action == 'list':
            return CustomFieldListSerializer
        elif self.action == 'create':
            return CustomFieldCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CustomFieldUpdateSerializer
        return CustomFieldDetailSerializer
    
    def get_serializer_context(self):
        """Add tournament_id to serializer context."""
        context = super().get_serializer_context()
        context['tournament_id'] = self.kwargs.get('tournament_pk')
        return context
    
    def check_object_permissions(self, request, obj):
        """
        Check object-level permissions.
        
        Write operations: organizer or staff only
        Read operations: public if tournament published
        """
        super().check_object_permissions(request, obj)
        
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            tournament = obj.tournament
            if tournament.organizer != request.user and not request.user.is_staff:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Only the organizer or staff can modify custom fields")
    
    def list(self, request, *args, **kwargs):
        """
        List custom fields for a tournament.
        
        GET /api/tournaments/{tournament_id}/custom-fields/
        
        Response 200:
        [
            {
                "id": 1,
                "field_name": "Discord Server",
                "field_key": "discord-server",
                "field_type": "url",
                "is_required": true,
                "order": 0
            },
            ...
        ]
        """
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a custom field.
        
        GET /api/tournaments/{tournament_id}/custom-fields/{id}/
        
        Response 200:
        {
            "id": 1,
            "tournament": 1,
            "field_name": "Discord Server",
            "field_key": "discord-server",
            "field_type": "url",
            "field_config": {"pattern": "^https://discord\\.gg/[a-zA-Z0-9]+$"},
            "field_value": {},
            "is_required": true,
            "help_text": "Tournament Discord server link",
            "order": 0
        }
        """
        return super().retrieve(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """
        Create a custom field for a tournament.
        
        POST /api/tournaments/{tournament_id}/custom-fields/
        
        Request body:
        {
            "field_name": "Discord Server",
            "field_type": "url",
            "field_config": {"pattern": "^https://discord\\.gg/[a-zA-Z0-9]+$"},
            "is_required": true,
            "help_text": "Tournament Discord server link",
            "order": 0
        }
        
        Response 201:
        {
            "id": 1,
            "tournament": 1,
            "field_name": "Discord Server",
            "field_key": "discord-server",
            "field_type": "url",
            "field_config": {"pattern": "^https://discord\\.gg/[a-zA-Z0-9]+$"},
            "field_value": {},
            "is_required": true,
            "help_text": "Tournament Discord server link",
            "order": 0
        }
        
        Response 400:
        {
            "error": "A field with key 'discord-server' already exists for this tournament"
        }
        
        Response 403:
        {
            "error": "Only the organizer or staff can add custom fields"
        }
        """
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            custom_field = serializer.save()
            
            # Return detailed representation
            response_serializer = CustomFieldDetailSerializer(custom_field)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    def update(self, request, *args, **kwargs):
        """
        Update a custom field (full update).
        
        PUT /api/tournaments/{tournament_id}/custom-fields/{id}/
        
        Request body: Same as create
        
        Response 200: Same as create
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        try:
            serializer.is_valid(raise_exception=True)
            custom_field = serializer.save()
            
            # Return detailed representation
            response_serializer = CustomFieldDetailSerializer(custom_field)
            return Response(response_serializer.data)
        
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    def partial_update(self, request, *args, **kwargs):
        """
        Update a custom field (partial update).
        
        PATCH /api/tournaments/{tournament_id}/custom-fields/{id}/
        
        Request body:
        {
            "is_required": false,
            "help_text": "Optional Discord link"
        }
        
        Response 200: Same as create
        
        Response 400:
        {
            "error": "Cannot update custom fields for tournament with status 'PUBLISHED'"
        }
        
        Response 403:
        {
            "error": "Only the organizer or staff can modify custom fields"
        }
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a custom field.
        
        DELETE /api/tournaments/{tournament_id}/custom-fields/{id}/
        
        Response 204: No content
        
        Response 403:
        {
            "error": "Only the organizer or staff can delete custom fields"
        }
        
        Response 400:
        {
            "error": "Cannot delete custom fields for tournament with status 'PUBLISHED'"
        }
        """
        instance = self.get_object()
        
        try:
            CustomFieldService.delete_field(
                field_id=instance.id,
                user=request.user
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
