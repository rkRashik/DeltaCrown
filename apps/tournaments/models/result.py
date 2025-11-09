"""
Tournament Result Models

Tracks final tournament results and winner determination.

Related Planning:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md#module-51
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md#section-3-tournament-models

Module: apps.tournaments.models.result
Implements: phase_5:module_5_1
"""

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

from apps.common.models import TimestampedModel, SoftDeleteModel


class TournamentResult(TimestampedModel, SoftDeleteModel):
    """
    Final tournament results and winner determination.
    
    Created when all matches complete and winner is determined.
    Stores audit trail of determination logic.
    """
    
    # Foreign Keys
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='result',
        help_text="Tournament this result belongs to"
    )
    winner = models.ForeignKey(
        'tournaments.Registration',
        on_delete=models.PROTECT,
        related_name='won_tournaments',
        help_text="Winner participant (Registration record)"
    )
    final_bracket = models.ForeignKey(
        'tournaments.Bracket',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Bracket used for determination"
    )
    
    # Placements
    runner_up = models.ForeignKey(
        'tournaments.Registration',
        on_delete=models.PROTECT,
        related_name='runner_up_tournaments',
        null=True,
        blank=True,
        help_text="Second place participant"
    )
    third_place = models.ForeignKey(
        'tournaments.Registration',
        on_delete=models.PROTECT,
        related_name='third_place_tournaments',
        null=True,
        blank=True,
        help_text="Third place participant (if applicable)"
    )
    
    # Determination Metadata
    DETERMINATION_METHOD_CHOICES = [
        ('normal', 'Normal Bracket Resolution'),
        ('tiebreaker', 'Tie-Breaking Rules Applied'),
        ('forfeit_chain', 'Forfeit Chain Winner'),
        ('manual', 'Manual Organizer Selection'),
    ]
    
    determination_method = models.CharField(
        max_length=20,
        choices=DETERMINATION_METHOD_CHOICES,
        default='normal',
        help_text="Method used to determine winner"
    )
    
    rules_applied = models.JSONField(
        default=dict,
        help_text=(
            "JSONB audit trail of determination logic. "
            "Contains ordered list of rules applied, intermediate scores, "
            "and reasoning for winner selection."
        )
    )
    
    requires_review = models.BooleanField(
        default=False,
        help_text=(
            "Flag indicating organizer review needed "
            "(e.g., forfeit chain, tie-breaking failures)"
        )
    )
    
    # Audit Fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tournament_results',
        help_text="User who triggered determination (or verified manually)"
    )
    
    class Meta:
        db_table = 'tournament_engine_result_tournamentresult'
        verbose_name = 'Tournament Result'
        verbose_name_plural = 'Tournament Results'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tournament'], name='idx_result_tournament'),
            models.Index(fields=['winner'], name='idx_result_winner'),
            models.Index(fields=['determination_method'], name='idx_result_method'),
            models.Index(fields=['requires_review'], name='idx_result_review'),
            models.Index(fields=['created_at'], name='idx_result_created'),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(runner_up=models.F('winner')),
                name='runner_up_not_winner'
            ),
            models.CheckConstraint(
                check=(
                    models.Q(third_place__isnull=True) |
                    (
                        ~models.Q(third_place=models.F('winner')) &
                        ~models.Q(third_place=models.F('runner_up'))
                    )
                ),
                name='third_place_unique'
            ),
        ]
    
    def __str__(self):
        return f"Result: {self.tournament.title} - Winner: {self.winner}"
    
    def clean(self):
        """Validation logic for TournamentResult."""
        super().clean()
        
        # Ensure winner is not same as runner-up
        if self.runner_up and self.runner_up == self.winner:
            raise ValidationError({
                'runner_up': 'Runner-up cannot be the same as winner'
            })
        
        # Ensure third place is unique
        if self.third_place:
            if self.third_place == self.winner:
                raise ValidationError({
                    'third_place': 'Third place cannot be the same as winner'
                })
            if self.third_place == self.runner_up:
                raise ValidationError({
                    'third_place': 'Third place cannot be the same as runner-up'
                })
        
        # Ensure all participants belong to same tournament
        if self.winner.tournament_id != self.tournament_id:
            raise ValidationError({
                'winner': 'Winner must be participant in this tournament'
            })
        
        if self.runner_up and self.runner_up.tournament_id != self.tournament_id:
            raise ValidationError({
                'runner_up': 'Runner-up must be participant in this tournament'
            })
        
        if self.third_place and self.third_place.tournament_id != self.tournament_id:
            raise ValidationError({
                'third_place': 'Third place must be participant in this tournament'
            })
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
