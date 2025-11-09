"""
Module 5.2: Prize Payouts & Reconciliation - PayoutService Unit Tests

Tests for PayoutService covering:
- Distribution calculations (percent & fixed, rounding)
- Payout processing (happy path & failures)
- Idempotency guarantees
- Economy integration (mocked)
- Refunds for cancelled tournaments
- Reconciliation verification

Target: ≥ 12 unit tests
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.tournaments.models import (
    Tournament, Registration, TournamentResult, PrizeTransaction, Game
)
from apps.tournaments.services.payout_service import PayoutService
from apps.economy.models import DeltaCrownTransaction

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestPayoutServiceDistribution:
    """Tests for calculate_prize_distribution()"""
    
    @pytest.fixture(scope='function')
    def tournament(self):
        """Create a test tournament with distribution config."""
        import uuid
        from django.utils import timezone
        from datetime import timedelta
        
        unique_id = str(uuid.uuid4())[:8]
        
        # Create game
        game = Game.objects.create(
            name=f"Test Game {unique_id}",
            slug=f"test-game-{unique_id}",
            default_team_size=5,
            profile_id_field='game_id',
            is_active=True
        )
        
        # Create organizer
        organizer = User.objects.create_user(
            username=f"organizer-{unique_id}",
            email=f"organizer-{unique_id}@test.com"
        )
        
        now = timezone.now()
        return Tournament.objects.create(
            name=f"Test Tournament {unique_id}",
            slug=f"test-tournament-{unique_id}",
            description="Test description",
            game=game,
            organizer=organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            min_participants=2,
            registration_start=now,
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=10),
            tournament_end=now + timedelta(days=12),
            status=Tournament.COMPLETED,
            prize_distribution={'1st': '500.00', '2nd': '300.00', '3rd': '200.00'}
        )
    
    def test_fixed_amount_distribution(self, tournament):
        """Test distribution with fixed amounts."""
        result = PayoutService.calculate_prize_distribution(tournament.id)
        
        assert result['1st'] == Decimal('500.00')
        assert result['2nd'] == Decimal('300.00')
        assert result['3rd'] == Decimal('200.00')
    
    def test_percent_distribution(self, tournament):
        """Test distribution with percentages."""
        tournament.prize_distribution = {'percent': {1: 50, 2: 30, 3: 20}}
        tournament.save()
        
        result = PayoutService.calculate_prize_distribution(tournament.id, prize_pool=Decimal('1000.00'))
        
        assert result['1st'] == Decimal('500.00')
        assert result['2nd'] == Decimal('300.00')
        assert result['3rd'] == Decimal('200.00')
    
    def test_percent_distribution_rounding_remainder_to_first(self, tournament):
        """Test that rounding remainder goes to 1st place."""
        # Set distribution that causes rounding remainder
        tournament.prize_distribution = {'percent': {1: 33, 2: 33, 3: 34}}
        tournament.save()
        
        result = PayoutService.calculate_prize_distribution(tournament.id, prize_pool=Decimal('100.00'))
        
        # 2nd = 33.00, 3rd = 34.00, 1st gets remainder = 33.00
        # With ROUND_DOWN: 2nd = 33.00, 3rd = 34.00, 1st = 100 - 67 = 33.00
        assert result['2nd'] == Decimal('33.00')
        assert result['3rd'] == Decimal('34.00')
        assert result['1st'] == Decimal('33.00')
        
        # Total should equal prize pool
        total = sum(result.values())
        assert total == Decimal('100.00')
    
    def test_missing_distribution_raises_error(self, tournament):
        """Test that missing distribution config raises ValidationError."""
        tournament.prize_distribution = {}  # Empty dict instead of None (NOT NULL constraint)
        tournament.save()
        
        with pytest.raises(ValidationError) as exc_info:
            PayoutService.calculate_prize_distribution(tournament.id)
        
        assert 'no prize distribution configured' in str(exc_info.value).lower()
    
    def test_percent_without_prize_pool_raises_error(self, tournament):
        """Test that percent mode without prize_pool raises ValidationError."""
        tournament.prize_distribution = {'percent': {1: 50, 2: 30, 3: 20}}
        tournament.save()
        
        with pytest.raises(ValidationError) as exc_info:
            PayoutService.calculate_prize_distribution(tournament.id)  # No prize_pool
        
        assert 'prize pool amount required' in str(exc_info.value).lower()
    
    def test_invalid_percent_sum_raises_error(self, tournament):
        """Test that percentages not summing to 100 raises ValidationError."""
        tournament.prize_distribution = {'percent': {1: 50, 2: 30, 3: 15}}  # Sums to 95
        tournament.save()
        
        with pytest.raises(ValidationError) as exc_info:
            PayoutService.calculate_prize_distribution(tournament.id, prize_pool=Decimal('1000.00'))
        
        assert 'must sum to 100' in str(exc_info.value).lower()


@pytest.mark.django_db(transaction=True)
class TestPayoutServicePayouts:
    """Tests for process_payouts()"""
    
    @pytest.fixture(scope='function')
    def completed_tournament(self):
        """Create a completed tournament with result."""
        import uuid
        from django.utils import timezone
        from datetime import timedelta
        
        unique_id = str(uuid.uuid4())[:8]
        
        # Create game
        game = Game.objects.create(
            name=f"Test Game {unique_id}",
            slug=f"test-game-{unique_id}",
            default_team_size=5,
            profile_id_field='game_id',
            is_active=True
        )
        
        # Create organizer
        organizer = User.objects.create_user(
            username=f"organizer-{unique_id}",
            email=f"organizer-{unique_id}@test.com"
        )
        
        now = timezone.now()
        tournament = Tournament.objects.create(
            name=f"Test Tournament {unique_id}",
            slug=f"test-tournament-{unique_id}",
            description="Test description",
            game=game,
            organizer=organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            min_participants=2,
            registration_start=now,
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=10),
            tournament_end=now + timedelta(days=12),
            status=Tournament.COMPLETED,
            prize_distribution={'1st': '100.00', '2nd': '50.00', '3rd': '25.00'}
        )
        
        # Create registrations (winners)
        unique_id2 = str(uuid.uuid4())[:8]
        user1 = User.objects.create_user(username=f"player1-{unique_id2}", email=f"p1-{unique_id2}@test.com")
        user2 = User.objects.create_user(username=f"player2-{unique_id2}", email=f"p2-{unique_id2}@test.com")
        user3 = User.objects.create_user(username=f"player3-{unique_id2}", email=f"p3-{unique_id2}@test.com")
        
        reg1 = Registration.objects.create(tournament=tournament, user=user1, status='confirmed')
        reg2 = Registration.objects.create(tournament=tournament, user=user2, status='confirmed')
        reg3 = Registration.objects.create(tournament=tournament, user=user3, status='confirmed')
        
        # Create tournament result
        TournamentResult.objects.create(
            tournament=tournament,
            winner=reg1,
            runner_up=reg2,
            third_place=reg3,
            created_by=organizer,
            rules_applied={'method': 'test_fixture'}
        )
        
        return tournament
    
    @patch('apps.tournaments.services.payout_service.award')
    def test_process_payouts_happy_path(self, mock_award, completed_tournament):
        """Test successful payout processing for all placements."""
        # Mock economy service award() to return DeltaCrownTransaction-like objects
        def create_mock_tx(profile, amount, **kwargs):
            mock_tx = Mock()
            mock_tx.id = hash(kwargs.get('idempotency_key', '')) % 10000  # Deterministic ID
            return mock_tx
        
        mock_award.side_effect = create_mock_tx
        
        # Process payouts
        tx_ids = PayoutService.process_payouts(completed_tournament.id)
        
        # Should create 3 transactions (1st, 2nd, 3rd)
        assert len(tx_ids) == 3
        assert mock_award.call_count == 3
        
        # Verify PrizeTransactions created
        prize_txs = PrizeTransaction.objects.filter(tournament=completed_tournament)
        assert prize_txs.count() == 3
        
        # Verify all are completed
        completed = prize_txs.filter(status=PrizeTransaction.Status.COMPLETED)
        assert completed.count() == 3
        
        # Verify amounts
        first_place_tx = prize_txs.get(placement=PrizeTransaction.Placement.FIRST)
        assert first_place_tx.amount == Decimal('100.00')
        assert first_place_tx.coin_transaction_id is not None
    
    @patch('apps.tournaments.services.payout_service.award')
    def test_process_payouts_idempotency(self, mock_award, completed_tournament):
        """Test that duplicate process_payouts() calls don't duplicate transactions."""
        # Mock economy service
        def create_mock_tx(profile, amount, **kwargs):
            mock_tx = Mock()
            mock_tx.id = hash(kwargs.get('idempotency_key', '')) % 10000
            return mock_tx
        
        mock_award.side_effect = create_mock_tx
        
        # First call
        tx_ids_1 = PayoutService.process_payouts(completed_tournament.id)
        assert len(tx_ids_1) == 3
        
        # Second call (idempotent)
        mock_award.reset_mock()
        tx_ids_2 = PayoutService.process_payouts(completed_tournament.id)
        
        # Should not call economy service again (existing PrizeTransactions found)
        assert mock_award.call_count == 0
        assert len(tx_ids_2) == 3  # Returns existing transaction IDs
        
        # Total PrizeTransactions should still be 3 (no duplicates)
        prize_txs = PrizeTransaction.objects.filter(tournament=completed_tournament)
        assert prize_txs.count() == 3
    
    @patch('apps.tournaments.services.payout_service.award')
    def test_process_payouts_economy_failure(self, mock_award, completed_tournament):
        """Test that economy service failures are recorded as failed PrizeTransactions."""
        # Mock economy service to fail for 2nd place
        call_count = [0]
        
        def create_mock_tx(profile, amount, **kwargs):
            call_count[0] += 1
            if 'runner_up' in str(kwargs.get('reason', '')).lower():
                raise Exception("Economy service unavailable")
            mock_tx = Mock()
            mock_tx.id = call_count[0] * 1000
            return mock_tx
        
        mock_award.side_effect = create_mock_tx
        
        # Process payouts
        tx_ids = PayoutService.process_payouts(completed_tournament.id)
        
        # Should create transactions for 1st and 3rd (2nd failed)
        assert len(tx_ids) == 2
        
        # Verify PrizeTransactions
        prize_txs = PrizeTransaction.objects.filter(tournament=completed_tournament)
        assert prize_txs.count() == 3
        
        # Verify statuses
        completed = prize_txs.filter(status=PrizeTransaction.Status.COMPLETED)
        failed = prize_txs.filter(status=PrizeTransaction.Status.FAILED)
        
        assert completed.count() == 2  # 1st and 3rd
        assert failed.count() == 1     # 2nd
        
        # Verify failed transaction has notes
        failed_tx = failed.first()
        assert 'economy service unavailable' in failed_tx.notes.lower()
        assert failed_tx.coin_transaction_id is None
    
    def test_process_payouts_precondition_not_completed(self, completed_tournament):
        """Test that non-COMPLETED tournament raises ValidationError."""
        completed_tournament.status = Tournament.REGISTRATION_OPEN
        completed_tournament.save()
        
        with pytest.raises(ValidationError) as exc_info:
            PayoutService.process_payouts(completed_tournament.id)
        
        assert 'must be completed' in str(exc_info.value).lower()
    
    def test_process_payouts_missing_result(self, completed_tournament):
        """Test that tournament without result raises ValidationError."""
        # Delete tournament result
        TournamentResult.objects.filter(tournament=completed_tournament).delete()
        
        with pytest.raises(ValidationError) as exc_info:
            PayoutService.process_payouts(completed_tournament.id)
        
        assert 'no result record' in str(exc_info.value).lower()
    
    @patch('apps.tournaments.services.payout_service.award')
    def test_process_payouts_partial_placements(self, mock_award, completed_tournament):
        """Test payout processing when only some placements are available."""
        # Remove 3rd place from result
        result = TournamentResult.objects.get(tournament=completed_tournament)
        result.third_place = None
        result.save()
        
        # Mock economy service
        def create_mock_tx(profile, amount, **kwargs):
            mock_tx = Mock()
            mock_tx.id = hash(kwargs.get('idempotency_key', '')) % 10000
            return mock_tx
        
        mock_award.side_effect = create_mock_tx
        
        # Process payouts
        tx_ids = PayoutService.process_payouts(completed_tournament.id)
        
        # Should only create 2 transactions (1st, 2nd)
        assert len(tx_ids) == 2
        assert mock_award.call_count == 2
        
        # Verify PrizeTransactions
        prize_txs = PrizeTransaction.objects.filter(tournament=completed_tournament)
        assert prize_txs.count() == 2


