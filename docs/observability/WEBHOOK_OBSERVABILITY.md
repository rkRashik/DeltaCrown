# Webhook Observability Guide

**Version**: 1.0  
**Status**: Production Canary  
**Last Updated**: 2025-11-13  
**Owner**: Platform Team

---

## Overview

This guide covers monitoring, alerting, and troubleshooting for the DeltaCrown webhook delivery system. Includes Prometheus metrics, Grafana dashboards, alert rules, and runbook procedures.

---

## 1. Metrics Architecture

### 1.1 Prometheus Metrics

All webhook metrics are exposed at `/metrics` endpoint and collected by Prometheus every 15 seconds.

**Module**: `apps/notifications/metrics.py`

#### Success Counter

```python
webhook_delivery_success_total{event, endpoint}
```

- **Type**: Counter
- **Labels**:
  - `event`: Event type (e.g., `payment_verified`, `match_started`)
  - `endpoint`: Target webhook URL
- **Description**: Total successful webhook deliveries (HTTP 2xx)
- **Example Query**: `rate(webhook_delivery_success_total[5m])`

#### Failure Counter

```python
webhook_delivery_failure_total{event, endpoint, code}
```

- **Type**: Counter
- **Labels**:
  - `event`: Event type
  - `endpoint`: Target webhook URL
  - `code`: HTTP status code or error type (`400`, `500`, `timeout`, `network_error`)
- **Description**: Total failed webhook deliveries
- **Example Query**: `rate(webhook_delivery_failure_total{code=~"5.."}[5m])`

#### Latency Histogram

```python
webhook_delivery_latency_seconds{event}
```

- **Type**: Histogram
- **Labels**:
  - `event`: Event type
- **Buckets**: 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0 (seconds)
- **Description**: Webhook delivery latency distribution
- **Example Query**: `histogram_quantile(0.95, rate(webhook_delivery_latency_seconds_bucket[5m]))`

#### Retry Counter

```python
webhook_retry_attempts_total{event, attempt}
```

- **Type**: Counter
- **Labels**:
  - `event`: Event type
  - `attempt`: Retry attempt number (1, 2, 3)
- **Description**: Total retry attempts (for 503/timeout errors)
- **Example Query**: `sum(rate(webhook_retry_attempts_total[5m])) by (attempt)`

#### Circuit Breaker Opens Counter

```python
webhook_cb_open_total{endpoint}
```

- **Type**: Counter
- **Labels**:
  - `endpoint`: Target webhook URL
- **Description**: Total circuit breaker open events
- **Example Query**: `increase(webhook_cb_open_total[24h])`

#### Circuit Breaker State Gauge

```python
webhook_cb_state{endpoint}
```

- **Type**: Gauge
- **Labels**:
  - `endpoint`: Target webhook URL
- **Values**:
  - `0`: CLOSED (healthy, accepting requests)
  - `1`: HALF_OPEN (probing after timeout)
  - `2`: OPEN (blocking requests due to failures)
- **Description**: Current circuit breaker state
- **Example Query**: `webhook_cb_state`

---

## 2. Grafana Dashboards

### 2.1 Observability Dashboard

**File**: `grafana/webhooks_canary_observability.json`  
**URL**: `https://grafana.deltacrown.gg/d/webhooks-canary`  
**Refresh**: 30 seconds

#### Panels

1. **Success Rate (%)** (Stat Panel)
   - Query: `sum(rate(webhook_delivery_success_total[5m])) / (sum(rate(webhook_delivery_success_total[5m])) + sum(rate(webhook_delivery_failure_total[5m]))) * 100`
   - Thresholds: <90% (red), <95% (yellow), ≥95% (green)

2. **P95 Latency (ms)** (Stat Panel)
   - Query: `histogram_quantile(0.95, sum(rate(webhook_delivery_latency_seconds_bucket[5m])) by (le)) * 1000`
   - Thresholds: >5000ms (red), >2000ms (yellow), <2000ms (green)

3. **Circuit Breaker Opens (Last 24h)** (Stat Panel)
   - Query: `sum(increase(webhook_cb_open_total[24h]))`
   - Thresholds: >20 (red), >5 (yellow), ≤5 (green)

4. **Circuit Breaker State** (Stat Panel)
   - Query: `webhook_cb_state`
   - Mappings: 0=CLOSED (green), 1=HALF_OPEN (yellow), 2=OPEN (red)

