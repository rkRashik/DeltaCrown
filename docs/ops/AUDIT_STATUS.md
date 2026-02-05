# Team Create Audit Implementation Status

**Date**: 2026-02-05  
**Mode**: AUDIT-FIRST (Evidence-Based Diagnosis)  
**Status**: ⏸️ WAITING FOR EVIDENCE

---

## What Was Implemented

### ✅ PHASE 1: Frontend Runtime Truth Overlay

**File**: `templates/organizations/team/team_create.html`

**Changes Applied**:
1. **Line 1**: Added template signature comment
   ```django
   {# TEAM_CREATE_TEMPLATE_SIG=vNext-2026-02-05-A #}
   ```

2. **Lines 807-970**: Added debug overlay system with:
   - Template/Script signature tracking
   - Initialization state monitoring
   - Listener count tracking
   - Validation state visualization
   - Last response preview (first 200 chars)
   - Error trap integration
   - Triggered by `?debug=1` query param or Django DEBUG mode

3. **Console Logging**: Boot signature logged:
   ```javascript
   console.log(`[TEAM_CREATE_BOOT] SIG=${SCRIPT_SIG} TEMPLATE=${TEMPLATE_SIG} INIT=starting`);
   console.log(`[TEAM_CREATE_BOOT] SIG=${SCRIPT_SIG} TEMPLATE=${TEMPLATE_SIG} INIT=complete LISTENERS=${count}`);
   ```

4. **Global Error Traps**:
   - `window.addEventListener('error', ...)` → captures syntax/runtime errors
   - `window.addEventListener('unhandledrejection', ...)` → captures promise rejections
   - Both write to overlay's "Last Error" section

**Verification Method**:
- Visit `/teams/create/?debug=1`
- Overlay should appear top-right with cyan border
- Console should show `[TEAM_CREATE_BOOT]` lines

---

### ⚠️ PHASE 2: Response Echo Instrumentation (PARTIAL)

**File**: `templates/organizations/team/team_create.html`

**Status**: Overlay infrastructure added, but fetch instrumentation NOT YET COMPLETE due to duplicate script blocks in file.

**Known Issue**: File contains duplicate validation functions at:
- Lines 1264 (validate-name fetch)
- Lines 2260 (validate-name fetch - duplicate)
- Lines 1586 (create POST)
- Lines 2647 (create POST - duplicate)

**Required**: Must locate and instrument ALL fetch calls to log:
- Request URL
- HTTP status
- Response headers (especially X-TeamsVNext-*)
- Response body (first 200 chars or full JSON)
- Write to overlay via `debugOverlay.logResponse(endpoint, status, data)`

**Manual Steps Required**:
1. Identify why duplicate script blocks exist
2. Remove duplicates OR instrument both
3. Add logging to each fetch:
   ```javascript
   console.log(`[VALIDATE_NAME] URL: ${url}`);
   console.log(`[VALIDATE_NAME] Status: ${response.status}`);
   console.log(`[VALIDATE_NAME] Headers:`, Object.fromEntries(response.headers.entries()));
   const data = await response.json();
   console.log(`[VALIDATE_NAME] Response:`, data);
   debugOverlay.logResponse('validate-name', response.status, data);
   ```

---

### ❌ PHASE 3: Backend Truth Headers (NOT APPLIED)

**File**: `apps/organizations/api/views/__init__.py`

**Status**: UUID import added (line 2), but headers NOT added to Response() calls yet.

**Required Changes** (see `scripts/audit_instrumentation_patterns.py` for exact code):

1. **validate_team_name** (~line 465):
   ```python
   return Response({...}, headers={
       'X-TeamsVNext-Sig': 'api-2026-02-05-A',
       'X-TeamsVNext-Endpoint': 'validate-name',
       'X-TeamsVNext-TraceId': str(uuid.uuid4())[:8]
   })
   ```

2. **validate_team_tag** (~line 575):
   ```python
   return Response({...}, headers={
       'X-TeamsVNext-Sig': 'api-2026-02-05-A',
       'X-TeamsVNext-Endpoint': 'validate-tag',
       'X-TeamsVNext-TraceId': str(uuid.uuid4())[:8]
   })
   ```

3. **check_team_ownership** (~line 670-675, both returns):
   ```python
   return Response({...}, headers={
       'X-TeamsVNext-Sig': 'api-2026-02-05-A',
       'X-TeamsVNext-Endpoint': 'ownership-check',
       'X-TeamsVNext-TraceId': str(uuid.uuid4())[:8]
   })
   ```

4. **create_team** success response (~line 1050):
   ```python
   return Response({...}, status=201, headers={
       'X-TeamsVNext-Sig': 'api-2026-02-05-A',
       'X-TeamsVNext-Endpoint': 'team-create',
       'X-TeamsVNext-TraceId': str(uuid.uuid4())[:8]
   })
   ```

**Why Not Applied**: Multi-replace tool failed due to duplicate matches and context ambiguity. Requires manual application or more surgical search/replace.

---

## Files Changed

| File | Lines | Status | Purpose |
|------|-------|--------|---------|
| `templates/organizations/team/team_create.html` | 1, 807-970 | ✅ Partial | Template signature + debug overlay |
| `apps/organizations/api/views/__init__.py` | 2 | ✅ Partial | UUID import added, headers NOT added |
| `docs/ops/TEAM_CREATE_AUDIT_CHECKLIST.md` | NEW | ✅ Complete | Evidence collection protocol for RK |
| `scripts/audit_instrumentation_patterns.py` | NEW | ✅ Complete | Backend header patterns (reference) |

