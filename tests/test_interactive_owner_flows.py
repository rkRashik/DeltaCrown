# tests/test_interactive_owner_flows.py
"""
Tests for Phase 2D Interactive Owner Flows

Tests:
- Bounty creation with sufficient/insufficient wallet
- Bounty acceptance (visitor only, not creator)
- Loadout hardware/config CRUD
- Trophy showcase update
- Unauthorized access prevention
"""

import pytest
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.user_profile.models import (
    Bounty, BountyStatus, HardwareGear, GameConfig,
    TrophyShowcaseConfig, UserBadge, Badge
)
from apps.core.models import Game
from apps.economy.models import DeltaCrownWallet

User = get_user_model()


@pytest.mark.django_db
class TestBountyCreation(TestCase):
    """Test bounty creation with wallet validation."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='creator', password='testpass123')
        self.game = Game.objects.create(name='Valorant', slug='valorant', is_active=True)
        
        # Create wallet
        self.wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=self.user.profile)
    
    def test_create_bounty_with_sufficient_balance(self):
        """Owner can create bounty if wallet has sufficient balance."""
        self.wallet.cached_balance = 1000
        self.wallet.save()
        
        self.client.login(username='creator', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:create_bounty'),
            data=json.dumps({
                'title': '1v1 Aim Duel',
                'game_id': self.game.id,
                'description': 'First to 100k Gridshot',
                'stake_amount': 500,
                'expires_in_hours': 72,
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['stake_amount'], 500)
        
        # Check bounty created
        bounty = Bounty.objects.get(pk=data['bounty_id'])
        self.assertEqual(bounty.creator, self.user)
        self.assertEqual(bounty.stake_amount, 500)
        self.assertEqual(bounty.status, BountyStatus.OPEN)
        
        # Check wallet locked
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.pending_balance, 500)
    
    def test_create_bounty_with_insufficient_balance(self):
        """Cannot create bounty if insufficient balance."""
        self.wallet.cached_balance = 100  # Not enough
        self.wallet.save()
        
        self.client.login(username='creator', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:create_bounty'),
            data=json.dumps({
                'title': '1v1 Aim Duel',
                'game_id': self.game.id,
                'stake_amount': 500,
                'expires_in_hours': 72,
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('balance', data['error'].lower())
    
    def test_create_bounty_validates_stake_range(self):
        """Stake amount must be between 100 and 50,000 DC."""
        self.wallet.cached_balance = 100000
        self.wallet.save()
        
        self.client.login(username='creator', password='testpass123')
        
        # Test below minimum
        response = self.client.post(
            reverse('user_profile:create_bounty'),
            data=json.dumps({
                'title': '1v1 Aim Duel',
                'game_id': self.game.id,
                'stake_amount': 50,  # Below min
                'expires_in_hours': 72,
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Minimum stake is 100 DC', data['error'])
        
        # Test above maximum
        response = self.client.post(
            reverse('user_profile:create_bounty'),
            data=json.dumps({
                'title': '1v1 Aim Duel',
                'game_id': self.game.id,
                'stake_amount': 60000,  # Above max
                'expires_in_hours': 72,
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Maximum stake is 50,000 DC', data['error'])


@pytest.mark.django_db
class TestBountyAcceptance(TestCase):
    """Test bounty acceptance flow."""
    
    def setUp(self):
        self.client = Client()
        self.creator = User.objects.create_user(username='creator', password='testpass123')
        self.acceptor = User.objects.create_user(username='acceptor', password='testpass123')
        self.game = Game.objects.create(name='Valorant', slug='valorant', is_active=True)
        
        # Fund creator
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=self.creator.profile)
        wallet.cached_balance = 1000
        wallet.save()
        
        # Import service to create bounty
        from apps.user_profile.services import bounty_service
        self.bounty = bounty_service.create_bounty(
            creator=self.creator,
            title='1v1 Aim Duel',
            game=self.game,
            stake_amount=500,
        )
    
    def test_visitor_can_accept_bounty(self):
        """Visitor can accept open bounty."""
        self.client.login(username='acceptor', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:accept_bounty', kwargs={'bounty_id': self.bounty.id})
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['bounty_id'], self.bounty.id)
        
        # Check bounty accepted
        self.bounty.refresh_from_db()
        self.assertEqual(self.bounty.status, BountyStatus.ACCEPTED)
        self.assertEqual(self.bounty.acceptor, self.acceptor)
    
    def test_creator_cannot_accept_own_bounty(self):
        """Creator cannot accept their own bounty."""
        self.client.login(username='creator', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:accept_bounty', kwargs={'bounty_id': self.bounty.id})
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('own', data['error'].lower())
    
    def test_cannot_accept_nonexistent_bounty(self):
        """Returns 404 for nonexistent bounty."""
        self.client.login(username='acceptor', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:accept_bounty', kwargs={'bounty_id': 99999})
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('not found', data['error'].lower())


@pytest.mark.django_db
class TestLoadoutAPI(TestCase):
    """Test loadout hardware and config CRUD."""
    
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owner', password='testpass123')
        self.other_user = User.objects.create_user(username='other', password='testpass123')
        self.game = Game.objects.create(name='Valorant', slug='valorant', is_active=True)
    
    def test_owner_can_save_hardware(self):
        """Owner can add/update hardware."""
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:save_hardware'),
            data=json.dumps({
                'category': 'MOUSE',
                'brand': 'Logitech',
                'model': 'G Pro X Superlight',
                'specs': {'dpi': 800, 'weight': '63g'},
                'is_public': True
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('hardware_id', data)
        
        # Check hardware created
        hardware = HardwareGear.objects.get(pk=data['hardware_id'])
        self.assertEqual(hardware.user, self.owner)
        self.assertEqual(hardware.brand, 'Logitech')
        self.assertEqual(hardware.model, 'G Pro X Superlight')
    
    def test_owner_can_save_game_config(self):
        """Owner can add/update game config."""
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:save_game_config'),
            data=json.dumps({
                'game_id': self.game.id,
                'settings': {
                    'dpi': 800,
                    'sensitivity': 0.45,
                    'crosshair_code': 'TEST123'
                },
                'notes': 'Aggressive entry setup',
                'is_public': True
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('config_id', data)
        
        # Check config created
        config = GameConfig.objects.get(pk=data['config_id'])
        self.assertEqual(config.user, self.owner)
        self.assertEqual(config.game, self.game)
        self.assertEqual(config.settings['dpi'], 800)
    
    def test_cannot_edit_others_hardware(self):
        """Cannot edit hardware owned by another user."""
        # Create hardware owned by other user
        hardware = HardwareGear.objects.create(
            user=self.other_user,
            category='MOUSE',
            brand='Razer',
            model='DeathAdder',
            is_public=True
        )
        
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:save_hardware'),
            data=json.dumps({
                'id': hardware.id,
                'category': 'MOUSE',
                'brand': 'Logitech',
                'model': 'G Pro',
                'is_public': True
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        
        # Hardware unchanged
        hardware.refresh_from_db()
        self.assertEqual(hardware.brand, 'Razer')


@pytest.mark.django_db
class TestTrophyShowcaseAPI(TestCase):
    """Test trophy showcase management."""
    
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owner', password='testpass123')
        
        # Create badges
        self.badge1 = Badge.objects.create(name='Champion', slug='champion', icon='🏆')
        self.badge2 = Badge.objects.create(name='MVP', slug='mvp', icon='⭐')
        self.badge3 = Badge.objects.create(name='Pro', slug='pro', icon='💎')
        self.badge4 = Badge.objects.create(name='Elite', slug='elite', icon='👑')
        
        # Award badges to user
        UserBadge.objects.create(user=self.owner, badge=self.badge1)
        UserBadge.objects.create(user=self.owner, badge=self.badge2)
        UserBadge.objects.create(user=self.owner, badge=self.badge3)
        UserBadge.objects.create(user=self.owner, badge=self.badge4)
    
    def test_owner_can_pin_badges(self):
        """Owner can pin up to 3 badges."""
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:update_trophy_showcase'),
            data=json.dumps({
                'pinned_badge_ids': [self.badge1.id, self.badge2.id, self.badge3.id]
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_cannot_pin_more_than_3_badges(self):
        """Cannot pin more than 3 badges."""
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:update_trophy_showcase'),
            data=json.dumps({
                'pinned_badge_ids': [
                    self.badge1.id, self.badge2.id,
                    self.badge3.id, self.badge4.id  # 4 badges
                ]
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Maximum 3 pinned badges', data['error'])
    
    def test_cannot_pin_unowned_badges(self):
        """Cannot pin badges not owned."""
        unowned_badge = Badge.objects.create(name='Unowned', slug='unowned', icon='❌')
        
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.post(
            reverse('user_profile:update_trophy_showcase'),
            data=json.dumps({
                'pinned_badge_ids': [unowned_badge.id]
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('not owned', data['error'].lower())


@pytest.mark.django_db
class TestUnauthorizedAccess(TestCase):
    """Test unauthorized access prevention."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
    
    def test_bounty_creation_requires_login(self):
        """Bounty creation requires authentication."""
        response = self.client.post(
            reverse('user_profile:create_bounty'),
            data=json.dumps({'title': 'Test'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_loadout_save_requires_login(self):
        """Loadout save requires authentication."""
        response = self.client.post(
            reverse('user_profile:save_hardware'),
            data=json.dumps({'category': 'MOUSE'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_showcase_update_requires_login(self):
        """Showcase update requires authentication."""
        response = self.client.post(
            reverse('user_profile:update_trophy_showcase'),
            data=json.dumps({'pinned_badge_ids': []}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect to login
