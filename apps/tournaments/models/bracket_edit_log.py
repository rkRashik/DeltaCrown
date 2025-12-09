"""
Bracket Edit Log Model (Epic 3.3)

Audit trail for bracket editor operations:
- Swap participants
- Move participants
- Remove participants
- Repair bracket

Records all manual bracket edits for compliance and debugging.
"""

from django.db import models
from django.utils import timezone


class BracketEditLog(models.Model):
    """
    Audit log for bracket editing operations.
    
    Records all manual changes made to tournament brackets via
    BracketEditorService for compliance, debugging, and rollback.
    
    Attributes:
        stage_id: TournamentStage ID (nullable for cross-stage repairs)
        operation: Type of edit (swap, move, remove, repair, validate)
        match_ids: JSON array of affected match IDs
        participant_ids: JSON array of affected participant IDs
        old_data: JSON snapshot of state before edit
        new_data: JSON snapshot of state after edit
        user_id: User who performed the edit (nullable for system edits)
        timestamp: When edit was performed
    
    Usage:
        # Log a swap operation
        BracketEditLog.objects.create(
            stage_id=42,
            operation="swap",
            match_ids=[101, 102],
            old_data={"match1_participants": [10, 20], "match2_participants": [30, 40]},
            new_data={"match1_participants": [30, 40], "match2_participants": [10, 20]},
            user_id=user.id,
            timestamp=timezone.now(),
        )
    """
    
    OPERATION_SWAP = "swap"
    OPERATION_MOVE = "move"
    OPERATION_REMOVE = "remove"
    OPERATION_REPAIR = "repair"
    OPERATION_VALIDATE = "validate"
    
    OPERATION_CHOICES = [
        (OPERATION_SWAP, "Swap Participants"),
        (OPERATION_MOVE, "Move Participant"),
        (OPERATION_REMOVE, "Remove Participant"),
        (OPERATION_REPAIR, "Repair Bracket"),
        (OPERATION_VALIDATE, "Validate Bracket"),
    ]
    
    stage_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="TournamentStage ID (nullable for cross-stage operations)",
    )
    
    operation = models.CharField(
        max_length=20,
        choices=OPERATION_CHOICES,
        help_text="Type of bracket edit operation",
    )
    
    match_ids = models.JSONField(
        default=list,
        help_text="List of affected match IDs",
    )
    
    participant_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of affected participant IDs (optional)",
    )
    
    old_data = models.JSONField(
        default=dict,
        help_text="State before edit (JSON)",
    )
    
    new_data = models.JSONField(
        default=dict,
        help_text="State after edit (JSON)",
    )
    
    user_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="User who performed edit (nullable for system edits)",
    )
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When edit was performed",
    )
    
    class Meta:
        db_table = "tournament_bracket_edit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["stage_id", "-timestamp"]),
            models.Index(fields=["operation", "-timestamp"]),
            models.Index(fields=["user_id", "-timestamp"]),
        ]
        verbose_name = "Bracket Edit Log"
        verbose_name_plural = "Bracket Edit Logs"
    
    def __str__(self):
        return f"{self.operation} on stage {self.stage_id} at {self.timestamp}"
    
    def __repr__(self):
        return (
            f"<BracketEditLog id={self.id} operation={self.operation} "
            f"stage_id={self.stage_id} timestamp={self.timestamp}>"
        )
