# Frontend Manual QA Pack (Required)

**Purpose**: Manual UI verification that cannot be automated.  
**Date**: 2026-02-04  
**Status**: Awaiting RK frontend verification

---

## IMPORTANT NOTE

**RK is NOT required to run backend commands or tests.**

This document is **ONLY** for manual frontend verification that cannot be automated.

Backend implementation is complete, code is reviewed, and automated tests exist. This QA focuses exclusively on user-facing UI flows.

---

## Frontend Manual QA Checklists

### 1. Team Manage HQ (Journey 3)

**URL**: `/teams/<team_slug>/manage/` or `/orgs/<org_slug>/teams/<team_slug>/manage/`

**Setup**:
- Create a test team (or use existing)
- Log in as team creator or manager

**Checklist**:

- [ ] **Open Team Manage**
  - Navigate to: `/teams/<test-team-slug>/manage/`
  - Expected: Page renders HQ template (`team_manage_hq.html`), no 500 error
  - Expected: Roster section shows current members

- [ ] **Add Member (username/email)**
  - Click "Add Member" button
  - Enter valid username or email
  - Submit form
  - Expected: Success message displayed (no full page refresh)
  - Expected: New member appears in roster immediately
  - Expected: TeamMembershipEvent created (JOINED event)

- [ ] **Change Role**
  - Click "Change Role" for a member
  - Select new role (e.g., PLAYER → COACH)
  - Submit
  - Expected: Success message displayed
  - Expected: Member's role updates in roster without refresh
  - Expected: TeamMembershipEvent created (ROLE_CHANGED event)

- [ ] **Remove Member**
  - Click "Remove" for a non-creator member
  - Confirm removal
  - Expected: Success message displayed
  - Expected: Member removed from active roster
  - Expected: TeamMembershipEvent created (REMOVED event)

- [ ] **Try to Remove Creator (must fail)**
  - Attempt to remove the team creator (`created_by` user)
  - Expected: Action blocked with error message
  - Expected: Creator remains in roster

- [ ] **Try to Assign OWNER Role (must fail)**
  - Attempt to change a member's role to OWNER
  - Expected: 400 error with validation message ("OWNER role not supported in vNext")

- [ ] **Update Team Settings**
  - Navigate to "Settings" section in Team Manage
  - Update tagline, accent color, or social URL
  - Submit
  - Expected: Success message displayed
  - Expected: Changes reflected immediately (no full refresh)

- [ ] **Error Presentation**
  - Try invalid action (e.g., add non-existent user)
  - Expected: Error shown inline (not full page error)
  - Expected: Form remains usable after error

**Pass Criteria**: All items checked, no full-page refresh bugs, inline error handling works

**QA Result**: [ ] PASS / [ ] FAIL  
**Notes**: _______________________________________________

---

### 2. Hub (Journey 7)

**URL**: `/teams/vnext/`

**Setup**:
- Ensure at least 1 existing team in database
- Prepare to create a new PUBLIC ACTIVE team

**Checklist**:

- [ ] **View Hub Before Team Creation**
  - Navigate to: `/teams/vnext/`
  - Expected: Page loads with existing teams (if any)
  - Expected: No 500 error, rankings preview renders

- [ ] **Create New Public Active Team**
  - Go to `/teams/create/`
  - Create a new PUBLIC ACTIVE team (note team name/slug)
  - Expected: Team created successfully

- [ ] **Verify Immediate Appearance in Hub**
  - Navigate back to: `/teams/vnext/`
  - Expected: New team appears in hub list **immediately** (within 10 seconds max)
  - Expected: No need to wait for long cache expiration

- [ ] **Refresh Behavior**
  - Refresh the hub page (`F5` or Ctrl+R)
  - Expected: Teams still visible, no empty list after refresh
  - Expected: Cache invalidation working (TTL=10s confirmed)

