# USER PROFILE → TOURNAMENT INTEGRATION ROLLOUT PLAN

**Date:** 2024-12-24  
**Owner:** Platform Team  
**Status:** PRE-ROLLOUT (Integration complete, flag OFF, hooks NOT placed)

---

## 1. CURRENT SYSTEM STATUS

### ✅ COMPLETE (User Profile Side)

- **Integration Module:** `apps/user_profile/integrations/tournaments.py` (782 lines, 8 event handlers)
- **Test Coverage:** 16/16 integration tests passing
- **Idempotency:** Deterministic keys (no timestamps)
- **Transaction Safety:** All side effects in `transaction.on_commit()` callbacks
- **Error Handling:** All exceptions caught and logged (non-fatal)
- **Feature Flag:** `USER_PROFILE_INTEGRATION_ENABLED` (default: `False`, env-controlled)

### ❌ DISABLED (Not Active)

- **Flag Status:** OFF in all environments
- **Hook Placement:** Tournament services do NOT call integration
- **Production Impact:** Zero (integration completely inactive)

### 🔧 TOURNAMENT SIDE (No Changes Yet)

- **Current State:** Tournament operations work normally, no awareness of integration
- **Required Changes:** Add 6 integration call sites (detailed in §2)

---

## 2. EXACT HOOK LOCATIONS

### Service: `apps/tournaments/services/registration.py`

#### Hook 1: Registration Status Change
**Function:** `RegistrationService.update_registration_status()`  
**Location:** After `registration.save()` (status change committed)  
**Call:**
```python
from apps.user_profile.integrations.tournaments import on_registration_status_change

# After registration.status = new_status; registration.save()
on_registration_status_change(
    user_id=registration.user_id,
    tournament_id=registration.tournament_id,
    registration_id=registration.id,
    status=registration.status,
    actor_user_id=request.user.id if status in ['approved', 'rejected'] else None,
)
```

**Trigger Conditions:** Status changes to `submitted`, `approved`, `rejected`, `withdrawn`

---

### Service: `apps/tournaments/services/checkin.py`

#### Hook 2: Check-in Toggle
**Function:** `CheckinService.organizer_toggle_checkin()`  
**Location:** After `registration.checked_in = checked_in; registration.save()`  
**Call:**
```python
from apps.user_profile.integrations.tournaments import on_checkin_toggled

# After registration.save()
on_checkin_toggled(
    user_id=registration.user_id,
    tournament_id=registration.tournament_id,
    registration_id=registration.id,
    checked_in=registration.checked_in,
    actor_user_id=organizer_user.id,
)
```

**Trigger Conditions:** Organizer manually toggles check-in status

---

### Service: `apps/tournaments/services/match_results.py`

#### Hook 3: Match Result Submission
**Function:** `ResultSubmissionService.submit_result()`  
**Location:** After `submission.save()` (result recorded)  
**Call:**
```python
from apps.user_profile.integrations.tournaments import on_match_result_submitted

# After submission.save()
on_match_result_submitted(
    user_id=submitter_user_id,
    match_id=match.id,
    tournament_id=match.tournament_id,
    submission_id=submission.id,
    status='pending_opponent',  # or 'agreed', 'disputed'
)
```

**Trigger Conditions:** Player submits match result (any status)

---

### Service: `apps/tournaments/services/result_verification.py`

#### Hook 4: Match Finalized (CRITICAL - Stats Recompute)
**Function:** `ResultVerificationService.verify_submission()`  
**Location:** After `match.winner_id = winner_id; match.save()` (winner finalized)  
**Call:**
```python
from apps.user_profile.integrations.tournaments import on_match_finalized

# After match.save() (winner finalized)
winner_user_ids = match.get_winner_user_ids()  # Team/player user IDs
loser_user_ids = match.get_loser_user_ids()

on_match_finalized(
    match_id=match.id,
    tournament_id=match.tournament_id,
    winner_id=match.winner_id,
    loser_id=match.loser_id,
    winner_user_ids=winner_user_ids,
    loser_user_ids=loser_user_ids,
)
```

