"""
Team membership event ledger for audit trail and player history.

TeamMembershipEvent provides an append-only record of all membership
changes (joins, role changes, removals, status changes) for fair play
enforcement, player profiles, and organizational audits.
"""

from django.db import models
from django.contrib.auth import get_user_model

from ..choices import MembershipRole, MembershipStatus, MembershipEventType

User = get_user_model()


class TeamMembershipEvent(models.Model):
    """
    Append-only ledger of team membership events.
    
    Every membership change (join, role change, leave, removal, status change)
    creates an immutable event record. Events are NEVER edited or deleted.
    
    Use Cases:
    - Player career history (Profile user journey)
    - Fair play enforcement (suspension tracking)
    - Organizational audits (roster change history)
    - Transfer dispute resolution
    
    Denormalized Fields:
    - team, user: Enable fast queries without joining through membership
    - Membership can be deleted, but events remain for historical record
    
    Database Table: organizations_membership_event
    """
    
    # Core relationships
    membership = models.ForeignKey(
        'organizations.TeamMembership',
        on_delete=models.SET_NULL,
        related_name='events',
        null=True,
        blank=True,
        help_text="Membership this event relates to (null if membership deleted)"
    )
    
    # Denormalized for fast queries
    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='membership_events',
        db_index=True,
        help_text="Team (denormalized for queries)"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='team_membership_events',
        db_index=True,
        help_text="User (denormalized for player history queries)"
    )
    
    # Actor (who performed the action)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='membership_actions_performed',
        null=True,
        blank=True,
        help_text="Who performed this action (creator/manager/admin/system)"
    )
    
    # Event classification
    event_type = models.CharField(
        max_length=20,
        choices=MembershipEventType.choices,
        db_index=True,
        help_text="Type of event (JOINED, ROLE_CHANGED, LEFT, REMOVED, STATUS_CHANGED, NOTE)"
    )
    
    # State transitions (nullable for events that don't involve role/status changes)
    old_role = models.CharField(
        max_length=20,
        choices=MembershipRole.choices,
        null=True,
        blank=True,
        help_text="Role before change (for ROLE_CHANGED events)"
    )
    new_role = models.CharField(
        max_length=20,
        choices=MembershipRole.choices,
        null=True,
        blank=True,
        help_text="Role after change (for JOINED, ROLE_CHANGED events)"
    )
    old_status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        null=True,
        blank=True,
        help_text="Status before change (for STATUS_CHANGED events)"
    )
    new_status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        null=True,
        blank=True,
        help_text="Status after change (for STATUS_CHANGED events)"
    )
    
    # Metadata for context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context: reason codes, admin notes, match refs, duration_days"
    )
    
    # Timestamp (append-only, immutable)
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Event timestamp (immutable)"
    )
    
    class Meta:
        db_table = 'organizations_membership_event'
        ordering = ['-created_at']
        
        indexes = [
            # Player history queries
            models.Index(fields=['user', '-created_at'], name='membership_event_user_time'),
            # Team roster history
            models.Index(fields=['team', '-created_at'], name='membership_event_team_time'),
            # Membership timeline
            models.Index(fields=['membership', '-created_at'], name='membership_event_mbr_time'),
            # Event type analytics
            models.Index(fields=['event_type', '-created_at'], name='membership_event_type_time'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.event_type} - {self.team.slug} at {self.created_at}"
    
    def save(self, *args, **kwargs):
        """
        Enforce append-only behavior.
        Events can only be created, never updated.
        """
        if self.pk is not None:
            raise ValueError("TeamMembershipEvent is append-only. Cannot update existing events.")
        super().save(*args, **kwargs)
