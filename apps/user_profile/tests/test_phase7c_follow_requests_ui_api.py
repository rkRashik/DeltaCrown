"""
Phase 7C Follow Requests UI/API Integration Tests

Tests the follow requests management UI from Settings → Privacy & Visibility
when user has enabled 'is_private_account'. Covers:

1. Listing pending follow requests
2. Approving follow requests
3. Rejecting follow requests

Related to PHASE 6A private account feature.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile, FollowRequest, Follow

User = get_user_model()


class FollowRequestsUIAPITestCase(TestCase):
    """Integration tests for follow requests UI APIs"""
    
    def setUp(self):
        self.client = Client()
        
        # Create private user (receives follow requests)
        self.private_user = User.objects.create_user(
            username='privateuser',
            email='private@test.com',
            password='testpass123'
        )
        self.private_profile, _ = UserProfile.objects.get_or_create(
            user=self.private_user,
            defaults={'display_name': 'Private User'}
        )
        
        # Create requesters
        self.requester1 = User.objects.create_user(
            username='requester1',
            email='req1@test.com',
            password='testpass123'
        )
        self.requester1_profile, _ = UserProfile.objects.get_or_create(
            user=self.requester1,
            defaults={'display_name': 'Requester One'}
        )
        
        self.requester2 = User.objects.create_user(
            username='requester2',
            email='req2@test.com',
            password='testpass123'
        )
        self.requester2_profile, _ = UserProfile.objects.get_or_create(
            user=self.requester2,
            defaults={'display_name': 'Requester Two'}
        )
        
        # Login as private user
        self.client.login(username='privateuser', password='testpass123')
    
    def test_list_pending_requests(self):
        """Test listing pending follow requests"""
        # Create pending follow requests
        FollowRequest.objects.create(
            requester=self.requester1_profile,
            target=self.private_profile,
            status='PENDING'
        )
        FollowRequest.objects.create(
            requester=self.requester2_profile,
            target=self.private_profile,
            status='PENDING'
        )
        
        response = self.client.get('/me/follow-requests/?status=PENDING')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['requests']), 2)
        
        # Verify request structure
        request_data = data['requests'][0]
        self.assertIn('id', request_data)
        self.assertIn('requester', request_data)
        self.assertIn('username', request_data['requester'])
        self.assertIn('display_name', request_data['requester'])
        self.assertEqual(request_data['status'], 'PENDING')
    
    def test_approve_follow_request(self):
        """Test approving a follow request"""
        # Create pending request
        follow_request = FollowRequest.objects.create(
            requester=self.requester1_profile,
            target=self.private_profile,
            status='PENDING'
        )
        
        payload = {
            'action': 'approve'
        }
        
        response = self.client.post(
            f'/profiles/{self.requester1.username}/follow/respond/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify request status changed
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.status, 'APPROVED')
        
        # Verify Follow relationship created
        follow_exists = Follow.objects.filter(
            follower=self.requester1,
            followed=self.private_user
        ).exists()
        self.assertTrue(follow_exists)
    
    def test_reject_follow_request(self):
        """Test rejecting a follow request"""
        # Create pending request
        follow_request = FollowRequest.objects.create(
            requester=self.requester1_profile,
            target=self.private_profile,
            status='PENDING'
        )
        
        payload = {
            'action': 'reject'
        }
        
        response = self.client.post(
            f'/profiles/{self.requester1.username}/follow/respond/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify request status changed
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.status, 'REJECTED')
        
        # Verify NO Follow relationship created
        follow_exists = Follow.objects.filter(
            follower=self.requester1,
            followed=self.private_user
        ).exists()
        self.assertFalse(follow_exists)
    
    def test_list_no_pending_requests(self):
        """Test listing when no pending requests"""
        response = self.client.get('/me/follow-requests/?status=PENDING')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['requests']), 0)
    
    def test_approve_request_permissions(self):
        """Test that users can only approve requests to themselves"""
        # Create request to private_user
        follow_request = FollowRequest.objects.create(
            requester=self.requester1_profile,
            target=self.private_profile,
            status='PENDING'
        )
        
        # Login as different user (requester2)
        self.client.logout()
        self.client.login(username='requester2', password='testpass123')
        
        payload = {'action': 'approve'}
        
        # Try to approve request to private_user (should fail)
        response = self.client.post(
            f'/profiles/{self.requester1.username}/follow/respond/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should get 403 or 404 (not allowed to approve others' requests)
        self.assertIn(response.status_code, [403, 404])
