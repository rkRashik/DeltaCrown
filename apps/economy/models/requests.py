# apps/economy/models/requests.py
from __future__ import annotations

from django.conf import settings
from django.db import models, transaction

from apps.common.managers import SoftDeleteManager
from apps.common.models import SoftDeleteModel
from .wallet import DeltaCrownWallet
from .transaction import DeltaCrownTransaction


class TopUpRequest(SoftDeleteModel):
    """
    Bangladesh Payment Top-Up Request.
    
    Workflow:
    1. User submits top-up request (amount + payment method + payment proof)
    2. Status = 'pending'
    3. Admin reviews payment proof
    4. On approval: DeltaCrownTransaction created (credit), status='completed'
    5. On rejection: status='rejected' with reason
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        COMPLETED = 'completed', 'Completed'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class PaymentMethod(models.TextChoices):
        BKASH = 'bkash', 'bKash'
        NAGAD = 'nagad', 'Nagad'
        ROCKET = 'rocket', 'Rocket'
        BANK = 'bank', 'Bank Transfer'
    
    # Core Fields
    wallet = models.ForeignKey(
        DeltaCrownWallet,
        on_delete=models.PROTECT,
        related_name='topup_requests'
    )
    amount = models.PositiveIntegerField(
        help_text='Amount in DeltaCoins to add'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Payment Details
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices
    )
    payment_number = models.CharField(
        max_length=50,
        help_text='bKash/Nagad/Rocket transaction ID or bank reference'
    )
    payment_details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional payment info (sender name, transaction ID, etc.)'
    )
    
    # Exchange Rate
    dc_to_bdt_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        help_text='DeltaCoin to BDT exchange rate (e.g., 1 DC = 1.00 BDT)'
    )
    bdt_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Amount paid in BDT'
    )
    
    # Review Metadata
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_topups'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When credits were actually added'
    )
    
    # Notes
    user_note = models.TextField(
        blank=True,
        default='',
        help_text='User note/payment proof details'
    )
    admin_note = models.TextField(
        blank=True,
        default='',
        help_text='Admin note (approval details, verification notes, etc.)'
    )
    rejection_reason = models.TextField(
        blank=True,
        default='',
        help_text='Reason for rejection (shown to user)'
    )
    
    # Transaction Reference
    transaction = models.ForeignKey(
        DeltaCrownTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='topup_request',
        help_text='Transaction that credited the coins (created on approval)'
    )
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['wallet', '-requested_at']),
            models.Index(fields=['status', '-requested_at']),
        ]
        verbose_name = 'Top-Up Request'
        verbose_name_plural = 'Top-Up Requests'
    
    def __str__(self):
        return f"TopUp {self.id}: {self.amount} DC via {self.get_payment_method_display()} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        """Calculate BDT amount if not set"""
        if not self.bdt_amount and self.amount:
            self.bdt_amount = self.amount * self.dc_to_bdt_rate
        super().save(*args, **kwargs)


class WithdrawalRequest(SoftDeleteModel):
    """
    [DEPRECATED — Architectural Pivot: Closed-Loop Economy Compliance]

    DC-to-Fiat withdrawals are no longer permitted under regional financial
    regulations. DeltaCoins are a closed-loop utility currency only.

    This model is RETAINED for:
      - Migration history integrity (0001_initial.py references it)
      - Backward compatibility with existing signals, tests, and views
        that have not yet been migrated
      - Audit trail of historical withdrawal records

    DO NOT create new WithdrawalRequest rows in production.
    Use PrizeClaim (below) for official tournament prize disbursements.

    Original Workflow (legacy reference):
    1. User requests withdrawal (amount + payment method + PIN verification)
    2. Status changes to 'pending'
    3. Amount is locked in wallet.pending_balance
    4. Admin reviews and approves/rejects
    5. On approval: funds transferred, status='completed', pending_balance reduced
    6. On rejection: pending_balance returned to available balance
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        COMPLETED = 'completed', 'Completed'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class PaymentMethod(models.TextChoices):
        BKASH = 'bkash', 'bKash'
        NAGAD = 'nagad', 'Nagad'
        ROCKET = 'rocket', 'Rocket'
        BANK = 'bank', 'Bank Transfer'
    
    # Core Fields
    wallet = models.ForeignKey(
        DeltaCrownWallet,
        on_delete=models.PROTECT,
        related_name='withdrawal_requests'
    )
    amount = models.PositiveIntegerField(
        help_text='Amount in DeltaCoins to withdraw'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Payment Details
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices
    )
    payment_number = models.CharField(
        max_length=50,
        help_text='bKash/Nagad/Rocket number or bank account number'
    )
    payment_details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional payment info (bank name, branch, account name, etc.)'
    )
    
    # Exchange Rate & Fee
    dc_to_bdt_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        help_text='DeltaCoin to BDT exchange rate (e.g., 1 DC = 1.00 BDT)'
    )
    processing_fee = models.PositiveIntegerField(
        default=0,
        help_text='Processing fee in DeltaCoins'
    )
    bdt_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Amount in BDT after conversion'
    )
    
    # Review Metadata
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_withdrawals'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When funds were actually transferred'
    )
    
    # Notes
    user_note = models.TextField(
        blank=True,
        default='',
        help_text='User note/reason for withdrawal'
    )
    admin_note = models.TextField(
        blank=True,
        default='',
        help_text='Admin note (rejection reason, transfer details, etc.)'
    )
    rejection_reason = models.TextField(
        blank=True,
        default='',
        help_text='Reason for rejection (shown to user)'
    )
    
    # Transaction Reference
    transaction = models.ForeignKey(
        DeltaCrownTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='withdrawal_request',
        help_text='Transaction that debited the coins (created on approval)'
    )
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['wallet', '-requested_at']),
            models.Index(fields=['status', '-requested_at']),
        ]
        verbose_name = 'Withdrawal Request'
        verbose_name_plural = 'Withdrawal Requests'
    
    def __str__(self):
        return f"Withdrawal {self.id}: {self.amount} DC via {self.get_payment_method_display()} - {self.get_status_display()}"
    
    @property
    def net_amount(self):
        """Amount after processing fee"""
        return self.amount - self.processing_fee
    
    @property
    def can_cancel(self):
        """Check if user can cancel this request"""
        return self.status == self.Status.PENDING
    
    @property
    def can_review(self):
        """Check if admin can review this request"""
        return self.status == self.Status.PENDING
    
    def save(self, *args, **kwargs):
        """Calculate BDT amount on save"""
        if not self.bdt_amount:
            self.bdt_amount = float(self.net_amount) * float(self.dc_to_bdt_rate)
        super().save(*args, **kwargs)
    
    def approve(self, reviewed_by, admin_note='', completed_immediately=True):
        """
        Approve withdrawal request.

        Creates up to two ledger rows atomically:
          1. WITHDRAWAL debit        → user wallet (full withdrawal amount)
          2. WITHDRAWAL_REVENUE credit → Master Treasury (processing fee, if > 0)

        Args:
            reviewed_by:           User who approved the request.
            admin_note:            Admin notes about the approval.
            completed_immediately: If True, mark as COMPLETED immediately.
        """
        from django.utils import timezone
        from apps.economy.services import get_master_treasury

        if self.status != self.Status.PENDING:
            raise ValueError(f"Cannot approve withdrawal with status '{self.status}'")

        with transaction.atomic():
            # Lock wallet to prevent race conditions on concurrent approvals
            wallet = DeltaCrownWallet.objects.select_for_update().get(pk=self.wallet_id)

            if not wallet.allow_overdraft and wallet.cached_balance < self.amount:
                raise ValueError(
                    f"Insufficient wallet balance ({wallet.cached_balance} DC) "
                    f"to cover withdrawal of {self.amount} DC."
                )

            # 1. Debit full withdrawal amount from user wallet
            wallet.cached_balance -= self.amount
            wallet.pending_balance = max(0, wallet.pending_balance - self.amount)
            wallet.last_withdrawal_at = timezone.now()
            wallet.save(update_fields=['cached_balance', 'pending_balance',
                                       'last_withdrawal_at', 'updated_at'])

            debit_transaction = DeltaCrownTransaction.objects.create(
                wallet=wallet,
                amount=-self.amount,
                reason=DeltaCrownTransaction.Reason.WITHDRAWAL,
                note=f"Withdrawal #{self.id} via {self.get_payment_method_display()}",
                created_by=reviewed_by,
                idempotency_key=f"withdrawal_{self.id}",
                cached_balance_after=wallet.cached_balance,
            )

            # 2. Credit processing fee to Master Treasury (if applicable)
            fee = getattr(self, 'processing_fee', 0) or 0
            if fee > 0:
                treasury = get_master_treasury()
                DeltaCrownTransaction.objects.create(
                    wallet=treasury,
                    amount=+fee,
                    reason=DeltaCrownTransaction.Reason.WITHDRAWAL_REVENUE,
                    note=f"Processing fee for withdrawal #{self.id}",
                    created_by=reviewed_by,
                    idempotency_key=f"withdrawal_fee_{self.id}",
                )
                treasury.recalc_and_save()

            self.transaction = debit_transaction
            self.status = self.Status.COMPLETED if completed_immediately else self.Status.APPROVED
            self.reviewed_by = reviewed_by
            self.reviewed_at = timezone.now()
            self.admin_note = admin_note

            if completed_immediately:
                self.completed_at = timezone.now()

            self.save()


    def reject(self, reviewed_by, rejection_reason):
        """
        Reject withdrawal request.
        
        Args:
            reviewed_by: User who rejected the request
            rejection_reason: Reason for rejection (shown to user)
        """
        from django.utils import timezone
        
        if self.status != self.Status.PENDING:
            raise ValueError(f"Cannot reject withdrawal with status '{self.status}'")
        
        with transaction.atomic():
            self.wallet.pending_balance = max(0, self.wallet.pending_balance - self.amount)
            self.wallet.save(update_fields=['pending_balance', 'updated_at'])
            
            self.status = self.Status.REJECTED
            self.reviewed_by = reviewed_by
            self.reviewed_at = timezone.now()
            self.rejection_reason = rejection_reason
            self.admin_note = rejection_reason
            
            self.save()
    
    def cancel(self):
        """
        Cancel withdrawal request (user-initiated).
        Only allowed for pending requests.
        """
        if not self.can_cancel:
            raise ValueError(f"Cannot cancel withdrawal with status '{self.status}'")
        
        with transaction.atomic():
            self.wallet.pending_balance = max(0, self.wallet.pending_balance - self.amount)
            self.wallet.save(update_fields=['pending_balance', 'updated_at'])
            
            self.status = self.Status.CANCELLED
            self.save()


