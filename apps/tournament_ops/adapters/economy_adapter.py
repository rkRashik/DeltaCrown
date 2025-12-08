"""
Economy service adapter for cross-domain payment/balance operations.

Provides TournamentOps with access to DeltaCoin economy operations (payments,
refunds, balance queries) without direct imports from apps.economy.models.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.1
"""

from typing import Protocol, runtime_checkable, Dict, Any, Optional

from .base import BaseAdapter


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
    
    This adapter is the ONLY way for TournamentOps to interact with the
    DeltaCoin economy system. It handles payments, refunds, and balance queries.
    
    Implementation Note:
    - Phase 1, Epic 1.1: Create adapter skeleton (this file)
    - Phase 1, Epic 1.3: Wire up DTOs
    - Phase 1, Epic 1.4: Implement actual payment operations via economy service
    - Phase 1, Epic 1.1: Add unit tests with mocked economy service
    
    Reference: CLEANUP_AND_TESTING_PART_6.md - §4.4 (Service-Based APIs)
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
        
        TODO: Implement via WalletService.charge() (Phase 1, Epic 1.4).
        TODO: Return PaymentResultDTO instead of dict.
        
        For Phase 1, returns mock success response.
        
        Args:
            user_id: User to charge
            tournament_id: Tournament context
            amount: DeltaCoin amount to charge
            currency: Currency code (default: DC)
        
        Returns:
            Dict containing transaction details
        
        Raises:
            PaymentFailedError: If payment processing fails
        """
        from apps.tournament_ops.exceptions import PaymentFailedError
        import uuid
        from datetime import datetime, timezone
        
        # TODO: Replace with actual WalletService.charge() call
        # from apps.economy.services.wallet_service import WalletService
        # result = WalletService.charge(
        #     user_id=user_id,
        #     amount=amount,
        #     currency=currency,
        #     metadata={'tournament_id': tournament_id, 'type': 'registration_fee'}
        # )
        # return PaymentResultDTO.from_model(result)
        
        # Phase 1 mock implementation
        if amount < 0:
            raise PaymentFailedError("Invalid amount: must be positive")
        
        return {
            'transaction_id': str(uuid.uuid4()),
            'user_id': user_id,
            'amount': amount,
            'currency': currency,
            'status': 'completed',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'metadata': {
                'tournament_id': tournament_id,
                'type': 'registration_fee'
            }
        }
    
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
        
        TODO: Implement via WalletService.refund() (Phase 1, Epic 1.4).
        TODO: Return PaymentResultDTO instead of dict.
        
        For Phase 1, returns mock success response.
        
        Args:
            user_id: User to refund
            tournament_id: Tournament context
            amount: DeltaCoin amount to refund
            currency: Currency code (default: DC)
            reason: Optional refund reason
        
        Returns:
            Dict containing refund transaction details
        
        Raises:
            PaymentFailedError: If refund processing fails
        """
        from apps.tournament_ops.exceptions import PaymentFailedError
        import uuid
        from datetime import datetime, timezone
        
        # TODO: Replace with actual WalletService.refund() call
        # from apps.economy.services.wallet_service import WalletService
        # result = WalletService.refund(
        #     user_id=user_id,
        #     amount=amount,
        #     currency=currency,
        #     metadata={'tournament_id': tournament_id, 'reason': reason}
        # )
        # return PaymentResultDTO.from_model(result)
        
        # Phase 1 mock implementation
        if amount < 0:
            raise PaymentFailedError("Invalid refund amount: must be positive")
        
        return {
            'transaction_id': str(uuid.uuid4()),
            'user_id': user_id,
            'amount': amount,
            'currency': currency,
            'status': 'refunded',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'metadata': {
                'tournament_id': tournament_id,
                'type': 'refund',
                'reason': reason or 'Tournament cancellation'
            }
        }
    
    def get_balance(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's current DeltaCoin balance.
        
        TODO: Implement via WalletService.get_balance() (Phase 1, Epic 1.4).
        TODO: Return BalanceDTO instead of dict.
        
        For Phase 1, returns mock balance data.
        
        Args:
            user_id: User identifier
        
        Returns:
            Dict containing balance data
        """
        # TODO: Replace with actual WalletService.get_balance() call
        # from apps.economy.services.wallet_service import WalletService
        # balance = WalletService.get_balance(user_id)
        # return BalanceDTO.from_model(balance)
        
        # Phase 1 mock implementation
        return {
            'user_id': user_id,
            'balance': 10000,  # Mock balance: 10,000 DC
            'currency': 'DC',
            'frozen_balance': 0,
        }
    
    def verify_payment(self, transaction_id: str) -> bool:
        """
        Verify that a payment transaction completed successfully.
        
        TODO: Implement via WalletService.verify_transaction() (Phase 1, Epic 1.4).
        
        For Phase 1, returns True (mock verification).
        
        Args:
            transaction_id: Payment transaction identifier
        
        Returns:
            bool: True if payment verified, False otherwise
        """
        # TODO: Replace with actual WalletService.verify_transaction() call
        # from apps.economy.services.wallet_service import WalletService
        # return WalletService.verify_transaction(transaction_id)
        
        # Phase 1 mock implementation - verify UUID format
        import uuid
        try:
            uuid.UUID(transaction_id)
            return True
        except (ValueError, AttributeError):
            return False
    
    def check_health(self) -> bool:
        """
        Check if economy service is accessible.
        
        TODO: Implement actual health check when economy models/services exist.
        For Phase 1, always returns True (no economy service dependency yet).
        """
        # TODO: Check WalletService.check_health() when available
        # For Phase 1, assume healthy
        return True
