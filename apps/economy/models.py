# apps/economy/models.py
# Implements: Documents/ExecutionPlan/Modules/MODULE_7.1_KICKOFF.md - Step 2 (Ledger Invariants)
from __future__ import annotations

from django.conf import settings
from django.db import models, transaction
from django.db.models import Sum
from django.contrib.auth.hashers import make_password, check_password

from .exceptions import InsufficientFunds, InvalidAmount


class DeltaCrownWallet(models.Model):
    """
    One wallet per user profile.
    cached_balance is a derived value from the immutable transaction ledger.
    
    allow_overdraft: If True, balance can go negative. Default False (reject debits beyond balance).
    
    Bangladesh Payment Integration:
    - bkash_number, nagad_number, rocket_number for mobile wallets
    - bank account details for direct deposits
    - pin_hash for withdrawal security
    - pending_balance for pending withdrawals
    """
    profile = models.OneToOneField(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="dc_wallet",
    )
    cached_balance = models.IntegerField(default=0)
    allow_overdraft = models.BooleanField(
        default=False,
        help_text="If True, allows negative balance (overdraft). Default: False (reject insufficient funds)."
    )
    
    # Bangladesh Mobile Payment Methods
    bkash_number = models.CharField(
        max_length=15,
        blank=True,
        default='',
        help_text="bKash mobile wallet number (e.g., 01712345678)"
    )
    nagad_number = models.CharField(
        max_length=15,
        blank=True,
        default='',
        help_text="Nagad mobile wallet number (e.g., 01812345678)"
    )
    rocket_number = models.CharField(
        max_length=15,
        blank=True,
        default='',
        help_text="Rocket mobile wallet number (e.g., 01912345678)"
    )
    
    # Bank Account Details
    bank_account_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Full name as per bank account"
    )
    bank_account_number = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text="Bank account number"
    )
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Name of the bank (e.g., Dutch-Bangla Bank, Brac Bank)"
    )
    bank_branch = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Branch name or code"
    )
    
    # Withdrawal Security
    pin_hash = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Hashed 4-digit PIN for withdrawal verification"
    )
    
    # Balance Tracking
    pending_balance = models.IntegerField(
        default=0,
        help_text="Balance locked in pending withdrawals"
    )
    lifetime_earnings = models.IntegerField(
        default=0,
        help_text="Total DeltaCoins earned from prizes (all-time)"
    )
    
    # Metadata
    last_withdrawal_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful withdrawal timestamp"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["profile"]),
        ]
        verbose_name = "DeltaCrown Wallet"

    def __str__(self) -> str:
        return f"Wallet<{getattr(self.profile, 'id', None)}>: {self.cached_balance}"
    
    # ====================================================================
    # Balance Methods
    # ====================================================================
    
    @property
    def available_balance(self) -> int:
        """
        Available balance (excluding pending withdrawals).
        This is the amount user can actually withdraw or spend.
        """
        return self.cached_balance - self.pending_balance

    @property
    def balance(self) -> int:
        """
        Backwards compatible alias for cached_balance used across older templates and tests.
        """
        return self.cached_balance
    
    @transaction.atomic
    def recalc_and_save(self) -> int:
        """
        Atomically recalculate cached_balance from ledger sum with row lock.
        
        Uses SELECT FOR UPDATE to prevent concurrent modifications.
        Returns the corrected balance.
        
        PII Discipline: Only logs wallet ID, no user data.
        """
        # Row lock: prevent concurrent updates during recalc
        locked_wallet = DeltaCrownWallet.objects.select_for_update().get(pk=self.pk)
        
        # Recompute from ledger
        total = locked_wallet.transactions.aggregate(s=Sum("amount"))["s"] or 0
        
        if locked_wallet.cached_balance != total:
            locked_wallet.cached_balance = int(total)
            locked_wallet.save(update_fields=["cached_balance", "updated_at"])
            # Refresh self to match locked_wallet state
            self.cached_balance = locked_wallet.cached_balance
        
        return self.cached_balance
    
    # ====================================================================
    # Bangladesh Payment Methods
    # ====================================================================
    
    def has_payment_method(self) -> bool:
        """Check if user has added any payment method"""
        return bool(
            self.bkash_number or 
            self.nagad_number or 
            self.rocket_number or 
            self.bank_account_number
        )
    
    def get_primary_payment_method(self) -> dict:
        """
        Get the first available payment method.
        Returns dict with 'type' and 'value' keys.
        """
        if self.bkash_number:
            return {'type': 'bkash', 'value': self.bkash_number}
        elif self.nagad_number:
            return {'type': 'nagad', 'value': self.nagad_number}
        elif self.rocket_number:
            return {'type': 'rocket', 'value': self.rocket_number}
        elif self.bank_account_number:
            return {
                'type': 'bank',
                'value': self.bank_account_number,
                'name': self.bank_account_name,
                'bank': self.bank_name,
                'branch': self.bank_branch
            }
        return {'type': None, 'value': None}
    
    def mask_payment_number(self, number: str) -> str:
        """
        Mask payment number for security (e.g., 01712345678 → 017*****78).
        Shows first 3 and last 2 digits.
        """
        if not number or len(number) < 6:
            return number
        
        visible_start = 3
        visible_end = 2
        masked_length = len(number) - visible_start - visible_end
        
        return f"{number[:visible_start]}{'*' * masked_length}{number[-visible_end:]}"
    
    def get_masked_bkash(self) -> str:
        """Get masked bKash number"""
        return self.mask_payment_number(self.bkash_number) if self.bkash_number else ''
    
    def get_masked_nagad(self) -> str:
        """Get masked Nagad number"""
        return self.mask_payment_number(self.nagad_number) if self.nagad_number else ''
    
    def get_masked_rocket(self) -> str:
        """Get masked Rocket number"""
        return self.mask_payment_number(self.rocket_number) if self.rocket_number else ''
    
    def get_masked_bank_account(self) -> str:
        """Get masked bank account number"""
        return self.mask_payment_number(self.bank_account_number) if self.bank_account_number else ''
    
    # ====================================================================
    # PIN Management
    # ====================================================================
    
    def set_pin(self, pin: str) -> None:
        """
        Set withdrawal PIN (4 digits).
        PIN is hashed using Django's password hasher.
        
        Args:
            pin: 4-digit PIN as string
        
        Raises:
            ValueError: If PIN is not exactly 4 digits
        """
        if not pin or len(pin) != 4 or not pin.isdigit():
            raise ValueError("PIN must be exactly 4 digits")
        
        self.pin_hash = make_password(pin)
    
    def check_pin(self, pin: str) -> bool:
        """
        Verify withdrawal PIN.
        
        Args:
            pin: 4-digit PIN to verify
        
        Returns:
            True if PIN matches, False otherwise
        """
        if not self.pin_hash:
            return False
        
        return check_password(pin, self.pin_hash)
    
    def has_pin(self) -> bool:
        """Check if PIN has been set"""
        return bool(self.pin_hash)


