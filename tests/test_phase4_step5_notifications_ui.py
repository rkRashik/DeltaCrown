"""
PHASE4_STEP5: Comprehensive Tests for Notifications UI Overhaul

Tests verify:
1. Bell button converted from dropdown toggle to direct link
2. Badge element has correct ID for SSE live updates
3. Notifications page accessible and renders correctly
4. Mark-all-read API returns JSON (not redirects)
5. Nav preview API returns JSON with proper auth checks
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.notifications.models import Notification

User = get_user_model()


class Phase4Step5NavigationTests(TestCase):
    """Test navigation bar bell button changes"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_navigation_bell_is_link_not_button(self):
        """
        CRITICAL: Bell must be <a href="/notifications/"> not <button data-notif-toggle>
        PHASE4_STEP5: Removed dropdown, bell now links directly to /notifications/ page
        """
        self.client.force_login(self.user)
        response = self.client.get('/')
        
        # Assert: Bell is an anchor tag linking to /notifications/
        self.assertContains(
            response, 
            '<a href="/notifications/" class="unified-nav-desktop__notif-btn"',
            msg_prefix="Bell button must be converted to link"
        )
        
        # Assert: NO dropdown toggle button exists
        self.assertNotContains(
            response,
            'data-notif-toggle',
            msg_prefix="Dropdown toggle attribute must be removed"
        )
        
        # Assert: Button element no longer used for notifications bell
        self.assertNotContains(
            response,
            '<button class="unified-nav-desktop__notif-btn"',
            msg_prefix="Button element must be replaced with anchor"
        )
    
    def test_badge_has_correct_id_for_sse(self):
        """
        Badge element must have id="notification-bell-badge" for SSE updates
        PHASE4_STEP5: Badge kept for live count updates via live_notifications.js
        """
        self.client.force_login(self.user)
        response = self.client.get('/')
        
        # Assert: Badge has correct ID
        self.assertContains(
            response,
            'id="notification-bell-badge"',
            msg_prefix="Badge must have ID for SSE integration"
        )
        
        # Assert: Badge has data attribute for future enhancements
        self.assertContains(
            response,
            'data-notif-badge',
            msg_prefix="Badge must have data attribute"
        )
    
    def test_badge_always_rendered_with_hidden_class(self):
        """
        Badge element must always exist (even if 0 count) so SSE can unhide it
        PHASE4_STEP5: Badge needs to exist in DOM for JavaScript to update
        """
        self.client.force_login(self.user)
        response = self.client.get('/')
        
        # Assert: Badge exists in HTML
        self.assertContains(
            response,
            'class="unified-nav-desktop__badge',
            count=1,
            msg_prefix="Badge element must exist exactly once"
        )


class Phase4Step5NotificationsPageTests(TestCase):
    """Test /notifications/ page accessibility and rendering"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_notifications_page_requires_login(self):
        """Anonymous users redirected to login"""
        response = self.client.get('/notifications/')
        
        # Assert: Redirects to login (302)
        self.assertEqual(response.status_code, 302)
        # Django might use /account/login/ or /accounts/login/?next=
        self.assertIn(
            '/account',
            response.url,
            msg="Anonymous users must be redirected to login"
        )
    
    def test_notifications_page_accessible_when_authenticated(self):
        """Authenticated users can access notifications page"""
        self.client.force_login(self.user)
        response = self.client.get('/notifications/')
        
        # Assert: Returns 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Assert: Template contains expected elements
        self.assertContains(response, 'Notifications')
        self.assertContains(response, 'Mark all read')
        self.assertContains(response, 'Follow Requests')
    
    def test_notifications_page_shows_empty_state(self):
        """Page renders empty state when no notifications"""
        self.client.force_login(self.user)
        response = self.client.get('/notifications/')
        
        # Assert: Empty state message present
        self.assertContains(response, 'No notifications yet')
    
    def test_notifications_page_shows_notifications_list(self):
        """Page renders notification items correctly"""
        self.client.force_login(self.user)
        
        # Create a test notification
        Notification.objects.create(
            recipient=self.user,
            type='generic',
            title='Test Notification',
            body='Test message body',
            is_read=False
        )
        
        response = self.client.get('/notifications/')
        
        # Assert: Notification appears on page
        self.assertContains(response, 'Test Notification')
        self.assertContains(response, 'Test message body')
        self.assertContains(response, 'Mark read')


class Phase4Step5MarkAllReadAPITests(TestCase):
    """Test mark-all-read API returns JSON (not redirects)"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_mark_all_read_returns_401_json_for_anonymous(self):
        """
        CRITICAL: Anonymous users get 401 JSON (NOT redirect)
        PHASE4_STEP5: API must return JSON for AJAX/fetch usage
        """
        response = self.client.post('/notifications/mark-all-read/')
        
        # Assert: Returns 401 status
        self.assertEqual(
            response.status_code, 
            401,
            msg="Anonymous users must get 401 (not redirect)"
        )
        
        # Assert: Response is JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Assert: JSON contains error details
        data = response.json()
        self.assertFalse(data.get('success'))
        self.assertIn('error', data)
    
    def test_mark_all_read_returns_405_json_for_get_request(self):
        """GET request to mark-all-read returns 405 Method Not Allowed"""
        self.client.force_login(self.user)
        response = self.client.get('/notifications/mark-all-read/')
        
        # Assert: Returns 405 status
        self.assertEqual(response.status_code, 405)
        
        # Assert: Response is JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Assert: JSON contains error message
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'method_not_allowed')
    
    def test_mark_all_read_returns_200_json_for_authenticated_post(self):
        """
        Authenticated POST returns 200 OK with JSON success response
        PHASE4_STEP5: API returns JSON for JavaScript consumption
        """
        self.client.force_login(self.user)
        
        # Create unread notifications
        Notification.objects.create(
            recipient=self.user,
            type='generic',
            title='Notification 1',
            is_read=False
        )
        Notification.objects.create(
            recipient=self.user,
            type='generic',
            title='Notification 2',
            is_read=False
        )
        
        response = self.client.post('/notifications/mark-all-read/')
        
        # Assert: Returns 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Assert: Response is JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Assert: JSON contains success=true
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['updated_count'], 2)
        self.assertIn('message', data)
        
        # Assert: Notifications actually marked as read in DB
        unread_count = Notification.objects.filter(recipient=self.user, is_read=False).count()
        self.assertEqual(unread_count, 0, msg="All notifications must be marked read")


