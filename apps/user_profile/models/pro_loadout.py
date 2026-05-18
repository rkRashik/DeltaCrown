"""
Pro Loadout Models — full platform-aware esports loadout system.

UserLoadoutProfile  — 1:1 with UserProfile; primary platform + visibility.
LoadoutDevice       — individual hardware/device entries (replaces HardwareGear for UI).
GameLoadoutSetting  — per-game, per-platform in-game settings.

Backward-compat: existing HardwareLoadout and HardwareGear rows are untouched.
The Gear tab reads from LoadoutDevice first, falls back to HardwareLoadout.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class UserLoadoutProfile(models.Model):
    class Platform(models.TextChoices):
        PC      = 'PC',      _('PC')
        MOBILE  = 'MOBILE',  _('Mobile')
        CONSOLE = 'CONSOLE', _('Console')
        HYBRID  = 'HYBRID',  _('Hybrid / Multiple')

    class Visibility(models.TextChoices):
        PUBLIC  = 'PUBLIC',  _('Public')
        PRIVATE = 'PRIVATE', _('Private')

    user_profile = models.OneToOneField(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='pro_loadout',
    )
    primary_platform = models.CharField(
        max_length=10, choices=Platform.choices, default=Platform.PC,
    )
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profile_user_loadout_profile'
        verbose_name = 'Pro Loadout Profile'

    def __str__(self):
        return f"{self.user_profile} — {self.primary_platform}"

    @property
    def is_public(self):
        return self.visibility == self.Visibility.PUBLIC


class LoadoutDevice(models.Model):
    class Category(models.TextChoices):
        MOUSE         = 'MOUSE',         _('Mouse')
        KEYBOARD      = 'KEYBOARD',      _('Keyboard')
        HEADSET       = 'HEADSET',       _('Headset')
        MONITOR       = 'MONITOR',       _('Monitor')
        CONTROLLER    = 'CONTROLLER',    _('Controller')
        MOBILE_DEVICE = 'MOBILE_DEVICE', _('Mobile Device')
        TABLET        = 'TABLET',        _('Tablet')
        CONSOLE       = 'CONSOLE',       _('Console')
        MICROPHONE    = 'MICROPHONE',    _('Microphone')
        CHAIR         = 'CHAIR',         _('Chair')
        MOUSEPAD      = 'MOUSEPAD',      _('Mousepad')
        OTHER         = 'OTHER',         _('Other')

    loadout = models.ForeignKey(
        UserLoadoutProfile,
        on_delete=models.CASCADE,
        related_name='devices',
    )
    category    = models.CharField(max_length=20, choices=Category.choices)
    brand       = models.CharField(max_length=100, blank=True, default='')
    model_name  = models.CharField(max_length=200, blank=True, default='')
    notes       = models.CharField(max_length=300, blank=True, default='')
    is_featured = models.BooleanField(default=False)
    order       = models.PositiveSmallIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profile_loadout_device'
        ordering = ['order', 'category']
        verbose_name = 'Loadout Device'

    def __str__(self):
        return f"{self.get_category_display()}: {self.brand} {self.model_name}".strip()

    @property
    def display_name(self):
        parts = [p for p in [self.brand, self.model_name] if p]
        return ' '.join(parts) or self.get_category_display()


class GameLoadoutSetting(models.Model):
    class Platform(models.TextChoices):
        PC      = 'PC',      _('PC')
        MOBILE  = 'MOBILE',  _('Mobile')
        CONSOLE = 'CONSOLE', _('Console')

    class Visibility(models.TextChoices):
        PUBLIC  = 'PUBLIC',  _('Public')
        PRIVATE = 'PRIVATE', _('Private')

    loadout  = models.ForeignKey(
        UserLoadoutProfile, on_delete=models.CASCADE, related_name='game_settings',
    )
    game     = models.ForeignKey('games.Game', on_delete=models.CASCADE, related_name='pro_loadout_settings')
    platform = models.CharField(max_length=10, choices=Platform.choices, default=Platform.PC)

    # ── PC / FPS sensitivity ──────────────────────────────────────
    mouse_dpi           = models.PositiveIntegerField(null=True, blank=True)
    in_game_sensitivity = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    scoped_sensitivity  = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    ads_sensitivity     = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    crosshair_code      = models.CharField(max_length=200, blank=True, default='')

    # ── PC display ────────────────────────────────────────────────
    resolution    = models.CharField(max_length=20, blank=True, default='')  # e.g. "1920x1080"
    refresh_rate  = models.PositiveSmallIntegerField(null=True, blank=True)  # Hz
    fps_cap       = models.PositiveSmallIntegerField(null=True, blank=True)
    graphics_quality = models.CharField(max_length=50, blank=True, default='')

    # ── Mobile ────────────────────────────────────────────────────
    gyro_enabled    = models.BooleanField(null=True, blank=True)
    gyro_sensitivity = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hud_code        = models.CharField(max_length=200, blank=True, default='')
    claw_style      = models.CharField(max_length=50, blank=True, default='')  # e.g. "4-finger claw"

    # ── Console / Controller ──────────────────────────────────────
    controller_model       = models.CharField(max_length=100, blank=True, default='')
    horizontal_sensitivity = models.PositiveSmallIntegerField(null=True, blank=True)
    vertical_sensitivity   = models.PositiveSmallIntegerField(null=True, blank=True)
    deadzone_left          = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    deadzone_right         = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    aim_assist             = models.CharField(max_length=50, blank=True, default='')

    notes      = models.TextField(blank=True, default='')
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profile_game_loadout_setting'
        unique_together = [('loadout', 'game', 'platform')]
        ordering = ['game__name', 'platform']
        verbose_name = 'Game Loadout Setting'

    def __str__(self):
        return f"{self.game.name} ({self.platform})"

    @property
    def edpi(self):
        if self.mouse_dpi and self.in_game_sensitivity:
            try:
                return round(float(self.mouse_dpi) * float(self.in_game_sensitivity), 1)
            except Exception:
                return None
        return None
