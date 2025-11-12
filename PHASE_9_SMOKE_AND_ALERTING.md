# Phase 9: Smoke Tests & Alerting

## Overview

This phase implements end-to-end smoke tests and synthetic monitoring for DeltaCrown's critical user paths. **All enforcement flags default to OFF**, ensuring zero behavior change until explicitly enabled.

---

## Smoke Tests Coverage

### Test File
`tests/smoke/test_end_to_end_paths.py` (12 tests)

### Tests Included

| Test Name | Purpose | Critical Path |
|-----------|---------|---------------|
| `test_health_has_version_key_and_status_ok` | Health endpoint contract | Infrastructure |
| `test_auth_handshake_minimal_claims_no_pii` | JWT/session auth without PII | Auth |
| `test_wallet_debit_credit_round_trip_balance_consistent` | Economy transaction consistency | Economy |
| `test_transaction_csv_export_bom_once` | CSV export UTF-8 BOM correctness | Reporting |
| `test_websocket_connect_disconnect_lifecycle_succeeds` | WebSocket infrastructure | Real-time |
| `test_purchase_happy_path_flags_off` | Purchase succeeds when flags OFF | E-commerce |
| `test_purchase_denied_when_flags_on_and_banned` | Purchase blocked when flags ON + banned | Enforcement |
| `test_revenue_summary_returns_ints_no_decimal` | JSON serialization correctness | Admin |
| `test_error_envelope_404_keys_stable` | Error contract stability | API |
| `test_perf_harness_quick_mode_smoke_outputs_samples` | Performance testing infra | Testing |
| `test_admin_read_only_views_expose_no_secrets` | Sensitive data masking | Security |
| `test_openapi_served_contains_no_emails_or_usernames` | API schema PII safety | Documentation |

### Running Smoke Tests

```bash
# Run all smoke tests
pytest -v -m smoke tests/smoke/

# Or use Make target
make smoke

# Run specific test
pytest -v tests/smoke/test_end_to_end_paths.py::test_health_has_version_key_and_status_ok
```

**Expected Runtime**: ~30-60 seconds (all 12 tests)

---

## Synthetic Monitoring

### Configuration File
`synthetics/uptime_checks.yml`

### Monitored Endpoints (4 checks, 1-min cadence)

| Endpoint | Method | Success Criteria | Criticality |
|----------|--------|------------------|-------------|
| `/health` | GET | 200, <800ms, contains "ok" | High |
| `/api/transactions?page=1&page_size=10` | GET | 200/401, <800ms, JSON response | Medium |
| `/api/shop/items` | GET | 200/401, <800ms, JSON response | Medium |
| `/api/moderation/enforcement/ping` | GET | 200, <800ms, `{"allow": true}` | Low |

### Deployment

**No secrets required** for basic monitoring (uses public/unauthenticated endpoints).

#### Local Testing
```bash
# Validate YAML syntax
yamllint synthetics/uptime_checks.yml

# Or use CI lint job
make synthetics-lint
```

#### Production Deployment
```bash
# Datadog Synthetics (example)
datadog-ci synthetics upload synthetics/uptime_checks.yml

# New Relic (example)
newrelic synthetics create --config synthetics/uptime_checks.yml

# Custom monitoring (parse YAML and schedule HTTP checks)
python scripts/deploy_synthetics.py --env production
```

---

## Alert Thresholds

### Consecutive Failures (Immediate)

**Trigger**: 3 consecutive failures within 3 minutes  
**Severity**: WARNING  
**Action**:
1. Check application logs for errors
2. Verify infrastructure (load balancer, DNS)
3. Escalate to on-call if not resolved in 10 minutes

**Example**:
```
Alert: health_endpoint failed 3 times
Time: 2025-11-13 14:03:00 - 14:05:00
Status codes: 503, 503, 503
```

---

### Weekly Availability (Degraded Service)

**Trigger**: Availability < 98.5% over 7 days  
**Severity**: CRITICAL  
**Action**:
1. Review incident log (count and duration of outages)
2. Identify root cause (deployment, infrastructure, code)
3. Implement fix and validate with smoke tests
4. Post-mortem within 48 hours

**Calculation**:
```
Availability = (Total Uptime Seconds) / (Total Monitored Seconds)

Example: 
- 7 days = 604,800 seconds
- Downtime: 10,000 seconds (2.78 hours)
- Availability = 594,800 / 604,800 = 98.35% ❌ (below 98.5%)
```

---

### Latency Degradation

**Trigger**: p95 response time > 800ms for 10 consecutive minutes  
**Severity**: WARNING  
**Action**:
1. Check Grafana "Gate Latency" panel (from observability dashboard)
2. Verify cache hit rate (should be >70%)
3. Check database slow query log
4. Consider scaling horizontally if load-related

---

## On-Call Escalation

