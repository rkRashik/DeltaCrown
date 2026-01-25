# P5-T6: Staging Dual-Write Testing Runbook

**Version:** 1.0  
**Last Updated:** 2026-01-25  
**Phase:** Phase 5 (Data Migration)  
**Status:** READY FOR EXECUTION  

---

## Overview

This runbook provides step-by-step instructions for enabling and testing dual-write functionality in the **staging environment**. The goal is to prove that vNext write operations correctly create/update legacy shadow rows after commit with zero inline legacy writes.

**Duration Estimate:** 2-3 hours  
**Prerequisites:** Access to staging environment, database read access, log access  
**Risk Level:** Low (staging only, strict mode OFF, easy rollback)  

---

## Repository Audit - File Locations

**Purpose:** Verify all required files exist before proceeding with staging testing.

### Core Files (Verified)

| File Path | Purpose | Status |
|-----------|---------|--------|
| `docs/runbooks/P5_T6_STAGING_DUAL_WRITE_TESTING.md` | This runbook | ✅ Exists |
| `docs/runbooks/DUAL_WRITE_ROLLBACK.md` | Emergency rollback procedures | ✅ Exists |
| `scripts/staging_validation_test.py` | Automated report generation + delta analysis | ✅ Exists |
| `apps/organizations/management/commands/vnext_validation_report.py` | Django management command | ✅ Exists |
| `apps/organizations/services/validation_report_service.py` | Report generation service | ✅ Exists |
| `apps/organizations/services/dual_write_sync_service.py` | Dual-write sync logic | ✅ Exists |

### Environment Variables (Required)

| Variable | Default | Location | Purpose |
|----------|---------|----------|---------|
| `TEAM_VNEXT_DUAL_WRITE_ENABLED` | `False` | `deltacrown/settings.py:1014` | Enable dual-write to legacy tables |
| `TEAM_VNEXT_DUAL_WRITE_STRICT_MODE` | `False` | `deltacrown/settings.py:1015` | Fail requests if dual-write errors |
| `TEAM_LEGACY_WRITE_BLOCKED` | `True` | `deltacrown/settings.py:977` | Block direct legacy writes (Phase 5 default) |
| `TEAM_LEGACY_WRITE_BYPASS_ENABLED` | `False` | `deltacrown/settings.py:978` | Emergency bypass for legacy writes |

### Verification Commands

```bash
# Verify management command exists
python manage.py vnext_validation_report --help

# Verify dual-write service imports
python manage.py shell -c "from apps.organizations.services.dual_write_sync_service import DualWriteSyncService; print('✅ DualWriteSyncService OK')"

# Verify validation script exists
ls -lh scripts/staging_validation_test.py
python scripts/staging_validation_test.py --help
```

---

## Pre-Flight Checklist

### Environment Health
- [ ] Staging environment is healthy (no ongoing incidents)
- [ ] Database backups are current (verify last backup timestamp)
- [ ] You have SSH/kubectl access to staging pods
- [ ] You have database read access to verify shadow rows
- [ ] Log aggregation is working (can view application logs)
- [ ] Django debug toolbar or query logging enabled (for performance checks)
- [ ] Rollback plan reviewed and understood
- [ ] Incident response team notified (awareness, not alert)

### Access Verification

```bash
# Verify kubectl access (if using Kubernetes)
kubectl get pods -n deltacrown
kubectl logs deployment/deltacrown-web -n deltacrown --tail=10

# Verify database access
psql $STAGING_DATABASE_URL -c "SELECT COUNT(*) FROM organizations_team;"

# Verify feature flags are currently DISABLED (baseline)
kubectl exec -it $(kubectl get pods -n deltacrown -l app=deltacrown-web -o jsonpath='{.items[0].metadata.name}') -n deltacrown -- \
  python manage.py shell -c "from django.conf import settings; print(f'DUAL_WRITE: {settings.TEAM_VNEXT_DUAL_WRITE_ENABLED}, STRICT: {settings.TEAM_VNEXT_DUAL_WRITE_STRICT_MODE}')"
# Expected output: DUAL_WRITE: False, STRICT: False

# Verify legacy write blocking is ON (Phase 5 default)
kubectl exec -it $(kubectl get pods -n deltacrown -l app=deltacrown-web -o jsonpath='{.items[0].metadata.name}') -n deltacrown -- \
  python manage.py shell -c "from django.conf import settings; print(f'LEGACY_BLOCKED: {settings.TEAM_LEGACY_WRITE_BLOCKED}')"
# Expected output: LEGACY_BLOCKED: True
```

### Artifact Directory Setup

```bash
# Create timestamped artifacts directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACTS_DIR="artifacts/p5_t6/${TIMESTAMP}"
mkdir -p "${ARTIFACTS_DIR}/baseline"
mkdir -p "${ARTIFACTS_DIR}/after"
mkdir -p "${ARTIFACTS_DIR}/logs"

echo "Artifacts will be saved to: ${ARTIFACTS_DIR}"
```

---

## Phase 1: Baseline Validation Report

**Objective:** Capture current state before enabling dual-write.

### 1.1 Run Validation Report (Before)

