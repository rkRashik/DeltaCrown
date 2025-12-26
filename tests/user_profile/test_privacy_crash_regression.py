"""
Regression test for FieldError crash in /me/privacy endpoint.

Issue: PrivacySettings.objects.get_or_create(user=request.user) failed
because PrivacySettings uses user_profile FK, not user FK.

Fix: Changed to use user_profile=get_user_profile_safe(request.user)
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestPrivacyPageRegression:
    """Regression tests for /me/privacy endpoint"""
    
    def test_privacy_page_does_not_crash(self, client):
        """
        Regression test: /me/privacy should not crash with FieldError.
        
        Before fix: PrivacySettings.objects.get_or_create(user=...) 
        → FieldError: Cannot resolve keyword 'user' into field
        
        After fix: Uses user_profile FK correctly
        """
        # Create user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Login
        client.login(username='testuser', password='testpass123')
        
        # Access privacy page (should not crash)
        url = reverse('user_profile:profile_privacy_v2')
        response = client.get(url)
        
        # Should return 200, not 500
        assert response.status_code == 200
        assert 'Privacy Settings' in response.content.decode()
    
    def test_privacy_page_creates_settings_if_not_exists(self, client):
        """
        Privacy page should work even if PrivacySettings was auto-created.
        
        Note: In tests (and production), PrivacySettings is auto-created via signals,
        so this test verifies the page works with existing settings.
        """
        from apps.user_profile.models import PrivacySettings, UserProfile
        
        # Create user (PrivacySettings auto-created via conftest signal)
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        # Verify PrivacySettings WAS auto-created (expected behavior)
        profile = user.profile
        privacy = PrivacySettings.objects.get(user_profile=profile)
        assert privacy.visibility_preset in ['PUBLIC', 'PROTECTED', 'PRIVATE']
        
        # Login and access privacy page
        client.login(username='testuser2', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        response = client.get(url)
        
        # Should succeed
        assert response.status_code == 200
    
    def test_privacy_page_works_if_settings_already_exist(self, client):
        """Privacy page should work if PrivacySettings already exists"""
        from apps.user_profile.models import PrivacySettings
        
        # Create user (PrivacySettings auto-created via signal)
        user = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='testpass123'
        )
        
        # Manually update PrivacySettings to PRIVATE
        profile = user.profile
        privacy = PrivacySettings.objects.get(user_profile=profile)
        privacy.visibility_preset = 'PRIVATE'
        privacy.save()
        
        # Login and access privacy page
        client.login(username='testuser3', password='testpass123')
        url = reverse('user_profile:profile_privacy_v2')
        response = client.get(url)
        
        # Should succeed
        assert response.status_code == 200
        
        # Should show existing settings
        assert 'PRIVATE' in response.content.decode() or 'Private' in response.content.decode()
