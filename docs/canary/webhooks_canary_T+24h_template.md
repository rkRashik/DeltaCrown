# Webhook Canary T+24h Report

**Report ID**: `canary-webhooks-5pct-{{report_timestamp}}`  
**Canary Start**: {{start_time}}  
**Report Time**: {{report_time}}  
**Elapsed**: {{elapsed_hours}} hours  
**Traffic Allocation**: {{traffic_percent}}%  
**Verdict**: {{verdict}}

---

## Executive Summary

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Success Rate | ≥95% | {{success_rate}}% | {{success_status}} |
| P95 Latency | <2000ms | {{p95_ms}}ms | {{p95_status}} |
| Circuit Breaker Opens | <5/day | {{cb_opens}} | {{cb_status}} |
| PII Leaks | 0 | {{pii_leaks}} | {{pii_status}} |

**Overall SLO Status**: {{overall_slo_status}}

**Recommendation**: {{recommendation}}

---

## Timeline

| Milestone | Timestamp | Metrics | Notes |
|-----------|-----------|---------|-------|
| Canary Start | {{start_time}} | - | Secret rotated, 5% traffic enabled |
| Guardrails Applied | {{guardrails_time}} | - | DB pool + rate smoothing + alerts |
| T+30m Report | {{t30m_time}} | Success: {{t30m_success}}%, P95: {{t30m_p95}}ms | {{t30m_verdict}} |
| T+2h Report | {{t2h_time}} | Success: {{t2h_success}}%, P95: {{t2h_p95}}ms | {{t2h_verdict}} |
| **T+24h Report** | {{t24h_time}} | Success: {{success_rate}}%, P95: {{p95_ms}}ms | {{verdict}} |

---

## Detailed Metrics

### Hourly Rollup (24 hours)

| Hour | Delivered | Failed | Success Rate | P50 | P95 | P99 | CB Opens |
|------|-----------|--------|--------------|-----|-----|-----|----------|
{{hourly_rollup_rows}}

**Total**: {{total_delivered}} delivered, {{total_failed}} failed, **{{success_rate}}% success**

### Delta vs Previous Reports

| Report | Success Rate | P95 Latency | CB Opens | Notes |
|--------|--------------|-------------|----------|-------|
| T+30m | {{t30m_success}}% | {{t30m_p95}}ms | {{t30m_cb}} | {{t30m_delta_notes}} |
| T+2h | {{t2h_success}}% | {{t2h_p95}}ms | {{t2h_cb}} | {{t2h_delta_notes}} |
| **T+24h** | **{{success_rate}}%** | **{{p95_ms}}ms** | **{{cb_opens}}** | {{t24h_delta_notes}} |

**Trend**: {{trend_summary}}

---

## Event Breakdown by Type

| Event Type | Count | Success Rate | Avg Latency | Failures | Notes |
|------------|-------|--------------|-------------|----------|-------|
{{event_breakdown_rows}}

**Highest Volume**: {{highest_volume_event}} ({{highest_volume_count}} events)  
**Highest Failure Rate**: {{highest_failure_event}} ({{highest_failure_rate}}%)

---

## Failure Analysis

### Failure Categories

| Category | Count | % of Failures | Root Cause | Mitigation |
|----------|-------|---------------|------------|------------|
{{failure_category_rows}}

### Top 5 Failures (by frequency)

{{failure_details}}

---

## Retry Distribution

| Retry Count | Deliveries | % of Total | Notes |
|-------------|------------|------------|-------|
| 0 (no retry) | {{retry_0}} | {{retry_0_pct}}% | Success on first attempt |
| 1 retry | {{retry_1}} | {{retry_1_pct}}% | Recovered after 2s backoff |
| 2 retries | {{retry_2}} | {{retry_2_pct}}% | Recovered after 4s backoff |
| 3 retries (max) | {{retry_3}} | {{retry_3_pct}}% | Exhausted retries, failed |

**Retry Effectiveness**: {{retry_effectiveness}}% (recovered after retry / total retried)

---

## Circuit Breaker Status

| Endpoint | State | Opens (24h) | Half-Open Attempts | Last Event | Notes |
|----------|-------|-------------|-------------------|------------|-------|
{{cb_status_rows}}

**Circuit Breaker Opens**: {{cb_opens}} (Target: <5/day)  
**Status**: {{cb_opens_status}}

---

## Database Health

### Receiver DB Pool (PgBouncer)

```sql
-- pg_stat_activity snapshot (T+24h)
{{pg_stat_activity_snapshot}}
```

**Long-running queries**: {{long_queries_count}} (threshold: >5s)  
**Pool utilization**: {{pool_utilization}}% ({{active_conns}}/{{max_conns}})  
**Status**: {{db_health_status}}

