"""
User Profile Tests - Canonical Templates
Tests for public profile and settings pages using the production templates.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testplayer",
        email="test@example.com",
        password="testpass123"
    )


@pytest.fixture
def other_user(db):
    """Create another user."""
    return User.objects.create_user(
        username="otherplayer",
        email="other@example.com",
        password="testpass123"
    )


@pytest.mark.django_db
def test_public_profile_renders_200(client, test_user):
    """/@<username>/ should render 200 with public profile template."""
    url = reverse('user_profile:profile_public_v2', args=[test_user.username])
    response = client.get(url)
    
    assert response.status_code == 200
    assert test_user.username in response.content.decode()
    # Verify canonical template is used
    assert b'<!-- REBIRTH_PUBLIC_TEMPLATE -->' in response.content


@pytest.mark.django_db
def test_public_profile_contains_settings_link(client, test_user):
    """Public profile should contain namespaced settings link for owner."""
    client.force_login(test_user)
    url = reverse('user_profile:profile_public_v2', args=[test_user.username])
    response = client.get(url)
    
    assert response.status_code == 200
    settings_url = reverse('user_profile:profile_settings_v2')
    assert settings_url in response.content.decode()


@pytest.mark.django_db
def test_settings_page_requires_auth(client):
    """/me/settings/ should require authentication."""
    url = reverse('user_profile:profile_settings_v2')
    response = client.get(url)
    
    # Should redirect to login
    assert response.status_code == 302
    assert '/login/' in response.url or '/accounts/login/' in response.url


@pytest.mark.django_db
def test_settings_page_renders_200_for_authenticated(client, test_user):
    """/me/settings/ should render 200 for authenticated user."""
    client.force_login(test_user)
    url = reverse('user_profile:profile_settings_v2')
    response = client.get(url)
    
    assert response.status_code == 200
    # Verify canonical template is used
    assert b'<!-- REBIRTH_SETTINGS_TEMPLATE -->' in response.content


@pytest.mark.django_db
def test_templates_compile_without_errors(client, test_user):
    """Both canonical templates should compile without TemplateSyntaxError."""
    client.force_login(test_user)
    
    # Test public profile
    url_public = reverse('user_profile:profile_public_v2', args=[test_user.username])
    response_public = client.get(url_public)
    assert response_public.status_code == 200
    assert b'<!-- REBIRTH_PUBLIC_TEMPLATE -->' in response_public.content
    
    # Test settings
    url_settings = reverse('user_profile:profile_settings_v2')
    response_settings = client.get(url_settings)
    assert response_settings.status_code == 200
    assert b'<!-- REBIRTH_SETTINGS_TEMPLATE -->' in response_settings.content
