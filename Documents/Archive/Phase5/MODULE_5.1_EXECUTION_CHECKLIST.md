# Module 5.1: Winner Determination & Verification - Execution Checklist

**Status:** 📋 Pre-Implementation Review  
**Date:** November 9, 2025  
**Estimated Effort:** ~24 hours  
**Target Coverage:** ≥85%

---

## 1. Inputs & Data Sources

### Required Tournament State
- **Tournament Status:** `COMPLETED` or `CONCLUDED`
  - All matches in bracket must have `state = 'COMPLETED'`
  - Bracket status must be `COMPLETED`
  - No pending disputes (`Dispute.status != 'pending'`)

### Data Dependencies
- ✅ **Tournament Model** (`apps/tournaments/models/tournament.py`)
  - Fields: `id`, `status`, `organizer`, `prize_pool`, `prize_distribution`
  
- ✅ **Bracket Model** (`apps/tournaments/models/bracket.py`)
  - Fields: `tournament`, `status`, `bracket_data` (JSONB tree structure)
  - Tree traversal to find final winner node
  
- ✅ **BracketNode Model** (`apps/tournaments/models/bracket.py`)
  - Fields: `winner_id`, `round_number`, `position_in_round`
  - Navigate tree: root → finals → champion
  
- ✅ **Match Model** (`apps/tournaments/models/match.py`)
  - Fields: `state`, `winner_id`, `bracket_node`
  - Verify all matches complete
  
- ✅ **Registration Model** (`apps/tournaments/models/registration.py`)
  - Fields: `id`, `user`, `team`, `status = 'checked_in'`
  - Winner participant info

### External Integration Points
- ⚠️ **apps.economy** (for Module 5.2, not 5.1)
- ✅ **WebSocket consumers** (broadcast tournament_completed event)
- ✅ **Admin interface** (organizer review workflow)

---

## 2. Outputs & State Changes

### New Model: TournamentResult

```python
# apps/tournaments/models/result.py
class TournamentResult(TimestampedModel, SoftDeleteModel):
    """Final tournament results and winner determination."""
    
    # Foreign Keys
    tournament = models.OneToOneField('Tournament', related_name='result')
    winner_participant = models.ForeignKey('Registration', related_name='won_tournaments')
    final_bracket = models.ForeignKey('Bracket', null=True)
    runner_up_participant = models.ForeignKey('Registration', related_name='runner_up_tournaments', null=True)
    third_place_participant = models.ForeignKey('Registration', related_name='third_place_tournaments', null=True)
    
    # Metadata
    determined_at = models.DateTimeField(auto_now_add=True)
    determination_method = models.CharField(
        max_length=50,
        choices=[
            ('bracket_resolution', 'Bracket Resolution'),
            ('manual_selection', 'Manual Organizer Selection'),
            ('tiebreaker', 'Tie-Breaking Rules'),
            ('forfeit_default', 'Forfeit/Default Win'),
        ]
    )
    reasoning = models.TextField(help_text="Audit trail explanation")
    
    # Verification (optional organizer review)
    verified_by = models.ForeignKey(User, null=True, related_name='verified_tournament_results')
    verified_at = models.DateTimeField(null=True)
```

**Database Table:** `tournament_engine_result_tournamentresult`

**Indexes:**
- `tournament_id` (unique, OneToOne)
- `winner_participant_id` (FK index)
- `determined_at` (ordering)

### State Transitions

**Tournament.status:**
- `COMPLETED` → `CONCLUDED` (after winner determined)
- Triggers: All matches complete → WinnerService.determine_winner() → status update

**TournamentResult Creation:**
- New record created with winner, runner-up, 3rd place
- `determination_method` set based on logic path
- `reasoning` populated with audit explanation

---

## 3. Service Layer Design

### WinnerDeterminationService

