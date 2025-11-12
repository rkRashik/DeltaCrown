# Release Checklist V1

**Version**: 1.0  
**Last Updated**: 2025-11-13  
**Target Release**: Phase 10 — Cutover & Ops Readiness

---

## Feature Flag Matrix

| **Flag** | **Default** | **Who Toggles** | **Where** | **Rollback** |
|----------|-------------|-----------------|-----------|--------------|
| `MODERATION_OBSERVABILITY_ENABLED` | `false` | Platform SRE | Environment variable | Set to `false` |
| `MODERATION_CACHE_ENABLED` | `true` | Platform SRE | Environment variable | Set to `false` |
| `MODERATION_CACHE_TTL_SECONDS` | `60` | Platform SRE | Environment variable | Increase to `120` or disable cache |
| `MODERATION_SAMPLING_RATE` | `0.10` (10%) | Platform SRE | Environment variable | Set to `0.01` (1%) or `0` |
| `PURCHASE_ENFORCEMENT_ENABLED` | `false` | Product + SRE | Environment variable | Set to `false` |

**Toggle Process**:
1. Update environment variable in deployment system (Kubernetes ConfigMap, AWS Parameter Store, etc.)
2. Rolling restart application pods/instances (no downtime)
3. Monitor Grafana dashboards for 5 minutes post-toggle
4. If degradation detected, immediately toggle back and investigate

---

## Go/No-Go Gate Checklist

**Pre-Release Gates** (must be GREEN before deploy):

- [ ] **All tests pass**: `pytest -q` (exit code 0)
  - [ ] Observability tests: `pytest -q -m observability` (12 tests)
  - [ ] Smoke tests: `pytest -q -m smoke` (12 tests)
  - [ ] Ops drills: `pytest -q -m ops` (4 tests)
- [ ] **Coverage thresholds**:
  - [ ] Observability: ≥85% (`pytest --cov=apps/observability tests/observability/`)
  - [ ] Smoke: ≥80% (`pytest --cov=tests/smoke tests/smoke/`)
  - [ ] Ops: ≥70% (`pytest --cov=tests/ops tests/ops/`)
- [ ] **CI guards pass**:
  - [ ] `synthetics-lint.yml`: YAML validation, schema check, secret detection
  - [ ] `pii-scan.yml`: No PII leaked (emails, IPs, usernames)
  - [ ] `pre-commit`: gitleaks, detect-private-key, check-yaml
- [ ] **Secret scans**:
  - [ ] No hardcoded passwords in denylist patterns (`ci/policy/denylist.yml`)
  - [ ] Grafana dashboards use `${DS_PROMETHEUS}` (no hardcoded datasource UIDs)
  - [ ] Synthetics YAML has no hardcoded credentials (uses `${BASE_URL}`, `${ENVIRONMENT}`)
- [ ] **Performance budgets**:
  - [ ] Observability metrics overhead: <5ms per request (when enabled)
  - [ ] Cache hit rate: ≥70% over 50 requests
  - [ ] p95 latency: <200ms for gate decisions
  - [ ] Smoke test suite: <2 minutes total runtime

**On-Call Readiness**:

- [ ] **Runbooks available**: `RUNBOOKS/ONCALL_HANDOFF.md` reviewed by on-call team
- [ ] **Dashboards imported**: Grafana dashboards imported and tested (moderation_enforcement_dashboard.json, slo_burn_alerts.json)
- [ ] **Alerting configured**: SLO burn alerts (fast burn 2%/1h, slow burn 5%/24h)
- [ ] **Escalation chain**: PagerDuty/Slack webhooks configured (see alerting section in synthetics/uptime_checks.yml)
- [ ] **MTTR targets documented**: Critical=15min, High=30min, Medium=60min

---

## Dry-Run Steps

**1. Pre-Production Staging Validation** (1 hour):

```bash
# 1a. Deploy to staging environment
# (Deployment commands specific to your infrastructure)

# 1b. Run smoke tests against staging
BASE_URL=https://staging.deltacrown.example.com pytest -v -m smoke tests/smoke/

# 1c. Verify observability metrics (flags ON in staging only)
export MODERATION_OBSERVABILITY_ENABLED=true
export MODERATION_CACHE_ENABLED=true
pytest -v -m observability tests/observability/

# 1d. Check Grafana dashboards (staging datasource)
# Manual: Import grafana/moderation_enforcement_dashboard.json to staging Grafana
# Verify panels show data (decisions/min, cache hit rate, latency)

# 1e. Run ops drills (test-only, no prod impact)
pytest -v -m ops tests/ops/
```

**2. Production Deploy - Staged Rollout** (2 hours):

```bash
# 2a. Deploy to 10% of production pods (canary)
# Monitor Grafana dashboards for 15 minutes
# - Check error rates, latency p95, cache hit rate
# - Alert on regression >15% from baseline

# 2b. If canary GREEN, deploy to 50% of production pods
# Monitor for 15 minutes

# 2c. If 50% GREEN, deploy to 100% of production pods
# Monitor for 30 minutes

# 2d. Run production smoke tests (read-only, no writes)
BASE_URL=https://deltacrown.example.com pytest -v -m smoke tests/smoke/ -k "health or openapi"

# 2e. Verify synthetics checks are GREEN
# Check .github/workflows/perf-smoke.yml CI run
# Confirm artifacts/smoke/smoke_run_summary.json uploaded
```

