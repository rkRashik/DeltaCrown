"""
UP-M0 Safety Utilities Test Suite

Tests for get_or_create_user_profile, get_user_profile_safe, and @ensure_profile_exists.
Target: 100% coverage with race condition, rollback, and concurrent access scenarios.

See: Documents/UserProfile_CommandCenter_v1/01_Planning/UP_PHASE_0_IMPLEMENTATION_CHECKLIST.md
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser
from unittest.mock import Mock, patch
import threading
import time

from apps.user_profile.models import UserProfile
from apps.user_profile.utils import get_or_create_user_profile, get_user_profile_safe
from apps.user_profile.decorators import ensure_profile_exists

User = get_user_model()


class GetOrCreateUserProfileTestCase(TestCase):
    """Test get_or_create_user_profile utility"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_profile_when_missing(self):
        """Profile created if doesn't exist"""
        # Delete profile created by signal
        UserProfile.objects.filter(user=self.user).delete()
        
        profile, created = get_or_create_user_profile(self.user)
        
        self.assertTrue(created)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.display_name, 'testuser')
    
    def test_return_existing_profile(self):
        """Returns existing profile without creating duplicate"""
        profile, created = get_or_create_user_profile(self.user)
        
        self.assertFalse(created)
        self.assertEqual(profile.user, self.user)
    
    def test_idempotency(self):
        """Multiple calls return same profile, no duplicates"""
        profile1, created1 = get_or_create_user_profile(self.user)
        profile2, created2 = get_or_create_user_profile(self.user)
        profile3, created3 = get_or_create_user_profile(self.user)
        
        self.assertEqual(profile1.pk, profile2.pk)
        self.assertEqual(profile2.pk, profile3.pk)
        self.assertFalse(created2)
        self.assertFalse(created3)
    
    def test_unsaved_user_raises_value_error(self):
        """Unsaved user (no pk) raises ValueError"""
        unsaved_user = User(username='unsaved', email='unsaved@example.com')
        
        with self.assertRaises(ValueError) as cm:
            get_or_create_user_profile(unsaved_user)
        
        self.assertIn("unsaved user", str(cm.exception).lower())
    
    def test_display_name_fallback_order(self):
        """display_name uses username > email > User{pk} fallback"""
        # Test username fallback
        UserProfile.objects.filter(user=self.user).delete()
        profile1, _ = get_or_create_user_profile(self.user)
        self.assertEqual(profile1.display_name, 'testuser')
        
        # Test email fallback (no username)
        user2 = User.objects.create_user(username='', email='email@example.com', password='pass')
        UserProfile.objects.filter(user=user2).delete()
        profile2, _ = get_or_create_user_profile(user2)
        self.assertEqual(profile2.display_name, 'email@example.com')
        
        # Test pk fallback (no username, no email)
        user3 = User.objects.create_user(username='temp', email='temp@example.com', password='pass')
        user3.username = ''
        user3.email = ''
        user3.save()
        UserProfile.objects.filter(user=user3).delete()
        profile3, _ = get_or_create_user_profile(user3)
        self.assertEqual(profile3.display_name, f'User{user3.pk}')
    
    def test_signals_fire_on_creation(self):
        """PrivacySettings and VerificationRecord created via signals"""
        # Delete profile created by signal
        UserProfile.objects.filter(user=self.user).delete()
        
        profile, created = get_or_create_user_profile(self.user)
        
        # Refresh to get signal-created related objects
        profile.refresh_from_db()
        
        self.assertTrue(created)
        self.assertTrue(hasattr(profile, 'privacy_settings'))
        self.assertTrue(hasattr(profile, 'verification_record'))
    
    @patch('apps.user_profile.utils.UserProfile.objects.create')
    def test_retry_on_integrity_error(self, mock_create):
        """Retries on IntegrityError (race condition simulation)"""
        UserProfile.objects.filter(user=self.user).delete()
        
        # First call raises IntegrityError, second succeeds
        real_profile = UserProfile(user=self.user, display_name='testuser')
        mock_create.side_effect = [
            IntegrityError("UNIQUE constraint failed"),
            real_profile
        ]
        
        # Mock get() to return profile after "concurrent creation"
        with patch('apps.user_profile.utils.UserProfile.objects.get') as mock_get:
            mock_get.return_value = real_profile
            profile, created = get_or_create_user_profile(self.user, max_retries=3)
        
        # Should recover from race condition
        self.assertIsNotNone(profile)
    
    @patch('apps.user_profile.utils.UserProfile.objects.create')
    @patch('apps.user_profile.utils.UserProfile.objects.get')
    def test_runtime_error_after_max_retries(self, mock_get, mock_create):
        """Raises RuntimeError if all retries fail"""
        UserProfile.objects.filter(user=self.user).delete()
        
        # Simulate persistent failure
        mock_create.side_effect = IntegrityError("UNIQUE constraint failed")
        mock_get.side_effect = UserProfile.DoesNotExist()
        
        with self.assertRaises(RuntimeError) as cm:
            get_or_create_user_profile(self.user, max_retries=2)
        
        self.assertIn("after 2 attempts", str(cm.exception))


