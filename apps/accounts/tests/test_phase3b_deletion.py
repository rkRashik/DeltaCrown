# apps/accounts/tests/test_phase3b_deletion.py
"""
Phase 3B: Account Deletion System Tests
Comprehensive test coverage for scheduling, cancellation, and finalization.
"""
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from django.contrib.sessions.models import Session
import json

from apps.accounts.models import AccountDeletionRequest
from apps.accounts.deletion_services import (
    schedule_account_deletion,
    cancel_account_deletion,
    get_deletion_status,
    finalize_account_deletion,
    process_pending_deletions,
    REQUIRED_CONFIRMATION_PHRASE,
    DELETION_COOLDOWN_DAYS
)

User = get_user_model()


class AccountDeletionModelTest(TestCase):
    """Test AccountDeletionRequest model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_deletion_request(self):
        """Test creating a deletion request"""
        scheduled_for = timezone.now() + timedelta(days=14)
        deletion = AccountDeletionRequest.objects.create(
            user=self.user,
            scheduled_for=scheduled_for,
            confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
        )
        
        self.assertEqual(deletion.user, self.user)
        self.assertEqual(deletion.status, AccountDeletionRequest.Status.SCHEDULED)
        self.assertIsNotNone(deletion.requested_at)
    
    def test_days_remaining_calculation(self):
        """Test days_remaining() method"""
        scheduled_for = timezone.now() + timedelta(days=7)
        deletion = AccountDeletionRequest.objects.create(
            user=self.user,
            scheduled_for=scheduled_for
        )
        
        days = deletion.days_remaining()
        self.assertIsNotNone(days)
        self.assertTrue(0 <= days <= 7)
    
    def test_is_cancellable(self):
        """Test is_cancellable() method"""
        # Future scheduled deletion
        scheduled_for = timezone.now() + timedelta(days=7)
        deletion = AccountDeletionRequest.objects.create(
            user=self.user,
            scheduled_for=scheduled_for,
            status=AccountDeletionRequest.Status.SCHEDULED
        )
        self.assertTrue(deletion.is_cancellable())
        
        # Past scheduled deletion
        deletion.scheduled_for = timezone.now() - timedelta(days=1)
        deletion.save()
        self.assertFalse(deletion.is_cancellable())
        
        # Canceled deletion
        deletion.status = AccountDeletionRequest.Status.CANCELED
        deletion.save()
        self.assertFalse(deletion.is_cancellable())


class ScheduleDeletionServiceTest(TestCase):
    """Test schedule_account_deletion service"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_schedule_with_correct_password(self):
        """Test scheduling deletion with correct password"""
        result = schedule_account_deletion(
            user=self.user,
            password='testpass123',
            confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
        )
        
        self.assertTrue(result['success'])
        self.assertIn('scheduled_for', result)
        self.assertEqual(result['days_remaining'], DELETION_COOLDOWN_DAYS)
        
        # Verify deletion request created
        self.assertTrue(hasattr(self.user, 'deletion_request'))
        self.assertEqual(self.user.deletion_request.status, AccountDeletionRequest.Status.SCHEDULED)
    
    def test_schedule_with_wrong_password(self):
        """Test scheduling deletion with wrong password is rejected"""
        from django.core.exceptions import ValidationError
        
        with self.assertRaises(ValidationError) as context:
            schedule_account_deletion(
                user=self.user,
                password='wrongpassword',
                confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
            )
        
        self.assertIn('Incorrect password', str(context.exception))
    
    def test_schedule_without_confirmation_phrase(self):
        """Test scheduling deletion without confirmation phrase fails"""
        from django.core.exceptions import ValidationError
        
        with self.assertRaises(ValidationError) as context:
            schedule_account_deletion(
                user=self.user,
                password='testpass123',
                confirmation_phrase='wrong phrase'
            )
        
        self.assertIn('Confirmation phrase must be exactly', str(context.exception))
    
    def test_schedule_oauth_user_without_password(self):
        """Test OAuth user can schedule without password"""
        oauth_user = User.objects.create_user(
            username='oauthuser',
            email='oauth@example.com'
        )
        oauth_user.set_unusable_password()
        oauth_user.save()
        
        result = schedule_account_deletion(
            user=oauth_user,
            password=None,
            confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
        )
        
        self.assertTrue(result['success'])
    
    def test_schedule_already_scheduled_fails(self):
        """Test scheduling when already scheduled returns error"""
        # First schedule
        schedule_account_deletion(
            user=self.user,
            password='testpass123',
            confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
        )
        
        # Try to schedule again
        result = schedule_account_deletion(
            user=self.user,
            password='testpass123',
            confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
        )
        
        self.assertFalse(result['success'])
        self.assertIn('already scheduled', result['message'])


