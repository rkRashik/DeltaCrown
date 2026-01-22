from __future__ import annotations

from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        REG_CONFIRMED = "reg_confirmed", "Registration confirmed"
        BRACKET_READY = "bracket_ready", "Bracket generated"
        MATCH_SCHEDULED = "match_scheduled", "Match scheduled"
        RESULT_VERIFIED = "result_verified", "Result verified"
        PAYMENT_VERIFIED = "payment_verified", "Payment verified"
        CHECKIN_OPEN = "checkin_open", "Check-in window open"
        GENERIC = "generic", "Generic"
        # Task 9 - New notification types
        INVITE_SENT = "invite_sent", "Team invite sent"
        INVITE_ACCEPTED = "invite_accepted", "Team invite accepted"
        ROSTER_CHANGED = "roster_changed", "Team roster changed"
        TOURNAMENT_REGISTERED = "tournament_registered", "Tournament registered"
        MATCH_RESULT = "match_result", "Match result posted"
        RANKING_CHANGED = "ranking_changed", "Team ranking changed"
        SPONSOR_APPROVED = "sponsor_approved", "Sponsor approved"
        PROMOTION_STARTED = "promotion_started", "Promotion started"
        PAYOUT_RECEIVED = "payout_received", "Payout received"
        ACHIEVEMENT_EARNED = "achievement_earned", "Achievement earned"
        # UP PHASE 8: Follow Requests
        FOLLOW_REQUEST = "follow_request", "Follow request received"
        # Social Notifications (PHASE 9: Follow System Completion)
        USER_FOLLOWED = "user_followed", "User followed you"
        POST_LIKED = "post_liked", "Post liked"
        COMMENT_ADDED = "comment_added", "Comment added"
        POST_SHARED = "post_shared", "Post shared"
        MENTION = "mention", "Mentioned in post"
        FOLLOW_REQUEST_APPROVED = "follow_request_approved", "Follow request approved"
        FOLLOW_REQUEST_REJECTED = "follow_request_rejected", "Follow request rejected"

    event = models.CharField(max_length=64, db_index=True, default="generic")
    type = models.CharField(max_length=40, choices=Type.choices, db_index=True, default=Type.GENERIC)

    title = models.CharField(max_length=140)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False, help_text="Whether notification was successfully delivered via SSE/WebSocket")
    created_at = models.DateTimeField(auto_now_add=True)

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    
    # Phase 4: Additional fields for actionable notifications
    action_label = models.CharField(max_length=255, blank=True, help_text="CTA button text (e.g., 'View Request', 'Approve')")
    action_url = models.CharField(max_length=500, blank=True, help_text="URL for primary action button")
    category = models.CharField(max_length=100, blank=True, db_index=True, help_text="Notification category (e.g., 'social', 'system')")
    message = models.TextField(blank=True, help_text="Alternative message text for display")
    
    # Phase 4 Step 2.1: Stable linkage to action objects (e.g., FollowRequest ID for follow_request notifications)
    action_object_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="ID of related object (e.g., FollowRequest.id for follow_request type)")
    action_type = models.CharField(max_length=50, blank=True, db_index=True, help_text="Type of action object (e.g., 'follow_request')")

    # NOTE: Changed to IntegerField - tournament app moved to legacy (Nov 2, 2025)
    # Stores legacy tournament/match IDs for historical reference
    tournament_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Legacy tournament ID (reference only)")
    match_id = models.IntegerField(null=True, blank=True, help_text="Legacy match ID (reference only)")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
            models.Index(fields=["recipient", "type"]),
        ]

    def __str__(self) -> str:
        return f"{self.event or self.type}: {self.title}"

    def save(self, *args, **kwargs):
        if not self.event:
            self.event = self.type or self.Type.GENERIC
        if self.type not in self.Type.values:
            self.type = self.Type.GENERIC
        super().save(*args, **kwargs)


class NotificationPreference(models.Model):
    """
    User preferences for notification delivery channels.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences"
    )
    
    # Channel preferences for each notification type
    invite_sent_channels = models.JSONField(default=list, blank=True)
    invite_accepted_channels = models.JSONField(default=list, blank=True)
    roster_changed_channels = models.JSONField(default=list, blank=True)
    tournament_registered_channels = models.JSONField(default=list, blank=True)
    match_result_channels = models.JSONField(default=list, blank=True)
    ranking_changed_channels = models.JSONField(default=list, blank=True)
    sponsor_approved_channels = models.JSONField(default=list, blank=True)
    promotion_started_channels = models.JSONField(default=list, blank=True)
    payout_received_channels = models.JSONField(default=list, blank=True)
    achievement_earned_channels = models.JSONField(default=list, blank=True)
    
    # Digest preferences
    enable_daily_digest = models.BooleanField(default=True)
    digest_time = models.TimeField(default='08:00:00')  # 8 AM by default
    
    # Global opt-outs
    opt_out_email = models.BooleanField(default=False)
    opt_out_in_app = models.BooleanField(default=False)
    opt_out_discord = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"
    
    def __str__(self):
        return f"Notification preferences for {self.user.username}"
    
    def get_channels_for_type(self, notification_type):
        """Get enabled channels for a specific notification type."""
        from django.conf import settings
        
        # Get the field name
        field_name = f"{notification_type}_channels"
        
        # Get user preferences or use defaults
        if hasattr(self, field_name):
            channels = getattr(self, field_name) or []
        else:
            # Use default preferences from settings
            default_prefs = getattr(settings, 'DEFAULT_NOTIFICATION_PREFERENCES', {})
            channels = default_prefs.get(notification_type, ['in_app'])
        
        # Apply global opt-outs
        if self.opt_out_email and 'email' in channels:
            channels.remove('email')
        if self.opt_out_in_app and 'in_app' in channels:
            channels.remove('in_app')
        if self.opt_out_discord and 'discord' in channels:
            channels.remove('discord')
        
        return channels
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create notification preferences for a user with defaults."""
        from django.conf import settings
        
        preference, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'invite_sent_channels': ['in_app', 'email'],
                'invite_accepted_channels': ['in_app', 'email'],
                'roster_changed_channels': ['in_app'],
                'tournament_registered_channels': ['in_app', 'email'],
                'match_result_channels': ['in_app', 'email'],
                'ranking_changed_channels': ['in_app'],
                'sponsor_approved_channels': ['in_app', 'email'],
                'promotion_started_channels': ['in_app'],
                'payout_received_channels': ['in_app', 'email'],
                'achievement_earned_channels': ['in_app', 'email'],
            }
        )
        return preference


class NotificationDigest(models.Model):
    """
    Daily digest of notifications for batched delivery.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_digests"
    )
    
    digest_date = models.DateField()
    notifications = models.ManyToManyField(Notification, related_name="digests")
    
    sent_at = models.DateTimeField(null=True, blank=True)
    is_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['user', 'digest_date']]
        ordering = ['-digest_date']
        indexes = [
            models.Index(fields=['user', 'digest_date', 'is_sent']),
        ]
    
    def __str__(self):
        return f"Digest for {self.user.username} on {self.digest_date}"

