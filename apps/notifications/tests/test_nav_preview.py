"""
Tests for nav_preview API endpoint.
Phase 4 Step 1.1: Notification dropdown data source.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.notifications.models import Notification
from apps.user_profile.models_main import UserProfile, FollowRequest


User = get_user_model()


class NavPreviewTestCase(TestCase):
    """Test suite for /notifications/api/nav-preview/ endpoint"""
    
    def setUp(self):
        """Create test users and client"""
        self.client = Client()
        
        # User 1 (will have notifications)
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        # Profile is auto-created by signal
        self.profile1 = UserProfile.objects.get(user=self.user1)
        self.profile1.display_name = 'Test User 1'
        self.profile1.save()
        
        # User 2 (for multi-user tests)
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        # Profile is auto-created by signal
        self.profile2 = UserProfile.objects.get(user=self.user2)
        self.profile2.display_name = 'Test User 2'
        self.profile2.save()
        
        self.url = reverse('notifications:nav_preview')
    
    def test_anonymous_returns_401_json(self):
        """
        Test that anonymous users get 401 JSON response (not 302 redirect).
        Critical: API endpoints must return JSON, never HTML redirects.
        """
        response = self.client.get(self.url)
        
        # Must be 401, not 302
        self.assertEqual(response.status_code, 401)
        
        # Must be JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Must have correct structure
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'auth_required')
    
    def test_authenticated_returns_200_and_structure(self):
        """
        Test that authenticated users get 200 with correct JSON structure.
        """
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.get(self.url)
        
        # Must be 200
        self.assertEqual(response.status_code, 200)
        
        # Must be JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse response
        data = json.loads(response.content)
        
        # Verify structure
        self.assertTrue(data['success'])
        self.assertIn('unread_count', data)
        self.assertIn('pending_follow_requests', data)
        self.assertIn('items', data)
        
        # Verify types
        self.assertIsInstance(data['unread_count'], int)
        self.assertIsInstance(data['pending_follow_requests'], int)
        self.assertIsInstance(data['items'], list)
    
    def test_only_returns_current_user_notifications(self):
        """
        Test that endpoint only returns notifications for authenticated user.
        Security: Users must not see other users' notifications.
        """
        # Create notification for user1
        notif1 = Notification.objects.create(
            recipient=self.user1,
            type=Notification.Type.GENERIC,
            title="Notification for User 1",
            body="This is for user 1",
            url="/test1/"
        )
        
        # Create notification for user2
        notif2 = Notification.objects.create(
            recipient=self.user2,
            type=Notification.Type.GENERIC,
            title="Notification for User 2",
            body="This is for user 2",
            url="/test2/"
        )
        
        # Login as user1
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.get(self.url)
        
        data = json.loads(response.content)
        items = data['items']
        
        # Should have exactly 1 item (user1's notification)
        self.assertEqual(len(items), 1)
        
        # Verify it's user1's notification
        self.assertEqual(items[0]['title'], "Notification for User 1")
        self.assertEqual(items[0]['id'], notif1.id)
        
        # Verify user2's notification is NOT present
        notification_ids = [item['id'] for item in items]
        self.assertNotIn(notif2.id, notification_ids)
    
    def test_includes_follow_request_items(self):
        """
        Test that follow_request type notifications are included in response.
        Critical: This is the primary use case for Phase 4.
        """
        # Create follow_request notification
        follow_notif = Notification.objects.create(
            recipient=self.user1,
            type=Notification.Type.FOLLOW_REQUEST,
            event='follow_request',
            title=f"@{self.user2.username} wants to follow you",
            body=f"{self.profile2.display_name} sent you a follow request.",
            url="/me/settings/",
            action_label="View Request",
            action_url="/me/settings/",
            category="social",
            message=f"{self.profile2.display_name} sent you a follow request."
        )
        
        # Login and fetch
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.get(self.url)
        
        data = json.loads(response.content)
        items = data['items']
        
        # Should have the follow request notification
        self.assertEqual(len(items), 1)
        
        # Verify it's the follow_request type
        self.assertEqual(items[0]['type'], 'follow_request')
        self.assertEqual(items[0]['event'], 'follow_request')
        
        # Verify action fields are present
        self.assertEqual(items[0]['action_label'], "View Request")
        self.assertEqual(items[0]['action_url'], "/me/settings/")
        
        # Verify message field
        self.assertIn("sent you a follow request", items[0]['message'])
    
    def test_pending_follow_requests_count_correct(self):
        """
        Test that pending_follow_requests count matches actual FollowRequest objects.
        Critical: Badge count must be accurate.
        """
        # Create 3 pending follow requests for user1
        for i in range(3):
            sender_user = User.objects.create_user(
                username=f'follower{i}',
                email=f'follower{i}@example.com',
                password='testpass123'
            )
            sender_profile = UserProfile.objects.get(user=sender_user)
            sender_profile.display_name = f'Follower {i}'
            sender_profile.save()
            
            FollowRequest.objects.create(
                requester=sender_profile,
                target=self.profile1,
                status='PENDING'
            )
        
        # Create 1 approved follow request (should NOT count)
        approved_user = User.objects.create_user(
            username='approved_follower',
            email='approved@example.com',
            password='testpass123'
        )
        approved_profile = UserProfile.objects.get(user=approved_user)
        approved_profile.display_name = 'Approved Follower'
        approved_profile.save()
        FollowRequest.objects.create(
            requester=approved_profile,
            target=self.profile1,
            status='APPROVED'
        )
        
        # Create 1 pending request for user2 (should NOT count for user1)
        FollowRequest.objects.create(
            requester=self.profile1,
            target=self.profile2,
            status='PENDING'
        )
        
        # Login as user1 and fetch
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.get(self.url)
        
        data = json.loads(response.content)
        
        # Should have exactly 3 pending follow requests
        self.assertEqual(data['pending_follow_requests'], 3)
    
    def test_empty_list(self):
        """
        Test that endpoint handles users with no notifications gracefully.
        """
        # User1 has no notifications
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.get(self.url)
        
        data = json.loads(response.content)
        
        # Should succeed with empty list
        self.assertTrue(data['success'])
        self.assertEqual(data['unread_count'], 0)
        self.assertEqual(data['pending_follow_requests'], 0)
        self.assertEqual(len(data['items']), 0)
    
    def test_limits_to_10_items(self):
        """
        Test that endpoint returns max 10 items (dropdown size limit).
        """
        # Create 15 notifications
        for i in range(15):
            Notification.objects.create(
                recipient=self.user1,
                type=Notification.Type.GENERIC,
                title=f"Notification {i}",
                body=f"Body {i}",
                url=f"/test{i}/"
            )
        
        # Login and fetch
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.get(self.url)
        
        data = json.loads(response.content)
        
        # Should have exactly 10 items (not 15)
        self.assertEqual(len(data['items']), 10)
    
    def test_unread_count_correct(self):
        """
        Test that unread_count matches actual unread notifications.
        """
        # Create 5 unread notifications
        for i in range(5):
            Notification.objects.create(
                recipient=self.user1,
                type=Notification.Type.GENERIC,
                title=f"Unread {i}",
                body=f"Body {i}",
                url=f"/test{i}/",
                is_read=False
            )
        
        # Create 3 read notifications
        for i in range(3):
            Notification.objects.create(
                recipient=self.user1,
                type=Notification.Type.GENERIC,
                title=f"Read {i}",
                body=f"Body {i}",
                url=f"/test{i}/",
                is_read=True
            )
        
        # Login and fetch
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.get(self.url)
        
        data = json.loads(response.content)
        
        # Should count only unread (5)
        self.assertEqual(data['unread_count'], 5)
        
        # Should return all 8 items (unread + read)
        self.assertEqual(len(data['items']), 8)
    
    def test_item_fields_complete(self):
        """
        Test that each notification item has all required fields.
        """
        # Create notification with all fields
        Notification.objects.create(
            recipient=self.user1,
            type=Notification.Type.FOLLOW_REQUEST,
            event='follow_request',
            title="Test Title",
            body="Test Body",
            url="/test/",
            action_label="Test Action",
            action_url="/action/",
            category="social",
            message="Test Message",
            is_read=False
        )
        
        # Login and fetch
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.get(self.url)
        
        data = json.loads(response.content)
        item = data['items'][0]
        
        # Verify all required fields present
        required_fields = [
            'id', 'type', 'event', 'title', 'message', 'url',
            'created_at', 'is_read', 'action_label', 'action_url'
        ]
        for field in required_fields:
            self.assertIn(field, item, f"Missing field: {field}")
        
        # Verify values
        self.assertEqual(item['title'], "Test Title")
        self.assertEqual(item['message'], "Test Message")
        self.assertEqual(item['action_label'], "Test Action")
        self.assertEqual(item['action_url'], "/action/")
        self.assertFalse(item['is_read'])


class MarkAllReadTestCase(TestCase):
    """Test suite for mark-all-read endpoint"""
    
    def setUp(self):
        """Create test user and notifications"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.url = reverse('notifications:mark_all_read')
    
    def test_anonymous_returns_401_json(self):
        """Test that anonymous users get 401 JSON response"""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'auth_required')
    
    def test_get_not_allowed(self):
        """Test that GET requests return 405"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'method_not_allowed')
    
    def test_marks_all_notifications_read(self):
        """Test that POST marks all unread notifications as read"""
        # Create 5 unread notifications
        for i in range(5):
            Notification.objects.create(
                recipient=self.user,
                type=Notification.Type.GENERIC,
                title=f"Unread {i}",
                body=f"Body {i}",
                url=f"/test{i}/",
                is_read=False
            )
        
        # Create 2 already read notifications
        for i in range(2):
            Notification.objects.create(
                recipient=self.user,
                type=Notification.Type.GENERIC,
                title=f"Read {i}",
                body=f"Body {i}",
                url=f"/test{i}/",
                is_read=True
            )
        
        # Login and mark all read
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(self.url)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['updated_count'], 5)  # Only unread ones updated
        
        # Verify all notifications are now read
        unread_count = Notification.objects.filter(recipient=self.user, is_read=False).count()
        self.assertEqual(unread_count, 0)
    
    def test_returns_zero_when_no_unread(self):
        """Test that marking read when no unread notifications returns count=0"""
        # Create only read notifications
        for i in range(3):
            Notification.objects.create(
                recipient=self.user,
                type=Notification.Type.GENERIC,
                title=f"Read {i}",
                body=f"Body {i}",
                url=f"/test{i}/",
                is_read=True
            )
        
        # Mark all read
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(self.url)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['updated_count'], 0)
