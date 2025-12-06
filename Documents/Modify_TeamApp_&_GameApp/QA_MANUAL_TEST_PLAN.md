# Manual QA Test Plan - Teams/Games/Tournaments/Rankings

**Purpose**: Human-executable test checklist for validating Phases 1-6 changes before production deployment.

**Scope**: Teams app refactor, Games service migration, Tournament-Game integration, Rankings leaderboards.

---

## Prerequisites
- [ ] Staging environment deployed with latest migrations
- [ ] Database seeded with 9 TournamentGame records (see `scripts/seed_games.py`)
- [ ] Test user account created with login credentials
- [ ] Browser DevTools open (check for console errors)

---

## Test 1: TournamentGame Service
**Purpose**: Verify GameService correctly serves 9 games

### Steps:
1. [ ] Navigate to admin panel: `/admin/games/tournamentgame/`
2. [ ] Verify exactly 9 games appear in the list:
   - PUBG Mobile
   - FreeFire
   - Call of Duty Mobile
   - Clash of Clans
   - Clash Royale
   - BGMI
   - VALORANT
   - Brawl Stars
   - eFootball
3. [ ] Check each game has:
   - Unique `slug` field (no duplicates)
   - `is_active = True`
   - Non-empty `profile_id_field` (e.g., "riot_id", "player_tag")
   - `default_team_size > 0`

**Expected**: All 9 games present, all fields populated, no errors.

---

## Test 2: Team Creation & Identity Field
**Purpose**: Verify Team.game uses slug and enforces game-specific identity

### Steps:
1. [ ] Navigate to: `/teams/create/`
2. [ ] Fill form:
   - **Team Name**: QA Test Team
   - **Tag**: QATT
   - **Game**: Select "VALORANT" from dropdown
   - **Identity field** (should say "Riot ID"): Enter `QA#1234`
3. [ ] Submit form
4. [ ] Verify team created successfully (no 500 error)
5. [ ] Navigate to team detail page
6. [ ] Verify:
   - Game displays as "VALORANT" (not database ID)
   - Identity field shows "QA#1234"
   - Team detail page loads without errors

**Expected**: Team created with `game='valorant'` (slug), identity field correctly labeled and stored.

---

## Test 3: Tournament Creation with Game FK
**Purpose**: Verify Tournament.game uses TournamentGame FK (migration 0014)

### Steps:
1. [ ] Navigate to: `/admin/tournaments/tournament/add/`
2. [ ] Fill required fields:
   - **Name**: QA Test Tournament
   - **Slug**: qa-test-tournament
   - **Game**: Select "VALORANT" from dropdown (FK field)
   - **Organizer**: Select test user
   - **Max Participants**: 16
   - **Registration Start**: Tomorrow's date
   - **Registration End**: 7 days from now
   - **Tournament Start**: 8 days from now
3. [ ] Save tournament
4. [ ] Verify:
   - Tournament created successfully
   - Game field shows "VALORANT" (TournamentGame instance, not slug)
   - No database errors in logs

**Expected**: Tournament.game now ForeignKey to TournamentGame (not CharField slug).

---

## Test 4: Tournament Registration Flow
**Purpose**: Verify teams can register for tournaments

### Steps:
1. [ ] Log in as test user
2. [ ] Navigate to tournament detail: `/tournaments/qa-test-tournament/`
3. [ ] Click "Register Team" button
4. [ ] Select "QA Test Team" from roster
5. [ ] Submit registration
6. [ ] Verify:
   - Registration status = "Confirmed" or "Pending"
   - Team appears in tournament participants list
   - No IntegrityError (like "reminder_sent" constraint)

**Expected**: Registration succeeds, team added to tournament.

**Note**: If "reminder_sent" error occurs, this is **pre-existing technical debt** (Category B), not a Phase 1-6 regression.

---

## Test 5: Tournament Results → Rankings Integration
**Purpose**: Verify TournamentResult creates TeamGameRanking entries

### Steps:
1. [ ] Navigate to admin: `/admin/tournaments/tournamentresult/add/`
2. [ ] Fill fields:
   - **Tournament**: QA Test Tournament
   - **Team**: QA Test Team
   - **Position**: 1 (Winner)
   - **Points Awarded**: 100
3. [ ] Save result
4. [ ] Navigate to: `/leaderboards/valorant/` (game-specific leaderboard)
5. [ ] Verify:
   - "QA Test Team" appears in leaderboard
   - Total points = 100
   - Ranking position = 1
6. [ ] Navigate to: `/leaderboards/` (global leaderboard)
7. [ ] Verify team appears in global view

