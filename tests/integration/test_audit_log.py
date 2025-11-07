"""
Integration tests for Module 2.4: Audit Logging

Tests cover:
- AuditLog model creation and retrieval
- audit_event() function with metadata capture
- Payment audit events (verify, reject, refund)
- Bracket audit events (finalize)
- Dispute audit events (resolve, escalate)
- Query helpers (by user, tournament, action)

Phase 2: Real-Time Features & Security
Module 2.4: Security Hardening
"""

import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from apps.tournaments.models import (
    Tournament, Registration, Payment, Bracket, 
    BracketNode, Match, Dispute, Game, AuditLog
)
from apps.tournaments.security.audit import (
    audit_event, AuditAction,
    get_user_audit_trail,
    get_tournament_audit_trail,
    get_action_audit_trail
)
from apps.tournaments.services.registration_service import RegistrationService
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.services.match_service import MatchService

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="adminpass123",
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def game(db):
    """Create a test game."""
    return Game.objects.create(
        name="Test Game",
        slug="test-game",
        platform="PC",
        is_active=True
    )


@pytest.fixture
def tournament(db, game):
    """Create a test tournament."""
    return Tournament.objects.create(
        name="Test Tournament",
        slug="test-tournament",
        game=game,
        status="PUBLISHED",
        max_participants=16,
        registration_start=timezone.now() - timedelta(days=1),
        registration_end=timezone.now() + timedelta(days=7),
        start_date=timezone.now() + timedelta(days=10),
        entry_fee=Decimal("10.00")
    )


@pytest.fixture
def registration(db, tournament, user):
    """Create a test registration."""
    return Registration.objects.create(
        tournament=tournament,
        participant_type="SOLO",
        participant_id=user.id,
        status="PENDING"
    )


@pytest.fixture
def payment(db, registration):
    """Create a test payment."""
    return Payment.objects.create(
        registration=registration,
        amount=Decimal("10.00"),
        payment_method="STRIPE",
        status="PENDING",
        transaction_id="test_txn_123"
    )


@pytest.fixture
def bracket(db, tournament):
    """Create a test bracket."""
    return Bracket.objects.create(
        tournament=tournament,
        bracket_type="SINGLE_ELIMINATION",
        status="DRAFT"
    )


@pytest.fixture
def match(db, tournament, bracket, user):
    """Create a test match."""
    return Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        participant1_type="SOLO",
        participant1_id=user.id,
        status="SCHEDULED"
    )


@pytest.fixture
def dispute(db, match, user):
    """Create a test dispute."""
    return Dispute.objects.create(
        match=match,
        reported_by=user,
        reported_participant_type="SOLO",
        reported_participant_id=user.id,
        claimed_score=10,
        reason="Score mismatch",
        status="PENDING"
    )


# ============================================================================
# AUDITLOG MODEL TESTS
# ============================================================================

@pytest.mark.django_db
def test_audit_log_creation(user):
    """Test that AuditLog entries can be created."""
    log = AuditLog.objects.create(
        user=user,
        action=AuditAction.PAYMENT_VERIFY.value,
        metadata={
            'payment_id': 1,
            'tournament_id': 1,
            'amount': '10.00'
        },
        ip_address='127.0.0.1',
        user_agent='Mozilla/5.0'
    )
    
    assert log.id is not None
    assert log.user == user
    assert log.action == AuditAction.PAYMENT_VERIFY.value
    assert log.metadata['payment_id'] == 1
    assert log.ip_address == '127.0.0.1'
    assert log.timestamp is not None


@pytest.mark.django_db
def test_audit_log_ordering(user):
    """Test that AuditLog entries are ordered by timestamp (newest first)."""
    # Create multiple logs
    log1 = AuditLog.objects.create(
        user=user,
        action=AuditAction.PAYMENT_VERIFY.value,
        metadata={'step': 1}
    )
    
    log2 = AuditLog.objects.create(
        user=user,
        action=AuditAction.PAYMENT_REJECT.value,
        metadata={'step': 2}
    )
    
    log3 = AuditLog.objects.create(
        user=user,
        action=AuditAction.PAYMENT_REFUND.value,
        metadata={'step': 3}
    )
    
    # Query all logs
    logs = AuditLog.objects.all()
    
    # Should be ordered newest first
    assert logs[0].metadata['step'] == 3
    assert logs[1].metadata['step'] == 2
    assert logs[2].metadata['step'] == 1


