"""
Tests for User Profile URL Routing (UP-PRODUCTIZATION-01 + UP-FE-FIX-02)

Regression tests to ensure all URL patterns resolve correctly.
Covers NoReverseMatch scenarios and legacy redirects.
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_user(db):
    """Create test user for routing tests"""
    user = User.objects.create_user(
        username='routetest',
        email='route@test.com',
        password='testpass123'
    )
    profile = user.profile
    profile.display_name = 'Route Test'
    profile.save()
    return user


# ============================================
# URL NAME RESOLUTION TESTS
# ============================================

def test_settings_url_exists(test_user):
    """Test that 'user_profile:settings' URL name exists and resolves"""
    url = reverse('user_profile:settings')
    assert url == '/me/settings/'


def test_settings_v2_url_exists(test_user):
    """Test that 'user_profile:profile_settings_v2' URL name exists"""
    url = reverse('user_profile:profile_settings_v2')
    assert url == '/me/settings/'


def test_update_basic_info_url_exists(test_user):
    """Test that 'user_profile:update_basic_info' URL exists"""
    url = reverse('user_profile:update_basic_info')
    assert url == '/me/settings/basic/'


def test_update_social_links_url_exists(test_user):
    """Test that 'user_profile:update_social_links' URL exists"""
    url = reverse('user_profile:update_social_links')
    assert url == '/me/settings/social/'


def test_home_page_renders_without_noreversematch(client):
    """
    Regression test: home page should not raise NoReverseMatch for 'settings'
    
    This was a production bug where templates referenced {% url 'user_profile:settings' %}
    but the URL name didn't exist, causing server errors.
    """
    response = client.get('/')
    
    # Should not raise NoReverseMatch
    assert response.status_code == 200


def test_profile_public_v2_url_pattern(test_user):
    """Test V2 public profile URL pattern"""
    url = reverse('user_profile:profile_public_v2', kwargs={'username': 'routetest'})
    assert url == '/@routetest/'


def test_profile_activity_v2_url_pattern(test_user):
    """Test V2 activity feed URL pattern"""
    url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'routetest'})
    assert url == '/@routetest/activity/'


# ============================================
# UP-FE-FIX-02: ALIAS & LEGACY REDIRECT TESTS
# ============================================

def test_profile_alias_exists(test_user):
    """Test that 'profile' alias resolves to same URL as profile_public_v2"""
    url_v2 = reverse('user_profile:profile_public_v2', kwargs={'username': 'alice'})
    url_alias = reverse('user_profile:profile', kwargs={'username': 'alice'})
    assert url_v2 == url_alias == '/@alice/'


def test_legacy_u_redirect_works(client, test_user):
    """Test GET /u/routetest/ returns 301 to /@routetest/ without exceptions"""
    response = client.get('/u/routetest/')
    
    # Should redirect (301 permanent)
    assert response.status_code == 301
    assert response.url == '/@routetest/'


def test_legacy_username_redirect_works(client, test_user):
    """Test GET /routetest/ returns 301 to /@routetest/ without exceptions"""
    response = client.get('/routetest/')
    
    # Should redirect (301 permanent)
    assert response.status_code == 301
    assert response.url == '/@routetest/'


def test_settings_page_renders_for_authenticated_user(client, test_user):
    """Test GET /me/settings/ renders 200 for authenticated user"""
    client.force_login(test_user)
    response = client.get('/me/settings/')
    
    # Should render successfully (stub view returns 200)
    assert response.status_code == 200


def test_settings_page_redirects_for_anonymous_user(client, test_user):
    """Test GET /me/settings/ redirects to login for anonymous user"""
    response = client.get('/me/settings/')
    
    # Should redirect to login (302)
    assert response.status_code == 302
    assert '/login' in response.url or '/accounts/login' in response.url


# ============================================
# NAMESPACE-SAFE REVERSE TESTS
# ============================================

def test_namespaced_profile_reverse_works(test_user):
    """Test reverse('user_profile:profile_public_v2') works with namespace"""
    url = reverse('user_profile:profile_public_v2', kwargs={'username': 'alice'})
    assert url == '/@alice/'


def test_namespaced_settings_reverse_works(test_user):
    """Test reverse('user_profile:settings') works with namespace"""
    url = reverse('user_profile:settings')
    assert url == '/me/settings/'


def test_namespaced_profile_alias_reverse_works(test_user):
    """Test reverse('user_profile:profile') alias works with namespace"""
    url = reverse('user_profile:profile', kwargs={'username': 'bob'})
    assert url == '/@bob/'