### Primary Escalation (Immediate)
1. **Slack alert** → `#deltacrown-alerts` channel
2. **PagerDuty** → On-call engineer (if enabled)
3. **Expected response time**: 15 minutes

### Secondary Escalation (If unresolved after 1 hour)
1. **Engineering lead** contacted
2. **Incident commander** assigned
3. **War room** opened in Slack (`#incident-YYYYMMDD-HHMM`)

### Escalation Matrix

| Time Since Alert | Action | Responsible |
|------------------|--------|-------------|
| 0-15 min | Acknowledge alert, begin investigation | On-call engineer |
| 15-30 min | Initial diagnosis, apply known fixes | On-call engineer |
| 30-60 min | Escalate to lead if not resolved | On-call + Lead |
| 60+ min | Incident commander, war room, customer comms | IC + Team |

---

## MTTR Targets (Mean Time To Recovery)

| Severity | Target MTTR | Max Acceptable |
|----------|-------------|----------------|
| Critical (service down) | 15 minutes | 30 minutes |
| High (degraded performance) | 30 minutes | 1 hour |
| Medium (isolated feature) | 1 hour | 4 hours |
| Low (cosmetic/non-blocking) | 4 hours | 24 hours |

---

## Flags OFF Confirmation

**Default State** (no behavior change):
- ✅ `MODERATION_OBSERVABILITY_ENABLED=false` → No metrics overhead
- ✅ `PURCHASE_ENFORCEMENT_ENABLED=false` (Phase 10, not yet implemented) → No purchase blocking
- ✅ `MODERATION_CACHE_ENABLED=true` → Cache active (transparent, improves performance)

**To Enable Enforcement** (Phase 10):
1. Set `PURCHASE_ENFORCEMENT_ENABLED=true` in environment
2. Restart application
3. Run smoke test: `test_purchase_denied_when_flags_on_and_banned` to verify blocking works
4. Monitor deny rate in Grafana (should start >0% after enabling)

---

## Rollback Steps

### Rollback Smoke Test Changes (if issues found)
```bash
# Revert smoke tests commit
git revert <COMMIT_SHA>
git push origin master

# Re-run core test suite
pytest -v tests/
```

### Rollback Synthetics (if false positives)
```bash
# Disable alerting in uptime_checks.yml
sed -i 's/enabled: true/enabled: false/g' synthetics/uptime_checks.yml
git commit -am "Disable synthetic alerts temporarily"
git push origin master
```

### Emergency Rollback (Enforcement Flags)
```bash
# SSH to production server
ssh prod-server

# Disable enforcement
export PURCHASE_ENFORCEMENT_ENABLED=false
sudo systemctl restart deltacrown

# Verify flag state
curl http://localhost:8000/api/moderation/enforcement/ping
# Should return: {"allow": true}
```

---

## Related Documentation

- [MODULE_8.3_OBSERVABILITY_NOTES.md](../MODULE_8.3_OBSERVABILITY_NOTES.md) - Metrics and dashboard
- [config/flags.md](../config/flags.md) - All feature flags and defaults
- [docs/ops/ALERT_MATRIX.md](ops/ALERT_MATRIX.md) - Symptom → cause → action mapping
- [RUNBOOKS/ONCALL_HANDOFF.md](../RUNBOOKS/ONCALL_HANDOFF.md) - On-call procedures (Phase 10)

---

## CI Integration

### Smoke Tests in CI
File: `.github/workflows/perf-smoke.yml` (updated)

```yaml
jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: pytest -v -m smoke tests/smoke/  # Run smoke tests
```

### Synthetics Lint in CI
File: `.github/workflows/synthetics-lint.yml` (new)

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install yamllint
      - run: yamllint synthetics/uptime_checks.yml
      - run: python scripts/validate_synthetics.py  # Custom validation
```

---

## Verification Commands

```bash
# Run all smoke tests
make smoke

# Check synthetics YAML validity
yamllint synthetics/uptime_checks.yml

# Verify no PII in test code
grep -rE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' tests/smoke/ | grep -v example.com

# Check flags are OFF by default
grep -r "MODERATION_OBSERVABILITY_ENABLED" deltacrown/settings.py
# Should show: default value = false or not set

# Run single smoke test
pytest -v tests/smoke/test_end_to_end_paths.py::test_health_has_version_key_and_status_ok
```

---

## Post-Deployment Checklist

- [ ] Smoke tests pass in CI (all 12 green)
- [ ] Synthetics YAML validated (yamllint passes)
- [ ] Flags confirmed OFF in production environment
- [ ] Grafana dashboard imported (from MODULE_8.3)
- [ ] Alert channels tested (send test alert to Slack)
- [ ] On-call engineer briefed on new alerts
- [ ] MTTR targets communicated to team
- [ ] Incident response runbook accessible
