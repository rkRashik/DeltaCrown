# P5-T6 Deliverables Summary

**Task:** Staging Testing / Enable Dual-Write  
**Status:** ✅ Documentation Complete - Awaiting Manual Execution  
**Completed:** 2026-01-25 20:50  
**Duration:** ~14 minutes (documentation only)  
**Team Member Required:** Yes (manual staging execution)  

---

## 📦 What Was Delivered

### Documentation Files (4)

1. **[docs/runbooks/P5_T6_STAGING_DUAL_WRITE_TESTING.md](g:/My%20Projects/WORK/DeltaCrown/docs/runbooks/P5_T6_STAGING_DUAL_WRITE_TESTING.md)** (NEW - 680 lines)
   - Comprehensive 8-phase runbook
   - Pre-flight checklist
   - Baseline validation capture
   - Flag enablement (Kubernetes/Docker/env)
   - 5 end-to-end test flows with verification
   - Performance validation
   - Failure simulation (optional)
   - Rollback procedures
   - Success criteria checklist
   - Troubleshooting guide
   - 3 appendices (env vars, SQL queries, report interpretation)

2. **[docs/runbooks/DUAL_WRITE_ROLLBACK.md](g:/My%20Projects/WORK/DeltaCrown/docs/runbooks/DUAL_WRITE_ROLLBACK.md)** (NEW - 350 lines)
   - 5 emergency rollback scenarios
   - Quick reference table (<5 minute procedures)
   - Transaction-safe cleanup scripts
   - Backup restoration procedures
   - Rollback decision matrix
   - Verification checklist
   - Communication template
   - Emergency contacts

3. **[docs/runbooks/P5_T6_QUICK_START.md](g:/My%20Projects/WORK/DeltaCrown/docs/runbooks/P5_T6_QUICK_START.md)** (NEW - 120 lines)
   - TL;DR command reference
   - Copy-paste ready scripts
   - What to look for (logs, database)
   - Expected results table
   - 5-minute emergency rollback
   - Troubleshooting quick reference

4. **[docs/runbooks/P5_T6_README.md](g:/My%20Projects/WORK/DeltaCrown/docs/runbooks/P5_T6_README.md)** (NEW - 280 lines)
   - Documentation index
   - Execution workflow diagram
   - Success criteria
   - Important notes
   - Emergency rollback reference
   - Support contacts
   - Execution tracking checklist

### Automation Script (1)

5. **[scripts/staging_validation_test.py](g:/My%20Projects/WORK/DeltaCrown/scripts/staging_validation_test.py)** (NEW - 380 lines)
   - Automated baseline/after report generation
   - Delta analysis and comparison
   - Summary report generation (markdown)
   - Support for Kubernetes, Docker, local environments
   - Command-line interface with options
   - Usage: `python scripts/staging_validation_test.py --env=staging-k8s`

### Tracker Updates (1)

6. **[Documents/Team & Organization/Execution/TEAM_ORG_VNEXT_TRACKER.md](g:/My%20Projects/WORK/DeltaCrown/Documents/Team%20&%20Organization/Execution/TEAM_ORG_VNEXT_TRACKER.md)** (MODIFIED)
   - Updated: P5-T6 status (Documentation Complete)
   - Documented: All deliverables created
   - Listed: Manual execution requirements
   - Provided: Quick command reference
   - Defined: Success criteria
   - Noted: Stop point (awaiting manual execution)

---

## ✅ Verification

- ✅ Django check passed (no configuration errors)
- ✅ All documentation files created
- ✅ Automation script created with CLI interface
- ✅ Runbooks include comprehensive procedures
- ✅ Rollback procedures documented with quick reference
- ✅ Tracker updated with full task documentation
- ✅ Success criteria clearly defined

---

## 📋 What Engineering Team Must Do

**Manual Execution Required in Staging Environment:**

### Step 1: Pre-Flight (5 minutes)
```bash
# Read quick start guide
cat docs/runbooks/P5_T6_QUICK_START.md

# Verify staging access
kubectl get pods -n deltacrown
# OR: docker ps | grep deltacrown
# OR: ssh user@staging-server

# Check database backups are current
# (Verify last backup timestamp)
```

### Step 2: Baseline Report (5 minutes)
```bash
# Capture baseline state
kubectl exec -it <staging-pod> -n deltacrown -- \
  python manage.py vnext_validation_report \
  --format=json \
  --sample-size=100 \
  > logs/validation_before.json

# Review metrics
cat logs/validation_before.json | jq '.coverage'
```

### Step 3: Enable Dual-Write (2 minutes)
```bash
# Set environment variables
kubectl set env deployment/deltacrown-web \
  TEAM_VNEXT_DUAL_WRITE_ENABLED=true \
  TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=false \
  -n deltacrown

# Restart pods
kubectl rollout restart deployment/deltacrown-web -n deltacrown
kubectl rollout status deployment/deltacrown-web -n deltacrown

# Verify flags active
kubectl exec -it <pod> -n deltacrown -- \
  python manage.py shell -c "
from django.conf import settings
print(f'Dual-Write: {getattr(settings, \"TEAM_VNEXT_DUAL_WRITE_ENABLED\", False)}')
print(f'Strict Mode: {getattr(settings, \"TEAM_VNEXT_DUAL_WRITE_STRICT_MODE\", False)}')
"
# Expected: Dual-Write: True, Strict Mode: False
```