5. **Success vs Failure (Timeseries)**
   - Queries:
     - Success: `sum(rate(webhook_delivery_success_total[5m]))`
     - Failure: `sum(rate(webhook_delivery_failure_total[5m]))`

6. **Latency Percentiles (P50/P95/P99)** (Timeseries)
   - Queries:
     - P50: `histogram_quantile(0.50, sum(rate(webhook_delivery_latency_seconds_bucket[5m])) by (le)) * 1000`
     - P95: `histogram_quantile(0.95, ...)`
     - P99: `histogram_quantile(0.99, ...)`

7. **Retry Distribution** (Bar Chart)
   - Query: `sum(increase(webhook_retry_attempts_total[1h])) by (attempt)`

8. **4xx vs 5xx Errors** (Timeseries)
   - Queries:
     - 4xx: `sum(rate(webhook_delivery_failure_total{code=~"4.."}[5m]))`
     - 5xx: `sum(rate(webhook_delivery_failure_total{code=~"5.."}[5m]))`

9. **Events per Second (by Type)** (Timeseries)
   - Query: `sum(rate(webhook_delivery_success_total[5m])) by (event)`

#### Template Variables

- **event**: Multi-select dropdown (all events)
  - Query: `label_values(webhook_delivery_success_total, event)`
- **endpoint**: Single-select dropdown (all endpoints)
  - Query: `label_values(webhook_delivery_success_total, endpoint)`

---

### 2.2 Alert Rules Dashboard

**File**: `grafana/webhooks_canary_alerts.json`  
**Type**: Prometheus Alert Rules (imported to Prometheus)

#### Critical Alerts (ROLLBACK Triggers)

1. **WebhookSuccessRateCritical**
   - **Condition**: Success rate <90% for ≥5 minutes
   - **Severity**: critical
   - **Action**: IMMEDIATE ROLLBACK + page on-call
   - **Query**: `sum(rate(webhook_delivery_success_total[5m])) / (sum(rate(webhook_delivery_success_total[5m])) + sum(rate(webhook_delivery_failure_total[5m]))) < 0.9`

2. **WebhookP95LatencyCritical**
   - **Condition**: P95 latency >5 seconds for ≥10 minutes
   - **Severity**: critical
   - **Action**: INVESTIGATE + consider rollback
   - **Query**: `histogram_quantile(0.95, sum(rate(webhook_delivery_latency_seconds_bucket[5m])) by (le)) > 5`

3. **WebhookCircuitBreakerOpensExcessive**
   - **Condition**: Circuit breaker opens >5 times in 24 hours
   - **Severity**: critical
   - **Action**: HOLD + investigate receiver
   - **Query**: `sum(increase(webhook_cb_open_total[24h])) > 5`

4. **WebhookCircuitBreakerStuckOpen**
   - **Condition**: Circuit breaker OPEN (state=2) for >5 minutes
   - **Severity**: critical
   - **Action**: Check receiver health + manual reset if needed
   - **Query**: `webhook_cb_state == 2`

#### Warning Alerts

5. **WebhookSuccessRateWarning**
   - **Condition**: Success rate <95% for ≥10 minutes
   - **Severity**: warning
   - **Action**: Monitor closely + investigate failures
   - **Query**: `... < 0.95`

6. **WebhookP95LatencyWarning**
   - **Condition**: P95 latency >2 seconds for ≥15 minutes
   - **Severity**: warning
   - **Action**: Monitor trends + check receiver capacity
   - **Query**: `histogram_quantile(0.95, ...) > 2`

7. **WebhookCircuitBreakerOpening**
   - **Condition**: Circuit breaker opens >1 time in 1 hour
   - **Severity**: warning
   - **Action**: Check receiver intermittent issues
   - **Query**: `sum(increase(webhook_cb_open_total[1h])) > 1`

8. **WebhookHighRetryRate**
   - **Condition**: Retry rate >20% of total deliveries
   - **Severity**: warning
   - **Action**: Investigate receiver 503 errors
   - **Query**: `sum(rate(webhook_retry_attempts_total[5m])) / sum(rate(webhook_delivery_success_total[5m]) + rate(webhook_delivery_failure_total[5m])) > 0.2`

