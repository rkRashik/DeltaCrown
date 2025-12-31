"""
Test profile_settings URL resolution.

Regression test for Phase 2B.1.5: NoReverseMatch fix.
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


@pytest.mark.django_db
class TestProfileSettingsURL:
    """Test that profile_settings URL can be reversed and accessed."""
    
    def test_reverse_profile_settings_with_namespace(self):
        """Verify reverse('user_profile:profile_settings') resolves correctly."""
        url = reverse('user_profile:profile_settings')
        assert url == '/profile/me/settings/'
    
    def test_profile_settings_alias_resolves(self):
        """Verify 'settings' alias also resolves."""
        url = reverse('user_profile:settings')
        assert url == '/profile/me/settings/'
    
    def test_profile_privacy_resolves(self):
        """Verify profile_privacy URL resolves."""
        url = reverse('user_profile:profile_privacy')
        assert url == '/profile/me/privacy/'
    
    def test_public_profile_page_loads_for_owner(self, client, user):
        """Smoke test: GET /@username/ returns 200 for profile owner."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        
        # Should not crash with NoReverseMatch
        assert response.status_code == 200
    
    def test_public_profile_page_loads_for_visitor(self, client, user, other_user):
        """Smoke test: GET /@username/ returns 200 for visitor."""
        client.force_login(other_user)
        
        response = client.get(f'/@{user.username}/')
        
        # Should not crash with NoReverseMatch
        assert response.status_code == 200
    
    def test_public_profile_edit_button_renders_for_owner(self, client, user):
        """Verify 'Edit Profile' button with settings URL renders for owner."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        
        # Check that Edit Profile button is present with correct URL
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Edit Profile' in content
        assert '/profile/me/settings/' in content or 'profile_settings' in content


# Fixtures
@pytest.fixture
def user():
    """Create test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
    )


@pytest.fixture
def other_user():
    """Create another test user."""
    return User.objects.create_user(
        username='visitor',
        email='visitor@example.com',
        password='testpass123',
    )


@pytest.fixture
def client():
    """Create Django test client."""
    return Client()
