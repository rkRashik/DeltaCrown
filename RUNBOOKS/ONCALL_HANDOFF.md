# On-Call Handoff — DeltaCrown Operations Runbook

**Last Updated**: 2025-11-13  
**Owner**: Platform SRE Team  
**On-Call Rotation**: Weekly (Monday 00:00 UTC)

---

## First-Hour Playbook

**When an alert fires, follow this checklist within 60 minutes**:

### 1. **Acknowledge Alert** (0-2 min)

- [ ] Acknowledge in PagerDuty/Slack (#incidents channel)
- [ ] Claim incident: "I'm investigating [alert name], ETA 15 min"
- [ ] Check alert metadata:
  - **Service**: deltacrown-api, deltacrown-worker, etc.
  - **Environment**: production, staging
  - **Severity**: critical, high, warning
  - **First seen**: timestamp (is this recurring?)

### 2. **Assess Impact** (2-5 min)

- [ ] Check Grafana dashboards:
  - **SLO Burn Rate**: `grafana/slo_burn_alerts.json` (fast burn 2%/1h, slow burn 5%/24h)
  - **Moderation Enforcement**: `grafana/moderation_enforcement_dashboard.json` (deny %, latency, cache hit rate)
- [ ] Check synthetics: `synthetics/uptime_checks.yml` status (are external checks failing?)
- [ ] Check error rate: Prometheus `http_requests_total{code=~"5.."}` (5xx spike?)
- [ ] Check traffic: Prometheus `http_requests_total` (traffic spike or drop?)

**Impact Categories**:
- **Critical**: >5% error rate, >50% traffic drop, payment processing down
- **High**: 2-5% error rate, latency p95 >400ms, cache down
- **Warning**: 1-2% error rate, latency p95 200-400ms

### 3. **Check Recent Changes** (5-10 min)

- [ ] Review recent deployments: `git log --oneline -10` (any deploys in last 2 hours?)
- [ ] Check feature flags: Are any flags recently toggled?
  - `MODERATION_OBSERVABILITY_ENABLED` (should be `false` in production by default)
  - `MODERATION_CACHE_ENABLED` (should be `true`)
  - `PURCHASE_ENFORCEMENT_ENABLED` (should be `false` until Phase 11)
- [ ] Check CI status: Any failed jobs in GitHub Actions?
- [ ] Check infrastructure: AWS Console → RDS, Redis, S3 (any service degradation?)

### 4. **Mitigate Immediately** (10-20 min)

**Quick Wins** (try in order):

1. **Rollback deployment** (if deploy within last 2 hours):
   ```bash
   # Rollback to previous git tag
   git checkout tags/v1.0.0-stable
   # Redeploy (infrastructure-specific commands)
   kubectl rollout undo deployment/deltacrown-api
   ```

2. **Toggle feature flags OFF** (if flag change suspected):
   ```bash
   # Set all flags to safe defaults
   export MODERATION_OBSERVABILITY_ENABLED=false
   export MODERATION_CACHE_ENABLED=false  # Only if cache causing issues
   kubectl rollout restart deployment/deltacrown-api
   ```

3. **Scale up resources** (if traffic spike):
   ```bash
   # Horizontal scaling
   kubectl scale deployment/deltacrown-api --replicas=10
   ```

4. **Restart unhealthy pods** (if specific pods crashing):
   ```bash
   # Delete unhealthy pods (Kubernetes will recreate)
   kubectl delete pod -l app=deltacrown-api --field-selector=status.phase=Failed
   ```

### 5. **Monitor Recovery** (20-30 min)

- [ ] Verify error rate dropping: Prometheus `rate(http_requests_total{code=~"5.."}[5m])`
- [ ] Verify latency improving: Prometheus `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- [ ] Run smoke tests: `pytest -q -m smoke tests/smoke/`
- [ ] Check synthetics: All 4 checks GREEN? (`/health`, `/api/transactions`, `/api/shop/items`, `/api/moderation/enforcement/ping`)

**If still not resolved after 30 min**, escalate to secondary on-call.

### 6. **Communicate Status** (30-60 min)

- [ ] Post update in Slack #incidents:
  ```
  🔥 INCIDENT UPDATE: [alert name]
  Status: MITIGATING
  Impact: [users affected, services down]
  Root cause (suspected): [deploy, flag toggle, infra]
  ETA resolution: [time]
  Next update: [time]
  ```

- [ ] Update status page (if customer-facing): https://status.deltacrown.example.com
- [ ] Notify stakeholders: Product team, support team (if critical)

---

## MTTA / MTTR Targets

**Mean Time To Acknowledge** (MTTA): Time from alert firing to engineer acknowledgment.

| **Severity** | **MTTA Target** | **Breach Consequence** |
|--------------|-----------------|------------------------|
| **Critical** | 5 minutes | Page secondary on-call |
| **High** | 15 minutes | Escalate to team lead |
| **Warning** | 30 minutes | Log in post-mortem, improve runbooks |

**Mean Time To Resolve** (MTTR): Time from alert firing to incident resolved (error rate <1%, latency normal).

| **Severity** | **MTTR Target** | **Breach Consequence** |
|--------------|-----------------|------------------------|
| **Critical** | 15 minutes | Executive notification, post-mortem required |
| **High** | 30 minutes | Post-mortem required |
| **Warning** | 60 minutes | Optional post-mortem |

**Tracking**: Log incidents in spreadsheet/dashboard:
- Incident ID, timestamp, severity, MTTA, MTTR, root cause, action items

---

## Escalation Chain

**Primary On-Call** → **Secondary On-Call** → **Team Lead** → **Engineering Manager**

| **Role** | **Contact** | **Escalate If** |
|----------|-------------|-----------------|
| **Primary On-Call** | Slack @on-call-primary, PagerDuty | - |
| **Secondary On-Call** | Slack @on-call-secondary, PagerDuty | Not acknowledged in 5 min (critical) OR not resolved in 30 min |
| **Team Lead** | Slack @team-lead-sre, Phone: +1-XXX-XXX-XXXX | Not resolved in 60 min OR cross-team coordination needed |
| **Engineering Manager** | Slack @eng-manager, Email: manager@deltacrown.com | Customer-facing outage >2 hours OR data breach suspected |

**Paging Procedure**:
1. PagerDuty automatically pages primary on-call
2. If no acknowledgment in 5 min, auto-escalate to secondary
3. Manual page team lead: `@pagerduty escalate [incident-id]`

---

## Common Issues & Step-by-Step Fixes

### Issue 1: DB Pool Exhaustion

**Symptoms**:
- `OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections`
- Latency spike (p95 >2s)
- 5xx errors on write endpoints

**Diagnosis** (5 min):
```bash
# Check active connections
psql -h $DB_HOST -U $DB_USER -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"
# Expected: <80 (max pool size = 100)

# Check long-running queries
psql -h $DB_HOST -U $DB_USER -c "SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 10;"
```

**Fix** (10 min):
```bash
# Step 1: Kill long-running queries (>30s)
psql -h $DB_HOST -U $DB_USER -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '30 seconds';"

# Step 2: Restart application pods (release connections)
kubectl rollout restart deployment/deltacrown-api

# Step 3: Increase pool size temporarily (if needed)
export DB_POOL_SIZE=150  # Default: 100
kubectl rollout restart deployment/deltacrown-api
```

**Prevention**:
- Add query timeout: `SET statement_timeout = '10s';` in Django settings
- Add connection pool monitoring: Alert if active connections >80

---

### Issue 2: Redis Latency Spike

**Symptoms**:
- Cache operations slow (p95 >100ms, normally <10ms)
- Moderation gate decisions slow (p95 >200ms)
- Metrics: `moderation_cache_hits_total` / `moderation_cache_misses_total` ratio <0.7

**Diagnosis** (5 min):
```bash
# Check Redis latency
redis-cli -h $REDIS_HOST --latency
# Expected: <5ms avg

# Check Redis memory usage
redis-cli -h $REDIS_HOST INFO memory
# Check: used_memory_human, maxmemory_policy (should be allkeys-lru)

# Check eviction rate
redis-cli -h $REDIS_HOST INFO stats | grep evicted_keys
# High eviction rate (>1000/min) indicates memory pressure
```

**Fix** (10 min):
```bash
# Step 1: Check for slow queries
redis-cli -h $REDIS_HOST SLOWLOG GET 10
# If slow commands found, optimize or add indexes

# Step 2: Clear cache if corrupted
redis-cli -h $REDIS_HOST FLUSHALL  # ⚠️ CAUTION: clears all cache

# Step 3: Scale up Redis instance
# (Infrastructure-specific: AWS ElastiCache, increase node size)

# Step 4: Disable cache temporarily (if critical)
export MODERATION_CACHE_ENABLED=false
kubectl rollout restart deployment/deltacrown-api
```

**Prevention**:
- Increase Redis memory: Scale to r6g.large (13 GB)
- Add cache monitoring: Alert if eviction rate >1000/min

---

### Issue 3: S3 Partial Outage

**Symptoms**:
- `ClientError: An error occurred (503) when calling the PutObject operation: Service Unavailable`
- File uploads failing (user avatars, team logos)
- Error rate spike on `/api/upload` endpoint

**Diagnosis** (5 min):
```bash
# Check S3 service status
aws s3api head-bucket --bucket deltacrown-media-prod
# If returns 503, S3 is degraded

# Check AWS Service Health Dashboard
# https://health.aws.amazon.com/health/status
```

**Fix** (10 min):
```bash
# Step 1: Enable local fallback storage
export S3_FALLBACK_ENABLED=true
export S3_FALLBACK_PATH=/mnt/efs/fallback_storage
kubectl rollout restart deployment/deltacrown-api

# Step 2: Notify users (if prolonged)
# Post in #support-internal: "File uploads temporarily unavailable, investigating"

# Step 3: Retry failed uploads after S3 recovers
# Run batch job to sync local fallback → S3
python manage.py sync_fallback_to_s3 --dry-run
python manage.py sync_fallback_to_s3  # Execute
```

**Prevention**:
- Implement retry logic: Exponential backoff (1s, 2s, 4s, 8s)
- Add S3 health check: Smoke test uploads every 1 min

---

## Dashboard Links

**Grafana Dashboards**:
- **SLO Burn Rate Alerts**: https://grafana.deltacrown.internal/d/slo_burn_alerts_deltacrown
- **Moderation Enforcement**: https://grafana.deltacrown.internal/d/moderation_enforcement_deltacrown
- **Infrastructure**: https://grafana.deltacrown.internal/d/infra_overview

**Logs**:
- **Centralized Logs (CloudWatch / ELK)**: https://logs.deltacrown.internal
- **Application Logs**: `kubectl logs -f deployment/deltacrown-api --tail=100`

**CI/CD**:
- **GitHub Actions**: https://github.com/rkRashik/DeltaCrown/actions
- **Synthetics CI**: https://github.com/rkRashik/DeltaCrown/actions/workflows/synthetics-lint.yml

**Monitoring**:
- **Prometheus**: https://prometheus.deltacrown.internal
- **Synthetics Checks**: `synthetics/uptime_checks.yml` (check status in monitoring service)

---

## Alert Policies

**PagerDuty Integration**:
- **Critical alerts** (fast burn >2%/1h, 5xx rate >5%): Page immediately
- **High alerts** (slow burn >5%/24h, latency p95 >400ms): Page if not acknowledged in 15 min
- **Warning alerts** (cache hit rate <70%, eviction rate high): Slack only, no page

**Slack Channels**:
- **#incidents**: Active incidents, real-time updates
- **#infra-alerts**: Non-critical alerts (cost thresholds, storage warnings)
- **#on-call**: On-call rotation schedule, handoff notes

---

## Rollback Commands (Quick Reference)

**Git Rollback**:
```bash
# Check previous stable tag
git tag --sort=-creatordate | head -5

# Rollback to specific tag
git checkout tags/v1.0.0-stable

# Redeploy
# (Infrastructure-specific commands)
```

**Feature Flag Rollback**:
```bash
# Set all flags to safe defaults
export MODERATION_OBSERVABILITY_ENABLED=false
export MODERATION_CACHE_ENABLED=true  # Keep cache enabled unless causing issues
export PURCHASE_ENFORCEMENT_ENABLED=false

# Restart pods
kubectl rollout restart deployment/deltacrown-api
kubectl rollout status deployment/deltacrown-api  # Wait for completion
```

**Database Rollback** (if migration caused issue):
```bash
# Check current migration
python manage.py showmigrations

# Rollback to previous migration
python manage.py migrate <app_name> <previous_migration_number>
```

**Cache Clear** (if corrupted data):
```bash
# Clear Redis cache
redis-cli -h $REDIS_HOST FLUSHALL

# Or clear specific keys
redis-cli -h $REDIS_HOST --scan --pattern "moderation_cache:*" | xargs redis-cli -h $REDIS_HOST DEL
```

---

## Post-Incident Actions

**Within 24 hours**:
- [ ] Schedule post-mortem meeting (30-60 min)
- [ ] Document incident in shared drive:
  - Timeline (alert fired → acknowledged → mitigated → resolved)
  - Root cause (e.g., "DB pool exhaustion due to long-running query")
  - Impact (e.g., "5% error rate for 15 minutes, ~500 users affected")
  - Action items (e.g., "Add query timeout, increase pool size")
- [ ] Update runbooks if new issue discovered
- [ ] Add regression test to prevent recurrence

**Post-Mortem Template**:
```markdown
# Post-Mortem: [Incident Title]

**Date**: 2025-11-13  
**Duration**: 15 minutes (10:00 - 10:15 UTC)  
**Severity**: Critical  
**Impact**: 5% error rate, ~500 users affected  

## Timeline
- 10:00: Alert fired (SLO fast burn >2%)
- 10:02: Acknowledged by @on-call-primary
- 10:05: Root cause identified (DB pool exhaustion)
- 10:10: Mitigation applied (killed long-running queries, restarted pods)
- 10:15: Incident resolved (error rate <1%)

## Root Cause
Long-running query (`SELECT * FROM tournaments_registration WHERE created_at > '2024-01-01'`) held DB connection for 45 seconds, exhausting pool.

## Action Items
1. Add query timeout: `SET statement_timeout = '10s'` in Django settings (Owner: @sre-team, Due: 2025-11-15)
2. Add DB connection pool monitoring: Alert if active connections >80 (Owner: @sre-team, Due: 2025-11-16)
3. Optimize query: Add index on `created_at` (Owner: @backend-team, Due: 2025-11-17)

## Lessons Learned
- Current DB pool size (100) is insufficient for peak traffic
- Query timeout not enforced at application level
- Need proactive monitoring for long-running queries
```

---

## On-Call Handoff Checklist

**Outgoing On-Call** (end of rotation):
- [ ] Document any ongoing incidents in Slack #on-call
- [ ] Share runbook updates (if any)
- [ ] Highlight any system quirks discovered during rotation
- [ ] Transfer PagerDuty primary escalation to incoming on-call

**Incoming On-Call** (start of rotation):
- [ ] Verify PagerDuty access (can receive pages)
- [ ] Verify Slack notifications enabled (#incidents, #on-call)
- [ ] Review recent incidents (last 7 days)
- [ ] Test access to dashboards, logs, Kubernetes

---

## References

- **RELEASE_CHECKLIST_V1.md**: Deploy checklist, rollback procedures
- **COST_GUARDRAILS.md**: Query cost checks, performance budgets
- **MODULE_8.3_OBSERVABILITY_NOTES.md**: Cache metrics, PII guards
- **PHASE_9_SMOKE_AND_ALERTING.md**: Smoke tests, alert thresholds
- **tests/ops/test_dr_chaos_minidrill.py**: Chaos drill scenarios

---

**Last Updated**: 2025-11-13  
**Next Review**: After first critical incident (within 48 hours)
