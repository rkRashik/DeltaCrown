"""
Loadout Models - Pro Settings Engine (P0)

Models:
- HardwareGear: User's hardware setup (mouse, keyboard, headset, monitor, mousepad)
- GameConfig: Per-game configuration settings (sensitivity, crosshair, keybinds, graphics)

Design Reference: 03c_loadout_and_live_status_design.md
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# ============================================================================
# HARDWARE GEAR MODEL
# ============================================================================

class HardwareGear(models.Model):
    """
    User's hardware setup for competitive gaming.
    
    Stores peripherals and their configurations (DPI, polling rate, etc.).
    One entry per hardware category per user.
    
    Privacy:
    - Visibility controlled by user profile privacy settings
    - No separate privacy controls at hardware level (MVP)
    
    Categories:
    - MOUSE: Gaming mouse (DPI, polling rate, weight)
    - KEYBOARD: Gaming keyboard (switch type, layout)
    - HEADSET: Gaming headset (wired/wireless, surround sound)
    - MONITOR: Gaming monitor (refresh rate, resolution, panel type)
    - MOUSEPAD: Gaming mousepad (size, surface type)
    
    Usage:
    - Display in "Loadout" tab on profile
    - Filter players by hardware ("Show all players using X mouse")
    - Optional affiliate links for e-commerce
    """
    
    class HardwareCategory(models.TextChoices):
        MOUSE = 'MOUSE', _('Mouse')
        KEYBOARD = 'KEYBOARD', _('Keyboard')
        HEADSET = 'HEADSET', _('Headset')
        MONITOR = 'MONITOR', _('Monitor')
        MOUSEPAD = 'MOUSEPAD', _('Mousepad')
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hardware_gear'
    )
    
    category = models.CharField(
        max_length=20,
        choices=HardwareCategory.choices,
        help_text="Hardware category (mouse, keyboard, etc.)"
    )
    
    # Hardware identification
    brand = models.CharField(
        max_length=100,
        help_text="Brand name (e.g., Logitech, Razer, SteelSeries)"
    )
    
    model = models.CharField(
        max_length=200,
        help_text="Product model (e.g., G Pro X Superlight)"
    )
    
    # Specifications (stored as JSON for flexibility)
    specs = models.JSONField(
        default=dict,
        blank=True,
        help_text="Hardware specifications (DPI, polling rate, weight, etc.)"
    )
    
    # Optional affiliate link (e-commerce integration)
    purchase_url = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text="Optional purchase link (affiliate URL)"
    )
    
    # Privacy control
    is_public = models.BooleanField(
        default=True,
        help_text="Show on public profile (owner-only if False)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_hardware_gear'
        verbose_name = 'Hardware Gear'
        verbose_name_plural = 'Hardware Gear'
        ordering = ['category', '-updated_at']
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['brand', 'model']),
            models.Index(fields=['category', 'is_public']),
        ]
        constraints = [
            # One hardware item per category per user
            models.UniqueConstraint(
                fields=['user', 'category'],
                name='unique_hardware_per_category_per_user'
            )
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_category_display()}: {self.brand} {self.model}"
    
    def clean(self):
        """Validate hardware gear data."""
        super().clean()
        
        # Validate brand and model not empty
        if not self.brand or not self.brand.strip():
            raise ValidationError({'brand': 'Brand cannot be empty'})
        
        if not self.model or not self.model.strip():
            raise ValidationError({'model': 'Model cannot be empty'})
        
        # Validate purchase_url if provided
        if self.purchase_url:
            from apps.user_profile.services.url_validator import validate_affiliate_url
            try:
                validate_affiliate_url(self.purchase_url)
            except ValueError as e:
                raise ValidationError({'purchase_url': str(e)})
    
    def save(self, *args, **kwargs):
        """Override save to enforce validation."""
        self.full_clean()
        super().save(*args, **kwargs)


# ============================================================================
# GAME CONFIG MODEL
# ============================================================================

class GameConfig(models.Model):
    """
    Per-game configuration settings for competitive players.
    
    Stores game-specific settings (sensitivity, crosshair, keybinds, graphics).
    One config per user per game (uniqueness constraint).
    
    Privacy:
    - is_public: Show on public profile (True) or owner-only (False)
    - Allows players to share some configs but hide others
    
    Settings Structure (JSON):
    - Valorant: {"sensitivity": 0.45, "dpi": 800, "crosshair_style": "small_dot", ...}
    - CS2: {"sensitivity": 1.2, "dpi": 800, "viewmodel_fov": 68, ...}
    - PUBG: {"sensitivity": 50, "vehicle_controls": {...}, ...}
    
    Each game has different schema (no shared fields across games).
    Settings validation done via GameSettingsSchema (future phase).
    
    Usage:
    - Display in "Loadout" tab on profile
    - Filter players by settings ("Show Valorant players with sens 0.3-0.5")
    - Copy pro settings to own config
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='game_configs'
    )
    
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.CASCADE,
        related_name='user_configs',
        help_text="Game this configuration applies to"
    )
    
    # Game-specific settings (flexible JSON structure)
    settings = models.JSONField(
        default=dict,
        help_text="Game-specific configuration (sensitivity, crosshair, keybinds, etc.)"
    )
    
    # Privacy control
    is_public = models.BooleanField(
        default=True,
        help_text="Show on public profile (owner-only if False)"
    )
    
    # Optional notes
    notes = models.TextField(
        blank=True,
        default='',
        max_length=500,
        help_text="Optional notes about this config (e.g., 'Tournament setup')"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_game_config'
        verbose_name = 'Game Configuration'
        verbose_name_plural = 'Game Configurations'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'game']),
            models.Index(fields=['game', 'is_public']),
            models.Index(fields=['user', 'is_public']),
        ]
        constraints = [
            # One config per user per game
            models.UniqueConstraint(
                fields=['user', 'game'],
                name='unique_game_config_per_user_per_game'
            )
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.game.name} Config"
    
    def clean(self):
        """Validate game config data."""
        super().clean()
        
        # Validate settings is a dict
        if not isinstance(self.settings, dict):
            raise ValidationError({'settings': 'Settings must be a dictionary'})
        
        # Validate notes length
        if self.notes and len(self.notes) > 500:
            raise ValidationError({'notes': 'Notes cannot exceed 500 characters'})
    
    def save(self, *args, **kwargs):
        """Override save to enforce validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_effective_dpi(self):
        """
        Calculate effective DPI (eDPI) for comparison.
        
        eDPI = sensitivity * DPI
        
        Returns:
            float or None: eDPI if sensitivity and dpi present in settings
        """
        sensitivity = self.settings.get('sensitivity')
        dpi = self.settings.get('dpi')
        
        if sensitivity is not None and dpi is not None:
            try:
                return float(sensitivity) * float(dpi)
            except (ValueError, TypeError):
                return None
        return None


# ============================================================================
# SIMPLE HARDWARE LOADOUT (Phase 4)
# ============================================================================

class HardwareLoadout(models.Model):
    """
    Simple hardware loadout for profile showcase.
    Maps directly to Loadout tab inputs in settings_control_deck.html.
    
    Phase 4B: Backend persistence for previously non-functional Loadout tab.
    This is a simpler alternative to HardwareGear for basic profile display.
    """
    user_profile = models.OneToOneField(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='hardware_loadout',
        help_text="User profile this hardware loadout belongs to"
    )
    
    # ===== PERIPHERAL GEAR (Simple Text Fields) =====
    mouse_brand = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Mouse brand/model (e.g., 'Logitech G Pro X Superlight')"
    )
    
    keyboard_brand = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Keyboard brand/model (e.g., 'Wooting 60HE')"
    )
    
    headset_brand = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Headset brand/model (e.g., 'HyperX Cloud II')"
    )
    
    monitor_brand = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Monitor brand/model (e.g., 'BenQ Zowie XL2546K 240Hz')"
    )
    
    # ===== METADATA =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_hardware_loadout'
        verbose_name = 'Hardware Loadout'
        verbose_name_plural = 'Hardware Loadouts'
    
    def __str__(self):
        return f"{self.user_profile.display_name} - Hardware Loadout"
    
    def get_gear_summary(self):
        """Return list of non-empty gear items for display."""
        gear = []
        if self.mouse_brand:
            gear.append(('Mouse', self.mouse_brand))
        if self.keyboard_brand:
            gear.append(('Keyboard', self.keyboard_brand))
        if self.headset_brand:
            gear.append(('Headset', self.headset_brand))
        if self.monitor_brand:
            gear.append(('Monitor', self.monitor_brand))
        return gear
    
    @property
    def is_complete(self):
        """Check if loadout has at least one hardware item."""
        return bool(self.mouse_brand or self.keyboard_brand or self.headset_brand or self.monitor_brand)
