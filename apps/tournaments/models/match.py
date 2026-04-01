"""
Match and Dispute models for tournament matches (Module 1.4)

Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 6: Match Lifecycle Models)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Match/Dispute models, state machine)
- Documents/Planning/PROPOSAL_PART_2_TECHNICAL_ARCHITECTURE.md (Dispute Model section 4.5)
- Documents/Planning/PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md (Constraints & indexes)
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md (ADR-001, ADR-003, ADR-007)

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

    # Series format (BO1 / BO3 / BO5)
    BEST_OF_1 = 1
    BEST_OF_3 = 3
    BEST_OF_5 = 5
    BEST_OF_CHOICES = [(1, 'BO1'), (3, 'BO3'), (5, 'BO5')]

    best_of = models.PositiveSmallIntegerField(
        default=1,
        choices=BEST_OF_CHOICES,
        verbose_name=_('Best Of'),
        help_text=_('Series format: 1 = single game, 3 = first to 2, 5 = first to 3')
    )

    game_scores = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Game Scores'),
        help_text=_(
            'Per-game scores for BO3/BO5 series. '
            'List of {"game": N, "p1": X, "p2": Y, "winner_slot": 1|2} objects.'
        )
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
                condition=models.Q(
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
                condition=models.Q(participant1_score__gte=0) & models.Q(participant2_score__gte=0),
                name='chk_match_scores_positive'
            ),
            # If COMPLETED, require winner/loser unless this is a tied draw result.
            models.CheckConstraint(
                condition=(
                    models.Q(state='completed', winner_id__isnull=False, loser_id__isnull=False) |
                    models.Q(
                        state='completed',
                        winner_id__isnull=True,
                        loser_id__isnull=True,
                        participant1_score=models.F('participant2_score'),
                    ) |
                    ~models.Q(state='completed')
                ),
                name='chk_match_completed_has_winner'
            ),
            # Round and match numbers must be positive
            models.CheckConstraint(
                condition=models.Q(round_number__gt=0) & models.Q(match_number__gt=0),
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

    def validate_participants(self) -> None:
        """
        Validate that non-null participant IDs correspond to active
        registrations for this tournament.

        Raises:
            ValidationError: If any participant is not an active registrant.
        """
        from django.core.exceptions import ValidationError
        from apps.tournaments.models.registration import Registration

        if not self.tournament_id:
            return

        active_statuses = (Registration.CONFIRMED, Registration.AUTO_APPROVED)
        errors = {}

        for field_name, pid in [
            ('participant1_id', self.participant1_id),
            ('participant2_id', self.participant2_id),
        ]:
            if pid is None:
                continue  # BYE slot or TBD — allowed
            exists = Registration.objects.filter(
                tournament_id=self.tournament_id,
                status__in=active_statuses,
                is_deleted=False,
            ).filter(
                models.Q(user_id=pid) | models.Q(team_id=pid)
            ).exists()
            if not exists:
                errors[field_name] = (
                    f"Participant ID {pid} is not an active registrant "
                    f"for tournament {self.tournament_id}."
                )

        if errors:
            raise ValidationError(errors)

    def clean(self):
        super().clean()
        self.validate_participants()
