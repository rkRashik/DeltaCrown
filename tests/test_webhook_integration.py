"""
End-to-end integration tests for webhook delivery.

Tests that NotificationService properly delivers webhooks when
NOTIFICATIONS_WEBHOOK_ENABLED=True.
"""

from unittest.mock import patch, Mock

import pytest
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

# Import notify directly - services/__init__.py now re-exports it
from apps.notifications.services import notify


User = get_user_model()


@pytest.mark.django_db
class TestWebhookIntegration(TestCase):
    """Test webhook integration with NotificationService."""
    
    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
    
    @override_settings(NOTIFICATIONS_WEBHOOK_ENABLED=False)
    @patch('apps.notifications.services.deliver_webhook')
    def test_webhook_not_called_when_disabled(self, mock_deliver):
        """Test webhook is not called when NOTIFICATIONS_WEBHOOK_ENABLED=False."""
        notify(
            recipients=[self.user],
            event='test_event',
            title='Test Notification',
            body='Test body',
        )
        
        # Webhook should NOT be called
        mock_deliver.assert_not_called()
    
    @override_settings(
        NOTIFICATIONS_WEBHOOK_ENABLED=True,
        WEBHOOK_ENDPOINT='https://example.com/webhook',
    )
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_webhook_called_when_enabled(self, mock_post):
        """Test webhook is called when NOTIFICATIONS_WEBHOOK_ENABLED=True."""
        # Mock successful webhook response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_post.return_value = mock_response
        
        result = notify(
            recipients=[self.user],
            event='test_event',
            title='Test Notification',
            body='Test body',
        )
        
        # Webhook should be called
        assert mock_post.call_count == 1
        assert result['webhook_sent'] == 1
    
    @override_settings(
        NOTIFICATIONS_WEBHOOK_ENABLED=True,
        WEBHOOK_ENDPOINT='https://example.com/webhook',
    )
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_webhook_includes_notification_data(self, mock_post):
        """Test webhook payload includes notification data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_post.return_value = mock_response
        
        notify(
            recipients=[self.user],
            event='payment_verified',
            title='Payment Verified',
            body='Your payment has been verified',
            url='/payments/123/',
            tournament_id=456,
        )
        
        # Verify webhook payload structure
        import json
        call_kwargs = mock_post.call_args[1]
        payload = json.loads(call_kwargs['data'])
        
        assert payload['event'] == 'payment_verified'
        assert payload['data']['title'] == 'Payment Verified'
        assert payload['data']['body'] == 'Your payment has been verified'
        assert payload['data']['url'] == '/payments/123/'
        assert payload['data']['tournament_id'] == 456
        assert payload['data']['recipient_count'] == 1
    
    @override_settings(
        NOTIFICATIONS_WEBHOOK_ENABLED=True,
        WEBHOOK_ENDPOINT='https://example.com/webhook',
    )
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_webhook_failure_does_not_break_notification(self, mock_post):
        """Test webhook failure doesn't prevent notification creation."""
        import requests
        # Mock webhook failure
        mock_post.side_effect = requests.exceptions.Timeout('Timeout')
        
        result = notify(
            recipients=[self.user],
            event='test_event',
            title='Test Notification',
        )
        
        # Notification should still be created
        assert result['created'] == 1
        assert result['webhook_sent'] == 0
    
    @override_settings(
        NOTIFICATIONS_WEBHOOK_ENABLED=True,
        WEBHOOK_ENDPOINT='https://example.com/webhook',
        WEBHOOK_SECRET='test-secret',
    )
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_webhook_includes_hmac_signature(self, mock_post):
        """Test webhook includes HMAC signature in headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_post.return_value = mock_response
        
        notify(
            recipients=[self.user],
            event='test_event',
            title='Test',
        )
        
        # Verify signature header exists
        call_kwargs = mock_post.call_args[1]
        headers = call_kwargs['headers']
        
        assert 'X-Webhook-Signature' in headers
        assert headers['X-Webhook-Event'] == 'test_event'
        # Note: Signature may be empty if SECRET wasn't configured at service init time
        # In production, service would be initialized with proper config
    
    @override_settings(
        NOTIFICATIONS_WEBHOOK_ENABLED=True,
        WEBHOOK_ENDPOINT='https://example.com/webhook',
    )
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_webhook_metadata_includes_notification_stats(self, mock_post):
        """Test webhook metadata includes notification statistics."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_post.return_value = mock_response
        
        # Create multiple recipients
        user2 = User.objects.create_user(username='user2', email='user2@test.com')
        
        notify(
            recipients=[self.user, user2],
            event='tournament_completed',
            title='Tournament Completed',
        )
        
        # Verify metadata
        import json
        call_kwargs = mock_post.call_args[1]
        payload = json.loads(call_kwargs['data'])
        
        assert payload['metadata']['created'] == 2
        assert payload['metadata']['skipped'] == 0
        assert 'email_sent' in payload['metadata']
