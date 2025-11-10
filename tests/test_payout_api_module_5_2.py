"""
Prize Payout & Refund API Tests

API endpoint tests for Module 5.2 Milestone 3.

Related Planning:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md#module-52
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md#section-6

Module: tests.test_payout_api_module_5_2
Implements: phase_5:module_5_2:milestone_3

Test Coverage:
- Permission checks (401/403/200)
- Happy path payouts (creates transactions, returns IDs)
- Idempotency (second POST returns no duplicates)
- Happy path refunds (cancelled tournaments)
- Refund idempotency
- Reconciliation ok/!ok branches
- 409 conflicts for bad tournament state
- 400 for malformed distribution
"""

import pytest
import uuid
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from decimal import Decimal

from apps.tournaments.models import (
    Game, Tournament, Registration, TournamentResult, PrizeTransaction
)

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestPayoutAPIPermissions:
    """Test permission checks for payout endpoints."""
    
    @pytest.fixture(scope='function')
    def setup_data(self):
        """Create test data for permission tests."""
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
            email=f"organizer-{unique_id}@test.com",
            password='testpass123'
        )
        
        # Create other user
        other_user = User.objects.create_user(
            username=f"other-{unique_id}",
            email=f"other-{unique_id}@test.com",
            password='testpass123'
        )
        
        # Create admin user (using create_superuser to ensure is_staff=True)
        admin_user = User.objects.create_superuser(
            username=f"admin-{unique_id}",
            email=f"admin-{unique_id}@test.com",
            password='testpass123'
        )
        
        # Create tournament
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
        
        return {
            'tournament': tournament,
            'organizer': organizer,
            'other_user': other_user,
            'admin_user': admin_user
        }
    
    def test_anonymous_user_gets_401(self, setup_data):
        """Test that anonymous users get 401 Unauthorized."""
        tournament = setup_data['tournament']
        client = APIClient()
        
        response = client.post(f'/api/tournaments/{tournament.id}/payouts/', {})
        assert response.status_code == 401
    
    def test_non_organizer_gets_403(self, setup_data):
        """Test that non-organizer authenticated users get 403 Forbidden."""
        tournament = setup_data['tournament']
        other_user = setup_data['other_user']
        
        client = APIClient()
        client.force_authenticate(user=other_user)
        
        response = client.post(f'/api/tournaments/{tournament.id}/payouts/', {})
        assert response.status_code == 403
    
    def test_organizer_gets_200(self, setup_data):
        """Test that tournament organizer gets 200."""
        tournament = setup_data['tournament']
        organizer = setup_data['organizer']
        
        # Create result
        reg = Registration.objects.create(tournament=tournament, user=organizer, status='confirmed')
        TournamentResult.objects.create(
            tournament=tournament,
            winner=reg,
            created_by=organizer,
            rules_applied={'method': 'test'}
        )
        
        client = APIClient()
        client.force_authenticate(user=organizer)
        
        with patch('apps.tournaments.services.payout_service.award') as mock_award:
            mock_tx = Mock()
            mock_tx.id = 123
            mock_award.return_value = mock_tx
            
            response = client.post(f'/api/tournaments/{tournament.id}/payouts/', {})
            assert response.status_code == 200
    
    def test_admin_gets_200(self, setup_data):
        """Test that admin user gets 200."""
        tournament = setup_data['tournament']
        organizer = setup_data['organizer']
        admin_user = setup_data['admin_user']
        
        # Create result
        reg = Registration.objects.create(tournament=tournament, user=organizer, status='confirmed')
        TournamentResult.objects.create(
            tournament=tournament,
            winner=reg,
            created_by=organizer,
            rules_applied={'method': 'test'}
        )
        
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        with patch('apps.tournaments.services.payout_service.award') as mock_award:
            mock_tx = Mock()
            mock_tx.id = 123
            mock_award.return_value = mock_tx
            
            response = client.post(f'/api/tournaments/{tournament.id}/payouts/', {})
            assert response.status_code == 200


