"""
Moderation Models

Implements account sanctions, audit trails, and abuse reporting for Phase 8.

Models:
- ModerationSanction: Account sanctions (ban, suspend, mute)
- ModerationAudit: Append-only audit trail
- AbuseReport: User-submitted abuse reports with state machine
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class ModerationSanction(models.Model):
    """
    Account sanctions: ban, suspend, or mute a user profile.
    
    Scope:
    - global: Applies to entire platform
    - tournament: Applies to specific tournament (scope_id required)
    
    Lifecycle:
    - Active: starts_at <= now < ends_at, revoked_at IS NULL
    - Expired: ends_at IS NOT NULL AND ends_at < now
    - Revoked: revoked_at IS NOT NULL
    """
    TYPE_BAN = 'ban'
    TYPE_SUSPEND = 'suspend'
    TYPE_MUTE = 'mute'
    TYPE_CHOICES = [
        (TYPE_BAN, 'Ban'),
        (TYPE_SUSPEND, 'Suspend'),
        (TYPE_MUTE, 'Mute'),
    ]
    
    SCOPE_GLOBAL = 'global'
    SCOPE_TOURNAMENT = 'tournament'
    SCOPE_CHOICES = [
        (SCOPE_GLOBAL, 'Global'),
        (SCOPE_TOURNAMENT, 'Tournament'),
    ]
    
    # User being sanctioned (FK to user_profile.UserProfile)
    subject_profile_id = models.IntegerField(db_index=True)
    
    # Sanction details
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    scope_id = models.IntegerField(null=True, blank=True)  # Tournament ID for scope=tournament
    reason_code = models.CharField(max_length=100)  # e.g., "abuse", "cheating"
    notes = models.JSONField(default=dict, blank=True)  # JSONB for flexible metadata
    
    # Issued by (FK to user_profile.UserProfile, nullable for system actions)
    issued_by = models.IntegerField(null=True, blank=True)
    
    # Time windows
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)  # NULL = permanent
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    # Idempotency
    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'moderation_sanction'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['subject_profile_id', 'type', 'scope', 'scope_id', 'ends_at', 'revoked_at'],
                name='mod_sanction_query_idx'
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=models.F('starts_at')),
                name='sanction_ends_after_starts'
            ),
        ]
    
    def clean(self):
        """Validate model fields."""
        if self.scope == self.SCOPE_TOURNAMENT and not self.scope_id:
            raise ValidationError("scope_id required when scope=tournament")
        if self.ends_at and self.starts_at and self.ends_at <= self.starts_at:
            raise ValidationError("ends_at must be after starts_at")
    
    def is_active(self, at=None):
        """Check if sanction is active at given time (default: now)."""
        at = at or timezone.now()
        
        # Revoked sanctions are never active
        if self.revoked_at:
            return False
        
        # Check time window
        if self.starts_at > at:
            return False
        if self.ends_at and self.ends_at <= at:
            return False
        
        return True
    
    def __str__(self):
        return f"{self.type}:{self.scope} for profile#{self.subject_profile_id}"


class ModerationAudit(models.Model):
    """
    Append-only audit trail for moderation actions.
    
    Records all sanction and report state changes with actor, subject, and metadata.
    No updates or deletes - append-only for compliance.
    """
    # Event type (e.g., "sanction_created", "report_triaged")
    event = models.CharField(max_length=100, db_index=True)
    
    # Actor performing the action (nullable for system actions)
    actor_id = models.IntegerField(null=True, blank=True, db_index=True)
    
    # Subject of the action (nullable if not user-specific)
    subject_profile_id = models.IntegerField(null=True, blank=True)
    
    # Reference to entity (e.g., ref_type="sanction", ref_id=123)
    ref_type = models.CharField(max_length=50)
    ref_id = models.IntegerField()
    
    # JSONB metadata (PII-free)
    meta = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'moderation_audit'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ref_type', 'ref_id', 'created_at'], name='mod_audit_ref_idx'),
            models.Index(fields=['actor_id', 'created_at'], name='mod_audit_actor_idx'),
        ]
    
    def __str__(self):
        actor_str = f"actor#{self.actor_id}" if self.actor_id else "system"
        return f"{self.event} by {actor_str} on {self.ref_type}#{self.ref_id}"


class AbuseReport(models.Model):
    """
    User-submitted abuse reports with state machine.
    
    States:
    - open: Initial state when filed
    - triaged: Under review by moderator
    - resolved: Action taken, report closed
    - rejected: No action needed, report closed
    
    Transitions: open → triaged → {resolved, rejected}
    No reverse transitions allowed.
    """
    STATE_OPEN = 'open'
    STATE_TRIAGED = 'triaged'
    STATE_RESOLVED = 'resolved'
    STATE_REJECTED = 'rejected'
    STATE_CHOICES = [
        (STATE_OPEN, 'Open'),
        (STATE_TRIAGED, 'Triaged'),
        (STATE_RESOLVED, 'Resolved'),
        (STATE_REJECTED, 'Rejected'),
    ]
    
    VALID_TRANSITIONS = {
        STATE_OPEN: [STATE_TRIAGED],
        STATE_TRIAGED: [STATE_RESOLVED, STATE_REJECTED],
        STATE_RESOLVED: [],  # Terminal state
        STATE_REJECTED: [],  # Terminal state
    }
    
    # Reporter (FK to user_profile.UserProfile)
    reporter_profile_id = models.IntegerField(db_index=True)
    
    # Subject being reported (nullable if content-based report)
    subject_profile_id = models.IntegerField(null=True, blank=True, db_index=True)
    
    # Report details
    category = models.CharField(max_length=50)  # e.g., "harassment", "cheating"
    ref_type = models.CharField(max_length=50)  # e.g., "chat_message", "profile"
    ref_id = models.IntegerField()
    
    # State machine
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default=STATE_OPEN, db_index=True)
    
    # Idempotency
    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    # Priority (0=lowest, 5=highest)
    priority = models.IntegerField(default=3)
    
    # JSONB metadata (PII-free)
    meta = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'abuse_report'
        ordering = ['-priority', '-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(priority__gte=0, priority__lte=5),
                name='report_priority_bounds'
            ),
        ]
    
    def clean(self):
        """Validate priority bounds."""
        if not (0 <= self.priority <= 5):
            raise ValidationError("priority must be between 0 and 5")
    
    def can_transition_to(self, new_state):
        """Check if transition is valid."""
        return new_state in self.VALID_TRANSITIONS.get(self.state, [])
    
    def __str__(self):
        return f"Report#{self.id} ({self.state}): {self.category} on {self.ref_type}#{self.ref_id}"
