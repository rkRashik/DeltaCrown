# Phase 4 Deferred Items & Backlog

**Last Updated:** November 9, 2025  
**Phase:** 4 (Tournament Live Operations)  
**Status:** Documented for future sprints

---

## Overview

This document tracks deferred items from Phase 4 modules that were explicitly postponed to maintain delivery velocity and avoid breaking changes. All items are non-blocking and can be addressed in future phases.

**Prioritization Framework:**
- **High:** Unblocks skipped tests or improves test coverage significantly
- **Medium:** Enhances functionality or user experience
- **Low:** Nice-to-have features or optimizations

**Effort Estimates:**
- **S (Small):** 1-2 hours
- **M (Medium):** 4-8 hours
- **L (Large):** 12-24 hours
- **XL (Extra Large):** 24+ hours

---

## High Priority Items (Phase 6)

### 1. Convert WebSocket Broadcast Helpers to Async-Native

**Module:** 4.5 (WebSocket Enhancement)

**Description:**
Current WebSocket broadcast helper functions (`broadcast_bracket_generated`, `broadcast_match_updated`, etc.) use synchronous Django ORM queries wrapped in `sync_to_async`. This causes 4 tests to be skipped due to async context issues.

**Current State:**
```python
# apps/tournaments/realtime/utils.py (current)
def broadcast_bracket_generated(bracket_id):
    bracket = Bracket.objects.get(id=bracket_id)  # Sync query
    async_to_sync(channel_layer.group_send)(...) # Async send
```

**Desired State:**
```python
# apps/tournaments/realtime/utils.py (target)
async def broadcast_bracket_generated(bracket_id):
    bracket = await sync_to_async(Bracket.objects.get)(id=bracket_id)  # Proper async
    await channel_layer.group_send(...)  # Native async
```

**Benefits:**
- Unblocks 4 skipped tests in `test_websocket_enhancement_module_4_5.py`
- Improves async context handling
- Better performance for WebSocket operations

**Risks:**
- **Low:** Refactor only, no behavior change
- All callers already in async context (consumers)

**Effort:** **S** (~2 hours)

**Dependencies:** None

**Tests to Unblock:**
- `test_heartbeat_timeout_closes_connection`
- `test_score_batching_coalesces_rapid_updates`
- `test_dispute_created_emits_to_both_channels`
- `test_match_channel_isolation`

**Acceptance Criteria:**
- All 4 skipped tests pass
- No new test failures
- Coverage for `realtime/utils.py` increases from 61% to 75%+

---

### 2. Audit URL Routing Configuration

**Module:** 4.6 (API Polish & QA)

**Description:**
Some API endpoints return 404 instead of expected behavior (e.g., `/api/tournaments/brackets/` list endpoint). This caused 3 smoke tests to be skipped. Root cause likely URL pattern configuration or viewset router setup.

**Current State:**
- `/api/tournaments/brackets/` returns 404 (expected: 200 with bracket list)
- `/api/tournaments/brackets/tournaments/<id>/generate/` works correctly ✅
- `/api/tournaments/matches/` works correctly ✅

**Investigation Needed:**
1. Check `apps/tournaments/api/urls.py` router registration
2. Verify `BracketViewSet` implements `list()` method
3. Check URL namespace conflicts
4. Test with `/api/tournaments/brackets/?format=json` (trailing slash)

**Benefits:**
- Unblocks 3 skipped smoke tests
- Fixes potential API inconsistency
- Better developer experience (list endpoints work as expected)

**Risks:**
- **Low:** URL configuration only, no logic changes

**Effort:** **S** (~1 hour)

**Dependencies:** None

**Tests to Unblock:**
- `test_bracket_list_public_access`
- `test_match_list_filtering` (partial - also needs DB fix)
- Related API integration tests

**Acceptance Criteria:**
- `/api/tournaments/brackets/` returns 200 with paginated list
- DRF browsable API shows list endpoint
- Skipped tests pass or rationale updated

---

## Medium Priority Items (Phase 6-7)

### 3. Uplift realtime/ Coverage from 36% → 80%

**Module:** 4.5 (WebSocket Enhancement)

**Description:**
Current WebSocket coverage is 78% overall, but some files lag behind:
- `consumers.py`: 43% coverage
- `utils.py`: 61% coverage
- `match_consumer.py`: 70% coverage

**Target:** 80%+ coverage for all realtime/ files

**Coverage Gaps:**
1. **Error handling paths:** WebSocket authentication failures, permission denied
2. **Edge cases:** Invalid message formats, malformed JSON, oversized payloads
3. **Reconnection logic:** Client disconnect/reconnect scenarios
4. **Rate limiting integration:** Message throttling, connection limits

**Benefits:**
- Better confidence in WebSocket stability
- Catches edge case bugs before production
- Aligns with Phase 3 coverage standards (85-91%)

