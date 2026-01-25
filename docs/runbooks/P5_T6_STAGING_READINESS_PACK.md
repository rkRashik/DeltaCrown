# P5-T6 Staging Readiness Pack

**Document Version:** 1.0  
**Last Updated:** 2026-01-26  
**Purpose:** Quick reference guide for executing P5-T6 staging dual-write testing safely and efficiently.

---

## 1. Environment Variables Reference

| Variable | Default | Purpose | Phase 5 Value |
|----------|---------|---------|---------------|
| `TEAM_VNEXT_DUAL_WRITE_ENABLED` | `False` | Master toggle for dual-write behavior | `True` (for testing) |
| `TEAM_VNEXT_DUAL_WRITE_STRICT_MODE` | `False` | Fail vNext requests if dual-write fails | `False` (log only) |
| `TEAM_LEGACY_WRITE_BLOCKED` | `True` | Block direct writes to legacy team tables | `True` (keep blocked) |
| `TEAM_LEGACY_WRITE_BYPASS_ENABLED` | `False` | Allow admin bypass for legacy writes | `False` (not needed) |

**Location in Code:**
- File: `deltacrown/settings.py`
- Lines: 977-978, 1014-1015
- All use `os.getenv()` with explicit defaults

**Verification Command:**
```bash
# Inside staging pod/container
python manage.py shell -c "
from django.conf import settings
print(f'DUAL_WRITE_ENABLED: {settings.TEAM_VNEXT_DUAL_WRITE_ENABLED}')
print(f'STRICT_MODE: {settings.TEAM_VNEXT_DUAL_WRITE_STRICT_MODE}')
print(f'LEGACY_BLOCKED: {settings.TEAM_LEGACY_WRITE_BLOCKED}')
"
```

---

## 2. Deployment Methods Quick Reference

### Method A: kubectl set env (Fastest)
```bash
kubectl set env deployment/deltacrown-web \
  TEAM_VNEXT_DUAL_WRITE_ENABLED=true \
  -n deltacrown

kubectl rollout restart deployment/deltacrown-web -n deltacrown
kubectl rollout status deployment/deltacrown-web -n deltacrown
```

### Method B: Kubernetes ConfigMap
```bash
kubectl edit configmap deltacrown-config -n deltacrown
# Add or update env vars, save
kubectl rollout restart deployment/deltacrown-web -n deltacrown
```

### Method C: Docker Compose
```bash
# Edit docker-compose.staging.yml
vim docker-compose.staging.yml
# Add TEAM_VNEXT_DUAL_WRITE_ENABLED=true to environment section
docker-compose -f docker-compose.staging.yml up -d web
```

### Method D: Environment File
```bash
# Edit .env.staging
echo "TEAM_VNEXT_DUAL_WRITE_ENABLED=true" >> .env.staging
# Restart app (depends on deployment: systemctl, supervisorctl, etc.)
supervisorctl restart deltacrown-web
```

### Method E: PaaS (Render/Heroku)
```bash
# Render
render config set TEAM_VNEXT_DUAL_WRITE_ENABLED=true --service=deltacrown-staging

# Heroku
heroku config:set TEAM_VNEXT_DUAL_WRITE_ENABLED=true --app=deltacrown-staging
```

---

## 3. Preconditions Checklist

### 3.1 Access Verification

- [ ] **Kubernetes Access**
  ```bash
  kubectl get pods -n deltacrown
  # Should list running pods
  ```

- [ ] **Database Access**
  ```bash
  psql $STAGING_DATABASE_URL -c "SELECT COUNT(*) FROM organizations_team;"
  # Should return count (not error)
  ```

- [ ] **Feature Flags Baseline**
  ```bash
  kubectl exec -it <pod-name> -n deltacrown -- python manage.py shell -c "
  from django.conf import settings
  print(settings.TEAM_VNEXT_DUAL_WRITE_ENABLED)  # Expected: False
  print(settings.TEAM_LEGACY_WRITE_BLOCKED)      # Expected: True
  "
  ```