class CancelDeletionServiceTest(TestCase):
    """Test cancel_account_deletion service"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_cancel_before_deadline(self):
        """Test canceling deletion before deadline succeeds"""
        # Schedule deletion
        schedule_account_deletion(
            user=self.user,
            password='testpass123',
            confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
        )
        
        # Cancel it
        result = cancel_account_deletion(self.user)
        
        self.assertTrue(result['success'])
        self.assertIn('canceled', result['message'].lower())
        
        # Verify status updated
        self.user.deletion_request.refresh_from_db()
        self.assertEqual(self.user.deletion_request.status, AccountDeletionRequest.Status.CANCELED)
        self.assertIsNotNone(self.user.deletion_request.canceled_at)
    
    def test_cancel_after_deadline_fails(self):
        """Test canceling deletion after deadline is rejected"""
        # Create deletion request in the past
        past_date = timezone.now() - timedelta(days=1)
        AccountDeletionRequest.objects.create(
            user=self.user,
            scheduled_for=past_date,
            status=AccountDeletionRequest.Status.SCHEDULED
        )
        
        result = cancel_account_deletion(self.user)
        
        self.assertFalse(result['success'])
        self.assertIn('deadline has passed', result['message'])
    
    def test_cancel_without_deletion_request_fails(self):
        """Test canceling when no deletion request exists"""
        result = cancel_account_deletion(self.user)
        
        self.assertFalse(result['success'])
        self.assertIn('No deletion request found', result['message'])


class FinalizeDeletionServiceTest(TestCase):
    """Test finalize_account_deletion service"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_finalize_eligible_deletion(self):
        """Test finalizing eligible deletion soft-deletes and anonymizes"""
        # Create deletion scheduled in the past
        past_date = timezone.now() - timedelta(days=1)
        AccountDeletionRequest.objects.create(
            user=self.user,
            scheduled_for=past_date,
            status=AccountDeletionRequest.Status.SCHEDULED
        )
        
        result = finalize_account_deletion(self.user)
        
        self.assertTrue(result['success'])
        
        # Verify user is deactivated
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        
        # Verify PII anonymized
        self.assertIn('deleted_', self.user.username)
        self.assertIn('deleted_', self.user.email)
        self.assertEqual(self.user.first_name, '')
        self.assertEqual(self.user.last_name, '')
        
        # Verify deletion request marked completed
        self.user.deletion_request.refresh_from_db()
        self.assertEqual(self.user.deletion_request.status, AccountDeletionRequest.Status.COMPLETED)
        self.assertIsNotNone(self.user.deletion_request.completed_at)
    
    def test_finalize_before_scheduled_time_fails(self):
        """Test finalizing before scheduled time is rejected"""
        # Create deletion scheduled in the future
        future_date = timezone.now() + timedelta(days=7)
        AccountDeletionRequest.objects.create(
            user=self.user,
            scheduled_for=future_date,
            status=AccountDeletionRequest.Status.SCHEDULED
        )
        
        result = finalize_account_deletion(self.user)
        
        self.assertFalse(result['success'])
        self.assertIn('not yet arrived', result['message'])