# =============================================================================
# PRIZE CLAIM — Fiat Prize Disbursement (Compliance replacement for withdrawals)
# =============================================================================

class PrizeClaim(SoftDeleteModel):
    """
    Official tournament prize disbursement ticket.

    Architecture Note
    -----------------
    This model handles **direct BDT (fiat) payouts** to tournament winners.
    It has NO relationship with DeltaCrownTransaction because the funds flow
    entirely outside the DC economy — from the organizer/platform bank account
    directly to the winner's mobile banking or bank account.

    Closed-Loop Compliance:
    - DeltaCoins can never be converted back to fiat (DC is utility-only).
    - This model is the ONLY sanctioned path for real-money prize disbursement.
    - KYC requirement is governed by the tournament's `require_kyc_for_prizes`.

    Workflow:
    1. Tournament completes → winner is determined.
    2. Winner submits a PrizeClaim ticket (amount, method, account details).
    3. Status = PENDING → admin reviews.
    4. If KYC required → Status = VERIFYING_KYC → documents checked.
    5. Admin manually disburses funds externally (bKash / Nagad / Bank).
    6. Admin marks Status = PAID with transfer reference in admin_note.
    7. On fraud/dispute → Status = REJECTED with admin_note explaining why.
    """

    class Status(models.TextChoices):
        PENDING       = 'pending',       'Pending Review'
        VERIFYING_KYC = 'verifying_kyc', 'Verifying KYC'
        PAID          = 'paid',          'Paid'
        REJECTED      = 'rejected',      'Rejected'

    class PaymentMethod(models.TextChoices):
        BKASH = 'bkash', 'bKash'
        NAGAD = 'nagad', 'Nagad'
        BANK  = 'bank',  'Bank Transfer'

    # ── Core ──────────────────────────────────────────────────────────────────
    wallet = models.ForeignKey(
        DeltaCrownWallet,
        on_delete=models.PROTECT,
        related_name='prize_claims',
        help_text='Wallet of the winner (used for identity reference only — no DC movement occurs)'
    )
    tournament_name = models.CharField(
        max_length=255,
        help_text='Name of the tournament (denormalised for audit stability after deletion/rename)'
    )
    amount_bdt = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Prize amount in BDT (Bangladeshi Taka) to be disbursed externally'
    )

    # ── Payout Details ────────────────────────────────────────────────────────
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        help_text='Channel through which the admin will transfer the funds'
    )
    account_details = models.TextField(
        help_text=(
            'Full account details for the selected payment method. '
            'bKash/Nagad: "01XXXXXXXXX (Account Name)". '
            'Bank: "Account No / Branch / Bank Name / Routing No".'
        )
    )

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    admin_note = models.TextField(
        blank=True,
        default='',
        help_text=(
            'Admin-only note. On PAID: record the external transfer reference '
            '(e.g. bKash TrxID). On REJECTED: explain the reason clearly.'
        )
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the winner submitted this claim'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When an admin marked this claim PAID or REJECTED'
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_prize_claims',
        help_text='Admin who processed this claim'
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['wallet', '-submitted_at']),
            models.Index(fields=['status', '-submitted_at']),
        ]
        verbose_name = 'Prize Claim'
        verbose_name_plural = 'Prize Claims'

    def __str__(self):
        return (
            f"PrizeClaim #{self.id}: ৳{self.amount_bdt} via "
            f"{self.get_payment_method_display()} [{self.get_status_display()}]"
        )

    @property
    def can_resolve(self) -> bool:
        """True when the claim is still awaiting admin action."""
        return self.status in (self.Status.PENDING, self.Status.VERIFYING_KYC)

    def mark_paid(self, admin_user, transfer_reference: str = '') -> None:
        """
        Mark this claim as PAID after the external transfer is complete.

        Args:
            admin_user:         Staff user marking the claim paid.
            transfer_reference: External reference (e.g. bKash TrxID).

        Raises:
            ValueError: If the claim is not in a resolvable state.
        """
        from django.utils import timezone
        if not self.can_resolve:
            raise ValueError(
                f"Cannot mark PrizeClaim #{self.id} as PAID "
                f"from status '{self.status}'."
            )
        self.status = self.Status.PAID
        self.resolved_by = admin_user
        self.resolved_at = timezone.now()
        if transfer_reference:
            self.admin_note = f"Transfer ref: {transfer_reference}"
        self.save(update_fields=['status', 'resolved_by', 'resolved_at', 'admin_note'])

    def reject(self, admin_user, reason: str) -> None:
        """
        Reject this claim.

        Args:
            admin_user: Staff user rejecting the claim.
            reason:     Reason for rejection (stored in admin_note).

        Raises:
            ValueError: If the claim is not in a resolvable state.
        """
        from django.utils import timezone
        if not self.can_resolve:
            raise ValueError(
                f"Cannot reject PrizeClaim #{self.id} "
                f"from status '{self.status}'."
            )
        self.status = self.Status.REJECTED
        self.resolved_by = admin_user
        self.resolved_at = timezone.now()
        self.admin_note = reason
        self.save(update_fields=['status', 'resolved_by', 'resolved_at', 'admin_note'])