9. **Webhook4xxSpike**
   - **Condition**: 4xx error rate increases >50% in 10 minutes
   - **Severity**: warning
   - **Action**: Check payload schema / validation
   - **Query**: `sum(rate(webhook_delivery_failure_total{code=~"4.."}[5m])) > 1.5 * sum(rate(webhook_delivery_failure_total{code=~"4.."}[15m] offset 10m))`

10. **Webhook5xxSpike**
    - **Condition**: 5xx error rate increases >50% in 10 minutes
    - **Severity**: critical
    - **Action**: Check receiver service health
    - **Query**: `sum(rate(webhook_delivery_failure_total{code=~"5.."}[5m])) > 1.5 * sum(rate(webhook_delivery_failure_total{code=~"5.."}[15m] offset 10m))`

#### Info Alerts

11. **WebhookNoDeliveries**
    - **Condition**: No webhook deliveries for >15 minutes
    - **Severity**: info
    - **Action**: Check if events are being generated
    - **Query**: `sum(rate(webhook_delivery_success_total[5m])) == 0 and sum(rate(webhook_delivery_failure_total[5m])) == 0`

---

## 3. SLO Definitions

### Success Rate SLO

- **Target**: ≥95%
- **Warning**: <95%
- **Critical**: <90% (ROLLBACK trigger)
- **Measurement**: Rolling 5-minute window
- **Formula**: `success / (success + failure)`

### Latency SLO (P95)

- **Target**: <2000 ms
- **Warning**: >2000 ms
- **Critical**: >5000 ms (INVESTIGATE trigger)
- **Measurement**: Rolling 5-minute window
- **Formula**: `histogram_quantile(0.95, rate(webhook_delivery_latency_seconds_bucket[5m]))`

### Circuit Breaker SLO

- **Target**: <5 opens per 24 hours
- **Warning**: >5 opens per 24 hours
- **Critical**: >20 opens per 24 hours (ROLLBACK trigger)
- **Measurement**: Rolling 24-hour window

### PII Leak SLO

- **Target**: 0 leaks (ZERO tolerance)
- **Critical**: ANY leak detected (IMMEDIATE ROLLBACK)
- **Measurement**: Real-time log scanning + manual review

---

## 4. Runbook Procedures

### 4.1 Success Rate <90% (IMMEDIATE ROLLBACK)

**Trigger**: WebhookSuccessRateCritical alert fires

**Actions**:

1. **Immediate**: Set `NOTIFICATIONS_WEBHOOK_ENABLED=false` for canary slice
2. **Verify**: Confirm traffic diverted (success rate should stop dropping)
3. **Investigate**: Check last 50 failed webhooks
   ```bash
   grep "webhook_delivery_failed" /var/log/deltacrown.log | tail -50
   ```
4. **RCA**: Complete rollback RCA template (see Section 5)
5. **Notify**: Post to `#webhooks-canary` + page platform team

### 4.2 P95 Latency >5s (INVESTIGATE)

**Trigger**: WebhookP95LatencyCritical alert fires

**Actions**:

1. **Check Receiver**: Verify receiver service health
   ```bash
   curl -X GET https://api.deltacrown.gg/webhooks/health
   ```
2. **Check Database**: Look for slow queries / connection pool saturation
3. **Check Network**: Measure network latency to receiver
   ```bash
   ping api.deltacrown.gg
   tracert api.deltacrown.gg
   ```
4. **Consider Rollback**: If latency remains >5s for >15 minutes
5. **Notify**: Post to `#webhooks-canary` with investigation findings

### 4.3 Circuit Breaker Stuck OPEN (MANUAL RESET)

**Trigger**: WebhookCircuitBreakerStuckOpen alert fires

**Actions**:

1. **Verify Receiver Health**: Confirm receiver is healthy and accepting requests
2. **Manual Reset**: Force circuit breaker to HALF_OPEN
   ```python
   from apps.notifications.services.circuit_breaker import CircuitBreaker
   cb = CircuitBreaker.get_instance("https://api.deltacrown.gg/webhooks")
   cb.force_half_open()
   ```
3. **Monitor**: Watch for successful probe delivery
4. **Investigate Root Cause**: Why did CB stick? (timeout issue, network partition, etc.)

### 4.4 High 4xx Error Rate (SCHEMA ISSUE)

**Trigger**: Webhook4xxSpike alert fires

**Actions**:

