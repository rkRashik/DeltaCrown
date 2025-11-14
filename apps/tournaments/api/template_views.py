"""
Tournament Template ViewSet

DRF ViewSet for tournament template API endpoints.

Source: BACKEND_ONLY_BACKLOG.md, Module 2.3
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone

from apps.tournaments.models import TournamentTemplate
from apps.tournaments.services.template_service import TemplateService
from apps.tournaments.api.template_serializers import (
    TournamentTemplateListSerializer,
    TournamentTemplateDetailSerializer,
    TournamentTemplateCreateSerializer,
    TournamentTemplateUpdateSerializer,
    TournamentTemplateApplySerializer,
    TournamentTemplateApplyResponseSerializer,
)


class TournamentTemplateViewSet(viewsets.GenericViewSet):
    """
    ViewSet for tournament template operations.
    
    Endpoints:
    - GET /api/tournament-templates/ - List templates
    - POST /api/tournament-templates/ - Create template
    - GET /api/tournament-templates/{id}/ - Get template detail
    - PATCH /api/tournament-templates/{id}/ - Update template
    - DELETE /api/tournament-templates/{id}/ - Delete template (soft delete)
    - POST /api/tournament-templates/{id}/apply/ - Apply template
    
    Permissions:
    - List: Anyone (unauthenticated see GLOBAL only)
    - Create: Authenticated users
    - Detail: Anyone (visibility check enforces access)
    - Update: Owner or staff
    - Delete: Owner or staff
    - Apply: Authenticated users (visibility check)
    """
    permission_classes = [AllowAny]  # Handled per-action
    queryset = TournamentTemplate.objects.none()  # For schema generation
    
    def get_permissions(self):
        """
        Customize permissions per action.
        """
        if self.action in ['create', 'partial_update', 'destroy', 'apply_template']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        """
        Return queryset filtered by user permissions.
        
        Uses TemplateService.list_templates() for visibility filtering.
        """
        user = self.request.user if self.request.user.is_authenticated else None
        
        # Get filter params from query string  
        game_id = self.request.query_params.get('game')
        visibility = self.request.query_params.get('visibility')
        is_active = self.request.query_params.get('is_active')
        created_by_id = self.request.query_params.get('created_by')
        organization_id = self.request.query_params.get('organization')
        
        # Convert is_active to boolean
        if is_active is not None:
            is_active = is_active.lower() in ('true', '1', 'yes')
        
        # Convert IDs to integers
        if game_id:
            game_id = int(game_id)
        if created_by_id:
            created_by_id = int(created_by_id)
        if organization_id:
            organization_id = int(organization_id)
        
        # Use TemplateService for filtering with permission checks
        templates = TemplateService.list_templates(
            user=user,
            game_id=game_id,
            visibility=visibility,
            is_active=is_active,
            created_by_id=created_by_id,
            organization_id=organization_id,
        )
        
        return templates
    
    def list(self, request):
        """
        List tournament templates.
        
        Query params:
        - game: Filter by game ID
        - visibility: Filter by visibility (private, org, global)
        - is_active: Filter by active status (true/false)
        - created_by: Filter by creator ID
        
        Returns:
            200: Paginated list of templates
        """
        templates = self.get_queryset()
        serializer = TournamentTemplateListSerializer(templates, many=True)
        
        # Simple pagination for now (DRF pagination would need proper queryset)
        return Response({
            'results': serializer.data,
            'count': len(serializer.data)
        })
    
    def create(self, request):
        """
        Create a new tournament template.
        
        Request body:
        - name (required): Template name
        - description: Template description
        - game_id: Game ID (optional, None for multi-game)
        - visibility: private (default), org, or global
        - organization_id: Organization ID (required for org visibility)
        - template_config: Tournament configuration (JSONB)
        
        Returns:
            201: Created template
            400: Validation error
            403: Permission denied
        """
        serializer = TournamentTemplateCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        try:
            serializer.is_valid(raise_exception=True)
            template = serializer.save()
            
            # Return detail serializer
            response_serializer = TournamentTemplateDetailSerializer(template)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionDenied as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    def retrieve(self, request, pk=None):
        """
        Get template detail.
        
        Returns:
            200: Template detail
            403: Permission denied
            404: Template not found
        """
        try:
            template = TemplateService.get_template(
                template_id=int(pk),
                user=request.user
            )
            serializer = TournamentTemplateDetailSerializer(template)
            return Response(serializer.data)
        
        except ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    def partial_update(self, request, pk=None):
        """
        Update a tournament template (partial update).
        
        Request body (all optional):
        - name: New name
        - description: New description
        - visibility: New visibility
        - template_config: New configuration
        - is_active: New active status
        
        Returns:
            200: Updated template
            400: Validation error
            403: Permission denied
            404: Template not found
        """
        try:
            # Get template
            template = TemplateService.get_template(
                template_id=int(pk),
                user=request.user
            )
            
            # Update via serializer
            serializer = TournamentTemplateUpdateSerializer(
                template,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            
            serializer.is_valid(raise_exception=True)
            updated_template = serializer.save()
            
            # Return detail serializer
            response_serializer = TournamentTemplateDetailSerializer(updated_template)
            return Response(response_serializer.data)
        
        except ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionDenied as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    def destroy(self, request, pk=None):
        """
        Delete a tournament template (soft delete).
        
        Returns:
            204: Template deleted
            403: Permission denied
            404: Template not found
        """
        try:
            TemplateService.delete_template(
                template_id=int(pk),
                user=request.user
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=True, methods=['post'], url_path='apply')
    def apply_template(self, request, pk=None):
        """
        Apply a template to generate tournament configuration.
        
        **Returns merged payload only** - does NOT create tournament.
        Caller should use POST /api/tournaments/ with merged config.
        
        Request body:
        - tournament_payload (optional): Tournament data to merge with template
          (payload values override template values)
        
        Response:
        - merged_config: Ready-to-use tournament configuration
        - template_id: Template that was applied
        - template_name: Template name
        - applied_at: Timestamp
        
        Returns:
            200: Merged configuration
            400: Validation error (inactive template, etc.)
            403: Permission denied
            404: Template not found
        
        Example:
            POST /api/tournament-templates/1/apply/
            {
                "tournament_payload": {
                    "name": "Summer Championship 2025",
                    "tournament_start": "2025-07-01T10:00:00Z"
                }
            }
            
            Response:
            {
                "merged_config": {
                    "format": "single_elimination",
                    "max_participants": 16,
                    "name": "Summer Championship 2025",
                    "tournament_start": "2025-07-01T10:00:00Z",
                    ...
                },
                "template_id": 1,
                "template_name": "5v5 Valorant Tournament",
                "applied_at": "2025-11-14T10:30:00Z"
            }
        """
        # Validate input
        input_serializer = TournamentTemplateApplySerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        
        tournament_payload = input_serializer.validated_data.get('tournament_payload')
        
        try:
            # Apply template via service
            merged_config = TemplateService.apply_template(
                template_id=int(pk),
                user=request.user,
                tournament_payload=tournament_payload
            )
            
            # Get template for response metadata
            template = TemplateService.get_template(int(pk), request.user)
            
            # Build response
            response_data = {
                'merged_config': merged_config,
                'template_id': template.id,
                'template_name': template.name,
                'applied_at': timezone.now(),
            }
            
            response_serializer = TournamentTemplateApplyResponseSerializer(response_data)
            return Response(response_serializer.data)
        
        except ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionDenied as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
