"""
PHASE 8B: Backend Lock Enforcement Tests
Tests for 30-day lock enforcement + verification status
"""

import json
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.user_profile.models import UserProfile, GameProfile
from apps.games.models import Game

User = get_user_model()


class Phase8BLockEnforcementTestCase(TestCase):
    """Test Phase 8B backend lock enforcement"""

    def setUp(self):
        """Set up test users and games"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        
        # Create admin user
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        
        # Create test game
        self.game = Game.objects.create(
            name='VALORANT',
            display_name='VALORANT',
            slug='valorant',
            short_code='VAL',
            category='FPS',
            is_active=True
        )
        
        self.client.login(username='testuser', password='testpass123')

    def test_locked_passport_cannot_update(self):
        """Test that locked passport returns 403 on update"""
        # Create locked passport
        locked_until = timezone.now() + timedelta(days=15)
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='LockedPlayer#123',
            region='NA',
            locked_until=locked_until
        )
        
        # Try to update
        payload = {
            'id': passport.id,
            'ign': 'NewName#456',
            'region': 'EU'
        }
        
        response = self.client.post(
            '/profile/api/game-passports/update/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'LOCKED')
        self.assertIn('days', data['message'].lower())
        
        # Verify passport not changed
        passport.refresh_from_db()
        self.assertEqual(passport.ign, 'LockedPlayer#123')

    def test_locked_passport_cannot_delete(self):
        """Test that locked passport returns 403 on delete"""
        # Create locked passport
        locked_until = timezone.now() + timedelta(days=10)
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='LockedPlayer#123',
            locked_until=locked_until
        )
        
        # Try to delete
        payload = {'id': passport.id}
        
        response = self.client.post(
            '/profile/api/game-passports/delete/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'LOCKED')
        
        # Verify passport still exists
        self.assertTrue(GameProfile.objects.filter(id=passport.id).exists())

    def test_expired_lock_allows_update(self):
        """Test that expired lock allows updates"""
        # Create passport with expired lock
        locked_until = timezone.now() - timedelta(days=1)
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='UnlockedPlayer#123',
            region='NA',  # Fix: include region
            locked_until=locked_until
        )
        
        # Try to update
        payload = {
            'id': passport.id,
            'ign': 'NewName#456',
            'region': 'EU'  # Fix: include region in update
        }
        
        response = self.client.post(
            '/profile/api/game-passports/update/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify update succeeded
        passport.refresh_from_db()
        self.assertEqual(passport.ign, 'NewName#456')

    def test_admin_bypass_locked_passport(self):
        """Test that superuser can bypass lock"""
        # Create locked passport for test user
        locked_until = timezone.now() + timedelta(days=20)
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='LockedPlayer#123',
            region='NA',
            locked_until=locked_until
        )
        
        # Create admin's own passport to bypass 404 (admin editing own passport)
        admin_passport = GameProfile.objects.create(
            user=self.admin,
            game=self.game,
            ign='AdminPlayer#000',
            region='NA',
            locked_until=timezone.now() + timedelta(days=10)
        )
        
        # Login as admin
        self.client.logout()
        self.client.login(username='admin', password='admin123')
        
        # Try to update admin's own locked passport (superuser bypass)
        payload = {
            'id': admin_passport.id,
            'ign': 'AdminChanged#999',
            'region': 'EU'
        }
        
        response = self.client.post(
            '/profile/api/game-passports/update/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify admin bypass worked
        admin_passport.refresh_from_db()
        self.assertEqual(admin_passport.ign, 'AdminChanged#999')

    def test_verification_status_default(self):
        """Test that new passports default to PENDING verification_status"""
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer#123'
        )
        
        self.assertEqual(passport.verification_status, 'PENDING')
        self.assertFalse(passport.is_verified)

    def test_verification_status_verified(self):
        """Test VERIFIED status syncs with is_verified"""
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer#123',
            verification_status='VERIFIED',
            verified_at=timezone.now()
        )
        
        passport.save()
        self.assertTrue(passport.is_verified)
        self.assertEqual(passport.verification_status, 'VERIFIED')

    def test_list_includes_verification_status(self):
        """Test that list endpoint includes verification_status"""
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer#123',
            verification_status='PENDING'
        )
        
        response = self.client.get('/profile/api/game-passports/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['passports']), 1)
        
        passport_data = data['passports'][0]
        self.assertIn('verification_status', passport_data)
        self.assertEqual(passport_data['verification_status'], 'PENDING')

    def test_list_includes_lock_status(self):
        """Test that list endpoint includes lock status"""
        locked_until = timezone.now() + timedelta(days=25)
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='LockedPlayer#123',
            locked_until=locked_until
        )
        
        response = self.client.get('/profile/api/game-passports/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        passport_data = data['passports'][0]
        
        self.assertIn('locked_until', passport_data)
        self.assertIn('is_locked', passport_data)
        self.assertIn('days_locked', passport_data)
        self.assertTrue(passport_data['is_locked'])
        self.assertGreater(passport_data['days_locked'], 0)