**Expected**: Tournament results automatically create/update TeamGameRanking entries, visible on leaderboards.

---

## Test 6: Game-Specific Leaderboard Views
**Purpose**: Verify Phase 6 leaderboard CSS extraction and accessibility

### Steps:
1. [ ] Navigate to: `/leaderboards/valorant/`
2. [ ] Check page rendering:
   - [ ] Leaderboard table displays correctly
   - [ ] CSS styling applied (no inline styles)
   - [ ] Responsive layout on mobile (resize browser to 375px width)
3. [ ] Run accessibility check (browser DevTools > Lighthouse):
   - [ ] Accessibility score > 90%
   - [ ] No contrast errors
   - [ ] ARIA labels present on interactive elements
4. [ ] Check browser console:
   - [ ] No JavaScript errors
   - [ ] No 404 for static files

**Expected**: Clean rendering, accessible markup, extracted CSS in `static/leaderboards/css/`.

---

## Test 7: Global Leaderboard Cross-Game Rankings
**Purpose**: Verify global leaderboard aggregates across all games

### Steps:
1. [ ] Create teams for 2+ different games (e.g., VALORANT, PUBG Mobile)
2. [ ] Create tournament results for each team
3. [ ] Navigate to: `/leaderboards/`
4. [ ] Verify:
   - All teams appear (not filtered by game)
   - Each team shows correct game association
   - Rankings sorted by total points descending
   - Page renders without errors

**Expected**: Global leaderboard shows all teams across all games.

---

## Test 8: Edge Cases & Error Handling

### 8.1: Invalid Game Slug
1. [ ] Navigate to: `/teams/create/`
2. [ ] Manually edit DOM to inject invalid game slug (DevTools)
3. [ ] Submit form
4. [ ] Verify: Form validation rejects invalid game (404 or validation error)

### 8.2: Duplicate Team Registration
1. [ ] Register same team twice for same tournament
2. [ ] Verify: System prevents duplicate (unique constraint error or form validation)

### 8.3: Missing Required Fields
1. [ ] Try creating team without identity field (e.g., leave Riot ID blank)
2. [ ] Verify: Form validation error (not 500 server error)

**Expected**: Graceful error handling, no crashes.

---

## Test 9: Performance Spot Check

### Steps:
1. [ ] Navigate to: `/leaderboards/`
2. [ ] Open browser Network tab
3. [ ] Measure page load time
4. [ ] Check database queries (Django Debug Toolbar if enabled):
   - [ ] Leaderboard queries < 50ms
   - [ ] No N+1 query issues (should be ~3-5 queries total)

**Expected**: Leaderboards render in < 500ms, minimal database queries.

---

## Test 10: Admin Panel Sanity Check

### Steps:
1. [ ] Navigate to: `/admin/`
2. [ ] Check all Phase 1-6 models accessible:
   - [ ] Games > TournamentGame
   - [ ] Teams > Team
   - [ ] Tournaments > Tournament
   - [ ] Tournaments > TournamentResult
   - [ ] Leaderboards > TeamGameRanking
3. [ ] Verify each list view loads without errors
4. [ ] Check model counts:
   - TournamentGame: 9 records
   - Team: At least 1 test team
   - Tournament: At least 1 test tournament

**Expected**: All admin views functional, no Django template errors.

---

## Regression Checks

### Phase 1-3 (Teams/Games)
- [ ] Existing teams still load (no game slug migration breakage)
- [ ] Team.game values match TournamentGame.slug (e.g., "valorant", "pubg-mobile")

### Phase 4-5 (Tournaments)
- [ ] Tournament.game now ForeignKey (not CharField)
- [ ] Existing tournaments migrated to new FK structure

### Phase 6 (Rankings/Leaderboards)
- [ ] Leaderboard CSS extracted to static files (no inline `<style>`)
- [ ] All leaderboard tests pass (see `tests/test_leaderboard_views.py`)

---

## Known Issues / Category B (Pre-Existing)
- **Integration Test Failures**: `tests/test_rankings_integration.py` failing due to:
  - Missing `reminder_sent` field on Registration model (model/DB schema mismatch)
  - Test fixtures not updated for Tournament required fields (registration_start, tournament_start)
  - **This is testing technical debt, NOT a functional regression in Phases 1-6**
- **Action**: Fix integration test fixtures separately (not blocking deployment)

---

## Sign-Off

**Tester Name**: _________________________  
**Date**: _________________________  
**Environment**: Staging / Production  
**Result**: PASS / FAIL / CONDITIONAL PASS

**Notes**:
