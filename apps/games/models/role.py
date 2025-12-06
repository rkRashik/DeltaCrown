"""
Game-specific role models (e.g., Duelist, Controller for Valorant).
"""

from django.db import models


class GameRole(models.Model):
    """
    Game-specific roles for players.
    E.g., Valorant: Duelist, Controller, Initiator, Sentinel
    E.g., Mobile Legends: Tank, Fighter, Assassin, Mage, Marksman, Support
    """
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.CASCADE,
        related_name='roles'
    )
    
    # === ROLE INFO ===
    role_name = models.CharField(
        max_length=50,
        help_text="Role name (e.g., 'Duelist', 'Controller', 'Tank')"
    )
    role_code = models.CharField(
        max_length=20,
        help_text="Short code for role (e.g., 'DUE', 'CTRL', 'TNK')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of role responsibilities"
    )
    
    # === DISPLAY ===
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon identifier or emoji (e.g., '🎯', 'duelist-icon')"
    )
    color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Hex color for role (e.g., '#ff4655')"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order"
    )
    
    # === COMPETITIVE ===
    is_competitive = models.BooleanField(
        default=True,
        help_text="Is this a competitive/ranked role?"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is this role currently active in the meta?"
    )
    
    # === METADATA ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'games_role'
        verbose_name = 'Game Role'
        verbose_name_plural = 'Game Roles'
        ordering = ['game', 'order', 'role_name']
        unique_together = [('game', 'role_name')]
        indexes = [
            models.Index(fields=['game', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.game.name} - {self.role_name}"
