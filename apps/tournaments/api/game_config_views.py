"""
Game Configuration API ViewSet

Module: 2.2 - Game Configurations & Custom Fields (Backend Only)
Source Documents:
- Documents/ExecutionPlan/Core/BACKEND_ONLY_BACKLOG.md (Module 2.2)

Description:
REST API endpoints for game configuration management.
Provides read access for all users, staff-only updates.

Endpoints:
- GET /api/games/{id}/config/ - Retrieve game configuration
- PATCH /api/games/{id}/config/ - Update game configuration (staff only)
- GET /api/games/{id}/config-schema/ - Get JSON Schema for game config

Architecture Decisions:
- ADR-001: Service Layer Pattern - Delegates to GameConfigService
- ADR-009: API Security - IsAuthenticatedOrReadOnly + IsAdminUser for updates
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.games.models.game import Game
from apps.tournaments.api.game_config_serializers import (
    GameConfigSerializer,
    GameConfigUpdateSerializer,
    GameConfigSchemaSerializer
)


class GameConfigViewSet(viewsets.GenericViewSet):
    """
    ViewSet for game configuration management.
    
    Provides configuration retrieval, updates, and schema endpoints.
    """
    queryset = Game.objects.filter(is_active=True)
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        """Return serializer class based on action."""
        if self.action == 'partial_update':
            return GameConfigUpdateSerializer
        elif self.action == 'config_schema':
            return GameConfigSchemaSerializer
        return GameConfigSerializer
    
    def get_permissions(self):
        """Staff-only for updates."""
        if self.action == 'partial_update':
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]
    
    @action(detail=True, methods=['get'], url_path='config')
    def retrieve_config(self, request, pk=None):
        """
        Retrieve game configuration.
        
        GET /api/games/{id}/config/
        
        Returns the full game_config JSONB or default schema.
        Public access (read-only).
        
        Response 200:
        {
            "schema_version": "1.0",
            "allowed_formats": ["single_elimination", "double_elimination"],
            "team_size_range": [1, 5],
            "custom_field_schemas": [],
            "match_settings": {"default_best_of": 1, "available_maps": []}
        }
        """
        game = self.get_object()
        serializer = GameConfigSerializer(game)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'], url_path='config', permission_classes=[IsAdminUser])
    def update_config(self, request, pk=None):
        """
        Update game configuration (partial update).
        
        PATCH /api/games/{id}/config/
        
        Staff-only. Deep merges config updates into existing config.
        Validates via GameConfigService.
        
        Request body:
        {
            "allowed_formats": ["single_elimination"],
            "team_size_range": [5, 5]
        }
        
        Response 200:
        {
            "schema_version": "1.0",
            "allowed_formats": ["single_elimination"],
            "team_size_range": [5, 5],
            "custom_field_schemas": [],
            "match_settings": {"default_best_of": 1, "available_maps": []}
        }
        
        Response 400:
        {
            "error": "Invalid allowed_formats: ['invalid_format'] not in valid choices"
        }
        
        Response 403:
        {
            "detail": "You do not have permission to perform this action."
        }
        """
        game = self.get_object()
        serializer = GameConfigUpdateSerializer(
            game,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            # Return updated config
            response_serializer = GameConfigSerializer(game)
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
    
    @action(detail=True, methods=['get'], url_path='config-schema')
    def config_schema(self, request, pk=None):
        """
        Get JSON Schema for game configuration.
        
        GET /api/games/{id}/config-schema/
        
        Returns JSON Schema (draft-07) describing game_config structure.
        Public access. Used for API documentation and client validation.
        
        Response 200:
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Valorant Configuration Schema",
            "type": "object",
            "properties": {
                "schema_version": {"type": "string"},
                "allowed_formats": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["single_elimination", "double_elimination", ...]
                    }
                },
                "team_size_range": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {"type": "integer", "minimum": 1}
                },
                ...
            },
            "required": ["schema_version", "allowed_formats", "team_size_range"]
        }
        """
        game = self.get_object()
        serializer = GameConfigSchemaSerializer(game)
        return Response(serializer.data)
