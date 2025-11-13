# Webhook Canary Runbook

**Version**: 1.0.0  
**Last Updated**: 2025-11-13  
**Owner**: Platform Team  
**Scope**: Production webhook delivery canary rollout (5% → 25% → 100%)

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-flight Checklist](#pre-flight-checklist)
3. [T+30m Checkpoint](#t30m-checkpoint)
4. [T+2h Checkpoint](#t2h-checkpoint)
5. [T+24h Checkpoint](#t24h-checkpoint)
6. [Promotion Decision](#promotion-decision)
7. [Rollback Procedure](#rollback-procedure)
8. [Emergency Contacts](#emergency-contacts)

---

## Overview

### Canary Strategy

| Phase | Traffic | Duration | Decision Point |
|-------|---------|----------|----------------|
| Phase 1 | 5% | 24h | T+30m, T+2h, T+24h |
| Phase 2 | 25% | 48h | T+2h, T+24h, T+48h |
| Phase 3 | 100% | Ongoing | Daily monitoring |

### SLO Gates (ALL must be met)

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Success Rate | ≥95% | <90% triggers immediate rollback |
| P95 Latency | <2000ms | >5000ms triggers immediate rollback |
| Circuit Breaker Opens | <5/day | >10/day triggers immediate rollback |
| PII Leaks | 0 | Any leak triggers immediate rollback |

### Guardrails

1. **Receiver DB Pool**: PgBouncer with pool_mode=transaction, statement_timeout=5s
2. **Sender Rate Smoothing**: Token bucket (10 QPS for 5%, 50 QPS for 25%, 200 QPS for 100%)
3. **Alert Rules**: 12 Prometheus alerts (6 critical, 6 warning)
4. **Circuit Breaker**: Per-endpoint CB with 60s timeout, 50% error threshold

---

## Pre-flight Checklist

**Timeline**: T-30min to T+0

### 1. Environment Preparation

```bash
# Generate fresh webhook secret
python -c "import secrets; import hashlib; secret = secrets.token_hex(32); print(f'Secret: {secret}'); print(f'SHA256: {hashlib.sha256(secret.encode()).hexdigest()}')"

# Verify secret length ≥32 chars
echo -n "$WEBHOOK_SECRET" | wc -c  # Should be ≥32

# Update .env for 5% instances (e.g., prod-webhook-001 to prod-webhook-005)
# NOTIFICATIONS_WEBHOOK_ENABLED=True
# WEBHOOK_ENDPOINT=https://receiver.example.com/webhooks
# WEBHOOK_SECRET=<generated_secret>
# WEBHOOK_TIMEOUT=10
# WEBHOOK_MAX_RETRIES=3
```

### 2. Infrastructure Verification

```bash
# Verify PgBouncer config on receiver
PGPASSWORD=$DB_PASSWORD psql -h pgbouncer.prod -U webhook_user -d webhooks -c "SHOW POOLS;"
# Expected: pool_mode=transaction, default_pool_size=25

# Verify Prometheus alerts active
curl -s http://prometheus.prod:9090/api/v1/rules | jq '.data.groups[] | select(.name=="webhook_canary")'
# Expected: 12 rules active

# Verify Grafana dashboard accessible
curl -s -H "Authorization: Bearer $GRAFANA_API_KEY" \
  http://grafana.prod:3000/api/dashboards/uid/webhook-canary-observability
# Expected: HTTP 200
```

### 3. Documentation

```bash
# Create evidence directory
mkdir -p evidence/canary/{hourly,6h,grafana,db,alerts,pii}

# Create reports directory
mkdir -p reports/canary/

# Copy smoke test payload
cp evidence/canary/smoke.json evidence/canary/smoke_backup_$(date +%Y%m%d_%H%M%S).json
```

### 4. Communication

- [ ] Post in `#platform-ops`: "🚀 Webhook canary starting in 30 minutes (5% traffic)"
- [ ] Update status page: "Webhook delivery canary in progress"
- [ ] Set Slack reminder for T+30m, T+2h, T+24h checkpoints

### 5. Enable Canary

```bash
# Enable feature flag for 5% instances (Kubernetes example)
kubectl set env deployment/webhook-sender-001 NOTIFICATIONS_WEBHOOK_ENABLED=True
kubectl set env deployment/webhook-sender-002 NOTIFICATIONS_WEBHOOK_ENABLED=True
kubectl set env deployment/webhook-sender-003 NOTIFICATIONS_WEBHOOK_ENABLED=True
kubectl set env deployment/webhook-sender-004 NOTIFICATIONS_WEBHOOK_ENABLED=True
kubectl set env deployment/webhook-sender-005 NOTIFICATIONS_WEBHOOK_ENABLED=True

# Verify deployments rolled out
kubectl rollout status deployment/webhook-sender-001
# ... (repeat for 002-005)

# Record start time
date -u +"%Y-%m-%dT%H:%M:%SZ" > evidence/canary/start_time.txt
echo "Canary started at $(cat evidence/canary/start_time.txt)"
```

**Pre-flight Complete**: ✅ Ready to start T+30m observation

---

## T+30m Checkpoint

**Timeline**: T+25m to T+35m  
**Purpose**: Early smoke test, identify immediate issues

### 1. Collect Metrics

```bash
# Export Prometheus metrics (last 30 minutes)
START_TIME=$(cat evidence/canary/start_time.txt)
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

curl -G http://prometheus.prod:9090/api/v1/query_range \
  --data-urlencode 'query=rate(webhook_delivery_success_total[5m])' \
  --data-urlencode "start=$START_TIME" \
  --data-urlencode "end=$END_TIME" \
  --data-urlencode 'step=60s' \
  > evidence/canary/metrics_T+30m_success.json

curl -G http://prometheus.prod:9090/api/v1/query_range \
  --data-urlencode 'query=histogram_quantile(0.95, rate(webhook_delivery_duration_seconds_bucket[5m]))' \
  --data-urlencode "start=$START_TIME" \
  --data-urlencode "end=$END_TIME" \
  --data-urlencode 'step=60s' \
  > evidence/canary/metrics_T+30m_p95.json

# Calculate summary stats
python scripts/calculate_canary_metrics.py \
  --window 30m \
  --output evidence/canary/summary_T+30m.json
```

### 2. Check SLO Gates

```bash
# Parse summary JSON
SUCCESS_RATE=$(jq -r '.success_rate' evidence/canary/summary_T+30m.json)
P95_MS=$(jq -r '.p95_ms' evidence/canary/summary_T+30m.json)
CB_OPENS=$(jq -r '.cb_opens' evidence/canary/summary_T+30m.json)
PII_LEAKS=$(jq -r '.pii_leaks' evidence/canary/summary_T+30m.json)

echo "T+30m Metrics:"
echo "  Success Rate: ${SUCCESS_RATE}% (target: ≥95%)"
echo "  P95 Latency: ${P95_MS}ms (target: <2000ms)"
echo "  CB Opens: ${CB_OPENS} (target: <5/day = <1 in 30min)"
echo "  PII Leaks: ${PII_LEAKS} (target: 0)"

# Check gates
if (( $(echo "$SUCCESS_RATE < 90" | bc -l) )); then
  echo "❌ CRITICAL: Success rate <90% - IMMEDIATE ROLLBACK REQUIRED"
  exit 1
elif (( $(echo "$SUCCESS_RATE < 95" | bc -l) )); then
  echo "⚠️  WARNING: Success rate <95% but ≥90% - investigate and apply guardrails"
fi

if (( $(echo "$P95_MS > 5000" | bc -l) )); then
  echo "❌ CRITICAL: P95 latency >5s - IMMEDIATE ROLLBACK REQUIRED"
  exit 1
elif (( $(echo "$P95_MS > 2000" | bc -l) )); then
  echo "⚠️  WARNING: P95 latency >2s but <5s - monitor closely"
fi

if (( $PII_LEAKS > 0 )); then
  echo "❌ CRITICAL: PII leak detected - IMMEDIATE ROLLBACK REQUIRED"
  exit 1
fi
```

### 3. Generate T+30m Report

```bash
# Use report generator
python scripts/generate_webhook_canary_report.py \
  --start-time "$(cat evidence/canary/start_time.txt)" \
  --metrics-file evidence/canary/summary_T+30m.json \
  --output reports/canary_T+30m.md \
  --operator "$(whoami)"

# Review report
cat reports/canary_T+30m.md
```

### 4. Decision: Continue or Rollback?

**If all gates green** (success ≥95%, P95 <2s, CB <1, PII=0):
- ✅ Continue to T+2h
- Post in `#platform-ops`: "✅ T+30m checkpoint PASS - continuing"
- No action required

**If success 90-95% (marginal)**:
- ⚠️ Apply guardrails immediately (see [Guardrails](#guardrails-application))
- Continue to T+2h with increased monitoring
- Post in `#platform-ops`: "⚠️ T+30m checkpoint MARGINAL - guardrails applied"

**If any critical threshold breached**:
- ❌ Immediate rollback (see [Rollback Procedure](#rollback-procedure))
- Post in `#platform-ops`: "❌ T+30m checkpoint FAIL - rolling back"

---

## T+2h Checkpoint

**Timeline**: T+1h 55m to T+2h 10m  
**Purpose**: Validate guardrail effectiveness, confirm stability

### 1. Collect Metrics

```bash
# Export 2-hour window metrics
START_TIME=$(cat evidence/canary/start_time.txt)
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

python scripts/calculate_canary_metrics.py \
  --window 2h \
  --output evidence/canary/summary_T+2h.json

# Snapshot receiver DB pool health
PGPASSWORD=$DB_PASSWORD psql -h pgbouncer.prod -U webhook_user -d webhooks \
  -c "SHOW POOLS;" \
  > evidence/canary/db/pgbouncer_show_pools_T+2h.txt

PGPASSWORD=$DB_PASSWORD psql -h pgbouncer.prod -U webhook_user -d webhooks \
  -c "SELECT pid, usename, application_name, client_addr, state, query_start, state_change, wait_event_type, wait_event, query FROM pg_stat_activity WHERE datname = 'webhooks' AND state != 'idle' ORDER BY query_start;" \
  > evidence/canary/db/pg_stat_activity_T+2h.txt
```

### 2. PII Compliance Scan

```bash
# Scan logs for PII patterns (5 patterns)
grep -r -E '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b' logs/webhooks/canary/*.log \
  > evidence/canary/pii/email_grep_T+2h.txt || echo "No email matches"

grep -r -E '\b(username|user_name):\s*["\']?[A-Za-z0-9_-]+["\']?' logs/webhooks/canary/*.log \
  > evidence/canary/pii/username_grep_T+2h.txt || echo "No username matches"

grep -r -E '\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b' logs/webhooks/canary/*.log \
  > evidence/canary/pii/ip_grep_T+2h.txt || echo "No IP matches"

grep -r -E '\b(\+?1?[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b' logs/webhooks/canary/*.log \
  > evidence/canary/pii/phone_grep_T+2h.txt || echo "No phone matches"

grep -r -E '\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b' logs/webhooks/canary/*.log \
  > evidence/canary/pii/card_grep_T+2h.txt || echo "No card matches"

# Count total matches
PII_LEAKS=$(cat evidence/canary/pii/*_grep_T+2h.txt | grep -v "No .* matches" | wc -l)
echo "PII leaks found: $PII_LEAKS"
```

### 3. Generate T+2h Report

```bash
python scripts/generate_webhook_canary_report.py \
  --start-time "$(cat evidence/canary/start_time.txt)" \
  --metrics-file evidence/canary/summary_T+2h.json \
  --output reports/canary_T+2h.md \
  --operator "$(whoami)"
```

### 4. Decision: Continue or Rollback?

Same decision matrix as T+30m:
- **All green**: Continue to T+24h
- **Marginal (90-95%)**: Re-evaluate guardrails, continue with caution
- **Critical breach**: Immediate rollback

---

## T+24h Checkpoint

**Timeline**: T+23h 50m to T+24h 30m  
**Purpose**: Final promotion decision for 5% → 25%

### 1. Collect Full 24h Metrics

```bash
# Generate hourly snapshots (24 files)
for hour in {0..23}; do
  python scripts/calculate_canary_metrics.py \
    --window "${hour}h-$((hour+1))h" \
    --output "evidence/canary/hourly/T+${hour}h.json"
done

# Generate 6-hour bundles (4 files)
for bundle in {0..3}; do
  start_h=$((bundle * 6))
  end_h=$((start_h + 6))
  
  zip "evidence/canary/6h/bundle_${bundle}.zip" \
    evidence/canary/hourly/T+${start_h}h.json \
    evidence/canary/hourly/T+$((start_h+1))h.json \
    evidence/canary/hourly/T+$((start_h+2))h.json \
    evidence/canary/hourly/T+$((start_h+3))h.json \
    evidence/canary/hourly/T+$((start_h+4))h.json \
    evidence/canary/hourly/T+$((start_h+5))h.json
done

# Calculate 24h summary
python scripts/calculate_canary_metrics.py \
  --window 24h \
  --output evidence/canary/summary_T+24h.json
```

### 2. Grafana Dashboard Snapshots

```bash
# Export dashboard images
curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "http://grafana.prod:3000/render/d-solo/webhook-canary-observability/webhooks-canary?panelId=1&width=1200&height=600&from=now-24h&to=now" \
  > evidence/canary/grafana/T+24h_success_rate.png

curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "http://grafana.prod:3000/render/d-solo/webhook-canary-observability/webhooks-canary?panelId=2&width=1200&height=600&from=now-24h&to=now" \
  > evidence/canary/grafana/T+24h_p95_latency.png

curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "http://grafana.prod:3000/render/d-solo/webhook-canary-observability/webhooks-canary?panelId=10&width=1200&height=600&from=now-24h&to=now" \
  > evidence/canary/grafana/T+24h_retry_histogram.png

curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "http://grafana.prod:3000/render/d-solo/webhook-canary-observability/webhooks-canary?panelId=11&width=1200&height=600&from=now-24h&to=now" \
  > evidence/canary/grafana/T+24h_cb_sparkline.png
```

### 3. Alert History Export

```bash
# Export Prometheus alert manager history (24h)
curl -s http://alertmanager.prod:9093/api/v2/alerts \
  | jq '[.[] | select(.labels.job=="webhook-canary")]' \
  > evidence/canary/alerts/prometheus_alerts_T+24h.json

# Count alerts by severity
CRITICAL_ALERTS=$(jq '[.[] | select(.labels.severity=="critical")] | length' evidence/canary/alerts/prometheus_alerts_T+24h.json)
WARNING_ALERTS=$(jq '[.[] | select(.labels.severity=="warning")] | length' evidence/canary/alerts/prometheus_alerts_T+24h.json)

echo "Alerts fired (24h): Critical=$CRITICAL_ALERTS, Warning=$WARNING_ALERTS"
```

### 4. Generate T+24h Report (Full)

```bash
python scripts/generate_webhook_canary_report.py \
  --start-time "$(cat evidence/canary/start_time.txt)" \
  --metrics-file evidence/canary/summary_T+24h.json \
  --output reports/canary_T+24h.md \
  --template docs/canary/webhooks_canary_T+24h_template.md \
  --operator "$(whoami)"

# Review report (comprehensive, 1000+ lines)
less reports/canary_T+24h.md
```

### 5. Promotion Decision

**Decision Criteria** (ALL must be true):

```bash
SUCCESS_RATE=$(jq -r '.success_rate' evidence/canary/summary_T+24h.json)
P95_MS=$(jq -r '.p95_ms' evidence/canary/summary_T+24h.json)
CB_OPENS=$(jq -r '.cb_opens' evidence/canary/summary_T+24h.json)
PII_LEAKS=$(jq -r '.pii_leaks' evidence/canary/summary_T+24h.json)

# Check ALL gates
PROMOTE=true

if (( $(echo "$SUCCESS_RATE < 95" | bc -l) )); then
  echo "❌ Success rate <95%: $SUCCESS_RATE"
  PROMOTE=false
fi

if (( $(echo "$P95_MS >= 2000" | bc -l) )); then
  echo "❌ P95 latency ≥2s: ${P95_MS}ms"
  PROMOTE=false
fi

if (( $CB_OPENS >= 5 )); then
  echo "❌ CB opens ≥5: $CB_OPENS"
  PROMOTE=false
fi

if (( $PII_LEAKS > 0 )); then
  echo "❌ PII leaks detected: $PII_LEAKS"
  PROMOTE=false
fi

if (( $CRITICAL_ALERTS > 0 )); then
  echo "❌ Critical alerts fired: $CRITICAL_ALERTS"
  PROMOTE=false
fi

if [ "$PROMOTE" = true ]; then
  echo "✅ ALL GATES GREEN - PROMOTE TO 25%"
else
  echo "❌ PROMOTION BLOCKED - ROLLBACK TO 0%"
fi
```

**If PROMOTE=true**:
- Proceed to Phase 2 (25% traffic)
- Generate new webhook secret for 25% slice
- Update 20 additional instances (webhook-sender-006 to webhook-sender-025)
- Schedule T+2h and T+24h checkpoints for Phase 2
- Post in `#platform-ops`: "✅ Phase 1 (5%) COMPLETE - promoting to Phase 2 (25%)"

**If PROMOTE=false**:
- Execute rollback procedure (see below)
- Schedule post-mortem meeting
- Block future canaries until RCA complete
- Post in `#platform-ops`: "❌ Phase 1 (5%) FAILED - rolling back to 0%"

---

## Promotion Decision

### Promotion Rule

**IF** all 4 SLO gates remain green for the **full 24-hour window**:
- Success Rate ≥95%
- P95 Latency <2000ms
- Circuit Breaker Opens <5
- PII Leaks = 0

**THEN** recommend promotion:
- **5% → 25%**: After first 24h canary
- **25% → 100%**: After second 48h canary

### Phase 2 (25% Traffic) Setup

```bash
# Generate fresh secret for Phase 2
python -c "import secrets; import hashlib; secret = secrets.token_hex(32); print(f'Phase 2 Secret: {secret}'); print(f'SHA256: {hashlib.sha256(secret.encode()).hexdigest()}')" \
  > evidence/canary/phase2_secret.txt

# Update 20 additional instances (006-025)
for i in {6..25}; do
  instance=$(printf "webhook-sender-%03d" $i)
  kubectl set env deployment/$instance \
    NOTIFICATIONS_WEBHOOK_ENABLED=True \
    WEBHOOK_SECRET="$(grep 'Phase 2 Secret:' evidence/canary/phase2_secret.txt | awk '{print $4}')"
  
  kubectl rollout status deployment/$instance
done

# Adjust rate limiting for 25% traffic
# Token bucket: 50 QPS (25% of 200 QPS total)
kubectl set env deployment/webhook-sender-* \
  WEBHOOK_RATE_LIMIT_QPS=50 \
  WEBHOOK_RATE_LIMIT_BURST=100 \
  WEBHOOK_MAX_INFLIGHT=500

# Record Phase 2 start time
date -u +"%Y-%m-%dT%H:%M:%SZ" > evidence/canary/phase2_start_time.txt
echo "Phase 2 started at $(cat evidence/canary/phase2_start_time.txt)"

# Create Phase 2 evidence directories
mkdir -p evidence/canary/phase2/{hourly,6h,grafana,db,alerts,pii}
```

### Phase 3 (100% Traffic) Setup

**Prerequisites**:
- Phase 2 (25%) completed successfully (48h with all gates green)
- No rollbacks in Phase 1 or Phase 2
- Post-canary retrospective completed
- Runbook updated with lessons learned

```bash
# Generate final secret for 100% rollout
python -c "import secrets; import hashlib; secret = secrets.token_hex(32); print(f'Production Secret: {secret}'); print(f'SHA256: {hashlib.sha256(secret.encode()).hexdigest()}')" \
  > evidence/canary/production_secret.txt

# Enable all 100 instances
kubectl set env deployment/webhook-sender-* \
  NOTIFICATIONS_WEBHOOK_ENABLED=True \
  WEBHOOK_SECRET="$(grep 'Production Secret:' evidence/canary/production_secret.txt | awk '{print $3}')"

# Full production rate limiting
kubectl set env deployment/webhook-sender-* \
  WEBHOOK_RATE_LIMIT_QPS=200 \
  WEBHOOK_RATE_LIMIT_BURST=400 \
  WEBHOOK_MAX_INFLIGHT=2000

# Move to daily monitoring (no more canary reports)
# Set up daily health check dashboard
```

---

## Rollback Procedure

**Trigger Conditions** (ANY of these):
- Success rate <90% for >5 minutes
- P95 latency >5s for >10 minutes
- Circuit breaker opens >10 in any 24h window
- Any PII leak detected
- Manual escalation from on-call engineer

### Immediate Rollback (15-minute procedure)

```bash
# Step 1: Disable feature flag (0-2 minutes)
echo "$(date -u) - ROLLBACK INITIATED" >> evidence/canary/rollback_log.txt

for i in {1..25}; do
  instance=$(printf "webhook-sender-%03d" $i)
  kubectl set env deployment/$instance NOTIFICATIONS_WEBHOOK_ENABLED=False
done

# Step 2: Verify rollout (2-5 minutes)
for i in {1..25}; do
  instance=$(printf "webhook-sender-%03d" $i)
  kubectl rollout status deployment/$instance --timeout=60s
done

# Step 3: Verify webhook traffic stops (5-10 minutes)
# Wait 5 minutes for in-flight requests to drain
sleep 300

# Check webhook delivery metrics (should be 0 QPS)
curl -s http://prometheus.prod:9090/api/v1/query \
  --data-urlencode 'query=rate(webhook_delivery_total[1m])' \
  | jq '.data.result[0].value[1]'
# Expected: "0" or very close to 0

# Step 4: Generate rollback report (10-15 minutes)
python scripts/generate_rollback_report.py \
  --start-time "$(cat evidence/canary/start_time.txt)" \
  --rollback-time "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  --output reports/canary_ROLLBACK.md

# Step 5: Communication
echo "$(date -u) - ROLLBACK COMPLETE" >> evidence/canary/rollback_log.txt
```

### Post-Rollback Actions

1. **Immediate** (within 1 hour):
   - Post in `#platform-ops`: "❌ Webhook canary rolled back - [link to rollback report]"
   - Update status page: "Webhook delivery canary halted"
   - Notify stakeholders (PM, Tech Lead, On-call Manager)

2. **Within 4 hours**:
   - Generate post-mortem draft using template: `docs/canary/postmortem_template.md`
   - Assign RCA owner
   - Schedule post-mortem meeting (within 24h)

3. **Within 24 hours**:
   - Complete RCA with:
     - Timeline of events
     - Root cause analysis
     - Corrective actions (with owners and due dates)
     - Prevention measures
   - Update runbook with lessons learned
   - Block future canaries until corrective actions complete

4. **Before next canary**:
   - Verify all corrective actions completed
   - Add regression tests for failure mode
   - Update guardrails if needed
   - Get sign-off from Tech Lead

---

## Guardrails Application

### When to Apply

- **Proactive** (T-30min): Always apply before canary starts
- **Reactive** (T+30m): If success rate 90-95%, apply immediately

### Receiver DB Pool Hardening

```bash
# Update PgBouncer config (pgbouncer.ini)
cat <<EOF > /etc/pgbouncer/pgbouncer.ini
[databases]
webhooks = host=postgres.prod port=5432 dbname=webhooks

[pgbouncer]
pool_mode = transaction
default_pool_size = 25
reserve_pool_size = 10
min_pool_size = 5
max_client_conn = 200
max_db_connections = 50
server_idle_timeout = 600
server_lifetime = 3600
server_connect_timeout = 15
query_wait_timeout = 120
EOF

# Reload PgBouncer config
sudo systemctl reload pgbouncer

# Set statement timeout in PostgreSQL
PGPASSWORD=$DB_PASSWORD psql -h postgres.prod -U postgres -d webhooks \
  -c "ALTER DATABASE webhooks SET statement_timeout = '5s';"

# Restart Gunicorn workers with connection limits
# (In Kubernetes deployment YAML)
# env:
#   - name: GUNICORN_WORKERS
#     value: "2"
#   - name: GUNICORN_MAX_REQUESTS
#     value: "1000"
#   - name: GUNICORN_MAX_REQUESTS_JITTER
#     value: "100"
```

### Sender Rate Smoothing

```bash
# Update sender config (for 5% traffic)
kubectl set env deployment/webhook-sender-* \
  WEBHOOK_RATE_LIMIT_QPS=10 \
  WEBHOOK_RATE_LIMIT_BURST=20 \
  WEBHOOK_MAX_INFLIGHT=100 \
  WEBHOOK_BACKPRESSURE_SLEEP_MS=100

# Verify rate limiting active
kubectl logs -l app=webhook-sender --tail=100 | grep "rate_limited"
# Expected: Should see log lines like "rate_limited=true count=0"
```

### Alert Rule Activation

```bash
# Import alert rules
curl -X POST http://prometheus.prod:9090/api/v1/rules \
  -H "Content-Type: application/yaml" \
  --data-binary @grafana/webhooks_canary_alerts.json

# Verify alerts active
curl -s http://prometheus.prod:9090/api/v1/rules \
  | jq '.data.groups[] | select(.name=="webhook_canary") | .rules[] | .name'
# Expected: 12 rule names
```

---

## Emergency Contacts

| Role | Name | Slack | Phone | Escalation Level |
|------|------|-------|-------|-----------------|
| On-call Engineer | Rotation | @oncall-platform | +1-555-0100 | L1 |
| Tech Lead | Platform Team | @platform-lead | +1-555-0101 | L2 |
| Engineering Manager | Platform Mgr | @platform-manager | +1-555-0102 | L3 |
| VP Engineering | VP Eng | @vp-engineering | +1-555-0103 | L4 |

**Escalation Path**:
1. L1 (On-call): Handle routine checkpoints, apply guardrails
2. L2 (Tech Lead): Rollback decision, RCA oversight
3. L3 (Manager): Stakeholder communication, resource allocation
4. L4 (VP): Executive escalation, external communication

**Slack Channels**:
- `#platform-ops`: Operational updates
- `#incidents`: Active incidents (rollback = SEV2)
- `#platform-team`: Team communication

**PagerDuty**:
- Service: `webhook-canary`
- Escalation Policy: `Platform On-call → Tech Lead → Manager`

---

**Runbook Version**: 1.0.0  
**Last Reviewed**: 2025-11-13  
**Next Review**: 2025-12-13 (monthly)  
**Approver**: Platform Tech Lead
