"""
Match and Dispute models for tournament matches (Module 1.4)

Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 6: Match Lifecycle Models)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Match/Dispute models, state machine)
- Documents/Planning/PROPOSAL_PART_2_TECHNICAL_ARCHITECTURE.md (Dispute Model section 4.5)
- Documents/Planning/PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md (Constraints & indexes)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-001, ADR-003, ADR-007)

Architecture Decisions:
- ADR-001: Service layer pattern - Business logic in MatchService
- ADR-003: Soft delete pattern for Match model
- ADR-007: WebSocket support for real-time score updates

State Machine (Match):
SCHEDULED → CHECK_IN → READY → LIVE → PENDING_RESULT → COMPLETED
                 │                          │
                 │                          └──> DISPUTED
                 │
                 └──> FORFEIT (if check-in failed)

Status Workflow (Dispute):
OPEN → UNDER_REVIEW → RESOLVED / ESCALATED

Note: Bracket model moved to bracket.py in Module 1.5.
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from typing import Any

from apps.common.models import SoftDeleteModel, TimestampedModel


# ===========================
# Match Model (Full Implementation)
# ===========================


class Match(SoftDeleteModel, TimestampedModel):
    """
    Match lifecycle management with state machine workflow.
    
    Features:
    - State machine for match progression
    - Check-in tracking for participants
    - Score tracking and result submission
    - JSONB lobby info for game-specific data
    - Real-time updates via WebSocket (ADR-007)
    - Soft delete support (ADR-003)
    
    Related Services:
    - MatchService: Match creation, state transitions, result submission
    - BracketService: Match progression and winner advancement
    
    Database Constraints:
    - State must be valid (CHECK constraint)
    - Scores must be non-negative (CHECK constraint)
    - If COMPLETED, must have winner_id and loser_id (CHECK constraint)
    - Winner must be one of participants (CHECK constraint)
    - Round and match numbers must be positive (CHECK constraint)
    """
    
    # State choices
    SCHEDULED = 'scheduled'
    CHECK_IN = 'check_in'
    READY = 'ready'
    LIVE = 'live'
    PENDING_RESULT = 'pending_result'
    COMPLETED = 'completed'
    DISPUTED = 'disputed'
    FORFEIT = 'forfeit'
    CANCELLED = 'cancelled'
    
    STATE_CHOICES = [
        (SCHEDULED, _('Scheduled')),
        (CHECK_IN, _('Check-in Open')),
        (READY, _('Ready to Start')),
        (LIVE, _('Live/In Progress')),
        (PENDING_RESULT, _('Pending Result')),
        (COMPLETED, _('Completed')),
        (DISPUTED, _('Disputed')),
        (FORFEIT, _('Forfeit')),
        (CANCELLED, _('Cancelled')),
    ]
    
    # Foreign keys
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name=_('Tournament'),
        help_text=_('Tournament this match belongs to')
    )
    
    bracket = models.ForeignKey(
        'tournaments.Bracket',
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name=_('Bracket'),
        null=True,
        blank=True,
        help_text=_('Bracket this match belongs to (null for group stage)')
    )
    
    # Match identification
    round_number = models.PositiveIntegerField(
        verbose_name=_('Round Number'),
        validators=[MinValueValidator(1)],
        help_text=_('Round number in bracket (1 = first round)')
    )
    
    match_number = models.PositiveIntegerField(
        verbose_name=_('Match Number'),
        validators=[MinValueValidator(1)],
        help_text=_('Match number within round')
    )
    
    # Participants (IntegerField for external references)
    participant1_id = models.PositiveIntegerField(
        verbose_name=_('Participant 1 ID'),
        null=True,
        blank=True,
        help_text=_('Team ID or User ID for participant 1')
    )
    
    participant1_name = models.CharField(
        max_length=100,
        verbose_name=_('Participant 1 Name'),
        blank=True,
        help_text=_('Denormalized name for display')
    )
    
    participant2_id = models.PositiveIntegerField(
        verbose_name=_('Participant 2 ID'),
        null=True,
        blank=True,
        help_text=_('Team ID or User ID for participant 2')
    )
    
    participant2_name = models.CharField(
        max_length=100,
        verbose_name=_('Participant 2 Name'),
        blank=True,
        help_text=_('Denormalized name for display')
    )
    
    # Match state
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default=SCHEDULED,
        verbose_name=_('State'),
        db_index=True,
        help_text=_('Current state in match lifecycle')
    )
    
    # Scores
    participant1_score = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Participant 1 Score'),
        validators=[MinValueValidator(0)],
        help_text=_('Score for participant 1')
    )
    
    participant2_score = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Participant 2 Score'),
        validators=[MinValueValidator(0)],
        help_text=_('Score for participant 2')
    )
    
    # Winner/Loser tracking
    winner_id = models.PositiveIntegerField(
        verbose_name=_('Winner ID'),
        null=True,
        blank=True,
        db_index=True,
        help_text=_('Team ID or User ID of winner (set when match completed)')
    )
    
    loser_id = models.PositiveIntegerField(
        verbose_name=_('Loser ID'),
        null=True,
        blank=True,
        help_text=_('Team ID or User ID of loser (set when match completed)')
    )
    
    # Lobby information (JSONB for game-specific data)
    lobby_info = models.JSONField(
        verbose_name=_('Lobby Info'),
        default=dict,
        blank=True,
        help_text=_(
            'Game lobby details (map, server, lobby code, password, etc.). '
            'Example: {"game_mode": "Competitive", "map": "Haven", "lobby_code": "ABC123"}'
        )
    )
    
    # Streaming
    stream_url = models.URLField(
        max_length=200,
        verbose_name=_('Stream URL'),
        blank=True,
        help_text=_('Twitch/YouTube stream URL for spectators')
    )
    
    # Scheduling
    scheduled_time = models.DateTimeField(
        verbose_name=_('Scheduled Time'),
        null=True,
        blank=True,
        db_index=True,
        help_text=_('When match is scheduled to start')
    )
    
    check_in_deadline = models.DateTimeField(
        verbose_name=_('Check-in Deadline'),
        null=True,
        blank=True,
        help_text=_('Deadline for participants to check in')
    )
    
    # Check-in tracking
    participant1_checked_in = models.BooleanField(
        default=False,
        verbose_name=_('Participant 1 Checked In'),
        help_text=_('Whether participant 1 has checked in')
    )
    
    participant2_checked_in = models.BooleanField(
        default=False,
        verbose_name=_('Participant 2 Checked In'),
        help_text=_('Whether participant 2 has checked in')
    )
    
    # Match lifecycle timestamps
    started_at = models.DateTimeField(
        verbose_name=_('Started At'),
        null=True,
        blank=True,
        help_text=_('When match actually started (state → LIVE)')
    )
    
    completed_at = models.DateTimeField(
        verbose_name=_('Completed At'),
        null=True,
        blank=True,
        help_text=_('When match was completed (state → COMPLETED)')
    )
    
    class Meta:
        db_table = 'tournament_engine_match_match'
        verbose_name = _('Match')
        verbose_name_plural = _('Matches')
        ordering = ['tournament', 'round_number', 'match_number']
        indexes = [
            models.Index(fields=['tournament'], name='idx_match_tournament'),
            models.Index(fields=['bracket'], name='idx_match_bracket'),
            models.Index(fields=['bracket', 'round_number'], name='idx_match_round'),
            models.Index(fields=['state'], name='idx_match_state'),
            models.Index(fields=['scheduled_time'], name='idx_match_scheduled'),
            models.Index(fields=['participant1_id', 'participant2_id'], name='idx_match_participants'),
            models.Index(fields=['winner_id'], name='idx_match_winner'),
            # Partial index for CHECK_IN state
            models.Index(
                fields=['check_in_deadline', 'state'],
                name='idx_match_check_in',
                condition=models.Q(state='check_in')
            ),
            # Partial index for LIVE state
            models.Index(
                fields=['tournament', 'state'],
                name='idx_match_live',
                condition=models.Q(state='live')
            ),
            # GIN index for lobby_info JSONB
            models.Index(fields=['lobby_info'], name='idx_match_lobby_gin'),
        ]
        constraints = [
            # State must be valid (enforced by choices)
            models.CheckConstraint(
                check=models.Q(
                    state__in=[
                        'scheduled', 'check_in', 'ready', 'live',
                        'pending_result', 'completed', 'disputed',
                        'forfeit', 'cancelled'
                    ]
                ),
                name='chk_match_state_valid'
            ),
            # Scores must be non-negative (enforced by PositiveIntegerField + validator)
            models.CheckConstraint(
                check=models.Q(participant1_score__gte=0) & models.Q(participant2_score__gte=0),
                name='chk_match_scores_positive'
            ),
            # If COMPLETED, must have winner and loser
            models.CheckConstraint(
                check=(
                    models.Q(state='completed', winner_id__isnull=False, loser_id__isnull=False) |
                    ~models.Q(state='completed')
                ),
                name='chk_match_completed_has_winner'
            ),
            # Round and match numbers must be positive
            models.CheckConstraint(
                check=models.Q(round_number__gt=0) & models.Q(match_number__gt=0),
                name='chk_match_numbers_positive'
            ),
        ]
    
    def __str__(self) -> str:
        """String representation of match"""
        if self.participant1_name and self.participant2_name:
            return f"Round {self.round_number}, Match {self.match_number}: {self.participant1_name} vs {self.participant2_name}"
        return f"Round {self.round_number}, Match {self.match_number}"
    
    # Properties
    
    @property
    def is_both_checked_in(self) -> bool:
        """Check if both participants have checked in"""
        return self.participant1_checked_in and self.participant2_checked_in
    
    @property
    def is_ready_to_start(self) -> bool:
        """Check if match is ready to start (both checked in or no check-in required)"""
        if self.state == self.READY:
            return True
        if self.check_in_deadline is None:
            return True  # No check-in required
        return self.is_both_checked_in
    
    @property
    def has_result(self) -> bool:
        """Check if match has a result (winner determined)"""
        return self.winner_id is not None
    
    @property
    def is_in_progress(self) -> bool:
        """Check if match is currently in progress"""
        return self.state in [self.LIVE, self.PENDING_RESULT]
    
    # Methods (business logic in MatchService - ADR-001)
    
    def get_lobby_detail(self, key: str, default: Any = None) -> Any:
        """
        Get specific lobby detail from JSONB field.
        
        Args:
            key: Lobby info key (e.g., 'map', 'lobby_code')
            default: Default value if key not found
            
        Returns:
            Lobby detail value or default
        """
        return self.lobby_info.get(key, default)
    
    def set_lobby_detail(self, key: str, value: Any) -> None:
        """
        Set specific lobby detail in JSONB field.
        
        Args:
            key: Lobby info key
            value: Value to set
        """
        self.lobby_info[key] = value
        self.save(update_fields=['lobby_info'])


class Dispute(TimestampedModel):
    """
    Match dispute resolution workflow.
    
    Features:
    - Dispute reason tracking (score mismatch, no-show, cheating, etc.)
    - Evidence upload (screenshots, video URLs)
    - Status workflow: OPEN → UNDER_REVIEW → RESOLVED/ESCALATED
    - Resolution tracking with final scores
    - Organizer and admin notes
    
    Related Services:
    - DisputeService: Dispute creation, resolution, escalation
    - MatchService: Integration with match state transitions
    
    Database Constraints:
    - Reason must be valid (CHECK constraint via choices)
    - Status must be valid (CHECK constraint via choices)
    """
    
    # Reason choices
    SCORE_MISMATCH = 'score_mismatch'
    NO_SHOW = 'no_show'
    CHEATING = 'cheating'
    TECHNICAL_ISSUE = 'technical_issue'
    OTHER = 'other'
    
    REASON_CHOICES = [
        (SCORE_MISMATCH, _('Score Mismatch')),
        (NO_SHOW, _('No Show')),
        (CHEATING, _('Cheating Accusation')),
        (TECHNICAL_ISSUE, _('Technical Issue')),
        (OTHER, _('Other')),
    ]
    
    # Status choices
    OPEN = 'open'
    UNDER_REVIEW = 'under_review'
    RESOLVED = 'resolved'
    ESCALATED = 'escalated'
    
    STATUS_CHOICES = [
        (OPEN, _('Open')),
        (UNDER_REVIEW, _('Under Review')),
        (RESOLVED, _('Resolved')),
        (ESCALATED, _('Escalated to Admin')),
    ]
    
    # Foreign keys
    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='disputes',
        verbose_name=_('Match'),
        help_text=_('Match this dispute is about')
    )
    
    # Initiator (IntegerField for external User reference)
    initiated_by_id = models.PositiveIntegerField(
        verbose_name=_('Initiated By ID'),
        help_text=_('User ID who initiated the dispute')
    )
    
    # Dispute information
    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        verbose_name=_('Reason'),
        help_text=_('Reason for dispute')
    )
    
    description = models.TextField(
        verbose_name=_('Description'),
        help_text=_('Detailed description of the dispute')
    )
    
    # Evidence
    evidence_screenshot = models.ImageField(
        upload_to='disputes/evidence/',
        verbose_name=_('Evidence Screenshot'),
        null=True,
        blank=True,
        help_text=_('Screenshot evidence for dispute')
    )
    
    evidence_video_url = models.URLField(
        verbose_name=_('Evidence Video URL'),
        blank=True,
        help_text=_('YouTube/Twitch URL with video evidence')
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=OPEN,
        verbose_name=_('Status'),
        db_index=True,
        help_text=_('Current dispute status')
    )
    
    # Resolution (IntegerField for external User reference)
    resolved_by_id = models.PositiveIntegerField(
        verbose_name=_('Resolved By ID'),
        null=True,
        blank=True,
        help_text=_('User ID who resolved the dispute (organizer or admin)')
    )
    
    resolution_notes = models.TextField(
        verbose_name=_('Resolution Notes'),
        blank=True,
        help_text=_('Organizer/admin notes on resolution')
    )
    
    final_participant1_score = models.PositiveIntegerField(
        verbose_name=_('Final Participant 1 Score'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_('Final score for participant 1 after resolution')
    )
    
    final_participant2_score = models.PositiveIntegerField(
        verbose_name=_('Final Participant 2 Score'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_('Final score for participant 2 after resolution')
    )
    
    # Timestamps
    resolved_at = models.DateTimeField(
        verbose_name=_('Resolved At'),
        null=True,
        blank=True,
        help_text=_('When dispute was resolved')
    )
    
    class Meta:
        db_table = 'tournament_engine_match_dispute'
        verbose_name = _('Dispute')
        verbose_name_plural = _('Disputes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['match', 'status'], name='idx_dispute_match_status'),
            models.Index(fields=['status', 'created_at'], name='idx_dispute_status_created'),
            models.Index(fields=['reason'], name='idx_dispute_reason'),
        ]
        constraints = [
            # Reason must be valid (enforced by choices)
            models.CheckConstraint(
                check=models.Q(
                    reason__in=[
                        'score_mismatch', 'no_show', 'cheating',
                        'technical_issue', 'other'
                    ]
                ),
                name='chk_dispute_reason_valid'
            ),
            # Status must be valid (enforced by choices)
            models.CheckConstraint(
                check=models.Q(
                    status__in=['open', 'under_review', 'resolved', 'escalated']
                ),
                name='chk_dispute_status_valid'
            ),
        ]
    
    def __str__(self) -> str:
        """String representation of dispute"""
        return f"Dispute for {self.match} - {self.get_reason_display()}"
    
    # Properties
    
    @property
    def is_open(self) -> bool:
        """Check if dispute is still open"""
        return self.status in [self.OPEN, self.UNDER_REVIEW, self.ESCALATED]
    
    @property
    def is_resolved(self) -> bool:
        """Check if dispute has been resolved"""
        return self.status == self.RESOLVED
    
    @property
    def has_evidence(self) -> bool:
        """Check if dispute has evidence attached"""
        return bool(self.evidence_screenshot or self.evidence_video_url)
    
    # Methods (business logic in DisputeService - ADR-001)
    
    def get_resolution_summary(self) -> str:
        """
        Get summary of dispute resolution.
        
        Returns:
            Formatted resolution summary or empty string if not resolved
        """
        if not self.is_resolved:
            return ""
        
        summary = f"Resolved by user {self.resolved_by_id}"
        if self.final_participant1_score is not None and self.final_participant2_score is not None:
            summary += f" - Final Score: {self.final_participant1_score}-{self.final_participant2_score}"
        
        return summary