class DeltaCrownTransaction(models.Model):
    """
    Immutable coin ledger line. Positive amounts = credit, negative = debit.
    NEVER mutate amount after creation; use compensating transactions.
    
    Invariants enforced:
    - Immutability: Cannot modify amount/reason after save (raises exception)
    - Amount validation: Cannot be zero (DB CHECK constraint)
    - Idempotency: Unique constraint on idempotency_key WHERE NOT NULL
    - Balance check: Service layer checks wallet balance before debit (if not overdraft)
    """
    class Reason(models.TextChoices):
        PARTICIPATION = "participation", "Participation"
        TOP4 = "top4", "Top 4"
        RUNNER_UP = "runner_up", "Runner-up"
        WINNER = "winner", "Winner"
        ENTRY_FEE_DEBIT = "entry_fee_debit", "Entry fee (debit)"
        REFUND = "refund", "Refund"
        MANUAL_ADJUST = "manual_adjust", "Manual adjust"
        CORRECTION = "correction", "Correction"
        P2P_TRANSFER = "p2p_transfer", "P2P Transfer"  # For Step 3

    wallet = models.ForeignKey(
        DeltaCrownWallet,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    amount = models.IntegerField(help_text="Positive for credit, negative for debit")
    reason = models.CharField(max_length=32, choices=Reason.choices)

    # Context (optional but helps audit)
    # NOTE: Changed to IntegerField - tournament app moved to legacy (Nov 2, 2025)
    # Stores legacy tournament/registration/match IDs for historical reference
    tournament_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Legacy tournament ID (reference only)")
    registration_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Legacy registration ID (reference only)")
    match_id = models.IntegerField(null=True, blank=True, help_text="Legacy match ID (reference only)")

    note = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="coin_transactions_created"
    )

    # Idempotency guard: unique across the whole table (nullable). Services must set this.
    idempotency_key = models.CharField(max_length=64, blank=True, null=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "id")
        indexes = [
            models.Index(fields=["reason", "created_at"]),
            models.Index(fields=["wallet"]),
            models.Index(fields=["wallet", "created_at"]),  # Fast history queries
            models.Index(fields=["wallet", "id"]),  # Pagination optimization
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(amount=0),
                name="economy_transaction_amount_nonzero"
            ),
        ]
        verbose_name = "DeltaCrown Transaction"

    def __str__(self) -> str:
        return f"Tx[{self.id}] {self.amount} for {self.get_reason_display()} (wallet={self.wallet_id})"

    def save(self, *args, **kwargs):
        """
        Save transaction with immutability enforcement.
        
        Raises:
            InvalidAmount: If amount is zero
            ValueError: If attempting to modify existing transaction
        """
        is_create = self._state.adding
        
        # Validation: amount cannot be zero
        if self.amount == 0:
            raise InvalidAmount("Transaction amount cannot be zero")
        
        # Immutability: prevent modification of existing transactions
        if not is_create:
            # Load original from DB
            try:
                original = DeltaCrownTransaction.objects.get(pk=self.pk)
                
                # Check if critical fields changed
                if original.amount != self.amount:
                    raise ValueError(
                        f"Cannot modify transaction amount after creation. "
                        f"Original: {original.amount}, Attempted: {self.amount}. "
                        f"Use compensating transaction instead."
                    )
                if original.reason != self.reason:
                    raise ValueError(
                        f"Cannot modify transaction reason after creation. "
                        f"Original: {original.reason}, Attempted: {self.reason}."
                    )
            except DeltaCrownTransaction.DoesNotExist:
                # Transaction was deleted? Unusual but allow re-creation
                pass
        
        # Check balance before debit (service layer primary check, model layer backup)
        if is_create and self.amount < 0:
            # Only check if wallet exists and has allow_overdraft set
            if self.wallet_id:
                try:
                    wallet = self.wallet if hasattr(self, 'wallet') else DeltaCrownWallet.objects.get(pk=self.wallet_id)
                    if not wallet.allow_overdraft:
                        projected_balance = wallet.cached_balance + self.amount
                        if projected_balance < 0:
                            raise InsufficientFunds(
                                f"Insufficient balance: {wallet.cached_balance} available, "
                                f"{abs(self.amount)} required (would result in {projected_balance})"
                            )
                except DeltaCrownWallet.DoesNotExist:
                    # Wallet doesn't exist yet (unusual, but allow transaction to proceed)
                    pass
        
        super().save(*args, **kwargs)
        
        # Maintain cached balance on create only
        if is_create:
            try:
                self.wallet.recalc_and_save()
            except Exception:
                # Never block writes to ledger even if recalc fails – ops can rebuild later
                pass


