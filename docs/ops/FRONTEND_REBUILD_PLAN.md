# Frontend Rebuild Phase — File System Cleanup Plan

**Date**: 2026-02-04  
**Phase**: Frontend UI Integration & Cleanup

---

## STEP 1: Template File Classification

### ✅ CANONICAL (Keep & Clean)
- `team_create.html` — Journey 1: Team Create
- `team_detail.html` — Journey 2: Team Detail  
- `team_manage_hq.html` — Journey 3: Team Manage HQ
- `team_invites.html` — Journey 4: Invites (secondary)

### ❌ BACKUP/LEGACY (Archive to backups/)
- `team_detail.html.backup` — Old backup
- `team_manage.backup_phase14.html` — Old backup
- `team_manage_vnext.backup.html` — Old backup
- `team_manage_vnext.html` — Superseded by team_manage_hq.html

### ❌ PARTIALS - LEGACY/DEMO (Delete)
- `partials/_demo_controller.html` — **DELETE** (demo-only dev tool)
- `partials/_body_legacy_fake.html` — **DELETE** (1460 lines of fake data)
- `partials/_body_honest.html` — **DELETE** (duplicate of _body.html, identical content)

### ✅ PARTIALS - CANONICAL (Keep & Clean)
- `partials/_body.html` — Team detail body (real data, no demo)
- `partials/_head_assets.html` — Head assets partial
- `partials/_scripts.html` — Scripts partial
- `partials/_team_manage_hq_scripts.html` — Team Manage HQ scripts

---

## STEP 2: Cleanup Actions

### 2.1 Archive Legacy Files
```
Move to: docs/vnext/archive/templates/team_2026-02-04/

Files:
- team_detail.html.backup
- team_manage.backup_phase14.html
- team_manage_vnext.backup.html
- team_manage_vnext.html
```

### 2.2 Delete Demo/Fake Files
```
DELETE:
- templates/organizations/team/partials/_demo_controller.html
- templates/organizations/team/partials/_body_legacy_fake.html
- templates/organizations/team/partials/_body_honest.html (exact duplicate of _body.html)
```

### 2.3 Final Directory Structure
```
templates/organizations/team/
├── team_create.html (CANONICAL - Journey 1)
├── team_detail.html (CANONICAL - Journey 2)
├── team_manage_hq.html (CANONICAL - Journey 3)
├── team_invites.html (CANONICAL - Journey 4)
└── partials/
    ├── _body.html (Team detail body, real data)
    ├── _head_assets.html (CSS/fonts)
    ├── _scripts.html (JS utilities)
    └── _team_manage_hq_scripts.html (Team Manage JS)
```

---

## STEP 3: Journey 1 — Team Create (Priority 1)

### Current Issues Identified
1. **JS Syntax Error** — Unclosed try/catch/finally blocks
2. **Validation** — Not wired to real vNext APIs
3. **Submit** — Not using POST `/api/vnext/teams/create/`
4. **Help Modal** — Broken (won't open/render)
5. **Error Handling** — Silent failures, no inline errors

### Required Fixes
1. Fix JS syntax (close try/catch blocks properly)
2. Wire real-time validation:
   - `GET /api/vnext/teams/validate-name/?name=<value>`
   - `GET /api/vnext/teams/validate-tag/?tag=<value>`
3. Wire form submit to `POST /api/vnext/teams/create/`
4. Implement inline error display (field-level + form-level)
5. Fix help modal functionality
6. Implement success redirect logic:
   - Independent team → `/teams/<slug>/`
   - Org team → `/orgs/<org_slug>/teams/<slug>/`

### API Endpoints Used
- `GET /api/vnext/teams/validate-name/`
- `GET /api/vnext/teams/validate-tag/`
- `POST /api/vnext/teams/create/`

---

## STEP 4: Journey 3 — Team Manage HQ (Priority 2)

### Current Issues
1. **Demo Controller** — Not present (good), but need to verify no demo data
2. **API Wiring** — Needs verification of real endpoints
3. **Roster Rendering** — Must use API data, not hardcoded
4. **Error Handling** — Must show inline errors

### Required Fixes
1. Verify GET `/api/vnext/teams/<slug>/detail/` integration
2. Verify POST member mutations (add/change/remove)
3. Verify POST settings mutations
4. Ensure all errors display inline
5. Verify no full-page refresh on actions

### API Endpoints Used
- `GET /api/vnext/teams/<slug>/detail/`
- `POST /api/vnext/teams/<slug>/members/add/`
- `POST /api/vnext/teams/<slug>/members/<id>/role/`
- `POST /api/vnext/teams/<slug>/members/<id>/remove/`
- `POST /api/vnext/teams/<slug>/settings/`

---

## STEP 5: Journey 7 — Hub UI (Priority 3)

### Current Issues
1. Hub template location unknown (need to verify)
2. Must render real teams from backend
3. Empty state only if truly no teams
4. Must show: team name, game, points, rank/UNRANKED

### Required Fixes
1. Locate hub template (`templates/organizations/hub/vnext_hub.html`)
2. Verify real data rendering (no fake/demo teams)
3. Implement proper empty state
4. Ensure cache invalidation working (10s TTL)

### API/View Used
- `apps/organizations/views/hub.py::vnext_hub`
- Cache: `featured_teams_{game_id}_{limit}` (10s TTL)

---

## STEP 6: Journey 8 — Rankings Redesign (Priority 4)

### Current Issues
1. Unclear if global vs per-game rankings are separated
2. "Score" vs "Points" terminology
3. No clear game indication in UI
4. Filters may be unclear

### Required Redesign
1. Create clear UI distinction:
   - Global rankings (all games)
   - Per-game rankings (single game)
2. Use "Points" terminology (not "score")
3. Show game name/logo prominently
4. Implement filters: game, verified teams
5. Show UNRANKED for 0-point teams
6. Ensure 3-level ordering visible (score DESC, created_at DESC, name ASC)

### Templates to Update
- `templates/competition/leaderboards/leaderboard_global.html`
- `templates/competition/leaderboards/leaderboard_game.html`

### Service Used
- `apps/competition/services/competition_service.py`
- LEFT JOIN with Coalesce defaults (includes 0-point teams)

---

## STEP 7: Admin Rationalization (Priority 5)

### Questions to Answer
1. **Why does TeamAdminProxy exist?** (vs just TeamAdmin)
2. **Should we keep it or remove it?**
3. **Why is User admin URL broken?** (needs fix)

### Required Fixes
1. Fix admin field display (show names, not raw IDs)
2. Fix User admin URL (if broken)
3. Make ranking admin functional:
   - Adjust points
   - Reset season
   - Apply penalties
4. Surface membership event ledger in admin (read-only inline)

### Admin Classes to Review
- `apps/organizations/admin.py::TeamAdmin` (line 221-290)
- `apps/organizations/admin.py::TeamAdminProxy` (if exists)
- `apps/organizations/admin.py::OrganizationAdmin` (line 88-218)

---

## Execution Order

1. **File Cleanup** (this doc) — Archive/delete legacy files
2. **Journey 1: Team Create** — Fix JS, wire APIs, test flow
3. **Journey 3: Team Manage HQ** — Verify API wiring, test mutations
4. **Journey 7: Hub** — Verify real data, test cache
5. **Journey 8: Rankings** — Redesign UI, clarify modes
6. **Journey 9: Admin** — Fix fields, add ledger inline

---

**Next Action**: Execute file cleanup, then start Journey 1 rebuild.

**No backend work** — Only UI integration and cleanup.

---

**End of Cleanup Plan**