```python
# apps/tournaments/services/winner_service.py
class WinnerDeterminationService:
    """Business logic for tournament winner determination."""
    
    def determine_winner(self, tournament_id: int) -> Optional[int]:
        """
        Main entry point: Determine tournament winner.
        
        Returns:
            Winner participant ID (Registration.id) or None if incomplete.
        
        Algorithm:
            1. Verify tournament completion (all matches done)
            2. Traverse bracket tree to find final winner node
            3. Extract winner_participant_id from final node
            4. Handle tie-breaking if needed
            5. Create TournamentResult record
            6. Update tournament status to CONCLUDED
            7. Broadcast tournament_completed WebSocket event
            8. Return winner_participant_id
        
        Failure Modes:
            - Incomplete bracket → return None, log warning
            - Missing winner in final node → return None, raise ValidationError
            - Pending disputes → return None, log warning
            - Database error → rollback, log error, re-raise
        """
    
    def verify_tournament_completion(self, tournament_id: int) -> bool:
        """
        Check if tournament is ready for winner determination.
        
        Checks:
            - Tournament status = COMPLETED
            - All matches in bracket have state = COMPLETED
            - No pending disputes (Dispute.status != 'pending')
            - Bracket status = COMPLETED
        
        Returns:
            True if ready, False otherwise
        """
    
    def _traverse_bracket_to_winner(self, bracket: Bracket) -> Optional[int]:
        """
        Internal: Traverse bracket tree to find final winner.
        
        Logic:
            - Single-elimination: Find highest round node with winner_id
            - Future: Double-elimination (winners bracket final + grand final)
        
        Returns:
            Participant ID (Registration.id) or None
        """
    
    def apply_tiebreaker_rules(
        self, 
        tournament_id: int, 
        tied_participants: List[int]
    ) -> int:
        """
        Apply tie-breaking rules to determine winner.
        
        Rules (configurable via Tournament.config JSONB):
            1. Default: Highest bracket position (earliest seed)
            2. Head-to-head record (if participants faced each other)
            3. Total score differential across all matches
            4. Match completion time (faster wins)
            5. Manual organizer decision (fallback)
        
        Returns:
            Winner participant ID
        
        Raises:
            ValidationError if no tie-breaking rule applies
        """
    
    def create_audit_log(
        self, 
        tournament_id: int, 
        winner_id: int, 
        reasoning: str
    ) -> None:
        """
        Create audit trail for winner determination.
        
        Stored in TournamentResult.reasoning field.
        
        Format:
            "Winner determined via {method}: {reasoning}"
            
        Example:
            "Winner determined via bracket_resolution: Team Phoenix won finals match (ID: 789) with score 3-1."
        """
```

---

## 4. WebSocket Integration

### Event: tournament_completed

**Broadcast To:**
- `tournament_{tournament_id}` group (all subscribers)

**Payload:**
```json
{
    "type": "tournament_completed",
    "data": {
        "tournament_id": 123,
        "winner_participant_id": 456,
        "winner_name": "Team Phoenix",
        "winner_type": "team",  // or "individual"
        "bracket_id": 789,
        "determined_at": "2025-11-09T15:30:00Z",
        "determination_method": "bracket_resolution",
        "runner_up_participant_id": 457,
        "runner_up_name": "Team Dragon",
        "third_place_participant_id": 458,
        "third_place_name": "Team Eagle",
        "requires_organizer_review": false
    }
}
```

**Broadcast Trigger:**
- Called from `WinnerDeterminationService.determine_winner()` after TournamentResult created
- Use existing `broadcast_tournament_event()` helper from `apps/tournaments/realtime/utils.py`

**Handler Location:**
- `apps/tournaments/realtime/consumers.py` → `TournamentConsumer.tournament_completed()`
- No new consumer needed (reuse existing)

---

## 5. Failure Modes & Error Handling

### Scenario 1: Incomplete Tournament
**Trigger:** `determine_winner()` called before all matches complete  
**Behavior:**
- `verify_tournament_completion()` returns False
- Log warning: "Tournament {id} not ready for winner determination: {reason}"
- Return None (no TournamentResult created)
- No state change

**Test:** `test_determine_winner_incomplete_tournament`

### Scenario 2: Missing Winner in Final Node
**Trigger:** Bracket tree traversal finds final node with `winner_id = None`  
**Behavior:**
- Raise `ValidationError("Bracket final node missing winner")`
- Log error with bracket details
- No TournamentResult created
- No state change

