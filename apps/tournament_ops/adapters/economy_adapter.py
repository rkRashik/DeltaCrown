"""
Economy service adapter for cross-domain payment/balance operations.

Provides TournamentOps with access to DeltaCoin economy operations (payments,
refunds, balance queries) without direct imports from apps.economy.models.

Wired to apps.economy.services (credit/debit/get_balance) in Phase 1.
"""

from typing import Protocol, runtime_checkable, Dict, Any, Optional
import logging

from .base import BaseAdapter

logger = logging.getLogger(__name__)


@runtime_checkable
class EconomyAdapterProtocol(Protocol):
    """
    Protocol defining the interface for economy/payment operations.
    
    All methods must return DTOs (not ORM models) once DTOs are implemented.
    
    TODO: Replace Dict[str, Any] with PaymentDTO, BalanceDTO, etc.
          once tournament_ops/dtos/ is implemented (Epic 1.3).
    """
    
    def charge_registration_fee(
        self,
        user_id: int,
        tournament_id: int,
        amount: int,
        currency: str = "DC"
    ) -> Dict[str, Any]:
        """
        Charge registration fee to user's DeltaCoin account.
        
        Args:
            user_id: User identifier
            tournament_id: Tournament identifier (for transaction tracking)
            amount: Amount to charge (in smallest currency unit, e.g., 1000 DC)
            currency: Currency code (default: "DC" for DeltaCoin)
            
        Returns:
            Dict containing payment transaction details (transaction_id, status, etc.)
            
        Raises:
            InsufficientFundsError: If user has insufficient balance
            PaymentFailedError: If payment processing fails
            
        TODO: Return PaymentDTO instead of dict.
        """
        ...
    
    def refund_registration_fee(
        self,
        user_id: int,
        tournament_id: int,
        amount: int,
        currency: str = "DC",
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refund registration fee to user's DeltaCoin account.
        
        Args:
            user_id: User identifier
            tournament_id: Tournament identifier (for transaction tracking)
            amount: Amount to refund (in smallest currency unit)
            currency: Currency code (default: "DC" for DeltaCoin)
            reason: Optional refund reason (e.g., "Tournament cancelled")
            
        Returns:
            Dict containing refund transaction details
            
        Raises:
            RefundFailedError: If refund processing fails
            
        TODO: Return RefundDTO instead of dict.
        """
        ...
    
    def get_balance(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's current DeltaCoin balance.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict containing balance data (amount, currency, etc.)
            
        TODO: Return BalanceDTO instead of dict.
        """
        ...
    
    def verify_payment(self, transaction_id: str) -> bool:
        """
        Verify that a payment transaction completed successfully.
        
        Args:
            transaction_id: Payment transaction identifier
            
        Returns:
            bool: True if payment verified, False otherwise
        """
        ...


class EconomyAdapter(BaseAdapter):
    """
    Concrete economy adapter implementation.
    
    Wired to apps.economy.services for real DeltaCoin operations:
    - charge_registration_fee() → economy.services.debit()
    - refund_registration_fee() → economy.services.credit()
    - get_balance() → economy.services.get_balance()
    - verify_payment() → economy.models.DeltaCrownTransaction lookup
    """
    
    def _resolve_profile(self, user_id: int):
        """Resolve user_id → UserProfile for economy service calls."""
        from apps.user_profile.models import UserProfile
        return UserProfile.objects.get(user_id=user_id)
    
    def charge_registration_fee(
        self,
        user_id: int,
        tournament_id: int,
        amount: int,
        currency: str = "DC"
    ) -> Dict[str, Any]:
        """
        Charge registration fee via economy.services.debit().
        
        Args:
            user_id: User to charge
            tournament_id: Tournament context
            amount: DeltaCoin amount to charge
            currency: Currency code (default: DC)
        
        Returns:
            Dict with transaction_id, user_id, amount, currency, status, metadata
        
        Raises:
            PaymentFailedError: If payment fails (insufficient funds, invalid amount, etc.)
        """
        from apps.tournament_ops.exceptions import PaymentFailedError
        
        if amount <= 0:
            raise PaymentFailedError("Invalid amount: must be positive")
        
        try:
            from apps.economy.services import debit
            
            profile = self._resolve_profile(user_id)
            result = debit(
                profile,
                amount,
                reason=f"Tournament registration fee (tournament #{tournament_id})",
                idempotency_key=f"reg-fee-{user_id}-{tournament_id}",
                meta={'tournament_id': tournament_id, 'type': 'registration_fee'},
            )
            
            return {
                'transaction_id': str(result.get('transaction_id', '')),
                'user_id': user_id,
                'amount': amount,
                'currency': currency,
                'status': 'completed',
                'balance_after': result.get('balance_after', 0),
                'metadata': {
                    'tournament_id': tournament_id,
                    'type': 'registration_fee',
                    'idempotency_key': result.get('idempotency_key'),
                },
            }
        except Exception as e:
            err_str = str(e).lower()
            if 'insufficient' in err_str:
                raise PaymentFailedError(f"Insufficient DeltaCoin balance for {amount} DC fee")
            if 'idempotency' in err_str:
                raise PaymentFailedError(f"Duplicate charge attempt for tournament #{tournament_id}")
            logger.error("EconomyAdapter.charge_registration_fee failed: %s", e)
            raise PaymentFailedError(f"Payment failed: {e}")
    
    def refund_registration_fee(
        self,
        user_id: int,
        tournament_id: int,
        amount: int,
        currency: str = "DC",
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refund registration fee via economy.services.credit().
        
        Args:
            user_id: User to refund
            tournament_id: Tournament context
            amount: DeltaCoin amount to refund
            currency: Currency code (default: DC)
            reason: Optional refund reason
        
        Returns:
            Dict with transaction details
        
        Raises:
            PaymentFailedError: If refund fails
        """
        from apps.tournament_ops.exceptions import PaymentFailedError
        
        if amount <= 0:
            raise PaymentFailedError("Invalid refund amount: must be positive")
        
        reason_str = reason or "Tournament cancellation"
        
        try:
            from apps.economy.services import credit
            
            profile = self._resolve_profile(user_id)
            result = credit(
                profile,
                amount,
                reason=f"Refund: {reason_str} (tournament #{tournament_id})",
                idempotency_key=f"refund-{user_id}-{tournament_id}",
                meta={'tournament_id': tournament_id, 'type': 'refund', 'reason': reason_str},
            )
            
            return {
                'transaction_id': str(result.get('transaction_id', '')),
                'user_id': user_id,
                'amount': amount,
                'currency': currency,
                'status': 'refunded',
                'balance_after': result.get('balance_after', 0),
                'metadata': {
                    'tournament_id': tournament_id,
                    'type': 'refund',
                    'reason': reason_str,
                    'idempotency_key': result.get('idempotency_key'),
                },
            }
        except Exception as e:
            logger.error("EconomyAdapter.refund_registration_fee failed: %s", e)
            raise PaymentFailedError(f"Refund failed: {e}")
    
    def get_balance(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's current DeltaCoin balance via economy.services.get_balance().
        
        Args:
            user_id: User identifier
        
        Returns:
            Dict with user_id, balance, currency, frozen_balance
        """
        try:
            from apps.economy.services import get_balance
            
            profile = self._resolve_profile(user_id)
            balance = get_balance(profile)
            
            return {
                'user_id': user_id,
                'balance': balance,
                'currency': 'DC',
                'frozen_balance': 0,  # TODO: Wire holds when available
            }
        except Exception as e:
            logger.warning("EconomyAdapter.get_balance failed for user %d: %s", user_id, e)
            return {
                'user_id': user_id,
                'balance': 0,
                'currency': 'DC',
                'frozen_balance': 0,
            }
    
    def verify_payment(self, transaction_id: str) -> bool:
        """
        Verify payment by checking DeltaCrownTransaction exists.
        
        Args:
            transaction_id: Transaction ID (integer stored as string)
        
        Returns:
            bool: True if transaction exists and is valid
        """
        try:
            from apps.economy.models import DeltaCrownTransaction
            txn_id = int(transaction_id)
            return DeltaCrownTransaction.objects.filter(pk=txn_id).exists()
        except (ValueError, TypeError):
            return False
        except Exception:
            return False
    
    def check_health(self) -> bool:
        """
        Check if economy service is accessible by testing wallet model.
        """
        try:
            from apps.economy.models import DeltaCrownWallet
            DeltaCrownWallet.objects.exists()
            return True
        except Exception:
            return False
