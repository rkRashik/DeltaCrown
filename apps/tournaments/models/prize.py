"""
Prize Transaction Model for Tournament Payouts

Module 5.2: Prize Payouts & Reconciliation

Implements:
- PART_2.2_SERVICES_INTEGRATION.md#section-6-integration-patterns (apps.economy)
- PART_3.1_DATABASE_DESIGN_ERD.md#section-3-tournament-models (prize_pool, prize_distribution)
- PHASE_5_IMPLEMENTATION_PLAN.md#module-52-prize-payouts--reconciliation
- 01_ARCHITECTURE_DECISIONS.md#adr-001-service-layer-pattern

This model serves as an audit trail for prize payouts. It records the intent to pay
and links to apps.economy.DeltaCrownTransaction for the actual coin transfer.

Architecture Note:
    Uses IntegerField for coin_transaction_id (not FK) to maintain decoupling from
    apps.economy. This follows the established pattern where economy models use
    IntegerField references to tournament entities (see apps/economy/models.py).
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import TimestampedModel


class PrizeTransaction(TimestampedModel):
    """
    Audit trail for tournament prize payouts.
    
    Records prize distribution to tournament participants. Each transaction represents
    a payout to a single participant for a specific placement. Links to DeltaCrownTransaction
    in apps.economy for the actual coin transfer.
    
    Workflow:
        1. Tournament completes (Module 5.1 determines winner)
        2. PayoutService creates PrizeTransaction records (status='pending')
        3. Service creates DeltaCrownTransaction in apps.economy
        4. PrizeTransaction updated with coin_transaction_id (status='completed')
    
    Attributes:
        tournament: Tournament awarding the prize
        participant: Registration receiving the prize (winner/runner-up/3rd/participation)
        placement: Placement earned ('1st', '2nd', '3rd', 'participation')
        amount: Prize amount in Delta Coins (always >= 0)
        coin_transaction_id: Reference to DeltaCrownTransaction.id (IntegerField, not FK)
        created_at: Timestamp when transaction was created (from TimestampedModel)
        updated_at: Timestamp when transaction was last updated (from TimestampedModel)
        processed_by: User who triggered the payout (organizer/admin)
        status: Current status (pending/completed/failed/refunded)
        notes: Optional notes for manual adjustments or reconciliation
    """
    
    class Placement(models.TextChoices):
        FIRST = '1st', '1st Place'
        SECOND = '2nd', '2nd Place'
        THIRD = '3rd', '3rd Place'
        PARTICIPATION = 'participation', 'Participation Reward'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
    
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='prize_transactions',
        help_text="Tournament awarding this prize"
    )
    participant = models.ForeignKey(
        'Registration',
        on_delete=models.PROTECT,
        related_name='prize_transactions',
        help_text="Registration receiving this prize"
    )
    placement = models.CharField(
        max_length=20,
        choices=Placement.choices,
        help_text="Placement earned by participant"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Prize amount in Delta Coins"
    )
    
    # Economy Integration (IntegerField pattern for decoupling)
    coin_transaction_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of DeltaCrownTransaction in apps.economy (reference only, not FK)"
    )
    
    # Metadata
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_prize_transactions',
        help_text="User who triggered the payout"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current status of this prize transaction"
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional notes for manual adjustments or reconciliation"
    )
    
    class Meta:
        db_table = 'tournament_engine_prize_prizetransaction'
        verbose_name = 'Prize Transaction'
        verbose_name_plural = 'Prize Transactions'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['tournament', 'status'], name='prize_tournament_status_idx'),
            models.Index(fields=['participant'], name='prize_participant_idx'),
            models.Index(fields=['coin_transaction_id'], name='prize_coin_tx_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gte=0),
                name='prize_amount_positive',
                violation_error_message="Prize amount must be non-negative"
            ),
            models.UniqueConstraint(
                fields=['tournament', 'participant', 'placement'],
                name='unique_prize_per_participant_placement',
                violation_error_message="Participant can only receive one prize per placement per tournament"
            ),
        ]
    
    def __str__(self) -> str:
        return (
            f"PrizeTransaction(tournament={self.tournament_id}, "
            f"participant={self.participant_id}, "
            f"placement={self.placement}, "
            f"amount={self.amount}, "
            f"status={self.status})"
        )
    
    def clean(self) -> None:
        """
        Validate prize transaction data.
        
        Raises:
            ValidationError: If amount is negative or participant not in tournament
        """
        super().clean()
        
        # Validate amount is non-negative (also enforced by CheckConstraint)
        if self.amount is not None and self.amount < Decimal('0'):
            raise ValidationError({
                'amount': 'Prize amount must be non-negative'
            })
        
        # Validate participant is registered for this tournament
        if self.tournament_id and self.participant_id:
            if self.participant.tournament_id != self.tournament_id:
                raise ValidationError({
                    'participant': f'Participant (Registration {self.participant_id}) is not registered for Tournament {self.tournament_id}'
                })
    
    def save(self, *args, **kwargs):
        """
        Save prize transaction with validation.
        
        Calls full_clean() to ensure all constraints are validated before saving.
        """
        self.full_clean()
        super().save(*args, **kwargs)
