"""
Prometheus metrics for monitoring (Module 9.5).
Tracks error counts, WebSocket errors, and close reasons.
"""
from prometheus_client import Counter, Histogram, Gauge
import time

# HTTP Request Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Error Metrics
error_count = Counter(
    'error_count',
    'Total error count by error code',
    ['code', 'endpoint']
)

# WebSocket Metrics
ws_connections_total = Gauge(
    'ws_connections_total',
    'Current number of WebSocket connections'
)

ws_error_count = Counter(
    'ws_error_count',
    'WebSocket error count by error type',
    ['error_type', 'endpoint']
)

ws_close_reason_count = Counter(
    'ws_close_reason_count',
    'WebSocket close reason count',
    ['close_code', 'reason']
)

ws_message_count = Counter(
    'ws_message_count',
    'WebSocket message count',
    ['message_type', 'endpoint']
)


class MetricsMiddleware:
    """
    Middleware to collect HTTP request metrics.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Record metrics
        duration = time.time() - start_time
        endpoint = request.path
        method = request.method
        status = response.status_code
        
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
        
        # Track errors
        if status >= 400:
            error_code = response.get('X-Error-Code', f'HTTP_{status}')
            error_count.labels(code=error_code, endpoint=endpoint).inc()
        
        return response


def track_ws_connection(delta=1):
    """Track WebSocket connection change."""
    if delta > 0:
        ws_connections_total.inc(delta)
    else:
        ws_connections_total.dec(abs(delta))


def track_ws_error(error_type, endpoint):
    """Track WebSocket error."""
    ws_error_count.labels(error_type=error_type, endpoint=endpoint).inc()


def track_ws_close(close_code, reason=None):
    """Track WebSocket close reason."""
    ws_close_reason_count.labels(
        close_code=str(close_code),
        reason=reason or 'normal'
    ).inc()


def track_ws_message(message_type, endpoint):
    """Track WebSocket message."""
    ws_message_count.labels(message_type=message_type, endpoint=endpoint).inc()
