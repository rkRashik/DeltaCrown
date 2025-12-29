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
    User notification preferences for email and platform notifications.
    
    Controls how/when the platform contacts the user about events.
    Separate from PrivacySettings (what others can see).
    """
    user_profile = models.OneToOneField(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='notification_prefs',
        help_text="User profile these preferences belong to"
    )
    
    # ===== EMAIL NOTIFICATIONS =====
    email_tournament_reminders = models.BooleanField(
        default=True,
        help_text="Send email reminders for upcoming tournaments you're registered for"
    )
    email_match_results = models.BooleanField(
        default=True,
        help_text="Send email notifications when match results are published"
    )
    email_team_invites = models.BooleanField(
        default=True,
        help_text="Send email when invited to join a team"
    )
    email_achievements = models.BooleanField(
        default=False,
        help_text="Send email when you unlock new achievements or badges"
    )
    email_platform_updates = models.BooleanField(
        default=True,
        help_text="Send email about platform updates, new features, and announcements"
    )
    
    # ===== PLATFORM NOTIFICATIONS (In-App) =====
    notify_tournament_start = models.BooleanField(
        default=True,
        help_text="Show notification when a tournament you're in starts"
    )
    notify_team_messages = models.BooleanField(
        default=True,
        help_text="Show notification for new team messages"
    )
    notify_follows = models.BooleanField(
        default=True,
        help_text="Show notification when someone follows you"
    )
    notify_achievements = models.BooleanField(
        default=True,
        help_text="Show notification popup when unlocking achievements"
    )
    
    # ===== METADATA =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_notification_preferences'
        verbose_name = 'Notification Preferences'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Notification Preferences for {self.user_profile.display_name}"


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
