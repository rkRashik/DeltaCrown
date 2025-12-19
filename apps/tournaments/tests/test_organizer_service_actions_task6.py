"""
Tests for DisputeService and additional MatchService/PaymentService organizer actions.

Phase 0 Refactor: Tests for ORM mutations moved from organizer views to service layer (Task #6).
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from decimal import Decimal

from apps.tournaments.models import Tournament, Game, Match, Bracket, Payment, Registration
from apps.tournaments.models.match import Dispute
from apps.tournaments.services.dispute_service import DisputeService
from apps.tournaments.services.match_service import MatchService
from apps.tournaments.services.payment_service import PaymentService

User = get_user_model()

# Print DB config at module load
print(f"\n{'='*60}")
print(f"TEST DATABASE CONFIGURATION")
print(f"{'='*60}")
import os
from django.conf import settings
if os.environ.get('USE_LOCAL_TEST_DB', 'false').lower() == 'true':
    db_config = settings.DATABASES['default']
    print(f"✓ Using LOCAL test database")
    print(f"  Database: {db_config['NAME']}")
    print(f"  Host: {db_config['HOST']}")
    print(f"  User: {db_config['USER']}")
else:
    print(f"⚠ Using DATABASE_URL (Neon) - may fail if user can't create test DB")
    print(f"  To use local: set USE_LOCAL_TEST_DB=true")
print(f"{'='*60}\n")


@pytest.fixture
def game(db):
    """Create a test game."""
    return Game.objects.create(
        name='Test Game',
        slug='test-game',
        default_team_size=5,
        profile_id_field='riot_id',
        default_result_type='map_score'
    )


@pytest.fixture
def organizer_user(db):
    """Create an organizer user."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@example.com',
        password='testpass123',
        is_staff=False
    )


@pytest.fixture
def tournament(db, game, organizer_user):
    """Create a test tournament."""
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        game=game,
        organizer=organizer_user,
        max_teams=16,
        registration_start=timezone.now() - timedelta(days=2),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=14),
        tournament_end=timezone.now() + timedelta(days=15),
        status='upcoming'
    )


@pytest.fixture
def bracket(db, tournament):
    """Create a test bracket."""
    return Bracket.objects.create(
        tournament=tournament,
        name='Main Bracket',
        bracket_type='single_elimination',
        size=8,
        current_round=1
    )


@pytest.fixture
def match(db, tournament, bracket):
    """Create a match."""
    return Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        state='live',
        participant1_id=101,
        participant1_name='Team A',
        participant2_id=102,
        participant2_name='Team B',
        score1=0,
        score2=0
    )


@pytest.fixture
def dispute(db, match):
    """Create a dispute."""
    return Dispute.objects.create(
        match=match,
        initiated_by_id=101,
        reason='wrong_score',
        description='Score reported incorrectly',
        status='open'
    )


@pytest.mark.django_db
class TestDisputeService:
    """Test DisputeService organizer actions"""
    
    def test_update_status_changes_dispute_status(self, dispute):
        """Test updating dispute status"""
        assert dispute.status == 'open'
        
        DisputeService.organizer_update_status(dispute, 'under_review')
        
        dispute.refresh_from_db()
        assert dispute.status == 'under_review'
    
    def test_resolve_sets_resolution_details(self, dispute, organizer_user):
        """Test resolving dispute with notes"""
        DisputeService.organizer_resolve(
            dispute,
            'Reviewed evidence, score stands',
            organizer_user
        )
        
        dispute.refresh_from_db()
        assert dispute.status == 'resolved'
        assert dispute.resolution_notes == 'Reviewed evidence, score stands'
        assert dispute.resolved_by == organizer_user
        assert dispute.resolved_at is not None


@pytest.mark.django_db
class TestMatchServiceSubmitScore:
    """Test MatchService.organizer_submit_score()"""
    
    def test_submit_score_sets_scores_and_winner(self, match):
        """Test submitting score completes match"""
        MatchService.organizer_submit_score(match, 10, 5)
        
        match.refresh_from_db()
        assert match.score1 == 10
        assert match.score2 == 5
        assert match.winner_id == match.participant1_id
        assert match.loser_id == match.participant2_id
        assert match.state == 'completed'
    
    def test_submit_score_rejects_tied_scores(self, match):
        """Test tied scores are rejected"""
        with pytest.raises(ValidationError, match='tied'):
            MatchService.organizer_submit_score(match, 5, 5)


@pytest.mark.django_db
class TestPaymentServiceOrganizerActions:
    """Test PaymentService organizer actions"""
    
    def test_bulk_verify_updates_multiple_payments(self, tournament, organizer_user, db):
        """Test bulk verifying payments"""
        # Create test registrations and payments
        user1 = User.objects.create_user(username='user1', password='pass')
        user2 = User.objects.create_user(username='user2', password='pass')
        
        reg1 = Registration.objects.create(tournament=tournament, user=user1, status='pending')
        reg2 = Registration.objects.create(tournament=tournament, user=user2, status='pending')
        
        payment1 = Payment.objects.create(registration=reg1, amount=Decimal('10.00'), status='submitted')
        payment2 = Payment.objects.create(registration=reg2, amount=Decimal('10.00'), status='submitted')
        
        updated = PaymentService.organizer_bulk_verify(
            [payment1.id, payment2.id],
            tournament,
            organizer_user
        )
        
        assert updated == 2
        payment1.refresh_from_db()
        payment2.refresh_from_db()
        assert payment1.status == 'verified'
        assert payment2.status == 'verified'
    
    def test_process_refund_stores_metadata_and_updates_status(self, tournament, organizer_user, db):
        """Test processing refund"""
        user = User.objects.create_user(username='user3', password='pass')
        reg = Registration.objects.create(tournament=tournament, user=user, status='confirmed')
        payment = Payment.objects.create(registration=reg, amount=Decimal('20.00'), status='verified')
        
        PaymentService.organizer_process_refund(
            payment,
            Decimal('20.00'),
            'Tournament cancelled',
            'manual',
            organizer_user.username
        )
        
        payment.refresh_from_db()
        assert payment.status == 'refunded'
        assert 'refund' in payment.metadata
        assert payment.metadata['refund']['reason'] == 'Tournament cancelled'
        assert payment.metadata['refund']['amount'] == '20.00'