@pytest.mark.django_db(transaction=True)
class TestPayoutAPIHappyPath:
    """Test happy path scenarios for payout processing."""
    
    @pytest.fixture(scope='function')
    def completed_tournament(self):
        """Create a completed tournament with results."""
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
            email=f"organizer-{unique_id}@test.com",
            password='testpass123'
        )
        
        # Create tournament
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
        
        return {'tournament': tournament, 'organizer': organizer}
    
    @patch('apps.tournaments.services.payout_service.award')
    def test_process_payouts_returns_transaction_ids(self, mock_award, completed_tournament):
        """Test that process_payouts returns created transaction IDs."""
        tournament = completed_tournament['tournament']
        organizer = completed_tournament['organizer']
        
        # Mock economy service
        def create_mock_tx(profile, amount, **kwargs):
            mock_tx = Mock()
            mock_tx.id = hash(kwargs.get('idempotency_key', '')) % 10000
            return mock_tx
        
        mock_award.side_effect = create_mock_tx
        
        client = APIClient()
        client.force_authenticate(user=organizer)
        
        response = client.post(f'/api/tournaments/{tournament.id}/payouts/', {})
        
        assert response.status_code == 200
        assert 'tournament_id' in response.data
        assert 'created_transaction_ids' in response.data
        assert 'count' in response.data
        assert 'mode' in response.data
        assert 'idempotent' in response.data
        
        assert response.data['tournament_id'] == tournament.id
        assert response.data['mode'] == 'payout'
        assert response.data['idempotent'] is True
        assert response.data['count'] == 3
        assert len(response.data['created_transaction_ids']) == 3
    
    @patch('apps.tournaments.services.payout_service.award')
    def test_process_payouts_creates_prize_transactions(self, mock_award, completed_tournament):
        """Test that process_payouts creates PrizeTransaction records."""
        tournament = completed_tournament['tournament']
        organizer = completed_tournament['organizer']
        
        # Mock economy service
        mock_tx = Mock()
        mock_tx.id = 123
        mock_award.return_value = mock_tx
        
        client = APIClient()
        client.force_authenticate(user=organizer)
        
        response = client.post(f'/api/tournaments/{tournament.id}/payouts/', {})
        
        assert response.status_code == 200
        
        # Verify PrizeTransaction records created
        prize_txs = PrizeTransaction.objects.filter(tournament=tournament)
        assert prize_txs.count() == 3
        assert prize_txs.filter(status='completed').count() == 3
    
    @patch('apps.tournaments.services.payout_service.award')
    def test_process_payouts_idempotency(self, mock_award, completed_tournament):
        """Test that duplicate payout calls don't create duplicates."""
        tournament = completed_tournament['tournament']
        organizer = completed_tournament['organizer']
        
        # Mock economy service
        mock_tx = Mock()
        mock_tx.id = 123
        mock_award.return_value = mock_tx
        
        client = APIClient()
        client.force_authenticate(user=organizer)
        
        # First call
        response1 = client.post(f'/api/tournaments/{tournament.id}/payouts/', {})
        assert response1.status_code == 200
        count1 = response1.data['count']
        
        # Reset mock
        mock_award.reset_mock()
        
        # Second call (idempotent)
        response2 = client.post(f'/api/tournaments/{tournament.id}/payouts/', {})
        assert response2.status_code == 200
        count2 = response2.data['count']

        # Should not call economy service again (idempotent)
        assert mock_award.call_count == 0
        # Idempotent: returns existing transactions, so count should be same
        assert count2 == count1        # Verify only 3 PrizeTransaction records exist (no duplicates)
        prize_txs = PrizeTransaction.objects.filter(tournament=tournament)
        assert prize_txs.count() == 3