@pytest.mark.django_db
def test_audit_log_string_representation(user):
    """Test AuditLog __str__ method."""
    log = AuditLog.objects.create(
        user=user,
        action=AuditAction.BRACKET_FINALIZE.value,
        metadata={}
    )
    
    str_repr = str(log)
    assert user.username in str_repr
    assert AuditAction.BRACKET_FINALIZE.value in str_repr


# ============================================================================
# AUDIT_EVENT FUNCTION TESTS
# ============================================================================

@pytest.mark.django_db
def test_audit_event_creates_log(user):
    """Test that audit_event() creates an AuditLog entry."""
    initial_count = AuditLog.objects.count()
    
    audit_event(
        user=user,
        action=AuditAction.PAYMENT_VERIFY,
        meta={
            'payment_id': 123,
            'amount': '25.00'
        }
    )
    
    assert AuditLog.objects.count() == initial_count + 1
    
    log = AuditLog.objects.latest('timestamp')
    assert log.user == user
    assert log.action == AuditAction.PAYMENT_VERIFY.value
    assert log.metadata['payment_id'] == 123
    assert log.metadata['amount'] == '25.00'


@pytest.mark.django_db
def test_audit_event_with_request_captures_ip_and_ua(user):
    """Test that audit_event() captures IP and user agent from request."""
    # Mock request object
    class MockRequest:
        META = {
            'REMOTE_ADDR': '192.168.1.100',
            'HTTP_USER_AGENT': 'TestBrowser/1.0'
        }
    
    request = MockRequest()
    
    audit_event(
        user=user,
        action=AuditAction.BRACKET_REGENERATE,
        meta={'bracket_id': 456},
        request=request
    )
    
    log = AuditLog.objects.latest('timestamp')
    assert log.ip_address == '192.168.1.100'
    assert log.user_agent == 'TestBrowser/1.0'


@pytest.mark.django_db
def test_audit_event_allows_null_user():
    """Test that audit_event() allows system actions (null user)."""
    audit_event(
        user=None,
        action=AuditAction.BRACKET_GENERATE,
        meta={'system': True}
    )
    
    log = AuditLog.objects.latest('timestamp')
    assert log.user is None
    assert log.action == AuditAction.BRACKET_GENERATE.value


# ============================================================================
# PAYMENT AUDIT TESTS
# ============================================================================

@pytest.mark.django_db
def test_verify_payment_creates_audit(payment, admin_user):
    """Test that verify_payment() creates an audit log entry."""
    initial_count = AuditLog.objects.count()
    
    RegistrationService.verify_payment(
        payment_id=payment.id,
        verified_by=admin_user,
        admin_notes="Payment verified successfully"
    )
    
    # Check audit log was created
    assert AuditLog.objects.count() == initial_count + 1
    
    log = AuditLog.objects.filter(action=AuditAction.PAYMENT_VERIFY.value).latest('timestamp')
    assert log.user == admin_user
    assert log.metadata['payment_id'] == payment.id
    assert log.metadata['tournament_id'] == payment.registration.tournament.id
    assert 'admin_notes' in log.metadata


@pytest.mark.django_db
def test_verify_payment_audit_metadata(payment, admin_user):
    """Test that verify_payment() audit includes complete metadata."""
    RegistrationService.verify_payment(
        payment_id=payment.id,
        verified_by=admin_user,
        admin_notes="Verified via bank transfer"
    )
    
    log = AuditLog.objects.filter(action=AuditAction.PAYMENT_VERIFY.value).latest('timestamp')
    metadata = log.metadata
    
    assert metadata['payment_id'] == payment.id
    assert metadata['tournament_id'] == payment.registration.tournament.id
    assert metadata['registration_id'] == payment.registration.id
    assert metadata['participant_type'] == payment.registration.participant_type
    assert metadata['amount'] == str(payment.amount)
    assert metadata['payment_method'] == payment.payment_method
    assert metadata['admin_notes'] == "Verified via bank transfer"


@pytest.mark.django_db
def test_reject_payment_creates_audit(payment, admin_user):
    """Test that reject_payment() creates an audit log entry."""
    initial_count = AuditLog.objects.count()
    
    RegistrationService.reject_payment(
        payment_id=payment.id,
        rejected_by=admin_user,
        reason="Insufficient proof of payment"
    )
    
    assert AuditLog.objects.count() == initial_count + 1
    
    log = AuditLog.objects.filter(action=AuditAction.PAYMENT_REJECT.value).latest('timestamp')
    assert log.user == admin_user
    assert log.metadata['payment_id'] == payment.id
    assert log.metadata['reason'] == "Insufficient proof of payment"


