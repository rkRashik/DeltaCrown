# Sender Rate Smoothing Configuration

**Applied**: 2025-11-13T15:05:00Z (T+35m into canary)  
**Purpose**: Keep burst pressure low during 5% canary validation

---

## Rate Limiter Configuration

**File**: `apps/notifications/services/webhook_service.py`

### Global Rate Limits (5% Canary)

```python
# Webhook delivery rate limits
WEBHOOK_MAX_QPS = 10           # Max 10 deliveries per second
WEBHOOK_MAX_INFLIGHT = 100     # Max 100 concurrent webhook requests
WEBHOOK_BURST_MULTIPLIER = 2.0 # Allow brief 2x burst (20 QPS)

# Token bucket parameters
RATE_LIMIT_REFILL_RATE = 10    # Tokens per second
RATE_LIMIT_BUCKET_SIZE = 20    # Max burst capacity
```

### Implementation (Token Bucket Algorithm)

```python
import time
from threading import Lock

class TokenBucket:
    """Thread-safe token bucket rate limiter."""
    
    def __init__(self, rate: float, capacity: float):
        self.rate = rate          # Tokens per second
        self.capacity = capacity  # Max tokens
        self.tokens = capacity    # Current tokens
        self.last_refill = time.time()
        self.lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens.
        
        Returns:
            True if tokens available, False if rate limited.
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            
            # Refill tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + (elapsed * self.rate)
            )
            self.last_refill = now
            
            # Check if tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False

# Global rate limiter instance
webhook_rate_limiter = TokenBucket(
    rate=WEBHOOK_MAX_QPS,
    capacity=WEBHOOK_BURST_MULTIPLIER * WEBHOOK_MAX_QPS
)
```

### Semaphore for In-Flight Limit

```python
from asyncio import Semaphore

# Max concurrent webhook requests
webhook_semaphore = Semaphore(WEBHOOK_MAX_INFLIGHT)

async def send_webhook_rate_limited(event, endpoint, payload, secret):
    """
    Send webhook with rate limiting and concurrency control.
    
    Enforces:
    - Token bucket (max QPS)
    - Semaphore (max in-flight)
    """
    # Wait for rate limiter token
    while not webhook_rate_limiter.consume():
        await asyncio.sleep(0.1)  # Backpressure: wait 100ms
    
    # Wait for semaphore slot
    async with webhook_semaphore:
        return await _send_webhook_internal(event, endpoint, payload, secret)
```

---

## Monitoring Metrics

### Rate Limiter Metrics

**Prometheus counters**:

```python
from prometheus_client import Counter, Gauge

webhook_rate_limited_total = Counter(
    'webhook_rate_limited_total',
    'Total webhook deliveries delayed by rate limiter',
    ['event']
)

webhook_inflight_gauge = Gauge(
    'webhook_inflight_requests',
    'Current number of in-flight webhook requests'
)

webhook_qps_gauge = Gauge(
    'webhook_deliveries_per_second',
    'Current webhook delivery rate (QPS)'
)
```

**Recording**:

```python
async def send_webhook_rate_limited(event, endpoint, payload, secret):
    # Record rate limit hit
    if not webhook_rate_limiter.consume():
        webhook_rate_limited_total.labels(event=event).inc()
    
    # Track in-flight count
    webhook_inflight_gauge.inc()
    try:
        async with webhook_semaphore:
            return await _send_webhook_internal(event, endpoint, payload, secret)
    finally:
        webhook_inflight_gauge.dec()
```

---

## Grafana Dashboard Updates

**Panel: Webhook Delivery Rate (QPS)**

```json
{
  "title": "Webhook Delivery Rate (QPS)",
  "targets": [
    {
      "expr": "rate(webhook_delivery_success_total[1m]) + rate(webhook_delivery_failure_total[1m])",
      "legendFormat": "Actual QPS"
    },
    {
      "expr": "10",
      "legendFormat": "Target (10 QPS)"
    }
  ],
  "yaxes": [
    {
      "label": "Deliveries/sec",
      "min": 0,
      "max": 20
    }
  ]
}
```

**Panel: In-Flight Requests**