**Trigger Conditions:** Match result verified, winner finalized  
**CRITICAL:** Triggers stats recompute for all participants

---

### Service: `apps/tournaments/services/tournament_lifecycle.py`

#### Hook 5: Tournament Completed
**Function:** `TournamentLifecycleService.complete_tournament()`  
**Location:** After `tournament.status = 'completed'; tournament.save()`  
**Call:**
```python
from apps.user_profile.integrations.tournaments import on_tournament_completed

# After tournament.save()
participant_user_ids = tournament.get_all_participant_user_ids()
winner_user_ids = tournament.get_winner_user_ids()
top3_user_ids = tournament.get_top3_user_ids()

on_tournament_completed(
    tournament_id=tournament.id,
    actor_user_id=request.user.id,  # Organizer
    participant_user_ids=participant_user_ids,
    winner_user_ids=winner_user_ids,
    top3_user_ids=top3_user_ids,
)
```

**Trigger Conditions:** Tournament marked as completed  
**CRITICAL:** Bulk stats recompute for all participants

---

### Service: `apps/tournaments/services/disputes.py`

#### Hook 6A: Dispute Opened
**Function:** `DisputeService.create_dispute()`  
**Location:** After `dispute.save()` (dispute recorded)  
**Call:**
```python
from apps.user_profile.integrations.tournaments import on_dispute_opened

# After dispute.save()
on_dispute_opened(
    user_id=dispute.initiator_user_id,
    match_id=dispute.match_id,
    tournament_id=dispute.tournament_id,
    dispute_id=dispute.id,
    submission_id=dispute.submission_id,
    reason_code=dispute.reason_code,
)
```

#### Hook 6B: Dispute Resolved
**Function:** `DisputeService.resolve_dispute()`  
**Location:** After `dispute.resolution_type = resolution; dispute.save()`  
**Call:**
```python
from apps.user_profile.integrations.tournaments import on_dispute_resolved

# After dispute.save()
winner_user_ids = None
loser_user_ids = None

# Only if resolution finalizes match result
if resolution_type in ['approve_original', 'approve_dispute', 'custom_result']:
    winner_user_ids = dispute.match.get_winner_user_ids()
    loser_user_ids = dispute.match.get_loser_user_ids()

on_dispute_resolved(
    match_id=dispute.match_id,
    tournament_id=dispute.tournament_id,
    dispute_id=dispute.id,
    resolution_type=resolution_type,
    actor_user_id=organizer_user.id,
    winner_user_ids=winner_user_ids,
    loser_user_ids=loser_user_ids,
)
```

**Trigger Conditions:** Organizer resolves dispute  
**Conditional Stats Recompute:** Only if resolution finalizes match winner

---

### Service: `apps/economy/services/payments.py`

#### Hook 7: Payment Status Change
**Function:** `PaymentService.verify_payment()`, `reject_payment()`, `refund_payment()`  
**Location:** After payment transaction status updated  
**Call:**
```python
from apps.user_profile.integrations.tournaments import on_payment_status_change

# After payment.status = new_status; payment.save()
on_payment_status_change(
    user_id=payment.user_id,
    tournament_id=payment.tournament_id,
    transaction_id=payment.transaction_id,
    registration_id=payment.registration_id,
    status=payment.status,  # 'verified', 'rejected', 'refunded'
    actor_user_id=organizer_user.id,
    amount=payment.amount,
    reason=payment.rejection_reason or payment.refund_reason,
)
```

**Trigger Conditions:** Organizer verifies, rejects, or refunds payment

---

## 3. FEATURE FLAG ROLLOUT STRATEGY

### Phase 0: Pre-Rollout (CURRENT)
**Duration:** N/A  
**Flag:** `USER_PROFILE_INTEGRATION_ENABLED=False` (all environments)  
**Status:** Integration module complete, tests passing, no production impact

