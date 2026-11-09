"""Single wallet-PIN policy: validation, verification with lockout, and persistence.

Policy
- New PINs (setup or change) are exactly 6 digits and not trivially weak.
- Verification accepts 4-6 digit input so an existing legacy 4-digit PIN keeps working; the
  stored hash alone decides. Existing PINs are never replaced without verifying the current one.
- A wallet "has a PIN" when ``pin_hash`` is set (``pin_enabled`` is only written, never trusted).
- 5 consecutive failures lock verification for 15 minutes, for every entry point that uses
  :func:`verify_pin_with_lockout`. Counters are updated under a row lock.
- PINs are hashed with Django's password hashers and never logged or returned.
"""
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.economy.models import DeltaCrownWallet

PIN_LENGTH = 6
LEGACY_PIN_LENGTH = 4
MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15

_WEAK = {str(d) * PIN_LENGTH for d in range(10)} | {'012345', '123456', '234567', '345678', '456789',
                                                   '543210', '654321', '765432', '876543', '987654'}


def wallet_has_pin(wallet) -> bool:
    return bool(wallet.pin_hash)


def validate_new_pin(pin: str) -> str:
    """Return the PIN if it satisfies the policy for a new PIN, else raise ValidationError."""
    pin = (pin or '').strip()
    if len(pin) != PIN_LENGTH or not pin.isdigit():
        raise ValidationError(f'PIN must be exactly {PIN_LENGTH} digits')
    if pin in _WEAK:
        raise ValidationError('PIN is too easy to guess. Please choose a different PIN.')
    return pin


def is_plausible_entry(pin: str) -> bool:
    """Shape check for an entered (existing) PIN: 4-6 digits (legacy 4-digit PINs stay valid)."""
    return LEGACY_PIN_LENGTH <= len(pin or '') <= PIN_LENGTH and (pin or '').isdigit()


def lock_minutes_remaining(wallet) -> int:
    if wallet.pin_locked_until and timezone.now() < wallet.pin_locked_until:
        return max(1, int((wallet.pin_locked_until - timezone.now()).total_seconds() // 60))
    return 0


@dataclass
class PinCheck:
    ok: bool
    locked: bool = False
    message: str = ''
    remaining_attempts: int = 0


def verify_pin_with_lockout(wallet_id: int, pin: str) -> PinCheck:
    """Check ``pin`` against the wallet's stored hash, enforcing and updating the lockout.

    Locks the wallet row for the duration, so concurrent guesses cannot exceed the limit.
    """
    with transaction.atomic():
        wallet = DeltaCrownWallet.objects.select_for_update().get(pk=wallet_id)
        if not wallet_has_pin(wallet):
            return PinCheck(False, message='PIN not configured. Please set up your PIN first.')
        minutes = lock_minutes_remaining(wallet)
        if minutes:
            return PinCheck(False, locked=True, message=f'PIN locked. Try again in {minutes} minutes.')
        if wallet.pin_locked_until:  # lock expired: start a fresh window
            wallet.pin_locked_until = None
            wallet.pin_failed_attempts = 0

        if is_plausible_entry(pin) and check_password(pin, wallet.pin_hash):
            wallet.pin_failed_attempts = 0
            wallet.save(update_fields=['pin_failed_attempts', 'pin_locked_until', 'updated_at'])
            return PinCheck(True)

        wallet.pin_failed_attempts += 1
        if wallet.pin_failed_attempts >= MAX_FAILED_ATTEMPTS:
            wallet.pin_locked_until = timezone.now() + timedelta(minutes=LOCK_MINUTES)
            wallet.save(update_fields=['pin_failed_attempts', 'pin_locked_until', 'updated_at'])
            return PinCheck(False, locked=True, message=f'Too many failed attempts. PIN locked for {LOCK_MINUTES} minutes.')
        wallet.save(update_fields=['pin_failed_attempts', 'pin_locked_until', 'updated_at'])
        left = MAX_FAILED_ATTEMPTS - wallet.pin_failed_attempts
        return PinCheck(False, message=f'Incorrect PIN. {left} attempts remaining before lockout.', remaining_attempts=left)


def store_new_pin(wallet_id: int, pin: str) -> None:
    """Persist an already-validated new PIN (hash only) and reset the lockout state."""
    with transaction.atomic():
        wallet = DeltaCrownWallet.objects.select_for_update().get(pk=wallet_id)
        wallet.pin_hash = make_password(pin)
        wallet.pin_enabled = True
        wallet.pin_failed_attempts = 0
        wallet.pin_locked_until = None
        wallet.save(update_fields=['pin_hash', 'pin_enabled', 'pin_failed_attempts', 'pin_locked_until', 'updated_at'])
