"""
Dispute & Opponent Verification Models - Phase 6, Epic 6.2

Models for handling result disputes, opponent verification, and evidence management.

Reference:
- PHASE6_WORKPLAN_DRAFT.md - Epic 6.2 (Opponent Verification & Dispute System)
- Phase 6 state machines for dispute lifecycle

Created: December 12, 2025
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DisputeRecord(models.Model):
    """
    Tracks disputes raised against match result submissions.
    
    Workflow:
    1. Opponent disputes a MatchResultSubmission → DisputeRecord created (status='open')
    2. Organizer reviews → status='under_review'
    3. Resolution:
       - Submitter wins → status='resolved_for_submitter'
       - Opponent wins → status='resolved_for_opponent'
       - Cancelled → status='cancelled'
       - Escalated → status='escalated' (e.g., to higher-tier support)
    
    State Machine:
    - open → under_review → resolved_* / cancelled / escalated
    - Only one open dispute per submission at a time
    
    Relationships:
    - submission: The MatchResultSubmission being disputed
    - opened_by_user: User who opened the dispute (typically opponent)
    - opened_by_team: Team representing the disputer (if team tournament)
    - resolved_by_user: User who made the final resolution decision
    
    Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.2, Dispute State Machine
    """
    
    # Status choices
    OPEN = 'open'
    UNDER_REVIEW = 'under_review'
    RESOLVED_FOR_SUBMITTER = 'resolved_for_submitter'
    RESOLVED_FOR_OPPONENT = 'resolved_for_opponent'
    CANCELLED = 'cancelled'
    ESCALATED = 'escalated'
    
    STATUS_CHOICES = [
        (OPEN, 'Open'),
        (UNDER_REVIEW, 'Under Review'),
        (RESOLVED_FOR_SUBMITTER, 'Resolved - Submitter Wins'),
        (RESOLVED_FOR_OPPONENT, 'Resolved - Opponent Wins'),
        (CANCELLED, 'Cancelled'),
        (ESCALATED, 'Escalated'),
    ]
    
    # Reason code choices (extensible via config in future)
    REASON_SCORE_MISMATCH = 'score_mismatch'
    REASON_WRONG_WINNER = 'wrong_winner'
    REASON_CHEATING_SUSPICION = 'cheating_suspicion'
    REASON_INCORRECT_MAP = 'incorrect_map'
    REASON_MATCH_NOT_PLAYED = 'match_not_played'
    REASON_OTHER = 'other'
    
    REASON_CHOICES = [
        (REASON_SCORE_MISMATCH, 'Score Mismatch'),
        (REASON_WRONG_WINNER, 'Wrong Winner Declared'),
        (REASON_CHEATING_SUSPICION, 'Cheating Suspicion'),
        (REASON_INCORRECT_MAP, 'Incorrect Map/Details'),
        (REASON_MATCH_NOT_PLAYED, 'Match Not Played'),
        (REASON_OTHER, 'Other'),
    ]
    
    # Relationships
    submission = models.ForeignKey(
        'tournaments.MatchResultSubmission',
        on_delete=models.CASCADE,
        related_name='disputes',
        help_text='The result submission being disputed'
    )
    
    opened_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='opened_disputes',
        help_text='User who opened the dispute'
    )
    
    opened_by_team = models.ForeignKey(
        'teams.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disputes',
        help_text='Team representing the disputer (if team tournament)'
    )
    
    resolved_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_disputes',
        help_text='User who made the final resolution decision'
    )
    
    # Status & categorization
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=OPEN,
        db_index=True,
        help_text='Current dispute status'
    )
    
    reason_code = models.CharField(
        max_length=32,
        choices=REASON_CHOICES,
        default=REASON_OTHER,
        help_text='Categorized reason for dispute'
    )
    
    # Description & resolution
    description = models.TextField(
        help_text='Detailed description of the dispute from opponent'
    )
    
    resolution_notes = models.TextField(
        blank=True,
        default='',
        help_text='Internal notes explaining the resolution decision'
    )
    
    # Timestamps
    opened_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When the dispute was opened'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Last update timestamp'
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='When the dispute was resolved'
    )
    
    escalated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the dispute was escalated'
    )
    
    class Meta:
        db_table = 'tournaments_dispute_record'
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['submission', 'status'], name='idx_dispute_submission_status'),
            models.Index(fields=['opened_at'], name='idx_dispute_opened_at'),
            models.Index(fields=['resolved_at'], name='idx_dispute_resolved_at'),
            models.Index(fields=['status'], name='idx_dispute_status'),
        ]
    
    def __str__(self):
        return f"Dispute #{self.id} - {self.get_status_display()} (Submission #{self.submission_id})"
    
    def is_open(self):
        """Check if dispute is still open (not resolved/cancelled)."""
        return self.status in (self.OPEN, self.UNDER_REVIEW, self.ESCALATED)
    
    def is_resolved(self):
        """Check if dispute has been resolved."""
        return self.status in (
            self.RESOLVED_FOR_SUBMITTER,
            self.RESOLVED_FOR_OPPONENT,
            self.CANCELLED
        )


class DisputeEvidence(models.Model):
    """
    Evidence attached to a dispute (screenshots, videos, chat logs, etc.).
    
    Supports linking to external resources (S3, imgur, Discord, etc.).
    Full file upload integration deferred to Epic 6.5.
    
    Relationships:
    - dispute: The DisputeRecord this evidence belongs to
    - uploaded_by: User who uploaded the evidence
    
    Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.2, Evidence Management
    """
    
    # Evidence type choices
    TYPE_SCREENSHOT = 'screenshot'
    TYPE_VIDEO = 'video'
    TYPE_CHAT_LOG = 'chat_log'
    TYPE_OTHER = 'other'
    
    TYPE_CHOICES = [
        (TYPE_SCREENSHOT, 'Screenshot'),
        (TYPE_VIDEO, 'Video Recording'),
        (TYPE_CHAT_LOG, 'Chat Log'),
        (TYPE_OTHER, 'Other'),
    ]
    
    # Relationships
    dispute = models.ForeignKey(
        DisputeRecord,
        on_delete=models.CASCADE,
        related_name='evidence',
        help_text='The dispute this evidence belongs to'
    )
    
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_dispute_evidence',
        help_text='User who uploaded the evidence'
    )
    
    # Evidence details
    evidence_type = models.CharField(
        max_length=32,
        choices=TYPE_CHOICES,
        default=TYPE_SCREENSHOT,
        help_text='Type of evidence'
    )
    
    url = models.URLField(
        max_length=500,
        help_text='URL to external resource (imgur, Discord CDN, S3, etc.)'
    )
    
    notes = models.TextField(
        blank=True,
        default='',
        help_text='Additional context or notes about this evidence'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the evidence was uploaded'
    )
    
    class Meta:
        db_table = 'tournaments_dispute_evidence'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['dispute'], name='idx_evidence_dispute'),
            models.Index(fields=['created_at'], name='idx_evidence_created_at'),
        ]
    
    def __str__(self):
        return f"{self.get_evidence_type_display()} for Dispute #{self.dispute_id}"