### Sender Rate Limiting

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| QPS (avg) | ≤10 | {{qps_avg}} | {{qps_status}} |
| QPS (p95) | ≤15 | {{qps_p95}} | {{qps_p95_status}} |
| In-flight (avg) | ≤100 | {{inflight_avg}} | {{inflight_status}} |
| In-flight (max) | ≤100 | {{inflight_max}} | {{inflight_max_status}} |
| Rate-limited events | 0 | {{rate_limited}} | {{rate_limited_status}} |

**Rate smoothing effectiveness**: {{rate_smoothing_notes}}

---

## PII Compliance Audit

### Grep Scans (5 patterns)

```bash
# Scan command (executed at {{pii_scan_time}})
grep -r -E '(email|username|ip_address|phone|card)' logs/webhooks/canary/*.log

# Results:
{{pii_scan_results}}
```

**Email addresses**: {{email_matches}} matches  
**Usernames**: {{username_matches}} matches  
**IP addresses**: {{ip_matches}} matches  
**Phone numbers**: {{phone_matches}} matches  
**Card numbers**: {{card_matches}} matches  

**Total PII leaks**: **{{pii_leaks}}** (Target: 0)  
**Status**: {{pii_status}}

### Payload Sampling (10 random deliveries)

{{payload_sample_summary}}

---

## Guardrails Effectiveness

### Before Guardrails (T+0 to T+35m)

| Metric | Value | Notes |
|--------|-------|-------|
| DB pool failures | {{pre_guardrail_db_failures}} | 3 × 503 Service Unavailable |
| Success rate | {{pre_guardrail_success}}% | Below 95% target |
| P95 latency | {{pre_guardrail_p95}}ms | Acceptable but unstable |

### After Guardrails (T+35m to T+24h)

| Metric | Value | Delta | Notes |
|--------|-------|-------|-------|
| DB pool failures | {{post_guardrail_db_failures}} | {{db_failure_delta}} | {{db_failure_notes}} |
| Success rate | {{success_rate}}% | {{success_delta}} | {{success_notes}} |
| P95 latency | {{p95_ms}}ms | {{p95_delta}}ms | {{p95_notes}} |

**Guardrail impact**: {{guardrail_impact_summary}}

---

## Latency Percentiles (24h window)

| Percentile | Latency (ms) | Target | Status |
|------------|--------------|--------|--------|
| P50 | {{p50_ms}} | - | ℹ️ |
| P75 | {{p75_ms}} | - | ℹ️ |
| P90 | {{p90_ms}} | - | ℹ️ |
| **P95** | **{{p95_ms}}** | **<2000ms** | {{p95_status}} |
| P99 | {{p99_ms}} | - | ℹ️ |
| Max | {{max_ms}} | - | ℹ️ |

**Latency trend**: {{latency_trend}}

---

## Alert Summary

### Alerts Fired (24h)

{{alerts_fired_table}}

**Total alerts**: {{total_alerts}}  
**Critical alerts**: {{critical_alerts}}  
**Warning alerts**: {{warning_alerts}}

### Alert Rules Status

| Rule | Threshold | Status | Notes |
|------|-----------|--------|-------|
| Success rate <90% (critical) | 5min window | {{alert_success_90_status}} | {{alert_success_90_notes}} |
| Success rate <95% (warning) | 10min window | {{alert_success_95_status}} | {{alert_success_95_notes}} |
| P95 >5s (critical) | 10min window | {{alert_p95_5s_status}} | {{alert_p95_5s_notes}} |
| P95 >2s (warning) | 15min window | {{alert_p95_2s_status}} | {{alert_p95_2s_notes}} |
| CB opens >5/24h | 24h window | {{alert_cb_status}} | {{alert_cb_notes}} |
| CB stuck OPEN | 5min window | {{alert_cb_stuck_status}} | {{alert_cb_stuck_notes}} |

---

## Risk Assessment

### Risks Identified

{{risk_table}}

### Mitigations Applied

{{mitigation_table}}

---

## Decision Matrix

### Promotion Criteria (ALL must be met)

| Criterion | Required | Actual | Met? |
|-----------|----------|--------|------|
| Success rate ≥95% | ✅ | {{success_rate}}% | {{success_criterion}} |
| P95 latency <2000ms | ✅ | {{p95_ms}}ms | {{p95_criterion}} |
| CB opens <5/day | ✅ | {{cb_opens}} | {{cb_criterion}} |
| PII leaks = 0 | ✅ | {{pii_leaks}} | {{pii_criterion}} |
| No critical alerts | ✅ | {{critical_alerts}} | {{alert_criterion}} |

**All criteria met**: {{all_criteria_met}}

### Recommendation