```bash
# Set variables
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACTS_DIR="artifacts/p5_t6/${TIMESTAMP}"

# SSH into staging pod
POD_NAME=$(kubectl get pods -n deltacrown -l app=deltacrown-web -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it ${POD_NAME} -n deltacrown -- bash

# OR if using docker-compose staging
docker-compose -f docker-compose.staging.yml exec web bash

# Inside pod/container: Run validation report (text format)
python manage.py vnext_validation_report --sample-size=100 > /tmp/validation_before.txt
cat /tmp/validation_before.txt

# Inside pod/container: Run validation report (JSON format for analysis)
python manage.py vnext_validation_report --format=json --sample-size=100 > /tmp/validation_before.json
```

### 1.2 Copy Reports to Artifacts Directory

```bash
# Exit pod/container (Ctrl+D or type 'exit')

# Copy reports from pod to local artifacts directory
kubectl cp ${POD_NAME}:/tmp/validation_before.txt "${ARTIFACTS_DIR}/baseline/validation_before.txt" -n deltacrown
kubectl cp ${POD_NAME}:/tmp/validation_before.json "${ARTIFACTS_DIR}/baseline/validation_before.json" -n deltacrown

# OR for docker-compose
CONTAINER_ID=$(docker-compose -f docker-compose.staging.yml ps -q web)
docker cp ${CONTAINER_ID}:/tmp/validation_before.txt "${ARTIFACTS_DIR}/baseline/validation_before.txt"
docker cp ${CONTAINER_ID}:/tmp/validation_before.json "${ARTIFACTS_DIR}/baseline/validation_before.json"

# Verify files exist
ls -lh "${ARTIFACTS_DIR}/baseline/"
```

Record these values from the report:

```
Legacy Team Count: ___________
vNext Team Count: ___________
Mapped Team Count: ___________
Mapping Coverage: ___________% 
Unmapped Legacy Count: ___________

Duplicate Legacy IDs: ___________
Duplicate vNext IDs: ___________
Orphan Mappings: ___________

Dual-Write Health: (should be "null" - not enabled yet)
```

### 1.3 Save Baseline Files

```bash
# Copy files to local machine for comparison
kubectl cp <staging-pod>:/tmp/validation_before.txt ./validation_before.txt
kubectl cp <staging-pod>:/tmp/validation_before.json ./validation_before.json

# OR for docker-compose
docker cp <container-id>:/tmp/validation_before.txt ./validation_before.txt
docker cp <container-id>:/tmp/validation_before.json ./validation_before.json
```

---

## Phase 2: Enable Dual-Write Flags

**Objective:** Turn on dual-write in staging with safe settings.

### 2.1 Set Environment Variables

**Method A: Kubernetes (kubectl set env)**

```bash
# Enable dual-write flags using kubectl
kubectl set env deployment/deltacrown-web \
  TEAM_VNEXT_DUAL_WRITE_ENABLED=true \
  TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=false \
  -n deltacrown

# Restart deployment
kubectl rollout restart deployment/deltacrown-web -n deltacrown
kubectl rollout status deployment/deltacrown-web -n deltacrown

# Verify env vars on pod
POD_NAME=$(kubectl get pods -n deltacrown -l app=deltacrown-web -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it ${POD_NAME} -n deltacrown -- env | grep TEAM_VNEXT_DUAL_WRITE
```

**Method B: Kubernetes (ConfigMap/Secret)**

```bash
# Edit staging configmap
kubectl edit configmap deltacrown-config -n deltacrown

# Add these lines under 'data:' section:
data:
  TEAM_VNEXT_DUAL_WRITE_ENABLED: "true"
  TEAM_VNEXT_DUAL_WRITE_STRICT_MODE: "false"
  
# Restart pods to pick up config
kubectl rollout restart deployment/deltacrown-web -n deltacrown
kubectl rollout status deployment/deltacrown-web -n deltacrown
```

**Method C: Docker Compose Staging**

```bash
# Edit docker-compose.staging.yml
nano docker-compose.staging.yml

# Add to environment section:
environment:
  - TEAM_VNEXT_DUAL_WRITE_ENABLED=true
  - TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=false

# Restart services
docker-compose -f docker-compose.staging.yml down
docker-compose -f docker-compose.staging.yml up -d
```

**Method D: Environment File (.env)**

```bash
# Edit .env.staging
nano .env.staging

# Add or update:
TEAM_VNEXT_DUAL_WRITE_ENABLED=true
TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=false

# Reload application (method depends on deployment)
systemctl restart deltacrown-staging
# OR
supervisorctl restart deltacrown-staging
```

**Method E: Render/Heroku/PaaS**

```bash
# For Render
render config set TEAM_VNEXT_DUAL_WRITE_ENABLED=true TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=false --service=deltacrown-staging

# For Heroku
heroku config:set TEAM_VNEXT_DUAL_WRITE_ENABLED=true TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=false --app=deltacrown-staging

# Verify
render config --service=deltacrown-staging | grep TEAM_VNEXT
# OR
heroku config --app=deltacrown-staging | grep TEAM_VNEXT
```

### 2.2 Verify Flags Are Active

