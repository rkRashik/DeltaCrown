# Module 8.3: Observability & Cache Notes

## Overview

This module implements observability for moderation enforcement with caching layer for performance optimization. **All features default to OFF or safe defaults** to ensure zero behavior change until explicitly enabled.

---

## Feature Flags & Defaults

### Observability Flag (DEFAULT: OFF)
```python
# settings.py or environment
MODERATION_OBSERVABILITY_ENABLED = False  # Must be explicitly enabled
```

**Impact**: When `false` (default), no metrics are emitted, no sampling occurs, zero overhead.

### Cache Flags (DEFAULT: ON with safe TTL)
```python
MODERATION_CACHE_ENABLED = True  # Cache layer active by default
MODERATION_CACHE_TTL_SECONDS = 60  # 1-minute TTL (configurable)
```

**Impact**: Cache improves performance but can be disabled if needed. TTL ensures fresh data.

---

## Sampling Strategy

### Design
- **Sampling Rate**: 10% of moderation gate decisions (configurable via `MODERATION_SAMPLING_RATE`)
- **Why Sample**: Reduce metrics volume in high-traffic scenarios
- **When to Adjust**: Increase to 100% during incident investigation

### Configuration
```python
# Environment variable
MODERATION_SAMPLING_RATE=0.10  # 10% (default)

# Or in settings.py
MODERATION_SAMPLING_RATE = float(os.getenv('MODERATION_SAMPLING_RATE', '0.10'))
```

### Implementation Notes
- Uses `random.random() < sample_rate` for decision
- Sampling happens **after** gate decision (does not affect enforcement logic)
- Sampled events are tagged with `sampled=true` label in Prometheus

---

## PII Guard Rules

### Rejected Patterns
Observability payloads **must not** contain:
1. **Email addresses**: `user@example.com` → Use hashed user ID instead
2. **IP addresses**: `192.168.1.1` → Use country/region code
3. **Usernames**: `john_doe_123` → Use numeric user ID or hash

### Regex Patterns (enforced in tests and CI)
```regex
Email:    [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
IP:       \b(?:\d{1,3}\.){3}\d{1,3}\b
Username: \buser_[a-zA-Z0-9_]{3,}\b
```

### Safe Alternatives
```python
# ❌ BAD: Contains PII
payload = {"user_email": "john@example.com", "ip": "10.0.0.1"}

# ✅ GOOD: Hashed/anonymized
payload = {"user_id_hash": "abc123def", "country": "US", "region": "CA"}
```

### Enforcement
- **Test**: `test_observability_drops_pii_payloads_email_ip_username`
- **CI Job**: `ci/pii-scan.yml` rejects commits with PII in observability code

---

## Alert Thresholds

### Deny Rate
**Symptom**: High percentage of gate decisions resulting in "deny"

| Threshold | Duration | Severity | Action |
|-----------|----------|----------|--------|
| >5% | 10 minutes | WARN | Investigate for policy changes or attacks |
| >10% | 10 minutes | CRIT | Page on-call, check for ban wave or misconfiguration |

**Query**:
```promql
100 * (
  sum(rate(moderation_gate_decisions_total{result="deny"}[10m]))
  /
  sum(rate(moderation_gate_decisions_total[10m]))
) > 5
```

---

### p95 Latency
**Symptom**: Gate decisions taking too long (impacts user experience)

| Threshold | Duration | Severity | Action |
|-----------|----------|----------|--------|
| >150ms | 5 minutes | WARN | Check cache hit rate, DB query performance |
| >250ms | 5 minutes | CRIT | Page on-call, consider degraded mode (skip enforcement) |

**Query**:
```promql
histogram_quantile(0.95, rate(moderation_gate_latency_seconds_bucket[5m])) > 0.150
```

---

### Cache Hit Rate
**Symptom**: Too many cache misses (excessive DB load)

| Threshold | Duration | Severity | Action |
|-----------|----------|----------|--------|
| <60% | 10 minutes | WARN | Check cache eviction, TTL too short, or invalidation storms |
| <40% | 10 minutes | CRIT | Page on-call, increase cache size or disable enforcement temporarily |

**Query**:
```promql
100 * (
  sum(rate(moderation_cache_hits_total[10m]))
  /
  (sum(rate(moderation_cache_hits_total[10m])) + sum(rate(moderation_cache_misses_total[10m])))
) < 60
```