@pytest.mark.django_db
def test_refund_payment_creates_audit(payment, admin_user):
    """Test that refund_payment() creates an audit log entry."""
    # First verify the payment so it can be refunded
    payment.status = 'VERIFIED'
    payment.save()
    
    initial_count = AuditLog.objects.count()
    
    RegistrationService.refund_payment(
        payment_id=payment.id,
        refunded_by=admin_user,
        reason="Tournament cancelled"
    )
    
    assert AuditLog.objects.count() == initial_count + 1
    
    log = AuditLog.objects.filter(action=AuditAction.PAYMENT_REFUND.value).latest('timestamp')
    assert log.user == admin_user
    assert log.metadata['payment_id'] == payment.id
    assert log.metadata['amount'] == str(payment.amount)
    assert log.metadata['reason'] == "Tournament cancelled"


# ============================================================================
# BRACKET AUDIT TESTS
# ============================================================================

@pytest.mark.django_db
def test_finalize_bracket_creates_audit(bracket, admin_user):
    """Test that finalize_bracket() creates an audit log entry."""
    # Create some bracket nodes first
    BracketNode.objects.create(
        bracket=bracket,
        round_number=1,
        position=0,
        node_type="MATCH"
    )
    
    initial_count = AuditLog.objects.count()
    
    BracketService.finalize_bracket(
        bracket_id=bracket.id,
        finalized_by=admin_user
    )
    
    assert AuditLog.objects.count() == initial_count + 1
    
    log = AuditLog.objects.filter(action=AuditAction.BRACKET_FINALIZE.value).latest('timestamp')
    assert log.user == admin_user
    assert log.metadata['bracket_id'] == bracket.id
    assert log.metadata['tournament_id'] == bracket.tournament.id
    assert log.metadata['bracket_type'] == bracket.bracket_type


@pytest.mark.django_db
def test_finalize_bracket_no_audit_without_user(bracket):
    """Test that finalize_bracket() doesn't create audit log if no user provided."""
    initial_count = AuditLog.objects.count()
    
    # Call without finalized_by parameter
    BracketService.finalize_bracket(bracket_id=bracket.id)
    
    # No audit log should be created
    assert AuditLog.objects.count() == initial_count


# ============================================================================
# DISPUTE AUDIT TESTS
# ============================================================================

@pytest.mark.django_db
def test_resolve_dispute_creates_audit(dispute, admin_user):
    """Test that resolve_dispute() creates an audit log entry."""
    initial_count = AuditLog.objects.count()
    
    MatchService.resolve_dispute(
        dispute=dispute,
        resolved_by_id=admin_user.id,
        resolution_notes="Verified with screenshot evidence",
        final_participant1_score=10,
        final_participant2_score=5,
        status="RESOLVED"
    )
    
    assert AuditLog.objects.count() == initial_count + 1
    
    log = AuditLog.objects.filter(action=AuditAction.DISPUTE_RESOLVE.value).latest('timestamp')
    assert log.user == admin_user
    assert log.metadata['dispute_id'] == dispute.id
    assert log.metadata['match_id'] == dispute.match.id
    assert log.metadata['new_status'] == "RESOLVED"


@pytest.mark.django_db
def test_escalate_dispute_creates_correct_audit(dispute, admin_user):
    """Test that escalating a dispute creates DISPUTE_ESCALATE audit."""
    initial_count = AuditLog.objects.count()
    
    MatchService.resolve_dispute(
        dispute=dispute,
        resolved_by_id=admin_user.id,
        resolution_notes="Escalating to tournament organizer",
        final_participant1_score=None,
        final_participant2_score=None,
        status="ESCALATED"
    )
    
    assert AuditLog.objects.count() == initial_count + 1
    
    log = AuditLog.objects.latest('timestamp')
    assert log.action == AuditAction.DISPUTE_ESCALATE.value
    assert log.metadata['new_status'] == "ESCALATED"


# ============================================================================
# QUERY HELPER TESTS
# ============================================================================