```bash
# Get pod/container name
POD_NAME=$(kubectl get pods -n deltacrown -l app=deltacrown-web -o jsonpath='{.items[0].metadata.name}')

# SSH into pod/container
kubectl exec -it ${POD_NAME} -n deltacrown -- bash

# Check Django settings
python manage.py shell -c "
from django.conf import settings
print(f'TEAM_VNEXT_DUAL_WRITE_ENABLED: {getattr(settings, \"TEAM_VNEXT_DUAL_WRITE_ENABLED\", False)}')
print(f'TEAM_VNEXT_DUAL_WRITE_STRICT_MODE: {getattr(settings, \"TEAM_VNEXT_DUAL_WRITE_STRICT_MODE\", False)}')
print(f'TEAM_LEGACY_WRITE_BLOCKED: {getattr(settings, \"TEAM_LEGACY_WRITE_BLOCKED\", True)}')
"
```

**Expected Output:**
```
TEAM_VNEXT_DUAL_WRITE_ENABLED: True
TEAM_VNEXT_DUAL_WRITE_STRICT_MODE: False
TEAM_LEGACY_WRITE_BLOCKED: True
```

✅ **Checkpoint:** All three flags show expected values.

### 2.3 Optional: Enable Strict Mode for Secondary Test

**Purpose:** Test failure behavior when dual-write errors occur.

```bash
# Set strict mode TRUE (after initial safe testing)
kubectl set env deployment/deltacrown-web \
  TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=true \
  -n deltacrown

kubectl rollout restart deployment/deltacrown-web -n deltacrown

# Run 1-2 smoke flows only
# Expected: If dual-write fails, vNext request should return 500 error
# Log should show: dual_write_failed with severity=ERROR

# IMPORTANT: Disable strict mode after testing
kubectl set env deployment/deltacrown-web \
  TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=false \
  -n deltacrown

kubectl rollout restart deployment/deltacrown-web -n deltacrown
```

---

## Phase 3: End-to-End Smoke Tests

**Objective:** Execute vNext write operations and verify dual-write behavior.

### 3.1 Test Flow 1: Independent Team Creation

**Via API (Recommended for logging clarity):**

```bash
# Get auth token (adjust for your auth system)
TOKEN=$(curl -X POST https://staging.deltacrown.gg/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}' \
  | jq -r '.token')

# Create independent team
RESPONSE=$(curl -X POST https://staging.deltacrown.gg/api/vnext/teams/create/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Staging Test Team Alpha",
    "game_id": 1,
    "region": "NA",
    "branding": {
      "logo_url": "https://cdn.example.com/test.png",
      "primary_color": "#FF0000"
    }
  }')

echo "$RESPONSE" | jq '.'

# Save team_id for later steps
TEAM_ID=$(echo "$RESPONSE" | jq -r '.team_id')
TEAM_SLUG=$(echo "$RESPONSE" | jq -r '.team_slug')
echo "Created: team_id=${TEAM_ID}, slug=${TEAM_SLUG}"

# Save to artifacts
echo "${RESPONSE}" > "${ARTIFACTS_DIR}/logs/flow1_team_create_response.json"
```

**Expected Response (201):**
```json
{
  "team_id": 123,
  "team_slug": "staging-test-team-alpha",
  "team_url": "/organizations/teams/staging-test-team-alpha/"
}
```

**Via UI (Alternative):**
1. Navigate to https://staging.deltacrown.gg/teams/create/
2. Login if needed (use test account)
3. Fill form:
   - Team Name: "Staging Test Team Beta"
   - Game: Select "Valorant" (or available game)
   - Region: Select "NA"
   - Logo URL (optional): Leave blank or add test URL
4. Click "Create Team" button
5. Verify redirect to team detail page: `/organizations/teams/staging-test-team-beta/`
6. Note team ID from URL or page metadata
7. Open browser DevTools → Network tab → Find POST request → Copy team_id from response

**Fallback: If Team Model Not Yet Deployed to Staging**
```bash
# Skip test flow, document as "SKIPPED - Model not available"
echo "SKIPPED: organizations.Team model not yet in staging schema" >> "${ARTIFACTS_DIR}/logs/skipped_flows.txt"
# Proceed to next available test flow
```

### 3.2 Verify Logs Show Hook Scheduling

```bash
# Save team_id from API response to variable for log filtering
TEAM_ID=123  # Replace with actual ID from step 3.1

# Tail application logs with precise filters
kubectl logs -f deployment/deltacrown-web -n deltacrown | \
  grep -E "dual_write_scheduled|dual_write_completed|dual_write_failed" | \
  grep "team_id=${TEAM_ID}"

# OR for docker-compose
docker-compose -f docker-compose.staging.yml logs -f web | \
  grep -E "dual_write_scheduled|dual_write_completed|dual_write_failed" | \
  grep "team_id=${TEAM_ID}"

# Search last 10 minutes of logs (non-streaming)
kubectl logs deployment/deltacrown-web -n deltacrown --since=10m | \
  grep -E "dual_write_scheduled.*team_id=${TEAM_ID}"
```

**Expected Log Lines:**
```
INFO ... event_type=team_created team_id=123 team_slug=staging-test-team-alpha user_id=456
INFO ... event_type=dual_write_scheduled operation=sync_team_created team_id=123 user_id=456
INFO ... Dual-write scheduled for team creation: 123
INFO ... event_type=dual_write_completed operation=sync_team_created team_id=123 duration_ms=45
```