---

## Grafana Dashboard Import

### Prerequisites
1. **Prometheus datasource** configured in Grafana
2. Metrics emitted by application (requires `MODERATION_OBSERVABILITY_ENABLED=true`)

### Import Steps
1. Navigate to **Dashboards** → **Import**
2. Upload `grafana/moderation_enforcement_dashboard.json`
3. Select Prometheus datasource from dropdown (dashboard uses `${DS_PROMETHEUS}` placeholder)
4. Click **Import**

### Verify Import
- Dashboard UID: `moderation-enforcement`
- Expected panels: 6 (decisions, deny %, latency, cache hit rate, invalidations, dropped events)
- Variables: `environment` (production/staging/development), `service` (deltacrown)

### Dashboard JSON Integrity
```bash
# Verify sha256 hash (expected value filled by CI)
sha256sum grafana/moderation_enforcement_dashboard.json
# Expected: <SHA256_TBD_AFTER_CI>
```

---

## Prometheus Metrics Reference

### Decision Counters
```
moderation_gate_decisions_total{result="allow|deny", reason="BANNED|SUSPENDED|MUTED|NONE"}
```
- **Type**: Counter
- **Labels**: `result` (allow/deny), `reason` (sanction type or NONE)
- **Usage**: Track allow/deny rates, detect ban waves

### Latency Histogram
```
moderation_gate_latency_seconds_bucket
moderation_gate_latency_seconds_sum
moderation_gate_latency_seconds_count
```
- **Type**: Histogram
- **Buckets**: [0.01, 0.05, 0.1, 0.15, 0.25, 0.5, 1.0] (seconds)
- **Usage**: Calculate p50/p95/p99 latency

### Cache Metrics
```
moderation_cache_hits_total
moderation_cache_misses_total
moderation_cache_invalidations_total
```
- **Type**: Counters
- **Usage**: Calculate hit rate, detect invalidation storms

### Observability Drops
```
moderation_observability_dropped_total{reason="pii_rejected|rate_limited"}
```
- **Type**: Counter
- **Labels**: `reason` (why event was dropped)
- **Usage**: Monitor PII guard effectiveness, sampling health

---

## Troubleshooting

### No metrics appearing in Grafana
1. **Check flag**: `MODERATION_OBSERVABILITY_ENABLED=true` in environment
2. **Verify Prometheus scrape**: `curl http://localhost:8000/metrics | grep moderation_`
3. **Check datasource**: Grafana → Configuration → Data Sources → Prometheus (test connection)

### Cache hit rate < 60%
1. **TTL too short**: Increase `MODERATION_CACHE_TTL_SECONDS` from 60 to 300 (5 min)
2. **Invalidation storms**: Check `moderation_cache_invalidations_total` rate, may indicate bulk revokes
3. **Cache size**: Check Redis `maxmemory` setting, may be evicting too aggressively

### Deny rate spike (>10%)
1. **Check admin actions**: Look for bulk ban operations in Django admin logs
2. **Attack pattern**: Inspect `reason` label distribution (all BANNED = possible ban wave)
3. **Policy change**: Verify no recent changes to sanction creation logic

---

## Zero Behavior Change Confirmation

**Default State** (before enabling observability):
- ✅ `MODERATION_OBSERVABILITY_ENABLED=false` → No metrics emitted, zero overhead
- ✅ `MODERATION_CACHE_ENABLED=true` with `TTL=60s` → Cache active but transparent to users
- ✅ Enforcement logic unchanged (sanctions still applied as before)

**To Enable Observability**:
1. Set `MODERATION_OBSERVABILITY_ENABLED=true` in environment
2. Restart application
3. Verify metrics at `/metrics` endpoint
4. Import Grafana dashboard

**Rollback Plan**:
1. Set `MODERATION_OBSERVABILITY_ENABLED=false`
2. Restart application
3. Metrics stop emitting immediately (no data loss, counters reset on next enable)

---

## Related Documentation
- [Flags Configuration](../config/flags.md) - All feature flags and defaults
- [Alert Matrix](../ops/ALERT_MATRIX.md) - Symptom → cause → action mapping
- [Performance Runbook](../PERF_RUNBOOK.md) - SLO baselines and tuning
- [Test Coverage](../../tests/observability/test_sanction_cache_and_metrics.py) - 12 observability tests
