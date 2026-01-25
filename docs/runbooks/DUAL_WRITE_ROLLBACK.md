# Dual-Write Rollback Procedures

**Version:** 1.0  
**Last Updated:** 2026-01-25  
**Criticality:** HIGH  
**Execution Time:** < 5 minutes  

---

## Quick Reference

| Action | Command | Estimated Time |
|--------|---------|----------------|
| Disable Dual-Write | `kubectl set env deployment/deltacrown-web TEAM_VNEXT_DUAL_WRITE_ENABLED=false` | 30 seconds |
| Verify Disabled | `python manage.py shell -c "..."` | 10 seconds |
| Restart Pods | `kubectl rollout restart deployment/deltacrown-web` | 1-2 minutes |
| Cleanup Test Data | SQL scripts below | 2-5 minutes |

---

## Scenario 1: Disable Dual-Write (Emergency)

**Use When:** Dual-write causing production issues, performance degradation, or data corruption.

### Kubernetes Environment

```bash
# Method 1: Quick env update (fastest)
kubectl set env deployment/deltacrown-web \
  TEAM_VNEXT_DUAL_WRITE_ENABLED=false \
  -n deltacrown

# Method 2: Edit ConfigMap (persistent)
kubectl edit configmap deltacrown-config -n deltacrown
# Change: TEAM_VNEXT_DUAL_WRITE_ENABLED: "false"

# Restart pods to apply
kubectl rollout restart deployment/deltacrown-web -n deltacrown
kubectl rollout status deployment/deltacrown-web -n deltacrown
```

### Docker Compose Environment

```bash
# Edit docker-compose.staging.yml
sed -i 's/TEAM_VNEXT_DUAL_WRITE_ENABLED=true/TEAM_VNEXT_DUAL_WRITE_ENABLED=false/' docker-compose.staging.yml

# Restart service
docker-compose -f docker-compose.staging.yml restart web

# OR full restart
docker-compose -f docker-compose.staging.yml down
docker-compose -f docker-compose.staging.yml up -d
```

### Environment File Method

```bash
# Edit .env.staging
nano /opt/deltacrown/.env.staging
# Change: TEAM_VNEXT_DUAL_WRITE_ENABLED=false

# Reload application
systemctl restart deltacrown-staging

# OR send SIGHUP
kill -HUP $(cat /var/run/deltacrown.pid)
```

### Verification

```bash
# SSH into pod/container
kubectl exec -it <pod-name> -n deltacrown -- bash

# Verify flag is disabled
python manage.py shell -c "
from django.conf import settings
enabled = getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_ENABLED', False)
print(f'Dual-Write Enabled: {enabled}')
assert not enabled, 'DUAL_WRITE STILL ENABLED!'
print('✅ Dual-write is DISABLED')
"

# Check logs for confirmation
kubectl logs deployment/deltacrown-web -n deltacrown --tail=50 | grep -i dual_write
# Should see NO new "dual_write_scheduled" messages
```

**Expected Result:** No more `dual_write_scheduled` log messages, vNext requests still succeed.

---

## Scenario 2: Disable Strict Mode (Partial Rollback)

**Use When:** Dual-write failures crashing requests, but want to keep dual-write attempts for logging.

```bash
# Kubernetes
kubectl set env deployment/deltacrown-web \
  TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=false \
  -n deltacrown

kubectl rollout restart deployment/deltacrown-web -n deltacrown

# Verify
python manage.py shell -c "
from django.conf import settings
strict = getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_STRICT_MODE', False)
print(f'Strict Mode: {strict}')
assert not strict, 'STRICT MODE STILL ON!'
print('✅ Strict mode is OFF (log-only failures)')
"
```

**Expected Result:** Dual-write failures logged but don't crash requests.

---

## Scenario 3: Cleanup Test Data

**Use When:** Removing test teams/members created during staging validation.

### Step 1: Identify Test Data

```sql
-- Connect to database
psql $STAGING_DATABASE_URL

-- Find test teams (adjust pattern as needed)
SELECT 
  ot.id as vnext_id,
  ot.name,
  ot.slug,
  otm.legacy_team_id,
  ot.created_at
FROM organizations_team ot
LEFT JOIN organizations_teammigrationmap otm ON ot.id = otm.vnext_team_id
WHERE ot.name LIKE '%Staging Test%' 
   OR ot.name LIKE '%Test Team%'
ORDER BY ot.created_at DESC;

-- Record IDs:
-- vNext Team IDs: [123, 456, 789]
-- Legacy Team IDs: [abc, def, ghi]
```