{{#if all_criteria_met}}
✅ **PROMOTE TO 25%**

**Reasoning**:
- All SLO gates GREEN for full 24h window
- Guardrails effective (success rate improved {{success_improvement}}%)
- No PII leaks detected
- No critical alerts fired
- DB pool stable ({{pool_utilization}}% utilization)
- Rate smoothing working (0 backpressure events)

**Next Steps**:
1. Update feature flag: `NOTIFICATIONS_WEBHOOK_ENABLED=True` for 25% instances
2. Generate new webhook secret for 25% slice
3. Monitor T+2h checkpoint (due {{next_t2h_time}})
4. Schedule T+24h report (due {{next_t24h_time}})
5. Maintain guardrails (DB pool + rate smoothing + alerts)

**Rollback Trigger**:
- Success rate drops below 93% for >10min
- P95 latency exceeds 3s for >10min
- CB opens >5 in any 24h window
- Any PII leak detected

{{else}}
❌ **ROLLBACK TO 0%**

**Reasoning**:
{{rollback_reasoning}}

**Failed Criteria**:
{{failed_criteria_list}}

**Rollback Steps**:
1. Set `NOTIFICATIONS_WEBHOOK_ENABLED=False` for all 5% instances
2. Verify webhook delivery stops within 5 minutes
3. Generate post-mortem report (template: `docs/canary/postmortem_template.md`)
4. Schedule RCA meeting within 24h
5. Document learnings in `docs/canary/lessons_learned.md`

**Before Next Canary**:
{{rollback_blockers}}
{{/if}}

---

## Evidence Artifacts

| Artifact | Location | Description |
|----------|----------|-------------|
| Raw metrics | `evidence/canary/hourly/T+{{hour}}.json` | 24 JSON files (hourly snapshots) |
| 6h bundles | `evidence/canary/6h/bundle_{{n}}.zip` | 4 ZIP files (6h evidence windows) |
| Grafana snapshots | `evidence/canary/grafana/T+24h_*.png` | Dashboard screenshots |
| DB pool logs | `evidence/canary/db/pgbouncer_show_pools_T+24h.txt` | PgBouncer SHOW POOLS output |
| Alert history | `evidence/canary/alerts/prometheus_alerts_T+24h.json` | Prometheus alert manager export |
| PII scans | `evidence/canary/pii/grep_results_T+24h.txt` | Grep scan outputs |

---

## Appendix A: Configuration

### Canary Flags

```bash
# Sender (5% instances)
NOTIFICATIONS_WEBHOOK_ENABLED=True
WEBHOOK_ENDPOINT={{webhook_endpoint}}
WEBHOOK_SECRET={{webhook_secret_hash}}  # SHA256 hash
WEBHOOK_TIMEOUT=10
WEBHOOK_MAX_RETRIES=3

# Receiver
PGBOUNCER_POOL_MODE=transaction
PGBOUNCER_DEFAULT_POOL_SIZE=25
PGBOUNCER_RESERVE_POOL_SIZE=10
PGBOUNCER_STATEMENT_TIMEOUT=5000  # 5 seconds
```

### Rate Limiting

```python
# Token bucket config
WEBHOOK_RATE_LIMIT_QPS = 10  # 5% of 200 QPS total
WEBHOOK_RATE_LIMIT_BURST = 20  # 2× multiplier
WEBHOOK_MAX_INFLIGHT = 100  # Semaphore limit
```

### Alert Rules (excerpt)

```yaml
# Prometheus alert rules
groups:
  - name: webhook_canary
    interval: 30s
    rules:
      - alert: WebhookSuccessRateLow
        expr: rate(webhook_delivery_success_total[5m]) < 0.90
        labels:
          severity: critical
        annotations:
          summary: "Webhook success rate <90%"
```

---

## Appendix B: Methodology

### Success Rate Calculation

```python
success_rate = (
    sum(delivered_200_201_202_204) / 
    (sum(delivered_*) + sum(failed_*))
) * 100
```

### P95 Latency Calculation

```sql
-- PostgreSQL percentile_cont
SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)
FROM webhook_deliveries
WHERE created_at >= '{{start_time}}'
  AND created_at < '{{end_time}}';
```

### Circuit Breaker Logic

```python
# Open condition
if failure_rate > 0.5 and request_volume > 10:
    state = OPEN
    
# Half-open condition (after 60s cooldown)
if time_since_open > 60:
    state = HALF_OPEN
    
# Close condition (3 consecutive successes in half-open)
if consecutive_successes >= 3:
    state = CLOSED
```

---

**Report Generated**: {{generation_time}}  
**Generator**: `scripts/generate_webhook_canary_report.py`  
**Template Version**: 1.0.0  
**Operator**: {{operator_name}}
