# UP↔TOURNAMENT INTEGRATION CONTRACT

**Date:** December 24, 2025  
**Status:** CONTRACT DEFINED + SCAFFOLDING IMPLEMENTED (FLAG OFF)  
**Feature Flag:** `USER_PROFILE_INTEGRATION_ENABLED` (default: False)

---

## PURPOSE

Define minimal, clean integration points between User Profile system and Tournament/Tournament_Ops apps. This contract enables:
1. **Activity Tracking**: Log user actions in tournaments (registration, check-in, match participation, disputes)
2. **Stats Recompute**: Trigger UserProfileStats recalculation when match/tournament results finalize
3. **Audit Trail**: Record admin/organizer actions for compliance

**Design Principles:**
- **Non-Breaking**: Does NOT change tournament business logic
- **Idempotent**: Safe to call multiple times (uses idempotency keys)
- **Flag-Guarded**: All integration calls short-circuit when `USER_PROFILE_INTEGRATION_ENABLED=False`
- **Lightweight**: No heavy computation in sync paths (defer stats recompute if needed)

---

## INTEGRATION EVENTS

### Event 1: Registration Status Change
**Source:** `apps/tournament_ops/services/registration_service.py`  
**Trigger Methods:**
- `start_registration()` → status: "submitted"
- `complete_registration()` → status: "confirmed" (after payment)
- Hypothetical `approve_registration()` → status: "approved" (organizer action)
- Hypothetical `reject_registration()` → status: "rejected" (organizer action)

**Hook Point:** After registration status changes (end of service method)

**User Profile Actions:**
- **Activity Event**: `tournament.registration.{status}` (e.g., `tournament.registration.submitted`, `tournament.registration.confirmed`)
- **Audit Event** (organizer actions only): Record admin/organizer approval/rejection
- **Stats Recompute**: NO (no stats change until tournament completes)

**Payload Schema:**
```python
{
    'user_id': int,                    # Player who registered
    'tournament_id': int,              # Tournament ID
    'registration_id': int,            # Registration ID
    'team_id': Optional[int],          # Team ID (None for solo)
    'status': str,                     # 'submitted', 'confirmed', 'approved', 'rejected'
    'actor_user_id': Optional[int],    # Organizer/admin who approved/rejected
    'reason': Optional[str],           # Rejection reason (if applicable)
}
```

**Idempotency Key Format:**
```
registration_status:{registration_id}:{status}
```

**Example:** `registration_status:123:confirmed`

**CRITICAL:** Keys are deterministic (no timestamps) to ensure true idempotency.
Same event + same data = same key = single record.

---

### Event 2: Check-In Status Change
**Source:** `apps/tournaments/models.py` (TournamentRegistration.toggle_checkin or similar)  
**Trigger Methods:**
- `organizer_toggle_checkin(registration_id, checked_in: bool, actor_user_id: int)`

**Hook Point:** After check-in status toggled

**User Profile Actions:**
- **Activity Event**: `tournament.checkin.{checked_in|checked_out}`
- **Audit Event**: Record organizer who toggled check-in
- **Stats Recompute**: NO

**Payload Schema:**
```python
{
    'user_id': int,
    'tournament_id': int,
    'registration_id': int,
    'checked_in': bool,
    'actor_user_id': int,  # Organizer
}
```

**Idempotency Key Format:**
```
checkin:{registration_id}:{checked_in}
```

**Example:** `checkin:123:True`

---

### Event 3: Match Result Submitted
**Source:** `apps/tournament_ops/services/result_submission_service.py`  
**Trigger Methods:**
- `submit_result()` → submission created (PENDING_OPPONENT)
- `opponent_response()` → opponent accepts/disputes

**Hook Point:** After result submission saved

**User Profile Actions:**
- **Activity Event**: `tournament.match.result_submitted`
- **Stats Recompute**: NO (wait for finalization)

**Payload Schema:**
```python
{
    'user_id': int,          # Submitter
    'match_id': int,
    'tournament_id': int,
    'submission_id': int,
    'status': str,           # 'pending_opponent', 'accepted', 'disputed'
}
```

**Idempotency Key Format:**
```
match_result_submission:{submission_id}:{status}
```

**Example:** `match_result_submission:456:pending_opponent`

---

### Event 4: Match Finalized (Result Verified)
**Source:** `apps/tournament_ops/services/result_verification_service.py`  
**Trigger Methods:**
- `verify_submission()` → result finalized (updates Match.winner_id)

**Hook Point:** After Match.winner_id updated