**3. Post-Deploy Validation** (30 minutes):

```bash
# 3a. Verify feature flags are OFF (default state)
curl https://deltacrown.example.com/health | jq '.feature_flags.moderation_observability_enabled'
# Expected: false

# 3b. Check SLO burn alerts in Grafana
# Manual: Verify grafana/slo_burn_alerts.json panels show no active burns

# 3c. Run PII scan (local validation)
python -m scripts.pii_scan --paths apps/ tests/ grafana/ synthetics/
# Expected: No PII found

# 3d. Confirm artifact uploads in CI
# Check GitHub Actions > perf-smoke.yml > Artifacts
# Verify smoke_run_summary.json available for download (14-day retention)
```

---

## Staged Rollouts

| **Stage** | **Traffic %** | **Duration** | **Abort Criteria** |
|-----------|---------------|--------------|---------------------|
| **Canary** | 10% | 15 min | Error rate +5%, p95 latency +15%, any 5xx spike |
| **Half Rollout** | 50% | 15 min | Error rate +3%, p95 latency +10%, cache hit rate <50% |
| **Full Rollout** | 100% | 30 min | Error rate +2%, p95 latency +5%, smoke tests fail |

**Abort Procedure**:
1. Stop deployment immediately (rollback to previous version)
2. Notify on-call team via Slack/PagerDuty
3. Capture logs, metrics, error samples
4. Post-mortem: Analyze failure, update runbooks, add regression test

---

## Signoff Table

| **Role** | **Name** | **Timestamp** | **Signature** |
|----------|----------|---------------|---------------|
| **Platform SRE** | ___________ | _____________ | _____________ |
| **Product Lead** | ___________ | _____________ | _____________ |
| **QA Engineer** | ___________ | _____________ | _____________ |
| **Security Reviewer** | ___________ | _____________ | _____________ |

**Signoff Requirements**:
- Platform SRE: Verified all CI gates GREEN, runbooks reviewed, on-call team briefed
- Product Lead: Approved feature flags matrix, confirmed rollback plan
- QA Engineer: All test suites pass (observability, smoke, ops), coverage thresholds met
- Security Reviewer: PII scan passed, secret detection clean, denylist policy enforced

---

## Rollback Plan

**Immediate Rollback** (if production issues detected within 1 hour of deploy):

1. **Toggle flags OFF** (fastest, no redeploy):
   ```bash
   # Set all flags to safe defaults
   export MODERATION_OBSERVABILITY_ENABLED=false
   export MODERATION_CACHE_ENABLED=false
   export PURCHASE_ENFORCEMENT_ENABLED=false
   
   # Rolling restart (no downtime)
   kubectl rollout restart deployment/deltacrown-api
   ```

2. **Revert deployment** (if flag toggle insufficient):
   ```bash
   # Rollback to previous git tag
   git checkout tags/v1.0.0-pre-phase10
   
   # Redeploy previous version
   # (Deployment commands specific to your infrastructure)
   ```

3. **Verify rollback success**:
   ```bash
   # Check health endpoint
   curl https://deltacrown.example.com/health
   # Expected: status=ok, version matches previous release
   
   # Run smoke tests
   BASE_URL=https://deltacrown.example.com pytest -q -m smoke tests/smoke/
   # Expected: All tests pass
   ```

**Rollback Decision Matrix**:

| **Issue** | **Severity** | **Rollback Method** | **ETA** |
|-----------|--------------|---------------------|---------|
| Error rate spike >5% | Critical | Toggle flags OFF | 2 min |
| p95 latency +20% | High | Toggle flags OFF | 2 min |
| Cache hit rate <50% | Medium | Disable MODERATION_CACHE_ENABLED | 5 min |
| PII leak detected | Critical | **Full redeploy + incident** | 15 min |
| Smoke tests fail | High | Revert deployment | 10 min |

**Post-Rollback Actions**:
1. Notify stakeholders (Slack #releases, email)
2. Capture incident timeline (start, detection, rollback complete)
3. Schedule post-mortem within 24 hours
4. Update runbooks with lessons learned
5. Add regression test to prevent recurrence

---

## Cost Guardrails

See `docs/ops/COST_GUARDRAILS.md` for full details.

**Quick Checks**:
- [ ] S3 lifecycle policies active (STANDARD → IA after 30 days, Glacier after 90 days)
- [ ] Query cost thresholds enforced (no seq scans on large tables, EXPLAIN warnings in CI)
- [ ] Performance baseline budgets set (p95 envelopes: /health <50ms, /api/transactions <200ms, /api/shop/items <150ms)
- [ ] CI policy: PR fails if regression >15% or cost threshold exceeded

---

## References

- **Observability Docs**: `MODULE_8.3_OBSERVABILITY_NOTES.md`
- **Smoke & Alerting**: `PHASE_9_SMOKE_AND_ALERTING.md`
- **Feature Flags**: `config/flags.md`
- **Runbooks**: `RUNBOOKS/ONCALL_HANDOFF.md`
- **Cost Guardrails**: `docs/ops/COST_GUARDRAILS.md`
- **Grafana Dashboards**: `grafana/moderation_enforcement_dashboard.json`, `grafana/slo_burn_alerts.json`
- **Synthetics**: `synthetics/uptime_checks.yml`

---

**Last Review**: 2025-11-13  
**Next Review**: Post Phase 10 deployment (within 48 hours)
