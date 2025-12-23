# apps/user_profile/models/activity.py
"""
User Activity Event Log (UP-M2)

Immutable event log of all user actions for audit trail and stats derivation.
Event-sourced architecture: all stats computed from this ledger.

Created: December 23, 2025
Status: UP-M2 Implementation
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class EventType(models.TextChoices):
    """Event type choices for UserActivity"""
    
    # Tournament Events (7)
    TOURNAMENT_REGISTERED = 'tournament_registered', _('Registered for Tournament')
    TOURNAMENT_JOINED = 'tournament_joined', _('Tournament Started')
    TOURNAMENT_COMPLETED = 'tournament_completed', _('Tournament Finished')
    TOURNAMENT_WON = 'tournament_won', _('Won Tournament (1st)')
    TOURNAMENT_RUNNER_UP = 'tournament_runner_up', _('Runner-Up (2nd)')
    TOURNAMENT_TOP4 = 'tournament_top4', _('Top 4 Placement')
    TOURNAMENT_PLACED = 'tournament_placed', _('Placed in Tournament')
    
    # Match Events (3)
    MATCH_PLAYED = 'match_played', _('Played Match')
    MATCH_WON = 'match_won', _('Won Match')
    MATCH_LOST = 'match_lost', _('Lost Match')
    
    # Economy Events (2)
    COINS_EARNED = 'coins_earned', _('Earned DeltaCoins')
    COINS_SPENT = 'coins_spent', _('Spent DeltaCoins')
    
    # Achievement Events (1)
    ACHIEVEMENT_UNLOCKED = 'achievement_unlocked', _('Unlocked Achievement')
    
    # Team Events (3) - Future: UP-M4
    TEAM_CREATED = 'team_created', _('Created Team')
    TEAM_JOINED = 'team_joined', _('Joined Team')
    TEAM_LEFT = 'team_left', _('Left Team')


class UserActivity(models.Model):
    """
    Immutable event log of all user actions.
    
    Design Principles:
    - Append-only: No updates or deletes allowed
    - Event-sourced: All stats derived from this ledger
    - Auditable: Complete history for compliance (GDPR, disputes)
    - Traceable: source_model + source_id link to origin
    
    Scalability: ~500K events/month, 6M/year, handles 30M+ rows
    """
    
    # WHO: User performing action
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,  # PROTECT: never cascade delete events
        related_name='activities',
        db_index=True,
        help_text="User who performed the action"
    )
    
    # WHAT: Event type
    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
        db_index=True,
        help_text="Type of event (tournament_won, match_played, etc.)"
    )
    
    # WHEN: Timestamp (auto-set on creation)
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the event occurred (immutable)"
    )
    
    # WHY/CONTEXT: Event-specific metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Event-specific data (tournament_id, match_id, amount, etc.)"
    )
    
    # SOURCE: Traceability to origin model
    source_model = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Model name that triggered event (Registration, Match, etc.)"
    )
    
    source_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Primary key of source model instance"
    )
    
    # IMMUTABILITY: No updated_at field
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Event creation timestamp"
    )
    
    class Meta:
        db_table = 'user_profile_useractivity'
        verbose_name = "User Activity"
        verbose_name_plural = "User Activities"
        ordering = ['-timestamp']
        
        indexes = [
            # Most common: activity feed for user
            models.Index(fields=['user', '-timestamp'], name='idx_activity_user_time'),
            
            # Filter by event type
            models.Index(fields=['event_type', '-timestamp'], name='idx_activity_type_time'),
            
            # User + event type combo (analytics)
            models.Index(fields=['user', 'event_type'], name='idx_activity_user_type'),
            
            # Source lookup (audit trail)
            models.Index(fields=['source_model', 'source_id'], name='idx_activity_source'),
            
            # Time range queries
            models.Index(fields=['timestamp'], name='idx_activity_timestamp'),
        ]
        
        permissions = [
            ('view_activity_feed', 'Can view user activity feed'),
            ('export_activity_data', 'Can export activity data (GDPR)'),
        ]
        
        constraints = [
            # Idempotency: prevent duplicate events from same source
            models.UniqueConstraint(
                fields=['source_model', 'source_id', 'event_type'],
                name='unique_source_event',
                condition=models.Q(source_model__isnull=False, source_id__isnull=False),
                violation_error_message="Event already exists for this source"
            ),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_event_type_display()} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        """
        Override save to enforce immutability.
        Only allow creation (pk is None), no updates.
        """
        if self.pk is not None:
            raise ValidationError("UserActivity events are immutable. Cannot update existing event.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Override delete to prevent deletion"""
        raise ValidationError("UserActivity events are immutable. Cannot delete events.")
