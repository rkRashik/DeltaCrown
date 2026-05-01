# apps/economy/models/wallet.py
from __future__ import annotations

from django.db import models, transaction
from django.db.models import Sum
from django.contrib.auth.hashers import make_password, check_password

from apps.common.managers import SoftDeleteManager
from apps.common.models import SoftDeleteModel


class DeltaCrownWallet(SoftDeleteModel):
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
        null=True,
        blank=True,
        help_text="Owning user profile. Null only for the Master Treasury system wallet.",
    )
    is_treasury = models.BooleanField(
        default=False,
        help_text="True for the single Master Treasury system wallet. "
                  "Use economy.services.get_master_treasury() to obtain it.",
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

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        indexes = [
            models.Index(fields=["profile"]),
        ]
        constraints = [
            models.UniqueConstraint(
                condition=models.Q(is_treasury=True),
                fields=["is_treasury"],
                name="economy_single_master_treasury",
            ),
        ]
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"

    def __str__(self) -> str:
        if self.is_treasury:
            return f"MasterTreasury: {self.cached_balance} DC"
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
