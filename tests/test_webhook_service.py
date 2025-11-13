"""
Tests for WebhookService - MILESTONE F Phase 5

Tests webhook delivery with:
- HMAC signature generation and verification
- Successful delivery scenarios
- Retry logic with exponential backoff
- Error handling (timeouts, connection errors, HTTP errors)
- Configuration validation
"""

import json
import time
from unittest.mock import Mock, patch, call

import pytest
from django.test import TestCase, override_settings

from apps.notifications.services.webhook_service import (
    WebhookService,
    get_webhook_service,
    deliver_webhook,
)


@pytest.mark.django_db
class TestWebhookSignature(TestCase):
    """Test HMAC-SHA256 signature generation and verification."""
    
    def test_generate_signature_with_secret(self):
        """Test signature generation with valid secret."""
        service = WebhookService(secret='test-secret-key')
        payload = '{"event":"test","data":{}}'
        
        signature = service.generate_signature(payload)
        
        # Signature should be 64-character hex string (SHA256)
        assert len(signature) == 64
        assert all(c in '0123456789abcdef' for c in signature)
    
    def test_generate_signature_is_deterministic(self):
        """Test same payload produces same signature."""
        service = WebhookService(secret='test-secret')
        payload = '{"event":"test"}'
        
        sig1 = service.generate_signature(payload)
        sig2 = service.generate_signature(payload)
        
        assert sig1 == sig2
    
    def test_generate_signature_different_payloads(self):
        """Test different payloads produce different signatures."""
        service = WebhookService(secret='test-secret')
        
        sig1 = service.generate_signature('{"event":"test1"}')
        sig2 = service.generate_signature('{"event":"test2"}')
        
        assert sig1 != sig2
    
    def test_generate_signature_without_secret(self):
        """Test signature generation without secret returns empty string."""
        service = WebhookService(secret='')
        
        signature = service.generate_signature('{"event":"test"}')
        
        assert signature == ''
    
    def test_verify_signature_valid(self):
        """Test signature verification with valid signature."""
        service = WebhookService(secret='test-secret')
        payload = '{"event":"test"}'
        signature = service.generate_signature(payload)
        
        is_valid, error = service.verify_signature(payload, signature)
        
        assert is_valid is True
        assert error is None
    
    def test_verify_signature_invalid(self):
        """Test signature verification with invalid signature."""
        service = WebhookService(secret='test-secret')
        payload = '{"event":"test"}'
        
        is_valid, error = service.verify_signature(payload, 'invalid-signature')
        
        assert is_valid is False
        assert error == "Invalid signature"
    
    def test_verify_signature_different_secret(self):
        """Test signature fails when verified with different secret."""
        service1 = WebhookService(secret='secret1')
        service2 = WebhookService(secret='secret2')
        
        payload = '{"event":"test"}'
        signature = service1.generate_signature(payload)
        
        is_valid, error = service2.verify_signature(payload, signature)
        
        assert is_valid is False
        assert error == "Invalid signature"


