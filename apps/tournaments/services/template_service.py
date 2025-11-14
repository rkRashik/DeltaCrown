"""
Tournament Template Service

Provides business logic for tournament template management:
- Create templates from tournament configurations
- List/filter templates by visibility, game, owner
- Apply templates to new tournaments
- Update/delete templates with permission checks

Source: BACKEND_ONLY_BACKLOG.md, Module 2.3
ADR-001: Service Layer Architecture
ADR-004: PostgreSQL JSONB for template storage
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from django.db.models import Q

from apps.tournaments.models import TournamentTemplate, Game, Tournament
from apps.tournaments.services.game_config_service import GameConfigService


class TemplateService:
    """
    Service layer for tournament template operations.
    
    Handles template creation, updates, application, and filtering
    with proper permission checks and validation.
    """
    
    @staticmethod
    def create_template(
        name: str,
        created_by,
        game_id: Optional[int] = None,
        template_config: Optional[Dict[str, Any]] = None,
        description: str = "",
        visibility: str = TournamentTemplate.PRIVATE,
        organization_id: Optional[int] = None,
    ) -> TournamentTemplate:
        """
        Create a new tournament template.
        
        **Permissions**: Authenticated users can create PRIVATE templates,
        staff can create ORG/GLOBAL templates.
        
        **Validation**:
        - game_id must exist (if provided)
        - template_config structure is validated
        - ORG visibility requires organization_id
        - GLOBAL visibility requires staff permission
        
        Args:
            name: Template name (e.g., "5v5 Valorant Tournament")
            created_by: User creating the template
            game_id: Optional game ID (None for multi-game templates)
            template_config: Tournament configuration (JSONB)
            description: Template description
            visibility: PRIVATE, ORG, or GLOBAL
            organization_id: Organization ID for ORG visibility
        
        Returns:
            TournamentTemplate instance
        
        Raises:
            ValidationError: Invalid game_id or template_config
            PermissionDenied: User lacks permission for visibility level
        
        Example:
            >>> template = TemplateService.create_template(
            ...     name="5v5 Valorant Tournament",
            ...     created_by=request.user,
            ...     game_id=1,
            ...     template_config={
            ...         "format": "single_elimination",
            ...         "max_participants": 16,
            ...         "has_entry_fee": True,
            ...         "entry_fee_amount": "500.00"
            ...     },
            ...     visibility=TournamentTemplate.PRIVATE
            ... )
        """
        # Permission checks
        if visibility == TournamentTemplate.GLOBAL and not created_by.is_staff:
            raise PermissionDenied("Only staff can create GLOBAL templates")
        
        if visibility == TournamentTemplate.ORG and not organization_id:
            raise ValidationError("ORG visibility requires organization_id")
        
        # Validate game exists
        game = None
        if game_id:
            try:
                game = Game.objects.get(id=game_id)
            except Game.DoesNotExist:
                raise ValidationError(f"Game with id={game_id} does not exist")
        
        # Validate template_config structure
        if template_config is None:
            template_config = {}
        
        TemplateService._validate_template_config(template_config, game)
        
        # Create template
        with transaction.atomic():
            template = TournamentTemplate.objects.create(
                name=name,
                description=description,
                created_by=created_by,
                game=game,
                visibility=visibility,
                organization_id=organization_id,
                template_config=template_config,
            )
        
        return template
    
    @staticmethod
    def update_template(
        template_id: int,
        user,
        name: Optional[str] = None,
        description: Optional[str] = None,
        template_config: Optional[Dict[str, Any]] = None,
        visibility: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> TournamentTemplate:
        """
        Update an existing tournament template.
        
        **Permissions**: Owner or staff only.
        
        **Rules**:
        - Cannot modify inactive templates (unless activating)
        - Cannot change game after creation
        - Visibility changes require appropriate permissions
        
        Args:
            template_id: Template ID to update
            user: User performing the update
            name: New name (optional)
            description: New description (optional)
            template_config: New configuration (optional)
            visibility: New visibility (optional)
            is_active: New active status (optional)
        
        Returns:
            Updated TournamentTemplate instance
        
        Raises:
            ValidationError: Template not found or inactive
            PermissionDenied: User lacks permission
        """
        try:
            template = TournamentTemplate.objects.get(id=template_id, is_deleted=False)
        except TournamentTemplate.DoesNotExist:
            raise ValidationError(f"Template with id={template_id} does not exist")
        
        # Permission check
        if not TemplateService._can_modify_template(template, user):
            raise PermissionDenied("You do not have permission to modify this template")
        
        # Cannot modify inactive templates unless activating
        if not template.is_active and is_active is None:
            raise ValidationError("Cannot modify inactive template. Set is_active=True first.")
        
        # Update fields
        with transaction.atomic():
            if name is not None:
                template.name = name
            
            if description is not None:
                template.description = description
            
            if template_config is not None:
                TemplateService._validate_template_config(template_config, template.game)
                template.template_config = template_config
            
            if visibility is not None:
                # Validate permission for visibility change
                if visibility == TournamentTemplate.GLOBAL and not user.is_staff:
                    raise PermissionDenied("Only staff can set GLOBAL visibility")
                template.visibility = visibility
            
            if is_active is not None:
                template.is_active = is_active
            
            template.save()
        
        return template
    
    @staticmethod
    def get_template(template_id: int, user=None) -> TournamentTemplate:
        """
        Retrieve a single template by ID.
        
        **Permissions**: Respects visibility rules.
        - PRIVATE: Owner only
        - ORG: Organization members (not enforced here, just returns)
        - GLOBAL: Anyone
        
        Args:
            template_id: Template ID
            user: Optional user for permission checks
        
        Returns:
            TournamentTemplate instance
        
        Raises:
            ValidationError: Template not found
            PermissionDenied: User lacks access
        """
        try:
            template = TournamentTemplate.objects.select_related('game', 'created_by').get(
                id=template_id,
                is_deleted=False
            )
        except TournamentTemplate.DoesNotExist:
            raise ValidationError(f"Template with id={template_id} does not exist")
        
        # Check visibility
        if user and not TemplateService._can_view_template(template, user):
            raise PermissionDenied("You do not have permission to view this template")
        
        return template
    
    @staticmethod
    def list_templates(
        user=None,
        game_id: Optional[int] = None,
        visibility: Optional[str] = None,
        is_active: Optional[bool] = True,
        created_by_id: Optional[int] = None,
        organization_id: Optional[int] = None,
    ) -> List[TournamentTemplate]:
        """
        List templates with filtering.
        
        **Filters**:
        - game_id: Filter by game
        - visibility: Filter by visibility level
        - is_active: Filter by active status (default: True)
        - created_by_id: Filter by creator
        - organization_id: Filter by organization
        
        **Visibility Rules**:
        - PRIVATE: Only creator can see
        - ORG: Organization members can see (org check not enforced here)
        - GLOBAL: Everyone can see
        
        Args:
            user: Optional user for permission filtering
            game_id: Filter by game ID
            visibility: Filter by visibility
            is_active: Filter by active status
            created_by_id: Filter by creator user ID
            organization_id: Filter by organization ID
        
        Returns:
            List of TournamentTemplate instances
        """
        queryset = TournamentTemplate.objects.select_related('game', 'created_by').filter(
            is_deleted=False
        )
        
        # Apply filters
        if game_id is not None:
            queryset = queryset.filter(game_id=game_id)
        
        if visibility is not None:
            queryset = queryset.filter(visibility=visibility)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        if created_by_id is not None:
            queryset = queryset.filter(created_by_id=created_by_id)
        
        if organization_id is not None:
            queryset = queryset.filter(organization_id=organization_id)
        
        # Apply visibility filtering based on user
        if user:
            # Staff can see everything
            if not user.is_staff:
                # Non-staff can see: own PRIVATE, ORG (if in org), GLOBAL
                visibility_filter = Q(visibility=TournamentTemplate.GLOBAL) | Q(created_by=user)
                
                # Note: Organization membership check would go here
                # For now, we allow viewing all ORG templates
                # In production, you'd check: user.organization_memberships.filter(organization_id=F('organization_id'))
                visibility_filter |= Q(visibility=TournamentTemplate.ORG)
                
                queryset = queryset.filter(visibility_filter)
        else:
            # Anonymous users can only see GLOBAL templates
            queryset = queryset.filter(visibility=TournamentTemplate.GLOBAL)
        
        return list(queryset.order_by('-created_at'))
    
    @staticmethod
    def apply_template(template_id: int, user, tournament_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Apply a template to create tournament payload.
        
        **Returns**: Merged tournament configuration (does NOT create tournament).
        The caller should use TournamentService to create the actual tournament.
        
        **Behavior**:
        - Retrieves template configuration
        - Merges with provided tournament_payload (payload overrides template)
        - Validates game compatibility
        - Increments template usage counter
        
        **Permission**: User must have access to template (visibility rules)
        
        Args:
            template_id: Template ID to apply
            user: User applying the template
            tournament_payload: Optional tournament data to merge (overrides template)
        
        Returns:
            Dict with merged tournament configuration
        
        Raises:
            ValidationError: Template not found, inactive, or invalid
            PermissionDenied: User lacks access
        
        Example:
            >>> merged_config = TemplateService.apply_template(
            ...     template_id=1,
            ...     user=request.user,
            ...     tournament_payload={
            ...         "name": "Summer Championship 2025",
            ...         "tournament_start": "2025-07-01T10:00:00Z"
            ...     }
            ... )
            >>> # Then create tournament:
            >>> tournament = TournamentService.create_tournament(**merged_config, organizer=user)
        """
        # Get template with permission check
        template = TemplateService.get_template(template_id, user)
        
        # Validate template is active
        if not template.is_active:
            raise ValidationError("Cannot apply inactive template")
        
        # Start with template config
        merged_payload = template.template_config.copy()
        
        # Merge with provided payload (payload overrides template)
        if tournament_payload:
            merged_payload.update(tournament_payload)
        
        # Add game_id from template if not in payload
        if template.game_id and 'game_id' not in merged_payload:
            merged_payload['game_id'] = template.game_id
        
        # Validate merged payload
        if template.game:
            TemplateService._validate_merged_payload(merged_payload, template.game)
        
        # Increment usage counter
        with transaction.atomic():
            template.increment_usage()
        
        return merged_payload
    
    @staticmethod
    def delete_template(template_id: int, user) -> None:
        """
        Soft delete a template.
        
        **Permissions**: Owner or staff only.
        
        Args:
            template_id: Template ID to delete
            user: User performing deletion
        
        Raises:
            ValidationError: Template not found
            PermissionDenied: User lacks permission
        """
        try:
            template = TournamentTemplate.objects.get(id=template_id, is_deleted=False)
        except TournamentTemplate.DoesNotExist:
            raise ValidationError(f"Template with id={template_id} does not exist")
        
        # Permission check
        if not TemplateService._can_modify_template(template, user):
            raise PermissionDenied("You do not have permission to delete this template")
        
        # Soft delete
        with transaction.atomic():
            template.is_deleted = True
            template.deleted_at = timezone.now()
            template.deleted_by = user
            template.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    # Helper methods
    
    @staticmethod
    def _validate_template_config(config: Dict[str, Any], game: Optional[Game] = None) -> None:
        """
        Validate template_config structure.
        
        Checks:
        - Required fields are present (if specified)
        - format is valid (if specified)
        - Numeric values are valid
        - Game-specific rules (if game provided)
        
        Raises:
            ValidationError: Invalid configuration
        """
        # Validate format if specified
        if 'format' in config:
            valid_formats = dict(Tournament.FORMAT_CHOICES).keys()
            if config['format'] not in valid_formats:
                raise ValidationError(
                    f"Invalid format '{config['format']}'. Must be one of: {', '.join(valid_formats)}"
                )
        
        # Validate participation_type if specified
        if 'participation_type' in config:
            valid_types = dict(Tournament.PARTICIPATION_TYPE_CHOICES).keys()
            if config['participation_type'] not in valid_types:
                raise ValidationError(
                    f"Invalid participation_type '{config['participation_type']}'. "
                    f"Must be one of: {', '.join(valid_types)}"
                )
        
        # Validate numeric fields
        numeric_fields = [
            'max_participants', 'min_participants', 'entry_fee_amount',
            'prize_pool', 'entry_fee_deltacoin', 'prize_deltacoin'
        ]
        for field in numeric_fields:
            if field in config:
                try:
                    value = config[field]
                    if isinstance(value, str):
                        if 'amount' in field or 'pool' in field:
                            Decimal(value)
                        else:
                            int(value)
                except (ValueError, TypeError):
                    raise ValidationError(f"Invalid numeric value for '{field}': {config[field]}")
        
        # Validate game-specific rules if game provided
        if game and 'format' in config:
            try:
                # Only validate if game has configuration
                if hasattr(game, 'game_config') and game.game_config:
                    GameConfigService.validate_tournament_against_config(
                        game_id=game.id,
                        tournament_data=config
                    )
            except ValidationError as e:
                raise ValidationError(f"Game configuration validation failed: {str(e)}")
    
    @staticmethod
    def _validate_merged_payload(payload: Dict[str, Any], game: Game) -> None:
        """
        Validate merged payload against game configuration.
        
        Args:
            payload: Merged tournament payload
            game: Game instance
        
        Raises:
            ValidationError: Payload violates game rules
        """
        try:
            # Only validate if game has configuration
            if hasattr(game, 'game_config') and game.game_config:
                GameConfigService.validate_tournament_against_config(
                    game_id=game.id,
                    tournament_data=payload
                )
        except ValidationError as e:
            raise ValidationError(f"Merged payload validation failed: {str(e)}")
    
    @staticmethod
    def _can_modify_template(template: TournamentTemplate, user) -> bool:
        """
        Check if user can modify template.
        
        Rules:
        - Owner can modify
        - Staff can modify
        
        Args:
            template: TournamentTemplate instance
            user: User to check
        
        Returns:
            True if user can modify, False otherwise
        """
        return user.is_staff or template.created_by == user
    
    @staticmethod
    def _can_view_template(template: TournamentTemplate, user) -> bool:
        """
        Check if user can view template.
        
        Rules:
        - GLOBAL: Anyone
        - ORG: Organization members (not enforced, returns True)
        - PRIVATE: Owner only
        
        Args:
            template: TournamentTemplate instance
            user: User to check
        
        Returns:
            True if user can view, False otherwise
        """
        if template.visibility == TournamentTemplate.GLOBAL:
            return True
        
        if template.visibility == TournamentTemplate.ORG:
            # Note: In production, check organization membership
            # For now, allow staff + owner
            return user.is_staff or template.created_by == user
        
        # PRIVATE
        return template.created_by == user or user.is_staff
