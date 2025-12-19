# apps/tournaments/services/payment_service.py
"""
DeltaCoin Payment Integration Service

Implements: GAP_ANALYSIS.md - Section 9 (DeltaCoin Payment Integration)
            REGISTRATION_IMPLEMENTATION_AUDIT.md - Section 6.3 (apps.economy Integration)

Provides:
- DeltaCoin balance check
- Automatic payment deduction from wallet
- Auto-verification (skip manual verification)
- Refund to wallet on cancellation
- Transaction tracking with idempotency
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Any, Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.economy import services as economy_services
from apps.economy.exceptions import InsufficientFunds, InvalidAmount
from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet
from apps.tournaments.models import Payment, Registration

User = get_user_model()


class PaymentService:
    """
    Service for processing tournament payments with DeltaCoin integration.
    
    Features:
    - One-click DeltaCoin payment with balance check
    - Automatic verification (no manual review needed)
    - Refund on cancellation with transaction tracking
    - Idempotent operations (prevent duplicate charges)
    """
    
    @staticmethod
    def get_wallet_balance(user) -> int:
        """
        Get user's DeltaCoin wallet balance.
        
        Args:
            user: User instance or user ID
        
        Returns:
            int: Current wallet balance (0 if wallet doesn't exist)
        
        Example:
            >>> balance = PaymentService.get_wallet_balance(request.user)
            >>> print(f"Your balance: {balance} DC")
        """
        try:
            profile = user.profile if hasattr(user, 'profile') else None
            if not profile:
                return 0
            
            return economy_services.get_balance(profile)
        except Exception:
            return 0
    
    @staticmethod
    @transaction.atomic
    def process_deltacoin_payment(
        registration_id: int,
        user,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process DeltaCoin payment for tournament registration.
        
        Workflow:
        1. Validate registration exists and needs payment
        2. Check user's wallet balance
        3. Deduct entry fee from wallet
        4. Create Payment record with status=VERIFIED (auto-approved)
        5. Update registration status to CONFIRMED
        
        Args:
            registration_id: ID of registration to pay for
            user: User making the payment
            idempotency_key: Optional key to prevent duplicate charges
        
        Returns:
            Dict containing:
                - payment_id: Created payment ID
                - transaction_id: DeltaCoin transaction ID
                - amount: Amount deducted
                - balance_after: User's balance after payment
                - registration_id: Registration ID
                - status: Payment status ('verified')
        
        Raises:
            Registration.DoesNotExist: Registration not found
            ValidationError: Invalid registration state or tournament config
            InsufficientFunds: Wallet balance too low
        
        Example:
            >>> result = PaymentService.process_deltacoin_payment(
            ...     registration_id=123,
            ...     user=request.user,
            ...     idempotency_key=f"reg-{registration_id}-deltacoin"
            ... )
            >>> print(f"Payment verified! Balance: {result['balance_after']} DC")
        """
        # Get registration
        try:
            registration = Registration.objects.select_related(
                'tournament', 'user'
            ).get(id=registration_id)
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration {registration_id} not found")
        
        # Validate registration belongs to user
        if registration.user != user:
            raise ValidationError("You can only pay for your own registration")
        
        # Validate registration status
        if registration.status not in [Registration.PENDING, Registration.PAYMENT_SUBMITTED]:
            raise ValidationError(
                f"Cannot process payment for registration with status '{registration.get_status_display()}'"
            )
        
        # Check if payment already exists
        if hasattr(registration, 'payment'):
            # Payment already processed
            payment = registration.payment
            if payment.status == Payment.VERIFIED:
                return {
                    'payment_id': payment.id,
                    'transaction_id': payment.transaction_id,
                    'amount': int(payment.amount),
                    'balance_after': PaymentService.get_wallet_balance(user),
                    'registration_id': registration.id,
                    'status': 'verified',
                    'message': 'Payment already processed',
                }
            elif payment.payment_method == Payment.DELTACOIN:
                raise ValidationError("DeltaCoin payment already submitted for this registration")
        
        # Validate tournament has entry fee
        tournament = registration.tournament
        if not tournament.has_entry_fee:
            raise ValidationError("This tournament does not require an entry fee")
        
        # Get entry fee amount
        entry_fee = int(tournament.entry_fee_amount)  # Convert Decimal to int for DeltaCoin
        
        # Get user profile
        profile = user.profile if hasattr(user, 'profile') else None
        if not profile:
            raise ValidationError("User profile not found. Cannot process DeltaCoin payment.")
        
        # Build idempotency key if not provided
        if not idempotency_key:
            idempotency_key = f"tournament-reg-{registration_id}-deltacoin-{user.id}"
        
        # Deduct DeltaCoin from wallet (this will raise InsufficientFunds if balance too low)
        try:
            debit_result = economy_services.debit(
                profile=profile,
                amount=entry_fee,
                reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT,
                idempotency_key=idempotency_key,
                meta={
                    'tournament_id': tournament.id,
                    'tournament_slug': tournament.slug,
                    'registration_id': registration.id,
                    'description': f"Entry fee: {tournament.name}",
                }
            )
        except InsufficientFunds as e:
            # Re-raise with user-friendly message
            balance = PaymentService.get_wallet_balance(user)
            raise ValidationError(
                f"Insufficient DeltaCoin balance. You have {balance} DC, but need {entry_fee} DC. "
                f"Please purchase more DeltaCoin or use a different payment method."
            ) from e
        except InvalidAmount as e:
            raise ValidationError(f"Invalid payment amount: {e}") from e
        
        # Create Payment record (auto-verified for DeltaCoin)
        payment = Payment.objects.create(
            registration=registration,
            payment_method=Payment.DELTACOIN,
            amount=Decimal(entry_fee),
            transaction_id=str(debit_result['transaction_id']),
            status=Payment.VERIFIED,  # Auto-verify DeltaCoin payments
            verified_at=timezone.now(),
            verified_by=user,  # Mark as verified by the payer (system verification)
            notes={
                'auto_verified': True,
                'verification_method': 'deltacoin_automatic',
                'wallet_transaction_id': debit_result['transaction_id'],
                'balance_after': debit_result['balance_after'],
                'idempotency_key': idempotency_key,
            }
        )
        
        # Update registration status to CONFIRMED
        registration.status = Registration.CONFIRMED
        registration.save(update_fields=['status', 'updated_at'])
        
        # Return success result
        return {
            'payment_id': payment.id,
            'transaction_id': payment.transaction_id,
            'amount': entry_fee,
            'balance_after': debit_result['balance_after'],
            'registration_id': registration.id,
            'status': 'verified',
            'message': f'Payment successful! {entry_fee} DC deducted from your wallet.',
        }
    
    @staticmethod
    @transaction.atomic
    def refund_deltacoin_payment(
        registration_id: int,
        refund_reason: str = '',
        refunded_by = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refund DeltaCoin payment back to user's wallet.
        
        Used when:
        - Tournament is cancelled
        - Registration is rejected by organizer
        - User cancels registration before tournament starts
        
        Workflow:
        1. Validate registration has DeltaCoin payment
        2. Check payment is verified (can't refund pending payments)
        3. Credit DeltaCoin back to user's wallet
        4. Update payment status to REFUNDED
        5. Update registration status to CANCELLED
        
        Args:
            registration_id: ID of registration to refund
            refund_reason: Reason for refund (for audit trail)
            refunded_by: User performing the refund (organizer/admin)
            idempotency_key: Optional key to prevent duplicate refunds
        
        Returns:
            Dict containing:
                - refund_id: Payment ID
                - transaction_id: DeltaCoin credit transaction ID
                - amount: Amount refunded
                - balance_after: User's balance after refund
                - registration_id: Registration ID
                - status: Payment status ('refunded')
        
        Raises:
            Registration.DoesNotExist: Registration not found
            ValidationError: Invalid state (no payment, already refunded, etc.)
        
        Example:
            >>> result = PaymentService.refund_deltacoin_payment(
            ...     registration_id=123,
            ...     refund_reason="Tournament cancelled",
            ...     refunded_by=organizer_user
            ... )
            >>> print(f"Refund successful! {result['amount']} DC returned to wallet.")
        """
        # Get registration with payment
        try:
            registration = Registration.objects.select_related(
                'tournament', 'user', 'payment'
            ).get(id=registration_id)
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration {registration_id} not found")
        
        # Check payment exists
        if not hasattr(registration, 'payment'):
            raise ValidationError("No payment found for this registration")
        
        payment = registration.payment
        
        # Validate payment method is DeltaCoin
        if payment.payment_method != Payment.DELTACOIN:
            raise ValidationError(
                f"Cannot refund DeltaCoin for payment method '{payment.get_payment_method_display()}'. "
                f"Only DeltaCoin payments can be auto-refunded."
            )
        
        # Check payment status
        if payment.status == Payment.REFUNDED:
            # Already refunded - return existing refund info
            return {
                'refund_id': payment.id,
                'transaction_id': payment.notes.get('refund_transaction_id', payment.transaction_id),
                'amount': int(payment.amount),
                'balance_after': PaymentService.get_wallet_balance(registration.user),
                'registration_id': registration.id,
                'status': 'refunded',
                'message': 'Payment already refunded',
            }
        
        if payment.status != Payment.VERIFIED:
            raise ValidationError(
                f"Cannot refund payment with status '{payment.get_status_display()}'. "
                f"Only verified payments can be refunded."
            )
        
        # Get user profile
        user = registration.user
        profile = user.profile if hasattr(user, 'profile') else None
        if not profile:
            raise ValidationError("User profile not found. Cannot process refund.")
        
        # Build idempotency key if not provided
        if not idempotency_key:
            idempotency_key = f"tournament-refund-{registration_id}-deltacoin-{user.id}"
        
        # Credit DeltaCoin back to wallet
        refund_amount = int(payment.amount)
        
        try:
            credit_result = economy_services.credit(
                profile=profile,
                amount=refund_amount,
                reason=DeltaCrownTransaction.Reason.REFUND,
                idempotency_key=idempotency_key,
                meta={
                    'tournament_id': registration.tournament.id,
                    'tournament_slug': registration.tournament.slug,
                    'registration_id': registration.id,
                    'original_transaction_id': payment.transaction_id,
                    'refund_reason': refund_reason,
                    'description': f"Refund: {registration.tournament.name}",
                }
            )
        except Exception as e:
            raise ValidationError(f"Failed to process refund: {e}") from e
        
        # Update payment record
        payment.status = Payment.REFUNDED
        payment.refunded_at = timezone.now()
        payment.refunded_by = refunded_by
        
        # Store refund transaction details in notes
        if not isinstance(payment.notes, dict):
            payment.notes = {}
        
        payment.notes.update({
            'refunded': True,
            'refund_transaction_id': credit_result['transaction_id'],
            'refund_amount': refund_amount,
            'refund_reason': refund_reason,
            'refund_balance_after': credit_result['balance_after'],
            'refund_timestamp': timezone.now().isoformat(),
            'refund_idempotency_key': idempotency_key,
        })
        
        payment.save(update_fields=['status', 'refunded_at', 'refunded_by', 'notes', 'updated_at'])
        
        # Update registration status to CANCELLED
        registration.status = Registration.CANCELLED
        registration.save(update_fields=['status', 'updated_at'])
        
        # Return success result
        return {
            'refund_id': payment.id,
            'transaction_id': credit_result['transaction_id'],
            'amount': refund_amount,
            'balance_after': credit_result['balance_after'],
            'registration_id': registration.id,
            'status': 'refunded',
            'message': f'Refund successful! {refund_amount} DC credited back to wallet.',
        }
    
    @staticmethod
    @transaction.atomic
    def verify_payment(payment, verified_by):
        """
        Verify a payment (organizer action).
        
        Phase 0 Refactor: Extracted from organizer.py view.
        Preserves exact behavior - sets status to 'verified' and records verifier.
        
        Args:
            payment: Payment instance to verify
            verified_by: User performing the verification
        
        Returns:
            Payment: The updated payment instance
        """
        payment.status = 'verified'
        payment.verified_by = verified_by
        payment.verified_at = timezone.now()
        payment.save()
        return payment
    
    @staticmethod
    @transaction.atomic
    def reject_payment(payment, rejected_by):
        """
        Reject a payment (organizer action).
        
        Phase 0 Refactor: Extracted from organizer.py view.
        Phase 0 Patch: Fixed to match Payment model semantics - verified_by/verified_at
        track BOTH verifications and rejections per model help text.
        
        Note: Original view only set status='rejected', but Payment model fields
        verified_by/verified_at have help text: "Admin who verified/rejected the payment"
        and "When payment was verified/rejected". This patch aligns implementation
        with model design intent.
        
        Args:
            payment: Payment instance to reject
            rejected_by: User performing the rejection (stored in verified_by field)
        
        Returns:
            Payment: The updated payment instance
        """
        payment.status = 'rejected'
        payment.verified_by = rejected_by
        payment.verified_at = timezone.now()
        payment.save()
        return payment
    
    @staticmethod
    def can_use_deltacoin(user, entry_fee: int) -> Dict[str, Any]:
        """
        Check if user can afford to pay with DeltaCoin.
        
        Args:
            user: User to check balance for
            entry_fee: Required entry fee amount
        
        Returns:
            Dict containing:
                - can_afford: bool - True if balance >= entry_fee
                - balance: int - Current wallet balance
                - required: int - Required entry fee
                - shortfall: int - How much more needed (0 if can afford)
        
        Example:
            >>> check = PaymentService.can_use_deltacoin(request.user, 500)
            >>> if check['can_afford']:
            ...     print("You can pay with DeltaCoin!")
            >>> else:
            ...     print(f"Need {check['shortfall']} more DC")
        """
        balance = PaymentService.get_wallet_balance(user)
        can_afford = balance >= entry_fee
        shortfall = max(0, entry_fee - balance)
        
        return {
            'can_afford': can_afford,
            'balance': balance,
            'required': entry_fee,
            'shortfall': shortfall,
        }
    
    # =========================
    # Phase 0: Organizer Actions
    # =========================
    
    @staticmethod
    @transaction.atomic
    def organizer_bulk_verify(payment_ids: list, tournament, verified_by) -> int:
        """
        Bulk verify payments (organizer action).
        
        Phase 0 Refactor: Extracted from organizer.py bulk_verify_payments view.
        Preserves exact behavior - updates multiple payments to verified status.
        
        Args:
            payment_ids: List of payment IDs to verify
            tournament: Tournament instance (for filtering)
            verified_by: User instance (organizer)
        
        Returns:
            int: Number of payments updated
        """
        updated = Payment.objects.filter(
            id__in=payment_ids,
            registration__tournament=tournament,
            status='submitted'
        ).update(
            status='verified',
            verified_by=verified_by,
            verified_at=timezone.now()
        )
        
        return updated
    
    @staticmethod
    @transaction.atomic
    def organizer_process_refund(payment, refund_amount, reason: str, refund_method: str, processed_by_username: str):
        """
        Process refund for a payment (organizer action).
        
        Phase 0 Refactor: Extracted from organizer.py process_refund view.
        Preserves exact behavior - stores refund metadata, updates status.
        
        Args:
            payment: Payment instance
            refund_amount: Decimal amount to refund
            reason: Refund reason
            refund_method: Refund method ('manual', etc.)
            processed_by_username: Username of organizer
        
        Returns:
            Updated Payment instance
        
        Raises:
            ValidationError: If amount invalid or reason missing
        """
        from django.core.exceptions import ValidationError
        from decimal import Decimal
        
        # Convert to Decimal if needed
        if not isinstance(refund_amount, Decimal):
            refund_amount = Decimal(str(refund_amount))
        
        # Validate
        if refund_amount <= 0 or refund_amount > payment.amount:
            raise ValidationError('Invalid refund amount')
        
        if not reason or not reason.strip():
            raise ValidationError('Refund reason required')
        
        # Store refund info in payment metadata (JSONB)
        if not hasattr(payment, 'metadata') or payment.metadata is None:
            payment.metadata = {}
        
        payment.metadata['refund'] = {
            'amount': str(refund_amount),
            'reason': reason,
            'method': refund_method,
            'processed_at': timezone.now().isoformat(),
            'processed_by': processed_by_username,
        }
        payment.status = 'refunded'
        payment.save()
        
        return payment