**Test:** `test_determine_winner_missing_final_winner`

### Scenario 3: Pending Disputes
**Trigger:** One or more disputes with `status = 'pending'`  
**Behavior:**
- `verify_tournament_completion()` returns False
- Log warning: "Tournament {id} has pending disputes: {dispute_ids}"
- Return None
- No state change

**Test:** `test_determine_winner_pending_disputes`

### Scenario 4: Forfeit Chain (All Byes to Finals)
**Trigger:** Winner reached finals via all bye/forfeit matches  
**Behavior:**
- Still valid winner (legitimate bracket progression)
- `determination_method = 'forfeit_default'`
- `reasoning` includes "Winner advanced via forfeits"
- TournamentResult created normally

**Test:** `test_determine_winner_forfeit_chain`

### Scenario 5: Tie-Breaking Required
**Trigger:** Multiple participants tied for same placement  
**Behavior:**
- Call `apply_tiebreaker_rules(tournament_id, tied_participants)`
- Apply configured tie-breaking logic
- If no rule applies → manual organizer decision required
- Set `requires_organizer_review = True` in WebSocket event

**Test:** `test_apply_tiebreaker_rules`

### Scenario 6: Database Transaction Failure
**Trigger:** Error during TournamentResult.save() or Tournament.status update  
**Behavior:**
- Wrap in `transaction.atomic()` block
- Rollback all changes
- Log error with full traceback
- Re-raise exception (let caller handle)
- No partial state (all-or-nothing)

**Test:** `test_determine_winner_database_error`

---

## 6. Admin Integration

### TournamentResultAdmin

```python
# apps/tournaments/admin_result.py
@admin.register(TournamentResult)
class TournamentResultAdmin(admin.ModelAdmin):
    list_display = [
        'tournament', 
        'winner_participant', 
        'determination_method', 
        'determined_at', 
        'verified_by'
    ]
    list_filter = ['determination_method', 'determined_at']
    search_fields = ['tournament__title', 'winner_participant__user__username']
    readonly_fields = ['determined_at', 'reasoning']
    
    fieldsets = (
        ('Tournament', {
            'fields': ('tournament', 'final_bracket')
        }),
        ('Placements', {
            'fields': (
                'winner_participant', 
                'runner_up_participant', 
                'third_place_participant'
            )
        }),
        ('Determination', {
            'fields': ('determination_method', 'reasoning', 'determined_at')
        }),
        ('Verification', {
            'fields': ('verified_by', 'verified_at')
        }),
    )
    
    def has_add_permission(self, request):
        # Winners determined automatically, no manual creation
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Results are permanent audit records
        return False
```

**Admin Actions:**
- View-only for audit purposes
- Organizers can view via Django admin (if has permission)
- Future: Add "Verify Result" button for organizer review workflow

---

## 7. Test Scaffolding Plan

### Test File Structure