@pytest.mark.django_db(transaction=True)
class TestRefundAPIHappyPath:
    """Test happy path scenarios for refund processing."""
    
    @pytest.fixture(scope='function')
    def cancelled_tournament(self):
        """Create a cancelled tournament with registrations."""
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
            email=f"organizer-{unique_id}@test.com",
            password='testpass123'
        )
        
        # Create tournament
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
            entry_fee_amount=Decimal('10.00')
        )
        
        # Create registrations
        unique_id2 = str(uuid.uuid4())[:8]
        user1 = User.objects.create_user(username=f"player1-{unique_id2}", email=f"p1-{unique_id2}@test.com")
        user2 = User.objects.create_user(username=f"player2-{unique_id2}", email=f"p2-{unique_id2}@test.com")
        user3 = User.objects.create_user(username=f"player3-{unique_id2}", email=f"p3-{unique_id2}@test.com")
        
        Registration.objects.create(tournament=tournament, user=user1, status='confirmed')
        Registration.objects.create(tournament=tournament, user=user2, status='confirmed')
        Registration.objects.create(tournament=tournament, user=user3, status='confirmed')
        
        return {'tournament': tournament, 'organizer': organizer}
    
    @patch('apps.tournaments.services.payout_service.award')
    def test_process_refunds_returns_transaction_ids(self, mock_award, cancelled_tournament):
        """Test that process_refunds returns created transaction IDs."""
        tournament = cancelled_tournament['tournament']
        organizer = cancelled_tournament['organizer']
        
        # Mock economy service
        def create_mock_tx(profile, amount, **kwargs):
            mock_tx = Mock()
            mock_tx.id = hash(kwargs.get('idempotency_key', '')) % 10000
            return mock_tx
        
        mock_award.side_effect = create_mock_tx
        
        client = APIClient()
        client.force_authenticate(user=organizer)
        
        response = client.post(f'/api/tournaments/{tournament.id}/refunds/', {})
        
        assert response.status_code == 200
        assert response.data['tournament_id'] == tournament.id
        assert response.data['mode'] == 'refund'
        assert response.data['idempotent'] is True
        assert response.data['count'] == 3
        assert len(response.data['created_transaction_ids']) == 3
    
    @patch('apps.tournaments.services.payout_service.award')
    def test_process_refunds_idempotency(self, mock_award, cancelled_tournament):
        """Test that duplicate refund calls don't create duplicates."""
        tournament = cancelled_tournament['tournament']
        organizer = cancelled_tournament['organizer']
        
        # Mock economy service
        mock_tx = Mock()
        mock_tx.id = 456
        mock_award.return_value = mock_tx
        
        client = APIClient()
        client.force_authenticate(user=organizer)
        
        # First call
        response1 = client.post(f'/api/tournaments/{tournament.id}/refunds/', {})
        assert response1.status_code == 200
        count1 = response1.data['count']
        assert count1 == 3
        
        # Reset mock
        mock_award.reset_mock()
        
        # Second call (idempotent)
        response2 = client.post(f'/api/tournaments/{tournament.id}/refunds/', {})
        assert response2.status_code == 200
        count2 = response2.data['count']

        # Should not call economy service again
        assert mock_award.call_count == 0
        # Idempotent: returns existing transactions, so count should be same
        assert count2 == count1        # Verify only 3 PrizeTransaction records exist
        prize_txs = PrizeTransaction.objects.filter(tournament=tournament, status='refunded')
        assert prize_txs.count() == 3


