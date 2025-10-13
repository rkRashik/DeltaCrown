"""
Player Role Configuration Model

Stores available roles for each game (Duelist, IGL, Pos 1-5, etc.).
Enables role-based team composition and validation.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class PlayerRoleConfiguration(models.Model):
    """
    Defines available player roles for each game.
    
    Different games have different roles:
    - Valorant: Duelist, Controller, Initiator, Sentinel, IGL
    - Dota 2: Position 1-5 (Carry, Mid, Offlaner, Soft Support, Hard Support)
    - CS2: IGL, Entry Fragger, AWPer, Lurker, Support
    - MLBB: Gold Laner, EXP Laner, Mid Laner, Jungler, Roamer
    
    Some roles are unique (only one per team, e.g., IGL).
    """
    
    # Relationship
    game = models.ForeignKey(
        'GameConfiguration',
        on_delete=models.CASCADE,
        related_name='role_configurations',
        help_text=_("The game this role belongs to")
    )
    
    # Role identification
    role_code = models.CharField(
        max_length=50,
        help_text=_("Internal role identifier (e.g., 'duelist', 'igl', 'pos_1')")
    )
    
    role_name = models.CharField(
        max_length=100,
        help_text=_("Display name for the role (e.g., 'Duelist', 'In-Game Leader', 'Position 1 - Carry')")
    )
    
    role_abbreviation = models.CharField(
        max_length=10,
        blank=True,
        help_text=_("Short abbreviation (e.g., 'IGL', 'Pos 1', 'AWP')")
    )
    
    # Role constraints
    is_unique = models.BooleanField(
        default=False,
        help_text=_("Can only one player have this role per team? (e.g., IGL)")
    )
    
    is_required = models.BooleanField(
        default=False,
        help_text=_("Must at least one player have this role?")
    )
    
    max_per_team = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum number of players with this role (null = no limit)")
    )
    
    # Display
    description = models.TextField(
        blank=True,
        help_text=_("Description of the role's responsibilities")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order in which roles appear in dropdowns")
    )
    
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("CSS icon class or image (e.g., 'fas fa-crosshairs')")
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=_("Is this role currently available for selection?")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournaments_player_role_configuration'
        verbose_name = _("Player Role Configuration")
        verbose_name_plural = _("Player Role Configurations")
        ordering = ['game', 'display_order', 'role_name']
        unique_together = [['game', 'role_code']]
        indexes = [
            models.Index(fields=['game', 'is_active']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        if self.role_abbreviation:
            return f"{self.game.display_name} - {self.role_name} ({self.role_abbreviation})"
        return f"{self.game.display_name} - {self.role_name}"
    
    def clean(self):
        """Validate model constraints."""
        super().clean()
        
        # If unique, max_per_team should be 1 or None
        if self.is_unique and self.max_per_team and self.max_per_team > 1:
            raise ValidationError(
                _("A unique role cannot have max_per_team greater than 1.")
            )
        
        # max_per_team validation
        if self.max_per_team is not None and self.max_per_team < 1:
            raise ValidationError({
                'max_per_team': _("Maximum per team must be at least 1 if specified.")
            })
    
    @classmethod
    def get_available_roles(cls, game_code, exclude_assigned=None):
        """
        Get available roles for a game, optionally excluding already assigned roles.
        
        Args:
            game_code: The game identifier
            exclude_assigned: List of role_codes already assigned to other players
            
        Returns:
            QuerySet of available PlayerRoleConfiguration objects
        """
        queryset = cls.objects.filter(
            game__game_code=game_code,
            is_active=True
        ).select_related('game')
        
        # If we have assigned roles, filter out unique roles that are taken
        if exclude_assigned:
            # Get unique roles that are in the exclude list
            taken_unique_roles = cls.objects.filter(
                game__game_code=game_code,
                role_code__in=exclude_assigned,
                is_unique=True
            ).values_list('role_code', flat=True)
            
            # Exclude those roles
            if taken_unique_roles:
                queryset = queryset.exclude(role_code__in=taken_unique_roles)
        
        return queryset.order_by('display_order', 'role_name')
    
    @classmethod
    def validate_team_roles(cls, game_code, role_assignments):
        """
        Validate a team's role assignments against the game's role rules.
        
        Args:
            game_code: The game identifier
            role_assignments: List of role_codes assigned to team members
            
        Returns:
            tuple: (is_valid, errors_list)
        """
        errors = []
        
        # Get all role configurations for this game
        roles = cls.objects.filter(
            game__game_code=game_code,
            is_active=True
        ).select_related('game')
        
        # Check required roles
        required_roles = roles.filter(is_required=True)
        for role in required_roles:
            if role.role_code not in role_assignments:
                errors.append(f"Required role '{role.role_name}' is missing.")
        
        # Check unique roles
        unique_roles = roles.filter(is_unique=True)
        for role in unique_roles:
            count = role_assignments.count(role.role_code)
            if count > 1:
                errors.append(f"Role '{role.role_name}' can only be assigned to one player (found {count}).")
        
        # Check max_per_team constraints
        roles_with_max = roles.exclude(max_per_team__isnull=True)
        for role in roles_with_max:
            count = role_assignments.count(role.role_code)
            if count > role.max_per_team:
                errors.append(
                    f"Role '{role.role_name}' can have at most {role.max_per_team} "
                    f"player(s) (found {count})."
                )
        
        return len(errors) == 0, errors