```python
# tests/test_winner_determination_module_5_1.py

import pytest
from django.core.exceptions import ValidationError
from apps.tournaments.services.winner_service import WinnerDeterminationService
from apps.tournaments.models import Tournament, Bracket, Match, TournamentResult

# === UNIT TESTS (15) ===

# Winner Determination for Complete Brackets (4 tests)
@pytest.mark.skip(reason="Scaffolding")
def test_determine_winner_single_elimination_8_participants():
    """Complete 8-team bracket resolves to correct winner."""
    pass

@pytest.mark.skip(reason="Scaffolding")
def test_determine_winner_single_elimination_16_participants():
    """Complete 16-team bracket resolves to correct winner."""
    pass

@pytest.mark.skip(reason="Scaffolding")
def test_determine_winner_with_bye_matches():
    """Winner determined correctly with bye matches in bracket."""
    pass

@pytest.mark.skip(reason="Scaffolding")
def test_determine_winner_updates_tournament_status_to_concluded():
    """Tournament status changes from COMPLETED to CONCLUDED."""
    pass

# Incomplete Bracket Handling (3 tests)
@pytest.mark.skip(reason="Scaffolding")
def test_determine_winner_incomplete_tournament_returns_none():
    """Returns None when matches still pending."""
    pass

@pytest.mark.skip(reason="Scaffolding")
def test_determine_winner_missing_final_winner_raises_validation_error():
    """Raises ValidationError if final node has no winner."""
    pass

@pytest.mark.skip(reason="Scaffolding")
def test_verify_tournament_completion_pending_disputes_returns_false():
    """Returns False when disputes still pending."""
    pass

# Tie-Breaking Logic (3 tests)
@pytest.mark.skip(reason="Scaffolding")
def test_apply_tiebreaker_highest_bracket_position():
    """Tie-breaking: Participant with higher seed wins."""
    pass

@pytest.mark.skip(reason="Scaffolding")
def test_apply_tiebreaker_head_to_head_record():
    """Tie-breaking: Head-to-head winner determined."""
    pass

@pytest.mark.skip(reason="Scaffolding")
def test_apply_tiebreaker_total_score_differential():
    """Tie-breaking: Highest total score differential wins."""
    pass

# Audit Log Creation (2 tests)
@pytest.mark.skip(reason="Scaffolding")
def test_create_audit_log_stores_reasoning():
    """Audit trail stored in TournamentResult.reasoning."""
    pass

@pytest.mark.skip(reason="Scaffolding")
def test_audit_log_includes_determination_method():
    """Reasoning includes determination method."""
    pass

# Edge Cases (3 tests)
@pytest.mark.skip(reason="Scaffolding")
def test_determine_winner_forfeit_chain_to_finals():
    """Winner via all forfeits/byes still valid."""
    pass

@pytest.mark.skip(reason="Scaffolding")
def test_determine_winner_bye_match_in_finals():
    """Finals with bye (odd participants) handled correctly."""
    pass

@pytest.mark.skip(reason="Scaffolding")
def test_determine_winner_database_transaction_rollback():
    """Database error rolls back all changes."""
    pass

# === INTEGRATION TESTS (8) ===

# End-to-End Winner Determination (2 tests)
@pytest.mark.skip(reason="Scaffolding")
@pytest.mark.integration
def test_end_to_end_winner_determination_8_teams():
    """Full flow: create tournament → play matches → determine winner."""
    pass

@pytest.mark.skip(reason="Scaffolding")
@pytest.mark.integration
def test_end_to_end_winner_determination_with_prize_pool():
    """Winner determination with prize_pool for Module 5.2 integration."""
    pass

# WebSocket Event Broadcasting (2 tests)
@pytest.mark.skip(reason="Scaffolding")
@pytest.mark.integration
def test_tournament_completed_event_broadcasted():
    """tournament_completed event sent to tournament group."""
    pass

@pytest.mark.skip(reason="Scaffolding")
@pytest.mark.integration
def test_tournament_completed_event_payload_structure():
    """Event payload matches schema (winner, runner-up, 3rd place)."""
    pass

# Organizer Review Workflow (2 tests)
@pytest.mark.skip(reason="Scaffolding")
@pytest.mark.integration
def test_organizer_review_required_flag():
    """requires_organizer_review set when tie-breaking fails."""
    pass

@pytest.mark.skip(reason="Scaffolding")
@pytest.mark.integration
def test_organizer_manual_verification():
    """Organizer can verify result (verified_by, verified_at populated)."""
    pass

# Dispute Resolution Integration (2 tests)
@pytest.mark.skip(reason="Scaffolding")
@pytest.mark.integration
def test_pending_dispute_blocks_winner_determination():
    """Cannot determine winner while disputes pending."""
    pass

@pytest.mark.skip(reason="Scaffolding")
@pytest.mark.integration
def test_resolved_dispute_allows_winner_determination():
    """Winner determination proceeds after dispute resolved."""
    pass
```

---

## 8. Migration Strategy

### Migration File: `0XXX_tournament_result.py`

**Operations:**
1. **CreateModel: TournamentResult**
   - All fields as specified in schema
   - Foreign keys to Tournament, Registration, Bracket, User
   