### Step 4: Execute Test Flows (30-60 minutes)
```bash
# Get auth token
TOKEN=$(curl -X POST https://staging.deltacrown.gg/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}' \
  | jq -r '.token')

# Test 1: Create team
curl -X POST https://staging.deltacrown.gg/api/vnext/teams/create/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Staging Test Team Alpha",
    "game_id": 1,
    "region": "NA"
  }' | jq '.'

# Test 2-5: Add member, update role, update settings, remove member
# (See runbook for complete curl commands)
```

### Step 5: Verify (10 minutes)
```bash
# Check logs
kubectl logs -f deployment/deltacrown-web -n deltacrown | grep dual_write
# Look for: dual_write_scheduled events

# Check database
psql $STAGING_DB_URL -c "
SELECT * FROM organizations_teammigrationmap 
ORDER BY id DESC LIMIT 5;
"
# Verify: New mappings exist for test teams
```

### Step 6: After Report (5 minutes)
```bash
# Capture after state
kubectl exec -it <staging-pod> -n deltacrown -- \
  python manage.py vnext_validation_report \
  --format=json \
  --sample-size=100 \
  > logs/validation_after.json

# Compare reports
python scripts/staging_validation_test.py --env=staging-k8s
# Fills in baseline → prompts for testing → captures after → generates summary
```

### Step 7: Document & Update Tracker (10 minutes)
```bash
# Review generated summary
cat logs/staging_test_summary_*.md

# Fill in manual sections:
# - Issues encountered
# - Performance observations
# - Rollback status

# Update tracker
# (Mark P5-T6 as COMPLETED with results)
```

**Total Estimated Time:** 2-3 hours

---

## 🎯 Success Criteria

Team must verify ALL of these before marking P5-T6 complete:

- [ ] Dual-write flags enabled in staging
- [ ] All 5 test flows executed successfully
- [ ] Logs show `dual_write_scheduled` events for each operation
- [ ] Legacy shadow rows exist (TeamMigrationMap + legacy tables)
- [ ] Validation report shows increased mapping coverage
- [ ] Dual-write health section present in after report
- [ ] No performance regressions (query count, latency)
- [ ] Zero inline legacy writes detected
- [ ] Rollback procedures tested (optional but recommended)
- [ ] Tracker updated with complete results

---

## 📊 Expected Results

**Coverage Delta:**
- vNext Teams: +5 to +10 (test teams created)
- Mapped Teams: Should equal vNext teams created
- Mapping Coverage: Should increase or stay at 100%

**Dual-Write Health:**
- Section should appear in after report (was null before)
- Recent vNext Teams (24h): Count of test teams
- Missing Legacy Count: Should be 0 (all synced)
- Severity: Should be "ok" or "warning" (not "error")

**Performance:**
- Request latency: No significant increase (<10%)
- Query count: Same as baseline (no inline legacy writes)
- Error rate: Should remain at baseline (no new errors)

---

## 🚨 Emergency Rollback

If ANY issues detected:

```bash
# 1. Disable dual-write (< 1 minute)
kubectl set env deployment/deltacrown-web \
  TEAM_VNEXT_DUAL_WRITE_ENABLED=false \
  -n deltacrown

kubectl rollout restart deployment/deltacrown-web -n deltacrown

# 2. Verify disabled
kubectl exec -it <pod> -n deltacrown -- \
  python manage.py shell -c "
from django.conf import settings
print(getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_ENABLED', False))
"
# Expected: False

# 3. Notify team
# Post in #team-vnext-migration
```

**Full procedures:** See [DUAL_WRITE_ROLLBACK.md](g:/My%20Projects/WORK/DeltaCrown/docs/runbooks/DUAL_WRITE_ROLLBACK.md)

---

## 📞 Support

- **Documentation:** [docs/runbooks/P5_T6_README.md](g:/My%20Projects/WORK/DeltaCrown/docs/runbooks/P5_T6_README.md)
- **Quick Start:** [docs/runbooks/P5_T6_QUICK_START.md](g:/My%20Projects/WORK/DeltaCrown/docs/runbooks/P5_T6_QUICK_START.md)
- **Full Runbook:** [docs/runbooks/P5_T6_STAGING_DUAL_WRITE_TESTING.md](g:/My%20Projects/WORK/DeltaCrown/docs/runbooks/P5_T6_STAGING_DUAL_WRITE_TESTING.md)
- **Rollback:** [docs/runbooks/DUAL_WRITE_ROLLBACK.md](g:/My%20Projects/WORK/DeltaCrown/docs/runbooks/DUAL_WRITE_ROLLBACK.md)
- **Questions:** Slack #team-vnext-migration

---

## ⏭️ Next Steps

After P5-T6 manual execution completes:

1. **Review Results:** Team reviews summary report
2. **Update Tracker:** Mark P5-T6 as ✅ COMPLETED with metrics
3. **Team Meeting:** Discuss findings, issues, performance
4. **Plan Next Task:** Phase 6 Unblock Preparation
5. **Production Planning:** Schedule dual-write enablement in production

---

**Status:** Ready for Manual Execution by Engineering Team 🚀

**Last Updated:** 2026-01-25 20:50  
**AI Task Complete:** ✅ Documentation Delivered  
**Human Task Pending:** ⏳ Manual Staging Execution Required  