---

## What RK Must Do Next

### Step 1: Visit Page with Debug Mode
**URL**: `http://localhost:8000/teams/create/?debug=1`

**Expected**: Cyan-bordered overlay appears top-right

**If NO overlay**: Check browser console for `[TEAM_CREATE_BOOT]` line

### Step 2: Open Browser DevTools Console (F12 → Console)

**Look for**:
```
[TEAM_CREATE_BOOT] SIG=vNext-2026-02-05-A TEMPLATE=vNext-2026-02-05-A INIT=starting
[OVERLAY] Debug overlay initialized
[TEAM_CREATE_BOOT] SIG=vNext-2026-02-05-A TEMPLATE=vNext-2026-02-05-A INIT=complete LISTENERS=XX
```

### Step 3: Copy/Paste Evidence to Checklist

Use `docs/ops/TEAM_CREATE_AUDIT_CHECKLIST.md` and fill in ALL sections:
- Phase 1: Overlay text
- Phase 2: Console boot signature
- Phase 3: Validation network logs
- Phase 4: Tag validation logs
- Phase 5: Ownership check logs
- Phase 6: Form submission logs
- Phase 7: DOM element verification
- Phase 8: Error trap output

### Step 4: Paste Evidence Back to Copilot

Once checklist is complete, paste the filled-in sections.

**DO NOT**: Run any scripts, migrations, or commands.  
**DO**: Only reload browser pages and copy/paste console output.

---

## High-Probability Root Cause Hypotheses (To Be Confirmed)

Based on historical evidence, these are the most likely culprits:

### A) Wrong Template Served (Cached/Different Path)
**Evidence Needed**:
- Template signature in overlay doesn't match expected `vNext-2026-02-05-A`
- Script signature missing or different
- Console shows no `[TEAM_CREATE_BOOT]` line

**If Confirmed**: Template caching issue or multiple template files in use

---

### B) Old Script Still Present (Duplicate Blocks)
**Evidence Needed**:
- Multiple `[TEAM_CREATE_BOOT]` lines in console
- Listener count > expected
- Validation functions fire twice for one keystroke

**If Confirmed**: File has duplicate script blocks (lines 1200-1600 and 2200-2600)

---

### C) DOM IDs Mismatch
**Evidence Needed**:
- Phase 7 results show `inputName exists: false`
- Validation functions log "element not found"
- Overlay shows `listenersAttached: 0`

**If Confirmed**: HTML markup IDs don't match JavaScript selectors

---

### D) Backend Returning Unexpected Schema
**Evidence Needed**:
- Validation response missing `available` field
- Response has `exists` instead of `available`
- `field_errors` structure different than expected

**If Confirmed**: Backend validation functions returning old schema format

---

### E) 409 Conflict Misinterpreted
**Evidence Needed**:
- POST returns 409
- Response has `error_code: "conflict_one_team_per_game"`
- But UI shows "name is taken" message (wrong field)

**If Confirmed**: Frontend not parsing `error_code` correctly, falling back to generic message

---

### F) Ownership Check Logic Incorrect
**Evidence Needed**:
- Ownership check returns `has_team: false`
- But database shows user DOES have active team
- Or: returns `has_team: true` but for wrong game

**If Confirmed**: Ownership query filters incorrect (role constants, game_id vs game FK, etc.)

---

### G) Service Worker / Aggressive Caching
**Evidence Needed**:
- Hard refresh (Ctrl+Shift+R) shows different signature
- Overlay appears after cache clear but not on first load
- Network tab shows `(disk cache)` for template requests

**If Confirmed**: Service worker or CDN caching stale template

---

### H) IntegrityError Not Properly Caught
**Evidence Needed**:
- POST returns 500 instead of 409
- Server logs show `IntegrityError` exception
- Response body is HTML error page, not JSON

**If Confirmed**: IntegrityError escaping transaction.atomic() or not caught by except clause

---

## Next Actions (Copilot)

**BLOCKED ON**: RK evidence collection

**Once evidence received**:
1. ✅ Identify actual signature in browser
2. ✅ Confirm which script version is executing
3. ✅ Analyze actual HTTP status codes and response bodies
4. ✅ Match error_code values to frontend message mapping
5. ✅ Identify exact mismatch (schema, field names, status codes)
6. ✅ Apply TARGETED fix to specific broken component
7. ✅ Add additional instrumentation if root cause still unclear

**Will NOT**:
- ❌ Claim "fixed" without evidence
- ❌ Make bulk changes without confirming root cause
- ❌ Ask RK to run commands/scripts

---

## Summary

**Audit instrumentation added**:
- ✅ Frontend template signature
- ✅ Frontend debug overlay (visible with ?debug=1)
- ✅ Frontend boot signature logging
- ✅ Frontend error traps
- ⚠️ Frontend fetch logging (PARTIAL - duplicate blocks issue)
- ⚠️ Backend response headers (UUID imported, headers NOT added yet)

**Evidence collection protocol documented**:
- ✅ `docs/ops/TEAM_CREATE_AUDIT_CHECKLIST.md` - Step-by-step checklist for RK
- ✅ `scripts/audit_instrumentation_patterns.py` - Backend header patterns

**Status**: ⏸️ WAITING FOR EVIDENCE

**Next Step**: RK must visit `/teams/create/?debug=1`, open console, and paste evidence from checklist.