### Phase 1: Development Shadow Mode
**Duration:** 2-4 weeks  
**Flag:** `USER_PROFILE_INTEGRATION_ENABLED=True` (dev only)  
**Actions:**
1. Enable flag in local dev environment
2. Place all 7 hooks in tournament services
3. Run full test suite (expect 107/107 passing)
4. Manual testing: Create tournaments, register players, finalize matches
5. Verify UserActivity, UserAuditEvent, TournamentStats records created
6. Monitor logs for integration errors

**Success Criteria:**
- No tournament operations break
- Activity/audit events created correctly
- Stats recompute runs without errors
- No performance degradation (< 50ms overhead per operation)

### Phase 2: Staging Validation
**Duration:** 1-2 weeks  
**Flag:** `USER_PROFILE_INTEGRATION_ENABLED=True` (staging only)  
**Actions:**
1. Deploy to staging with flag enabled
2. Run smoke tests on staging (20+ tournaments, 100+ players)
3. Verify idempotency (duplicate calls create single records)
4. Monitor database growth (UserActivity, UserAuditEvent tables)
5. Load test: 100 concurrent match finalizations

**Success Criteria:**
- No duplicate UserActivity records (idempotency works)
- Database growth linear with tournament activity
- No transaction deadlocks
- Performance within acceptable range (< 100ms p95)

### Phase 3: Production Canary
**Duration:** 1 week  
**Flag:** `USER_PROFILE_INTEGRATION_ENABLED=True` (prod, 10% of tournaments)  
**Actions:**
1. Enable flag for 10% of tournaments (feature flag by tournament_id)
2. Monitor error rates, response times, database load
3. Compare canary vs control groups (tournament completion times)
4. Verify stats recompute correctness (spot-check 20 profiles)

**Success Criteria:**
- Error rate < 0.1%
- No latency increase for tournament operations
- Stats accuracy 100%
- No user-facing issues

### Phase 4: Production Full Rollout
**Duration:** Gradual (10% → 50% → 100%)  
**Flag:** `USER_PROFILE_INTEGRATION_ENABLED=True` (prod, all tournaments)  
**Actions:**
1. Increase to 50% of tournaments (1 week observation)
2. Increase to 100% of tournaments (1 week observation)
3. Monitor continuously for 2 weeks

**Success Criteria:**
- Integration stable at 100%
- No rollback required
- Stats recompute working for all users

---

## 4. RISK MATRIX

| Risk | Severity | Likelihood | Mitigation | Rollback |
|------|----------|------------|------------|----------|
| **Duplicate UserActivity records** | Medium | Low | Idempotency keys prevent duplicates | Disable flag, manual cleanup |
| **Stats recompute errors** | High | Medium | All exceptions caught, logged (non-fatal) | Disable flag, recompute stats offline |
| **Transaction deadlocks** | High | Low | `transaction.on_commit()` defers side effects | Disable flag immediately |
| **Performance degradation** | Medium | Medium | Integration adds < 50ms per operation | Disable flag, optimize queries |
| **Missing user_ids in calls** | Medium | Medium | Defensive coding in integration handlers | Fix tournament service code |
| **Database table growth** | Low | High | Expected (activity logging), monitor disk space | Archive old records |
| **Integration errors break tournaments** | Critical | Very Low | All errors caught (non-fatal), tournaments continue | No rollback needed (non-breaking) |

### Risk Mitigation Details

#### Duplicate Records
- **Prevention:** Deterministic idempotency keys (no timestamps)
- **Detection:** Query for duplicate keys in UserActivity table
- **Remediation:** Database unique constraint on `idempotency_key` (future enhancement)

#### Stats Recompute Errors
- **Prevention:** Try/catch in `_recompute_stats()` callback
- **Detection:** Monitor error logs for "Stats recompute failed"
- **Remediation:** Manual stats recompute via Django admin command

#### Transaction Deadlocks
- **Prevention:** `transaction.on_commit()` defers writes until tournament transaction commits
- **Detection:** Monitor PostgreSQL logs for deadlock errors
- **Remediation:** Disable flag, investigate lock contention

