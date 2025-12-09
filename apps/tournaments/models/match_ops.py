"""
Match Operations Models - Phase 7, Epic 7.4

Models for Match Operations Command Center (MOCC).

Stores operator actions, moderator notes, and match control logs
for authorized staff and referees.

Reference: Phase 7, Epic 7.4 - Match Operations Command Center
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class MatchOperationLog(models.Model):
    """
    Audit log for all manual match operations performed by staff/referees.
    
    Records every state change, override, and control action taken
    on a match for compliance and debugging.
    
    Reference: Phase 7, Epic 7.4 - MOCC Audit Trail
    """
    
    # Operation type constants
    OPERATION_LIVE = 'LIVE'
    OPERATION_PAUSED = 'PAUSED'
    OPERATION_RESUMED = 'RESUMED'
    OPERATION_FORCE_COMPLETED = 'FORCE_COMPLETED'
    OPERATION_NOTE_ADDED = 'NOTE_ADDED'
    OPERATION_OVERRIDE_RESULT = 'OVERRIDE_RESULT'
    OPERATION_OVERRIDE_REFEREE = 'OVERRIDE_REFEREE'
    
    OPERATION_TYPES = [
        (OPERATION_LIVE, 'Match Marked Live'),
        (OPERATION_PAUSED, 'Match Paused'),
        (OPERATION_RESUMED, 'Match Resumed'),
        (OPERATION_FORCE_COMPLETED, 'Match Force Completed'),
        (OPERATION_NOTE_ADDED, 'Moderator Note Added'),
        (OPERATION_OVERRIDE_RESULT, 'Result Overridden'),
        (OPERATION_OVERRIDE_REFEREE, 'Referee Assignment Overridden'),
    ]
    
    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='operation_logs',
        help_text="Match this operation was performed on"
    )
    
    operator_user_id = models.IntegerField(
        help_text="User ID of staff/referee who performed the operation"
    )
    
    operation_type = models.CharField(
        max_length=50,
        choices=OPERATION_TYPES,
        help_text="Type of operation performed"
    )
    
    payload = models.JSONField(
        null=True,
        blank=True,
        help_text="Additional metadata about the operation (previous state, overrides, etc.)"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the operation was performed"
    )
    
    class Meta:
        db_table = 'match_operation_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['match', 'created_at']),
            models.Index(fields=['operation_type', 'created_at']),
            models.Index(fields=['operator_user_id', 'created_at']),
        ]
    
    def __str__(self):
        return f"[{self.operation_type}] Match {self.match_id} by User {self.operator_user_id} at {self.created_at}"


class MatchModeratorNote(models.Model):
    """
    Notes added by staff/referees to a match.
    
    Used for communication between staff, documenting issues,
    and providing context for operator decisions.
    
    Reference: Phase 7, Epic 7.4 - MOCC Communication
    """
    
    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='moderator_notes',
        help_text="Match this note applies to"
    )
    
    author_user_id = models.IntegerField(
        help_text="User ID of staff/referee who wrote the note"
    )
    
    content = models.TextField(
        help_text="Note content"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the note was created"
    )
    
    class Meta:
        db_table = 'match_moderator_notes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['match', 'created_at']),
            models.Index(fields=['author_user_id', 'created_at']),
        ]
    
    def __str__(self):
        return f"Note on Match {self.match_id} by User {self.author_user_id} at {self.created_at}"