### 3.2 Artifact Directory Setup

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M)
ARTIFACTS_DIR="artifacts/p5_t6/${TIMESTAMP}"
mkdir -p "${ARTIFACTS_DIR}/baseline"
mkdir -p "${ARTIFACTS_DIR}/after"
mkdir -p "${ARTIFACTS_DIR}/logs"
echo "Artifacts directory: ${ARTIFACTS_DIR}"
```

### 3.3 Required Tools Installed

- [ ] `kubectl` (if using Kubernetes)
- [ ] `psql` (for database verification)
- [ ] `curl` (for API testing)
- [ ] `jq` (for JSON parsing)
- [ ] `docker` or `docker-compose` (if using Docker deployment)

---

## 4. Collectstatic Checklist

**When Required:**
- If static files updated (CSS, JS, images)
- If deploying code changes alongside dual-write flag change

**Commands:**
```bash
# Inside staging pod/container
python manage.py collectstatic --noinput

# Verify static files served correctly
curl -I https://staging.deltacrown.gg/static/css/main.css
# Expect: 200 OK
```

**Skip If:**
- Only changing environment variables (no code deploy)
- Static files already collected in container image

---

## 5. Monitoring Checklist

### 5.1 Log Patterns to Watch

**Success Pattern:**
```
INFO ... event_type=dual_write_scheduled operation=sync_team_created team_id=123
INFO ... event_type=dual_write_completed operation=sync_team_created team_id=123 duration_ms=45
```

**Warning Pattern (Strict Mode OFF):**
```
WARNING ... event_type=dual_write_failed operation=sync_team_created team_id=123 error="..."
INFO ... Dual-write failure logged, request succeeded (strict_mode=false)
```

**Critical Pattern (Strict Mode ON):**
```
ERROR ... event_type=dual_write_failed operation=sync_team_created team_id=123 error="..."
ERROR ... Dual-write strict mode: raising exception
```

### 5.2 Log Tail Commands

```bash
# Kubernetes
kubectl logs -f deployment/deltacrown-web -n deltacrown | \
  grep -E "dual_write_scheduled|dual_write_completed|dual_write_failed"

# Docker Compose
docker-compose -f docker-compose.staging.yml logs -f web | \
  grep -E "dual_write"

# Search last 10 minutes
kubectl logs deployment/deltacrown-web -n deltacrown --since=10m | \
  grep "dual_write"
```

### 5.3 Database Checks

```sql
-- Count recent vNext teams (last 24 hours)
SELECT COUNT(*) FROM organizations_team 
WHERE created_at > NOW() - INTERVAL '24 hours';

-- Count mappings created today
SELECT COUNT(*) FROM organizations_teammigrationmap
WHERE created_at::date = CURRENT_DATE;

-- Check for orphan mappings
SELECT COUNT(*) FROM organizations_teammigrationmap m
WHERE NOT EXISTS (SELECT 1 FROM organizations_team v WHERE v.id = m.vnext_team_id)
   OR NOT EXISTS (SELECT 1 FROM teams_team l WHERE l.id = m.legacy_team_id);
```

---

## 6. Performance Baseline

### 6.1 Expected Query Counts

| Operation | Before Dual-Write | After Dual-Write | Notes |
|-----------|-------------------|------------------|-------|
| Team Create | 5-8 queries | 5-8 queries | No change (dual-write in on_commit hook) |
| Member Add | 3-5 queries | 3-5 queries | No change |
| Team Update | 2-4 queries | 2-4 queries | No change |

**Key Principle:** Dual-write hooks execute AFTER transaction commit, so request-phase query count is unchanged.

### 6.2 Expected Latency

| Endpoint | Baseline p95 | Acceptable p95 | Alert Threshold |
|----------|--------------|----------------|-----------------|
| `/api/vnext/teams/create/` | 150ms | 200ms | >300ms |
| `/api/vnext/teams/{slug}/members/add/` | 80ms | 120ms | >200ms |
| `/api/vnext/teams/{slug}/settings/` | 100ms | 150ms | >250ms |

**Note:** Adjust thresholds based on your actual staging baseline measurements.

### 6.3 Performance Test Script

```bash
# Save to: scripts/perf_test_team_create.sh
#!/bin/bash
TOKEN="<your-staging-token>"
ENDPOINT="https://staging.deltacrown.gg/api/vnext/teams/create/"