#### Performance Degradation
- **Prevention:** Integration adds minimal overhead (single function call)
- **Detection:** Monitor p95 latency for tournament operations
- **Remediation:** Optimize integration queries, add database indexes

---

## 5. REQUIRED TOURNAMENT-SIDE CHANGES

### Summary
- **Services Modified:** 6 (registration, checkin, match_results, result_verification, tournament_lifecycle, disputes, payments)
- **Functions Modified:** 7-10 (depends on service structure)
- **Lines Added:** ~70 (7 hooks × ~10 lines each)
- **Risk:** Low (all integration calls are non-breaking)

### Change Template (Per Hook)
```python
# 1. Import at top of file
from apps.user_profile.integrations.tournaments import on_[event_name]

# 2. Add call after relevant save()
try:
    on_[event_name](
        # Required parameters (see §2 for exact signatures)
    )
except Exception as e:
    # Optional: Log if needed (integration already logs internally)
    logger.debug(f"User profile integration call failed: {e}")
```

### Testing Requirements
- **Unit Tests:** Add 7 new tests (one per hook) verifying integration called with correct params
- **Integration Tests:** Existing 16 tests cover integration behavior (no changes needed)
- **System Tests:** End-to-end tournament flow with flag ON

### Code Review Checklist
- ✅ Hook placed AFTER relevant `save()` (transaction committed)
- ✅ All required parameters passed (user_id, tournament_id, etc.)
- ✅ User IDs extracted correctly (teams → individual users)
- ✅ Actor user ID passed for organizer actions
- ✅ Integration call wrapped in try/except (optional, already safe)

---

## 6. VERIFICATION CHECKLIST (Before Enabling Flag)

### Pre-Deployment
- [ ] All 7 hooks placed in tournament services
- [ ] Tournament service tests updated (7 new tests)
- [ ] Integration tests passing (16/16)
- [ ] Full test suite passing (107/107)
- [ ] Code review completed (2+ reviewers)
- [ ] Database migrations applied (UserActivity, UserAuditEvent, TournamentStats tables exist)

### Staging Validation
- [ ] Flag enabled in staging (`USER_PROFILE_INTEGRATION_ENABLED=True`)
- [ ] Smoke test: Create 5 tournaments, 20 players, 50 matches
- [ ] Verify UserActivity records created (count matches events)
- [ ] Verify UserAuditEvent records created (organizer actions only)
- [ ] Verify TournamentStats updated (spot-check 5 profiles)
- [ ] Verify idempotency (submit same match result twice, check single record)
- [ ] Monitor error logs (no integration errors)
- [ ] Performance baseline (measure p95 latency for match finalization)

### Production Readiness
- [ ] Staging validation passed (all criteria met)
- [ ] Rollback plan documented (§7)
- [ ] On-call engineer briefed (know how to disable flag)
- [ ] Monitoring dashboards configured (error rates, latency)
- [ ] Database disk space verified (sufficient for 3 months growth)
- [ ] Feature flag infrastructure tested (can toggle without deploy)

### Post-Deployment (First 24h)
- [ ] Monitor error logs every 4 hours
- [ ] Check UserActivity table growth (linear with events)
- [ ] Verify stats recompute accuracy (spot-check 10 profiles)
- [ ] Compare tournament operation latency (pre vs post)
- [ ] User-facing issues reported (check support tickets)

---

## 7. STOP CONDITIONS (When NOT to Enable)

### Critical Blockers (DO NOT ENABLE)
1. **Test Failures:** Any integration test failing (< 16/16 passing)
2. **Missing Tables:** UserActivity, UserAuditEvent, or TournamentStats tables don't exist
3. **Staging Errors:** Integration errors in staging logs (> 1% error rate)
4. **Performance Issues:** Staging latency increased > 100ms for any operation
5. **Transaction Errors:** Any deadlock or transaction rollback errors in staging