### Step 2: Delete Test Data (Transaction-Safe)

```sql
-- Start transaction
BEGIN;

-- Step 1: Delete vNext memberships
DELETE FROM organizations_teammembership
WHERE team_id IN (123, 456, 789);  -- Replace with actual IDs

-- Step 2: Delete legacy memberships
DELETE FROM teams_teammembership
WHERE team_id IN (abc, def, ghi);  -- Replace with actual legacy IDs

-- Step 3: Delete migration mappings
DELETE FROM organizations_teammigrationmap
WHERE vnext_team_id IN (123, 456, 789);

-- Step 4: Delete legacy teams
DELETE FROM teams_team
WHERE id IN (abc, def, ghi);

-- Step 5: Delete vNext teams
DELETE FROM organizations_team
WHERE id IN (123, 456, 789);

-- Verify counts
SELECT 
  (SELECT COUNT(*) FROM organizations_team WHERE id IN (123, 456, 789)) as vnext_left,
  (SELECT COUNT(*) FROM teams_team WHERE id IN (abc, def, ghi)) as legacy_left,
  (SELECT COUNT(*) FROM organizations_teammigrationmap WHERE vnext_team_id IN (123, 456, 789)) as mappings_left;
-- Expected: vnext_left=0, legacy_left=0, mappings_left=0

-- If everything looks good:
COMMIT;

-- If something went wrong:
-- ROLLBACK;
```

### Step 3: Verify Cleanup

```sql
-- Confirm no test teams remain
SELECT COUNT(*) as test_teams_left
FROM organizations_team
WHERE name LIKE '%Staging Test%' OR name LIKE '%Test Team%';
-- Expected: 0

-- Check for orphaned mappings
SELECT COUNT(*) as orphans
FROM organizations_teammigrationmap otm
LEFT JOIN organizations_team ot ON otm.vnext_team_id = ot.id
LEFT JOIN teams_team tt ON otm.legacy_team_id = tt.id
WHERE ot.id IS NULL OR tt.id IS NULL;
-- Expected: 0 (or existing count from before testing)
```

---

## Scenario 4: Restore from Backup (Nuclear Option)

**Use When:** Data corruption detected, need to restore to pre-testing state.

### Step 1: Identify Backup

```bash
# List available backups
aws s3 ls s3://deltacrown-backups/staging/ | grep "$(date +%Y-%m-%d)"

# OR for local backups
ls -lh /backup/deltacrown/staging/ | grep "$(date +%Y-%m-%d)"
```

### Step 2: Stop Application

```bash
# Kubernetes
kubectl scale deployment/deltacrown-web --replicas=0 -n deltacrown

# Docker Compose
docker-compose -f docker-compose.staging.yml stop web

# Systemd
systemctl stop deltacrown-staging
```

### Step 3: Restore Database

```bash
# From S3 backup
aws s3 cp s3://deltacrown-backups/staging/deltacrown_staging_20260125_1800.sql.gz /tmp/
gunzip /tmp/deltacrown_staging_20260125_1800.sql.gz

# Restore
psql $STAGING_DATABASE_URL < /tmp/deltacrown_staging_20260125_1800.sql

# OR if using pg_restore
pg_restore -d $STAGING_DATABASE_URL /tmp/deltacrown_staging_20260125_1800.dump
```

### Step 4: Restart Application

```bash
# Kubernetes
kubectl scale deployment/deltacrown-web --replicas=3 -n deltacrown
kubectl rollout status deployment/deltacrown-web -n deltacrown

# Docker Compose
docker-compose -f docker-compose.staging.yml up -d web

# Systemd
systemctl start deltacrown-staging
```

### Step 5: Verify Restoration

```bash
# Check application health
curl https://staging.deltacrown.gg/health/
# Expected: {"status": "healthy"}

# Verify data state
psql $STAGING_DATABASE_URL -c "
SELECT 
  (SELECT COUNT(*) FROM organizations_team) as vnext_teams,
  (SELECT COUNT(*) FROM teams_team WHERE is_active = true) as legacy_teams,
  (SELECT COUNT(*) FROM organizations_teammigrationmap) as mappings;
"
# Compare counts to pre-testing baseline
```

