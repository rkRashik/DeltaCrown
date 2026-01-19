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
    
    # Withdrawal Security (UP PHASE 7.2)
    pin_hash = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Hashed 6-digit PIN for withdrawal verification"
    )
    pin_enabled = models.BooleanField(
        default=False,
        help_text="Whether PIN protection is enabled"
    )
    pin_failed_attempts = models.IntegerField(
        default=0,
        help_text="Number of consecutive failed PIN attempts"
    )
    pin_locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="PIN lockout expiry timestamp (15 min after 5 failed attempts)"
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


class TopUpRequest(models.Model):
    """
    Bangladesh Payment Top-Up Request.
    
    Workflow:
    1. User submits top-up request (amount + payment method + payment proof)
    2. Status = 'pending'
    3. Admin reviews payment proof
    4. On approval: DeltaCrownTransaction created (credit), status='completed'
    5. On rejection: status='rejected' with reason
    
    Security:
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


# =====================================================================
# PHASE 3A: INVENTORY SYSTEM
# =====================================================================

class InventoryItem(models.Model):
    """
    Master data for inventory items (cosmetics, cases, tokens, collectibles, badges).
    Immutable after creation (slug cannot change).
    
    Phase 3A Foundation - No marketplace yet.
    """
    class ItemType(models.TextChoices):
        COSMETIC = 'COSMETIC', 'Cosmetic Skin'
        CASE = 'CASE', 'Loot Case'
        TOKEN = 'TOKEN', 'Special Token'
        COLLECTIBLE = 'COLLECTIBLE', 'Collectible Item'
        BADGE = 'BADGE', 'Achievement Badge'
    
    class Rarity(models.TextChoices):
        COMMON = 'COMMON', 'Common'
        RARE = 'RARE', 'Rare'
        EPIC = 'EPIC', 'Epic'
        LEGENDARY = 'LEGENDARY', 'Legendary'
    
    # Core Fields
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text='Unique immutable identifier (e.g., awp-dragon-lore)'
    )
    name = models.CharField(
        max_length=200,
        help_text='Display name (e.g., AWP | Dragon Lore)'
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text='Item description for users'
    )
    
    # Classification
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        db_index=True
    )
    rarity = models.CharField(
        max_length=20,
        choices=Rarity.choices,
        db_index=True
    )
    
    # Trade & Gift Controls
    tradable = models.BooleanField(
        default=False,
        help_text='Can this item be traded between users?'
    )
    giftable = models.BooleanField(
        default=False,
        help_text='Can this item be gifted to other users?'
    )
    
    # Visuals
    icon = models.ImageField(
        upload_to='inventory/items/',
        blank=True,
        null=True,
        help_text='Item icon/image'
    )
    icon_url = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text='External icon URL (if not using ImageField)'
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional item data (game-specific, stats, etc.)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'economy_inventory_item'
        ordering = ['name']
        indexes = [
            models.Index(fields=['item_type', 'rarity']),
            models.Index(fields=['slug']),
        ]
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'
    
    def __str__(self):
        return f"{self.name} ({self.get_rarity_display()})"
    
    @property
    def icon_display_url(self):
        """Get icon URL (ImageField or external URL)"""
        if self.icon:
            return self.icon.url
        return self.icon_url or ''


class UserInventoryItem(models.Model):
    """
    User ownership of inventory items.
    Tracks quantity, acquisition method, and locked status.
    
    Constraints:
    - Unique(profile, item) - one row per user per item
    - quantity >= 0 enforced via CHECK constraint
    - locked items cannot be traded/gifted (enforced in views)
    """
    class AcquiredFrom(models.TextChoices):
        PURCHASE = 'PURCHASE', 'Purchase'
        REWARD = 'REWARD', 'Reward'
        GIFT = 'GIFT', 'Gift'
        TRADE = 'TRADE', 'Trade'
        ADMIN = 'ADMIN', 'Admin Grant'
    
    # Ownership
    profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='owned_inventory_items'
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='owned_by'
    )
    
    # Quantity & Status
    quantity = models.PositiveIntegerField(
        default=1,
        help_text='How many of this item the user owns'
    )
    locked = models.BooleanField(
        default=False,
        help_text='Locked items cannot be traded/gifted'
    )
    
    # Acquisition Context
    acquired_from = models.CharField(
        max_length=20,
        choices=AcquiredFrom.choices,
        db_index=True
    )
    acquired_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'economy_user_inventory_item'
        unique_together = [['profile', 'item']]
        ordering = ['-acquired_at']
        indexes = [
            models.Index(fields=['profile', '-acquired_at']),
            models.Index(fields=['acquired_from']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name='economy_user_inventory_quantity_nonnegative'
            )
        ]
        verbose_name = 'User Inventory Item'
        verbose_name_plural = 'User Inventory Items'
    
    def __str__(self):
        username = getattr(self.profile.user, 'username', 'Unknown')
        return f"{username} owns {self.quantity}x {self.item.name}"
    
    def can_trade(self) -> bool:
        """Check if this inventory item can be traded"""
        return (
            not self.locked and
            self.item.tradable and
            self.quantity > 0
        )
    
    def can_gift(self) -> bool:
        """Check if this inventory item can be gifted"""
        return (
            not self.locked and
            self.item.giftable and
            self.quantity > 0
        )


class GiftRequest(models.Model):
    """
    Gift request from one user to another.
    Phase 3A Foundation - Request-based flow only, no UI yet.
    
    Workflow:
    1. Sender creates gift request
    2. Receiver accepts/rejects
    3. On accept: atomic transfer
    4. On reject/cancel: no action
    
    Rules:
    - Item must be giftable
    - Sender must own sufficient quantity
    - Cannot gift locked items
    - Sender ≠ Receiver
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELED = 'CANCELED', 'Canceled'
    
    # Parties
    sender_profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='gifts_sent'
    )
    receiver_profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='gifts_received'
    )
    
    # Item Details
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='gift_requests'
    )
    quantity = models.PositiveIntegerField(default=1)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Optional Message
    message = models.TextField(
        blank=True,
        default='',
        max_length=500,
        help_text='Optional message from sender'
    )
    
    class Meta:
        db_table = 'economy_gift_request'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender_profile', '-created_at']),
            models.Index(fields=['receiver_profile', 'status', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
        verbose_name = 'Gift Request'
        verbose_name_plural = 'Gift Requests'
    
    def __str__(self):
        sender_name = getattr(self.sender_profile.user, 'username', 'Unknown')
        receiver_name = getattr(self.receiver_profile.user, 'username', 'Unknown')
        return f"Gift: {sender_name} → {receiver_name} ({self.quantity}x {self.item.name}) - {self.status}"
    
    def clean(self):
        """Validation rules"""
        from django.core.exceptions import ValidationError
        
        # Rule 1: Cannot gift to self
        if self.sender_profile_id == self.receiver_profile_id:
            raise ValidationError("Cannot gift items to yourself")
        
        # Rule 2: Item must be giftable
        if not self.item.giftable:
            raise ValidationError(f"Item '{self.item.name}' is not giftable")
        
        # Rule 3: Quantity must be positive
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")
        
        # Rule 4: Sender must own sufficient quantity (check if not new)
        if self.pk is None:  # New gift request
            try:
                sender_inventory = UserInventoryItem.objects.get(
                    profile=self.sender_profile,
                    item=self.item
                )
                
                # Check locked status
                if sender_inventory.locked:
                    raise ValidationError("Cannot gift locked items")
                
                # Check quantity
                if sender_inventory.quantity < self.quantity:
                    raise ValidationError(
                        f"Insufficient quantity. Have: {sender_inventory.quantity}, "
                        f"Requested: {self.quantity}"
                    )
            except UserInventoryItem.DoesNotExist:
                raise ValidationError(f"You do not own '{self.item.name}'")


class TradeRequest(models.Model):
    """
    Trade request between two users (1-sided offers for Phase 3A).
    Phase 3A Foundation - Simple 1-for-nothing offers, no complex barter yet.
    
    Workflow:
    1. Initiator creates trade request (offers item, optionally requests item)
    2. Target accepts/rejects
    3. On accept: atomic swap
    4. On reject/cancel: no action
    
    Rules:
    - Only tradable items allowed
    - Cannot trade locked items
    - Initiator ≠ Target
    - Atomic transfer on acceptance
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELED = 'CANCELED', 'Canceled'
    
    # Parties
    initiator_profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='trades_initiated'
    )
    target_profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='trades_received'
    )
    
    # Offered Item (what initiator gives)
    offered_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='trade_offers'
    )
    offered_quantity = models.PositiveIntegerField(default=1)
    
    # Requested Item (what initiator wants - nullable for simple gifts)
    requested_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='trade_requests',
        null=True,
        blank=True,
        help_text='Optional: What initiator wants in return'
    )
    requested_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Quantity of requested item'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Optional Message
    message = models.TextField(
        blank=True,
        default='',
        max_length=500,
        help_text='Optional message from initiator'
    )
    
    class Meta:
        db_table = 'economy_trade_request'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['initiator_profile', '-created_at']),
            models.Index(fields=['target_profile', 'status', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
        verbose_name = 'Trade Request'
        verbose_name_plural = 'Trade Requests'
    
    def __str__(self):
        initiator_name = getattr(self.initiator_profile.user, 'username', 'Unknown')
        target_name = getattr(self.target_profile.user, 'username', 'Unknown')
        request_part = f" for {self.requested_quantity}x {self.requested_item.name}" if self.requested_item else ""
        return f"Trade: {initiator_name} → {target_name} ({self.offered_quantity}x {self.offered_item.name}{request_part}) - {self.status}"
    
    def clean(self):
        """Validation rules"""
        from django.core.exceptions import ValidationError
        
        # Rule 1: Cannot trade with self
        if self.initiator_profile_id == self.target_profile_id:
            raise ValidationError("Cannot trade with yourself")
        
        # Rule 2: Offered item must be tradable
        if not self.offered_item.tradable:
            raise ValidationError(f"Item '{self.offered_item.name}' is not tradable")
        
        # Rule 3: Requested item must be tradable (if specified)
        if self.requested_item and not self.requested_item.tradable:
            raise ValidationError(f"Requested item '{self.requested_item.name}' is not tradable")
        
        # Rule 4: Quantities must be positive
        if self.offered_quantity <= 0:
            raise ValidationError("Offered quantity must be greater than 0")
        
        if self.requested_item and (self.requested_quantity is None or self.requested_quantity <= 0):
            raise ValidationError("Requested quantity must be greater than 0 when requesting an item")
        
        # Rule 5: Initiator must own sufficient offered quantity
        if self.pk is None:  # New trade request
            try:
                initiator_inventory = UserInventoryItem.objects.get(
                    profile=self.initiator_profile,
                    item=self.offered_item
                )
                
                # Check locked status
                if initiator_inventory.locked:
                    raise ValidationError("Cannot trade locked items")
                
                # Check quantity
                if initiator_inventory.quantity < self.offered_quantity:
                    raise ValidationError(
                        f"Insufficient quantity. Have: {initiator_inventory.quantity}, "
                        f"Offered: {self.offered_quantity}"
                    )
            except UserInventoryItem.DoesNotExist:
                raise ValidationError(f"You do not own '{self.offered_item.name}'")
            
            # Rule 6: Target must own sufficient requested quantity (if requesting)
            if self.requested_item:
                try:
                    target_inventory = UserInventoryItem.objects.get(
                        profile=self.target_profile,
                        item=self.requested_item
                    )
                    
                    # Check locked status
                    if target_inventory.locked:
                        raise ValidationError("Target's item is locked and cannot be traded")
                    
                    # Check quantity
                    if target_inventory.quantity < self.requested_quantity:
                        raise ValidationError(
                            f"Target has insufficient quantity. "
                            f"They have: {target_inventory.quantity}, "
                            f"You requested: {self.requested_quantity}"
                        )
                except UserInventoryItem.DoesNotExist:
                    raise ValidationError(
                        f"Target does not own '{self.requested_item.name}'"
                    )


class WalletPINOTP(models.Model):
    """
    UP PHASE 7.7: One-Time Password for PIN setup/change security.
    
    Flow:
    1. User requests OTP (6-digit code sent to email)
    2. OTP valid for 10 minutes
    3. Max 5 verification attempts before lockout
    4. OTP invalidated after successful verification
    
    Security:
    - OTP code is hashed before storage
    - Automatic expiry after 10 minutes
    - Attempt-based lockout
    - Audit trail with created/used timestamps
    """
    
    class Purpose(models.TextChoices):
        PIN_SETUP = 'pin_setup', 'PIN Setup (First Time)'
        PIN_CHANGE = 'pin_change', 'PIN Change'
    
    wallet = models.ForeignKey(
        DeltaCrownWallet,
        on_delete=models.CASCADE,
        related_name='pin_otps'
    )
    code_hash = models.CharField(
        max_length=255,
        help_text='Hashed OTP code (6 digits)'
    )
    purpose = models.CharField(
        max_length=20,
        choices=Purpose.choices,
        default=Purpose.PIN_SETUP
    )
    
    # Security
    attempt_count = models.IntegerField(
        default=0,
        help_text='Number of verification attempts'
    )
    max_attempts = models.IntegerField(
        default=5,
        help_text='Maximum allowed attempts'
    )
    is_used = models.BooleanField(
        default=False,
        help_text='Whether OTP has been successfully verified and used'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text='OTP expiry time (10 minutes from creation)'
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When OTP was successfully used'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['expires_at', 'is_used']),
        ]
        verbose_name = 'Wallet PIN OTP'
        verbose_name_plural = 'Wallet PIN OTPs'
    
    def __str__(self):
        return f"OTP for {self.wallet.profile.user.username} - {self.purpose} ({'used' if self.is_used else 'pending'})"
    
    def is_valid(self):
        """Check if OTP is still valid (not expired, not used, attempts remaining)"""
        from django.utils import timezone
        return (
            not self.is_used
            and self.expires_at > timezone.now()
            and self.attempt_count < self.max_attempts
        )
    
    def verify_code(self, plain_code):
        """Verify OTP code (increments attempt counter)"""
        from django.contrib.auth.hashers import check_password
        self.attempt_count += 1
        self.save()
        return check_password(plain_code, self.code_hash)
    
    def mark_used(self):
        """Mark OTP as successfully used"""
        from django.utils import timezone
        self.is_used = True
        self.used_at = timezone.now()
        self.save()

