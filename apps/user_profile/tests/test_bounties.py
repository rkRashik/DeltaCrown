# apps/user_profile/tests/test_bounties.py
"""
Test suite for Bounty System (P0 Feature).

Tests:
- Bounty creation with escrow locking
- Acceptance and participant verification
- Result submission and proof tracking
- Dispute management
- Expiry automation and refunds
- Economy integration (idempotent transactions)
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from datetime import timedelta

from apps.user_profile.models import (
    Bounty,
    BountyAcceptance,
    BountyProof,
    BountyDispute,
    BountyStatus,
    DisputeStatus,
)
from apps.user_profile.services import bounty_service
from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.core.models import Game

User = get_user_model()


# ============================================================================
# BOUNTY CREATION & ESCROW TESTS
# ============================================================================

@pytest.mark.django_db
class TestBountyCreation:
    """Test bounty creation with escrow locking."""
    
    def test_create_bounty_locks_escrow(self):
        """Creating bounty locks stake in pending_balance."""
        user = User.objects.create_user(username='player1', password='test123')
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        # Fund wallet
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=user.profile)
        wallet.cached_balance = 1000
        wallet.save()
        
        # Create bounty
        bounty = bounty_service.create_bounty(
            creator=user,
            title='1v1 Aim Duel',
            game=game,
            stake_amount=500,
        )
        
        assert bounty.id
        assert bounty.status == BountyStatus.OPEN
        assert bounty.stake_amount == 500
        
        # Check escrow lock
        wallet.refresh_from_db()
        assert wallet.cached_balance == 500  # Debited
        assert wallet.pending_balance == 500  # Locked
        assert wallet.available_balance == 0  # cached - pending
        
        # Check transaction
        tx = DeltaCrownTransaction.objects.get(reason='BOUNTY_ESCROW')
        assert tx.amount == -500
    
    def test_create_bounty_insufficient_funds(self):
        """Creating bounty fails if insufficient balance."""
        user = User.objects.create_user(username='player1', password='test123')
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        # Wallet with insufficient funds
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=user.profile)
        wallet.cached_balance = 100
        wallet.save()
        
        # Try to create 500 DC bounty
        with pytest.raises(PermissionDenied) as exc_info:
            bounty_service.create_bounty(
                creator=user,
                title='1v1 Aim Duel',
                game=game,
                stake_amount=500,
            )
        
        assert 'insufficient funds' in str(exc_info.value).lower()
    
    def test_create_bounty_minimum_stake(self):
        """Bounty requires minimum 100 DC stake."""
        user = User.objects.create_user(username='player1', password='test123')
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        with pytest.raises(ValidationError) as exc_info:
            bounty_service.create_bounty(
                creator=user,
                title='1v1 Aim Duel',
                game=game,
                stake_amount=50,  # Below minimum
            )
        
        assert 'minimum stake' in str(exc_info.value).lower()
    
    def test_create_bounty_rate_limit(self):
        """User limited to 10 bounties per 24 hours."""
        user = User.objects.create_user(username='player1', password='test123')
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        # Fund wallet generously
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=user.profile)
        wallet.cached_balance = 100000
        wallet.save()
        
        # Create 10 bounties
        for i in range(10):
            bounty_service.create_bounty(
                creator=user,
                title=f'Bounty {i}',
                game=game,
                stake_amount=100,
                expires_in_hours=1,  # Short expiry for testing
            )
        
        # 11th bounty should fail
        with pytest.raises(PermissionDenied) as exc_info:
            bounty_service.create_bounty(
                creator=user,
                title='Bounty 11',
                game=game,
                stake_amount=100,
            )
        
        assert 'rate limit' in str(exc_info.value).lower()


# ============================================================================
# BOUNTY ACCEPTANCE TESTS
# ============================================================================

@pytest.mark.django_db
class TestBountyAcceptance:
    """Test bounty acceptance."""
    
    def test_accept_open_bounty(self):
        """User can accept open bounty."""
        creator = User.objects.create_user(username='creator', password='test123')
        acceptor = User.objects.create_user(username='acceptor', password='test123')
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        # Fund creator
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=creator.profile)
        wallet.cached_balance = 1000
        wallet.save()
        
        # Create bounty
        bounty = bounty_service.create_bounty(
            creator=creator,
            title='1v1 Aim Duel',
            game=game,
            stake_amount=500,
        )
        
        # Accept bounty
        acceptance = bounty_service.accept_bounty(
            bounty_id=bounty.id,
            acceptor=acceptor,
        )
        
        assert acceptance.acceptor == acceptor
        
        # Check bounty updated
        bounty.refresh_from_db()
        assert bounty.status == BountyStatus.ACCEPTED
        assert bounty.acceptor == acceptor
        assert bounty.expires_at is None  # No longer applicable
    
    def test_cannot_accept_own_bounty(self):
        """Creator cannot accept their own bounty."""
        creator = User.objects.create_user(username='creator', password='test123')
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        # Fund creator
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=creator.profile)
        wallet.cached_balance = 1000
        wallet.save()
        
        # Create bounty
        bounty = bounty_service.create_bounty(
            creator=creator,
            title='1v1 Aim Duel',
            game=game,
            stake_amount=500,
        )
        
        # Try to accept own bounty
        with pytest.raises(PermissionDenied) as exc_info:
            bounty_service.accept_bounty(
                bounty_id=bounty.id,
                acceptor=creator,  # Same as creator
            )
        
        assert 'your own' in str(exc_info.value).lower()
    
    def test_cannot_accept_expired_bounty(self):
        """Cannot accept expired bounty."""
        creator = User.objects.create_user(username='creator', password='test123')
        acceptor = User.objects.create_user(username='acceptor', password='test123')
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        # Fund creator
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=creator.profile)
        wallet.cached_balance = 1000
        wallet.save()
        
        # Create bounty with past expiry
        bounty = bounty_service.create_bounty(
            creator=creator,
            title='1v1 Aim Duel',
            game=game,
            stake_amount=500,
            expires_in_hours=1,
        )
        
        # Manually set expiry to past
        bounty.expires_at = timezone.now() - timedelta(hours=2)
        bounty.save()
        
        # Try to accept expired bounty
        with pytest.raises(ValidationError) as exc_info:
            bounty_service.accept_bounty(
                bounty_id=bounty.id,
                acceptor=acceptor,
            )
        
        assert 'expired' in str(exc_info.value).lower()


# ============================================================================
# BOUNTY COMPLETION & PAYOUT TESTS
# ============================================================================

@pytest.mark.django_db
class TestBountyCompletion:
    """Test bounty completion and payout."""
    
    def test_complete_bounty_pays_winner(self):
        """Completing bounty pays winner 95%, platform keeps 5%."""
        creator = User.objects.create_user(username='creator', password='test123')
        acceptor = User.objects.create_user(username='acceptor', password='test123')
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        # Fund creator
        wallet_creator, _ = DeltaCrownWallet.objects.get_or_create(profile=creator.profile)
        wallet_creator.cached_balance = 1000
        wallet_creator.save()
        
        # Create bounty
        bounty = bounty_service.create_bounty(
            creator=creator,
            title='1v1 Aim Duel',
            game=game,
            stake_amount=500,
        )
        
        # Accept bounty
        bounty_service.accept_bounty(bounty_id=bounty.id, acceptor=acceptor)
        
        # Start match
        bounty_service.start_match(bounty_id=bounty.id, started_by=creator)
        
        # Submit result
        bounty_service.submit_result(
            bounty_id=bounty.id,
            submitted_by=creator,
            claimed_winner=acceptor,
            proof_url='https://imgur.com/proof123',
        )
        
        # Set result submission to 25 hours ago (past dispute window)
        bounty.refresh_from_db()
        bounty.result_submitted_at = timezone.now() - timedelta(hours=25)
        bounty.save()
        
        # Complete bounty
        completed = bounty_service.complete_bounty(bounty_id=bounty.id)
        
        assert completed.status == BountyStatus.COMPLETED
        assert completed.winner == acceptor
        assert completed.payout_amount == 475  # 95% of 500
        assert completed.platform_fee == 25  # 5% of 500
        
        # Check winner wallet
        wallet_acceptor, _ = DeltaCrownWallet.objects.get_or_create(profile=acceptor.profile)
        assert wallet_acceptor.cached_balance == 475
        
        # Check creator escrow released
        wallet_creator.refresh_from_db()
        assert wallet_creator.pending_balance == 0
        
        # Check transactions
        win_tx = DeltaCrownTransaction.objects.get(reason='BOUNTY_WIN')
        assert win_tx.amount == 475


# ============================================================================
# EXPIRY & REFUND TESTS
# ============================================================================

@pytest.mark.django_db
class TestBountyExpiry:
    """Test bounty expiry and refunds."""
    
    def test_expire_bounty_refunds_creator(self):
        """Expiring bounty refunds creator 100%."""
        creator = User.objects.create_user(username='creator', password='test123')
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        # Fund creator
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=creator.profile)
        wallet.cached_balance = 1000
        wallet.save()
        
        # Create bounty
        bounty = bounty_service.create_bounty(
            creator=creator,
            title='1v1 Aim Duel',
            game=game,
            stake_amount=500,
            expires_in_hours=1,
        )
        
        # Check escrow locked
        wallet.refresh_from_db()
        assert wallet.pending_balance == 500
        assert wallet.available_balance == 0
        
        # Manually expire
        bounty.expires_at = timezone.now() - timedelta(hours=2)
        bounty.save()
        
        # Expire bounty
        expired = bounty_service.expire_bounty(bounty_id=bounty.id)
        
        assert expired.status == BountyStatus.EXPIRED
        
        # Check refund
        wallet.refresh_from_db()
        assert wallet.pending_balance == 0  # Escrow released
        assert wallet.cached_balance == 1000  # Full refund
        
        # Check transaction
        refund_tx = DeltaCrownTransaction.objects.get(reason='BOUNTY_REFUND')
        assert refund_tx.amount == 500
    
    def test_cancel_bounty_refunds_creator(self):
        """Cancelling open bounty refunds creator."""
        creator = User.objects.create_user(username='creator', password='test123')
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        # Fund creator
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=creator.profile)
        wallet.cached_balance = 1000
        wallet.save()
        
        # Create bounty
        bounty = bounty_service.create_bounty(
            creator=creator,
            title='1v1 Aim Duel',
            game=game,
            stake_amount=500,
        )
        
        # Cancel bounty
        cancelled = bounty_service.cancel_bounty(
            bounty_id=bounty.id,
            cancelled_by=creator,
        )
        
        assert cancelled.status == BountyStatus.CANCELLED
        
        # Check refund
        wallet.refresh_from_db()
        assert wallet.pending_balance == 0
        assert wallet.cached_balance == 1000


# ============================================================================
# DISPUTE TESTS
# ============================================================================

@pytest.mark.django_db
class TestBountyDisputes:
    """Test dispute management."""
    
    def test_raise_dispute(self):
        """Participant can dispute result within 24 hours."""
        creator = User.objects.create_user(username='creator', password='test123')
        acceptor = User.objects.create_user(username='acceptor', password='test123')
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        # Fund creator
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=creator.profile)
        wallet.cached_balance = 1000
        wallet.save()
        
        # Create, accept, start, submit result
        bounty = bounty_service.create_bounty(
            creator=creator,
            title='1v1 Aim Duel',
            game=game,
            stake_amount=500,
        )
        bounty_service.accept_bounty(bounty_id=bounty.id, acceptor=acceptor)
        bounty_service.start_match(bounty_id=bounty.id, started_by=creator)
        bounty_service.submit_result(
            bounty_id=bounty.id,
            submitted_by=creator,
            claimed_winner=creator,
            proof_url='https://imgur.com/proof123',
        )
        
        # Acceptor disputes
        dispute = bounty_service.raise_dispute(
            bounty_id=bounty.id,
            disputer=acceptor,
            reason='Proof is fake, I actually won. Here is my evidence: [link]',
        )
        
        assert dispute.disputer == acceptor
        assert dispute.status == DisputeStatus.OPEN
        
        # Check bounty status
        bounty.refresh_from_db()
        assert bounty.status == BountyStatus.DISPUTED
    
    def test_resolve_dispute_confirm_winner(self):
        """Moderator can resolve dispute by confirming winner."""
        creator = User.objects.create_user(username='creator', password='test123')
        acceptor = User.objects.create_user(username='acceptor', password='test123')
        moderator = User.objects.create_user(username='mod', password='test123', is_staff=True)
        game = Game.objects.create(name='Valorant', slug='valorant')
        
        # Fund creator
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=creator.profile)
        wallet.cached_balance = 1000
        wallet.save()
        
        # Create, accept, start, submit, dispute
        bounty = bounty_service.create_bounty(
            creator=creator,
            title='1v1 Aim Duel',
            game=game,
            stake_amount=500,
        )
        bounty_service.accept_bounty(bounty_id=bounty.id, acceptor=acceptor)
        bounty_service.start_match(bounty_id=bounty.id, started_by=creator)
        bounty_service.submit_result(
            bounty_id=bounty.id,
            submitted_by=creator,
            claimed_winner=creator,
            proof_url='https://imgur.com/proof123',
        )
        dispute = bounty_service.raise_dispute(
            bounty_id=bounty.id,
            disputer=acceptor,
            reason='Proof is fake, I actually won. Here is my evidence: [link]',
        )
        
        # Moderator resolves (confirm original winner)
        resolved_dispute, resolved_bounty = bounty_service.resolve_dispute(
            dispute_id=dispute.bounty.id,
            moderator=moderator,
            decision='confirm',
            resolution='Proof is valid, creator won fairly',
        )
        
        assert resolved_dispute.is_resolved
        assert resolved_dispute.status == DisputeStatus.RESOLVED_CONFIRM
        assert resolved_bounty.status == BountyStatus.COMPLETED
        assert resolved_bounty.winner == creator