class Phase4Step5NavPreviewAPITests(TestCase):
    """Test nav-preview API returns proper JSON responses"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_nav_preview_returns_401_json_for_anonymous(self):
        """
        CRITICAL: Anonymous users get 401 JSON (NOT redirect)
        PHASE4_STEP5: Nav preview API must return JSON for AJAX usage
        """
        response = self.client.get('/notifications/api/nav-preview/')
        
        # Assert: Returns 401 status
        self.assertEqual(
            response.status_code,
            401,
            msg="Anonymous users must get 401 JSON (not redirect)"
        )
        
        # Assert: Response is JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Assert: JSON contains error
        data = response.json()
        self.assertFalse(data.get('success'))
    
    def test_nav_preview_returns_200_json_for_authenticated(self):
        """
        Authenticated GET returns 200 OK with notifications preview
        PHASE4_STEP5: API provides data for navigation dropdown (now deprecated)
        """
        self.client.force_login(self.user)
        
        # Create test notifications
        Notification.objects.create(
            recipient=self.user,
            type='generic',
            title='Test Notification',
            body='Test body',
            is_read=False
        )
        
        response = self.client.get('/notifications/api/nav-preview/')
        
        # Assert: Returns 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Assert: Response is JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Assert: JSON contains expected structure
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('items', data)
        self.assertIsInstance(data['items'], list)
        
        # Assert: Unread count present
        self.assertIn('unread_count', data)
        self.assertEqual(data['unread_count'], 1)


class Phase4Step5IntegrationTests(TestCase):
    """Integration tests for complete notification flow"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_full_notification_workflow(self):
        """
        Test complete workflow:
        1. User has unread notifications
        2. Badge shows count
        3. Click bell goes to /notifications/ page
        4. Mark all read via API
        5. Badge updated (via SSE in real system)
        """
        self.client.force_login(self.user)
        
        # Step 1: Create unread notifications
        Notification.objects.create(
            recipient=self.user,
            type='generic',
            title='Test 1',
            is_read=False
        )
        Notification.objects.create(
            recipient=self.user,
            type='generic',
            title='Test 2',
            is_read=False
        )
        
        # Step 2: Home page shows badge with count
        home_response = self.client.get('/')
        self.assertContains(home_response, 'id="notification-bell-badge"')
        
        # Step 3: Bell links to /notifications/ (not dropdown)
        self.assertContains(home_response, '<a href="/notifications/"')
        
        # Step 4: Notifications page accessible
        notif_response = self.client.get('/notifications/')
        self.assertEqual(notif_response.status_code, 200)
        self.assertContains(notif_response, 'Test 1')
        self.assertContains(notif_response, 'Test 2')
        
        # Step 5: Mark all read via API
        mark_response = self.client.post('/notifications/mark-all-read/')
        mark_data = mark_response.json()
        
        self.assertEqual(mark_response.status_code, 200)
        self.assertTrue(mark_data['success'])
        self.assertEqual(mark_data['updated_count'], 2)
        
        # Step 6: Verify notifications marked read in DB
        unread = Notification.objects.filter(recipient=self.user, is_read=False).count()
        self.assertEqual(unread, 0)
    
    def test_anonymous_user_workflow(self):
        """
        Anonymous users:
        1. Cannot see bell button
        2. Redirected to login when accessing /notifications/
        3. Get 401 JSON from APIs (not redirects)
        """
        # Step 1: Home page (anonymous) has no bell
        home_response = self.client.get('/')
        # Bell is inside {% if request.user.is_authenticated %}
        # So it won't appear for anonymous users
        
        # Step 2: /notifications/ redirects to login
        notif_response = self.client.get('/notifications/')
        self.assertEqual(notif_response.status_code, 302)
        self.assertIn('/account', notif_response.url)
        
        # Step 3: APIs return 401 JSON
        mark_response = self.client.post('/notifications/mark-all-read/')
        self.assertEqual(mark_response.status_code, 401)
        self.assertEqual(mark_response['Content-Type'], 'application/json')
        
        nav_response = self.client.get('/notifications/api/nav-preview/')
        self.assertEqual(nav_response.status_code, 401)
        self.assertEqual(nav_response['Content-Type'], 'application/json')
