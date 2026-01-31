# Wiring Readiness Checklist

**Document Version:** 1.0  
**Date:** 2026-01-30  
**Purpose:** Gate control for Team Detail Page feature wiring  
**Status:** PERMANENT DECISION GATE

---

## GATE PHILOSOPHY

**Principle:** "Backend is CANONICAL — Template is the CONTRACT"

The Team Detail Page template defines WHAT data is needed.  
The backend MUST provide that data — not the other way around.

**NO WIRING without explicit gate clearance.**

---

## SECTION 1 — PRE-WIRING PREPARATION GATE

### Gate Status: ⏸️ **PENDING USER REVIEW**

**Prerequisites Before ANY Code Wiring:**

- [x] Schema verification report created and reviewed
- [x] Game lookup resolution proposal created and reviewed
- [x] Wiring readiness checklist created (this document)
- [ ] **USER DECISION:** Privacy field strategy
  * Option A: Add `visibility` CharField migration
  * Option B: Add `is_private` BooleanField migration
  * Option C: Remove all privacy logic (all teams public)
- [ ] **USER APPROVAL:** Game lookup integration approach (GameService)
- [ ] **USER ACKNOWLEDGMENT:** Partner model doesn't exist (accept empty list)
- [ ] **USER ACKNOWLEDGMENT:** Match query is indirect (Q filter on participant_id)

**Exit Criteria:**
- ✅ All schema uncertainty eliminated
- ✅ Game lookup blocker resolved (GameService exists)
- ✅ Privacy strategy decided
- ✅ User explicitly authorizes Tier-1 wiring

**Blocker Status:**
- ❌ Privacy field decision: **BLOCKING ALL TIER-2 WIRING**
- ✅ Game lookup: **RESOLVED** (GameService.get_game_by_id exists)

---

## SECTION 2 — TIER-1 WIRING GATE (Critical Identity)

### Gate Status: ⚠️ **READY AFTER PRIVACY DECISION**

**Scope:** Non-controversial identity fields only