class ProcessPendingDeletionsTest(TestCase):
    """Test process_pending_deletions batch function"""
    
    def test_process_multiple_deletions(self):
        """Test processing multiple pending deletions"""
        # Create 3 users with past scheduled deletions
        past_date = timezone.now() - timedelta(days=1)
        users = []
        
        for i in range(3):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='pass123'
            )
            AccountDeletionRequest.objects.create(
                user=user,
                scheduled_for=past_date,
                status=AccountDeletionRequest.Status.SCHEDULED
            )
            users.append(user)
        
        # Process deletions
        result = process_pending_deletions()
        
        self.assertEqual(result['processed'], 3)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(result['total'], 3)
        
        # Verify all users deactivated
        for user in users:
            user.refresh_from_db()
            self.assertFalse(user.is_active)
    
    def test_process_no_pending_deletions(self):
        """Test processing when no pending deletions exist"""
        result = process_pending_deletions()
        
        self.assertEqual(result['processed'], 0)
        self.assertEqual(result['total'], 0)


class DeletionAPITest(TestCase):
    """Test deletion API endpoints"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='pass123'
        )
    
    def test_schedule_deletion_requires_auth(self):
        """Test schedule endpoint requires authentication"""
        response = self.client.post(
            reverse('accounts:schedule_deletion'),
            data=json.dumps({
                'password': 'pass123',
                'confirm_phrase': REQUIRED_CONFIRMATION_PHRASE
            }),
            content_type='application/json'
        )
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_schedule_deletion_success(self):
        """Test scheduling deletion via API"""
        self.client.force_login(self.user)
        
        response = self.client.post(
            reverse('accounts:schedule_deletion'),
            data=json.dumps({
                'password': 'pass123',
                'confirm_phrase': REQUIRED_CONFIRMATION_PHRASE
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('scheduled_for', data)
        self.assertEqual(data['days_remaining'], DELETION_COOLDOWN_DAYS)
    
    def test_cancel_deletion_success(self):
        """Test canceling deletion via API"""
        self.client.force_login(self.user)
        
        # Schedule deletion first
        schedule_account_deletion(
            user=self.user,
            password='pass123',
            confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
        )
        
        # Cancel it
        response = self.client.post(reverse('accounts:cancel_deletion'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
    
    def test_deletion_status_endpoint(self):
        """Test deletion status endpoint"""
        self.client.force_login(self.user)
        
        # No deletion scheduled
        response = self.client.get(reverse('accounts:deletion_status'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data['data'])
        
        # Schedule deletion
        schedule_account_deletion(
            user=self.user,
            password='pass123',
            confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
        )
        
        # Check status again
        response = self.client.get(reverse('accounts:deletion_status'))
        data = response.json()
        
        self.assertIsNotNone(data['data'])
        self.assertEqual(data['data']['status'], 'SCHEDULED')
        self.assertTrue(data['data']['can_cancel'])


class DeletionBlockingTest(TestCase):
    """Test that scheduled deletion users are blocked from access"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='blockeduser',
            email='blocked@example.com',
            password='pass123'
        )
    
    def test_scheduled_user_cannot_login(self):
        """Test user with scheduled deletion cannot log in"""
        # Schedule deletion
        schedule_account_deletion(
            user=self.user,
            password='pass123',
            confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
        )
        
        # Try to login
        login_result = self.client.login(username='blockeduser', password='pass123')
        
        # Login should fail
        self.assertFalse(login_result)
    
    def test_scheduled_user_settings_access_shows_deletion_only(self):
        """Test settings page is accessible but in deletion-only mode"""
        # Schedule deletion
        schedule_account_deletion(
            user=self.user,
            password='pass123',
            confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
        )
        
        # Force login (bypassing auth backend for testing middleware)
        self.client.force_login(self.user)
        
        # Settings should be accessible (deletion-only mode)
        response = self.client.get('/me/settings/')
        
        # Should be allowed (200) because middleware allows settings page
        self.assertEqual(response.status_code, 200)
    
    def test_scheduled_user_blocked_from_other_routes(self):
        """Test scheduled user is blocked from non-settings routes"""
        # Schedule deletion
        schedule_account_deletion(
            user=self.user,
            password='pass123',
            confirmation_phrase=REQUIRED_CONFIRMATION_PHRASE
        )
        
        # Force login
        self.client.force_login(self.user)
        
        # Try to access profile (should be blocked)
        response = self.client.get(f'/u/{self.user.username}/')
        
        # Should be redirected (302) after logout
        self.assertEqual(response.status_code, 302)