class CoinPolicy(models.Model):
    """
    Per-tournament coin policy. Enabled by default.
    NOTE: Changed to IntegerField - tournament app moved to legacy (Nov 2, 2025)
    """
    tournament_id = models.IntegerField(unique=True, null=True, blank=True, db_index=True, help_text="Legacy tournament ID (reference only)")
    enabled = models.BooleanField(default=True)

    participation = models.PositiveIntegerField(default=5)
    top4 = models.PositiveIntegerField(default=25)
    runner_up = models.PositiveIntegerField(default=50)
    winner = models.PositiveIntegerField(default=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"CoinPolicy(tournament_id={self.tournament_id})"


class WithdrawalRequest(models.Model):
    """
    Bangladesh Payment Withdrawal Request.
    
    Workflow:
    1. User requests withdrawal (amount + payment method + PIN verification)
    2. Status changes to 'pending'
    3. Amount is locked in wallet.pending_balance
    4. Admin reviews and approves/rejects
    5. On approval: funds transferred, status='completed', pending_balance reduced
    6. On rejection: pending_balance returned to available balance
    
    Security:
    - Requires 4-digit PIN verification
    - Admin approval required
    - Audit trail with reviewed_by and timestamps
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
        
        Args:
            reviewed_by: User who approved the request
            admin_note: Admin notes about the approval
            completed_immediately: If True, mark as completed immediately
        
        Flow:
        1. Create debit transaction
        2. Reduce wallet pending_balance
        3. Update withdrawal status
        4. Set review metadata
        """
        from django.utils import timezone
        
        if self.status != self.Status.PENDING:
            raise ValueError(f"Cannot approve withdrawal with status '{self.status}'")
        
        # Create debit transaction
        with transaction.atomic():
            debit_transaction = DeltaCrownTransaction.objects.create(
                wallet=self.wallet,
                amount=-self.amount,
                reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                note=f"Withdrawal #{self.id} via {self.get_payment_method_display()}",
                created_by=reviewed_by,
                idempotency_key=f"withdrawal_{self.id}"
            )
            
            self.transaction = debit_transaction
            
            # Update wallet pending balance
            self.wallet.pending_balance = max(0, self.wallet.pending_balance - self.amount)
            self.wallet.last_withdrawal_at = timezone.now()
            self.wallet.save(update_fields=['pending_balance', 'last_withdrawal_at', 'updated_at'])
            
            # Update withdrawal status
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
        
        Flow:
        1. Return pending_balance to available balance
        2. Update withdrawal status
        3. Set review metadata
        """
        from django.utils import timezone
        
        if self.status != self.Status.PENDING:
            raise ValueError(f"Cannot reject withdrawal with status '{self.status}'")
        
        # Return pending balance
        with transaction.atomic():
            self.wallet.pending_balance = max(0, self.wallet.pending_balance - self.amount)
            self.wallet.save(update_fields=['pending_balance', 'updated_at'])
            
            # Update withdrawal status
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
        
        # Return pending balance
        with transaction.atomic():
            self.wallet.pending_balance = max(0, self.wallet.pending_balance - self.amount)
            self.wallet.save(update_fields=['pending_balance', 'updated_at'])
            
            self.status = self.Status.CANCELLED
            self.save()