---

## Scenario 5: Block All Legacy Writes (Emergency)

**Use When:** Dual-write bypass not working correctly, need to enforce legacy write blocking.

```bash
# Set flag
kubectl set env deployment/deltacrown-web \
  TEAM_VNEXT_LEGACY_WRITE_BLOCKED=true \
  TEAM_VNEXT_DUAL_WRITE_ENABLED=false \
  -n deltacrown

kubectl rollout restart deployment/deltacrown-web -n deltacrown

# Verify
python manage.py shell -c "
from django.conf import settings
blocked = getattr(settings, 'TEAM_VNEXT_LEGACY_WRITE_BLOCKED', True)
dual_write = getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_ENABLED', False)
print(f'Legacy Write Blocked: {blocked}')
print(f'Dual-Write Enabled: {dual_write}')
assert blocked and not dual_write, 'Flags not correct!'
print('✅ Legacy writes BLOCKED, dual-write DISABLED')
"
```

---

## Rollback Decision Matrix

| Symptom | Action | Urgency |
|---------|--------|---------|
| Requests failing (500 errors) | Disable strict mode → Disable dual-write | IMMEDIATE |
| Performance degraded (>2x latency) | Disable dual-write | HIGH |
| Data inconsistencies detected | Disable dual-write → Investigate | HIGH |
| Logs show `dual_write_failed` (strict OFF) | Monitor → Investigate | LOW (expected) |
| Duplicate mappings detected | Stop dual-write → Cleanup → Re-enable | MEDIUM |
| Orphan mappings increasing | Investigate root cause → Cleanup | MEDIUM |
| Test data left in production | Cleanup test data | LOW |

---

## Verification Checklist

After any rollback:

- [ ] Verify flag changes applied: `kubectl describe deployment/deltacrown-web | grep TEAM_VNEXT`
- [ ] Check pods restarted: `kubectl get pods -n deltacrown`
- [ ] Verify no dual-write logs: `kubectl logs -f deployment/deltacrown-web | grep dual_write`
- [ ] Test vNext request succeeds: `curl -X POST .../api/vnext/teams/create/` (with auth)
- [ ] Check error rates: Grafana/monitoring dashboard
- [ ] Verify no performance regression: APM metrics
- [ ] Update incident log with rollback details
- [ ] Notify team of rollback completion

---

## Post-Rollback Communication Template

```markdown
### Dual-Write Rollback Notification

**Date:** [YYYY-MM-DD HH:MM]
**Environment:** [Staging/Production]
**Action Taken:** [Disabled dual-write / Disabled strict mode / Cleaned up test data]

**Reason:**
[Brief description of issue that triggered rollback]

**Impact:**
- vNext operations: [Unaffected / Degraded]
- Legacy operations: [Unaffected / Not syncing]
- User-facing impact: [None / Minimal / Significant]

**Current State:**
- TEAM_VNEXT_DUAL_WRITE_ENABLED: [true/false]
- TEAM_VNEXT_DUAL_WRITE_STRICT_MODE: [true/false]
- TEAM_VNEXT_LEGACY_WRITE_BLOCKED: [true/false]

**Next Steps:**
1. [Investigate root cause]
2. [Fix identified issue]
3. [Re-test in staging]
4. [Re-enable dual-write with monitoring]

**Team:** [Your name]
**Incident Ticket:** [Link to ticket]
```

---

## Emergency Contacts

- **On-Call Engineer:** [Slack: @oncall-engineering]
- **DevOps Lead:** [Slack: @devops-lead]
- **Database Admin:** [Slack: @dba-oncall]
- **Engineering Manager:** [Phone: xxx-xxx-xxxx]

---

## Rollback Runbook Testing

This runbook should be tested quarterly:

- [ ] Q1 2026: Test dual-write disable in staging (completed: YYYY-MM-DD)
- [ ] Q2 2026: Test strict mode toggle (completed: YYYY-MM-DD)
- [ ] Q3 2026: Test data cleanup procedure (completed: YYYY-MM-DD)
- [ ] Q4 2026: Test backup restoration (completed: YYYY-MM-DD)

**Last Tested:** [Date]  
**Tested By:** [Name]  
**Result:** [Success / Issues found: details]  

---

**End of Rollback Procedures**