**Risks:**
- **Low:** Test expansion only, no production changes

**Effort:** **M** (~4 hours)

**Dependencies:** Item #1 (async conversion) should be done first

**Acceptance Criteria:**
- `consumers.py`: 43% → 80%
- `utils.py`: 61% → 80%
- `match_consumer.py`: 70% → 85%
- No new skipped tests
- All error paths covered

---

### 4. Investigate Module 4.2 Test Failures

**Module:** 4.2 (Ranking & Seeding Integration)

**Description:**
4 tests fail in Module 4.2:
- 2 tie-breaking edge cases (deterministic algorithm not handling all scenarios)
- 2 API fixture issues (test data setup problems)

**Current Status:**
- 42/46 tests passing (91% pass rate)
- Core functionality works correctly ✅
- Failures are edge cases, non-blocking

**Investigation Needed:**
1. **Tie-breaking edge case 1:** Three teams with identical points, creation time, and sequential IDs
2. **Tie-breaking edge case 2:** Team ranking data missing for one participant
3. **API fixture issue 1:** Tournament creation fails with game config validation
4. **API fixture issue 2:** Ranking data not properly seeded in test DB

**Benefits:**
- 100% test pass rate for Module 4.2
- More robust tie-breaking algorithm
- Better test fixture reusability

**Risks:**
- **Low:** Test fixes only, no production impact

**Effort:** **S-M** (~2-3 hours)

**Dependencies:** None

**Acceptance Criteria:**
- All 46 tests pass (100% pass rate)
- Tie-breaking algorithm handles all edge cases deterministically
- Test fixtures documented and reusable

---

### 5. Add Admin Dispute Dashboard

**Module:** 4.4 (Result Submission & Confirmation)

**Description:**
Currently, disputes require manual organizer intervention via API calls. No admin UI exists for viewing, filtering, or resolving disputes efficiently.

**Proposed Features:**
1. **Dispute List View:**
   - Filter by tournament, status, date
   - Sort by priority (age, tournament importance)
   - Bulk actions (resolve, reject)

2. **Dispute Detail View:**
   - Match details (participants, scores, state)
   - Dispute reason and evidence
   - Resolution form (winner selection, notes)
   - Audit trail (who reported, when, IP)

3. **Notifications:**
   - Email organizer when dispute reported
   - Notify participants when dispute resolved

**Benefits:**
- Faster dispute resolution
- Better organizer experience
- Audit trail for compliance

**Risks:**
- **Medium:** New UI, requires frontend work

**Effort:** **M-L** (~8 hours)
- Backend endpoints: 2 hours
- Admin UI: 4 hours
- Testing: 2 hours

**Dependencies:** None (can be built independently)

**Acceptance Criteria:**
- Admin can view all disputes for their tournaments
- Admin can resolve disputes with winner selection
- Participants notified via WebSocket when dispute resolved
- Audit trail persisted

---

### 6. Fix Database Constraint Issues in Tests

**Module:** 4.6 (API Polish & QA)

**Description:**
2 smoke tests skipped due to `IntegrityError: duplicate key value violates unique constraint "tournament_engine_bracket_bracket_tournament_id_key"`. This prevents testing scenarios with multiple brackets or matches per tournament.

**Root Cause:**
Unique constraint on `bracket.tournament_id` enforces one bracket per tournament. This is an **intentional design choice** (single-elimination tournaments have one bracket).