**If Failure Occurs (Strict Mode OFF):**
```
WARNING ... event_type=dual_write_failed operation=sync_team_created team_id=123 error="DatabaseError: ..." severity=warning
INFO ... Dual-write failure logged, request succeeded (strict_mode=false)
```

✅ **Checkpoint:** Logs show `dual_write_scheduled` → `dual_write_completed` OR `dual_write_failed` (logged only).

### 3.3 Verify Legacy Shadow Rows Exist

```bash
# Connect to staging database
psql $STAGING_DATABASE_URL

# OR via kubectl
kubectl exec -it postgres-staging-0 -n deltacrown -- psql -U deltacrown deltacrown_db

# OR via docker-compose
docker-compose -f docker-compose.staging.yml exec db psql -U deltacrown
```

**Step 1: Check TeamMigrationMap**
```sql
-- Replace 123 with actual team_id from step 3.1
\x  -- Expanded display for readability

SELECT 
  id,
  legacy_team_id,
  vnext_team_id,
  migration_date,
  verified,
  created_at,
  updated_at
FROM organizations_teammigrationmap
WHERE vnext_team_id = 123;

-- Expected: 1 row with populated legacy_team_id
-- Save legacy_team_id value (e.g., 456) for next queries
```

**Step 2: Check Legacy Team Record**
```sql
-- Replace 456 with legacy_team_id from Step 1
SELECT 
  id,
  name,
  slug,
  game,
  region,
  is_active,
  created_at,
  updated_at
FROM teams_team
WHERE id = 456;

-- Expected: 1 row with matching name/slug/game/region as vNext team
```

**Step 3: Check vNext Team Record**
```sql
SELECT 
  id,
  name,
  slug,
  game_id,
  region,
  status,
  created_at,
  updated_at,
  branding  -- JSONB field
FROM organizations_team
WHERE id = 123;

-- Expected: 1 row with status='ACTIVE', matching name/slug
```

**Step 4: Verify Data Consistency (Single Query)**
```sql
-- Join all three tables to verify consistency
SELECT 
  v.id AS vnext_id,
  v.name AS vnext_name,
  v.slug AS vnext_slug,
  v.game_id AS vnext_game_id,
  v.region AS vnext_region,
  m.legacy_team_id,
  m.verified AS mapping_verified,
  l.id AS legacy_id,
  l.name AS legacy_name,
  l.slug AS legacy_slug,
  l.game AS legacy_game,
  l.region AS legacy_region
FROM organizations_team v
INNER JOIN organizations_teammigrationmap m ON v.id = m.vnext_team_id
INNER JOIN teams_team l ON m.legacy_team_id = l.id
WHERE v.id = 123;

-- Expected: 1 row with:
-- - vnext_name = legacy_name
-- - vnext_slug = legacy_slug  
-- - vnext_game_id = legacy_game (or mapped equivalent)
-- - vnext_region = legacy_region
-- - mapping_verified = true
```

**If No Mapping Found:**
```sql
-- Check if team exists in vNext but not mapped
SELECT id, name, slug FROM organizations_team WHERE id = 123;

-- Check if dual-write hook failed (check logs)
-- Then manually verify with: python manage.py vnext_validation_report --sample-size=1
```

✅ **Checkpoint:** All three tables have matching records, mapping is verified.

### 3.4 Test Flow 2: Add Team Member

**Via API:**

```bash
# Use TEAM_SLUG from Flow 1
curl -X POST https://staging.deltacrown.gg/api/vnext/teams/${TEAM_SLUG}/members/add/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_lookup": "testmember",
    "role": "PLAYER",
    "is_active": true
  }' | tee "${ARTIFACTS_DIR}/logs/flow2_member_add_response.json" | jq '.'

# Save membership_id
MEMBERSHIP_ID=$(jq -r '.membership_id' "${ARTIFACTS_DIR}/logs/flow2_member_add_response.json")
echo "Created membership: ${MEMBERSHIP_ID}"
```

**Expected Response (200):**
```json
{
  "success": true,
  "membership_id": 789,
  "member": {
    "id": 789,
    "user_id": 101,
    "username": "testmember",
    "role": "PLAYER",
    "status": "ACTIVE"
  }
}
```

**Via UI:**
1. Navigate to team detail page: https://staging.deltacrown.gg/organizations/teams/${TEAM_SLUG}/
2. Scroll to "Members" section
3. Click "Add Member" button
4. Fill form:
   - Username or Email: "testmember"
   - Role: Select "Player"
   - Active: Check checkbox
5. Click "Add" button
6. Verify member appears in list with "Player" role
7. Note membership_id from DOM or DevTools Network response

**Verify Logs:**
```bash
kubectl logs deployment/deltacrown-web -n deltacrown --since=5m | \
  grep -E "team_member_added|dual_write_scheduled.*membership_id=${MEMBERSHIP_ID}"
```

**Expected:**
```
INFO ... event_type=team_member_added membership_id=789 team_slug=staging-test-team-alpha
INFO ... event_type=dual_write_scheduled operation=sync_team_member_added membership_id=789
```