1. **Sample Failed Requests**: Get last 10 failed requests with 4xx
   ```bash
   grep "status=4" /var/log/deltacrown.log | tail -10
   ```
2. **Check Payload Schema**: Compare sent payload vs receiver expectations
3. **Check Documentation**: Verify we're following receiver's webhook contract
4. **Test Receiver**: Send test webhook to `/webhooks/test` endpoint
5. **Fix or Rollback**: If schema mismatch, fix payload or rollback

### 4.5 PII Leak Detected (IMMEDIATE ROLLBACK)

**Trigger**: Manual detection via log scan or automated PII scanner

**Actions**:

1. **IMMEDIATE ROLLBACK**: Set `NOTIFICATIONS_WEBHOOK_ENABLED=false`
2. **Quarantine Logs**: Move logs containing PII to secure storage
3. **Notify Security**: Page security team + file incident
4. **Redact PII**: Remove PII from affected payloads
5. **RCA**: Complete security incident RCA (separate template)

---

## 5. Rollback RCA Template

```markdown
# Webhook Canary Rollback — Root Cause Analysis

**Incident ID**: INC-YYYYMMDD-NNNN  
**Rollback Time**: YYYY-MM-DDTHH:MM:SSZ  
**Duration**: N hours  
**Trigger**: [Alert name or manual detection]

## 1. Timeline

- **T+0m**: Canary started at [timestamp]
- **T+Xm**: Alert fired: [alert name]
- **T+Ym**: Rollback executed
- **T+Zm**: Traffic confirmed diverted

## 2. Root Cause

[Detailed explanation of what went wrong]

## 3. Impact

- Affected traffic: X% of webhooks
- Failed deliveries: N webhooks
- Data loss: [Yes/No, details]
- PII leak: [Yes/No, details]

## 4. Resolution

[How issue was resolved]

## 5. Action Items

- [ ] Fix identified issue
- [ ] Add tests to prevent recurrence
- [ ] Update documentation
- [ ] Schedule retry canary (if applicable)
```

---

## 6. Testing Observability

**Test Suite**: `tests/observability/test_webhooks_metrics.py`

Run metrics tests:

```bash
pytest tests/observability/test_webhooks_metrics.py -v
```

Run Grafana dashboard validation:

```bash
pytest tests/observability/test_grafana_dashboards.py -v
```

---

## 7. Local Development

### Running Prometheus Locally

```bash
# Install Prometheus
# macOS: brew install prometheus
# Windows: Download from prometheus.io

# Configure scrape target
cat > prometheus.yml <<EOF
scrape_configs:
  - job_name: 'deltacrown'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
EOF

# Start Prometheus
prometheus --config.file=prometheus.yml
```

### Running Grafana Locally

```bash
# Install Grafana
# macOS: brew install grafana
# Windows: Download from grafana.com

# Start Grafana
grafana-server --config=/usr/local/etc/grafana/grafana.ini

# Access at http://localhost:3000
# Default credentials: admin / admin
```

### Import Dashboards

1. Open Grafana: `http://localhost:3000`
2. Navigate to Dashboards → Import
3. Upload `grafana/webhooks_canary_observability.json`
4. Select Prometheus data source
5. Click "Import"

---

## 8. Appendix

### A. Metric Label Cardinality

**Important**: Keep label cardinality low to avoid Prometheus performance issues.

- `event`: ~10 unique values (limited by event types)
- `endpoint`: ~5 unique values (limited by configured receivers)
- `code`: ~20 unique values (HTTP status codes + error types)

**Total Cardinality**: ~1,000 timeseries (acceptable for Prometheus)

### B. Retention Policies

- **Prometheus**: 30 days (scrape interval: 15s)
- **Grafana Annotations**: 90 days
- **Raw Logs**: 90 days (compressed)

### C. Export Metrics for Analysis

```bash
# Export last 24h of metrics to CSV
curl -G http://localhost:9090/api/v1/query_range \
  --data-urlencode 'query=webhook_delivery_success_total' \
  --data-urlencode 'start=2025-11-12T14:30:00Z' \
  --data-urlencode 'end=2025-11-13T14:30:00Z' \
  --data-urlencode 'step=60s' \
  | jq -r '.data.result[] | [.metric.event, .values[][1]] | @csv' > metrics.csv
```

---

**Questions?** Contact `#platform-team` or email `platform@deltacrown.gg`
