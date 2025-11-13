"""
Tests for WebhookService Hardening - MILESTONE F Phase 5.6

Tests Module 5.6 hardening features:
- Replay safety (timestamp + webhook_id)
- Circuit breaker per endpoint
- Timestamp-based signature verification
- Replay attack prevention
"""

import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, call

import pytest
from django.test import TestCase, override_settings

from apps.notifications.services.webhook_service import (
    WebhookService,
    get_webhook_service,
)


@pytest.mark.django_db
class TestReplaySafety(TestCase):
    """Test replay protection with timestamp + webhook_id."""
    
    def test_deliver_includes_timestamp_header(self):
        """Test webhook delivery includes X-Webhook-Timestamp header."""
        service = WebhookService(
            endpoint='https://api.example.com/webhooks',
            secret='test-secret',
        )
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b''
            mock_post.return_value = mock_response
            
            success, _ = service.deliver(
                event='test_event',
                data={'test': 'data'},
            )
            
            assert success
            assert mock_post.called
            
            # Check headers
            _, kwargs = mock_post.call_args
            headers = kwargs['headers']
            assert 'X-Webhook-Timestamp' in headers
            
            # Timestamp should be recent (within last 5 seconds)
            timestamp_ms = int(headers['X-Webhook-Timestamp'])
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            age_ms = now_ms - timestamp_ms
            assert 0 <= age_ms < 5000, f"Timestamp age: {age_ms}ms"
    
    def test_deliver_includes_webhook_id_header(self):
        """Test webhook delivery includes X-Webhook-Id (UUID v4)."""
        service = WebhookService(
            endpoint='https://api.example.com/webhooks',
            secret='test-secret',
        )
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b''
            mock_post.return_value = mock_response
            
            success, _ = service.deliver(
                event='test_event',
                data={'test': 'data'},
            )
            
            assert success
            
            # Check webhook_id header
            _, kwargs = mock_post.call_args
            headers = kwargs['headers']
            assert 'X-Webhook-Id' in headers
            
            # Should be valid UUID format (36 chars with hyphens)
            webhook_id = headers['X-Webhook-Id']
            assert len(webhook_id) == 36
            assert webhook_id.count('-') == 4
    
    def test_signature_includes_timestamp(self):
        """Test signature includes timestamp in signing message."""
        service = WebhookService(secret='test-secret')
        payload = '{"event":"test"}'
        timestamp_ms = 1700000000000
        
        # Generate signatures with and without timestamp
        sig_with_ts = service.generate_signature(payload, timestamp=timestamp_ms)
        sig_without_ts = service.generate_signature(payload)
        
        # Should be different (timestamp changes the signing message)
        assert sig_with_ts != sig_without_ts
        
        # Both should be valid 64-char hex
        assert len(sig_with_ts) == 64
        assert len(sig_without_ts) == 64
    
    def test_verify_signature_accepts_fresh_timestamp(self):
        """Test signature verification accepts fresh timestamps."""
        service = WebhookService(
            secret='test-secret',
            replay_window=300,  # 5 minutes
        )
        payload = '{"event":"test"}'
        
        # Generate signature with current timestamp
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        signature = service.generate_signature(payload, timestamp=now_ms)
        
        # Should verify successfully
        valid, error = service.verify_signature(payload, signature, timestamp=now_ms)
        assert valid
        assert error is None
    
    def test_verify_signature_rejects_stale_timestamp(self):
        """Test signature verification rejects timestamps older than replay_window."""
        service = WebhookService(
            secret='test-secret',
            replay_window=300,  # 5 minutes
        )
        payload = '{"event":"test"}'
        
        # Generate signature with old timestamp (10 minutes ago)
        old_timestamp_ms = int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp() * 1000)
        signature = service.generate_signature(payload, timestamp=old_timestamp_ms)
        
        # Should reject as too old
        valid, error = service.verify_signature(payload, signature, timestamp=old_timestamp_ms)
        assert not valid
        assert "too old" in error.lower()
    
    def test_verify_signature_rejects_future_timestamp(self):
        """Test signature verification rejects timestamps in the future."""
        service = WebhookService(secret='test-secret')
        payload = '{"event":"test"}'
        
        # Generate signature with future timestamp (1 hour ahead)
        future_timestamp_ms = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp() * 1000)
        signature = service.generate_signature(payload, timestamp=future_timestamp_ms)
        
        # Should reject as future timestamp
        valid, error = service.verify_signature(payload, signature, timestamp=future_timestamp_ms)
        assert not valid
        assert "future" in error.lower()
    
    def test_verify_signature_rejects_tampered_payload(self):
        """Test signature verification rejects tampered payloads."""
        service = WebhookService(secret='test-secret')
        original_payload = '{"event":"test","amount":100}'
        tampered_payload = '{"event":"test","amount":999}'
        
        # Generate signature for original
        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        signature = service.generate_signature(original_payload, timestamp=timestamp_ms)
        
        # Try to verify tampered payload with original signature
        valid, error = service.verify_signature(tampered_payload, signature, timestamp=timestamp_ms)
        assert not valid
        assert "Invalid signature" in error
    
    def test_verify_signature_rejects_replay_with_different_webhook_id(self):
        """Test that identical payloads with different webhook_id should use different IDs."""
        service = WebhookService(
            endpoint='https://api.example.com/webhooks',
            secret='test-secret',
        )
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b''
            mock_post.return_value = mock_response
            
            # Send same event twice
            service.deliver(event='test', data={'id': 123})
            service.deliver(event='test', data={'id': 123})
            
            # Should have different webhook_id values
            call1_headers = mock_post.call_args_list[0][1]['headers']
            call2_headers = mock_post.call_args_list[1][1]['headers']
            
            webhook_id_1 = call1_headers['X-Webhook-Id']
            webhook_id_2 = call2_headers['X-Webhook-Id']
            
            assert webhook_id_1 != webhook_id_2, "Webhook IDs should be unique per delivery"


