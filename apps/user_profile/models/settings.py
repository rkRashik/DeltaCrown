# apps/user_profile/models/settings.py
"""
Settings Models for User Preferences

Phase 6 Part C: Settings Page Redesign
- NotificationPreferences: Email and platform notification settings
- WalletSettings: Withdrawal methods and preferences for earnings
"""
from django.db import models
from django.core.validators import RegexValidator


class NotificationPreferences(models.Model):
    """
    User notification preferences (UP-PHASE2B).
    
    Controls delivery channels, categories, and timing for notifications.
    
    Channels:
    - Email notifications
    - Push notifications (browser/mobile)
    - SMS notifications (requires phone verification)
    
    Categories:
    - Tournaments (registrations, matches, results)
    - Teams (invites, roster changes, promotions)
    - Bounties (offers, acceptances, completions)
    - Messages (direct messages, chat)
    - System (announcements, maintenance)
    
    Timing:
    - Quiet hours (mute notifications during specified time range)
    """
    user_profile = models.OneToOneField(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='notification_prefs',
        help_text="User profile these preferences belong to"
    )
    
    # ===== CHANNEL TOGGLES (UP-PHASE2B) =====
    email_enabled = models.BooleanField(
        default=True,
        help_text="Receive email notifications"
    )
    push_enabled = models.BooleanField(
        default=True,
        help_text="Receive push notifications (browser/mobile)"
    )
    sms_enabled = models.BooleanField(
        default=False,
        help_text="Receive SMS notifications (requires phone verification)"
    )
    
    # ===== CATEGORY TOGGLES (UP-PHASE2B) =====
    notif_tournaments = models.BooleanField(
        default=True,
        help_text="Tournament updates (registrations, matches, results)"
    )
    notif_teams = models.BooleanField(
        default=True,
        help_text="Team updates (invites, roster changes, promotions)"
    )
    notif_bounties = models.BooleanField(
        default=True,
        help_text="Bounty updates (offers, acceptances, completions)"
    )
    notif_messages = models.BooleanField(
        default=True,
        help_text="Direct messages and chat notifications"
    )
    notif_system = models.BooleanField(
        default=True,
        help_text="System announcements and maintenance alerts"
    )
    
    # ===== QUIET HOURS (UP-PHASE2B) =====
    quiet_hours_enabled = models.BooleanField(
        default=False,
        help_text="Enable quiet hours (mute notifications during specified time)"
    )
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time for quiet hours (e.g., 22:00)"
    )
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text="End time for quiet hours (e.g., 08:00)"
    )
    
    # ===== METADATA =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_notification_preferences'
        verbose_name = 'Notification Preferences'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Notification Preferences for {self.user_profile.display_name or self.user_profile.user.username}"
    
    def clean(self):
        """
        Validate notification preferences.
        
        Business rules:
        - If quiet_hours_enabled, both start and end must be set
        - Quiet hours can wrap over midnight (e.g., 22:00 to 08:00)
        """
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Quiet hours validation
        if self.quiet_hours_enabled:
            if not self.quiet_hours_start:
                errors['quiet_hours_start'] = 'Start time is required when quiet hours are enabled'
            if not self.quiet_hours_end:
                errors['quiet_hours_end'] = 'End time is required when quiet hours are enabled'
        
        if errors:
            raise ValidationError(errors)


class WalletSettings(models.Model):
    """
    Wallet and withdrawal settings for tournament earnings.
    
    Bangladesh mobile banking only for now:
    - bKash (most popular)
    - Nagad (govt-backed)
    - Rocket (DBBL)
    """
    user_profile = models.OneToOneField(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='wallet_settings',
        help_text="User profile these wallet settings belong to"
    )
    
    # ===== WITHDRAWAL METHODS (Bangladesh Mobile Banking) =====
    # bKash
    bkash_enabled = models.BooleanField(
        default=False,
        help_text="Enable bKash as withdrawal method"
    )
    bkash_account = models.CharField(
        max_length=20,
        blank=True,
        default="",
        validators=[
            RegexValidator(
                regex=r'^01[3-9]\d{8}$',
                message="Enter a valid Bangladeshi mobile number (e.g., 01712345678)"
            )
        ],
        help_text="bKash account number (11-digit BD mobile number)"
    )
    
    # Nagad
    nagad_enabled = models.BooleanField(
        default=False,
        help_text="Enable Nagad as withdrawal method"
    )
    nagad_account = models.CharField(
        max_length=20,
        blank=True,
        default="",
        validators=[
            RegexValidator(
                regex=r'^01[3-9]\d{8}$',
                message="Enter a valid Bangladeshi mobile number (e.g., 01712345678)"
            )
        ],
        help_text="Nagad account number (11-digit BD mobile number)"
    )
    
    # Rocket
    rocket_enabled = models.BooleanField(
        default=False,
        help_text="Enable Rocket as withdrawal method"
    )
    rocket_account = models.CharField(
        max_length=20,
        blank=True,
        default="",
        validators=[
            RegexValidator(
                regex=r'^01[3-9]\d{8}$',
                message="Enter a valid Bangladeshi mobile number (e.g., 01712345678)"
            )
        ],
        help_text="Rocket account number (11-digit BD mobile number)"
    )
    
    # ===== WITHDRAWAL PREFERENCES =====
    auto_withdrawal_threshold = models.IntegerField(
        default=0,
        help_text="Automatically withdraw when balance reaches this threshold (DeltaCoins). 0 = manual withdrawals only"
    )
    auto_convert_to_usd = models.BooleanField(
        default=False,
        help_text="Automatically convert DeltaCoins to USD when withdrawing (subject to conversion rates)"
    )
    
    # ===== METADATA =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_wallet_settings'
        verbose_name = 'Wallet Settings'
        verbose_name_plural = 'Wallet Settings'
    
    def __str__(self):
        return f"Wallet Settings for {self.user_profile.display_name}"
    
    def get_enabled_methods(self):
        """Return list of enabled withdrawal methods."""
        methods = []
        if self.bkash_enabled and self.bkash_account:
            methods.append('bKash')
        if self.nagad_enabled and self.nagad_account:
            methods.append('Nagad')
        if self.rocket_enabled and self.rocket_account:
            methods.append('Rocket')
        return methods