2. **Add Indexes:**
   - `tournament_id` (unique, OneToOne)
   - `winner_participant_id` (FK)
   - `determined_at` (ordering)

3. **Add Database Constraints:**
   - `CHECK (winner_participant_id IS NOT NULL)` (cannot be null)
   - `CHECK (runner_up_participant_id != winner_participant_id)` (different participants)
   - `CHECK (third_place_participant_id NOT IN (winner_participant_id, runner_up_participant_id))` (different)

**Rollback Plan:**
- `DropModel: TournamentResult`
- Safe to rollback (no existing data)

---

## 9. Scope Verification: Phase 4 Dependencies

### No Phase 4 Backlog Items Required

Reviewing `BACKLOG_PHASE_4_DEFERRED.md`:
- ❌ **Item #1 (Async WebSocket):** Not required for 5.1 (uses sync broadcast helper)
- ❌ **Item #2 (URL Routing):** Not required (no new public APIs)
- ❌ **Item #3 (Coverage Uplift):** Not blocking (separate concern)
- ❌ **Item #4 (Test Failures):** Not blocking (Module 4.2 tests, separate)
- ❌ **Item #5 (Dispute Dashboard):** Not required (service layer checks dispute status)
- ❌ **Item #6 (DB Constraints):** Not blocking (documented, intentional design)
- ❌ **Items #7-9:** Not required (future features)

**Conclusion:** Module 5.1 can proceed without Phase 4 backlog items.

---

## 10. Implementation Order

### Step 1: Models & Migrations (~4 hours)
1. Create `apps/tournaments/models/result.py`
2. Define `TournamentResult` model
3. Generate migration: `python manage.py makemigrations tournaments`
4. Review migration SQL
5. Apply migration: `python manage.py migrate tournaments`
6. Verify in Django shell

### Step 2: Service Layer (~8 hours)
1. Create `apps/tournaments/services/winner_service.py`
2. Implement `WinnerDeterminationService` class
3. Implement `determine_winner()` method
4. Implement `verify_tournament_completion()` helper
5. Implement `_traverse_bracket_to_winner()` helper
6. Implement `apply_tiebreaker_rules()` method
7. Implement `create_audit_log()` helper
8. Add transaction.atomic() wrapper

### Step 3: Admin Integration (~3 hours)
1. Create `apps/tournaments/admin_result.py`
2. Implement `TournamentResultAdmin`
3. Register admin class
4. Test in Django admin interface

### Step 4: WebSocket Integration (~2 hours)
1. Update `apps/tournaments/realtime/utils.py`
2. Add `broadcast_tournament_completed()` helper (or reuse generic)
3. Call from `WinnerDeterminationService.determine_winner()`
4. Update `TournamentConsumer` to handle event

### Step 5: Unit Tests (~6 hours)
1. Create `tests/test_winner_determination_module_5_1.py`
2. Implement 15 unit tests (remove @pytest.mark.skip)
3. Run tests: `pytest tests/test_winner_determination_module_5_1.py -v`
4. Fix failures, iterate

### Step 6: Integration Tests (~4 hours)
1. Implement 8 integration tests
2. Run integration tests: `pytest tests/test_winner_determination_module_5_1.py -m integration -v`
3. Fix failures, iterate

### Step 7: Coverage & Documentation (~3 hours)
1. Run coverage: `pytest tests/test_winner_determination_module_5_1.py --cov=apps/tournaments/services/winner_service --cov=apps/tournaments/models/result --cov-report=term-missing`
2. Target: ≥85% coverage
3. Create `MODULE_5.1_COMPLETION_STATUS.md`
4. Update `MAP.md` and `trace.yml`
5. Run `verify_trace.py`

### Total Estimated Effort: ~24 hours

---

## 11. Acceptance Criteria

### Functional Requirements
- [ ] Winner automatically determined when all matches complete
- [ ] TournamentResult record created with winner, runner-up, 3rd place
- [ ] Tournament status updated from COMPLETED → CONCLUDED
- [ ] WebSocket event `tournament_completed` broadcasted
- [ ] Audit trail stored in `TournamentResult.reasoning`
- [ ] Organizer review workflow supported (verified_by, verified_at)
- [ ] Tie-breaking rules configurable per tournament
- [ ] Pending disputes block winner determination
- [ ] Forfeit chains handled correctly
- [ ] Bye matches handled correctly

