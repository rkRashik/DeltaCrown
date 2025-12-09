"""
Tournament Stage Models

Source Documents:
- Documents/Planning/LIFECYCLE_GAPS.md (Multi-stage tournament flow)
- Documents/Modify_TournamentApp/Workplan/DEV_PROGRESS_TRACKER.md (Epic 3.4)

Models:
- TournamentStage: Represents a sequential phase in a multi-stage tournament

Epic 3.4: Stage Transitions System
Enables "Group Stage → Playoffs" and other multi-stage tournament flows.
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, CheckConstraint

from apps.common.models import TimestampedModel


class TournamentStage(TimestampedModel):
    """
    Represents a sequential stage/phase in a multi-stage tournament.
    
    Examples:
    - Stage 1: Group Stage (round-robin within groups)
    - Stage 2: Playoffs (single-elimination bracket from top group finishers)
    - Stage 3: Grand Finals (best-of series)
    
    Supports:
    - Sequential ordering (order field)
    - Different formats per stage (round_robin, single_elim, double_elim, swiss)
    - Advancement rules (top N overall, top N per group, etc.)
    - State tracking (pending, active, completed)
    
    Epic 3.4: Stage Transitions System
    """
    
    # Format choices
    FORMAT_ROUND_ROBIN = 'round_robin'
    FORMAT_SINGLE_ELIM = 'single_elim'
    FORMAT_DOUBLE_ELIM = 'double_elim'
    FORMAT_SWISS = 'swiss'
    
    FORMAT_CHOICES = [
        (FORMAT_ROUND_ROBIN, 'Round Robin'),
        (FORMAT_SINGLE_ELIM, 'Single Elimination'),
        (FORMAT_DOUBLE_ELIM, 'Double Elimination'),
        (FORMAT_SWISS, 'Swiss System'),
    ]
    
    # State choices
    STATE_PENDING = 'pending'
    STATE_ACTIVE = 'active'
    STATE_COMPLETED = 'completed'
    
    STATE_CHOICES = [
        (STATE_PENDING, 'Pending'),
        (STATE_ACTIVE, 'Active'),
        (STATE_COMPLETED, 'Completed'),
    ]
    
    # Advancement criteria choices
    ADV_TOP_N = 'top_n'
    ADV_TOP_N_PER_GROUP = 'top_n_per_group'
    ADV_ALL = 'all'
    
    # Legacy aliases for backwards compatibility
    ADVANCEMENT_TOP_N = ADV_TOP_N
    ADVANCEMENT_TOP_N_PER_GROUP = ADV_TOP_N_PER_GROUP
    ADVANCEMENT_ALL = ADV_ALL
    
    ADVANCEMENT_CHOICES = [
        (ADV_TOP_N, 'Top N Overall'),
        (ADV_TOP_N_PER_GROUP, 'Top N Per Group'),
        (ADV_ALL, 'All Participants'),
    ]
    
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='stages',
        verbose_name=_('Tournament'),
        help_text=_('Tournament this stage belongs to')
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('Stage Name'),
        help_text=_('Name of this stage (e.g., "Group Stage", "Playoffs", "Grand Finals")')
    )
    
    order = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Order'),
        help_text=_('Sequential order of this stage (1 = first stage, 2 = second, etc.)')
    )
    
    format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        verbose_name=_('Format'),
        help_text=_('Tournament format for this stage')
    )
    
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Start Date'),
        help_text=_('Scheduled start date/time for this stage')
    )
    
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('End Date'),
        help_text=_('Scheduled or actual end date/time for this stage')
    )
    
    # Advancement configuration
    advancement_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Advancement Count'),
        help_text=_('Number of participants advancing to next stage (0 = final stage)')
    )
    
    advancement_criteria = models.CharField(
        max_length=20,
        choices=ADVANCEMENT_CHOICES,
        default=ADV_TOP_N,
        verbose_name=_('Advancement Criteria'),
        help_text=_('How participants advance to next stage')
    )
    
    # State tracking
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default=STATE_PENDING,
        verbose_name=_('State'),
        help_text=_('Current state of this stage')
    )
    
    # Optional link to GroupStage (if this stage is a group stage)
    group_stage = models.OneToOneField(
        'tournaments.GroupStage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournament_stage',
        verbose_name=_('Group Stage'),
        help_text=_('Link to GroupStage if this stage uses group format')
    )
    
    # Configuration
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Configuration'),
        help_text=_('JSON config: seeding_rules, tiebreakers, bracket_options')
    )
    # Example config:
    # {
    #     "seeding_rules": {
    #         "preserve_group_winners": True,  # Group winners seeded higher
    #         "avoid_same_group_early": True   # Avoid same-group matchups in early rounds
    #     },
    #     "tiebreakers": ["points", "head_to_head", "score_diff"],
    #     "bracket_options": {
    #         "third_place_match": True,
    #         "grand_finals_reset": False
    #     }
    # }
    
    class Meta:
        db_table = 'tournament_stages'
        verbose_name = _('Tournament Stage')
        verbose_name_plural = _('Tournament Stages')
        ordering = ['tournament', 'order']
        indexes = [
            models.Index(fields=['tournament', 'order']),
            models.Index(fields=['tournament', 'state']),
        ]
        unique_together = [
            ('tournament', 'order'),  # Each tournament has unique stage ordering
        ]
        constraints = [
            CheckConstraint(
                check=Q(order__gte=1),
                name='stage_min_order'
            ),
            CheckConstraint(
                check=Q(advancement_count__gte=0),
                name='stage_min_advancement'
            ),
        ]
    
    def __str__(self):
        return f"{self.tournament.name} - Stage {self.order}: {self.name}"
    
    def clean(self):
        """Validate stage configuration."""
        super().clean()
        
        # Validate date range
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date")
        
        # Validate group stage link
        if self.format == self.FORMAT_ROUND_ROBIN and not self.group_stage:
            # This is acceptable - could be a simple round-robin without groups
            pass
        
        if self.group_stage and self.format != self.FORMAT_ROUND_ROBIN:
            raise ValidationError(
                "Group stage link can only be used with round_robin format"
            )
    
    @property
    def is_group_stage(self):
        """Check if this stage is a group stage."""
        return self.group_stage is not None
    
    @property
    def is_final_stage(self):
        """Check if this is the final stage (no advancement)."""
        return self.advancement_count == 0
    
    @property
    def next_stage(self):
        """Get the next stage in the tournament."""
        return TournamentStage.objects.filter(
            tournament=self.tournament,
            order=self.order + 1
        ).first()
    
    @property
    def previous_stage(self):
        """Get the previous stage in the tournament."""
        return TournamentStage.objects.filter(
            tournament=self.tournament,
            order=self.order - 1
        ).first()
    
    def can_advance(self):
        """Check if participants can advance from this stage."""
        return not self.is_final_stage and self.state == self.STATE_COMPLETED