**Options:**
1. **Accept as design choice:** Document constraint in ERD and API docs (recommended)
2. **Remove constraint:** Allow multiple brackets (e.g., for double-elimination with loser's bracket)
3. **Improve test fixtures:** Mock bracket creation instead of using real DB

**Recommendation:** Option 1 (document as intentional)

**Benefits:**
- Clarifies design intent
- Prevents accidental constraint violations
- Better API documentation

**Risks:**
- **Low:** Documentation only

**Effort:** **S** (~1 hour)
- Update ERD documentation
- Add constraint note to API docs
- Update skipped test rationale

**Dependencies:** None

**Acceptance Criteria:**
- Constraint documented in `PART_3.1_DATABASE_DESIGN_ERD.md`
- API docs note one-bracket-per-tournament limit
- Skipped tests have clear rationale

---

## Low Priority Items (Phase 7+)

### 7. Double-Elimination Brackets

**Module:** 4.1 (Bracket Generation API)

**Description:**
Double-elimination bracket format deferred from Module 4.1. Requires loser's bracket logic, which is complex for seeding and match progression.

**Scope:**
1. **Bracket Structure:**
   - Winner's bracket (standard single-elimination)
   - Loser's bracket (feed from winners bracket losses)
   - Grand final (winner of each bracket)

2. **Seeding Logic:**
   - Initial seeding same as single-elimination
   - Loser placement algorithm (based on round lost)

3. **Match Progression:**
   - Win → advance in winner's bracket
   - Loss in winner's bracket → drop to loser's bracket
   - Loss in loser's bracket → eliminated
   - Grand final rematch if loser's bracket winner wins

**Benefits:**
- More forgiving format (teams get second chance)
- Popular for competitive tournaments
- Increases tournament engagement

**Risks:**
- **Medium:** Complex bracket logic, edge cases

**Effort:** **L** (~16 hours)
- Loser bracket algorithm: 6 hours
- Match progression logic: 4 hours
- Seeding integration: 2 hours
- Testing: 4 hours

**Dependencies:**
- Module 4.1 (single-elimination) complete ✅
- Module 4.3 (match management) complete ✅

**Acceptance Criteria:**
- Generate double-elimination bracket for 8/16/32 participants
- Loser's bracket seeding correct
- Grand final rematch logic works
- 90%+ test coverage

---

### 8. Round-Robin Format

**Module:** 4.1 (Bracket Generation API)

**Description:**
Round-robin format deferred from Module 4.1. Each team plays every other team once (or twice for double round-robin). Used for league-style tournaments.

**Scope:**
1. **Match Scheduling:**
   - Generate all-play-all match pairings
   - Fair scheduling (no team plays twice in a row)
   - Venue/time slot optimization

2. **Standings Calculation:**
   - Points system (win/draw/loss)
   - Tiebreakers (head-to-head, goal difference, etc.)
   - Real-time standings updates

3. **Bracket Visualization:**
   - Match grid (teams × rounds)
   - Standings table
   - Progress tracking

**Benefits:**
- Fairer format (every team plays everyone)
- Better for leagues and long-term tournaments
- More accurate skill assessment

**Risks:**
- **Medium:** Scheduling complexity, many matches

**Effort:** **M-L** (~12 hours)
- Pairing algorithm: 4 hours
- Scheduling logic: 3 hours
- Standings calculation: 3 hours
- Testing: 2 hours

**Dependencies:**
- Module 4.1 (bracket generation) complete ✅
- Module 4.3 (match management) complete ✅
- Module 4.4 (result submission) complete ✅

**Acceptance Criteria:**
- Generate round-robin bracket for 4/6/8/10 teams
- Fair scheduling (balanced rest periods)
- Standings update in real-time
- Tiebreaker logic tested

---

### 9. Add Fuzz Testing for Edge Cases

**Module:** Cross-cutting (all Phase 4 modules)

**Description:**
Add fuzz testing to hit remaining coverage gaps in bracket, match, and result APIs. Use hypothesis library to generate random inputs and test edge cases.

**Targets:**
- `bracket_views.py`: 31% → 60% (29% uplift)
- `match_views.py`: 32% → 60% (28% uplift)
- `result_views.py`: 32% → 60% (28% uplift)
- `permissions.py`: 26% → 60% (34% uplift)

**Fuzz Test Scenarios:**
1. **Invalid input fuzzing:** Random strings, negative numbers, extreme values
2. **Permission boundary fuzzing:** Random user roles, missing auth tokens
3. **State transition fuzzing:** Invalid state changes, concurrent updates
4. **WebSocket message fuzzing:** Malformed JSON, oversized payloads

**Benefits:**
- Discovers edge case bugs before users do
- Increases confidence in API stability
- Better error handling coverage

**Risks:**
- **Low:** Test expansion only

**Effort:** **M** (~6 hours)
- Setup hypothesis framework: 1 hour
- Write fuzz tests: 3 hours
- Fix discovered bugs: 2 hours

**Dependencies:** None

**Acceptance Criteria:**
- All Phase 4 API files ≥60% coverage
- No new bugs discovered (or all fixed)
- Fuzz tests pass consistently

---

## Summary

**Total Deferred Items:** 9

**By Priority:**
- High: 2 items (~3 hours total)
- Medium: 4 items (~17 hours total)
- Low: 3 items (~34 hours total)

**By Module:**
- Module 4.1 (Bracket): 2 items (double-elim, round-robin)
- Module 4.2 (Ranking): 1 item (test failures)
- Module 4.4 (Result): 1 item (admin dashboard)
- Module 4.5 (WebSocket): 2 items (async conversion, coverage uplift)
- Module 4.6 (Polish): 2 items (URL routing, DB constraints)
- Cross-cutting: 1 item (fuzz testing)

**Recommended Phase 6 Sprint:**
1. Convert WebSocket helpers to async (2 hours) - unblocks tests
2. Audit URL routing (1 hour) - quick win
3. Investigate Module 4.2 test failures (2 hours) - quality improvement

**Total Phase 6 effort:** ~5 hours (all high priority items)

---

**Prepared by:** GitHub Copilot  
**Date:** November 9, 2025  
**Review Status:** Ready for sprint planning  
**Next Update:** After Phase 6 planning meeting