@pytest.mark.django_db
class TestCircuitBreaker(TestCase):
    """Test circuit breaker per endpoint."""
    
    def setUp(self):
        """Reset circuit breaker state before each test."""
        WebhookService._circuit_state = 'closed'
        WebhookService._failure_count = 0
        WebhookService._failure_window_start = None
        WebhookService._circuit_opened_at = None
    
    def test_circuit_breaker_stays_closed_on_success(self):
        """Test circuit breaker remains closed with successful deliveries."""
        service = WebhookService(
            endpoint='https://api.example.com/webhooks',
            secret='test-secret',
            cb_max_fails=5,
        )
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b''
            mock_post.return_value = mock_response
            
            # Send 10 successful webhooks
            for _ in range(10):
                success, _ = service.deliver(event='test', data={'id': 1})
                assert success
            
            # Circuit should remain closed
            assert service._circuit_state == 'closed'
            assert service._failure_count == 0
    
    def test_circuit_breaker_opens_after_threshold_failures(self):
        """Test circuit breaker opens after reaching failure threshold."""
        service = WebhookService(
            endpoint='https://api.example.com/webhooks',
            secret='test-secret',
            cb_max_fails=5,
            cb_window=120,
        )
        
        with patch('requests.post') as mock_post:
            # Simulate 5xx errors
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.text = 'Service Unavailable'
            mock_post.return_value = mock_response
            
            # Attempt 5 deliveries (all fail)
            for i in range(5):
                success, response = service.deliver(event='test', data={'id': i})
                assert not success
                print(f"After delivery {i+1}: state={service._circuit_state}, failures={service._failure_count}")
            
            # Circuit should be open now
            print(f"Final state: {service._circuit_state}")
            assert service._circuit_state == 'open'
            assert service._circuit_opened_at is not None
    
    def test_circuit_breaker_blocks_requests_when_open(self):
        """Test circuit breaker blocks delivery attempts when open."""
        service = WebhookService(
            endpoint='https://api.example.com/webhooks',
            secret='test-secret',
            cb_max_fails=3,
            cb_open_seconds=60,
        )
        
        with patch('requests.post') as mock_post:
            # Simulate failures to open circuit
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.text = 'Service Unavailable'
            mock_post.return_value = mock_response
            
            # Cause 3 failures to open circuit
            for _ in range(3):
                service.deliver(event='test', data={'id': 1})
            
            assert service._circuit_state == 'open'
            
            # Reset mock to track new calls
            mock_post.reset_mock()
            
            # Next delivery should be blocked (no HTTP request made)
            success, response = service.deliver(event='test', data={'id': 2})
            assert not success
            assert 'circuit_breaker' in response
            assert response['circuit_breaker'] == 'open'
            assert not mock_post.called, "HTTP request should not be made when circuit is open"
    
    def test_circuit_breaker_transitions_to_half_open(self):
        """Test circuit breaker transitions to half-open after timeout."""
        service = WebhookService(
            endpoint='https://api.example.com/webhooks',
            secret='test-secret',
            cb_max_fails=3,
            cb_open_seconds=2,  # 2 second timeout for testing
        )
        
        with patch('requests.post') as mock_post:
            # Open circuit with failures
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.text = 'Service Unavailable'
            mock_post.return_value = mock_response
            
            for _ in range(3):
                service.deliver(event='test', data={'id': 1})
            
            assert service._circuit_state == 'open'
            
            # Wait for timeout
            time.sleep(2.1)
            
            # Now configure success response for probe
            mock_response.status_code = 200
            mock_response.content = b''
            
            # Next delivery should be allowed (half-open probe)
            success, _ = service.deliver(event='test', data={'id': 2})
            assert success
            
            # Circuit should transition back to closed
            assert service._circuit_state == 'closed'
            assert service._failure_count == 0
    
    def test_circuit_breaker_half_open_probe_success_closes_circuit(self):
        """Test successful probe in half-open state closes circuit."""
        service = WebhookService(
            endpoint='https://api.example.com/webhooks',
            secret='test-secret',
            cb_max_fails=2,
            cb_open_seconds=1,
        )
        
        with patch('requests.post') as mock_post:
            # Open circuit
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = 'Error'
            mock_post.return_value = mock_response
            
            service.deliver(event='test', data={'id': 1})
            service.deliver(event='test', data={'id': 2})
            
            assert service._circuit_state == 'open'
            
            # Wait and allow probe
            time.sleep(1.1)
            
            # Successful probe
            mock_response.status_code = 200
            mock_response.content = b''
            success, _ = service.deliver(event='test', data={'id': 3})
            
            assert success
            assert service._circuit_state == 'closed'
    
    def test_circuit_breaker_half_open_probe_failure_reopens_circuit(self):
        """Test failed probe in half-open state reopens circuit."""
        service = WebhookService(
            endpoint='https://api.example.com/webhooks',
            secret='test-secret',
            cb_max_fails=2,
            cb_open_seconds=1,
        )
        
        with patch('requests.post') as mock_post:
            # Open circuit
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = 'Error'
            mock_post.return_value = mock_response
            
            service.deliver(event='test', data={'id': 1})
            service.deliver(event='test', data={'id': 2})
            
            assert service._circuit_state == 'open'
            
            # Wait and allow probe
            time.sleep(1.1)
            
            # Failed probe (still 500)
            success, _ = service.deliver(event='test', data={'id': 3})
            
            assert not success
            assert service._circuit_state == 'open'
    
    def test_circuit_breaker_failure_window_resets(self):
        """Test failure window resets after expiration."""
        service = WebhookService(
            endpoint='https://api.example.com/webhooks',
            secret='test-secret',
            cb_max_fails=3,
            cb_window=2,  # 2 second window
        )
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = 'Error'
            mock_post.return_value = mock_response
            
            # Cause 2 failures
            service.deliver(event='test', data={'id': 1})
            service.deliver(event='test', data={'id': 2})
            
            assert service._failure_count == 2
            assert service._circuit_state == 'closed'
            
            # Wait for window to expire
            time.sleep(2.1)
            
            # Next check should reset failure count
            service.deliver(event='test', data={'id': 3})
            
            # Failure count should be 1 (not 3), window reset
            assert service._failure_count == 1
    
    def test_circuit_breaker_4xx_errors_open_circuit(self):
        """Test 4xx errors contribute to circuit breaker failure count."""
        service = WebhookService(
            endpoint='https://api.example.com/webhooks',
            secret='test-secret',
            cb_max_fails=3,
        )
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = 'Bad Request'
            mock_post.return_value = mock_response
            
            # Cause 3 client errors
            for _ in range(3):
                service.deliver(event='test', data={'id': 1})
            
            # Circuit should open (4xx counts as failure)
            assert service._circuit_state == 'open'