@pytest.mark.django_db(transaction=True)
class TestPayoutServiceRefunds:
    """Tests for process_refunds()"""
    
    @pytest.fixture(scope='function')
    def cancelled_tournament(self):
        """Create a cancelled tournament with confirmed registrations."""
        import uuid
        from django.utils import timezone
        from datetime import timedelta
        
        unique_id = str(uuid.uuid4())[:8]
        
        # Create game
        game = Game.objects.create(
            name=f"Test Game {unique_id}",
            slug=f"test-game-{unique_id}",
            default_team_size=5,
            profile_id_field='game_id',
            is_active=True
        )
        
        # Create organizer
        organizer = User.objects.create_user(
            username=f"organizer-{unique_id}",
            email=f"organizer-{unique_id}@test.com"
        )
        
        now = timezone.now()
        tournament = Tournament.objects.create(
            name=f"Test Tournament {unique_id}",
            slug=f"test-tournament-{unique_id}",
            description="Test description",
            game=game,
            organizer=organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            min_participants=2,
            registration_start=now,
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=10),
            tournament_end=now + timedelta(days=12),
            status=Tournament.CANCELLED,
            entry_fee_amount=Decimal('50.00')
        )
        
        # Create confirmed registrations
        unique_id2 = str(uuid.uuid4())[:8]
        for i in range(3):
            user = User.objects.create_user(
                username=f"player{i}-{unique_id2}",
                email=f"p{i}-{unique_id2}@test.com"
            )
            Registration.objects.create(
                tournament=tournament,
                user=user,
                status='confirmed'
            )
        
        return tournament
    
    @patch('apps.tournaments.services.payout_service.award')
    def test_process_refunds_happy_path(self, mock_award, cancelled_tournament):
        """Test successful refund processing for all confirmed registrations."""
        # Mock economy service
        def create_mock_tx(profile, amount, **kwargs):
            mock_tx = Mock()
            mock_tx.id = hash(kwargs.get('idempotency_key', '')) % 10000
            return mock_tx
        
        mock_award.side_effect = create_mock_tx
        
        # Process refunds
        tx_ids = PayoutService.process_refunds(cancelled_tournament.id)
        
        # Should create 3 refund transactions
        assert len(tx_ids) == 3
        assert mock_award.call_count == 3
        
        # Verify PrizeTransactions created
        prize_txs = PrizeTransaction.objects.filter(tournament=cancelled_tournament)
        assert prize_txs.count() == 3
        
        # Verify all are refunded
        refunded = prize_txs.filter(status=PrizeTransaction.Status.REFUNDED)
        assert refunded.count() == 3
        
        # Verify amounts and placement
        for tx in refunded:
            assert tx.amount == Decimal('50.00')
            assert tx.placement == PrizeTransaction.Placement.PARTICIPATION
    
    @patch('apps.tournaments.services.payout_service.award')
    def test_process_refunds_idempotency(self, mock_award, cancelled_tournament):
        """Test that duplicate process_refunds() calls don't duplicate refunds."""
        # Mock economy service
        def create_mock_tx(profile, amount, **kwargs):
            mock_tx = Mock()
            mock_tx.id = hash(kwargs.get('idempotency_key', '')) % 10000
            return mock_tx
        
        mock_award.side_effect = create_mock_tx
        
        # First call
        tx_ids_1 = PayoutService.process_refunds(cancelled_tournament.id)
        assert len(tx_ids_1) == 3
        
        # Second call (idempotent)
        mock_award.reset_mock()
        tx_ids_2 = PayoutService.process_refunds(cancelled_tournament.id)
        
        # Should not call economy service again
        assert mock_award.call_count == 0
        assert len(tx_ids_2) == 3
        
        # Total PrizeTransactions should still be 3
        prize_txs = PrizeTransaction.objects.filter(tournament=cancelled_tournament)
        assert prize_txs.count() == 3
    
    def test_process_refunds_not_cancelled_raises_error(self, cancelled_tournament):
        """Test that non-CANCELLED tournament raises ValidationError."""
        cancelled_tournament.status = Tournament.COMPLETED
        cancelled_tournament.save()
        
        with pytest.raises(ValidationError) as exc_info:
            PayoutService.process_refunds(cancelled_tournament.id)
        
        assert 'must be cancelled' in str(exc_info.value).lower()