**Verify Database:**
```sql
-- Check vNext membership
SELECT 
  id,
  team_id,
  user_id,
  role,
  status,
  created_at
FROM organizations_teammembership
WHERE id = 789;

-- Expected: 1 row with role='PLAYER', status='ACTIVE'

-- Check legacy membership (via mapping)
SELECT 
  tm.id AS legacy_membership_id,
  tm.team_id AS legacy_team_id,
  tm.user_id,
  tm.role,
  tm.status,
  v.id AS vnext_membership_id,
  v.role AS vnext_role
FROM teams_teammembership tm
INNER JOIN organizations_teammembership v ON tm.user_id = v.user_id
WHERE tm.team_id = (
  SELECT legacy_team_id 
  FROM organizations_teammigrationmap 
  WHERE vnext_team_id = (SELECT team_id FROM organizations_teammembership WHERE id = 789)
)
AND v.id = 789;

-- Expected: 1 row with matching user_id, role
```

✅ **Checkpoint:** Both vNext and legacy membership records exist with correct role.

### 3.5 Test Flow 3: Update Member Role

```bash
# Update member role
curl -X POST https://staging.deltacrown.gg/api/vnext/teams/staging-test-team-alpha/members/789/role/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "SUBSTITUTE"
  }' | jq '.'
```

**Expected Response (200):**
```json
{
  "success": true,
  "member": {
    "id": 789,
    "role": "SUBSTITUTE",
    ...
  }
}
```

**Verify Logs:**
```
INFO ... event_type=team_member_role_updated membership_id=789
INFO ... event_type=dual_write_scheduled operation=sync_team_member_updated membership_id=789
```

**Verify Database:**
```sql
-- Check vNext role updated
SELECT id, role FROM organizations_teammembership WHERE id = 789;
-- Expected: role = 'SUBSTITUTE'

-- Check legacy role updated
SELECT id, role FROM teams_teammembership 
WHERE id = (SELECT legacy_team_id FROM organizations_teammigrationmap WHERE vnext_team_id = 123)
AND user_id = (SELECT user_id FROM organizations_teammembership WHERE id = 789);
-- Expected: role = 'SUBSTITUTE' or equivalent legacy value
```

✅ **Checkpoint:** Both vNext and legacy roles updated.

### 3.6 Test Flow 4: Update Team Settings

```bash
# Update team settings
curl -X POST https://staging.deltacrown.gg/api/vnext/teams/staging-test-team-alpha/settings/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "region": "EU",
    "description": "Updated via dual-write test",
    "logo_url": "https://cdn.example.com/updated.png"
  }' | jq '.'
```

**Expected Response (200):**
```json
{
  "success": true,
  "team": {
    "id": 123,
    "region": "EU",
    "description": "Updated via dual-write test",
    ...
  }
}
```

**Verify Logs:**
```
INFO ... event_type=team_settings_updated team_id=123
INFO ... event_type=dual_write_scheduled operation=sync_team_settings_updated team_id=123
```

**Verify Database:**
```sql
-- Check vNext settings
SELECT id, region, description, branding->>'logo_url' as logo
FROM organizations_team WHERE id = 123;

-- Check legacy settings
SELECT id, region, description, logo_url
FROM teams_team 
WHERE id = (SELECT legacy_team_id FROM organizations_teammigrationmap WHERE vnext_team_id = 123);
```

✅ **Checkpoint:** Settings updated in both vNext and legacy.

### 3.7 Test Flow 5: Remove Team Member

```bash
# Remove member
curl -X POST https://staging.deltacrown.gg/api/vnext/teams/staging-test-team-alpha/members/789/remove/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'
```

**Expected Response (200):**
```json
{
  "success": true,
  "members": [...]
}
```

**Verify Logs:**
```
INFO ... event_type=team_member_removed membership_id=789
INFO ... event_type=dual_write_scheduled operation=sync_team_member_removed membership_id=789
```

**Verify Database:**
```sql
-- Check vNext membership status
SELECT id, status FROM organizations_teammembership WHERE id = 789;
-- Expected: status = 'INACTIVE' or deleted

-- Check legacy membership status
-- (Depends on implementation: might be soft-deleted or status updated)
```

✅ **Checkpoint:** Member removed/inactivated in both systems.

---

## Phase 4: Validation Report (After) + Delta Analysis

**Objective:** Measure delta after dual-write testing and generate summary.

### 4.1 Run Validation Report (After)

```bash
# Get pod name
POD_NAME=$(kubectl get pods -n deltacrown -l app=deltacrown-web -o jsonpath='{.items[0].metadata.name}')

# SSH into staging pod
kubectl exec -it ${POD_NAME} -n deltacrown -- bash

# Inside pod: Run validation report (text format)
python manage.py vnext_validation_report --sample-size=100 > /tmp/validation_after.txt
cat /tmp/validation_after.txt

# Inside pod: Run validation report (JSON format)
python manage.py vnext_validation_report --format=json --sample-size=100 > /tmp/validation_after.json
```

### 4.2 Copy Reports to Artifacts Directory

