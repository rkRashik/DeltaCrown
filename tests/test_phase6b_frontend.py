"""
Phase 6B: Private Account Frontend Integration Tests

Tests for:
- Privacy settings save endpoint accepting is_private_account
- Profile view context contains follow request status
- ProfilePermissionChecker using private account logic
- Private profile wall rendering with request status
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.http import JsonResponse
import json

from apps.user_profile.models_main import UserProfile, PrivacySettings, Follow, FollowRequest
from apps.user_profile.services.follow_service import FollowService
from apps.user_profile.services.profile_permissions import ProfilePermissionChecker

User = get_user_model()


@pytest.mark.django_db
class TestPrivacySettingsSave:
    """Test privacy settings API accepts and persists is_private_account"""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(username='testuser', email='test@test.com', password='test123')
    
    @pytest.fixture
    def client_logged_in(self, user):
        client = Client()
        client.force_login(user)
        return client
    
    def test_save_privacy_accepts_is_private_account(self, client_logged_in, user):
        """Test that update_privacy_settings endpoint accepts is_private_account"""
        url = reverse('user_profile:update_privacy_settings')
        
        response = client_logged_in.post(
            url,
            data=json.dumps({
                'is_private_account': True,
                'show_real_name': False
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify database persisted
        profile = UserProfile.objects.get(user=user)
        privacy = PrivacySettings.objects.get(user_profile=profile)
        assert privacy.is_private_account is True
    
    def test_get_privacy_returns_is_private_account(self, client_logged_in, user):
        """Test that get_privacy_settings endpoint returns is_private_account"""
        # Set is_private_account
        profile = UserProfile.objects.get(user=user)
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=profile)
        privacy.is_private_account = True
        privacy.save()
        
        url = reverse('user_profile:get_privacy_settings')
        response = client_logged_in.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['settings']['is_private_account'] is True
    
    def test_default_is_private_account_false(self, client_logged_in, user):
        """Test that is_private_account defaults to False"""
        url = reverse('user_profile:get_privacy_settings')
        response = client_logged_in.get(url)
        
        data = response.json()
        # Should default to False for new users
        assert data['settings']['is_private_account'] is False


@pytest.mark.django_db
class TestProfileContextFollowStatus:
    """Test profile view includes follow request status in context"""
    
    @pytest.fixture
    def public_user(self):
        return User.objects.create_user(username='public', email='public@test.com', password='test123')
    
    @pytest.fixture
    def private_user(self):
        user = User.objects.create_user(username='private', email='private@test.com', password='test123')
        profile = UserProfile.objects.get(user=user)
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=profile)
        privacy.is_private_account = True
        privacy.save()
        return user
    
    @pytest.fixture
    def viewer(self):
        return User.objects.create_user(username='viewer', email='viewer@test.com', password='test123')
    
    def test_profile_context_has_is_following(self, viewer, public_user):
        """Test profile view context includes is_following"""
        client = Client()
        client.force_login(viewer)
        
        response = client.get(f'/@{public_user.username}/')
        
        assert response.status_code == 200
        assert 'is_following' in response.context
        assert response.context['is_following'] is False
        
        # After following
        FollowService.follow_user(follower_user=viewer, followee_username=public_user.username)
        response = client.get(f'/@{public_user.username}/')
        assert response.context['is_following'] is True
    
    def test_profile_context_has_pending_request_status(self, viewer, private_user):
        """Test profile view context includes has_pending_request"""
        client = Client()
        client.force_login(viewer)
        
        # Private profile should block access but pass has_pending_request to template
        response = client.get(f'/@{private_user.username}/')
        
        # Should render private profile wall
        assert response.status_code == 200
        assert any('profile_private.html' in t.name for t in response.templates)
        assert 'has_pending_request' in response.context
        assert response.context['has_pending_request'] is False
        
        # After requesting
        FollowService.follow_user(follower_user=viewer, followee_username=private_user.username)
        response = client.get(f'/@{private_user.username}/')
        assert response.context['has_pending_request'] is True
    
    def test_owner_profile_no_follow_status(self, public_user):
        """Test own profile doesn't have follow status (can't follow yourself)"""
        client = Client()
        client.force_login(public_user)
        
        response = client.get(f'/@{public_user.username}/')
        
        assert response.status_code == 200
        assert response.context.get('is_following') is False
        assert response.context.get('has_pending_request') is False


@pytest.mark.django_db
class TestProfilePermissionCheckerPrivateAccount:
    """Test ProfilePermissionChecker integrates Phase 6A private account logic"""
    
    @pytest.fixture
    def private_user(self):
        user = User.objects.create_user(username='private', email='private@test.com', password='test123')
        profile = UserProfile.objects.get(user=user)
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=profile)
        privacy.is_private_account = True
        privacy.save()
        return user
    
    @pytest.fixture
    def viewer(self):
        return User.objects.create_user(username='viewer', email='viewer@test.com', password='test123')
    
    def test_anonymous_cannot_see_private_profile(self, private_user):
        """Test anonymous users blocked from private profiles"""
        profile = UserProfile.objects.get(user=private_user)
        checker = ProfilePermissionChecker(viewer=None, profile=profile)
        
        assert checker.can_view_profile() is False
    
    def test_visitor_cannot_see_private_profile(self, viewer, private_user):
        """Test non-followers blocked from private profiles"""
        profile = UserProfile.objects.get(user=private_user)
        checker = ProfilePermissionChecker(viewer=viewer, profile=profile)
        
        assert checker.can_view_profile() is False
    
    def test_approved_follower_can_see_private_profile(self, viewer, private_user):
        """Test approved followers can see private profiles"""
        # Request and approve
        request_obj, _ = FollowService.follow_user(viewer, private_user.username)
        FollowService.approve_follow_request(private_user, request_obj.id)
        
        profile = UserProfile.objects.get(user=private_user)
        checker = ProfilePermissionChecker(viewer=viewer, profile=profile)
        
        assert checker.can_view_profile() is True
    
    def test_owner_can_see_own_private_profile(self, private_user):
        """Test owner always sees own private profile"""
        profile = UserProfile.objects.get(user=private_user)
        checker = ProfilePermissionChecker(viewer=private_user, profile=profile)
        
        assert checker.can_view_profile() is True


@pytest.mark.django_db
class TestPrivateProfileWall:
    """Test private profile wall renders correctly with follow request status"""
    
    @pytest.fixture
    def private_user(self):
        user = User.objects.create_user(username='private', email='private@test.com', password='test123')
        profile = UserProfile.objects.get(user=user)
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=profile)
        privacy.is_private_account = True
        privacy.save()
        return user
    
    @pytest.fixture
    def viewer(self):
        return User.objects.create_user(username='viewer', email='viewer@test.com', password='test123')
    
    def test_private_wall_shows_send_request_button(self, viewer, private_user):
        """Test private profile wall shows 'Send Follow Request' button"""
        client = Client()
        client.force_login(viewer)
        
        response = client.get(f'/@{private_user.username}/')
        
        assert response.status_code == 200
        assert any('profile_private.html' in t.name for t in response.templates)
        
        content = response.content.decode()
        assert 'Send Follow Request' in content or 'sendFollowRequest' in content
    
    def test_private_wall_shows_pending_status(self, viewer, private_user):
        """Test private profile wall shows 'Request Pending' when request sent"""
        client = Client()
        client.force_login(viewer)
        
        # Send follow request
        FollowService.follow_user(viewer, private_user.username)
        
        response = client.get(f'/@{private_user.username}/')
        
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Request Pending' in content or 'pending' in content.lower()
    
    def test_anonymous_sees_login_button(self, private_user):
        """Test anonymous users see login button on private profile wall"""
        client = Client()
        
        response = client.get(f'/@{private_user.username}/')
        
        assert response.status_code == 200
        assert any('profile_private.html' in t.name for t in response.templates)
        content = response.content.decode()
        assert 'Log In' in content or 'login' in content.lower()


@pytest.mark.django_db
class TestFollowRequestAPIIntegration:
    """Test follow request API endpoints work with frontend"""
    
    @pytest.fixture
    def private_user(self):
        user = User.objects.create_user(username='private', email='private@test.com', password='test123')
        profile = UserProfile.objects.get(user=user)
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=profile)
        privacy.is_private_account = True
        privacy.save()
        return user
    
    @pytest.fixture
    def requester(self):
        return User.objects.create_user(username='requester', email='requester@test.com', password='test123')
    
    def test_follow_api_returns_request_sent_for_private(self, requester, private_user):
        """Test POST /profiles/<username>/follow/ returns action='request_sent' for private accounts"""
        client = Client()
        client.force_login(requester)
        
        url = reverse('user_profile:follow_user_api', kwargs={'username': private_user.username})
        response = client.post(url)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['action'] == 'request_sent'
        assert data['has_pending_request'] is True
    
    def test_get_follow_requests_lists_incoming(self, requester, private_user):
        """Test GET /me/follow-requests/ lists incoming requests"""
        # Create request
        FollowService.follow_user(requester, private_user.username)
        
        client = Client()
        client.force_login(private_user)
        
        url = reverse('user_profile:get_follow_requests_api')
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['count'] == 1
        assert data['requests'][0]['requester']['username'] == 'requester'
    
    def test_respond_to_request_approves(self, requester, private_user):
        """Test POST /profiles/<username>/follow/respond/ with action='approve'"""
        # Create request
        request_obj, _ = FollowService.follow_user(requester, private_user.username)
        
        client = Client()
        client.force_login(private_user)
        
        url = reverse('user_profile:respond_to_follow_request_api', kwargs={'username': requester.username})
        response = client.post(
            url,
            data=json.dumps({'request_id': request_obj.id, 'action': 'approve'}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['action'] == 'approved'
        assert data['is_following'] is True
        
        # Verify Follow created
        assert Follow.objects.filter(follower=requester, following=private_user).exists()
