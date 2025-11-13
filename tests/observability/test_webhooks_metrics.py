"""
Tests for Webhook Metrics (Prometheus Integration).

Validates that metrics.py correctly records success/failure/retry/CB events
and exposes Prometheus counters/histograms/gauges as expected.
"""

import pytest
from unittest.mock import Mock, patch, call
from apps.notifications.metrics import (
    record_success,
    record_failure,
    record_retry,
    record_circuit_breaker_open,
    set_circuit_breaker_state,
    METRICS_AVAILABLE,
)


@pytest.mark.django_db
class TestWebhookMetrics:
    """Test suite for webhook metrics recording."""

    @pytest.fixture(autouse=True)
    def mock_prometheus(self):
        """Mock prometheus_client to avoid registry conflicts in tests."""
        with patch("apps.notifications.metrics.Counter") as mock_counter, \
             patch("apps.notifications.metrics.Histogram") as mock_histogram, \
             patch("apps.notifications.metrics.Gauge") as mock_gauge:
            
            # Create mock metric instances
            self.mock_success_counter = Mock()
            self.mock_failure_counter = Mock()
            self.mock_retry_counter = Mock()
            self.mock_cb_open_counter = Mock()
            self.mock_latency_histogram = Mock()
            self.mock_cb_state_gauge = Mock()
            
            # Return mocks when metrics are instantiated
            mock_counter.side_effect = [
                self.mock_success_counter,
                self.mock_failure_counter,
                self.mock_retry_counter,
                self.mock_cb_open_counter,
            ]
            mock_histogram.return_value = self.mock_latency_histogram
            mock_gauge.return_value = self.mock_cb_state_gauge
            
            yield

    def test_record_success_with_event_and_endpoint(self):
        """Test recording successful delivery with event and endpoint."""
        record_success(
            event="payment_verified",
            endpoint="https://api.example.com/webhooks",
            latency_seconds=0.156
        )
        
        # Verify counter incremented
        self.mock_success_counter.labels.assert_called_once_with(
            event="payment_verified",
            endpoint="https://api.example.com/webhooks"
        )
        self.mock_success_counter.labels.return_value.inc.assert_called_once()
        
        # Verify latency recorded
        self.mock_latency_histogram.labels.assert_called_once_with(
            event="payment_verified"
        )
        self.mock_latency_histogram.labels.return_value.observe.assert_called_once_with(0.156)

    def test_record_success_without_latency(self):
        """Test recording success without latency (optional parameter)."""
        record_success(
            event="match_started",
            endpoint="https://api.example.com/webhooks"
        )
        
        # Counter should be incremented
        self.mock_success_counter.labels.assert_called_once()
        
        # Latency should NOT be recorded
        self.mock_latency_histogram.labels.assert_not_called()

    def test_record_failure_with_error_code(self):
        """Test recording failed delivery with HTTP error code."""
        record_failure(
            event="tournament_registration_opened",
            endpoint="https://api.example.com/webhooks",
            error_code="503"
        )
        
        # Verify counter incremented with error code
        self.mock_failure_counter.labels.assert_called_once_with(
            event="tournament_registration_opened",
            endpoint="https://api.example.com/webhooks",
            code="503"
        )
        self.mock_failure_counter.labels.return_value.inc.assert_called_once()

    def test_record_failure_network_timeout(self):
        """Test recording network timeout (no HTTP code)."""
        record_failure(
            event="payment_verified",
            endpoint="https://api.example.com/webhooks",
            error_code="timeout"
        )
        
        # Verify code="timeout" label
        self.mock_failure_counter.labels.assert_called_once_with(
            event="payment_verified",
            endpoint="https://api.example.com/webhooks",
            code="timeout"
        )

    def test_record_retry_first_retry(self):
        """Test recording first retry attempt."""
        record_retry(
            event="match_started",
            attempt=1
        )
        
        # Verify retry counter incremented
        self.mock_retry_counter.labels.assert_called_once_with(
            event="match_started",
            attempt=1
        )
        self.mock_retry_counter.labels.return_value.inc.assert_called_once()

    def test_record_retry_third_attempt(self):
        """Test recording third retry attempt."""
        record_retry(
            event="payment_verified",
            attempt=3
        )
        
        # Verify attempt=3 label
        self.mock_retry_counter.labels.assert_called_once_with(
            event="payment_verified",
            attempt=3
        )

    def test_record_circuit_breaker_open(self):
        """Test recording circuit breaker open event."""
        record_circuit_breaker_open(
            endpoint="https://api.example.com/webhooks"
        )
        
        # Verify CB open counter incremented
        self.mock_cb_open_counter.labels.assert_called_once_with(
            endpoint="https://api.example.com/webhooks"
        )
        self.mock_cb_open_counter.labels.return_value.inc.assert_called_once()

    def test_set_circuit_breaker_state_closed(self):
        """Test setting circuit breaker to CLOSED (0)."""
        set_circuit_breaker_state(
            endpoint="https://api.example.com/webhooks",
            state=0  # CLOSED
        )
        
        # Verify gauge set to 0
        self.mock_cb_state_gauge.labels.assert_called_once_with(
            endpoint="https://api.example.com/webhooks"
        )
        self.mock_cb_state_gauge.labels.return_value.set.assert_called_once_with(0)

    def test_set_circuit_breaker_state_half_open(self):
        """Test setting circuit breaker to HALF_OPEN (1)."""
        set_circuit_breaker_state(
            endpoint="https://api.example.com/webhooks",
            state=1  # HALF_OPEN
        )
        
        # Verify gauge set to 1
        self.mock_cb_state_gauge.labels.return_value.set.assert_called_once_with(1)

    def test_set_circuit_breaker_state_open(self):
        """Test setting circuit breaker to OPEN (2)."""
        set_circuit_breaker_state(
            endpoint="https://api.example.com/webhooks",
            state=2  # OPEN
        )
        
        # Verify gauge set to 2
        self.mock_cb_state_gauge.labels.return_value.set.assert_called_once_with(2)

    def test_multiple_events_same_endpoint(self):
        """Test recording multiple events for same endpoint."""
        endpoint = "https://api.example.com/webhooks"
        
        record_success("payment_verified", endpoint, 0.123)
        record_success("match_started", endpoint, 0.234)
        record_failure("tournament_registration_opened", endpoint, "503")
        
        # Verify 3 separate calls with different event types
        assert self.mock_success_counter.labels.call_count == 2
        assert self.mock_failure_counter.labels.call_count == 1
        assert self.mock_latency_histogram.labels.call_count == 2

    def test_graceful_degradation_when_prometheus_unavailable(self):
        """Test that metrics functions don't crash if prometheus_client is unavailable."""
        with patch("apps.notifications.metrics.METRICS_AVAILABLE", False):
            # These should not raise exceptions
            record_success("payment_verified", "https://example.com", 0.1)
            record_failure("match_started", "https://example.com", "500")
            record_retry("payment_verified", 1)
            record_circuit_breaker_open("https://example.com")
            set_circuit_breaker_state("https://example.com", 0)
        
        # No assertions needed - success = no exceptions raised

    def test_metrics_available_flag(self):
        """Test METRICS_AVAILABLE flag is set correctly based on prometheus_client import."""
        # This test validates the module-level flag
        # In real environment with prometheus_client installed, should be True
        assert isinstance(METRICS_AVAILABLE, bool)


