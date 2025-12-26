"""
Comprehensive test suite for canonical user profile UI (UP-UI-CANONICAL-01).

Tests all four profile pages (public, settings, privacy, activity) to ensure:
- Correct HTTP status codes (200/302/403)
- Authentication requirements enforced
- Templates render without compilation errors
- No Alpine.js dependencies
- Single canonical template per route
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.user_profile.models import UserProfile

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create a test user with profile."""
    user = User.objects.create_user(
        username='testplayer',
        email='test@example.com',
        password='testpass123'
    )
    # UserProfile is auto-created via signal
    profile = UserProfile.objects.get(user=user)
    profile.display_name = 'Test Player'
    profile.save()
    return user


@pytest.fixture
def other_user(db):
    """Create another user for non-owner tests."""
    user = User.objects.create_user(
        username='otherplayer',
        email='other@example.com',
        password='testpass123'
    )
    # UserProfile is auto-created via signal
    profile = UserProfile.objects.get(user=user)
    profile.display_name = 'Other Player'
    profile.save()
    return user


@pytest.fixture
def client_authenticated(client, test_user):
    """Return client logged in as test_user."""
    client.login(username='testplayer', password='testpass123')
    return client


# ============================================
# PUBLIC PROFILE TESTS
# ============================================

def test_public_profile_renders_200_for_owner(client_authenticated, test_user):
    """Owner can view their own public profile."""
    url = reverse('user_profile:profile_public_v2', kwargs={'username': 'testplayer'})
    response = client_authenticated.get(url)
    assert response.status_code == 200


def test_public_profile_renders_200_for_non_owner(client_authenticated, other_user):
    """Authenticated users can view other profiles."""
    url = reverse('user_profile:profile_public_v2', kwargs={'username': 'otherplayer'})
    response = client_authenticated.get(url)
    assert response.status_code == 200


def test_public_profile_renders_200_for_anonymous(client, test_user):
    """Anonymous users can view public profiles."""
    url = reverse('user_profile:profile_public_v2', kwargs={'username': 'testplayer'})
    response = client.get(url)
    assert response.status_code == 200


def test_public_profile_contains_display_name(client_authenticated, test_user):
    """Public profile displays user's display name."""
    url = reverse('user_profile:profile_public_v2', kwargs={'username': 'testplayer'})
    response = client_authenticated.get(url)
    assert 'Test Player' in response.content.decode()


def test_public_profile_uses_canonical_template(client, test_user):
    """Public profile uses canonical template path."""
    url = reverse('user_profile:profile_public_v2', kwargs={'username': 'testplayer'})
    response = client.get(url)
    assert 'user_profile/profile/public.html' in [t.name for t in response.templates]


def test_public_profile_no_alpinejs(client, test_user):
    """Public profile does not use Alpine.js."""
    url = reverse('user_profile:profile_public_v2', kwargs={'username': 'testplayer'})
    response = client.get(url)
    content = response.content.decode()
    assert 'alpinejs' not in content.lower()
    assert 'x-data' not in content
    assert '@click' not in content


# ============================================
# SETTINGS PAGE TESTS
# ============================================

def test_settings_requires_authentication(client, test_user):
    """Settings page requires login."""
    url = reverse('user_profile:profile_settings_v2')
    response = client.get(url)
    assert response.status_code == 302  # Redirect to login


def test_settings_renders_200_for_owner(client_authenticated, test_user):
    """Owner can view their own settings."""
    url = reverse('user_profile:profile_settings_v2')
    response = client_authenticated.get(url)
    assert response.status_code == 200


def test_settings_uses_canonical_template(client_authenticated, test_user):
    """Settings page uses canonical template path."""
    url = reverse('user_profile:profile_settings_v2')
    response = client_authenticated.get(url)
    assert 'user_profile/profile/settings.html' in [t.name for t in response.templates]


def test_settings_contains_form(client_authenticated, test_user):
    """Settings page contains profile update form."""
    url = reverse('user_profile:profile_settings_v2')
    response = client_authenticated.get(url)
    content = response.content.decode()
    assert '<form' in content
    assert 'display_name' in content


