# apps/economy/models/security.py
from __future__ import annotations

from django.db import models

from apps.common.models import SoftDeleteModel
from .wallet import DeltaCrownWallet


class WalletPINOTP(SoftDeleteModel):
    """
    UP PHASE 7.7: One-Time Password for PIN setup/change security.
    
    Flow:
    1. User requests OTP (6-digit code sent to email)
    2. OTP valid for 10 minutes
    3. Max 5 verification attempts before lockout
    4. OTP invalidated after successful verification
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