@pytest.mark.django_db
def test_get_user_audit_trail(user, admin_user):
    """Test get_user_audit_trail() filters by user correctly."""
    # Create logs for different users
    audit_event(user=user, action=AuditAction.PAYMENT_VERIFY, meta={'test': 1})
    audit_event(user=user, action=AuditAction.PAYMENT_REJECT, meta={'test': 2})
    audit_event(user=admin_user, action=AuditAction.BRACKET_FINALIZE, meta={'test': 3})
    
    # Get user's trail
    trail = get_user_audit_trail(user, limit=100)
    
    assert trail.count() == 2
    assert all(log.user == user for log in trail)


@pytest.mark.django_db
def test_get_tournament_audit_trail(tournament, user):
    """Test get_tournament_audit_trail() filters by tournament."""
    # Create logs with tournament metadata
    audit_event(
        user=user,
        action=AuditAction.PAYMENT_VERIFY,
        meta={'tournament_id': tournament.id, 'test': 1}
    )
    audit_event(
        user=user,
        action=AuditAction.BRACKET_FINALIZE,
        meta={'tournament_id': tournament.id, 'test': 2}
    )
    audit_event(
        user=user,
        action=AuditAction.PAYMENT_VERIFY,
        meta={'tournament_id': 999, 'test': 3}  # Different tournament
    )
    
    # Get tournament's trail
    trail = get_tournament_audit_trail(tournament.id, limit=100)
    
    assert trail.count() == 2
    assert all(log.metadata.get('tournament_id') == tournament.id for log in trail)


@pytest.mark.django_db
def test_get_action_audit_trail(user):
    """Test get_action_audit_trail() filters by action type."""
    # Create logs with different actions
    audit_event(user=user, action=AuditAction.PAYMENT_VERIFY, meta={'test': 1})
    audit_event(user=user, action=AuditAction.PAYMENT_VERIFY, meta={'test': 2})
    audit_event(user=user, action=AuditAction.BRACKET_FINALIZE, meta={'test': 3})
    
    # Get payment verify trail
    trail = get_action_audit_trail(AuditAction.PAYMENT_VERIFY, limit=100)
    
    assert trail.count() == 2
    assert all(log.action == AuditAction.PAYMENT_VERIFY.value for log in trail)


@pytest.mark.django_db
def test_audit_trail_respects_limit(user):
    """Test that audit trail queries respect the limit parameter."""
    # Create 10 logs
    for i in range(10):
        audit_event(user=user, action=AuditAction.PAYMENT_VERIFY, meta={'index': i})
    
    # Query with limit
    trail = get_user_audit_trail(user, limit=5)
    
    assert len(list(trail)) == 5


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.django_db
def test_audit_log_with_empty_metadata(user):
    """Test that audit logs work with empty metadata."""
    audit_event(user=user, action=AuditAction.BRACKET_GENERATE, meta={})
    
    log = AuditLog.objects.latest('timestamp')
    assert log.metadata == {}


@pytest.mark.django_db
def test_audit_log_with_complex_metadata(user):
    """Test that audit logs can store complex nested metadata."""
    complex_meta = {
        'payment_id': 123,
        'tournament': {
            'id': 456,
            'name': 'Test Tournament',
            'participants': [1, 2, 3, 4]
        },
        'scores': {
            'participant1': 10,
            'participant2': 5
        }
    }
    
    audit_event(user=user, action=AuditAction.MATCH_SCORE_UPDATE, meta=complex_meta)
    
    log = AuditLog.objects.latest('timestamp')
    assert log.metadata['tournament']['name'] == 'Test Tournament'
    assert log.metadata['scores']['participant1'] == 10
    assert len(log.metadata['tournament']['participants']) == 4


@pytest.mark.django_db
def test_multiple_concurrent_audit_events(user, admin_user):
    """Test that multiple concurrent audit events don't conflict."""
    initial_count = AuditLog.objects.count()
    
    # Create multiple audit events
    audit_event(user=user, action=AuditAction.PAYMENT_VERIFY, meta={'id': 1})
    audit_event(user=admin_user, action=AuditAction.PAYMENT_REJECT, meta={'id': 2})
    audit_event(user=user, action=AuditAction.BRACKET_FINALIZE, meta={'id': 3})
    
    assert AuditLog.objects.count() == initial_count + 3
    
    # All should be retrievable
    logs = AuditLog.objects.all()[:3]
    ids = [log.metadata.get('id') for log in logs]
    assert set(ids) == {1, 2, 3}
