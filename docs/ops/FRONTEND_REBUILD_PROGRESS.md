# Frontend Rebuild Phase — Progress Report

**Date**: 2026-02-04  
**Status**: File cleanup complete, Journey 1 analyzed

---

## ✅ STEP 1: File System Cleanup — COMPLETE

### Files Archived (moved to docs/vnext/archive/templates/team_2026-02-04/)
1. `team_detail.html.backup`
2. `team_manage.backup_phase14.html`
3. `team_manage_vnext.backup.html`
4. `team_manage_vnext.html`

### Files Deleted
1. `partials/_demo_controller.html` (demo-only dev tool)
2. `partials/_body_legacy_fake.html` (1460 lines of hardcoded fake data)
3. `partials/_body_honest.html` (exact duplicate of _body.html)

### Final Clean Structure ✅
```
templates/organizations/team/
├── team_create.html (Journey 1 - CANONICAL)
├── team_detail.html (Journey 2 - CANONICAL)
├── team_manage_hq.html (Journey 3 - CANONICAL)
├── team_invites.html (Journey 4 - CANONICAL)
└── partials/
    ├── _body.html (Team detail body - real data)
    ├── _head_assets.html (CSS/fonts)
    ├── _scripts.html (JS utilities)
    └── _team_manage_hq_scripts.html (Team Manage HQ scripts)
```

**Result**: Clean, minimal structure with 4 canonical templates + 4 necessary partials.

---

## ✅ STEP 2: Journey 1 (Team Create) — Analysis Complete

### Current State Assessment

#### ✅ What's Working
1. **Real-time validation** correctly wired to vNext APIs:
   - `GET /api/vnext/teams/validate-name/` (line 851)
   - `GET /api/vnext/teams/validate-tag/` (line 894)
   - Debounced (300ms delay)
   - Proper error display with inline messages

2. **Form submission** correctly wired:
   - `POST /api/vnext/teams/create/` (line 1144)
   - FormData construction includes all fields
   - CSRF token included
   - File uploads supported (logo, banner)

3. **Error handling**:
   - Field-level errors mapped to wizard steps
   - Auto-navigation to error step
   - Inline error messages
   - Network error fallback

4. **Success redirect logic** present (lines 1159-1166):
   - Uses `data.team_url` from backend
   - Fallback to `/organizations/hub/`

5. **JS syntax**: No unclosed try/catch blocks detected ✅

#### ⚠️ Minor Issues Identified
1. **Help Modal**: Not implemented in template (not critical for core flow)
2. **Redirect targets**: Backend must return correct URLs:
   - Independent: `/teams/<slug>/`
   - Org team: `/orgs/<org_slug>/teams/<slug>/`

### API Integration Status
| Endpoint | Status | Usage |
|----------|--------|-------|
| `GET /api/vnext/teams/validate-name/` | ✅ Wired | Real-time validation (line 851) |
| `GET /api/vnext/teams/validate-tag/` | ✅ Wired | Real-time validation (line 894) |
| `POST /api/vnext/teams/create/` | ✅ Wired | Form submission (line 1144) |

### Verification Required
**Manual UI Testing** (RK to perform):
1. Navigate to `/teams/create/`
2. Select a game → verify no errors
3. Enter team name → verify real-time validation (debounced)
4. Enter team tag → verify real-time validation
5. Complete wizard steps → verify navigation
6. Submit form:
   - Verify loading state
   - Verify success redirect (check URL)
   - Verify error handling (try duplicate name)

**Expected Backend Response** (`POST /api/vnext/teams/create/`):
```json
{
  "ok": true,
  "team_url": "/teams/<slug>/",  // or "/orgs/<org>/teams/<slug>/"
  "team_slug": "example-slug"
}
```

**Error Response**:
```json
{
  "ok": false,
  "safe_message": "Failed to create team.",
  "field_errors": {
    "name": "Team name already exists.",
    "tag": "Tag is taken."
  }
}
```

---

## 🔄 STEP 3: Journey 3 (Team Manage HQ) — Ready for Analysis

### Next Actions
1. Read `team_manage_hq.html` (3127 lines)
2. Read `partials/_team_manage_hq_scripts.html` (270 lines)
3. Verify API wiring:
   - GET `/api/vnext/teams/<slug>/detail/`
   - POST `/api/vnext/teams/<slug>/members/add/`
   - POST `/api/vnext/teams/<slug>/members/<id>/role/`
   - POST `/api/vnext/teams/<slug>/members/<id>/remove/`
   - POST `/api/vnext/teams/<slug>/settings/`
4. Check for hardcoded/demo data
5. Verify error handling

---

## 📋 Remaining Work

### Journey 7: Hub (Priority 3)
- Locate template: `templates/organizations/hub/vnext_hub.html`
- Verify real data rendering (no fake teams)
- Check empty state logic
- Verify cache invalidation (10s TTL)

### Journey 8: Rankings (Priority 4)
- Redesign UI for clarity:
  - Global vs per-game distinction
  - "Points" terminology (not "score")
  - Game name/logo display
  - Filters (game, verified)
- Update templates:
  - `templates/competition/leaderboards/leaderboard_global.html`
  - `templates/competition/leaderboards/leaderboard_game.html`

### Journey 9: Admin (Priority 5)
- Answer: Why does TeamAdminProxy exist?
- Fix admin field display (names not IDs)
- Fix User admin URL (if broken)
- Make ranking admin functional (points adjustment, season reset)
- Surface membership event ledger (read-only inline)

---

## Summary

**File Cleanup**: ✅ Complete (7 files archived/deleted)  
**Journey 1 Analysis**: ✅ Complete (template is production-ready, needs manual UI verification)  
**Journey 3**: ⏳ Ready for analysis  
**Journeys 7/8/9**: ⏳ Pending

**No backend work performed** — Only UI integration analysis.

---

**Next Step**: Analyze Journey 3 (Team Manage HQ) template for API wiring and demo data.