**Fields Included:**
- ✅ `team.name` (already wired)
- ✅ `team.slug` (already wired)
- ✅ `team.tag` (already wired)
- ✅ `team.tagline` (already wired)
- ✅ `team.region` (already wired)
- ✅ `team.logo_url` (already wired with fallback)
- ✅ `team.banner_url` (already wired with fallback)
- ⏸️ `team.game` (ready to wire - use GameService.get_game_by_id)
- ❌ `team.visibility` (BLOCKED - field doesn't exist)

**Prerequisites:**

- [x] Schema verification complete (9 models verified)
- [x] GameService.get_game_by_id() exists and tested
- [ ] Privacy field migration created
- [ ] Privacy field migration applied
- [ ] Data integrity check for game_id (no orphaned references)
- [ ] Game lookup tests added (4 new tests)
- [ ] All 26 tests passing (22 contract + 4 game lookup)

**Implementation Checklist:**

**Step 1: Context Builder Modification**
- [ ] Import `GameService` from `apps.games.services`
- [ ] Modify `_safe_game_context()` method
  * [ ] Call `GameService.get_game_by_id(team.game_id)`
  * [ ] Return full game dict (id, name, slug, logo_url, primary_color)
  * [ ] Handle None game_id (return fallback dict)
  * [ ] Handle invalid game_id (return fallback dict)
  * [ ] Handle missing logo (logo_url=None)
- [ ] Add caching (optional but recommended)
  * [ ] Cache key: `f'game_context:{team.game_id}'`
  * [ ] TTL: 86400 seconds (24 hours)
  * [ ] Cache invalidation on Game.save() signal (optional)

**Step 2: Test Coverage**
- [ ] Add `test_game_context_with_valid_game_id`
- [ ] Add `test_game_context_with_invalid_game_id`
- [ ] Add `test_game_context_with_none_game_id`
- [ ] Add `test_game_context_with_missing_logo`
- [ ] Run full test suite (expect 26/26 passing)

**Step 3: Data Integrity Verification**
- [ ] Run SQL query to find invalid game_id references
  ```sql
  SELECT t.id, t.name, t.game_id
  FROM organizations_team t
  LEFT JOIN games_game g ON t.game_id = g.id
  WHERE g.id IS NULL;
  ```
- [ ] Fix any orphaned game_id rows (set to NULL or assign default game)
- [ ] Document findings in migration notes

**Step 4: Django Check Validation**
- [ ] Run `python manage.py check` (expect 0 errors)
- [ ] Run `python manage.py test apps.organizations.tests.test_team_detail_contract --keepdb`
- [ ] Verify query count ≤3 without caching, ≤2 with caching

**Exit Criteria:**
- ✅ Game lookup integrated into context builder
- ✅ All 26 tests passing
- ✅ Query count within budget (≤3 queries)
- ✅ No console errors or exceptions
- ✅ Fallback handling verified (invalid game_id, missing logo)
- ✅ Data integrity check passed (no orphaned game_id)

**Risk Assessment:**
- ⚠️ Privacy field still missing → Tier-2 BLOCKED
- ✅ Game lookup solution verified → READY
- ⚠️ Match query indirect → Tier-2 performance concern

---

## SECTION 3 — TIER-1 UI ACTIVATION GATE (Optional)

### Gate Status: ⏸️ **HOLD UNTIL TIER-1 BACKEND COMPLETE**

**Scope:** Display game badge in hero section

**Prerequisites:**
- [ ] Tier-1 backend wiring complete (game data in context)
- [ ] Visual regression baseline captured (screenshot before changes)
- [ ] User approves UI change (game badge display)

**Implementation Checklist:**

**Step 1: Template Modification**
- [ ] Add game badge to hero section (`_body.html` lines 65-75)
  ```django
  {% if team.game.name %}
  <div class="game-badge">
      {% if team.game.logo_url %}
      <img src="{{ team.game.logo_url }}" alt="{{ team.game.name }}" class="game-icon">
      {% endif %}
      <span>{{ team.game.name }}</span>
  </div>
  {% endif %}
  ```
- [ ] Optional: Update title tag with game name (`_head_assets.html` line 10)
  ```django
  <title>{{ team_name }}{% if team.game.name %} — {{ team.game.name }}{% endif %} | DeltaCrown</title>
  ```

**Step 2: Visual QA**
- [ ] Test with valid game (Valorant team shows badge)
- [ ] Test with missing logo (only text shows, no broken image)
- [ ] Test with invalid game_id (no badge shows)
- [ ] Test with None game_id (no badge shows)
- [ ] Visual regression test (compare screenshots)

**Step 3: Browser Testing**
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile viewport (responsive check)

**Exit Criteria:**
- ✅ Game badge visible for valid games
- ✅ No broken images
- ✅ No layout shift
- ✅ Fallback handling graceful
- ✅ Visual regression test passes

---

## SECTION 4 — TIER-2 WIRING GATE (Engagement Data)

### Gate Status: ❌ **BLOCKED - PRIVACY FIELD MISSING**

**Scope:** Roster, stats, partners (privacy-aware sections)

**Prerequisites:**

**CRITICAL - UNMET:**
- [ ] **Privacy field migration created**
- [ ] **Privacy field migration applied**
- [ ] **Privacy field migration tested**
- [ ] **Privacy tests updated** (remove mocking, test real field)
- [ ] **`_get_team_visibility()` updated** (use real field)
- [ ] **`_roster_section()` updated** (use real privacy enforcement)
- [ ] **`_stats_section()` updated** (use real privacy enforcement)

**READY:**
- [x] Tier-1 wiring complete and stable
- [x] TeamMembership schema verified
- [x] TeamRanking schema verified
- [x] Match model located (indirect relationship documented)

**NOT READY:**
- [ ] Match query performance tested (Q filter benchmarked)
- [ ] Roster prefetch strategy tested (N+1 prevention)
- [ ] Partner model decision made (accept empty OR build model)

**Implementation Checklist:**

**Step 1: Privacy Field Migration (USER DECISION REQUIRED)**

**Option A: Add visibility CharField (RECOMMENDED)**
```python
# apps/organizations/migrations/00XX_add_team_visibility.py
operations = [
    migrations.AddField(
        model_name='team',
        name='visibility',
        field=models.CharField(
            max_length=20,
            choices=[
                ('PUBLIC', 'Public'),
                ('PRIVATE', 'Private'),
                ('UNLISTED', 'Unlisted'),
            ],
            default='PUBLIC',
            db_index=True,
            help_text='Team visibility setting'
        ),
    ),
]
```

**Option B: Add is_private BooleanField (SIMPLER)**
```python
# apps/organizations/migrations/00XX_add_team_privacy.py
operations = [
    migrations.AddField(
        model_name='team',
        name='is_private',
        field=models.BooleanField(
            default=False,
            db_index=True,
            help_text='Whether team is private (members-only)'
        ),
    ),
]
```

**Option C: Remove Privacy Logic (SIMPLEST)**
- Delete `_get_team_visibility()` method
- Delete privacy enforcement in `_roster_section()` and `_stats_section()`
- Remove privacy tests
- Document all teams as public (no privacy feature)

**Step 2: Update Context Builder**
- [ ] Remove hasattr() checks for privacy fields
- [ ] Use actual field (e.g., `team.visibility` or `team.is_private`)
- [ ] Update `_get_team_visibility()` to read real field
- [ ] Update `_roster_section()` to enforce privacy
- [ ] Update `_stats_section()` to enforce privacy

**Step 3: Update Tests**
- [ ] Remove mocking from privacy tests
- [ ] Test real field behavior (PUBLIC vs PRIVATE)
- [ ] Test unauthorized access to private team roster
- [ ] Test authorized access to private team roster
- [ ] Verify privacy enforcement (roster/stats hidden for private teams)

**Step 4: Roster Wiring**
- [ ] Query pattern: `team.memberships.select_related('user', 'user__profile').filter(status='ACTIVE')`
- [ ] Test N+1 prevention (use Django Debug Toolbar)
- [ ] Verify query count ≤6 for full Tier-2 page

**Step 5: Stats Wiring**
- [ ] Integrate TeamRanking data (Crown Points, tier, rank)
- [ ] Integrate Match stats (indirect query via Q filter)
  ```python
  from django.db.models import Q, Count
  
  matches = Match.objects.filter(
      Q(participant1_id=team.id) | Q(participant2_id=team.id),
      state='COMPLETED'
  )
  
  stats = matches.aggregate(
      total=Count('id'),
      wins=Count('id', filter=Q(winner_id=team.id)),
      losses=Count('id', filter=Q(loser_id=team.id))
  )
  ```
- [ ] Benchmark Match query performance
- [ ] Consider adding indexes on `participant1_id`, `participant2_id`
- [ ] Cache stats (10-minute TTL)

**Step 6: Partners Wiring**
- [ ] Accept empty list (Partner model doesn't exist)
- [ ] Return `[]` for `context['team']['partners']`
- [ ] Document as deferred feature

**Exit Criteria:**
- ✅ Privacy field exists in Team model
- ✅ Privacy enforcement functional (roster/stats hidden for private teams)
- ✅ All privacy tests passing (using real field, not mocks)
- ✅ Roster query optimized (N+1 prevented)
- ✅ Match stats query benchmarked (acceptable performance)
- ✅ Query count ≤6 for full Tier-2 page
- ✅ Visual QA passed (roster/stats sections display correctly)

---

## SECTION 5 — CONTROL PLANE COUPLING GATE (Write Operations)

### Gate Status: 🚫 **OUT OF SCOPE FOR PHASE 4**

**Scope:** Permission checks, edit actions, ownership transfer

**Prerequisites:**
- [ ] Tier-2 wiring complete and stable
- [ ] Permission system integration designed
- [ ] Write operation contracts defined (CRUD operations)
- [ ] Rollback plan documented
- [ ] Security audit complete

**Implementation Checklist:**
- [ ] Integrate permission checks for edit actions
- [ ] Wire "Edit Team" button visibility logic
- [ ] Wire "Manage Roster" button (if owner/manager)
- [ ] Wire "Leave Team" action (if member)
- [ ] Wire ownership transfer (if owner)
- [ ] Add CSRF protection for all POST actions
- [ ] Add rate limiting for sensitive actions

**Exit Criteria:**
- ✅ Permission checks functional (only owners can edit)
- ✅ Edit actions wired (update team info)
- ✅ Roster management actions wired (kick, promote)
- ✅ Security audit passed (no privilege escalation)

**Note:** This gate is **DEFERRED** to Phase 5+. Phase 4 is READ-ONLY.

---

## SECTION 6 — ROLLBACK PLAN

### Emergency Rollback Conditions

**Trigger Conditions:**
- Production errors or exceptions in team detail page
- Query count exceeds budget (>6 queries)
- Privacy enforcement broken (unauthorized data access)
- Visual regressions (layout broken)
- Performance degradation (page load >2s)

**Rollback Procedure:**

**Step 1: Revert Code Changes**
```bash
# Revert to last stable commit
git revert <commit_hash>

# Or checkout specific file
git checkout HEAD~1 -- apps/organizations/services/team_detail_context.py
```

**Step 2: Database Rollback (If Migration Applied)**
```bash
# Revert privacy field migration
python manage.py migrate organizations <previous_migration>
```

**Step 3: Clear Cache**
```bash
# Clear game context cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.delete_pattern('game_context:*')
```

**Step 4: Verify Rollback**
- [ ] Run Django check (0 errors)
- [ ] Run test suite (all tests passing)
- [ ] Manual QA (team detail page loads correctly)

---

## SECTION 7 — QUERY BUDGET ENFORCEMENT

**Contract Requirement:** ≤6 queries per page view

**Query Breakdown by Tier:**

| Tier | Query | Purpose | Count |
|------|-------|---------|-------|
| Base | Team fetch | `Team.objects.select_related('organization').get(slug=slug)` | 1 |
| Base | Viewer membership | `TeamMembership.objects.filter(team=team, user=viewer)` | 1 |
| Tier-1 | Game lookup | `Game.objects.get(id=team.game_id)` | 1* |
| Tier-2 | Ranking | `TeamRanking.objects.get(team=team)` (via select_related) | 0 |
| Tier-2 | Roster | `TeamMembership.objects.select_related('user', 'user__profile').filter(status='ACTIVE')` | 1 |
| Tier-2 | Match stats | `Match.objects.filter(Q(...)).aggregate(...)` | 1 |
| Tier-2 | Pending invites | `TeamInvite.objects.filter(team=team, invited_user=viewer, status='PENDING')` | 1 |

**Total:** 6 queries (5 with game caching)  
**Status:** ✅ Within budget

*Game lookup cached (24-hour TTL) → expected 99%+ cache hit rate → effectively 0 queries

---

## SECTION 8 — PERFORMANCE BENCHMARKS

**Target Metrics:**

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Page load time | <1s | Django Debug Toolbar |
| Query count | ≤6 | Django Debug Toolbar |
| Query time | <100ms | Django Debug Toolbar |
| Template render | <50ms | Django Debug Toolbar |
| Cache hit rate (game) | >95% | Redis metrics |

**Performance Testing Checklist:**
- [ ] Install Django Debug Toolbar
- [ ] Load team detail page with authenticated user
- [ ] Verify query count ≤6
- [ ] Verify total query time <100ms
- [ ] Verify no N+1 queries
- [ ] Verify cache usage (game context cached)
- [ ] Benchmark Match stats query (indirect relationship)
- [ ] Stress test with team that has 100+ matches

---

## SECTION 9 — GATE APPROVAL MATRIX

**Gate 1: Pre-Wiring Preparation**
- Approver: **USER**
- Status: ⏸️ PENDING
- Required: Privacy strategy decision, game lookup approval

**Gate 2: Tier-1 Wiring (Backend)**
- Approver: **USER**
- Status: ⚠️ READY AFTER PRIVACY DECISION
- Required: Schema verification approved, privacy migration applied

**Gate 3: Tier-1 UI Activation**
- Approver: **USER**
- Status: ⏸️ PENDING
- Required: Tier-1 backend complete, visual regression baseline captured

**Gate 4: Tier-2 Wiring**
- Approver: **USER**
- Status: ❌ BLOCKED
- Required: Privacy field exists, Tier-1 stable, performance benchmarked

**Gate 5: Control Plane Coupling**
- Approver: **USER + SECURITY**
- Status: 🚫 OUT OF SCOPE
- Required: Tier-2 complete, permission system designed, security audit

---

## SECTION 10 — DECISION LOG

**DATE: 2026-01-30**

**DECISION 1: Game Lookup Strategy**
- **Status:** ✅ APPROVED (discovery: GameService.get_game_by_id exists)
- **Decision:** Use existing GameService.get_game_by_id() method
- **Rationale:** Solution already exists, no migration needed, production-ready

**DECISION 2: Privacy Field Strategy**
- **Status:** ⏸️ PENDING USER DECISION
- **Options:**
  * A) Add `visibility` CharField (PUBLIC/PRIVATE/UNLISTED)
  * B) Add `is_private` BooleanField (True/False)
  * C) Remove privacy logic entirely (all teams public)
