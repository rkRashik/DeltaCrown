"""
Core Game model - single source of truth for game configuration.
"""

from django.db import models
from django.core.validators import RegexValidator
from django.utils.text import slugify


class Game(models.Model):
    """
    Canonical game definition.
    THE SINGLE SOURCE OF TRUTH for all game configuration.
    """
    
    # === BASIC INFO ===
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Technical name (e.g., 'Valorant')"
    )
    display_name = models.CharField(
        max_length=150,
        help_text="Display name (e.g., 'VALORANT™')"
    )
    slug = models.SlugField(
        unique=True,
        db_index=True,
        help_text="URL-safe identifier (e.g., 'valorant')"
    )
    short_code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short identifier (e.g., 'VAL', 'CS2', 'PUBGM')"
    )
    
    # === CLASSIFICATION ===
    CATEGORY_CHOICES = [
        ('FPS', 'First-Person Shooter'),
        ('MOBA', 'Multiplayer Online Battle Arena'),
        ('BR', 'Battle Royale'),
        ('SPORTS', 'Sports/Esports Simulation'),
        ('FIGHTING', 'Fighting Game'),
        ('STRATEGY', 'Strategy'),
        ('CCG', 'Card Game'),
        ('OTHER', 'Other'),
    ]
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        db_index=True
    )
    
    TYPE_CHOICES = [
        ('TEAM_VS_TEAM', 'Team vs Team'),
        ('1V1', '1 vs 1'),
        ('BATTLE_ROYALE', 'Battle Royale'),
        ('FREE_FOR_ALL', 'Free-for-All'),
    ]
    game_type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        default='TEAM_VS_TEAM'
    )
    
    platforms = models.JSONField(
        default=list,
        help_text="List of platforms: ['PC', 'Mobile', 'Console']"
    )
    
    has_servers = models.BooleanField(
        default=False,
        help_text="Does this game have regional servers that affect gameplay/ranking?"
    )
    
    # === RANKS/TIERS ===
    has_rank_system = models.BooleanField(
        default=False,
        help_text="Does this game have a competitive rank/tier system?"
    )
    available_ranks = models.JSONField(
        default=list,
        blank=True,
        help_text="Game-specific ranks: [{'value': 'iron', 'label': 'Iron'}, ...]"
    )
    
    # === MEDIA ===
    icon = models.ImageField(
        upload_to='games/icons/',
        null=True,
        blank=True
    )
    logo = models.ImageField(
        upload_to='games/logos/',
        null=True,
        blank=True
    )
    banner = models.ImageField(
        upload_to='games/banners/',
        null=True,
        blank=True
    )
    card_image = models.ImageField(
        upload_to='games/cards/',
        null=True,
        blank=True
    )
    
    # === BRANDING ===
    primary_color = models.CharField(
        max_length=7,
        default='#7c3aed',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$')],
        help_text="Hex color code (e.g., #7c3aed)"
    )
    secondary_color = models.CharField(
        max_length=7,
        default='#1e1b4b',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$')]
    )
    accent_color = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$')]
    )
    
    # === STATUS ===
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Is this game available for tournaments/teams?"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured on homepage?"
    )
    is_passport_supported = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Does this game support Game Passport functionality? (Admin filter)"
    )
    release_date = models.DateField(
        null=True,
        blank=True
    )
    
    # === METADATA ===
    description = models.TextField(
        blank=True,
        help_text="Game description for display"
    )
    official_website = models.URLField(
        blank=True
    )
    developer = models.CharField(
        max_length=100,
        blank=True
    )
    publisher = models.CharField(
        max_length=100,
        blank=True
    )

    # === GAME ID CUSTOMISATION ===
    game_id_label = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=(
            "Custom label for a player's in-game identifier "
            "(e.g. 'Riot ID' for Valorant, 'Steam ID' for CS2, 'UID' for PUBG Mobile). "
            "Leave blank to use the default 'Game ID'."
        ),
    )
    game_id_placeholder = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=(
            "Placeholder text shown in the Game ID input field "
            "(e.g. 'Username#TAG'). Leave blank for a generic placeholder."
        ),
    )

    # === SYSTEM ===
    created_by = models.ForeignKey(
        'user_profile.UserProfile',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_games'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        db_table = 'games_game'
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'is_featured']),
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        return self.display_name

    @property
    def primary_color_rgb(self):
        """Convert hex primary_color to 'R, G, B' string for CSS rgba() usage."""
        hex_color = self.primary_color or '#7c3aed'
        hex_color = hex_color.lstrip('#')
        try:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            return f"{r}, {g}, {b}"
        except (ValueError, IndexError):
            return "6, 182, 212"

    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.display_name:
            self.display_name = self.name
        super().save(*args, **kwargs)
    
    def get_roster_config(self):
        """Get roster configuration for this game."""
        return getattr(self, 'roster_config', None)
    
    def get_tournament_config(self):
        """Get tournament configuration for this game."""
        return getattr(self, 'tournament_config', None)
    
    def get_identity_configs(self):
        """Get all player identity configurations."""
        return self.identity_configs.all()
    
    def get_roles(self):
        """Get all game-specific roles."""
        return self.roles.all()
