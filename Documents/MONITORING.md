# Monitoring & Observability Guide

**Implements:**
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#monitoring-and-observability
- Documents/Planning/PART_2.4_SECURITY_HARDENING.md#audit-logging

---

## Overview

DeltaCrown uses a multi-layered monitoring approach:
- **Sentry**: Error tracking, performance monitoring, user feedback
- **Prometheus**: Metrics collection and time-series data
- **Django Logging**: Application logs (JSON format in production)
- **Health Checks**: `/healthz` and `/readiness` endpoints

---

## Sentry Integration

### Configuration

Sentry is already configured in `deltacrown/settings.py` (Phase 2).

**Environment Variables** (`.env`):
```bash
SENTRY_DSN=https://your-key@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% transaction sampling (production)
SENTRY_PROFILES_SAMPLE_RATE=0.1  # 10% profile sampling (production)
SENTRY_ENVIRONMENT=production  # Or: staging, development
SENTRY_RELEASE=v1.2.3  # Set via CI/CD
```

**Recommended Sampling Rates**:
- **Development**: 1.0 (100%) - capture everything
- **Staging**: 0.5 (50%) - representative sample
- **Production**: 0.1 (10%) - balance cost vs visibility

### What Sentry Tracks

1. **Errors & Exceptions**:
   - Uncaught Python exceptions
   - Django view errors (500, 404)
   - WebSocket connection failures
   - Celery task failures

2. **Performance Transactions**:
   - HTTP request duration
   - Database query performance
   - WebSocket message latency
   - Celery task execution time

3. **User Context**:
   - User ID (if authenticated)
   - Request headers
   - Custom tags (tournament_id, match_id, etc.)

### Manual Event Capture

```python
import sentry_sdk

# Capture custom exception
try:
    risky_operation()
except Exception as e:
    sentry_sdk.capture_exception(e)

# Add breadcrumb for context
sentry_sdk.add_breadcrumb(
    category='tournament',
    message='Bracket generation started',
    level='info',
    data={'tournament_id': 123}
)

# Capture message
sentry_sdk.capture_message('Important event occurred', level='warning')

# Set user context
sentry_sdk.set_user({"id": user.id, "username": user.username})

# Set custom tags
sentry_sdk.set_tag("tournament_id", tournament_id)
sentry_sdk.set_tag("match_type", "ELIMINATION")
```

### Sentry Dashboard Queries

**High Error Rate (Alerts)**:
- Query: `event.type:error`
- Threshold: > 100 errors/hour
- Alert: Email + Slack webhook

**Slow Transactions**:
- Query: `event.type:transaction AND transaction.duration:>2000`
- Shows requests slower than 2 seconds

**WebSocket Errors**:
- Query: `event.type:error AND tags[websocket]:true`
- Custom tag set in consumer error handlers

---

## Prometheus Metrics

### Installation

```bash
# Add to requirements.txt
django-prometheus>=2.3.1

# Install
pip install django-prometheus
```

### Configuration

**1. Update `deltacrown/settings.py`**:

```python
# Implements: Documents/MONITORING.md#prometheus-configuration

INSTALLED_APPS = [
    'django_prometheus',  # Must be FIRST for middleware timing
    # ... other apps
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',  # FIRST
    'django.middleware.security.SecurityMiddleware',
    # ... other middleware
    'django_prometheus.middleware.PrometheusAfterMiddleware',  # LAST
]

# Prometheus metrics database wrapper
DATABASES = {
    'default': {
        'ENGINE': 'django_prometheus.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'deltacrown_db'),
        # ... rest of config
    }
}
```

**2. Update `deltacrown/urls.py`**:

```python
from django.urls import path, include

urlpatterns = [
    # ... existing patterns
    path('metrics/', include('django_prometheus.urls')),  # Prometheus endpoint
]
```

**3. Environment Variables**:

```bash
# Enable Prometheus metrics
ENABLE_PROMETHEUS=1

# Metrics endpoint (default: /metrics/)
PROMETHEUS_METRICS_PATH=/metrics/
```

### Available Metrics

#### Request Metrics
- `django_http_requests_total_by_method` - Total requests by HTTP method
- `django_http_requests_latency_seconds` - Request duration histogram
- `django_http_requests_total_by_view_transport_method` - Requests per view
- `django_http_requests_body_total_bytes` - Request body size

#### Database Metrics
- `django_db_query_total` - Total database queries
- `django_db_execute_total` - Query execution count
- `django_db_errors_total` - Database errors