- [ ] **Roster Change Invalidates Cache**
  - Add or remove a member from a team
  - Navigate to `/teams/vnext/`
  - Expected: Hub cache invalidated, changes reflected within 10s

**Pass Criteria**: All items checked, new teams appear immediately, no stale empty lists

**QA Result**: [ ] PASS / [ ] FAIL  
**Notes**: _______________________________________________

---

### 3. Rankings (Journey 8)

**URL**: `/competition/rankings/` (global) and `/competition/rankings/<game_id>/` (per-game)

**Setup**:
- Ensure at least 1 team with snapshot data (non-zero score)
- Create 1 team with **no snapshot** (0-point team)
- Optionally: Create 2 teams with same score (test tie-breaker)

**Checklist**:

- [ ] **View Global Rankings**
  - Navigate to: `/competition/rankings/`
  - Expected: Page loads without error
  - Expected: All teams displayed (including 0-point teams)

- [ ] **Verify 0-Point Team Appears**
  - Locate team with no snapshot data
  - Expected: Team appears in rankings with:
    - Score: 0
    - Status: UNRANKED
    - No crash or missing team

- [ ] **Verify Ordering Stability**
  - Check team order: score DESC, created_at DESC, name ASC
  - If 2 teams have same score and created_at, check alphabetical name order
  - Expected: Deterministic ordering (3-level tie-breaker)

- [ ] **Per-Game Rankings**
  - Navigate to: `/competition/rankings/<game_id>/` (e.g., `/competition/rankings/1/`)
  - Expected: Page loads without error
  - Expected: Game-specific rankings include 0-point teams

- [ ] **Verified Filter**
  - If "verified only" filter exists, toggle it
  - Expected: Only teams with games_played >= 5 shown
  - Expected: Filter derives from snapshot data (not legacy TeamRanking)

**Pass Criteria**: All items checked, 0-point teams visible, ordering deterministic, no crashes

**QA Result**: [ ] PASS / [ ] FAIL  
**Notes**: _______________________________________________

---

### 4. Admin Stability (Journey 9)

**URL**: `/admin/`

**Setup**:
- Log in as superuser or staff user with admin access
- Ensure at least 1 team and 1 organization exist in database

**Checklist**:

- [ ] **Open Team Admin Changelist**
  - Navigate to: `/admin/organizations/team/`
  - Expected: Page loads without `FieldError`
  - Expected: Team list displays with `created_by` column (not `owner`)

- [ ] **Open Team Change Page**
  - Click on a team to edit
  - Navigate to: `/admin/organizations/team/<id>/change/`
  - Expected: Page loads without `FieldError`
  - Expected: No references to `owner_link` in displayed fields

- [ ] **Open Organization Admin Changelist**
  - Navigate to: `/admin/organizations/organization/`
  - Expected: Page loads without error
  - Expected: Organization list displays correctly

- [ ] **Open Organization Change Page**
  - Click on an organization to edit
  - Navigate to: `/admin/organizations/organization/<id>/change/`
  - Expected: Page loads without error

- [ ] **Verify No Legacy Owner References**
  - Check all admin pages for any mention of "owner_link" or "team.owner"
  - Expected: No legacy field references in runtime admin views

**Pass Criteria**: All items checked, no FieldError on any admin page, legacy owner references absent

**QA Result**: [ ] PASS / [ ] FAIL  
**Notes**: _______________________________________________

---

## After Manual QA Completion

Once **ALL** frontend checklist items are marked **PASS**:

Copilot may update `docs/vnext/TEAM_ORG_VNEXT_MASTER_TRACKER.md`:
- **Journey 3** → COMPLETE ✅
- **Journey 7** → COMPLETE ✅
- **Journey 8** → COMPLETE ✅
- **Journey 9** → COMPLETE ✅

No additional backend work is permitted at that stage.

After status flip, proceed to remaining Journeys (1, 2, 4, 5, 6) for UI completion.

---

**End of Frontend Manual QA Pack**