@pytest.mark.django_db
class TestTimestampVerification(TestCase):
    """Test timestamp-based verification edge cases."""
    
    def test_verify_accepts_timestamp_within_window(self):
        """Test verification accepts timestamps within replay window."""
        service = WebhookService(secret='test-secret', replay_window=300)
        payload = '{"test":"data"}'
        
        # Test timestamps at different points within window
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        test_offsets = [0, -60, -120, -240, -299]  # 0s to 4:59 ago
        
        for offset_seconds in test_offsets:
            timestamp_ms = now_ms + (offset_seconds * 1000)
            signature = service.generate_signature(payload, timestamp=timestamp_ms)
            valid, error = service.verify_signature(payload, signature, timestamp=timestamp_ms)
            assert valid, f"Should accept timestamp {offset_seconds}s ago: {error}"
    
    def test_verify_rejects_timestamp_outside_window(self):
        """Test verification rejects timestamps outside replay window."""
        service = WebhookService(secret='test-secret', replay_window=300)
        payload = '{"test":"data"}'
        
        # Test timestamps beyond window
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        test_offsets = [-301, -600, -3600]  # 5:01 to 60 minutes ago
        
        for offset_seconds in test_offsets:
            timestamp_ms = now_ms + (offset_seconds * 1000)
            signature = service.generate_signature(payload, timestamp=timestamp_ms)
            valid, error = service.verify_signature(payload, signature, timestamp=timestamp_ms)
            assert not valid, f"Should reject timestamp {offset_seconds}s ago"
            assert "too old" in error.lower()
    
    def test_verify_allows_clock_skew(self):
        """Test verification allows small future timestamps (clock skew)."""
        service = WebhookService(secret='test-secret')
        payload = '{"test":"data"}'
        
        # Test small future offsets (within 30s clock skew tolerance)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        test_offsets = [1, 10, 29]  # 1-29 seconds in future
        
        for offset_seconds in test_offsets:
            timestamp_ms = now_ms + (offset_seconds * 1000)
            signature = service.generate_signature(payload, timestamp=timestamp_ms)
            valid, error = service.verify_signature(payload, signature, timestamp=timestamp_ms)
            assert valid, f"Should allow clock skew of {offset_seconds}s: {error}"
    
    def test_verify_custom_max_age(self):
        """Test verification with custom max_age_seconds parameter."""
        service = WebhookService(secret='test-secret', replay_window=300)
        payload = '{"test":"data"}'
        
        # Timestamp 2 minutes ago
        timestamp_ms = int((datetime.now(timezone.utc) - timedelta(minutes=2)).timestamp() * 1000)
        signature = service.generate_signature(payload, timestamp=timestamp_ms)
        
        # Should reject with max_age=60 (1 minute)
        valid_short, error_short = service.verify_signature(payload, signature, timestamp=timestamp_ms, max_age_seconds=60)
        assert not valid_short
        assert "too old" in error_short.lower()
        
        # Should accept with max_age=180 (3 minutes)
        valid_long, error_long = service.verify_signature(payload, signature, timestamp=timestamp_ms, max_age_seconds=180)
        assert valid_long
        assert error_long is None
