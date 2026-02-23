"""
Prize Claim Model — Hub Bounty Board Module

When a tournament ends and PrizeTransaction records exist, eligible players
see a "Claim Prize" button in the Hub's Prizes tab. This model bridges the
UI action to the Economy app's payout pipeline.

Created: February 2026
"""

from django.conf import settings
from django.db import models
from apps.common.models import TimestampedModel


class PrizeClaim(TimestampedModel):
    """
    Player-initiated prize claim linked to a PrizeTransaction.

    Workflow:
        1. Tournament completes → PrizeTransaction records created (via PayoutService)
        2. Player opens Hub Prizes tab → sees their PrizeTransaction with "Claim Prize"
        3. Player submits claim → PrizeClaim created (status='pending')
        4. Organizer/admin reviews → status='processing'
        5. Payout executed → status='paid', paid_at set
        6. If rejected → status='rejected', admin_notes explains why

    Attributes:
        prize_transaction: OneToOne link to the PrizeTransaction
        claimed_by: The user claiming the prize
        payout_method: Chosen payout channel (deltacoin/bkash/nagad/rocket/bank)
        payout_destination: Masked target (e.g., bKash 017****678)
        status: Claim lifecycle state
        claimed_at: When the claim was submitted
        paid_at: When the payout was executed
        admin_notes: Internal notes from the admin/organizer
    """

    PAYOUT_DELTACOIN = 'deltacoin'
    PAYOUT_BKASH = 'bkash'
    PAYOUT_NAGAD = 'nagad'
    PAYOUT_ROCKET = 'rocket'
    PAYOUT_BANK = 'bank'

    PAYOUT_METHOD_CHOICES = [
        (PAYOUT_DELTACOIN, 'DeltaCoin Wallet'),
        (PAYOUT_BKASH, 'bKash'),
        (PAYOUT_NAGAD, 'Nagad'),
        (PAYOUT_ROCKET, 'Rocket'),
        (PAYOUT_BANK, 'Bank Transfer'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_PAID = 'paid'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_PAID, 'Paid'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    prize_transaction = models.OneToOneField(
        'tournaments.PrizeTransaction',
        on_delete=models.CASCADE,
        related_name='claim',
        help_text='The prize transaction being claimed',
    )
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prize_claims',
        help_text='User who claimed the prize',
    )
    payout_method = models.CharField(
        max_length=20,
        choices=PAYOUT_METHOD_CHOICES,
        default=PAYOUT_DELTACOIN,
        help_text='Chosen payout method',
    )
    payout_destination = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Masked payout target (e.g., 017****678)',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        help_text='Current claim lifecycle state',
    )
    claimed_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the user submitted the claim',
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the payout was executed',
    )
    admin_notes = models.TextField(
        blank=True,
        default='',
        help_text='Internal notes from organizer/admin',
    )

    class Meta:
        db_table = 'tournaments_prize_claim'
        ordering = ['-claimed_at']
        verbose_name = 'Prize Claim'
        verbose_name_plural = 'Prize Claims'
        indexes = [
            models.Index(fields=['status', 'claimed_at'], name='idx_prizeclaim_status_date'),
            models.Index(fields=['claimed_by'], name='idx_prizeclaim_user'),
        ]

    def __str__(self):
        return (
            f"PrizeClaim(tx={self.prize_transaction_id}, "
            f"user={self.claimed_by_id}, status={self.status})"
        )

    @property
    def is_claimable(self):
        """Whether this claim can still be processed."""
        return self.status in (self.STATUS_PENDING, self.STATUS_PROCESSING)
