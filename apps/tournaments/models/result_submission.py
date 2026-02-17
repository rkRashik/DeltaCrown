"""
Match Result Submission Models - Phase 6, Epic 6.1

Player/team-submitted match results with proof screenshots,
opponent verification, and auto-confirmation after 24 hours.

Architecture:
- Part of tournaments domain (ORM layer)
- Accessed via ResultSubmissionAdapter in tournament_ops
- No business logic here (pure Django models)
"""

from django.db import models
from django.utils import timezone
from datetime import timedelta


class MatchResultSubmission(models.Model):
    """
    Player/team-submitted match result.
    
    Lifecycle:
    - Player submits result + proof screenshot
    - Opponent confirms/disputes within 24 hours
    - Auto-confirm if no response
    - Organizer resolves disputes
    
    Status flow:
    PENDING → CONFIRMED → FINALIZED
            ↓
            DISPUTED → UNDER_REVIEW → RESOLVED → FINALIZED
            ↓
            AUTO_CONFIRMED (24 hours) → FINALIZED
    """
    
    # Status choices
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_DISPUTED = 'disputed'
    STATUS_AUTO_CONFIRMED = 'auto_confirmed'
    STATUS_FINALIZED = 'finalized'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Opponent Confirmation'),
        (STATUS_CONFIRMED, 'Confirmed by Opponent'),
        (STATUS_DISPUTED, 'Disputed by Opponent'),
        (STATUS_AUTO_CONFIRMED, 'Auto-Confirmed (24h timeout)'),
        (STATUS_FINALIZED, 'Finalized by Organizer'),
        (STATUS_REJECTED, 'Rejected by Organizer'),
    ]
    
    # Core foreign keys
    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='result_submissions',
        help_text='Match this result is for'
    )
    submitted_by_user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='submitted_results',
        help_text='User who submitted the result'
    )
    submitted_by_team_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        db_column='submitted_by_team_id',
        help_text='Team ID the submitter represents (if team tournament)'
    )
    
    # Result payload (game-specific JSON)
    raw_result_payload = models.JSONField(
        help_text='Raw result data from frontend (game-specific structure)'
    )
    
    # Proof
    proof_screenshot_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='URL to proof screenshot (Discord, Imgur, S3, etc.)'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        help_text='Current submission status'
    )
    
    # Timestamps
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When result was submitted'
    )
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When opponent confirmed result'
    )
    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When organizer finalized result'
    )
    auto_confirm_deadline = models.DateTimeField(
        help_text='Deadline for opponent to respond (submitted_at + 24h)'
    )
    
    # Confirmation tracking
    confirmed_by_user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_submissions',
        help_text='User who confirmed/disputed the result'
    )
    
    # Notes
    submitter_notes = models.TextField(
        blank=True,
        default='',
        help_text='Notes from submitter about the result'
    )
    organizer_notes = models.TextField(
        blank=True,
        default='',
        help_text='Notes from organizer during review'
    )
    
    class Meta:
        db_table = 'tournaments_match_result_submission'
        verbose_name = 'Match Result Submission'
        verbose_name_plural = 'Match Result Submissions'
        indexes = [
            models.Index(fields=['match', 'status'], name='idx_submission_match_status'),
            models.Index(fields=['submitted_at'], name='idx_submission_submitted_at'),
            models.Index(fields=['auto_confirm_deadline'], name='idx_submission_deadline'),
        ]
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Result for Match {self.match_id} by User {self.submitted_by_user_id} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-calculate auto_confirm_deadline if not set."""
        if not self.auto_confirm_deadline and self.submitted_at:
            self.auto_confirm_deadline = self.submitted_at + timedelta(hours=24)
        elif not self.auto_confirm_deadline:
            # For creation before submitted_at is set
            self.auto_confirm_deadline = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)


class ResultVerificationLog(models.Model):
    """
    Audit trail for result verification steps.
    
    Used in Epic 6.4 (Result Verification & Finalization).
    Phase 6.1 creates the model but doesn't heavily use it yet.
    """
    
    # Step types
    STEP_SCHEMA_VALIDATION = 'schema_validation'
    STEP_SCORING_CALCULATION = 'scoring_calculation'
    STEP_ORGANIZER_REVIEW = 'organizer_review'
    STEP_FINALIZATION = 'finalization'
    # Epic 6.2: Opponent verification steps
    STEP_OPPONENT_CONFIRM = 'opponent_confirm'
    STEP_OPPONENT_DISPUTE = 'opponent_dispute'
    STEP_DISPUTE_ESCALATED = 'dispute_escalated'
    STEP_DISPUTE_RESOLVED = 'dispute_resolved'
    
    STEP_CHOICES = [
        (STEP_SCHEMA_VALIDATION, 'Schema Validation'),
        (STEP_SCORING_CALCULATION, 'Scoring Calculation'),
        (STEP_ORGANIZER_REVIEW, 'Organizer Review'),
        (STEP_FINALIZATION, 'Finalization'),
        # Epic 6.2: Opponent verification
        (STEP_OPPONENT_CONFIRM, 'Opponent Confirmation'),
        (STEP_OPPONENT_DISPUTE, 'Opponent Dispute'),
        (STEP_DISPUTE_ESCALATED, 'Dispute Escalated'),
        (STEP_DISPUTE_RESOLVED, 'Dispute Resolved'),
    ]
    
    # Status
    STATUS_SUCCESS = 'success'
    STATUS_FAILURE = 'failure'
    
    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILURE, 'Failure'),
    ]
    
    submission = models.ForeignKey(
        MatchResultSubmission,
        on_delete=models.CASCADE,
        related_name='verification_logs',
        help_text='Submission being verified'
    )
    step = models.CharField(
        max_length=30,
        choices=STEP_CHOICES,
        help_text='Verification step performed'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        help_text='Step result (success/failure)'
    )
    details = models.JSONField(
        default=dict,
        help_text='Step details (errors, warnings, metadata)'
    )
    performed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='User who performed this step (if applicable)'
    )
    performed_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When step was performed'
    )
    
    class Meta:
        db_table = 'tournaments_result_verification_log'
        verbose_name = 'Result Verification Log'
        verbose_name_plural = 'Result Verification Logs'
        ordering = ['-performed_at']
    
    def __str__(self):
        return f"{self.step} for Submission {self.submission_id} - {self.status}"