### Warning Signs (PROCEED WITH CAUTION)
1. **Duplicate Records:** Idempotency not working (same event creates multiple records)
2. **Stats Inaccuracy:** TournamentStats values don't match manual calculation
3. **Missing Data:** UserActivity records missing for some events
4. **Slow Stats Recompute:** `TournamentStatsService.recompute_user_stats()` takes > 5s
5. **Database Growth:** UserActivity table growing faster than expected (> 1M rows/day)

### Immediate Rollback Triggers (Production)
1. **Error Spike:** Integration error rate > 1%
2. **Latency Spike:** Tournament operation p95 latency increases > 200ms
3. **Database Issues:** Connection pool exhaustion, deadlocks, or high CPU
4. **User Impact:** Tournament operations failing or delayed
5. **Data Corruption:** Incorrect stats visible to users

### Rollback Procedure
1. Set `USER_PROFILE_INTEGRATION_ENABLED=False` (environment variable)
2. Restart application servers (no code deploy needed)
3. Verify tournament operations return to normal
4. Investigation: Check logs, database queries, transaction traces
5. Fix root cause before re-enabling

---

## 8. MONITORING & OBSERVABILITY

### Key Metrics
- **Integration Calls:** Count per event type (registration, checkin, match, etc.)
- **Error Rate:** Integration exceptions per 1000 calls
- **Latency:** Time spent in integration handlers (p50, p95, p99)
- **Database Growth:** UserActivity table size (rows, disk space)
- **Stats Recompute:** Success rate, duration, errors

### Log Queries
```bash
# Integration errors
grep "Tournament integration error" /var/log/deltacrown/app.log

# Stats recompute failures
grep "Stats recompute failed" /var/log/deltacrown/app.log

# Integration calls (info level)
grep "Tournament integration:" /var/log/deltacrown/app.log | wc -l
```

### Database Queries
```sql
-- UserActivity growth by day
SELECT DATE(created_at), COUNT(*) 
FROM user_profile_useractivity 
GROUP BY DATE(created_at) 
ORDER BY DATE(created_at) DESC;

-- Duplicate idempotency keys (should be 0)
SELECT idempotency_key, COUNT(*) 
FROM user_profile_useractivity 
GROUP BY idempotency_key 
HAVING COUNT(*) > 1;

-- Stats recompute activity (last 24h)
SELECT event_type, COUNT(*) 
FROM user_profile_useractivity 
WHERE created_at > NOW() - INTERVAL '24 hours' 
GROUP BY event_type;
```

---

## 9. SUCCESS CRITERIA

### Phase 1 (Dev) Success
- ✅ 16/16 integration tests passing
- ✅ Tournament operations work normally
- ✅ UserActivity/UserAuditEvent records created
- ✅ No integration errors in logs

### Phase 2 (Staging) Success
- ✅ Idempotency verified (no duplicate records)
- ✅ Stats accuracy 100% (spot-checked)
- ✅ Performance within limits (< 100ms overhead)
- ✅ No transaction errors

### Phase 3 (Prod Canary) Success
- ✅ Error rate < 0.1%
- ✅ No latency increase
- ✅ Canary group stats accurate
- ✅ No user complaints

### Phase 4 (Full Rollout) Success
- ✅ Integration stable at 100%
- ✅ Stats recompute working for all users
- ✅ Database growth as expected
- ✅ No rollbacks in 2 weeks

---

## 10. REFERENCES

- **Integration Contract:** `Documents/UserProfile_CommandCenter_v1/03_Planning/UP_TOURNAMENT_INTEGRATION_CONTRACT.md`
- **Integration Module:** `apps/user_profile/integrations/tournaments.py`
- **Integration Tests:** `apps/user_profile/tests/test_tournament_integration.py`
- **Feature Flag:** `deltacrown/settings.py` (line 899)
- **Rollout Report:** `Documents/UserProfile/Integration/UP_INTEG_FIX_01_REPORT.md`

---

**END OF ROLLOUT PLAN**

**Next Action:** Place 7 hooks in tournament services (§2), then proceed with Phase 1 (dev testing).