```bash
# Exit pod (Ctrl+D or type 'exit')

# Copy after reports to artifacts
kubectl cp ${POD_NAME}:/tmp/validation_after.txt "${ARTIFACTS_DIR}/after/validation_after.txt" -n deltacrown
kubectl cp ${POD_NAME}:/tmp/validation_after.json "${ARTIFACTS_DIR}/after/validation_after.json" -n deltacrown

# OR for docker-compose
CONTAINER_ID=$(docker-compose -f docker-compose.staging.yml ps -q web)
docker cp ${CONTAINER_ID}:/tmp/validation_after.txt "${ARTIFACTS_DIR}/after/validation_after.txt"
docker cp ${CONTAINER_ID}:/tmp/validation_after.json "${ARTIFACTS_DIR}/after/validation_after.json"

# Verify files exist
ls -lh "${ARTIFACTS_DIR}/after/"
```

### 4.3 Run Automated Delta Analysis

```bash
# Use staging_validation_test.py script to compute delta
python scripts/staging_validation_test.py \
  --env=staging-k8s \
  --out-dir="${ARTIFACTS_DIR}" \
  --before="${ARTIFACTS_DIR}/baseline/validation_before.json" \
  --after="${ARTIFACTS_DIR}/after/validation_after.json"

# Script will generate:
# - ${ARTIFACTS_DIR}/delta.json (computed differences)
# - ${ARTIFACTS_DIR}/delta.md (human-readable markdown)
# - ${ARTIFACTS_DIR}/SUMMARY.md (copy/paste for tracker)
```

### 4.4 Review Delta Summary

```bash
# View markdown delta report
cat "${ARTIFACTS_DIR}/delta.md"

# Key metrics to verify:
# - vNext Teams Delta: +N (teams created during testing)
# - Mapped Teams Delta: +N (same as vNext teams - proves dual-write worked)
# - Mapping Coverage Delta: +X% or 0% (if already at 100%)
# - Duplicate IDs: Should remain 0
# - Orphan Mappings: Should remain 0 or decrease

# View full summary (for tracker update)
cat "${ARTIFACTS_DIR}/SUMMARY.md"
```

**Expected Delta:**
- `vnext_team_count`: +1 to +5 (depending on test flows executed)
- `mapped_team_count`: Same as vnext_team_count (proves dual-write successful)
- `mapping_percentage`: Increase (if was <100%) or stay at 100%
- `dual_write_health`: Should now be present with `recent_vnext_teams` > 0
- `missing_legacy_count`: Should be 0 (all test teams have legacy shadows)

✅ **Checkpoint:** Coverage percentage increased, dual-write health section present, no missing legacy shadows.

---

## Phase 5: Performance Validation

**Objective:** Confirm no performance regressions from dual-write hooks.

### 5.1 Sample API Endpoint Latencies

```bash
# Sample team creation endpoint (20 requests)
for i in {1..20}; do
  START=$(date +%s%N)
  curl -s -X POST https://staging.deltacrown.gg/api/vnext/teams/create/ \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "Perf Test Team '$i'", "game_id": 1, "region": "NA"}' \
    > /dev/null
  END=$(date +%s%N)
  ELAPSED=$(( (END - START) / 1000000 ))
  echo "Request $i: ${ELAPSED}ms"
done | tee "${ARTIFACTS_DIR}/logs/latency_team_create.txt"

# Calculate average and p95
cat "${ARTIFACTS_DIR}/logs/latency_team_create.txt" | \
  awk '{print $3}' | sed 's/ms//' | \
  sort -n | \
  awk '{sum+=$1; values[NR]=$1} END {
    printf "Average: %.2fms\n", sum/NR;
    printf "P95: %.2fms\n", values[int(NR*0.95)]
  }'

# Expected: Average < 200ms, P95 < 500ms (adjust for your baseline)
```

### 5.2 Check Query Counts

```bash
# If Django Debug Toolbar or query logging enabled
# Navigate to: https://staging.deltacrown.gg/teams/create/
# Create 1 test team via UI
# Check debug toolbar "SQL" panel or logs

# Expected query pattern:
# - Request phase: ~5-10 queries (team creation, permissions, user lookup)
# - NO queries to teams_team or teams_teammembership during request
# - After commit: Legacy writes happen asynchronously (check logs)
```

### 5.3 Verify No Inline Legacy Writes

```bash
# Search logs for legacy table queries during request lifecycle
kubectl logs deployment/deltacrown-web -n deltacrown --since=10m | \
  grep -E "INSERT INTO teams_team|UPDATE teams_team" | \
  grep -v "dual_write"

# Expected: EMPTY (no inline legacy writes)
# All legacy writes should be tagged with "dual_write" context

# Verify on_commit hooks are executing
kubectl logs deployment/deltacrown-web -n deltacrown --since=10m | \
  grep "dual_write_scheduled"

# Expected: Multiple entries showing "dual_write_scheduled" for each vNext operation
```

### 5.4 Monitor Application Metrics (If APM Available)

```bash
# Check metrics dashboard (e.g., Datadog, New Relic, Prometheus)
# - Request duration p95/p99
# - Database connection pool usage
# - Error rate
# - Transaction commit duration

# Compare with baseline metrics (before dual-write enabled)
# Expected: < 10% increase in latency, no connection pool exhaustion
```

✅ **Checkpoint:** No significant latency increase, no inline legacy writes detected, on_commit hooks executing correctly.

---

## Phase 6: Failure Simulation (Optional)

