"""
Routing Hardening Tests - Production Grade

Tests for:
1. All V2 routes can be resolved and reversed correctly
2. GET /@username/ returns 200 for valid user
3. GET /me/settings/ returns 200 for authenticated user
4. GET /me/privacy/ returns 200 for authenticated user
5. No NoReverseMatch errors for common patterns
6. Namespace routing works correctly
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse, resolve
from django.http import Http404

from apps.user_profile.models import UserProfile

User = get_user_model()


@pytest.mark.django_db
class TestURLResolveAndReverse:
    """Test that all V2 URLs can be resolved and reversed"""
    
    def test_profile_public_v2_resolves(self):
        """/@username/ route should resolve"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'testuser'})
        assert url == '/@testuser/'
        
        match = resolve('/@testuser/')
        assert match.url_name == 'profile_public_v2'
        assert match.namespace == 'user_profile'
    
    def test_profile_alias_resolves(self):
        """profile alias should work for backward compatibility"""
        url = reverse('user_profile:profile', kwargs={'username': 'testuser'})
        assert url == '/@testuser/'
    
    def test_profile_activity_v2_resolves(self):
        """/@username/activity/ route should resolve"""
        url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'testuser'})
        assert url == '/@testuser/activity/'
        
        match = resolve('/@testuser/activity/')
        assert match.url_name == 'profile_activity_v2'
    
    def test_profile_settings_v2_resolves(self):
        """/me/settings/ route should resolve"""
        url = reverse('user_profile:profile_settings_v2')
        assert url == '/me/settings/'
        
        match = resolve('/me/settings/')
        assert match.url_name == 'profile_settings_v2'
    
    def test_settings_alias_resolves(self):
        """settings alias should work for backward compatibility"""
        url = reverse('user_profile:settings')
        assert url == '/me/settings/'
    
    def test_profile_privacy_v2_resolves(self):
        """/me/privacy/ route should resolve"""
        url = reverse('user_profile:profile_privacy_v2')
        assert url == '/me/privacy/'
        
        match = resolve('/me/privacy/')
        assert match.url_name == 'profile_privacy_v2'
    
    def test_passport_api_routes_resolve(self):
        """Game Passport API routes should resolve"""
        routes = [
            ('user_profile:passport_toggle_lft', '/api/passports/toggle-lft/'),
            ('user_profile:passport_set_visibility', '/api/passports/set-visibility/'),
            ('user_profile:passport_pin', '/api/passports/pin/'),
            ('user_profile:passport_reorder', '/api/passports/reorder/'),
        ]
        
        for route_name, expected_path in routes:
            url = reverse(route_name)
            assert url == expected_path
            
            match = resolve(expected_path)
            assert match.namespace == 'user_profile'


@pytest.mark.django_db
class TestPublicProfileRoute:
    """Test GET /@username/ route behavior"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='publicuser',
            email='public@example.com',
            password='pass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.client = Client()
    
    def test_public_profile_loads_for_valid_user(self):
        """GET /@username/ should return 200 for valid user"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'publicuser'})
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert b'@publicuser' in response.content or b'publicuser' in response.content
    
    def test_public_profile_404_for_invalid_user(self):
        """GET /@nonexistent/ should return 404"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'nonexistent'})
        
        with pytest.raises(Http404):
            response = self.client.get(url)
    
    def test_public_profile_accessible_to_anonymous(self):
        """Anonymous users should be able to view public profiles"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'publicuser'})
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert not response.wsgi_request.user.is_authenticated
    
    def test_public_profile_accessible_to_authenticated(self):
        """Authenticated users should be able to view public profiles"""
        other_user = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='pass123'
        )
        self.client.force_login(other_user)
        
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'publicuser'})
        response = self.client.get(url)
        
        assert response.status_code == 200
    
    def test_public_profile_shows_edit_for_owner(self):
        """Owner should see edit actions on their own profile"""
        self.client.force_login(self.user)
        
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'publicuser'})
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert b'Edit Profile' in response.content or b'edit' in response.content.lower()


