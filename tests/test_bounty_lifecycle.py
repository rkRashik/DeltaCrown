"""
UP-PHASE2E: Bounty Lifecycle Tests (Match Progression, Proof, Disputes)

Full lifecycle testing:
    1. Create → Accept → Start → Submit Proof → Confirm → Escrow Release
    2. Dispute handling and moderator resolution
    3. Wallet safety (escrow freeze, payout calculations)
    4. Permission enforcement (only participants can act)
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.user_profile.models import UserProfile, Bounty, BountyStatus, BountyProof, BountyDispute
from apps.economy.models import DeltaCrownWallet
from apps.user_profile.services import bounty_service

User = get_user_model()


class BountyLifecycleTestCase(TestCase):
    """Test complete bounty lifecycle from creation to completion"""
    
    def setUp(self):
        """Create test users with wallets and a test game"""
        self.client = Client()
        
        # Create users
        self.creator = User.objects.create_user(
            username='bounty_creator',
            email='creator@test.com',
            password='testpass123'
        )
        self.acceptor = User.objects.create_user(
            username='bounty_acceptor',
            email='acceptor@test.com',
            password='testpass123'
        )
        self.outsider = User.objects.create_user(
            username='outsider',
            email='outsider@test.com',
            password='testpass123'
        )
        
        # Create profiles
        self.creator_profile = UserProfile.objects.get(user=self.creator)
        self.acceptor_profile = UserProfile.objects.get(user=self.acceptor)
        self.outsider_profile = UserProfile.objects.get(user=self.outsider)
        
        # Fund wallets
        self.creator_wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=self.creator_profile)
        self.acceptor_wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=self.acceptor_profile)
        
        self.creator_wallet.cached_balance = 1000
        self.creator_wallet.save()
        
        self.acceptor_wallet.cached_balance = 1000
        self.acceptor_wallet.save()
        
        # Create a test game
        from apps.game_passport.models import Game, GameStatus
        self.game = Game.objects.create(
            name="Valorant",
            slug="valorant",
            display_name="VALORANT",
            status=GameStatus.ACTIVE
        )
    
    def test_full_bounty_lifecycle_success(self):
        """Test complete happy path: create → accept → start → proof → confirm → escrow release"""
        
        # Step 1: Create bounty
        self.client.login(username='bounty_creator', password='testpass123')
        response = self.client.post(
            reverse('create_bounty'),
            data={
                'title': '1v1 Aim Duel',
                'game_id': self.game.id,
                'description': 'First to 10 kills wins',
                'stake_amount': 500,
                'expires_in_hours': 24,
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        bounty_id = data['bounty_id']
        
        # Verify escrow locked
        self.creator_wallet.refresh_from_db()
        self.assertEqual(self.creator_wallet.cached_balance, 500)  # 1000 - 500 stake
        self.assertEqual(self.creator_wallet.pending_balance, 500)  # 500 locked
        
        # Step 2: Accept bounty
        self.client.login(username='bounty_acceptor', password='testpass123')
        response = self.client.post(reverse('accept_bounty', args=[bounty_id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        bounty = Bounty.objects.get(pk=bounty_id)
        self.assertEqual(bounty.status, BountyStatus.ACCEPTED)
        self.assertEqual(bounty.acceptor, self.acceptor)
        
        # Step 3: Start match
        response = self.client.post(reverse('start_match', args=[bounty_id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        bounty.refresh_from_db()
        self.assertEqual(bounty.status, BountyStatus.IN_PROGRESS)
        self.assertIsNotNone(bounty.started_at)
        
        # Step 4: Submit proof (acceptor won)
        response = self.client.post(
            reverse('submit_proof', args=[bounty_id]),
            data={
                'claimed_winner_id': self.acceptor.id,
                'proof_url': 'https://imgur.com/scoreboard.png',
                'proof_type': 'screenshot',
                'description': 'Final scoreboard showing 10-3 victory',
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        bounty.refresh_from_db()
        self.assertEqual(bounty.status, BountyStatus.PENDING_RESULT)
        self.assertEqual(bounty.winner, self.acceptor)
        
        # Verify proof created
        proof = BountyProof.objects.get(bounty=bounty)
        self.assertEqual(proof.submitted_by, self.acceptor)
        self.assertEqual(proof.claimed_winner, self.acceptor)
        self.assertEqual(proof.proof_url, 'https://imgur.com/scoreboard.png')
        
        # Step 5: Confirm result (creator confirms)
        self.client.login(username='bounty_creator', password='testpass123')
        response = self.client.post(reverse('confirm_result', args=[bounty_id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        bounty.refresh_from_db()
        self.assertEqual(bounty.status, BountyStatus.COMPLETED)
        
        # Step 6: Verify escrow released and winner paid
        self.creator_wallet.refresh_from_db()
        self.acceptor_wallet.refresh_from_db()
        
        # Creator's pending balance should be 0 (escrow released)
        self.assertEqual(self.creator_wallet.pending_balance, 0)
        
        # Acceptor should receive 95% of stake (500 * 0.95 = 475)
        expected_payout = 475
        self.assertEqual(self.acceptor_wallet.cached_balance, 1000 + expected_payout)
        
        # Verify bounty payout metadata
        self.assertEqual(bounty.payout_amount, expected_payout)
        self.assertEqual(bounty.platform_fee, 25)  # 5% of 500
    
    def test_start_match_only_participants(self):
        """Test that only participants (creator/acceptor) can start match"""
        
        # Create and accept bounty
        bounty = bounty_service.create_bounty(
            creator=self.creator,
            title='Test Bounty',
            game_id=self.game.id,
            stake_amount=100,
            expires_in_hours=24
        )
        bounty_service.accept_bounty(bounty.id, self.acceptor)
        
        # Try to start as outsider
        self.client.login(username='outsider', password='testpass123')
        response = self.client.post(reverse('start_match', args=[bounty.id]))
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('Only participants', data['error'])
    
    def test_submit_proof_only_participants(self):
        """Test that only participants can submit proof"""
        
        # Create, accept, and start bounty
        bounty = bounty_service.create_bounty(
            creator=self.creator,
            title='Test Bounty',
            game_id=self.game.id,
            stake_amount=100,
            expires_in_hours=24
        )
        bounty_service.accept_bounty(bounty.id, self.acceptor)
        bounty_service.start_match(bounty.id, self.creator)
        
        # Try to submit proof as outsider
        self.client.login(username='outsider', password='testpass123')
        response = self.client.post(
            reverse('submit_proof', args=[bounty.id]),
            data={
                'claimed_winner_id': self.creator.id,
                'proof_url': 'https://imgur.com/fake.png',
                'proof_type': 'screenshot',
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
    
    def test_dispute_freezes_escrow(self):
        """Test that raising a dispute freezes escrow until resolution"""
        
        # Create bounty and progress to PENDING_RESULT
        bounty = bounty_service.create_bounty(
            creator=self.creator,
            title='Disputed Match',
            game_id=self.game.id,
            stake_amount=500,
            expires_in_hours=24
        )
        bounty_service.accept_bounty(bounty.id, self.acceptor)
        bounty_service.start_match(bounty.id, self.creator)
        bounty_service.submit_result(
            bounty_id=bounty.id,
            submitted_by=self.acceptor,
            claimed_winner=self.acceptor,
            proof_url='https://imgur.com/disputed.png',
            proof_type='screenshot'
        )
        
        # Verify initial pending balance
        self.creator_wallet.refresh_from_db()
        initial_pending = self.creator_wallet.pending_balance
        self.assertEqual(initial_pending, 500)
        
        # Raise dispute
        self.client.login(username='bounty_creator', password='testpass123')
        response = self.client.post(
            reverse('raise_dispute', args=[bounty.id]),
            data={
                'reason': 'The screenshot is doctored. I have video proof showing the real score was different. This is clearly fraudulent.'
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        bounty.refresh_from_db()
        self.assertEqual(bounty.status, BountyStatus.DISPUTED)
        
        # Verify escrow still frozen
        self.creator_wallet.refresh_from_db()
        self.acceptor_wallet.refresh_from_db()
        self.assertEqual(self.creator_wallet.pending_balance, 500)  # Still locked
        self.assertEqual(self.acceptor_wallet.cached_balance, 1000)  # No payout yet
        
        # Verify dispute created
        dispute = BountyDispute.objects.get(bounty=bounty)
        self.assertEqual(dispute.disputer, self.creator)
        self.assertIn('doctored', dispute.reason)
    
    def test_dispute_reason_validation(self):
        """Test that dispute reason must be at least 50 characters"""
        
        # Create bounty and progress to PENDING_RESULT
        bounty = bounty_service.create_bounty(
            creator=self.creator,
            title='Test',
            game_id=self.game.id,
            stake_amount=100,
            expires_in_hours=24
        )
        bounty_service.accept_bounty(bounty.id, self.acceptor)
        bounty_service.start_match(bounty.id, self.creator)
        bounty_service.submit_result(
            bounty_id=bounty.id,
            submitted_by=self.acceptor,
            claimed_winner=self.acceptor,
            proof_url='https://imgur.com/test.png',
            proof_type='screenshot'
        )
        
        # Try to dispute with short reason
        self.client.login(username='bounty_creator', password='testpass123')
        response = self.client.post(
            reverse('raise_dispute', args=[bounty.id]),
            data={'reason': 'Too short'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('at least 50 characters', data['error'])
    
    def test_dispute_window_enforcement(self):
        """Test that disputes can only be raised within 24-hour window"""
        
        # Create bounty and progress to PENDING_RESULT
        bounty = bounty_service.create_bounty(
            creator=self.creator,
            title='Test',
            game_id=self.game.id,
            stake_amount=100,
            expires_in_hours=24
        )
        bounty_service.accept_bounty(bounty.id, self.acceptor)
        bounty_service.start_match(bounty.id, self.creator)
        bounty_service.submit_result(
            bounty_id=bounty.id,
            submitted_by=self.acceptor,
            claimed_winner=self.acceptor,
            proof_url='https://imgur.com/test.png',
            proof_type='screenshot'
        )
        
        # Manually expire dispute window (simulate 25 hours passed)
        bounty.result_submitted_at = timezone.now() - timedelta(hours=25)
        bounty.save(update_fields=['result_submitted_at'])
        
        # Try to dispute after window expired
        self.client.login(username='bounty_creator', password='testpass123')
        response = self.client.post(
            reverse('raise_dispute', args=[bounty.id]),
            data={'reason': 'This is a long reason that meets the 50 character minimum requirement for disputes'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Dispute window expired', data['error'])
    
    def test_auto_complete_after_dispute_window(self):
        """Test that bounty auto-completes after 24-hour dispute window if no dispute"""
        
        # Create bounty and progress to PENDING_RESULT
        bounty = bounty_service.create_bounty(
            creator=self.creator,
            title='Auto Complete Test',
            game_id=self.game.id,
            stake_amount=500,
            expires_in_hours=24
        )
        bounty_service.accept_bounty(bounty.id, self.acceptor)
        bounty_service.start_match(bounty.id, self.creator)
        bounty_service.submit_result(
            bounty_id=bounty.id,
            submitted_by=self.acceptor,
            claimed_winner=self.acceptor,
            proof_url='https://imgur.com/test.png',
            proof_type='screenshot'
        )
        
        # Simulate 25 hours passed (beyond dispute window)
        bounty.result_submitted_at = timezone.now() - timedelta(hours=25)
        bounty.save(update_fields=['result_submitted_at'])
        
        # Call complete_bounty (simulating auto-complete cron job)
        bounty_service.complete_bounty(bounty.id)
        
        bounty.refresh_from_db()
        self.assertEqual(bounty.status, BountyStatus.COMPLETED)
        
        # Verify winner paid
        self.acceptor_wallet.refresh_from_db()
        self.assertEqual(self.acceptor_wallet.cached_balance, 1000 + 475)  # 95% of 500
    
    def test_unauthorized_confirm_blocked(self):
        """Test that non-creator cannot confirm result"""
        
        # Create bounty and progress to PENDING_RESULT
        bounty = bounty_service.create_bounty(
            creator=self.creator,
            title='Test',
            game_id=self.game.id,
            stake_amount=100,
            expires_in_hours=24
        )
        bounty_service.accept_bounty(bounty.id, self.acceptor)
        bounty_service.start_match(bounty.id, self.creator)
        bounty_service.submit_result(
            bounty_id=bounty.id,
            submitted_by=self.acceptor,
            claimed_winner=self.acceptor,
            proof_url='https://imgur.com/test.png',
            proof_type='screenshot'
        )
        
        # Try to confirm as outsider
        self.client.login(username='outsider', password='testpass123')
        response = self.client.post(reverse('confirm_result', args=[bounty.id]))
        
        # Service layer should block this
        # Note: View layer currently doesn't check, but service layer does
        self.assertEqual(response.status_code, 400)  # ValidationError from service
    
    def test_proof_url_required(self):
        """Test that proof submission requires a valid proof URL"""
        
        # Create bounty and progress to IN_PROGRESS
        bounty = bounty_service.create_bounty(
            creator=self.creator,
            title='Test',
            game_id=self.game.id,
            stake_amount=100,
            expires_in_hours=24
        )
        bounty_service.accept_bounty(bounty.id, self.acceptor)
        bounty_service.start_match(bounty.id, self.creator)
        
        # Try to submit proof without URL
        self.client.login(username='bounty_acceptor', password='testpass123')
        response = self.client.post(
            reverse('submit_proof', args=[bounty.id]),
            data={
                'claimed_winner_id': self.acceptor.id,
                'proof_url': '',  # Empty
                'proof_type': 'screenshot',
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Proof URL is required', data['error'])
    
    def test_cannot_start_already_started_match(self):
        """Test that match cannot be started twice"""
        
        # Create, accept, and start bounty
        bounty = bounty_service.create_bounty(
            creator=self.creator,
            title='Test',
            game_id=self.game.id,
            stake_amount=100,
            expires_in_hours=24
        )
        bounty_service.accept_bounty(bounty.id, self.acceptor)
        bounty_service.start_match(bounty.id, self.creator)
        
        # Try to start again
        self.client.login(username='bounty_acceptor', password='testpass123')
        response = self.client.post(reverse('start_match', args=[bounty.id]))
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Cannot start match', data['error'])
    
    def test_platform_fee_calculation(self):
        """Test that platform fee is correctly calculated (5% of stake)"""
        
        # Create bounty with various stakes
        stakes = [100, 500, 1000]
        
        for stake in stakes:
            # Reset wallets
            self.creator_wallet.cached_balance = 2000
            self.creator_wallet.pending_balance = 0
            self.creator_wallet.save()
            
            self.acceptor_wallet.cached_balance = 2000
            self.acceptor_wallet.pending_balance = 0
            self.acceptor_wallet.save()
            
            # Create and complete bounty
            bounty = bounty_service.create_bounty(
                creator=self.creator,
                title=f'Test {stake}',
                game_id=self.game.id,
                stake_amount=stake,
                expires_in_hours=24
            )
            bounty_service.accept_bounty(bounty.id, self.acceptor)
            bounty_service.start_match(bounty.id, self.creator)
            bounty_service.submit_result(
                bounty_id=bounty.id,
                submitted_by=self.acceptor,
                claimed_winner=self.acceptor,
                proof_url='https://imgur.com/test.png',
                proof_type='screenshot'
            )
            bounty_service.complete_bounty(bounty.id)
            
            bounty.refresh_from_db()
            expected_payout = int(stake * 0.95)
            expected_fee = stake - expected_payout
            
            self.assertEqual(bounty.payout_amount, expected_payout)
            self.assertEqual(bounty.platform_fee, expected_fee)
            
            # Verify winner balance
            self.acceptor_wallet.refresh_from_db()
            self.assertEqual(self.acceptor_wallet.cached_balance, 2000 + expected_payout)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
