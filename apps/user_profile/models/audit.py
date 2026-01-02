"""
User Audit Event Model (UP-M5)

Immutable, append-only audit log for user profile changes.
Captures who did what, when, and what changed.

Design:
- Append-only (no updates/deletes allowed in normal code)
- Privacy-safe (no PII in snapshots)
- Queryable for compliance
- Generic references (object_type + object_id)
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class UserAuditEvent(models.Model):
    """
    Immutable audit log for user profile changes.
    
    Records:
    - Who: actor_user (nullable for system actions)
    - What: event_type, object_type, object_id
    - When: created_at
    - Where: ip_address, user_agent
    - Changes: before_snapshot, after_snapshot
    
    CRITICAL: This model is APPEND-ONLY. Never update or delete records.
    """
    
    # Event types (add more as needed)
    class EventType(models.TextChoices):
        # Public ID (UP-M1)
        PUBLIC_ID_ASSIGNED = 'public_id_assigned', 'Public ID Assigned'
        PUBLIC_ID_BACKFILLED = 'public_id_backfilled', 'Public ID Backfilled'
        
        # Economy Sync (UP-M3)
        ECONOMY_SYNC = 'economy_sync', 'Economy Sync'
        ECONOMY_DRIFT_CORRECTED = 'economy_drift_corrected', 'Economy Drift Corrected'
        
        # Stats Recompute (UP-M2/M4)
        STATS_RECOMPUTED = 'stats_recomputed', 'Stats Recomputed'
        STATS_BACKFILLED = 'stats_backfilled', 'Stats Backfilled'
        
        # Profile Changes
        PROFILE_CREATED = 'profile_created', 'Profile Created'
        PROFILE_UPDATED = 'profile_updated', 'Profile Updated'
        
        # Privacy
        PRIVACY_SETTINGS_CHANGED = 'privacy_settings_changed', 'Privacy Settings Changed'
        
        # Game Profiles (UP-CLEANUP-04 Phase C Part 2)
        GAME_PROFILE_CREATED = 'game_profile_created', 'Game Profile Created'
        GAME_PROFILE_UPDATED = 'game_profile_updated', 'Game Profile Updated'
        GAME_PROFILE_DELETED = 'game_profile_deleted', 'Game Profile Deleted'
        
        # Social/Follow (UP-CLEANUP-04 Phase C Part 2)
        FOLLOW_CREATED = 'follow_created', 'Follow Created'
        FOLLOW_DELETED = 'follow_deleted', 'Follow Deleted'
        
        # Phase 6A: Follow Requests for Private Accounts
        FOLLOW_REQUESTED = 'follow_requested', 'Follow Request Created'
        FOLLOW_REQUEST_APPROVED = 'follow_request_approved', 'Follow Request Approved'
        FOLLOW_REQUEST_REJECTED = 'follow_request_rejected', 'Follow Request Rejected'
        
        # Admin Actions
        ADMIN_OVERRIDE = 'admin_override', 'Admin Override'
        SYSTEM_RECONCILE = 'system_reconcile', 'System Reconcile'
    
    # Who performed the action (nullable for system actions)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions_performed',
        help_text="User who performed the action (null for system)"
    )
    
    # Who was affected
    subject_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='audit_events',
        db_index=True,
        help_text="User whose data was affected"
    )
    
    # What happened
    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
        db_index=True,
        help_text="Type of event"
    )
    
    source_app = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Source app (user_profile, economy, tournaments, etc.)"
    )
    
    # Generic object reference
    object_type = models.CharField(
        max_length=100,
        help_text="Type of object changed (UserProfile, UserProfileStats, DeltaCrownWallet, etc.)"
    )
    
    object_id = models.BigIntegerField(
        help_text="ID of object changed"
    )
    
    # Request tracking
    request_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Request ID for correlation"
    )
    
    idempotency_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Idempotency key for deduplication"
    )
    
    # Request metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of requester"
    )
    
    user_agent = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="User agent string"
    )
    
    # Change tracking (JSON, privacy-safe)
    before_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="State before change (privacy-safe fields only)"
    )
    
    after_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="State after change (privacy-safe fields only)"
    )
    
    # Additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context (reason, source command, etc.)"
    )
    
    # When
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When event occurred"
    )
    
    class Meta:
        db_table = 'user_profile_audit_event'
        verbose_name = 'User Audit Event'
        verbose_name_plural = 'User Audit Events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subject_user', '-created_at'], name='idx_audit_subject'),
            models.Index(fields=['actor_user', '-created_at'], name='idx_audit_actor'),
            models.Index(fields=['event_type', '-created_at'], name='idx_audit_event_type'),
            models.Index(fields=['source_app', '-created_at'], name='idx_audit_source'),
            models.Index(fields=['object_type', 'object_id'], name='idx_audit_object'),
        ]
    
    def __str__(self):
        actor = self.actor_user.username if self.actor_user else 'SYSTEM'
        return f"{self.event_type} by {actor} on {self.subject_user.username} at {self.created_at}"
    
    def save(self, *args, **kwargs):
        """Override save to prevent updates after creation."""
        if self.pk is not None:
            raise ValidationError("UserAuditEvent is immutable. Cannot update after creation.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Override delete to prevent deletion."""
        raise ValidationError("UserAuditEvent is immutable. Cannot delete.")