@pytest.mark.django_db
class TestOwnerOnlyRoutes:
    """Test owner-only routes (/me/...)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='owneruser',
            email='owner@example.com',
            password='pass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.client = Client()
    
    def test_settings_requires_authentication(self):
        """GET /me/settings/ should redirect anonymous users to login"""
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        assert response.status_code == 302  # Redirect to login
        assert '/login' in response.url or 'login' in response.url
    
    def test_settings_loads_for_authenticated_user(self):
        """GET /me/settings/ should return 200 for authenticated user"""
        self.client.force_login(self.user)
        
        url = reverse('user_profile:profile_settings_v2')
        response = self.client.get(url)
        
        assert response.status_code == 200
    
    def test_privacy_requires_authentication(self):
        """GET /me/privacy/ should redirect anonymous users to login"""
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        assert response.status_code == 302  # Redirect to login
    
    def test_privacy_loads_for_authenticated_user(self):
        """GET /me/privacy/ should return 200 for authenticated user"""
        self.client.force_login(self.user)
        
        url = reverse('user_profile:profile_privacy_v2')
        response = self.client.get(url)
        
        assert response.status_code == 200


@pytest.mark.django_db
class TestNoReverseMatchPrevention:
    """Test that common reverse patterns don't raise NoReverseMatch"""
    
    def test_namespaced_profile_settings_reverse(self):
        """user_profile:profile_settings_v2 should reverse correctly"""
        try:
            url = reverse('user_profile:profile_settings_v2')
            assert url is not None
        except Exception as e:
            pytest.fail(f"NoReverseMatch for 'user_profile:profile_settings_v2': {e}")
    
    def test_namespaced_profile_privacy_reverse(self):
        """user_profile:profile_privacy_v2 should reverse correctly"""
        try:
            url = reverse('user_profile:profile_privacy_v2')
            assert url is not None
        except Exception as e:
            pytest.fail(f"NoReverseMatch for 'user_profile:profile_privacy_v2': {e}")
    
    def test_namespaced_profile_public_reverse(self):
        """user_profile:profile_public_v2 should reverse correctly"""
        try:
            url = reverse('user_profile:profile_public_v2', kwargs={'username': 'test'})
            assert url is not None
        except Exception as e:
            pytest.fail(f"NoReverseMatch for 'user_profile:profile_public_v2': {e}")
    
    def test_namespaced_profile_activity_reverse(self):
        """user_profile:profile_activity_v2 should reverse correctly"""
        try:
            url = reverse('user_profile:profile_activity_v2', kwargs={'username': 'test'})
            assert url is not None
        except Exception as e:
            pytest.fail(f"NoReverseMatch for 'user_profile:profile_activity_v2': {e}")


@pytest.mark.django_db
class TestTemplateContextIntegration:
    """Test that templates can access reversed URLs without errors"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='templateuser',
            email='template@example.com',
            password='pass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_profile_page_contains_edit_link(self):
        """Profile page should contain edit profile link with correct URL"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'templateuser'})
        response = self.client.get(url)
        
        assert response.status_code == 200
        
        # Check that settings URL is in the page
        settings_url = reverse('user_profile:profile_settings_v2')
        content = response.content.decode('utf-8')
        assert settings_url in content, f"Settings URL {settings_url} not found in profile page"
    
    def test_profile_page_contains_privacy_link(self):
        """Profile page should contain privacy settings link with correct URL"""
        url = reverse('user_profile:profile_public_v2', kwargs={'username': 'templateuser'})
        response = self.client.get(url)
        
        assert response.status_code == 200
        
        # Check that privacy URL is in the page
        privacy_url = reverse('user_profile:profile_privacy_v2')
        content = response.content.decode('utf-8')
        assert privacy_url in content, f"Privacy URL {privacy_url} not found in profile page"


@pytest.mark.django_db
class TestBackwardCompatibility:
    """Test that alias routes maintain backward compatibility"""
    
    def test_profile_alias_works(self):
        """'user_profile:profile' alias should work"""
        url1 = reverse('user_profile:profile', kwargs={'username': 'test'})
        url2 = reverse('user_profile:profile_public_v2', kwargs={'username': 'test'})
        assert url1 == url2
    
    def test_settings_alias_works(self):
        """'user_profile:settings' alias should work"""
        url1 = reverse('user_profile:settings')
        url2 = reverse('user_profile:profile_settings_v2')
        assert url1 == url2


@pytest.mark.django_db
class TestGamePassportRoutes:
    """Test Game Passport API routes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='passportuser',
            email='passport@example.com',
            password='pass123'
        )
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_toggle_lft_route_accessible(self):
        """POST /api/passports/toggle-lft/ should be accessible"""
        url = reverse('user_profile:passport_toggle_lft')
        response = self.client.post(url, {'game': 'valorant'}, content_type='application/json')
        
        # Should not be 404 or 500 (may be 400 if validation fails, that's OK)
        assert response.status_code in [200, 400]
    
    def test_set_visibility_route_accessible(self):
        """POST /api/passports/set-visibility/ should be accessible"""
        url = reverse('user_profile:passport_set_visibility')
        response = self.client.post(url, {'game': 'valorant', 'visibility': 'PUBLIC'}, content_type='application/json')
        
        assert response.status_code in [200, 400]
    
    def test_pin_passport_route_accessible(self):
        """POST /api/passports/pin/ should be accessible"""
        url = reverse('user_profile:passport_pin')
        response = self.client.post(url, {'game': 'valorant', 'pin': True}, content_type='application/json')
        
        assert response.status_code in [200, 400]
    
    def test_reorder_passports_route_accessible(self):
        """POST /api/passports/reorder/ should be accessible"""
        url = reverse('user_profile:passport_reorder')
        response = self.client.post(url, {'game_order': ['valorant', 'cs2']}, content_type='application/json')
        
        assert response.status_code in [200, 400]