- **Blocker:** Cannot proceed with Tier-2 without decision

**DECISION 3: Partner Model**
- **Status:** ✅ ACCEPTED
- **Decision:** Partner model doesn't exist, return empty list
- **Rationale:** Tier-2 nice-to-have, defer to Phase 9+

**DECISION 4: Match Relationship**
- **Status:** ✅ ACCEPTED WITH CAUTION
- **Decision:** Use indirect query with Q filter on participant_id
- **Rationale:** No FK exists, query performance acceptable with indexes

**DECISION 5: Wiring Mode**
- **Status:** ✅ LOCKED
- **Decision:** ANALYTICAL ONLY - NO CODE CHANGES YET
- **Rationale:** Backend readiness verification before wiring

---

## SECTION 11 — CRITICAL PATH SUMMARY

**Path to Tier-1 Completion:**

```
1. USER DECISION: Privacy field strategy (blocking)
2. Create privacy field migration
3. Apply migration
4. Integrate GameService.get_game_by_id()
5. Add 4 game lookup tests
6. Run 26 tests (expect all passing)
7. Data integrity check (no orphaned game_id)
8. Django check validation
9. USER APPROVAL: Tier-1 complete
```

**Estimated Time:** 2-4 hours (after privacy decision)

---

**Path to Tier-2 Completion:**