for i in {1..20}; do
  START=$(date +%s%N)
  curl -s -X POST "$ENDPOINT" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"Perf Test $i\", \"game_id\": 1, \"region\": \"NA\"}" \
    > /dev/null
  END=$(date +%s%N)
  ELAPSED=$(( (END - START) / 1000000 ))
  echo "Request $i: ${ELAPSED}ms"
done
```

---

## 7. Rollback Decision Matrix

| Symptom | Severity | Action | Urgency |
|---------|----------|--------|---------|
| Dual-write failures logged (strict mode OFF) | LOW | Continue testing, investigate logs | Normal |
| 100% dual-write failures | HIGH | Disable dual-write, investigate | Immediate |
| vNext requests failing (strict mode ON) | CRITICAL | Disable dual-write + strict mode | Emergency |
| Database connection pool exhaustion | CRITICAL | Disable dual-write, scale DB | Emergency |
| Duplicate legacy IDs detected | MEDIUM | Pause testing, run consistency report | High |
| Orphan mappings increasing | MEDIUM | Investigate mapping logic | High |
| p95 latency >2x baseline | HIGH | Consider rollback, profile queries | Immediate |

### 7.1 Fast Rollback Command

```bash
# Kubernetes
kubectl set env deployment/deltacrown-web \
  TEAM_VNEXT_DUAL_WRITE_ENABLED=false \
  TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=false \
  -n deltacrown

kubectl rollout restart deployment/deltacrown-web -n deltacrown
```

**Full Rollback Runbook:** See [DUAL_WRITE_ROLLBACK.md](./DUAL_WRITE_ROLLBACK.md)

---

## 8. Evidence Package Checklist

### 8.1 Required Files for PR/Ticket

- [ ] `baseline/validation_before.txt`
- [ ] `baseline/validation_before.json`
- [ ] `after/validation_after.txt`
- [ ] `after/validation_after.json`
- [ ] `delta.json` (computed differences)
- [ ] `delta.md` (human-readable delta)
- [ ] `SUMMARY.md` (copy/paste for tracker)
- [ ] `logs/` directory with:
  - [ ] Flow response JSONs (e.g., `flow1_team_create_response.json`)
  - [ ] Log excerpts showing dual_write events
  - [ ] Performance test results (if applicable)

### 8.2 Artifact Generation

```bash
# Automated with script
python scripts/staging_validation_test.py \
  --env=staging-k8s \
  --out-dir="${ARTIFACTS_DIR}" \
  --before="${ARTIFACTS_DIR}/baseline/validation_before.json" \
  --after="${ARTIFACTS_DIR}/after/validation_after.json"

