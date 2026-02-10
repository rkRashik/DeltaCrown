"""
Activity logging model for audit trails.

TeamActivityLog records all significant team events for compliance,
debugging, and user activity feeds.
"""

from django.db import models
from django.contrib.auth import get_user_model

from ..choices import ActivityActionType

User = get_user_model()


class TeamActivityLog(models.Model):
    """
    Audit trail for all team-related actions.
    
    Purpose:
    - Compliance and audit requirements
    - Debugging migration issues
    - User-facing activity feeds
    - Security incident investigation
    
    Logged Actions:
    - Team creation/updates/deletion
    - Roster changes (add/remove/role change)
    - Tournament registrations
    - Ranking changes
    - Migration events
    - Organization acquisitions
    
    Retention Policy:
    - Keep indefinitely for compliance
    - Indexed for fast querying
    - Never delete (soft-delete teams instead)
    
    Database Table: organizations_activity_log
    """
    
    # Relationship
    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='activity_logs',
        db_index=True,
        help_text="Team this activity belongs to"
    )
    
    # Action classification
    action_type = models.CharField(
        max_length=50,
        choices=ActivityActionType.choices,
        db_index=True,
        help_text="Type of action performed"
    )
    
    # Actor information
    actor_id = models.IntegerField(
        help_text="User ID who performed action"
    )
    actor_username = models.CharField(
        max_length=150,
        help_text="Cached username (preserved if user deleted)"
    )
    
    # Description
    description = models.TextField(
        help_text="Human-readable description of action"
    )
    
    # Additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Additional context (e.g., {'old_role': 'PLAYER', 'new_role': 'MANAGER'})"
        )
    )
    
    # Timestamp
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When action occurred"
    )
    
    # Journey filtering fields (Point 2)
    is_pinned = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Pinned events always show in public journey timeline",
    )
    is_milestone = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Milestone events show in public timeline (auto-set for major actions)",
    )
    
    class Meta:
        db_table = 'organizations_activity_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['team', '-timestamp'], name='activity_team_time_idx'),
            models.Index(fields=['action_type'], name='activity_type_idx'),
            models.Index(fields=['-timestamp'], name='activity_time_idx'),
            models.Index(fields=['actor_id', '-timestamp'], name='activity_actor_time_idx'),
        ]
        verbose_name = 'Team Activity Log'
        verbose_name_plural = 'Team Activity Logs'
    
    def __str__(self):
        """Return human-readable activity log entry."""
        return f"{self.action_type} on {self.team.name} by {self.actor_username}"
    
    @classmethod
    def log_action(cls, team, action_type, actor, description, metadata=None):
        """
        Create activity log entry.
        
        Helper method for consistent logging across the codebase.
        
        Args:
            team: Team instance
            action_type: ActivityActionType choice
            actor: User instance who performed action
            description: Human-readable description
            metadata: Optional dict with additional context
            
        Returns:
            TeamActivityLog: Created log entry
        """
        return cls.objects.create(
            team=team,
            action_type=action_type,
            actor_id=actor.id,
            actor_username=actor.username,
            description=description,
            metadata=metadata or {}
        )
    
    @classmethod
    def get_team_feed(cls, team, limit=20):
        """
        Get recent activity feed for a team.
        
        Used for team dashboard activity timeline.
        
        Args:
            team: Team instance
            limit: Maximum number of entries to return
            
        Returns:
            QuerySet[TeamActivityLog]: Recent activity entries
        """
        return cls.objects.filter(team=team).select_related('team')[:limit]
    
    @classmethod
    def get_user_feed(cls, user, limit=20):
        """
        Get recent activity feed for a user's actions.
        
        Used for user profile activity timeline.
        
        Args:
            user: User instance
            limit: Maximum number of entries to return
            
        Returns:
            QuerySet[TeamActivityLog]: Recent activity entries by user
        """
        return cls.objects.filter(actor_id=user.id).select_related('team')[:limit]
