"""
Tests for UP-CLEANUP-04 Phase C Part 1: Safe Mutation Endpoints

Coverage:
- Privacy settings save (audit + privacy enforcement)
- Follow/unfollow (privacy + audit + idempotency)

Tests (10 total, 2 per endpoint):
- Functionality tests (200 status, correct behavior)
- Audit/privacy tests (audit events created, privacy enforced)
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.user_profile.models import UserProfile, PrivacySettings
from apps.user_profile.models_main import Follow
from apps.user_profile.models.audit import UserAuditEvent

User = get_user_model()


@pytest.fixture
def alice(db):
    """Create test user alice with profile."""
    user = User.objects.create_user(
        username='alice_cleanup04',
        email='alice@test.com',
        password='pass123'
    )
    UserProfile.objects.get_or_create(user=user)
    return user


@pytest.fixture
def bob(db):
    """Create test user bob with profile."""
    user = User.objects.create_user(
        username='bob_cleanup04',
        email='bob@test.com',
        password='pass123'
    )
    UserProfile.objects.get_or_create(user=user)
    return user


@pytest.mark.django_db
class TestPrivacySettingsSafe:
    """Test safe privacy settings endpoint."""
    
    def test_privacy_update_works(self, client: Client, alice):
        """Privacy settings update returns 302 and saves correctly."""
        client.force_login(alice)
        
        response = client.post('/actions/privacy-settings/save/', {
            'show_email': 'on',  # Checkbox value
            'show_phone': '',  # Unchecked
            'show_real_name': 'on',
            'show_age': '',
            'show_country': 'on',
            'show_socials': 'on',
            'allow_friend_requests': 'on',
        })
        
        assert response.status_code == 302  # Redirect
        
        # Verify settings saved
        privacy = PrivacySettings.objects.get(user_profile__user=alice)
        assert privacy.show_email is True
        assert privacy.show_phone is False
        assert privacy.show_real_name is True
        assert privacy.allow_friend_requests is True
    
    def test_privacy_update_creates_audit_event(self, client: Client, alice):
        """Privacy update records audit event."""
        client.force_login(alice)
        initial_count = UserAuditEvent.objects.count()
        
        client.post('/actions/privacy-settings/save/', {
            'show_email': 'on',
            'allow_friend_requests': '',
        })
        
        # Verify audit event created
        assert UserAuditEvent.objects.count() == initial_count + 1
        
        audit = UserAuditEvent.objects.latest('created_at')
        assert audit.event_type == UserAuditEvent.EventType.PRIVACY_SETTINGS_CHANGED
        assert audit.subject_user_id == alice.id
        assert audit.actor_user_id == alice.id
        assert audit.source_app == 'user_profile'
        assert audit.object_type == 'PrivacySettings'


@pytest.mark.django_db
class TestFollowSafe:
    """Test safe follow endpoint."""
    
    def test_follow_works(self, client: Client, alice, bob):
        """Follow endpoint returns 200 and creates follow."""
        client.force_login(alice)
        
        response = client.post(f'/actions/follow-safe/{bob.username}/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['status'] == 'following'
        assert 'follower_count' in data
        
        # Verify follow created
        assert Follow.objects.filter(
            follower=alice,
            following=bob
        ).exists()
    
    def test_follow_creates_audit_event(self, client: Client, alice, bob):
        """Follow records audit event."""
        client.force_login(alice)
        initial_count = UserAuditEvent.objects.count()
        
        client.post(f'/actions/follow-safe/{bob.username}/')
        
        # Verify audit event
        assert UserAuditEvent.objects.count() == initial_count + 1
        
        audit = UserAuditEvent.objects.latest('created_at')
        assert audit.event_type == UserAuditEvent.EventType.FOLLOW_CREATED
        assert audit.subject_user_id == bob.id
        assert audit.actor_user_id == alice.id
        assert audit.metadata['followee_username'] == bob.username
    
    def test_follow_respects_privacy(self, client: Client, alice, bob):
        """Follow denied if user disabled friend requests."""
        client.force_login(alice)
        
        # Bob disables friend requests
        bob_profile = UserProfile.objects.get(user=bob)
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=bob_profile)
        privacy.allow_friend_requests = False
        privacy.save()
        
        response = client.post(f'/actions/follow-safe/{bob.username}/')
        
        assert response.status_code == 403
        data = response.json()
        assert 'error' in data
        assert 'not accepting' in data['error'].lower()
        
        # Verify follow NOT created
        assert not Follow.objects.filter(
            follower=alice,
            following=bob
        ).exists()
    
    def test_follow_idempotent(self, client: Client, alice, bob):
        """Follow twice returns 200 both times (idempotent)."""
        client.force_login(alice)
        
        # First follow
        response1 = client.post(f'/actions/follow-safe/{bob.username}/')
        assert response1.status_code == 200
        
        # Second follow (idempotent)
        response2 = client.post(f'/actions/follow-safe/{bob.username}/')
        assert response2.status_code == 200
        
        # Only 1 follow exists
        assert Follow.objects.filter(
            follower=alice,
            following=bob
        ).count() == 1


@pytest.mark.django_db
class TestUnfollowSafe:
    """Test safe unfollow endpoint."""
    
    def test_unfollow_works(self, client: Client, alice, bob):
        """Unfollow endpoint returns 200 and deletes follow."""
        client.force_login(alice)
        
        # Create follow first
        Follow.objects.create(follower=alice, following=bob)
        
        response = client.post(f'/actions/unfollow-safe/{bob.username}/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['status'] == 'unfollowed'
        assert data['was_following'] is True
        
        # Verify follow deleted
        assert not Follow.objects.filter(
            follower=alice,
            following=bob
        ).exists()
    
    def test_unfollow_creates_audit_event(self, client: Client, alice, bob):
        """Unfollow records audit event."""
        client.force_login(alice)
        
        # Create follow first
        Follow.objects.create(follower=alice, following=bob)
        
        initial_count = UserAuditEvent.objects.count()
        
        client.post(f'/actions/unfollow-safe/{bob.username}/')
        
        # Verify audit event
        assert UserAuditEvent.objects.count() == initial_count + 1
        
        audit = UserAuditEvent.objects.latest('created_at')
        assert audit.event_type == UserAuditEvent.EventType.FOLLOW_DELETED
        assert audit.subject_user_id == bob.id
        assert audit.actor_user_id == alice.id
    
    def test_unfollow_idempotent(self, client: Client, alice, bob):
        """Unfollow twice returns 200 both times (idempotent)."""
        client.force_login(alice)
        
        # Create follow first
        Follow.objects.create(follower=alice, following=bob)
        
        # First unfollow
        response1 = client.post(f'/actions/unfollow-safe/{bob.username}/')
        assert response1.status_code == 200
        assert response1.json()['was_following'] is True
        
        # Second unfollow (idempotent)
        response2 = client.post(f'/actions/unfollow-safe/{bob.username}/')
        assert response2.status_code == 200
        assert response2.json()['was_following'] is False  # Not following anymore
        
        # No follows exist
        assert Follow.objects.filter(
            follower=alice,
            following=bob
        ).count() == 0
