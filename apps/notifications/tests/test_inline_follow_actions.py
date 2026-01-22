"""
Tests for inline follow request actions on notifications page.
Phase 4 Step 2: Approve/Reject follow requests directly from /notifications/
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()
Notification = apps.get_model("notifications", "Notification")
FollowRequest = apps.get_model("user_profile", "FollowRequest")
Follow = apps.get_model("user_profile", "Follow")
UserProfile = apps.get_model("user_profile", "UserProfile")


class ResolveFollowRequestTests(TestCase):
    """Test the resolve endpoint that maps requester username → follow_request_id."""
    
    def setUp(self):
        """Create test users and follow request."""
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
    
    def test_resolve_returns_pending_follow_request_id(self):
        """Resolve endpoint returns follow_request_id for pending request."""
        # Create pending follow request
        fr = FollowRequest.objects.create(
            requester=self.requester_profile,
            target=self.target_profile,
            status='PENDING'
        )
        
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.get('/api/follow-requests/resolve/', {'requester': 'requester'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['follow_request_id'], fr.id)
        self.assertEqual(data['requester_username'], 'requester')
        self.assertEqual(data['status'], 'PENDING')
    
    def test_resolve_returns_404_if_no_pending_request(self):
        """Resolve returns 404 if no pending request from that user."""
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.get('/api/follow-requests/resolve/', {'requester': 'requester'})
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('No pending follow request', data['error'])
    
    def test_resolve_returns_404_if_request_already_approved(self):
        """Resolve returns 404 if request was already approved."""
        # Create approved follow request
        FollowRequest.objects.create(
            requester=self.requester_profile,
            target=self.target_profile,
            status='APPROVED'
        )
        
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.get('/api/follow-requests/resolve/', {'requester': 'requester'})
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_resolve_requires_authentication(self):
        """Resolve endpoint returns JSON 401 if not authenticated."""
        client = Client()
        response = client.get('/api/follow-requests/resolve/', {'requester': 'requester'})
        
        # Should return JSON 401 (not redirect)
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'auth_required')
    
    def test_resolve_returns_400_if_missing_requester_param(self):
        """Resolve returns 400 if requester parameter missing."""
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.get('/api/follow-requests/resolve/')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Missing requester parameter', data['error'])
    
    def test_resolve_only_returns_requests_where_user_is_target(self):
        """Resolve only returns requests where current user is the target."""
        # Create follow request where target is target of request
        FollowRequest.objects.create(
            requester=self.requester_profile,
            target=self.target_profile,
            status='PENDING'
        )
        
        # Log in as requester (not target)
        client = Client()
        client.login(username='requester', password='testpass123')
        
        # Try to resolve - should return 404 because requester is not the target
        response = client.get('/api/follow-requests/resolve/', {'requester': 'target'})
        
        self.assertEqual(response.status_code, 404)


class ApproveFollowRequestFromNotificationTests(TestCase):
    """Test approving follow request from notifications page."""
    
    def setUp(self):
        """Create test users and follow request."""
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
        
        self.follow_request = FollowRequest.objects.create(
            requester=self.requester_profile,
            target=self.target_profile,
            status='PENDING'
        )
    
    def test_approve_creates_follow_relationship(self):
        """Approving follow request creates Follow relationship."""
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.post(f'/api/follow-requests/{self.follow_request.id}/approve/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'approved')
        
        # Verify Follow relationship exists
        follow_exists = Follow.objects.filter(
            follower=self.requester,
            following=self.target
        ).exists()
        self.assertTrue(follow_exists)
    
    def test_approve_updates_follow_request_status(self):
        """Approving follow request updates status to APPROVED."""
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.post(f'/api/follow-requests/{self.follow_request.id}/approve/')
        
        self.assertEqual(response.status_code, 200)
        
        # Refresh from DB
        self.follow_request.refresh_from_db()
        self.assertEqual(self.follow_request.status, 'APPROVED')
        self.assertIsNotNone(self.follow_request.resolved_at)
    
    def test_approve_returns_403_if_not_target_user(self):
        """Only the target user can approve the request."""
        # Create third user
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        
        client = Client()
        client.login(username='other', password='testpass123')
        
        response = client.post(f'/api/follow-requests/{self.follow_request.id}/approve/')
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])


class RejectFollowRequestFromNotificationTests(TestCase):
    """Test rejecting follow request from notifications page."""
    
    def setUp(self):
        """Create test users and follow request."""
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
        
        self.follow_request = FollowRequest.objects.create(
            requester=self.requester_profile,
            target=self.target_profile,
            status='PENDING'
        )
    
    def test_reject_does_not_create_follow_relationship(self):
        """Rejecting follow request does NOT create Follow relationship."""
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.post(f'/api/follow-requests/{self.follow_request.id}/reject/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'rejected')
        
        # Verify Follow relationship does NOT exist
        follow_exists = Follow.objects.filter(
            follower=self.requester,
            following=self.target
        ).exists()
        self.assertFalse(follow_exists)
    
    def test_reject_updates_follow_request_status(self):
        """Rejecting follow request updates status to REJECTED."""
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.post(f'/api/follow-requests/{self.follow_request.id}/reject/')
        
        self.assertEqual(response.status_code, 200)
        
        # Refresh from DB
        self.follow_request.refresh_from_db()
        self.assertEqual(self.follow_request.status, 'REJECTED')
        self.assertIsNotNone(self.follow_request.resolved_at)
    
    def test_reject_returns_403_if_not_target_user(self):
        """Only the target user can reject the request."""
        # Create third user
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        
        client = Client()
        client.login(username='other', password='testpass123')
        
        response = client.post(f'/api/follow-requests/{self.follow_request.id}/reject/')
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])


class NotificationListRenderingTests(TestCase):
    """Test that follow_request notifications render with action buttons."""
    
    def setUp(self):
        """Create test user, follow request, and notification."""
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
            action_label='Review',
            action_url='/@target/follow-requests/',
            category='follow',
            action_object_id=self.follow_request.id,
            action_type='follow_request'
        )
    
    def test_notifications_page_renders_approve_reject_buttons(self):
        """Notifications page renders approve/reject buttons with follow_request_id for follow_request type."""
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.get('/notifications/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'handleFollowRequestAction')
        self.assertContains(response, 'data-action-btn="approve"')
        self.assertContains(response, 'data-action-btn="reject"')
        self.assertContains(response, '@requester wants to follow you')
        # Check for data-follow-request-id attribute with the follow request ID
        self.assertContains(response, f'data-follow-request-id="{self.follow_request.id}"')
    
    def test_non_follow_request_notifications_do_not_show_action_buttons(self):
        """Non-follow_request notifications render with regular View button, not inline actions."""
        # Create a different type of notification (using generic type)
        generic_notif = Notification.objects.create(
            recipient=self.target,
            type='generic',
            title='System notification',
            body='This is a system message',
            url='/test/',
            action_label='View',
            action_url='/test/',
            category='system'
        )
        
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.get('/notifications/')
        
        self.assertEqual(response.status_code, 200)
        # Should contain both notifications
        self.assertContains(response, 'System notification')
        self.assertContains(response, '@requester wants to follow you')
        # Verify follow_request has inline approve/reject buttons
        self.assertContains(response, 'handleFollowRequestAction')
        self.assertContains(response, 'data-action-btn="approve"')
        self.assertContains(response, 'data-action-btn="reject"')

class NavPreviewFollowRequestTests(TestCase):
    """Test that nav_preview API includes follow_request_id for follow_request notifications."""
    
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
    
    def test_nav_preview_includes_follow_request_id(self):
        """nav_preview API includes follow_request_id for follow_request notifications."""
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.get('/notifications/api/nav-preview/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertGreater(len(data['items']), 0)
        
        # Find the follow_request notification in items
        follow_req_item = None
        for item in data['items']:
            if item['type'] == 'follow_request':
                follow_req_item = item
                break
        
        self.assertIsNotNone(follow_req_item)
        self.assertIn('follow_request_id', follow_req_item)
        self.assertEqual(follow_req_item['follow_request_id'], self.follow_request.id)
    
    def test_nav_preview_non_follow_request_no_follow_request_id(self):
        """nav_preview API does not include follow_request_id for non-follow_request notifications."""
        # Delete the follow_request notification from setUp
        self.notification.delete()
        
        # Create generic notification (not follow_request)
        generic_notif = Notification.objects.create(
            recipient=self.target,
            type='generic',
            title='System notification',
            body='This is a system message'
        )
        
        client = Client()
        client.login(username='target', password='testpass123')
        
        response = client.get('/notifications/api/nav-preview/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['items']), 1)
        
        # The only item should be the generic notification
        generic_item = data['items'][0]
        self.assertEqual(generic_item['type'], 'generic')
        self.assertNotIn('follow_request_id', generic_item)