class GetUserProfileSafeTestCase(TestCase):
    """Test get_user_profile_safe convenience wrapper"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_returns_profile_only(self):
        """Returns profile without 'created' flag"""
        profile = get_user_profile_safe(self.user)
        
        self.assertIsInstance(profile, UserProfile)
        self.assertEqual(profile.user, self.user)
    
    def test_creates_if_missing(self):
        """Creates profile if doesn't exist"""
        UserProfile.objects.filter(user=self.user).delete()
        
        profile = get_user_profile_safe(self.user)
        
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user, self.user)
    
    def test_unsaved_user_raises_error(self):
        """Unsaved user raises ValueError"""
        unsaved_user = User(username='unsaved', email='unsaved@example.com')
        
        with self.assertRaises(ValueError):
            get_user_profile_safe(unsaved_user)


class EnsureProfileExistsDecoratorTestCase(TestCase):
    """Test @ensure_profile_exists decorator"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.request = HttpRequest()
        self.request.user = self.user
        self.request.path = '/test-path/'
    
    def test_authenticated_user_gets_profile(self):
        """Authenticated user has profile guaranteed"""
        UserProfile.objects.filter(user=self.user).delete()
        
        @ensure_profile_exists
        def test_view(request):
            profile = request.user.profile
            return Mock(status_code=200, content=f"Profile: {profile.pk}")
        
        response = test_view(self.request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())
    
    def test_anonymous_user_skipped(self):
        """Anonymous user skips profile check"""
        self.request.user = AnonymousUser()
        
        @ensure_profile_exists
        def test_view(request):
            return Mock(status_code=200, content="OK")
        
        response = test_view(self.request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_logs_warning_on_creation(self):
        """Logs warning if profile was missing"""
        UserProfile.objects.filter(user=self.user).delete()
        
        @ensure_profile_exists
        def test_view(request):
            return Mock(status_code=200)
        
        with self.assertLogs('apps.user_profile.decorators', level='WARNING') as logs:
            test_view(self.request)
        
        self.assertTrue(any('created missing profile' in log for log in logs.output))
    
    def test_returns_500_on_failure(self):
        """Returns HTTP 500 if profile provisioning fails"""
        with patch('apps.user_profile.decorators.get_or_create_user_profile') as mock_util:
            mock_util.side_effect = RuntimeError("Provisioning failed")
            
            @ensure_profile_exists
            def test_view(request):
                return Mock(status_code=200)
            
            response = test_view(self.request)
        
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Failed to provision user profile", response.content)
        self.assertIn(b"profile_provision_failure", response.content)
    
    def test_idempotent_multiple_decorators(self):
        """Multiple @ensure_profile_exists decorators are safe"""
        @ensure_profile_exists
        @ensure_profile_exists
        def test_view(request):
            return Mock(status_code=200)
        
        response = test_view(self.request)
        
        self.assertEqual(response.status_code, 200)
        # Should only have 1 profile, not duplicates
        self.assertEqual(UserProfile.objects.filter(user=self.user).count(), 1)


class ConcurrentAccessTestCase(TransactionTestCase):
    """Test race conditions with concurrent profile creation"""
    
    def test_concurrent_creation_no_duplicates(self):
        """10 threads trying to create profile, only 1 succeeds"""
        user = User.objects.create_user(
            username='raceuser',
            email='race@example.com',
            password='testpass123'
        )
        UserProfile.objects.filter(user=user).delete()
        
        results = []
        errors = []
        
        def create_profile():
            try:
                profile, created = get_or_create_user_profile(user)
                results.append((profile.pk, created))
            except Exception as e:
                errors.append(e)
        
        # Launch 10 concurrent threads
        threads = [threading.Thread(target=create_profile) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 10)
        
        # All threads got a profile
        profile_pks = [pk for pk, _ in results]
        self.assertTrue(all(pk == profile_pks[0] for pk in profile_pks), "All PKs should be same")
        
        # Only 1 profile created
        created_flags = [created for _, created in results]
        self.assertEqual(sum(created_flags), 1, "Exactly 1 thread should report created=True")
        
        # Database has exactly 1 profile
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
    
    def test_concurrent_with_existing_profile(self):
        """10 threads accessing existing profile, all succeed"""
        user = User.objects.create_user(
            username='existuser',
            email='exist@example.com',
            password='testpass123'
        )
        # Profile created by signal, keep it
        existing_profile = UserProfile.objects.get(user=user)
        
        results = []
        
        def get_profile():
            profile, created = get_or_create_user_profile(user)
            results.append((profile.pk, created))
        
        threads = [threading.Thread(target=get_profile) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All threads got same profile
        self.assertEqual(len(results), 10)
        self.assertTrue(all(pk == existing_profile.pk for pk, _ in results))
        self.assertTrue(all(not created for _, created in results))  # None created new