#### WebSocket Metrics (Custom)
- `ws_connections_active` - Current active WebSocket connections
- `ws_connections_total` - Total connections (counter)
- `ws_messages_received_total` - Total messages received
- `ws_messages_sent_total` - Total messages sent
- `ws_message_latency_seconds` - Message processing latency

#### Custom Business Metrics
- `tournament_registrations_total` - Tournament sign-ups
- `matches_completed_total` - Completed matches
- `payments_processed_total` - Payment transactions
- `coins_awarded_total` - Virtual currency awards

### Custom Metrics Implementation

**Add to `apps/core/metrics.py`**:

```python
# Implements: Documents/MONITORING.md#custom-metrics
from prometheus_client import Counter, Gauge, Histogram

# WebSocket metrics
ws_connections_active = Gauge(
    'ws_connections_active',
    'Number of active WebSocket connections',
    ['tournament_id']
)

ws_messages_received = Counter(
    'ws_messages_received_total',
    'Total WebSocket messages received',
    ['message_type', 'tournament_id']
)

ws_message_latency = Histogram(
    'ws_message_latency_seconds',
    'WebSocket message processing latency',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# Business metrics
tournament_registrations = Counter(
    'tournament_registrations_total',
    'Total tournament registrations',
    ['tournament_id', 'status']  # status: SUCCESS, FAILED
)

matches_completed = Counter(
    'matches_completed_total',
    'Total matches completed',
    ['tournament_id', 'game_title']
)

payments_processed = Counter(
    'payments_processed_total',
    'Total payment transactions',
    ['status', 'method']  # status: SUCCESS, FAILED; method: STRIPE, PAYPAL
)
```

**Usage in WebSocket Consumer**:

```python
from apps.core.metrics import ws_connections_active, ws_messages_received, ws_message_latency
import time

class TournamentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Increment active connections gauge
        ws_connections_active.labels(tournament_id=self.tournament_id).inc()
        await self.accept()
    
    async def disconnect(self, close_code):
        # Decrement active connections gauge
        ws_connections_active.labels(tournament_id=self.tournament_id).dec()
    
    async def receive(self, text_data):
        start_time = time.time()
        
        data = json.loads(text_data)
        message_type = data.get('type', 'unknown')
        
        # Increment message counter
        ws_messages_received.labels(
            message_type=message_type,
            tournament_id=self.tournament_id
        ).inc()
        
        # Process message...
        await self.handle_message(data)
        
        # Record latency
        latency = time.time() - start_time
        ws_message_latency.observe(latency)
```

### Grafana Dashboard Setup

**Prometheus Queries for Dashboards**:

1. **Active WebSocket Connections**:
   ```promql
   sum(ws_connections_active) by (tournament_id)
   ```

2. **WebSocket Message Rate** (messages/sec):
   ```promql
   rate(ws_messages_received_total[5m])
   ```

3. **HTTP Request Rate** (requests/sec):
   ```promql
   rate(django_http_requests_total_by_method[5m])
   ```

4. **95th Percentile Request Latency**:
   ```promql
   histogram_quantile(0.95, rate(django_http_requests_latency_seconds_bucket[5m]))
   ```

5. **Database Query Rate**:
   ```promql
   rate(django_db_query_total[5m])
   ```

6. **Error Rate** (HTTP 5xx):
   ```promql
   rate(django_http_requests_total_by_method{status=~"5.."}[5m])
   ```

---

## Health Check Endpoints

### `/healthz` - Basic Liveness

Returns 200 OK if the application is running.

```bash
$ curl http://localhost:8000/healthz
{"status": "healthy"}
```

**Use Case**: Kubernetes liveness probe, load balancer health checks

### `/readiness` - Full Readiness

Returns 200 OK if application + dependencies are ready.

