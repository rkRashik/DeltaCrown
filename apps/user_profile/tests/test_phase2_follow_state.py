"""
Phase 2: Follow State Persistence Tests

Tests the new follow status endpoint and follow button state management:

1. Follow status endpoint (GET /api/profile/<username>/follow/status/)
2. Server-truth follow state on page load
3. JSON auth behavior (401 not redirect for unauthenticated)
4. Private account follow request flow
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile, FollowRequest, Follow, PrivacySettings

User = get_user_model()


class FollowStatusEndpointTestCase(TestCase):
    """Tests for the follow status endpoint"""
    
    def setUp(self):
        self.client = Client()
        
        # Create users
        self.user1 = User.objects.create_user(
            username='alice',
            email='alice@test.com',
            password='testpass123'
        )
        self.profile1, _ = UserProfile.objects.get_or_create(
            user=self.user1,
            defaults={'display_name': 'Alice'}
        )
        
        self.user2 = User.objects.create_user(
            username='bob',
            email='bob@test.com',
            password='testpass123'
        )
        self.profile2, _ = UserProfile.objects.get_or_create(
            user=self.user2,
            defaults={'display_name': 'Bob'}
        )
        
        self.private_user = User.objects.create_user(
            username='charlie_private',
            email='charlie@test.com',
            password='testpass123'
        )
        self.private_profile, _ = UserProfile.objects.get_or_create(
            user=self.private_user,
            defaults={'display_name': 'Charlie Private'}
        )
        
        # Make charlie_private a private account
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=self.private_profile)
        privacy.is_private_account = True
        privacy.save()
    
    def test_follow_status_unauthenticated(self):
        """Test that unauthenticated users get 401 (not redirect)"""
        response = self.client.get('/api/profile/bob/follow/status/')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertIn('Authentication required', data['error'])
    
    def test_follow_status_self(self):
        """Test follow status for viewing own profile"""
        self.client.login(username='alice', password='testpass123')
        
        response = self.client.get('/api/profile/alice/follow/status/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['state'], 'self')
        self.assertFalse(data['can_follow'])
    
    def test_follow_status_none(self):
        """Test follow status when not following"""
        self.client.login(username='alice', password='testpass123')
        
        response = self.client.get('/api/profile/bob/follow/status/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['state'], 'none')
        self.assertTrue(data['can_follow'])
        self.assertFalse(data['is_private_account'])
    
    def test_follow_status_following(self):
        """Test follow status when already following"""
        self.client.login(username='alice', password='testpass123')
        
        # Create follow relationship
        Follow.objects.create(follower=self.user1, following=self.user2)
        
        response = self.client.get('/api/profile/bob/follow/status/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['state'], 'following')
        self.assertFalse(data['can_follow'])  # Already following
    
    def test_follow_status_requested_private(self):
        """Test follow status when follow request is pending to private account"""
        self.client.login(username='alice', password='testpass123')
        
        # Create pending follow request
        FollowRequest.objects.create(
            requester=self.profile1,
            target=self.private_profile,
            status='PENDING'
        )
        
        response = self.client.get('/api/profile/charlie_private/follow/status/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['state'], 'requested')
        self.assertTrue(data['is_private_account'])
        self.assertFalse(data['can_follow'])  # Already requested
    
    def test_follow_status_private_account_no_request(self):
        """Test follow status for private account with no pending request"""
        self.client.login(username='alice', password='testpass123')
        
        response = self.client.get('/api/profile/charlie_private/follow/status/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['state'], 'none')
        self.assertTrue(data['is_private_account'])
        self.assertTrue(data['can_follow'])
    
    def test_follow_status_nonexistent_user(self):
        """Test follow status for non-existent user"""
        self.client.login(username='alice', password='testpass123')
        
        response = self.client.get('/api/profile/nonexistent/follow/status/')
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])


class FollowRequestWorkflowTestCase(TestCase):
    """Test complete private account follow request workflow"""
    
    def setUp(self):
        self.client = Client()
        
        # Public user
        self.public_user = User.objects.create_user(
            username='public_alice',
            email='public@test.com',
            password='testpass123'
        )
        self.public_profile, _ = UserProfile.objects.get_or_create(
            user=self.public_user,
            defaults={'display_name': 'Public Alice'}
        )
        
        # Private user
        self.private_user = User.objects.create_user(
            username='private_bob',
            email='private@test.com',
            password='testpass123'
        )
        self.private_profile, _ = UserProfile.objects.get_or_create(
            user=self.private_user,
            defaults={'display_name': 'Private Bob'}
        )
        
        # Make bob private
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=self.private_profile)
        privacy.is_private_account = True
        privacy.save()
    
    def test_follow_private_account_creates_request(self):
        """Test that following a private account creates a FollowRequest"""
        self.client.login(username='public_alice', password='testpass123')
        
        # Attempt to follow private account
        response = self.client.post('/api/profile/private_bob/follow/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'request_sent')
        self.assertIn('Follow request sent', data['message'])
        
        # Verify FollowRequest was created
        request_exists = FollowRequest.objects.filter(
            requester=self.public_profile,
            target=self.private_profile,
            status='PENDING'
        ).exists()
        self.assertTrue(request_exists)
        
        # Verify NO Follow relationship created yet
        follow_exists = Follow.objects.filter(
            follower=self.public_user,
            following=self.private_user
        ).exists()
        self.assertFalse(follow_exists)
    
    def test_approve_follow_request_creates_follow(self):
        """Test that approving a request creates a Follow relationship"""
        # Create pending request
        follow_request = FollowRequest.objects.create(
            requester=self.public_profile,
            target=self.private_profile,
            status='PENDING'
        )
        
        # Login as private user (target)
        self.client.login(username='private_bob', password='testpass123')
        
        # Approve the request
        response = self.client.post(f'/api/follow-requests/{follow_request.id}/approve/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'approved')
        self.assertTrue(data['is_following'])
        
        # Verify request status changed
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.status, 'APPROVED')
        
        # Verify Follow relationship created
        follow_exists = Follow.objects.filter(
            follower=self.public_user,
            following=self.private_user
        ).exists()
        self.assertTrue(follow_exists)
    
    def test_reject_follow_request_no_follow(self):
        """Test that rejecting a request does not create Follow"""
        # Create pending request
        follow_request = FollowRequest.objects.create(
            requester=self.public_profile,
            target=self.private_profile,
            status='PENDING'
        )
        
        # Login as private user (target)
        self.client.login(username='private_bob', password='testpass123')
        
        # Reject the request
        response = self.client.post(f'/api/follow-requests/{follow_request.id}/reject/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'rejected')
        self.assertFalse(data['is_following'])
        
        # Verify request status changed
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.status, 'REJECTED')
        
        # Verify NO Follow relationship
        follow_exists = Follow.objects.filter(
            follower=self.public_user,
            following=self.private_user
        ).exists()
        self.assertFalse(follow_exists)
    
    def test_follow_request_appears_in_inbox(self):
        """Test that pending requests appear in the inbox API"""
        # Create pending request
        FollowRequest.objects.create(
            requester=self.public_profile,
            target=self.private_profile,
            status='PENDING'
        )
        
        # Login as private user (target)
        self.client.login(username='private_bob', password='testpass123')
        
        # Get inbox
        response = self.client.get('/me/follow-requests/?status=PENDING')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['requests']), 1)
        self.assertEqual(data['requests'][0]['requester']['username'], 'public_alice')
        self.assertEqual(data['requests'][0]['status'], 'PENDING')
    
    def test_only_target_can_approve_request(self):
        """Test that only the target user can approve/reject requests"""
        # Create pending request from alice to bob
        follow_request = FollowRequest.objects.create(
            requester=self.public_profile,
            target=self.private_profile,
            status='PENDING'
        )
        
        # Login as alice (requester) - should NOT be able to approve own request
        self.client.login(username='public_alice', password='testpass123')
        
        response = self.client.post(f'/api/follow-requests/{follow_request.id}/approve/')
        
        # Should get 403 or 404
        self.assertIn(response.status_code, [403, 404])
        
        # Verify request status unchanged
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.status, 'PENDING')


class FollowStateIntegrationTestCase(TestCase):
    """Integration tests for follow state on profile page"""
    
    def setUp(self):
        self.client = Client()
        
        self.viewer = User.objects.create_user(
            username='viewer',
            email='viewer@test.com',
            password='testpass123'
        )
        self.viewer_profile, _ = UserProfile.objects.get_or_create(
            user=self.viewer,
            defaults={'display_name': 'Viewer'}
        )
        
        self.target = User.objects.create_user(
            username='target',
            email='target@test.com',
            password='testpass123'
        )
        self.target_profile, _ = UserProfile.objects.get_or_create(
            user=self.target,
            defaults={'display_name': 'Target'}
        )
    
    def test_profile_page_includes_follow_state_json(self):
        """Test that profile page includes follow state JSON blob"""
        self.client.login(username='viewer', password='testpass123')
        
        response = self.client.get(f'/@{self.target.username}/')
        
        self.assertEqual(response.status_code, 200)
        
        # Check that JSON state script is present
        self.assertContains(response, '<script id="profile-follow-state" type="application/json">')
        self.assertContains(response, '"profile_username"')
        self.assertContains(response, '"relationship_state"')
        self.assertContains(response, '"viewer_is_authenticated"')
    
    def test_profile_state_reflects_following(self):
        """Test that state JSON reflects following status"""
        self.client.login(username='viewer', password='testpass123')
        
        # Create follow
        Follow.objects.create(follower=self.viewer, following=self.target)
        
        response = self.client.get(f'/@{self.target.username}/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"relationship_state": "following"')
