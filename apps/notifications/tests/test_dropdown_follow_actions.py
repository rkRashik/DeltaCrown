"""
Tests for Phase 4 Step 3: Inline approve/reject in dropdown
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()
Notification = apps.get_model("notifications", "Notification")
FollowRequest = apps.get_model("user_profile", "FollowRequest")
Follow = apps.get_model("user_profile", "Follow")
UserProfile = apps.get_model("user_profile", "UserProfile")


class DropdownFollowRequestIntegrationTests(TestCase):
    """Integration tests for dropdown approve/reject flow."""
    
    def setUp(self):
        """Create test users, follow request, and notification."""
        self.requester = User.objects.create_user(
            username='requester',
            email='requester@example.com',
            password='testpass123'
        )
        self.target = User.objects.create_user(
            username='target',
            email='target@example.com',
            password='testpass123'
        )
        
        self.requester_profile, _ = UserProfile.objects.get_or_create(user=self.requester)
        self.target_profile, _ = UserProfile.objects.get_or_create(user=self.target)
        
        # Create follow request
        self.follow_request = FollowRequest.objects.create(
            requester=self.requester_profile,
            target=self.target_profile,
            status='PENDING'
        )
        
        # Create follow_request notification with action_object_id
        self.notification = Notification.objects.create(
            recipient=self.target,
            type='follow_request',
            title='@requester wants to follow you',
            body='requester sent you a follow request.',
            url='/@target/follow-requests/',
            action_object_id=self.follow_request.id,
            action_type='follow_request'
        )
    
    def test_approve_from_dropdown_creates_follow_and_updates_nav_preview(self):
        """Approving from dropdown creates Follow and updates nav-preview response."""
        client = Client()
        client.login(username='target', password='testpass123')
        
        # Step 1: Call nav-preview - should show follow_request notification
        response = client.get('/notifications/api/nav-preview/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['type'], 'follow_request')
        self.assertEqual(data['items'][0]['follow_request_id'], self.follow_request.id)
        self.assertEqual(data['pending_follow_requests'], 1)
        
        # Step 2: Approve the request
        approve_response = client.post(f'/api/follow-requests/{self.follow_request.id}/approve/')
        self.assertEqual(approve_response.status_code, 200)
        approve_data = approve_response.json()
        self.assertTrue(approve_data['success'])
        self.assertEqual(approve_data['action'], 'approved')
        
        # Step 3: Verify Follow relationship created
        follow_exists = Follow.objects.filter(
            follower=self.requester,
            following=self.target
        ).exists()
        self.assertTrue(follow_exists)
        
        # Step 4: Verify FollowRequest status updated
        self.follow_request.refresh_from_db()
        self.assertEqual(self.follow_request.status, 'APPROVED')
        self.assertIsNotNone(self.follow_request.resolved_at)
        
        # Step 5: Call nav-preview again - pending_follow_requests should be 0
        response2 = client.get('/notifications/api/nav-preview/')
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertTrue(data2['success'])
        self.assertEqual(data2['pending_follow_requests'], 0)
    
    def test_reject_from_dropdown_does_not_create_follow(self):
        """Rejecting from dropdown does NOT create Follow relationship."""
        client = Client()
        client.login(username='target', password='testpass123')
        
        # Reject the request
        response = client.post(f'/api/follow-requests/{self.follow_request.id}/reject/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'rejected')
        
        # Verify NO Follow relationship created
        follow_exists = Follow.objects.filter(
            follower=self.requester,
            following=self.target
        ).exists()
        self.assertFalse(follow_exists)
        
        # Verify FollowRequest status updated
        self.follow_request.refresh_from_db()
        self.assertEqual(self.follow_request.status, 'REJECTED')
        
        # Verify nav-preview pending count decreased
        response2 = client.get('/notifications/api/nav-preview/')
        data2 = response2.json()
        self.assertEqual(data2['pending_follow_requests'], 0)
    
    def test_approve_requires_target_user_permission(self):
        """Only the target user can approve the follow request."""
        # Create third user
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        
        client = Client()
        client.login(username='other', password='testpass123')
        
        # Try to approve someone else's request
        response = client.post(f'/api/follow-requests/{self.follow_request.id}/approve/')
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        # Check error message contains expected text
        error_msg = data.get('error', '').lower()
        self.assertTrue('target' in error_msg or 'approve' in error_msg)
    
    def test_reject_requires_target_user_permission(self):
        """Only the target user can reject the follow request."""
        # Create third user
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        
        client = Client()
        client.login(username='other', password='testpass123')
        
        # Try to reject someone else's request
        response = client.post(f'/api/follow-requests/{self.follow_request.id}/reject/')
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])


class NavPreviewSerializationTests(TestCase):
    """Test nav-preview API serialization for dropdown rendering."""
    
    def setUp(self):
        """Create test users."""
        self.requester = User.objects.create_user(
            username='requester',
            email='requester@example.com',
            password='testpass123'
        )
        self.target = User.objects.create_user(
            username='target',
            email='target@example.com',
            password='testpass123'
        )
        
        self.requester_profile, _ = UserProfile.objects.get_or_create(user=self.requester)
        self.target_profile, _ = UserProfile.objects.get_or_create(user=self.target)
    
    def test_nav_preview_includes_all_required_fields(self):
        """nav-preview includes all fields needed for dropdown rendering."""
        # Create notification
        notif = Notification.objects.create(
            recipient=self.target,
            type='generic',
            title='Test notification',
            message='Test message',
            url='/test/',
            is_read=False
        )
        
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.get('/notifications/api/nav-preview/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['items']), 1)
        
        item = data['items'][0]
        # Check required fields
        self.assertIn('id', item)
        self.assertIn('type', item)
        self.assertIn('title', item)
        self.assertIn('message', item)
        self.assertIn('url', item)
        self.assertIn('created_at', item)
        self.assertIn('is_read', item)
        
        # Verify values
        self.assertEqual(item['id'], notif.id)
        self.assertEqual(item['type'], 'generic')
        self.assertEqual(item['title'], 'Test notification')
        self.assertEqual(item['message'], 'Test message')
        self.assertFalse(item['is_read'])
    
    def test_nav_preview_includes_follow_request_id_for_follow_requests(self):
        """nav-preview includes follow_request_id for follow_request notifications."""
        # Create follow request
        follow_request = FollowRequest.objects.create(
            requester=self.requester_profile,
            target=self.target_profile,
            status='PENDING'
        )
        
        # Create notification with action_object_id
        notif = Notification.objects.create(
            recipient=self.target,
            type='follow_request',
            title='@requester wants to follow you',
            message='requester sent you a follow request.',
            action_object_id=follow_request.id,
            action_type='follow_request'
        )
        
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.get('/notifications/api/nav-preview/')
        data = response.json()
        
        item = data['items'][0]
        self.assertIn('follow_request_id', item)
        self.assertEqual(item['follow_request_id'], follow_request.id)
    
    def test_nav_preview_omits_follow_request_id_for_non_follow_requests(self):
        """nav-preview does NOT include follow_request_id for other notification types."""
        # Create generic notification
        Notification.objects.create(
            recipient=self.target,
            type='generic',
            title='Generic notification'
        )
        
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.get('/notifications/api/nav-preview/')
        data = response.json()
        
        item = data['items'][0]
        self.assertNotIn('follow_request_id', item)
    
    def test_nav_preview_pending_count_accurate(self):
        """nav-preview pending_follow_requests count is accurate."""
        client = Client()
        client.login(username='target', password='testpass123')
        
        # Initially no pending requests
        response = client.get('/notifications/api/nav-preview/')
        data = response.json()
        self.assertEqual(data['pending_follow_requests'], 0)
        
        # Create 2 pending requests
        for i in range(2):
            other_user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='testpass123'
            )
            other_profile, _ = UserProfile.objects.get_or_create(user=other_user)
            
            FollowRequest.objects.create(
                requester=other_profile,
                target=self.target_profile,
                status='PENDING'
            )
        
        # Check count increased
        response2 = client.get('/notifications/api/nav-preview/')
        data2 = response2.json()
        self.assertEqual(data2['pending_follow_requests'], 2)


class DropdownAuthTests(TestCase):
    """Test authentication for dropdown-related endpoints."""
    
    def test_nav_preview_requires_auth_json_401(self):
        """nav-preview returns JSON 401 if not authenticated (not redirect)."""
        client = Client()
        response = client.get('/notifications/api/nav-preview/')
        
        # Should return JSON 401, not 302 redirect
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'auth_required')
    
    def test_approve_endpoint_requires_auth(self):
        """approve endpoint requires authentication."""
        client = Client()
        response = client.post('/api/follow-requests/999/approve/')
        
        # Should return 302 redirect to login (approve endpoint uses @login_required)
        # NOTE: This could be improved to use JSON 401 in future, but not required for Step 3
        self.assertIn(response.status_code, [302, 401])
    
    def test_reject_endpoint_requires_auth(self):
        """reject endpoint requires authentication."""
        client = Client()
        response = client.post('/api/follow-requests/999/reject/')
        
        # Should return 302 redirect to login
        self.assertIn(response.status_code, [302, 401])


class DropdownMessageFieldTests(TestCase):
    """Test that message field is properly populated for dropdown rendering."""
    
    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_notification_message_field_used_in_nav_preview(self):
        """nav-preview uses message field if available."""
        notif = Notification.objects.create(
            recipient=self.user,
            type='generic',
            title='Test Title',
            message='This is the message field',
            body='This is the body field'
        )
        
        client = Client()
        client.login(username='testuser', password='testpass123')
        
        response = client.get('/notifications/api/nav-preview/')
        data = response.json()
        
        # Should prefer message over body
        self.assertEqual(data['items'][0]['message'], 'This is the message field')
    
    def test_notification_body_fallback_in_nav_preview(self):
        """nav-preview falls back to body if message is blank."""
        notif = Notification.objects.create(
            recipient=self.user,
            type='generic',
            title='Test Title',
            message='',  # Empty message
            body='This is the body field'
        )
        
        client = Client()
        client.login(username='testuser', password='testpass123')
        
        response = client.get('/notifications/api/nav-preview/')
        data = response.json()
        
        # Should fall back to body
        self.assertEqual(data['items'][0]['message'], 'This is the body field')