**Objective:** Verify log-only behavior when strict mode is OFF.

### 6.1 Simulate Dual-Write Failure

**Option A: Temporarily break legacy database connection**

```bash
# Edit DualWriteSyncService to inject failure (dev only!)
# OR
# Temporarily revoke legacy DB access for staging app user

# Run team creation
# Expected: vNext request succeeds, logs show "dual_write_failed"
```

**Option B: Use feature flag to disable legacy writes**

```bash
# Temporarily set TEAM_VNEXT_LEGACY_WRITE_BLOCKED=true (if not already)
# This should be ON by default in Phase 5
# Dual-write should use bypass context to succeed
```

### 6.2 Verify Request Succeeds Despite Dual-Write Failure

```bash
# Check logs
kubectl logs deployment/deltacrown-web -n deltacrown | grep "dual_write_failed"

# Expected log:
ERROR ... event_type=dual_write_failed operation=sync_team_created exception_type=...
```

✅ **Checkpoint:** vNext request succeeded, failure logged, no crash.

---

## Phase 7: Rollback Procedures

**Objective:** Quick recovery if issues detected.

### 7.1 Disable Dual-Write (Emergency)

```bash
# Method A: Kubernetes ConfigMap
kubectl edit configmap deltacrown-config -n deltacrown
# Change:
#   TEAM_VNEXT_DUAL_WRITE_ENABLED: "false"
kubectl rollout restart deployment/deltacrown-web -n deltacrown

# Method B: Docker Compose
# Edit docker-compose.staging.yml
# Set: TEAM_VNEXT_DUAL_WRITE_ENABLED=false
docker-compose -f docker-compose.staging.yml restart web

# Method C: Environment file
# Edit .env.staging
# Set: TEAM_VNEXT_DUAL_WRITE_ENABLED=false
systemctl restart deltacrown-staging
```

### 7.2 Verify Flags Disabled

```bash
python manage.py shell -c "
from django.conf import settings
print(f'TEAM_VNEXT_DUAL_WRITE_ENABLED: {getattr(settings, \"TEAM_VNEXT_DUAL_WRITE_ENABLED\", False)}')
"
# Expected: False
```

### 7.3 Revert Database Changes (If Needed)

```sql
-- Delete test teams created during staging tests
DELETE FROM organizations_teammigrationmap WHERE vnext_team_id IN (123, ...);
DELETE FROM teams_team WHERE id IN (...);  -- Use legacy IDs from mapping
DELETE FROM organizations_team WHERE id IN (123, ...);

-- Verify cleanup
SELECT COUNT(*) FROM organizations_team WHERE name LIKE 'Staging Test Team%';
-- Expected: 0
```

✅ **Checkpoint:** Dual-write disabled, test data cleaned up.

---

## Phase 8: Documentation & Handoff

### 8.1 Update Tracker

Edit `Documents/Team & Organization/Execution/TEAM_ORG_VNEXT_TRACKER.md`:

- Mark P5-T6 as ✅ COMPLETED
- Document staging environment details
- Include before/after validation report summaries
- List any issues encountered and resolutions
- Confirm strict mode stayed OFF
- Recommend next task (likely Phase 6 unblock)

### 8.2 Create Incident Summary (If Issues)

If any unexpected behavior occurred:

```markdown
### P5-T6 Staging Testing - Incident Summary

**Issue:** [Description]
**Impact:** [Scope - how many teams/requests affected]
**Root Cause:** [Analysis]
**Resolution:** [How fixed]
**Prevention:** [Future safeguards]
**Rollback Executed:** [Yes/No - details]
```

### 8.3 Notify Stakeholders

- Engineering team: "P5-T6 staging dual-write testing complete, [SUCCESS/ISSUES]"
- Product team: "Phase 5 staging validation complete, ready for [next phase]"
- Ops team: "Staging environment flags updated, [performance impact]"

---

## Success Criteria

- [ ] Dual-write enabled in staging (ENABLED=true, STRICT_MODE=false)
- [ ] All 5 test flows executed successfully (team create, member add/update/remove, settings update)
- [ ] Logs show `dual_write_scheduled` for each operation
- [ ] Legacy shadow rows verified in database for all operations
- [ ] TeamMigrationMap entries created for new teams
- [ ] Validation report shows increased mapping coverage
- [ ] Dual-write health section appears in report (when enabled)
- [ ] No performance regressions detected (query count, latency)
- [ ] No inline legacy writes detected (all in on_commit hooks)
- [ ] Failure simulation succeeded (if executed): vNext request OK, failure logged
- [ ] Rollback procedure tested and documented
- [ ] Tracker updated with results

---

## Troubleshooting

### Issue: Flags Not Taking Effect

**Symptoms:** `dual_write_scheduled` logs not appearing

**Resolution:**
```bash
# Verify environment variables
env | grep TEAM_VNEXT

# Check Django settings
python manage.py shell -c "from django.conf import settings; print(vars(settings))" | grep TEAM_VNEXT

# Restart application (ensure config reload)
kubectl rollout restart deployment/deltacrown-web -n deltacrown
```

### Issue: Legacy Shadow Rows Not Created

**Symptoms:** TeamMigrationMap empty, legacy tables have no new rows

