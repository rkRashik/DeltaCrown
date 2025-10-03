# tests/tournaments/test_deprecation.py
"""
Tests for Deprecated Registration Views

Tests that old URLs redirect correctly to modern registration.
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages

from apps.tournaments.models import Tournament

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    """Create a test client."""
    return Client()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def tournament():
    """Create a test tournament."""
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        game='valorant',
        status='PUBLISHED',
        entry_fee=100,
    )


class TestDeprecatedViewRedirects:
    """Test that deprecated views redirect correctly."""
    
    def test_old_register_redirects(self, client, user, tournament):
        """Old /register/<slug>/ should redirect to /register-modern/<slug>/"""
        client.force_login(user)
        
        old_url = reverse('tournaments:register', kwargs={'slug': tournament.slug})
        response = client.get(old_url)
        
        # Should redirect (302)
        assert response.status_code == 302
        
        # Should redirect to modern URL
        expected_url = reverse('tournaments:modern_register', kwargs={'slug': tournament.slug})
        assert response.url == expected_url
    
    def test_unified_register_redirects(self, client, user, tournament):
        """Unified registration should redirect."""
        client.force_login(user)
        
        old_url = reverse('tournaments:unified_register', kwargs={'slug': tournament.slug})
        response = client.get(old_url)
        
        assert response.status_code == 302
        expected_url = reverse('tournaments:modern_register', kwargs={'slug': tournament.slug})
        assert response.url == expected_url
    
    def test_enhanced_register_redirects(self, client, user, tournament):
        """Enhanced registration should redirect."""
        client.force_login(user)
        
        old_url = reverse('tournaments:enhanced_register', kwargs={'slug': tournament.slug})
        response = client.get(old_url)
        
        assert response.status_code == 302
        expected_url = reverse('tournaments:modern_register', kwargs={'slug': tournament.slug})
        assert response.url == expected_url
    
    def test_valorant_register_redirects(self, client, user, tournament):
        """Valorant-specific registration should redirect."""
        client.force_login(user)
        
        old_url = reverse('tournaments:valorant_register', kwargs={'slug': tournament.slug})
        response = client.get(old_url)
        
        assert response.status_code == 302
        expected_url = reverse('tournaments:modern_register', kwargs={'slug': tournament.slug})
        assert response.url == expected_url
    
    def test_efootball_register_redirects(self, client, user, tournament):
        """eFootball-specific registration should redirect."""
        client.force_login(user)
        
        old_url = reverse('tournaments:efootball_register', kwargs={'slug': tournament.slug})
        response = client.get(old_url)
        
        assert response.status_code == 302
        expected_url = reverse('tournaments:modern_register', kwargs={'slug': tournament.slug})
        assert response.url == expected_url


class TestDeprecationMessages:
    """Test that deprecation warnings are shown."""
    
    def test_deprecation_warning_message(self, client, user, tournament):
        """Should show warning message when using deprecated URL."""
        client.force_login(user)
        
        old_url = reverse('tournaments:register', kwargs={'slug': tournament.slug})
        response = client.get(old_url, follow=True)
        
        # Check messages
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        
        # Should contain warning about legacy page
        warning_found = any('legacy' in str(msg).lower() for msg in messages)
        assert warning_found, "Expected deprecation warning message"


class TestModernRegistrationWorks:
    """Test that modern registration still works correctly."""
    
    def test_modern_registration_loads(self, client, user, tournament):
        """Modern registration page should load successfully."""
        client.force_login(user)
        
        url = reverse('tournaments:modern_register', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        # Should load successfully (200 or redirect to detail if already registered)
        assert response.status_code in [200, 302]
    
    def test_modern_registration_has_correct_template(self, client, user, tournament):
        """Modern registration should use modern_register.html template."""
        client.force_login(user)
        
        url = reverse('tournaments:modern_register', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        if response.status_code == 200:
            # Should use modern template, not deprecated ones
            template_names = [t.name for t in response.templates if t.name]
            assert 'tournaments/modern_register.html' in template_names or \
                   any('modern' in name for name in template_names)


class TestURLReversing:
    """Test that URL reversing works for all views."""
    
    def test_all_registration_urls_reversible(self, tournament):
        """All registration URL patterns should be reversible."""
        url_names = [
            'tournaments:register',
            'tournaments:unified_register',
            'tournaments:enhanced_register',
            'tournaments:valorant_register',
            'tournaments:efootball_register',
            'tournaments:modern_register',
        ]
        
        for url_name in url_names:
            url = reverse(url_name, kwargs={'slug': tournament.slug})
            assert url is not None
            assert tournament.slug in url
    
    def test_modern_url_structure(self, tournament):
        """Modern registration URL should have correct structure."""
        url = reverse('tournaments:modern_register', kwargs={'slug': tournament.slug})
        assert 'register-modern' in url
        assert tournament.slug in url


class TestBackwardCompatibility:
    """Test backward compatibility features."""
    
    def test_old_urls_still_accessible(self, client, tournament):
        """Old URLs should still be accessible (not 404)."""
        old_urls = [
            reverse('tournaments:register', kwargs={'slug': tournament.slug}),
            reverse('tournaments:unified_register', kwargs={'slug': tournament.slug}),
            reverse('tournaments:enhanced_register', kwargs={'slug': tournament.slug}),
        ]
        
        for url in old_urls:
            response = client.get(url)
            # Should redirect (302), not 404
            assert response.status_code in [302, 200], \
                f"URL {url} returned {response.status_code}, expected 302 or 200"
    
    def test_modern_url_accessible(self, client, tournament):
        """Modern URL should be accessible."""
        url = reverse('tournaments:modern_register', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        # Should work (200) or redirect to login (302)
        assert response.status_code in [200, 302]


class TestAnonymousUserHandling:
    """Test how deprecated views handle anonymous users."""
    
    def test_anonymous_user_redirects(self, client, tournament):
        """Anonymous users should be redirected through deprecation."""
        old_url = reverse('tournaments:register', kwargs={'slug': tournament.slug})
        response = client.get(old_url)
        
        # Should redirect (either to modern or to login)
        assert response.status_code == 302
    
    def test_redirect_chain(self, client, tournament):
        """Test complete redirect chain for anonymous user."""
        old_url = reverse('tournaments:register', kwargs={'slug': tournament.slug})
        response = client.get(old_url, follow=True)
        
        # Final URL should be either login or modern registration
        final_url = response.redirect_chain[-1][0] if response.redirect_chain else response.request['PATH_INFO']
        assert 'login' in final_url or 'register-modern' in final_url