```bash
$ curl http://localhost:8000/readiness
{
  "status": "ready",
  "database": "ok",
  "redis": "ok",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Checks**:
- Database connection (PostgreSQL)
- Redis connection (cache + channels)
- Channel layer availability

**Use Case**: Kubernetes readiness probe, deployment verification

**Error Response** (503 Service Unavailable):
```json
{
  "status": "not_ready",
  "database": "ok",
  "redis": "error",
  "error": "Redis connection failed",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Logging Configuration

### Development Logging

**Console output** (human-readable):
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

### Production Logging

**JSON structured logs** (for log aggregation):

```python
# Requires: python-json-logger
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/deltacrown.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.tournaments': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### Custom Log Messages

```python
import logging

logger = logging.getLogger(__name__)

# Info level
logger.info('Tournament created', extra={
    'tournament_id': tournament.id,
    'user_id': request.user.id,
    'game_title': tournament.game_title
})

# Warning level
logger.warning('High WebSocket connection count', extra={
    'tournament_id': tournament.id,
    'connection_count': connection_count
})

# Error level
logger.error('Payment processing failed', extra={
    'user_id': user.id,
    'payment_method': 'stripe',
    'error_code': error.code
}, exc_info=True)  # Include stack trace
```

---

## Alert Thresholds

### Critical Alerts (Page on-call)

1. **Error Rate Spike**:
   - Threshold: > 100 errors/5min
   - Metric: `rate(django_http_requests_total_by_method{status=~"5.."}[5m]) > 0.33`

2. **Database Down**:
   - Endpoint: `/readiness` returns 503
   - Check: Every 30 seconds

3. **High WebSocket Connection Failures**:
   - Threshold: > 50 failed connections/min
   - Custom metric: `ws_connection_failures_total`

4. **Payment Processing Failures**:
   - Threshold: > 5 failures/hour
   - Metric: `payments_processed_total{status="FAILED"}`

### Warning Alerts (Notify Slack)

1. **High Response Time**:
   - Threshold: p95 > 2 seconds
   - Metric: `histogram_quantile(0.95, rate(django_http_requests_latency_seconds_bucket[5m])) > 2`

2. **High Database Query Count**:
   - Threshold: > 1000 queries/sec
   - Metric: `rate(django_db_query_total[5m]) > 1000`

3. **WebSocket Message Queue Backlog**:
   - Threshold: > 10,000 pending messages
   - Redis `LLEN` on channel layer queue

4. **Disk Space**:
   - Threshold: < 20% free
   - System metric (node exporter)

---

## Testing Monitoring Setup

### 1. Verify Sentry

```python
# In Django shell or view
import sentry_sdk
sentry_sdk.capture_message("Test message from DeltaCrown", level="info")

# Check Sentry dashboard for the event
```

### 2. Verify Prometheus Metrics

```bash
# Access metrics endpoint
curl http://localhost:8000/metrics/

# Should see output like:
# django_http_requests_total_by_method{method="GET"} 1234
# django_db_query_total 5678
```

### 3. Verify Health Checks

```bash
# Liveness check
curl http://localhost:8000/healthz

# Readiness check
curl http://localhost:8000/readiness
```

### 4. Generate Load for Testing

```python
# Load test script
import requests
import concurrent.futures

def make_request():
    response = requests.get('http://localhost:8000/api/tournaments/')
    return response.status_code

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(make_request) for _ in range(100)]
    results = [f.result() for f in futures]
    print(f"Completed {len(results)} requests")

# Check Prometheus for spike in request metrics
```

---

## Deployment Checklist

- [ ] Configure Sentry DSN in production `.env`
- [ ] Set appropriate Sentry sampling rates (0.1 for production)
- [ ] Install `django-prometheus` package
- [ ] Add Prometheus middleware to `settings.py`
- [ ] Configure Grafana dashboards with PromQL queries
- [ ] Set up alert rules in Prometheus/Grafana
- [ ] Configure Slack webhook for non-critical alerts
- [ ] Configure PagerDuty for critical alerts
- [ ] Test health check endpoints from load balancer
- [ ] Verify JSON logging in production
- [ ] Set up log aggregation (ELK stack or CloudWatch)

---

## Troubleshooting

### Metrics not appearing in Prometheus

1. Check `/metrics/` endpoint manually
2. Verify `django-prometheus` in `INSTALLED_APPS` (must be FIRST)
3. Check middleware order (Before/After middlewares)
4. Restart application after config changes

### Sentry not capturing errors

1. Verify `SENTRY_DSN` is set correctly
2. Check Sentry integration is initialized (search settings.py for `sentry_sdk.init`)
3. Test with manual `capture_exception()` call
4. Check Sentry project settings (allowed domains, rate limits)

### High cardinality warning (Prometheus)

If you see too many unique label combinations:
- Avoid using user IDs as labels (use aggregated metrics instead)
- Limit tournament_id labels to active tournaments only
- Use label prefixing/bucketing for high-cardinality data

---

## Support

- **Sentry Documentation**: https://docs.sentry.io/platforms/python/guides/django/
- **Prometheus Django**: https://github.com/korfuri/django-prometheus
- **Grafana Dashboards**: https://grafana.com/grafana/dashboards/