**Resolution:**
1. Check logs for `dual_write_failed` errors
2. Verify DualWriteSyncService has legacy DB access
3. Confirm `TEAM_VNEXT_LEGACY_WRITE_BLOCKED` bypass is working
4. Check transaction commit completed (no rollback)

```bash
# Check for errors
kubectl logs deployment/deltacrown-web | grep -A 10 "dual_write_failed"
```

### Issue: Performance Degradation

**Symptoms:** Request latency increased significantly

**Resolution:**
1. Check if legacy DB connection is slow
2. Verify on_commit hooks are not blocking
3. Check for N+1 queries in dual-write logic
4. Consider async dual-write (future task)

```bash
# Monitor request timing
kubectl logs deployment/deltacrown-web | grep "request_time"
```

### Issue: Strict Mode Accidentally Enabled

**Symptoms:** Requests failing when dual-write errors occur

**Resolution:**
```bash
# Immediately disable strict mode
kubectl edit configmap deltacrown-config -n deltacrown
# Set: TEAM_VNEXT_DUAL_WRITE_STRICT_MODE: "false"
kubectl rollout restart deployment/deltacrown-web
```

---

## Contact & Escalation

- **Primary Contact:** Engineering Lead (Phase 5 owner)
- **On-Call:** DevOps team (for staging infrastructure issues)
- **Escalation:** CTO (if critical staging issues blocking production path)

---

## Appendix A: Environment Variables Reference

| Variable | Value | Purpose |
|----------|-------|---------|
| `TEAM_VNEXT_DUAL_WRITE_ENABLED` | `true` | Enable dual-write to legacy tables |
| `TEAM_VNEXT_DUAL_WRITE_STRICT_MODE` | `false` | Log-only failures (safe) |
| `TEAM_VNEXT_LEGACY_WRITE_BLOCKED` | `true` | Block direct legacy writes (Phase 5 default) |
| `TEAM_VNEXT_ADAPTER_ENABLED` | `true` | Enable vNext routing |
| `TEAM_VNEXT_ROUTING_MODE` | `vnext_primary` | Route to vNext by default |
| `TEAM_VNEXT_FORCE_LEGACY` | `false` | Emergency legacy fallback |

---

## Appendix B: SQL Queries for Manual Verification

```sql
-- Count vNext teams
SELECT COUNT(*) as vnext_teams FROM organizations_team WHERE status = 'ACTIVE';

-- Count legacy teams
SELECT COUNT(*) as legacy_teams FROM teams_team WHERE is_active = true;

-- Count mappings
SELECT COUNT(*) as mappings FROM organizations_teammigrationmap;

-- Check mapping coverage
SELECT 
  (COUNT(DISTINCT otm.legacy_team_id)::float / COUNT(DISTINCT tt.id)::float * 100) as coverage_pct
FROM teams_team tt
LEFT JOIN organizations_teammigrationmap otm ON tt.id = otm.legacy_team_id
WHERE tt.is_active = true;

-- Find unmapped legacy teams
SELECT tt.id, tt.name, tt.slug, tt.game
FROM teams_team tt
LEFT JOIN organizations_teammigrationmap otm ON tt.id = otm.legacy_team_id
WHERE tt.is_active = true AND otm.id IS NULL;

-- Check recent dual-write activity (teams created in last 24h)
SELECT 
  ot.id as vnext_id,
  ot.name,
  ot.created_at,
  otm.legacy_team_id,
  tt.id as legacy_id_check,
  tt.created_at as legacy_created_at
FROM organizations_team ot
LEFT JOIN organizations_teammigrationmap otm ON ot.id = otm.vnext_team_id
LEFT JOIN teams_team tt ON otm.legacy_team_id = tt.id
WHERE ot.created_at > NOW() - INTERVAL '24 hours'
ORDER BY ot.created_at DESC;
```

---

## Appendix C: Validation Report Interpretation

### Coverage Section
- **Mapping Coverage < 100%**: Legacy teams exist without vNext mappings (expected in Phase 5)
- **Unmapped Legacy Count > 0**: Number of legacy teams not yet migrated (run migration scripts)

### Mapping Health Section
- **Duplicate Legacy IDs > 0**: CRITICAL - same legacy team mapped to multiple vNext teams
- **Duplicate vNext IDs > 0**: CRITICAL - same vNext team mapped to multiple legacy teams
- **Orphan Mappings > 0**: WARNING - mappings pointing to deleted teams

### Consistency Section
- **Name/Slug Mismatches**: Data drift between legacy and vNext (investigate)
- **Membership Count Mismatches**: Different roster sizes (might be expected if migrations incomplete)
- **Ranking Mismatches**: One system has rankings, other doesn't (migration gap)

### Dual-Write Health Section (Only When Enabled)
- **Recent vNext Teams**: Count of teams created in last 24h
- **Missing Legacy Count**: vNext teams without legacy shadows (dual-write failures)
- **Severity = ERROR**: Strict mode ON, failures blocked requests
- **Severity = WARNING**: Strict mode OFF, failures logged only

### Recommendations Section
- **🔴 CRITICAL**: Blocking issues for production launch
- **🟡 WARNING**: Non-blocking but should be addressed
- **✅ SUCCESS**: All checks passed, ready for next phase

---

**End of Runbook**
