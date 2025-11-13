"""
Webhook Observability — Prometheus Metrics

Provides per-event counters and histograms for webhook delivery monitoring.
Integrates with Prometheus + Grafana for real-time canary observability.

Metrics exported:
- webhook_delivery_success_total: Counter (event, endpoint)
- webhook_delivery_failure_total: Counter (event, endpoint, code)
- webhook_delivery_latency_seconds: Histogram (event)
- webhook_cb_open_total: Counter (endpoint)
- webhook_retry_attempts_total: Counter (event, attempt)
"""

from prometheus_client import Counter, Histogram
from typing import Optional

# Success counter: Tracks successful webhook deliveries
webhook_delivery_success_total = Counter(
    'webhook_delivery_success_total',
    'Total number of successful webhook deliveries',
    ['event', 'endpoint']
)

# Failure counter: Tracks failed deliveries with HTTP status codes
webhook_delivery_failure_total = Counter(
    'webhook_delivery_failure_total',
    'Total number of failed webhook deliveries',
    ['event', 'endpoint', 'code']
)

# Latency histogram: Tracks delivery times (including retries)
webhook_delivery_latency_seconds = Histogram(
    'webhook_delivery_latency_seconds',
    'Webhook delivery latency in seconds (including retries)',
    ['event'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

# Circuit breaker counter: Tracks when circuit opens
webhook_cb_open_total = Counter(
    'webhook_cb_open_total',
    'Total number of times circuit breaker opened',
    ['endpoint']
)

# Retry counter: Tracks retry attempts distribution
webhook_retry_attempts_total = Counter(
    'webhook_retry_attempts_total',
    'Total webhook retry attempts',
    ['event', 'attempt']
)

# Circuit breaker state gauge (0=CLOSED, 1=HALF_OPEN, 2=OPEN)
from prometheus_client import Gauge

webhook_cb_state = Gauge(
    'webhook_cb_state',
    'Current circuit breaker state (0=CLOSED, 1=HALF_OPEN, 2=OPEN)',
    ['endpoint']
)


def record_success(event: str, endpoint: str, latency_seconds: float):
    """
    Record a successful webhook delivery.
    
    Args:
        event: Event type (e.g., 'payment_verified')
        endpoint: Webhook endpoint URL
        latency_seconds: Total delivery time in seconds
    """
    webhook_delivery_success_total.labels(event=event, endpoint=endpoint).inc()
    webhook_delivery_latency_seconds.labels(event=event).observe(latency_seconds)


def record_failure(event: str, endpoint: str, status_code: int):
    """
    Record a failed webhook delivery.
    
    Args:
        event: Event type
        endpoint: Webhook endpoint URL
        status_code: HTTP status code (e.g., 500, 503)
    """
    webhook_delivery_failure_total.labels(
        event=event,
        endpoint=endpoint,
        code=str(status_code)
    ).inc()


def record_retry(event: str, attempt: int):
    """
    Record a retry attempt.
    
    Args:
        event: Event type
        attempt: Retry attempt number (1, 2, 3)
    """
    webhook_retry_attempts_total.labels(
        event=event,
        attempt=str(attempt)
    ).inc()


def record_circuit_breaker_open(endpoint: str):
    """
    Record a circuit breaker opening event.
    
    Args:
        endpoint: Webhook endpoint URL
    """
    webhook_cb_open_total.labels(endpoint=endpoint).inc()


def set_circuit_breaker_state(endpoint: str, state: str):
    """
    Update circuit breaker state gauge.
    
    Args:
        endpoint: Webhook endpoint URL
        state: 'CLOSED', 'HALF_OPEN', or 'OPEN'
    """
    state_value = {
        'CLOSED': 0,
        'HALF_OPEN': 1,
        'OPEN': 2
    }.get(state, 0)
    
    webhook_cb_state.labels(endpoint=endpoint).set(state_value)