**User Profile Actions:**
- **Activity Event**: `tournament.match.finalized`
- **Stats Recompute**: **YES** → Trigger `TournamentStatsService.recompute_user_stats()` for BOTH participants
  - This recalculates matches_played, matches_won from source Match table
- **Audit Event**: NO (automatic verification, not manual action)

**Payload Schema:**
```python
{
    'match_id': int,
    'tournament_id': int,
    'winner_id': int,          # Team/player ID
    'loser_id': int,           # Team/player ID
    'winner_user_ids': List[int],  # All users in winning team/player
    'loser_user_ids': List[int],   # All users in losing team/player
}
```

**Idempotency Key Format:*
```

**Example:** `match_finalized:789`
match_finalized:{match_id}:{timestamp}
```

**Stats Recompute Strategy:**
- Enqueue Celery task `recompute_user_stats_async(user_ids)` if Celery enabled
- Otherwise: Call `TournamentStatsService.recompute_user_stats(user_id)` synchronously for each user
- Recompute is idempotent (safe to call multiple times)

---

### Event 5: Tournament Completed
**Source:** `apps/tournaments/models.py` (Tournament.status → 'completed')  
**Trigger Methods:**
- Hypothetical `complete_tournament(tournament_id, actor_user_id)`

**Hook Point:** After Tournament.status = 'completed' and TournamentResult records created

**User Profile Actions:**
- **Activity Event**: `tournament.completed` (for ALL participants)
- **Stats Recompute**: **YES** → Trigger `TournamentStatsService.recompute_user_stats()` for ALL participants
  - Recalculates tournaments_played, tournaments_won, tournaments_top3
- **Audit Event**: YES (organizer action) → Record who completed tournament

**Payload Schema:**
```python
{
    'tournament_id': int,
    'actor_user_id': int,      # Organizer who completed tournament
    'participant_user_ids': List[int],  # All users who participated
    'winner_user_ids': List[int],       # All users in winning team/player
    'top3_user_ids': List[int],         # All users in top 3 placements
}
```

**Idempotency Key Format:**
```

**Example:** `tournament_completed:42`
tournament_completed:{tournament_id}:{timestamp}
```

---

### Event 6: Dispute Opened
**Source:** `apps/tournament_ops/services/dispute_service.py`  
**Trigger Methods:**
- `opponent_response()` in ResultSubmissionService (creates dispute)

**Hook Point:** After Dispute record created

**User Profile Actions:**
- **Activity Event**: `tournament.dispute.opened`
- **Stats Recompute**: NO
- **Audit Event**: NO (automatic, not organizer action)

**Payload Schema:**
```python
{
    'user_id': int,          # Disputer
    'match_id': int,
    'tournament_id': int,
    'dispute_id': int,
    'submission_id': int,
    'reason_code': str,
}
```

**Idempotency Key Format:**
```

**Example:** `dispute_opened:999`
dispute_opened:{dispute_id}:{timestamp}
```

---

### Event 7: Dispute Resolved
**Source:** `apps/tournament_ops/services/dispute_service.py`  
**Trigger Methods:**
- `resolve_dispute()` → organizer resolves dispute (4 resolution types)

**Hook Point:** After dispute status updated to 'resolved'

**User Profile Actions:**
- **Activity Event**: `tournament.dispute.resolved`
- **Stats Recompute**: **YES** (if resolution finalizes match result) → Same as Event 4
- **Audit Event**: YES → Record organizer who resolved dispute

**Payload Schema:**
```python
{
    'match_id': int,
    'tournament_id': int,
    'dispute_id': int,
    'resolution_type': str,  # 'approve_original', 'approve_dispute', 'custom_result', 'dismiss_dispute'
    'actor_user_id': int,    # Organizer who resolved
    'winner_user_ids': Optional[List[int]],  # If result finalized
    'loser_user_ids': Optional[List[int]],
}
```
```

**Example:** `dispute_resolved:999:approve_original
**Idempotency Key Format:**
```
dispute_resolved:{dispute_id}:{resolution_type}:{timestamp}
```

---

### Event 8: Payment Status Change
**Source:** `apps/tournament_ops/services/payment_service.py` or `apps/economy/`  
**Trigger Methods:**
- `verify_payment()` → payment verified
- `reject_payment()` → payment rejected
- `refund_payment()` → payment refunded

**Hook Point:** After payment status updated