@pytest.mark.django_db
class TestMetricsIntegration:
    """Integration tests for metrics within webhook service."""

    @pytest.fixture
    def mock_requests(self):
        """Mock requests library for webhook delivery."""
        with patch("apps.notifications.services.webhook_service.requests") as mock:
            yield mock

    @pytest.fixture
    def mock_metrics(self):
        """Mock all metrics functions."""
        with patch("apps.notifications.services.webhook_service.metrics") as mock:
            yield mock

    def test_successful_delivery_records_metrics(self, mock_requests, mock_metrics):
        """Test that successful delivery records success + latency metrics."""
        from apps.notifications.services.webhook_service import WebhookService
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.145
        mock_requests.post.return_value = mock_response
        
        service = WebhookService()
        service.send_webhook(
            event="payment_verified",
            endpoint="https://api.example.com/webhooks",
            payload={"test": "data"},
            secret="test_secret_123"
        )
        
        # Verify record_success was called
        mock_metrics.record_success.assert_called_once_with(
            event="payment_verified",
            endpoint="https://api.example.com/webhooks",
            latency_seconds=0.145
        )

    def test_failed_delivery_records_failure_metric(self, mock_requests, mock_metrics):
        """Test that failed delivery records failure metric with error code."""
        from apps.notifications.services.webhook_service import WebhookService
        
        # Mock 503 response
        mock_response = Mock()
        mock_response.status_code = 503
        mock_requests.post.return_value = mock_response
        
        service = WebhookService()
        service.send_webhook(
            event="match_started",
            endpoint="https://api.example.com/webhooks",
            payload={"test": "data"},
            secret="test_secret_123"
        )
        
        # Verify record_failure was called with 503
        mock_metrics.record_failure.assert_called_once_with(
            event="match_started",
            endpoint="https://api.example.com/webhooks",
            error_code="503"
        )

    def test_retry_attempt_records_retry_metric(self, mock_requests, mock_metrics):
        """Test that retry attempts record retry metrics."""
        from apps.notifications.services.webhook_service import WebhookService
        
        # Mock 503 then 200
        mock_response_fail = Mock()
        mock_response_fail.status_code = 503
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.elapsed.total_seconds.return_value = 0.156
        
        mock_requests.post.side_effect = [mock_response_fail, mock_response_success]
        
        service = WebhookService()
        service.send_webhook(
            event="payment_verified",
            endpoint="https://api.example.com/webhooks",
            payload={"test": "data"},
            secret="test_secret_123",
            max_retries=1
        )
        
        # Verify record_retry was called for attempt 1
        mock_metrics.record_retry.assert_called_once_with(
            event="payment_verified",
            attempt=1
        )
        
        # Verify final success was recorded
        mock_metrics.record_success.assert_called_once()

    def test_circuit_breaker_open_records_cb_metrics(self, mock_metrics):
        """Test that circuit breaker state changes record CB metrics."""
        from apps.notifications.services.circuit_breaker import CircuitBreaker
        
        cb = CircuitBreaker(
            endpoint="https://api.example.com/webhooks",
            failure_threshold=5,
            timeout_seconds=30
        )
        
        # Simulate 5 failures to open circuit
        for _ in range(5):
            cb.record_failure()
        
        # Verify CB open was recorded
        mock_metrics.record_circuit_breaker_open.assert_called_once_with(
            endpoint="https://api.example.com/webhooks"
        )
        
        # Verify CB state set to OPEN (2)
        mock_metrics.set_circuit_breaker_state.assert_called_with(
            endpoint="https://api.example.com/webhooks",
            state=2  # OPEN
        )