@pytest.mark.django_db(transaction=True)
class TestPayoutServiceReconciliation:
    """Tests for verify_payout_reconciliation()"""
    
    @pytest.fixture(scope='function')
    def tournament_with_payouts(self):
        """Create a tournament with completed payouts."""
        import uuid
        from django.utils import timezone
        from datetime import timedelta
        
        unique_id = str(uuid.uuid4())[:8]
        
        # Create game
        game = Game.objects.create(
            name=f"Test Game {unique_id}",
            slug=f"test-game-{unique_id}",
            default_team_size=5,
            profile_id_field='game_id',
            is_active=True
        )
        
        # Create organizer
        organizer = User.objects.create_user(
            username=f"organizer-{unique_id}",
            email=f"organizer-{unique_id}@test.com"
        )
        
        now = timezone.now()
        tournament = Tournament.objects.create(
            name=f"Test Tournament {unique_id}",
            slug=f"test-tournament-{unique_id}",
            description="Test description",
            game=game,
            organizer=organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            min_participants=2,
            registration_start=now,
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=10),
            tournament_end=now + timedelta(days=12),
            status=Tournament.COMPLETED,
            prize_distribution={'1st': '100.00', '2nd': '50.00'}
        )
        
        # Create registrations
        unique_id2 = str(uuid.uuid4())[:8]
        user1 = User.objects.create_user(username=f"player1-{unique_id2}", email=f"p1-{unique_id2}@test.com")
        user2 = User.objects.create_user(username=f"player2-{unique_id2}", email=f"p2-{unique_id2}@test.com")
        
        reg1 = Registration.objects.create(tournament=tournament, user=user1, status='confirmed')
        reg2 = Registration.objects.create(tournament=tournament, user=user2, status='confirmed')
        
        # Create tournament result
        TournamentResult.objects.create(
            tournament=tournament,
            winner=reg1,
            runner_up=reg2,
            created_by=organizer,
            rules_applied={'method': 'test_fixture'}
        )
        
        # Create completed payouts
        PrizeTransaction.objects.create(
            tournament=tournament,
            participant=reg1,
            placement=PrizeTransaction.Placement.FIRST,
            amount=Decimal('100.00'),
            coin_transaction_id=1001,
            status=PrizeTransaction.Status.COMPLETED
        )
        
        PrizeTransaction.objects.create(
            tournament=tournament,
            participant=reg2,
            placement=PrizeTransaction.Placement.SECOND,
            amount=Decimal('50.00'),
            coin_transaction_id=1002,
            status=PrizeTransaction.Status.COMPLETED
        )
        
        return tournament
    
    def test_reconciliation_happy_path(self, tournament_with_payouts):
        """Test reconciliation passes when all payouts are correct."""
        is_valid, report = PayoutService.verify_payout_reconciliation(tournament_with_payouts.id)
        
        assert is_valid is True
        assert report['is_reconciled'] is True
        assert report['expected_placements'] == ['1st', '2nd']
        assert len(report['completed_payouts']) == 2
        assert len(report['missing_payouts']) == 0
        assert len(report['amount_mismatches']) == 0
        assert len(report['duplicate_checks']) == 0
        assert len(report['failed_transactions']) == 0
    
    def test_reconciliation_missing_payout(self, tournament_with_payouts):
        """Test reconciliation detects missing payouts."""
        # Delete 2nd place payout
        PrizeTransaction.objects.filter(
            tournament=tournament_with_payouts,
            placement=PrizeTransaction.Placement.SECOND
        ).delete()
        
        is_valid, report = PayoutService.verify_payout_reconciliation(tournament_with_payouts.id)
        
        assert is_valid is False
        assert report['is_reconciled'] is False
        assert '2nd' in report['missing_payouts']
        assert len(report['completed_payouts']) == 1  # Only 1st place
    
    def test_reconciliation_amount_mismatch(self, tournament_with_payouts):
        """Test reconciliation detects amount mismatches."""
        # Change 1st place amount
        prize_tx = PrizeTransaction.objects.get(
            tournament=tournament_with_payouts,
            placement=PrizeTransaction.Placement.FIRST
        )
        prize_tx.amount = Decimal('90.00')  # Should be 100.00
        prize_tx.save()
        
        is_valid, report = PayoutService.verify_payout_reconciliation(tournament_with_payouts.id)
        
        assert is_valid is False
        assert report['is_reconciled'] is False
        assert len(report['amount_mismatches']) == 1
        assert report['amount_mismatches'][0]['placement'] == '1st'
        assert report['amount_mismatches'][0]['expected'] == '100.00'
        assert report['amount_mismatches'][0]['actual'] == '90.00'
    
    def test_reconciliation_failed_transactions(self, tournament_with_payouts):
        """Test reconciliation detects failed transactions."""
        # Add a failed transaction
        reg1 = TournamentResult.objects.get(tournament=tournament_with_payouts).winner
        PrizeTransaction.objects.create(
            tournament=tournament_with_payouts,
            participant=reg1,
            placement=PrizeTransaction.Placement.THIRD,
            amount=Decimal('25.00'),
            coin_transaction_id=None,
            status=PrizeTransaction.Status.FAILED,
            notes="Test failure"
        )
        
        is_valid, report = PayoutService.verify_payout_reconciliation(tournament_with_payouts.id)
        
        # Note: Failed transactions don't affect reconciliation of expected placements
        # (3rd place not in expected_placements), but they're still reported
        assert len(report['failed_transactions']) == 1
        assert report['failed_transactions'][0]['notes'] == "Test failure"