@pytest.mark.django_db
class TestWebhookDelivery(TestCase):
    """Test webhook delivery with various scenarios."""
    
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_successful_delivery_200(self, mock_post):
        """Test successful webhook delivery with 200 OK."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"received": true}'
        mock_response.json.return_value = {'received': True}
        mock_post.return_value = mock_response
        
        service = WebhookService(
            endpoint='https://example.com/webhook',
            secret='test-secret',
        )
        
        success, response_data = service.deliver(
            event='test_event',
            data={'key': 'value'},
        )
        
        assert success is True
        assert response_data == {'received': True}
        assert mock_post.call_count == 1
    
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_successful_delivery_accepts_2xx_codes(self, mock_post):
        """Test delivery succeeds with various 2xx status codes."""
        for status_code in [200, 201, 202, 204]:
            mock_post.reset_mock()
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.content = b''
            mock_post.return_value = mock_response
            
            service = WebhookService(endpoint='https://example.com/webhook')
            success, _ = service.deliver(event='test', data={})
            
            assert success is True, f"Failed for status {status_code}"
    
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_delivery_includes_correct_headers(self, mock_post):
        """Test webhook request includes correct headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_post.return_value = mock_response
        
        service = WebhookService(
            endpoint='https://example.com/webhook',
            secret='test-secret',
        )
        
        service.deliver(event='payment_verified', data={'id': 123})
        
        # Verify headers
        call_kwargs = mock_post.call_args[1]
        headers = call_kwargs['headers']
        
        assert headers['Content-Type'] == 'application/json'
        assert headers['X-Webhook-Event'] == 'payment_verified'
        assert 'X-Webhook-Signature' in headers
        assert len(headers['X-Webhook-Signature']) == 64  # SHA256 hex
    
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_delivery_includes_metadata(self, mock_post):
        """Test webhook payload includes metadata."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_post.return_value = mock_response
        
        service = WebhookService(endpoint='https://example.com/webhook')
        
        service.deliver(
            event='test_event',
            data={'key': 'value'},
            metadata={'user_id': 123, 'timestamp': '2025-11-13T10:00:00Z'},
        )
        
        # Verify payload structure
        call_kwargs = mock_post.call_args[1]
        payload = json.loads(call_kwargs['data'])
        
        assert payload['event'] == 'test_event'
        assert payload['data'] == {'key': 'value'}
        assert payload['metadata'] == {'user_id': 123, 'timestamp': '2025-11-13T10:00:00Z'}
    
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_delivery_without_endpoint_returns_false(self, mock_post):
        """Test delivery fails gracefully without endpoint configured."""
        service = WebhookService(endpoint=None)
        
        success, response_data = service.deliver(event='test', data={})
        
        assert success is False
        assert response_data is None
        assert mock_post.call_count == 0  # No request made


@pytest.mark.django_db
class TestWebhookRetryLogic(TestCase):
    """Test exponential backoff retry logic."""
    
    @patch('apps.notifications.services.webhook_service.time.sleep')
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_retry_on_500_error(self, mock_post, mock_sleep):
        """Test retry with exponential backoff on 500 error."""
        # First 2 attempts fail, 3rd succeeds
        mock_responses = [
            Mock(status_code=500, text='Internal Error'),
            Mock(status_code=500, text='Internal Error'),
            Mock(status_code=200, content=b''),
        ]
        mock_post.side_effect = mock_responses
        
        service = WebhookService(
            endpoint='https://example.com/webhook',
            max_retries=3,
        )
        
        success, _ = service.deliver(event='test', data={})
        
        assert success is True
        assert mock_post.call_count == 3
        
        # Verify exponential backoff: 2^1=2s, 2^2=4s (but only 2 sleeps since 1st attempt has no delay)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2)  # 2^1
        mock_sleep.assert_any_call(4)  # 2^2
    
    @patch('apps.notifications.services.webhook_service.time.sleep')
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_retry_on_timeout(self, mock_post, mock_sleep):
        """Test retry on timeout exceptions."""
        import requests
        
        # First 2 attempts timeout, 3rd succeeds
        mock_post.side_effect = [
            requests.exceptions.Timeout('Request timeout'),
            requests.exceptions.Timeout('Request timeout'),
            Mock(status_code=200, content=b''),
        ]
        
        service = WebhookService(endpoint='https://example.com/webhook', max_retries=3)
        
        success, _ = service.deliver(event='test', data={})
        
        assert success is True
        assert mock_post.call_count == 3
    
    @patch('apps.notifications.services.webhook_service.time.sleep')
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_retry_on_connection_error(self, mock_post, mock_sleep):
        """Test retry on connection errors."""
        import requests
        
        mock_post.side_effect = [
            requests.exceptions.ConnectionError('Connection refused'),
            Mock(status_code=200, content=b''),
        ]
        
        service = WebhookService(endpoint='https://example.com/webhook', max_retries=2)
        
        success, _ = service.deliver(event='test', data={})
        
        assert success is True
        assert mock_post.call_count == 2
    
    @patch('apps.notifications.services.webhook_service.time.sleep')
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_no_retry_on_400_client_error(self, mock_post, mock_sleep):
        """Test no retry on 4xx client errors."""
        mock_response = Mock(status_code=400, text='Bad Request')
        mock_post.return_value = mock_response
        
        service = WebhookService(endpoint='https://example.com/webhook', max_retries=3)
        
        success, _ = service.deliver(event='test', data={})
        
        assert success is False
        assert mock_post.call_count == 1  # No retries
        assert mock_sleep.call_count == 0
    
    @patch('apps.notifications.services.webhook_service.time.sleep')
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_exhausted_retries_returns_false(self, mock_post, mock_sleep):
        """Test all retries exhausted returns False."""
        mock_response = Mock(status_code=500, text='Server Error')
        mock_post.return_value = mock_response
        
        service = WebhookService(endpoint='https://example.com/webhook', max_retries=3)
        
        success, response_data = service.deliver(event='test', data={})
        
        assert success is False
        assert response_data is None
        assert mock_post.call_count == 3


@pytest.mark.django_db
class TestWebhookConfiguration(TestCase):
    """Test configuration from Django settings."""
    
    @override_settings(
        WEBHOOK_ENDPOINT='https://configured.example.com/webhook',
        WEBHOOK_SECRET='configured-secret',
        WEBHOOK_TIMEOUT=15,
        WEBHOOK_MAX_RETRIES=5,
    )
    def test_configuration_from_settings(self):
        """Test WebhookService reads configuration from settings."""
        service = WebhookService()
        
        assert service.endpoint == 'https://configured.example.com/webhook'
        assert service.secret == 'configured-secret'
        assert service.timeout == 15
        assert service.max_retries == 5
    
    def test_configuration_override_via_constructor(self):
        """Test constructor parameters override settings."""
        service = WebhookService(
            endpoint='https://custom.example.com/webhook',
            secret='custom-secret',
            timeout=20,
            max_retries=7,
        )
        
        assert service.endpoint == 'https://custom.example.com/webhook'
        assert service.secret == 'custom-secret'
        assert service.timeout == 20
        assert service.max_retries == 7


@pytest.mark.django_db
class TestWebhookConvenienceFunctions(TestCase):
    """Test singleton and convenience functions."""
    
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_get_webhook_service_singleton(self, mock_post):
        """Test get_webhook_service returns singleton instance."""
        service1 = get_webhook_service()
        service2 = get_webhook_service()
        
        assert service1 is service2
    
    @patch('apps.notifications.services.webhook_service.requests.post')
    def test_deliver_webhook_convenience_function(self, mock_post):
        """Test deliver_webhook convenience function."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_post.return_value = mock_response
        
        with override_settings(WEBHOOK_ENDPOINT='https://example.com/webhook'):
            success, _ = deliver_webhook(
                event='test_event',
                data={'key': 'value'},
                metadata={'user_id': 123},
            )
        
        assert success is True
        assert mock_post.call_count == 1