**User Profile Actions:**
- **Activity Event**: `tournament.payment.{verified|rejected|refunded}`
- **Audit Event**: YES (organizer action) → Record who verified/rejected/refunded
- **Stats Recompute**: NO (payment doesn't affect stats)

**Payload Schema:**
```python
{
    'user_id': int,
    'tournament_id': int,
    'transaction_id': str,
    'registration_id': int,
    'status': str,           # 'verified', 'rejected', 'refunded'
    'actor_user_id': int,    # Organizer
    'amount': Decimal,
    'reason': Optional[str], # Rejection/refund reason
}
```
```

**Example:** `payment:TXN123:verified
**Idempotency Key Format:**
```
payment:{transaction_id}:{status}:{timestamp}
```

---

## IDEMPOTENCY STRdeterministic `idempotency_key` in UserAuditEvent and UserActivity metadata
- **Format:** `{event_type}:{primary_key}:{status}` (NO timestamps)
- **Example:** `registration_status:123:confirmed`
- **Storage:** Stored in metadata JSON for UserActivity, native field for UserAuditEvent
- **Check:** Query for existing record with same idempotency_key before insert

**CRITICAL Design Decision:**
- **Timestamps REMOVED** from idempotency keys (as of Dec 24, 2025)
- **Why:** Timestamps made keys unique on every call, defeating idempotency
- **Now:** Same event data = same key = single record (true idempotency)

**Implementation:**
```python
# apps/user_profile/integrations/tournaments.py
def _generate_idempotency_key(event_type: str, primary_key: str, status: str = '') -> str:
    """Generate deterministic idempotency key (no timestamps)."""
    if status:
        return f"{event_type}:{primary_key}:{status}"
    return f"{event_type}:{primary_key}"

# Before insert:
existing = UserActivity.objects.filter(
    user_id=user_id,
    event_type=event_type,
    metadata__idempotency_key=idempotency_key
).first()

if existing:
    return  # Already recorded, skip
```

**Formats:**
- `registration_status:{registration_id}:{status}` → `registration_status:123:confirmed`
- `checkin:{registration_id}:{checked_in}` → `checkin:123:True`
- `match_finalized:{match_id}` → `match_finalized:789`
- `tournament_completed:{tournament_id}` → `tournament_completed:42`
- `dispute_opened:{dispute_id}` → `dispute_opened:999`
- `dispute_resolved:{dispute_id}:{resolution_type}` → `dispute_resolved:999:approve_original`
- `payment:{transaction_id}:{status}` → `payment:TXN123:verified`

**Implementation:**
- AuditService already supports idempotency_key parameter
- ActivityService will check for duplicate idempotency_key before insert

---

## AUDIT STRATEGY

**What Gets Audited:**
- **YES**: Organizer/admin actions (approve/reject/resolve/verify/toggle)
- **NO**: Automatic system actions (player registration submission, automatic verification)

**Audit Record Fields:**
- `subject_user_id`: User affected by action
- `event_type`: From UserAuditEvent.EventType (add new types as needed)
- `source_app`: 'tournaments' or 'tournament_ops'
- `object_type`: 'Registration', 'Match', 'Dispute', 'Payment'
- `object_id`: ID of registration/match/dispute/payment
- `actor_user_id`: Organizer/admin who performed action
- `before_snapshot`: State before action (if applicable)
- `after_snapshot`: State after action
- `metadata`: Additional context (rejection reason, resolution type, etc.)

**New Event Types to Add:**
```python
# In apps/user_profile/models/audit.py UserAuditEvent.EventType
REGISTRATION_APPROVED = 'registration_approved'
REGISTRATION_REJECTED = 'registration_rejected'
CHECKIN_TOGGLED = 'checkin_toggled'
DISPUTE_RESOLVED = 'dispute_resolved'
PAYMENT_VERIFIED = 'payment_verified'
PAYMENT_REJECTED = 'payment_rejected'
PAYMENT_REFUNDED = 'payment_refunded'
```

---

## STATS RECOMPUTE STRATEGY

**When to Recompute:**
- Match finalized (Event 4) → Recompute matches_played, matches_won for participants
- Tournament completed (Event 5) → Recompute tournaments_played, tournaments_won, tournaments_top3 for participants
- Dispute resolved with finalization (Event 7) → Same as Event 4

**What Gets Recomputed:**
- `UserProfileStats.matches_played`
- `UserProfileStats.matches_won`
- `UserProfileStats.tournaments_played`
- `UserProfileStats.tournaments_won`
- `UserProfileStats.tournaments_top3`

**Recompute Method:**
- Use `TournamentStatsService.recompute_user_stats(user_id)`
- Service queries source tables (Match, Tournament, Registration, TournamentResult)
- Idempotent (safe to call multiple times)
- Deterministic (same source data = same stats)

**Transaction Safety:**
- **CRITICAL:** All integration side effects (UserActivity, UserAuditEvent, stats recompute) 
  run inside `transaction.on_commit()` callbacks
- **Why:** Ensures tournament transaction commits successfully BEFORE side effects execute
- **Result:** If tournament operation fails and rolls back, integration side effects don't execute
- **Implementation:** All integration functions wrap DB writes/recompute in `transaction.on_commit(lambda: ...)`

**Async Strategy:**
- If Celery available: Enqueue task `recompute_user_stats_async.delay(user_id)`
- Otherwise: Call synchronously (lightweight for single user)
- For bulk operations (tournament completed): Batch enqueue tasks

---

## ACTUAL HOOK MAP (AS IMPLEMENTED)

**Status:** Contract defined, scaffolding implemented, **hooks NOT yet placed in tournament services**

This section documents where hooks SHOULD be placed vs. where they currently ARE.

### ✅ Implemented (Integration Module Ready)
**File:** `apps/user_profile/integrations/tournaments.py` (740 lines)

**Functions Available:**
1. `on_registration_status_change()` - Ready for registration service
2. `on_checkin_toggled()` - Ready for check-in toggle
3. `on_match_result_submitted()` - Ready for result submission
4. `on_match_finalized()` - Ready for result verification
5. `on_tournament_completed()` - Ready for tournament completion
6. `on_dispute_opened()` - Ready for dispute creation
7. `on_dispute_resolved()` - Ready for dispute resolution
8. `on_payment_status_change()` - Ready for payment verification

**All functions:**
- Feature-flag guarded (`USER_PROFILE_INTEGRATION_ENABLED`)
- Use deterministic idempotency keys
- Run side effects in `transaction.on_commit()`
- Catch and log errors (non-fatal)

---

### ❌ NOT YET HOOKED (Future Work)

The following tournament services exist but do NOT yet call integration functions.
This is intentional - integration is opt-in via feature flag.

**Registration Flow:**
- **File:** `apps/tournament_ops/services/registration_service.py`
- **Methods:** `start_registration()`, `complete_registration()`
- **Hook Needed:** Add `on_registration_status_change()` calls at end of methods
- **Status:** ❌ Not implemented (integration module ready, service hooks missing)

**Check-In:**
- **File:** TBD (check-in service not yet refactored into tournament_ops)
- **Method:** Hypothetical `organizer_toggle_checkin()`
- **Hook Needed:** Add `on_checkin_toggled()` call
- **Status:** ❌ Service doesn't exist yet

**Match Result Submission:**
- **File:** `apps/tournament_ops/services/result_submission_service.py` (likely)
- **Methods:** `submit_result()`, `opponent_response()`
- **Hook Needed:** Add `on_match_result_submitted()` calls
- **Status:** ❌ Not implemented

**Match Finalization:**
- **File:** `apps/tournament_ops/services/result_verification_service.py`
- **Method:** `verify_submission()` (after Match.winner_id updated)
- **Hook Needed:** Add `on_match_finalized()` call
- **Status:** ❌ Not implemented (CRITICAL - this triggers stats recompute)

**Tournament Completion:**
- **File:** `apps/tournaments/models.py` or tournament service
- **Method:** Hypothetical `complete_tournament()`
- **Hook Needed:** Add `on_tournament_completed()` call
- **Status:** ❌ Service doesn't exist yet

**Dispute Flow:**
- **File:** `apps/tournament_ops/services/dispute_service.py`
- **Methods:** `create_dispute()`, `resolve_dispute()`
- **Hook Needed:** Add `on_dispute_opened()` and `on_dispute_resolved()` calls
- **Status:** ❌ Not implemented

**Payment Verification:**
- **File:** `apps/tournament_ops/services/payment_service.py` or economy adapter
- **Methods:** `verify_payment()`, `reject_payment()`, `refund_payment()`
- **Hook Needed:** Add `on_payment_status_change()` calls
- **Status:** ❌ Not implemented

---

### 📋 Hook Placement Checklist (Phase 1 Implementation)

When ready to enable integration, add hooks in this order:

**Priority 1 (Match Stats):**
- [ ] `ResultVerificationService.verify_submission()` → `on_match_finalized()`
- [ ] Test with flag ON, verify matches_played/matches_won update correctly

**Priority 2 (Tournament Stats):**
- [ ] Tournament completion logic → `on_tournament_completed()`
- [ ] Test with flag ON, verify tournaments_played/won/top3 update correctly

**Priority 3 (Activity Tracking):**
- [ ] `RegistrationService` → `on_registration_status_change()`
- [ ] `ResultSubmissionService` → `on_match_result_submitted()`
- [ ] `DisputeService` → `on_dispute_opened()`, `on_dispute_resolved()`

**Priority 4 (Audit Trail):**
- [ ] Check-in toggle → `on_checkin_toggled()`
- [ ] Payment verification → `on_payment_status_change()`

**Verification After Each Hook:**
```bash
# Flag OFF (default) - no side effects
pytest apps/tournament_ops/tests/

# Flag ON - verify integration
USER_PROFILE_INTEGRATION_ENABLED=True pytest apps/tournament_ops/tests/
pytest apps/user_profile/tests/test_tournament_integration.py
```

---

## ROLLOUT PLAN

### Phase 0: Contract + Scaffolding (CURRENT)
**Status:** ✅ COMPLETE  
**Flag:** OFF (default: False)

**Deliverables:**
- This contract document
- Integration module with flag-guarded functions
- Hook calls in tournament services (no-op when flag OFF)
- Basic tests verifying flag behavior

**Verification:**
```bash
# Flag OFF (default) - no integration
python manage.py check
pytest apps/user_profile/tests/
pytest apps/tournament_ops/tests/
```

---

### Phase 1: Shadow Mode (TESTING)
**Status:** NOT STARTED  
**Flag:** ON (manually enabled in test environments)

**Goal:** Verify integration works WITHOUT affecting production behavior

**Activities:**
1. Enable flag in test/staging: `USER_PROFILE_INTEGRATION_ENABLED = True`
2. Monitor logs for integration calls
3. Verify activity/audit records created correctly
4. Verify stats recompute works (compare with manual queries)
5. Load test: Ensure no performance regression

**Success Criteria:**
- No errors in integration calls
- Activity events match expected patterns
- Stats recompute produces correct values (verified manually)
- No performance degradation (<50ms p99 overhead)

**Rollback:** Set flag to False if errors occur

---

### Phase 2: Production Rollout (GRADUAL)
**Status:** NOT STARTED  
**Flag:** ON (default: True)

**Goal:** Enable integration in production

**Activities:**
1. Enable flag in production: `USER_PROFILE_INTEGRATION_ENABLED = True`
2. Monitor for 7 days:
   - Error rates in integration calls
   - Activity event creation rates
   - Stats recompute timing (should be <1s per user)
   - Audit log growth (estimate storage needs)
3. Backfill historical data (optional):
   - Run `recompute_user_stats` for all users
   - Backfill activity events for past 30 days (if needed)

**Success Criteria:**
- Zero integration errors for 7 days
- Stats match manual queries for 100 random users
- No user complaints about incorrect stats

**Rollback:** Set flag to False, investigate issues, fix, re-enable

---

### Phase 3: Deprecate Flag (CLEANUP)
**Status:** NOT STARTED  

**Goal:** Remove feature flag after 30 days of stable production

**Activities:**
1. Remove `if not USER_PROFILE_INTEGRATION_ENABLED` checks
2. Remove flag from settings
3. Update this document to mark integration as "ALWAYS ON"

---

## TESTING STRATEGY

### Unit Tests (apps/user_profile/tests/test_tournament_integration.py)
**Scope:** Test integration module in isolation

**Test Cases:**
1. Flag OFF → All functions return early (no DB writes)
2. Flag ON → Activity events created with correct payload
3. Flag ON → Audit events created for organizer actions
4. Flag ON → Stats recompute called with correct user_ids
5. Idempotency → Duplicate calls don't create duplicate records

**Mock Strategy:**
- Mock `TournamentStatsService.recompute_user_stats()` (verify call args, don't execute)
- Mock `ActivityService.record_event()` (verify call args)
- Mock `AuditService.record_event()` (verify call args)

---

### Integration Tests (apps/tournament_ops/tests/)
**Scope:** Test tournament services with integration enabled

**Test Cases:**
1. Registration flow → Verify activity events created
2. Match finalization → Verify stats recompute triggered
3. Tournament completion → Verify audit event + stats recompute
4. Dispute resolution → Verify audit event + conditional stats recompute

**Setup:**
- Enable flag: `settings.USER_PROFILE_INTEGRATION_ENABLED = True`
- Use real DB (or test fixtures)
- Verify UserActivity/UserAuditEvent/UserProfileStats records created

---

### Performance Tests (smoke tests)
**Scope:** Ensure integration doesn't degrade tournament operations

**Test Cases:**
1. Registration with integration ON vs OFF (measure latency)
2. Match finalization with integration ON vs OFF
3. Tournament completion with 100 participants (measure stats recompute time)

**Success Criteria:**
- <50ms p99 overhead for registration/check-in
- <100ms p99 overhead for match finalization (includes stats recompute)
- <10s total for tournament completion with 100 participants

---

## IMPLEMENTATION CHECKLIST

### Core Integration Module
- [x] Create `apps/user_profile/integrations/tournaments.py`
- [x] Add feature flag `USER_PROFILE_INTEGRATION_ENABLED` to settings
- [x] Implement flag-guarded functions for each event type
- [x] Add idempotency key generation helpers
- [x] Add audit event type constants

### Hook Calls (Tournament Services)
- [ ] RegistrationService: Hook `start_registration()`, `complete_registration()` (**NOT YET DONE**)
- [ ] CheckinService: Hook check-in toggle (**Service doesn't exist yet**)
- [ ] ResultVerificationService: Hook `verify_submission()` (Event 4) (**NOT YET DONE - CRITICAL**)
- [ ] TournamentService: Hook tournament completion (Event 5) (**NOT YET DONE**)
- [ ] DisputeService: Hook `resolve_dispute()` (Event 7) (**NOT YET DONE**)
- [ ] PaymentService: Hook payment verification/rejection/refund (Event 8) (**NOT YET DONE**)

**Note:** Integration module is complete and tested. Tournament service hooks are NOT yet placed.
This is intentional - integration is opt-in and controlled by feature flag.

### Tests
- [x] Unit tests for integration module (flag behavior, idempotency)
- [ ] Integration tests for registration flow
- [ ] Integration tests for match finalization
- [ ] Integration tests for tournament completion

### Documentation
- [x] This contract document
- [ ] Update tournament service docstrings with integration notes
- [ ] Add migration guide for enabling flag in production

---

## APPENDIX: Integration Module API

### Function Signatures

```python
# apps/user_profile/integrations/tournaments.py

def on_registration_status_change(
    user_id: int,
    tournament_id: int,
    registration_id: int,
    status: str,
    team_id: Optional[int] = None,
    actor_user_id: Optional[int] = None,
    reason: Optional[str] = None,
) -> None:
    """Record activity/audit for registration status change."""
    pass

def on_checkin_toggled(
    user_id: int,
    tournament_id: int,
    registration_id: int,
    checked_in: bool,
    actor_user_id: int,
) -> None:
    """Record activity/audit for check-in toggle."""
    pass

def on_match_result_submitted(
    user_id: int,
    match_id: int,
    tournament_id: int,
    submission_id: int,
    status: str,
) -> None:
    """Record activity for match result submission."""
    pass

def on_match_finalized(
    match_id: int,
    tournament_id: int,
    winner_id: int,
    loser_id: int,
    winner_user_ids: List[int],
    loser_user_ids: List[int],
) -> None:
    """Record activity and trigger stats recompute for match finalization."""
    pass

def on_tournament_completed(
    tournament_id: int,
    actor_user_id: int,
    participant_user_ids: List[int],
    winner_user_ids: List[int],
    top3_user_ids: List[int],
) -> None:
    """Record activity/audit and trigger stats recompute for tournament completion."""
    pass

def on_dispute_opened(
    user_id: int,
    match_id: int,
    tournament_id: int,
    dispute_id: int,
    submission_id: int,
    reason_code: str,
) -> None:
    """Record activity for dispute opened."""
    pass

def on_dispute_resolved(
    match_id: int,
    tournament_id: int,
    dispute_id: int,
    resolution_type: str,
    actor_user_id: int,
    winner_user_ids: Optional[List[int]] = None,
    loser_user_ids: Optional[List[int]] = None,
) -> None:
    """Record activity/audit and conditionally trigger stats recompute for dispute resolution."""
    pass

def on_payment_status_change(
    user_id: int,
    tournament_id: int,
    transaction_id: str,
    registration_id: int,
    status: str,
    actor_user_id: int,
    amount: Decimal,
    reason: Optional[str] = None,
) -> None:
    """Record activity/audit for payment status change."""
    pass
```

---

**Document Version:** 1.0  
**Last Updated:** December 24, 2025  
**Maintained By:** Platform Architecture Team