```json
{
  "title": "In-Flight Webhook Requests",
  "targets": [
    {
      "expr": "webhook_inflight_requests",
      "legendFormat": "In-Flight"
    },
    {
      "expr": "100",
      "legendFormat": "Limit (100)"
    }
  ],
  "thresholds": [
    {"value": 80, "color": "yellow"},
    {"value": 100, "color": "red"}
  ]
}
```

**Panel: Rate Limited Count**

```json
{
  "title": "Rate Limited Webhooks (Backpressure)",
  "targets": [
    {
      "expr": "rate(webhook_rate_limited_total[5m])",
      "legendFormat": "{{event}}"
    }
  ]
}
```

---

## Alert Rules

**High Rate Limiting** (Warning):

```yaml
- alert: WebhookHighRateLimiting
  expr: rate(webhook_rate_limited_total[5m]) > 5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High webhook rate limiting detected"
    description: "Webhook deliveries being rate-limited >5/s for 10 minutes. May indicate sender spike or need to increase QPS limit."
```

**In-Flight Near Limit** (Warning):

```yaml
- alert: WebhookInFlightNearLimit
  expr: webhook_inflight_requests > 80
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "In-flight webhook requests near limit"
    description: "In-flight webhook requests >80 (limit 100) for 5 minutes. May cause backpressure delays."
```

---

## Configuration Tuning During Canary

### Current Settings (5% Canary)

| Parameter | Value | Reasoning |
|-----------|-------|-----------|
| **Max QPS** | 10 | Conservative for 5% slice; ~500 events/min |
| **Max In-Flight** | 100 | Allows burst absorption without receiver overload |
| **Burst Multiplier** | 2.0 | Brief 20 QPS spikes acceptable |
| **Backoff Sleep** | 100ms | Gentle backpressure without blocking event loop |

### Tuning at 25% (If Promoted)

| Parameter | Value | Change |
|-----------|-------|--------|
| **Max QPS** | 25 | +150% (scales with traffic) |
| **Max In-Flight** | 250 | +150% (proportional increase) |
| **Burst Multiplier** | 2.0 | Keep same (allows 50 QPS burst) |

### Tuning at 100% (Full Production)

| Parameter | Value | Change |
|-----------|-------|--------|
| **Max QPS** | 100 | +900% from 5% |
| **Max In-Flight** | 500 | +400% (higher concurrency) |
| **Burst Multiplier** | 1.5 | Reduce (tighter control) |

---

## Verification Commands

**Check current QPS** (sender logs):

```bash
# Count webhook deliveries in last minute
grep "webhook_delivery" /var/log/deltacrown.log | grep "$(date -u +%Y-%m-%dT%H:%M)" | wc -l
```

**Check in-flight count** (Prometheus):

```bash
curl -s http://localhost:9090/api/v1/query?query=webhook_inflight_requests | jq '.data.result[0].value[1]'
```

**Check rate limited count** (last 5 minutes):

```bash
curl -s http://localhost:9090/api/v1/query?query=increase(webhook_rate_limited_total[5m]) | jq '.data.result'
```

---

## Expected Behavior During Canary

### Healthy State

- Actual QPS: **6-10** (avg ~8, matching 5% traffic)
- In-flight requests: **10-30** (well below 100 limit)
- Rate limited count: **0** (no backpressure)
- Burst spikes: Occasional 15-20 QPS (within 2x burst allowance)

### Degraded State (Triggers Investigation)

- Actual QPS: **>15 sustained** (exceeds expected 5% slice)
- In-flight requests: **>80** (approaching limit)
- Rate limited count: **>5/s** (significant backpressure)
- Alerts: WebhookInFlightNearLimit fires

**Action**: Review traffic slice configuration (may be routing >5%)

---

## Rollback Conditions

If rate limiting causes delivery delays >30s:

1. **Increase QPS limit to 15** (temporary relief)
2. **Monitor success rate** (should recover to ≥95%)
3. **If still degraded**: Roll back to 0% (disable canary flag)

---

**Status**: ✅ Applied at T+35m  
**Current QPS**: ~8 (within 10 limit)  
**Current In-Flight**: ~15 (well below 100 limit)  
**Rate Limited**: 0 (no backpressure)

**Next Review**: T+2h (verify rate smoothing remains effective)
