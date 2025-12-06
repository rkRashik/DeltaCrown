"""
Roster configuration models for game-specific team structure.
"""

from django.db import models


class GameRosterConfig(models.Model):
    """
    Team roster specifications for a game.
    Defines how teams are structured.
    """
    game = models.OneToOneField(
        'games.Game',
        on_delete=models.CASCADE,
        related_name='roster_config'
    )
    
    # === TEAM SIZE (players on field) ===
    min_team_size = models.IntegerField(
        default=1,
        help_text="Minimum players on field during match"
    )
    max_team_size = models.IntegerField(
        default=5,
        help_text="Maximum players on field during match"
    )
    
    # === SUBSTITUTES ===
    min_substitutes = models.IntegerField(
        default=0,
        help_text="Minimum substitute players"
    )
    max_substitutes = models.IntegerField(
        default=2,
        help_text="Maximum substitute players"
    )
    
    # === TOTAL ROSTER ===
    min_roster_size = models.IntegerField(
        default=1,
        help_text="Minimum total roster size (including subs)"
    )
    max_roster_size = models.IntegerField(
        default=10,
        help_text="Maximum total roster size (including subs)"
    )
    
    # === STAFF ===
    allow_coaches = models.BooleanField(
        default=True,
        help_text="Allow coaches on roster?"
    )
    max_coaches = models.IntegerField(
        default=2,
        help_text="Maximum number of coaches"
    )
    
    allow_analysts = models.BooleanField(
        default=True,
        help_text="Allow analysts on roster?"
    )
    max_analysts = models.IntegerField(
        default=1,
        help_text="Maximum number of analysts"
    )
    
    allow_managers = models.BooleanField(
        default=True,
        help_text="Allow managers on roster?"
    )
    max_managers = models.IntegerField(
        default=2,
        help_text="Maximum number of managers"
    )
    
    # === ROLE SYSTEM ===
    has_roles = models.BooleanField(
        default=False,
        help_text="Does this game have defined roles (e.g., Duelist, Support)?"
    )
    require_unique_roles = models.BooleanField(
        default=False,
        help_text="Each role can only be filled by one player"
    )
    allow_multi_role = models.BooleanField(
        default=True,
        help_text="Can players have multiple roles?"
    )
    
    # === REGIONS ===
    has_regions = models.BooleanField(
        default=False,
        help_text="Does this game have regional restrictions?"
    )
    available_regions = models.JSONField(
        default=list,
        help_text="[{'code': 'NA', 'name': 'North America'}, ...]"
    )
    
    # === GAME-SPECIFIC RULES ===
    extra_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional game-specific roster rules (JSON)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'games_roster_config'
        verbose_name = 'Roster Configuration'
        verbose_name_plural = 'Roster Configurations'
    
    def __str__(self):
        return f"{self.game.name} - Roster Config"
    
    def get_team_size_display(self):
        """Get human-readable team size (e.g., '5v5')."""
        if self.min_team_size == self.max_team_size:
            return f"{self.max_team_size}v{self.max_team_size}"
        return f"{self.min_team_size}-{self.max_team_size}"
    
    def validate_roster_size(self, total_players, total_subs):
        """
        Validate roster size against configuration.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        total = total_players + total_subs
        
        if total < self.min_roster_size:
            return False, f"Roster too small. Minimum {self.min_roster_size} players required."
        
        if total > self.max_roster_size:
            return False, f"Roster too large. Maximum {self.max_roster_size} players allowed."
        
        if total_players < self.min_team_size:
            return False, f"Not enough starting players. Minimum {self.min_team_size} required."
        
        if total_players > self.max_team_size:
            return False, f"Too many starting players. Maximum {self.max_team_size} allowed."
        
        if total_subs < self.min_substitutes:
            return False, f"Not enough substitutes. Minimum {self.min_substitutes} required."
        
        if total_subs > self.max_substitutes:
            return False, f"Too many substitutes. Maximum {self.max_substitutes} allowed."
        
        return True, None