# Verify all files created
ls -lh "${ARTIFACTS_DIR}"
ls -lh "${ARTIFACTS_DIR}/baseline/"
ls -lh "${ARTIFACTS_DIR}/after/"
ls -lh "${ARTIFACTS_DIR}/logs/"
```

### 8.3 Tracker Update Block

After running script, copy from `SUMMARY.md`:

```
P5-T6 Staging Testing Completed (YYYY-MM-DD)
- vNext Teams Created: N
- Mapped Teams: N
- Dual-Write Status: ✅ SUCCESS / ❌ ISSUES FOUND
- Artifact Directory: artifacts/p5_t6/YYYYMMDD_HHMM/
```

Paste into tracker at: `Documents/Team & Organization/Execution/TEAM_ORG_VNEXT_TRACKER.md`

---

## 9. Smoke Test Quick Reference

| Flow | API Endpoint | Expected Dual-Write Event |
|------|--------------|--------------------------|
| 1. Create Team | `POST /api/vnext/teams/create/` | `sync_team_created` |
| 2. Add Member | `POST /api/vnext/teams/{slug}/members/add/` | `sync_team_member_added` |
| 3. Update Role | `POST /api/vnext/teams/{slug}/members/{id}/role/` | `sync_team_member_updated` |
| 4. Update Settings | `POST /api/vnext/teams/{slug}/settings/` | `sync_team_settings_updated` |
| 5. Remove Member | `POST /api/vnext/teams/{slug}/members/{id}/remove/` | `sync_team_member_removed` |

**Detailed Flows:** See [P5_T6_STAGING_DUAL_WRITE_TESTING.md](./P5_T6_STAGING_DUAL_WRITE_TESTING.md) Phase 3.

---

## 10. Common Issues & Solutions

### Issue: "dual_write_scheduled" not appearing in logs

**Solution:**
1. Verify flag enabled: `kubectl exec <pod> -- python manage.py shell -c "from django.conf import settings; print(settings.TEAM_VNEXT_DUAL_WRITE_ENABLED)"`
2. Ensure pod restarted after flag change
3. Check signal handlers registered (should be automatic)

### Issue: Legacy shadow rows not created

**Solution:**
1. Check logs for `dual_write_failed` events
2. Verify database permissions (staging user can write to `teams_team`)
3. Check for foreign key constraints (e.g., game_id, user_id validity)
4. Run validation report: `python manage.py vnext_validation_report`

### Issue: High dual-write failure rate

**Solution:**
1. Check database logs for errors
2. Verify legacy schema matches expectations
3. Check for race conditions (e.g., duplicate slug conflicts)
4. Consider enabling strict mode temporarily to surface errors immediately

### Issue: Performance regression

**Solution:**
1. Profile dual-write hook execution (check logs for `duration_ms`)
2. Verify on_commit hooks not executing inline (should be async)
3. Check database connection pool (may need scaling)
4. Review dual-write service queries for N+1 patterns

---

## 11. Post-Testing Cleanup (Optional)

### 11.1 Remove Test Data

```sql
-- CAUTION: Only in staging, wrap in transaction
BEGIN;

-- Delete test teams (by naming pattern)
DELETE FROM organizations_team 
WHERE name LIKE 'Staging Test%' OR name LIKE 'Perf Test%';

-- Delete orphan mappings (if any)
DELETE FROM organizations_teammigrationmap m
WHERE NOT EXISTS (SELECT 1 FROM organizations_team v WHERE v.id = m.vnext_team_id);

-- Verify counts
SELECT COUNT(*) FROM organizations_team WHERE name LIKE '%Test%';

-- ROLLBACK; -- if counts look wrong
COMMIT;
```

### 11.2 Keep Dual-Write Enabled

**Recommendation for Phase 5:**
- Keep `TEAM_VNEXT_DUAL_WRITE_ENABLED=true` in staging after successful testing
- Allows ongoing validation as new vNext features are added
- Prepares for production dual-write (Phase 6)

**Disable only if:**
- Critical bugs found requiring code fixes
- Rolling back to Phase 4

---

## 12. Next Steps After Successful Testing

1. ✅ Update tracker: Mark P5-T6 "Manual Staging Execution Complete"
2. ✅ Commit artifact directory to repository
3. ✅ Schedule team review of results
4. ✅ Plan Phase 6 preparation (unblock legacy endpoint writes)
5. ✅ Monitor staging for 24-48 hours with dual-write enabled
6. ✅ Document any edge cases or unexpected behaviors
7. ✅ Update runbook with lessons learned

---

## 13. Emergency Contacts

**Who to contact if issues arise:**
- Backend Lead: [FILL IN]
- Database Admin: [FILL IN]
- DevOps/Platform: [FILL IN]
- On-Call Engineer: [FILL IN]

**Escalation:**
- Severity LOW: Slack #team-backend
- Severity MEDIUM: Slack + mention @backend-lead
- Severity HIGH: Slack + PagerDuty alert
- Severity CRITICAL: PagerDuty + phone call

---

**END OF READINESS PACK**