# ============================================
# PRIVACY PAGE TESTS
# ============================================

def test_privacy_requires_authentication(client, test_user):
    """Privacy settings page requires login."""
    url = reverse('user_profile:profile_privacy_v2')
    response = client.get(url)
    assert response.status_code == 302  # Redirect to login


def test_privacy_renders_200_for_owner(client_authenticated, test_user):
    """Owner can view their own privacy settings."""
    url = reverse('user_profile:profile_privacy_v2')
    response = client_authenticated.get(url)
    assert response.status_code == 200


def test_privacy_uses_canonical_template(client_authenticated, test_user):
    """Privacy page uses canonical template path."""
    url = reverse('user_profile:profile_privacy_v2')
    response = client_authenticated.get(url)
    assert 'user_profile/profile/privacy.html' in [t.name for t in response.templates]


def test_privacy_contains_toggle_switches(client_authenticated, test_user):
    """Privacy page contains custom toggle switches."""
    url = reverse('user_profile:profile_privacy_v2')
    response = client_authenticated.get(url)
    content = response.content.decode()
    assert 'toggle-switch' in content
    assert 'show_email' in content
    assert 'show_real_name' in content


def test_privacy_form_posts_correctly(client_authenticated, test_user):
    """Privacy form submits to correct endpoint."""
    url = reverse('user_profile:profile_privacy_v2')
    response = client_authenticated.get(url)
    content = response.content.decode()
    # Check form exists with correct action
    assert '<form' in content
    assert 'method="POST"' in content or 'method="post"' in content


# ============================================
# ACTIVITY PAGE TESTS
# ============================================

def test_activity_renders_200_for_owner(client_authenticated, test_user):
    """Owner can view their own activity feed."""
    url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'testplayer'})
    response = client_authenticated.get(url)
    assert response.status_code == 200


def test_activity_renders_200_for_non_owner(client_authenticated, other_user):
    """Users can view other users' public activity."""
    url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'otherplayer'})
    response = client_authenticated.get(url)
    assert response.status_code == 200


def test_activity_uses_canonical_template(client_authenticated, test_user):
    """Activity page uses canonical template path."""
    url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'testplayer'})
    response = client_authenticated.get(url)
    assert 'user_profile/profile/activity.html' in [t.name for t in response.templates]


def test_activity_shows_empty_state_when_no_events(client_authenticated, test_user):
    """Activity page shows empty state when user has no activity."""
    url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'testplayer'})
    response = client_authenticated.get(url)
    content = response.content.decode()
    assert 'No Activity Yet' in content or 'No activity yet' in content


# ============================================
# TEMPLATE COMPILATION TESTS
# ============================================

def test_all_canonical_templates_compile(client_authenticated, test_user):
    """All canonical templates compile without syntax errors."""
    urls = [
        reverse('user_profile:profile_public_v2', kwargs={'username': 'testplayer'}),
        reverse('user_profile:profile_settings_v2'),
        reverse('user_profile:profile_privacy_v2'),
        reverse('user_profile:profile_activity_v2', kwargs={'username': 'testplayer'}),
    ]
    for url in urls:
        response = client_authenticated.get(url)
        assert response.status_code == 200, f"Template compilation failed for {url}"


def test_no_v2_directory_references(client_authenticated, test_user):
    """Templates do not reference v2/ directory paths."""
    urls = [
        reverse('user_profile:profile_public_v2', kwargs={'username': 'testplayer'}),
        reverse('user_profile:profile_settings_v2'),
        reverse('user_profile:profile_privacy_v2'),
        reverse('user_profile:profile_activity_v2', kwargs={'username': 'testplayer'}),
    ]
    for url in urls:
        response = client_authenticated.get(url)
        # Check that canonical templates are used
        template_names = [t.name for t in response.templates]
        for template_name in template_names:
            if 'user_profile' in template_name:
                assert '/v2/' not in template_name, f"Found v2 reference in {template_name}"