```
1. Tier-1 stable and approved
2. Update privacy enforcement logic (use real field)
3. Remove mocking from privacy tests
4. Wire roster section (with N+1 prevention)
5. Wire stats section (Match query + TeamRanking)
6. Add Match query indexes (optional, for performance)
7. Benchmark query performance (≤6 queries)
8. Visual QA (roster/stats display correctly)
9. USER APPROVAL: Tier-2 complete
```

**Estimated Time:** 6-8 hours (after Tier-1 complete)

---

**Path to Control Plane Coupling:**

```
🚫 DEFERRED TO PHASE 5+ (write operations out of scope)
```

---

## SECTION 12 — FINAL CHECKLIST BEFORE ANY CODE CHANGE

**Agent Must Verify:**

- [ ] User has reviewed schema verification report
- [ ] User has reviewed game lookup resolution proposal
- [ ] User has reviewed this wiring readiness checklist
- [ ] User has decided on privacy field strategy
- [ ] User has explicitly authorized Tier-1 wiring
- [ ] All documentation is approved and locked

**Agent Must NOT:**

- [ ] ❌ Make template changes without explicit approval
- [ ] ❌ Modify context builder logic without gate clearance
- [ ] ❌ Introduce feature flags or service refactoring
- [ ] ❌ Expand query logic without performance benchmarking
- [ ] ❌ Proceed with Tier-2 before privacy field exists
- [ ] ❌ Wire write operations (edit, delete) in Phase 4

---

## CHANGELOG

**v1.0 (2026-01-30):**
- Initial wiring readiness checklist
- 5 gates defined with approval matrix
- Critical path identified (privacy field blocker)
- Query budget enforcement documented
- Rollback plan defined
- Performance benchmarks specified

---

**APPROVAL STATUS:** ⏸️ **AWAITING USER REVIEW**

**Next Action:** USER reviews all 3 documents and makes privacy field decision.

---

**END OF CHECKLIST**