### Quality Requirements
- [ ] 23/23 tests passing (15 unit + 8 integration)
- [ ] ≥85% test coverage for `winner_service.py` and `models/result.py`
- [ ] No N+1 queries (use select_related, prefetch_related)
- [ ] Transaction.atomic() wraps all database changes
- [ ] Admin interface functional (view-only)
- [ ] Documentation complete (docstrings, completion doc)

### Non-Functional Requirements
- [ ] Winner determination completes in <5 seconds (8-team bracket)
- [ ] Winner determination completes in <15 seconds (64-team bracket)
- [ ] No breaking changes to Phase 4 APIs
- [ ] Zero P0/P1 bugs
- [ ] WebSocket event payload matches schema

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Bracket tree traversal complexity** | Medium | High | Write comprehensive unit tests for all bracket sizes (4/8/16/32/64) |
| **Database transaction failures** | Low | Critical | Use transaction.atomic(), add rollback tests |
| **WebSocket broadcast failures** | Low | Medium | Wrap in try/except, log errors, don't block winner determination |
| **Tie-breaking logic bugs** | Medium | Medium | Extensive tie-breaking tests, validate against planning docs |
| **Missing dispute integration** | Low | Medium | Verify dispute status in `verify_tournament_completion()` |
| **Admin permission issues** | Low | Low | Restrict admin actions (view-only), test with different user roles |

---

## 13. Questions for Clarification

### Q1: Tournament Status Transition
**Question:** Should winner determination automatically transition tournament from `COMPLETED` → `CONCLUDED`, or require manual organizer confirmation?  
**Planning Docs:** `PART_3.1_DATABASE_DESIGN_ERD.md` mentions `CONCLUDED` status but doesn't specify trigger  
**Recommendation:** Automatic transition after winner determined (can add organizer review flag if needed)

### Q2: Tie-Breaking Priority
**Question:** What is the default tie-breaking order if multiple rules apply?  
**Planning Docs:** `PHASE_5_IMPLEMENTATION_PLAN.md` lists 4 rules but no priority order  
**Recommendation:** 
1. Head-to-head record (if direct match exists)
2. Total score differential
3. Highest bracket position (seed)
4. Match completion time (tiebreaker of last resort)

### Q3: Runner-Up & 3rd Place Determination
**Question:** How to determine runner-up and 3rd place in single-elimination?  
**Recommendation:**
- **Runner-up:** Finals loser (straightforward)
- **3rd place:** Semi-finals losers (if 3rd place match exists, use that winner; otherwise pick higher seed)

### Q4: Forfeit Chain Edge Case
**Question:** If winner reaches finals via all forfeits, is this a valid win?  
**Recommendation:** Yes, valid (legitimate bracket progression), but set `determination_method = 'forfeit_default'` for audit trail

---

## 14. Pre-Implementation Checklist

- [x] Read PHASE_5_IMPLEMENTATION_PLAN.md (Module 5.1 section)
- [x] Read PART_2.2_SERVICES_INTEGRATION.md (bracket service, winner progression)
- [x] Read PART_3.1_DATABASE_DESIGN_ERD.md (Tournament, Bracket models)
- [x] Reviewed existing Bracket/BracketNode models
- [x] Verified no Phase 4 backlog dependencies
- [x] Created trace.yml Phase 5 stubs
- [x] Updated MAP.md Phase 5 scaffold
- [ ] **AWAITING APPROVAL:** Execution checklist + test plan reviewed by user
- [ ] Install dependencies (if needed): None for 5.1
- [ ] Create test file with skipped tests (scaffolding)
- [ ] Begin implementation (Step 1: Models & Migrations)

---

**Prepared by:** GitHub Copilot  
**Date:** November 9, 2025  
**Status:** Ready for review  
**Next Action:** Await user approval to proceed with implementation

