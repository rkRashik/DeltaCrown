"""
Module 5.2: Prize Payouts & Reconciliation - PayoutService

Handles prize distribution, refunds, and reconciliation for completed tournaments.

Key Features:
- Calculate prize distribution (percent or fixed amounts)
- Process payouts with idempotency (via economy service)
- Process refunds for cancelled tournaments
- Verify payout reconciliation

Source: PHASE_5_IMPLEMENTATION_PLAN.md Module 5.2
ADR-001: Economy app decoupling (IntegerField references)
"""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet
from apps.tournaments.models import Tournament, Registration, TournamentResult, PrizeTransaction, Payment

User = get_user_model()
logger = logging.getLogger(__name__)

__all__ = [
    'PayoutService',
]


class PayoutService:
    """
    Service for managing tournament prize payouts and refunds.
    
    All methods are atomic and idempotent via unique constraints and idempotency keys.
    """
    
    # Placement mapping for PrizeTransaction.Placement choices
    PLACEMENT_MAP = {
        '1st': PrizeTransaction.Placement.FIRST,
        '2nd': PrizeTransaction.Placement.SECOND,
        '3rd': PrizeTransaction.Placement.THIRD,
        'participation': PrizeTransaction.Placement.PARTICIPATION,
    }

    @staticmethod
    def _locked_wallet_for_profile(profile):
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
        return DeltaCrownWallet.objects.select_for_update().get(pk=wallet.pk)

    @classmethod
    def _create_wallet_transaction(
        cls,
        *,
        profile,
        amount: int,
        reason: str,
        tournament_id: int,
        registration_id: int,
        note: str,
        created_by: Optional[User],
        idempotency_key: str,
    ) -> Tuple[DeltaCrownTransaction, bool]:
        wallet = cls._locked_wallet_for_profile(profile)
        balance_after = int(wallet.cached_balance) + int(amount)

        try:
            coin_tx = DeltaCrownTransaction.objects.create(
                wallet=wallet,
                amount=int(amount),
                reason=reason,
                tournament_id=tournament_id,
                registration_id=registration_id,
                note=note,
                created_by=created_by,
                idempotency_key=idempotency_key,
                cached_balance_after=balance_after,
            )
        except IntegrityError:
            existing_tx = DeltaCrownTransaction.objects.get(idempotency_key=idempotency_key)
            return existing_tx, False

        wallet.cached_balance = balance_after
        wallet.save(update_fields=['cached_balance', 'updated_at'])
        return coin_tx, True
    
    @classmethod
    def calculate_prize_distribution(
        cls,
        tournament_id: int,
        prize_pool: Optional[Decimal] = None
    ) -> Dict[str, Decimal]:
        """
        Calculate prize distribution amounts for a tournament.
        
        Supports two modes:
        1. Percentage distribution: e.g., {1: 50, 2: 30, 3: 20} -> calculates from prize_pool
        2. Fixed amounts: e.g., {"1st": "500.00", "2nd": "300.00", "3rd": "200.00"}
        
        Args:
            tournament_id: Tournament ID
            prize_pool: Total prize pool amount (required for percentage mode)
        
        Returns:
            Dict mapping placement ('1st', '2nd', '3rd') to Decimal amounts
        
        Raises:
            ValidationError: If tournament not found, invalid distribution config, or missing prize pool
        
        Notes:
            - All amounts rounded to 2 decimal places (ROUND_DOWN)
            - Remainder from rounding goes to 1st place (documented in notes)
        """
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament {tournament_id} not found")
        
        # Get distribution configuration from tournament
        # In this implementation, we'll use a simple JSONB field pattern
        # For now, assume tournament has a prize_distribution field (JSONB)
        distribution_config = getattr(tournament, 'prize_distribution', None)
        
        if not distribution_config or distribution_config == {}:
            raise ValidationError(
                f"Tournament {tournament_id} has no prize distribution configured. "
                "Set tournament.prize_distribution to a dict like {{'1st': '500.00', '2nd': '300.00'}} "
                "or {{'percent': {{1: 50, 2: 30, 3: 20}}}} with prize_pool."
            )
        
        # Mode 1: Fixed amounts (dict with placement keys)
        if '1st' in distribution_config or '2nd' in distribution_config or '3rd' in distribution_config:
            result = {}
            for placement_key in ['1st', '2nd', '3rd']:
                if placement_key in distribution_config:
                    amount = Decimal(str(distribution_config[placement_key]))
                    # Round to 2 decimal places
                    result[placement_key] = amount.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            return result
        
        # Mode 2: Percentage distribution
        if 'percent' in distribution_config:
            if not prize_pool:
                raise ValidationError(
                    f"Prize pool amount required for percentage distribution. "
                    f"Distribution config: {distribution_config}"
                )
            
            prize_pool = Decimal(str(prize_pool))
            percent_map = distribution_config['percent']
            
            # Validate percentages sum to 100
            total_percent = sum(percent_map.values())
            if total_percent != 100:
                raise ValidationError(
                    f"Percentage distribution must sum to 100, got {total_percent}. "
                    f"Config: {percent_map}"
                )
            
            result = {}
            allocated_total = Decimal('0.00')
            
            # Calculate amounts for 2nd and 3rd first (ROUND_DOWN)
            # Note: JSON serialization converts integer keys to strings
            for position, percent in sorted(percent_map.items(), reverse=True):
                # Normalize position to int for comparison
                pos_int = int(position) if isinstance(position, str) else position
                if pos_int == 1:
                    continue  # Handle 1st place last to get remainder
                
                # Map position number to placement key
                placement_key = '2nd' if pos_int == 2 else '3rd'
                amount = (prize_pool * Decimal(percent) / Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_DOWN
                )
                result[placement_key] = amount
                allocated_total += amount
            
            # 1st place gets remainder (handles rounding remainder)
            # Check for both int and string keys
            if 1 in percent_map or '1' in percent_map:
                result['1st'] = prize_pool - allocated_total
            
            return result
        
        raise ValidationError(
            f"Invalid prize distribution config. Expected fixed amounts or percent map. "
            f"Got: {distribution_config}"
        )
    
    @classmethod
    @transaction.atomic
    def process_payouts(
        cls,
        tournament_id: int,
        processed_by: Optional[User] = None
    ) -> List[int]:
        """
        Process prize payouts for a completed tournament.
        
        Preconditions:
        - Tournament status must be COMPLETED
        - TournamentResult must exist (from Module 5.1)
        
        For each placement (1st/2nd/3rd):
        - Creates DeltaCrownTransaction via economy service (idempotent)
        - Creates PrizeTransaction audit record
        - Sets status='completed' on success, 'failed' on error (with notes)
        
        Args:
            tournament_id: Tournament ID
            processed_by: User who triggered the payout (optional)
        
        Returns:
            List of DeltaCrownTransaction IDs created
        
        Raises:
            ValidationError: If preconditions not met or distribution invalid
        
        Notes:
            - Idempotency key pattern: prize_payout_t{t_id}_r{reg_id}_p{placement}
            - If placement winner missing, skips that placement (logs warning)
            - Economy call failures: sets status='failed' + notes, continues with others
            - Method returns partial success list on failures
        """
        # Validate preconditions
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament {tournament_id} not found")
        
        if tournament.status != Tournament.COMPLETED:
            raise ValidationError(
                f"Tournament {tournament_id} must be COMPLETED for payouts. "
                f"Current status: {tournament.status}"
            )
        
        # Check for TournamentResult (from Module 5.1)
        try:
            result = TournamentResult.objects.get(tournament=tournament)
        except TournamentResult.DoesNotExist:
            raise ValidationError(
                f"Tournament {tournament_id} has no result record. "
                "Run WinnerDeterminationService.determine_winners() first (Module 5.1)."
            )
        
        # Get prize distribution
        prize_pool = getattr(tournament, 'prize_pool_amount', None)
        if prize_pool:
            prize_pool = Decimal(str(prize_pool))
        
        try:
            distribution = cls.calculate_prize_distribution(tournament_id, prize_pool)
        except ValidationError as e:
            raise ValidationError(f"Invalid prize distribution: {e}")
        
        created_transaction_ids: List[int] = []
        
        # Map TournamentResult fields to placement keys
        placement_winners = {
            '1st': result.winner_id,
            '2nd': result.runner_up_id,
            '3rd': result.third_place_id,
        }
        
        for placement_key, registration_id in placement_winners.items():
            if not registration_id:
                logger.warning(
                    f"Tournament {tournament_id}: No {placement_key} place winner, skipping payout"
                )
                continue
            
            if placement_key not in distribution:
                logger.warning(
                    f"Tournament {tournament_id}: No amount configured for {placement_key} place, skipping"
                )
                continue
            
            amount = distribution[placement_key]
            if amount <= 0:
                logger.info(
                    f"Tournament {tournament_id}: {placement_key} place amount is {amount}, skipping"
                )
                continue
            
            # Get registration
            try:
                registration = Registration.objects.select_related('user').get(id=registration_id)
            except Registration.DoesNotExist:
                logger.error(
                    f"Tournament {tournament_id}: Registration {registration_id} not found for {placement_key}"
                )
                continue
            
            # Idempotency: Check if PrizeTransaction already exists
            placement_enum = cls.PLACEMENT_MAP[placement_key]
            existing = PrizeTransaction.objects.filter(
                tournament=tournament,
                participant=registration,
                placement=placement_enum
            ).first()
            
            if existing:
                logger.info(
                    f"Tournament {tournament_id}: PrizeTransaction already exists for {placement_key} "
                    f"(Registration {registration_id}), status={existing.status}"
                )
                if existing.coin_transaction_id and existing.status == PrizeTransaction.Status.COMPLETED:
                    created_transaction_ids.append(existing.coin_transaction_id)
                continue
            
            # Award via economy service
            try:
                if not registration.user_id:
                    raise ValueError(f"Registration {registration_id} has no user")
                profile = registration.user.profile
                
                # Idempotency key for economy service
                idempotency_key = f"prize_payout_t{tournament_id}_r{registration_id}_p{placement_key}"
                
                # Convert Decimal to int (Delta Coins are stored as integers in economy)
                amount_int = int(amount)
                
                # Atomic: both economy credit and prize audit record succeed or fail together
                with transaction.atomic():
                    coin_tx, _created = cls._create_wallet_transaction(
                        profile=profile,
                        amount=amount_int,
                        reason=DeltaCrownTransaction.Reason.WINNER if placement_key == '1st' else (
                            DeltaCrownTransaction.Reason.RUNNER_UP if placement_key == '2nd' else 
                            DeltaCrownTransaction.Reason.TOP4
                        ),
                        tournament_id=tournament.id,
                        registration_id=registration.id,
                        note=f"Prize payout - {placement_key} place",
                        created_by=processed_by,
                        idempotency_key=idempotency_key,
                    )
                    
                    # Create PrizeTransaction audit record
                    prize_tx = PrizeTransaction.objects.create(
                        tournament=tournament,
                        participant=registration,
                        placement=placement_enum,
                        amount=amount,
                        coin_transaction_id=coin_tx.id,  # IntegerField reference to economy
                        status=PrizeTransaction.Status.COMPLETED,
                        processed_by=processed_by,
                        notes=f"Prize payout processed successfully. Economy TX ID: {coin_tx.id}"
                    )
                
                created_transaction_ids.append(coin_tx.id)
                logger.info(
                    f"Tournament {tournament_id}: Created payout for {placement_key} place "
                    f"(Registration {registration_id}, Amount: {amount}, Economy TX: {coin_tx.id})"
                )
            
            except Exception as e:
                # Economy call failed - create failed PrizeTransaction
                logger.error(
                    f"Tournament {tournament_id}: Payout failed for {placement_key} place "
                    f"(Registration {registration_id}): {e}"
                )
                
                PrizeTransaction.objects.create(
                    tournament=tournament,
                    participant=registration,
                    placement=placement_enum,
                    amount=amount,
                    coin_transaction_id=None,
                    status=PrizeTransaction.Status.FAILED,
                    processed_by=processed_by,
                    notes=f"Payout failed: {str(e)}"
                )
        
        return created_transaction_ids
    
    @classmethod
    @transaction.atomic
    def process_refunds(
        cls,
        tournament_id: int,
        processed_by: Optional[User] = None
    ) -> List[int]:
        """
        Process refunds for a cancelled tournament.
        
        Refunds verified DeltaCoin payments only, using the original debit
        transaction amount.
        
        Args:
            tournament_id: Tournament ID
            processed_by: User who triggered refunds (optional)
        
        Returns:
            List of DeltaCrownTransaction IDs created
        
        Raises:
            ValidationError: If tournament not found or not cancelled
        
        Notes:
            - Idempotency key pattern: prize_refund_t{t_id}_r{reg_id}
            - Creates PrizeTransaction with status='refunded' and placement='participation'
            - Only processes confirmed registrations that paid with DeltaCoin
        """
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament {tournament_id} not found")
        
        if tournament.status != Tournament.CANCELLED:
            raise ValidationError(
                f"Tournament {tournament_id} must be CANCELLED for refunds. "
                f"Current status: {tournament.status}"
            )
        
        payments = Payment.objects.filter(
            registration__tournament=tournament,
            registration__status=Registration.CONFIRMED,
            payment_method=Payment.DELTACOIN,
            status=Payment.VERIFIED,
        ).select_related('registration__user')

        if not payments.exists():
            logger.info(
                f"Tournament {tournament_id}: No verified DeltaCoin payments, no refunds to process"
            )
            return []
        
        created_transaction_ids: List[int] = []
        
        for payment in payments:
            registration = payment.registration
            original_idempotency_key = f"tournament_entry_{tournament_id}_reg_{registration.id}"
            original_tx = DeltaCrownTransaction.objects.filter(
                idempotency_key=original_idempotency_key,
                amount__lt=0,
                reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT,
            ).first()
            if original_tx is None:
                logger.warning(
                    f"Tournament {tournament_id}: Missing original DeltaCoin debit for "
                    f"Registration {registration.id}, skipping refund"
                )
                continue

            amount_int = abs(int(original_tx.amount))
            refund_amount = Decimal(str(amount_int))

            # Idempotency: Check if refund PrizeTransaction already exists
            existing = PrizeTransaction.objects.filter(
                tournament=tournament,
                participant=registration,
                placement=PrizeTransaction.Placement.PARTICIPATION,
                status=PrizeTransaction.Status.REFUNDED
            ).first()
            
            if existing:
                logger.info(
                    f"Tournament {tournament_id}: Refund already processed for Registration {registration.id}"
                )
                if existing.coin_transaction_id:
                    created_transaction_ids.append(existing.coin_transaction_id)
                continue
            
            # Award via economy service (positive amount = credit)
            try:
                if not registration.user_id:
                    raise ValueError(f"Registration {registration.id} has no user")
                profile = registration.user.profile
                
                # Idempotency key for economy service
                idempotency_key = f"prize_refund_t{tournament_id}_r{registration.id}"
                
                coin_tx, _created = cls._create_wallet_transaction(
                    profile=profile,
                    amount=amount_int,
                    reason=DeltaCrownTransaction.Reason.REFUND,
                    tournament_id=tournament.id,
                    registration_id=registration.id,
                    note=f"Entry fee refund - tournament cancelled",
                    created_by=processed_by,
                    idempotency_key=idempotency_key,
                )
                
                # Create PrizeTransaction audit record
                prize_tx = PrizeTransaction.objects.create(
                    tournament=tournament,
                    participant=registration,
                    placement=PrizeTransaction.Placement.PARTICIPATION,  # Refunds use 'participation'
                    amount=refund_amount,
                    coin_transaction_id=coin_tx.id,
                    status=PrizeTransaction.Status.REFUNDED,
                    processed_by=processed_by,
                    notes=f"Entry fee refund processed. Economy TX ID: {coin_tx.id}"
                )
                
                created_transaction_ids.append(coin_tx.id)
                logger.info(
                    f"Tournament {tournament_id}: Refund processed for Registration {registration.id} "
                    f"(Amount: {refund_amount}, Economy TX: {coin_tx.id})"
                )
            
            except Exception as e:
                # Economy call failed - create failed refund record
                logger.error(
                    f"Tournament {tournament_id}: Refund failed for Registration {registration.id}: {e}"
                )
                
                PrizeTransaction.objects.create(
                    tournament=tournament,
                    participant=registration,
                    placement=PrizeTransaction.Placement.PARTICIPATION,
                    amount=refund_amount,
                    coin_transaction_id=None,
                    status=PrizeTransaction.Status.FAILED,
                    processed_by=processed_by,
                    notes=f"Refund failed: {str(e)}"
                )
        
        return created_transaction_ids
    
    @classmethod
    def verify_payout_reconciliation(cls, tournament_id: int) -> Tuple[bool, Dict[str, any]]:
        """
        Verify payout reconciliation for a tournament.
        
        Checks:
        1. Every expected placement has a completed transaction
        2. Transaction amounts match distribution
        3. No duplicate payouts for same (tournament, participant, placement)
        
        Args:
            tournament_id: Tournament ID
        
        Returns:
            Tuple of (is_valid, report_dict)
            - is_valid: True if all checks pass
            - report_dict: Detailed reconciliation report
        
        Report structure:
            {
                'tournament_id': int,
                'status': str,
                'expected_placements': List[str],
                'completed_payouts': Dict[str, Decimal],
                'missing_payouts': List[str],
                'amount_mismatches': List[Dict],
                'duplicate_checks': Dict[str, int],
                'failed_transactions': List[Dict],
                'is_reconciled': bool
            }
        """
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return False, {'error': f'Tournament {tournament_id} not found'}
        
        report = {
            'tournament_id': tournament_id,
            'status': tournament.status,
            'expected_placements': [],
            'completed_payouts': {},
            'missing_payouts': [],
            'amount_mismatches': [],
            'duplicate_checks': {},
            'failed_transactions': [],
            'is_reconciled': False
        }
        
        # Get tournament result to determine expected placements
        try:
            result = TournamentResult.objects.get(tournament=tournament)
        except TournamentResult.DoesNotExist:
            report['error'] = 'No tournament result found'
            return False, report
        
        # Determine expected placements
        if result.winner_id:
            report['expected_placements'].append('1st')
        if result.runner_up_id:
            report['expected_placements'].append('2nd')
        if result.third_place_id:
            report['expected_placements'].append('3rd')
        
        # Get prize distribution
        prize_pool = getattr(tournament, 'prize_pool_amount', None)
        if prize_pool:
            prize_pool = Decimal(str(prize_pool))
        
        try:
            expected_distribution = cls.calculate_prize_distribution(tournament_id, prize_pool)
        except ValidationError as e:
            report['error'] = f'Invalid distribution: {e}'
            return False, report
        
        # Get all PrizeTransactions for this tournament
        prize_txs = PrizeTransaction.objects.filter(tournament=tournament).select_related('participant')
        
        # Check for completed payouts
        for placement_key in report['expected_placements']:
            placement_enum = cls.PLACEMENT_MAP[placement_key]
            
            # Find completed transactions for this placement
            completed = prize_txs.filter(
                placement=placement_enum,
                status=PrizeTransaction.Status.COMPLETED
            )
            
            if completed.count() == 0:
                report['missing_payouts'].append(placement_key)
            elif completed.count() > 1:
                # Duplicate check
                report['duplicate_checks'][placement_key] = completed.count()
            else:
                # Check amount match
                tx = completed.first()
                expected_amount = expected_distribution.get(placement_key, Decimal('0.00'))
                if tx.amount != expected_amount:
                    report['amount_mismatches'].append({
                        'placement': placement_key,
                        'expected': str(expected_amount),
                        'actual': str(tx.amount),
                        'participant_id': tx.participant_id
                    })
                else:
                    report['completed_payouts'][placement_key] = tx.amount
        
        # Check for failed transactions
        failed = prize_txs.filter(status=PrizeTransaction.Status.FAILED)
        for tx in failed:
            report['failed_transactions'].append({
                'id': tx.id,
                'placement': tx.placement,
                'participant_id': tx.participant_id,
                'amount': str(tx.amount),
                'notes': tx.notes
            })
        
        # Determine if reconciled
        report['is_reconciled'] = (
            len(report['missing_payouts']) == 0 and
            len(report['amount_mismatches']) == 0 and
            len(report['duplicate_checks']) == 0 and
            len(report['failed_transactions']) == 0 and
            len(report['completed_payouts']) == len(report['expected_placements'])
        )
        
        return report['is_reconciled'], report