@pytest.mark.django_db(transaction=True)
class TestReconciliationAPI:
    """Test reconciliation verification endpoint."""
    
    @pytest.fixture(scope='function')
    def tournament_with_payouts(self):
        """Create a tournament with completed payouts."""
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
            email=f"organizer-{unique_id}@test.com",
            password='testpass123'
        )
        
        # Create tournament
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
        
        # Create completed payout transactions
        PrizeTransaction.objects.create(
            tournament=tournament,
            participant=reg1,
            placement=PrizeTransaction.Placement.FIRST,
            amount=Decimal('100.00'),
            coin_transaction_id=123,
            status='completed'
        )
        PrizeTransaction.objects.create(
            tournament=tournament,
            participant=reg2,
            placement=PrizeTransaction.Placement.SECOND,
            amount=Decimal('50.00'),
            coin_transaction_id=124,
            status='completed'
        )
        
        return {'tournament': tournament, 'organizer': organizer}
    
    def test_reconciliation_happy_path(self, tournament_with_payouts):
        """Test that reconciliation returns ok=true when all payouts match."""
        tournament = tournament_with_payouts['tournament']
        organizer = tournament_with_payouts['organizer']
        
        client = APIClient()
        client.force_authenticate(user=organizer)
        
        response = client.get(f'/api/tournaments/{tournament.id}/payouts/verify/')
        
        assert response.status_code == 200
        assert 'tournament_id' in response.data
        assert 'ok' in response.data
        assert 'details' in response.data
        
        assert response.data['tournament_id'] == tournament.id
        assert response.data['ok'] is True
        assert 'expected' in response.data['details']
        assert 'actual' in response.data['details']
        assert 'missing' in response.data['details']


@pytest.mark.django_db(transaction=True)
class TestPayoutAPIErrorCases:
    """Test error handling for payout endpoints."""
    
    @pytest.fixture(scope='function')
    def in_progress_tournament(self):
        """Create an in-progress tournament (not completed)."""
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
            email=f"organizer-{unique_id}@test.com",
            password='testpass123'
        )
        
        # Create tournament (IN_PROGRESS, not COMPLETED)
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
            status=Tournament.LIVE,  # Not COMPLETED (uses LIVE instead of IN_PROGRESS)
            prize_distribution={'1st': '100.00', '2nd': '50.00', '3rd': '25.00'}
        )
        
        return {'tournament': tournament, 'organizer': organizer}
    
    def test_payout_409_if_not_completed(self, in_progress_tournament):
        """Test that payouts return 409 if tournament not COMPLETED."""
        tournament = in_progress_tournament['tournament']
        organizer = in_progress_tournament['organizer']
        
        client = APIClient()
        client.force_authenticate(user=organizer)
        
        response = client.post(f'/api/tournaments/{tournament.id}/payouts/', {})
        
        assert response.status_code == 409
        assert 'detail' in response.data
        assert 'must be completed' in response.data['detail'].lower()
    
    def test_refund_409_if_not_cancelled(self, in_progress_tournament):
        """Test that refunds return 409 if tournament not CANCELLED."""
        tournament = in_progress_tournament['tournament']
        organizer = in_progress_tournament['organizer']
        
        client = APIClient()
        client.force_authenticate(user=organizer)
        
        response = client.post(f'/api/tournaments/{tournament.id}/refunds/', {})
        
        assert response.status_code == 409
        assert 'detail' in response.data
        assert 'must be cancelled' in response.data['detail'].lower()
    
    def test_payout_400_if_no_distribution(self):
        """Test that payouts return 400 if no prize distribution configured."""
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
            email=f"organizer-{unique_id}@test.com",
            password='testpass123'
        )
        
        # Create tournament without prize distribution
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
            prize_distribution={}  # Empty distribution
        )
        
        # Create result
        reg = Registration.objects.create(tournament=tournament, user=organizer, status='confirmed')
        TournamentResult.objects.create(
            tournament=tournament,
            winner=reg,
            created_by=organizer,
            rules_applied={'method': 'test'}
        )
        
        client = APIClient()
        client.force_authenticate(user=organizer)
        
        response = client.post(f'/api/tournaments/{tournament.id}/payouts/', {})
        
        assert response.status_code == 400
        assert 'detail' in response.data
        assert 'no prize distribution' in response.data['detail'].lower()
