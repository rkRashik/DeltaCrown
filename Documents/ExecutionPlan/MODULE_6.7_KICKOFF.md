# Module 6.7 Kickoff - Realtime Coverage Carry-Forward + Fuzz Testing

**Module**: 6.7 - Coverage Carry-Forward (Utils Batching, Match Consumer Lifecycle, Rate-Limit Enforcement)  
**Status**: 🔄 In Progress  
**Start Date**: 2025-11-11  
**Implements**: Module 6.6 carry-forward items + PHASE_6_IMPLEMENTATION_PLAN.md#module-67

---

## 🎯 Module Objectives

Complete the three carry-forward coverage gaps from Module 6.6, bringing realtime package coverage from 45% → **target ≥65%** overall.

**Rationale**: Module 6.6 achieved substantial uplift (+19% absolute) but stopped at 45% due to diminishing returns and test-only constraints. Module 6.7 completes the high-value remaining work with focused surgical tests.

---

## 📋 Work Items (Sequential)

### Step 1: Utils Batching Coverage (~2-3 hours) ⏳ IN PROGRESS
**Target**: `apps/tournaments/realtime/utils.py` from **29% → ≥65%** (+36% gap)

**Current State**: 
- Coverage: 29% (121 statements, 86 missed)
- Uncovered: Lines 153-261 (batch processing, debouncing, sequence numbers)

**Approach**: Monkeypatch batch windows to 5-20ms, use in-memory channel layer, assert emitted messages

**Tests to Add (8-10)**:
1. **Latest-wins coalescing**: Burst of updates → verify only final payload emitted
2. **Monotonic sequence numbers**: Across multiple batches
3. **Terminal flush path**: Immediate flush for terminal events (match_completed, etc.)
4. **Cancel on disconnect**: No leftover tasks after consumer disconnect
5. **Per-match lock**: Prevents interleaved sends across two matches
6. **Back-pressure recovery**: Burst → cool-down → recovery window
7. **Error branch**: Malformed event dropped without emit (if applicable)
8. **Batch window timing**: Verify configurable BATCH_WINDOW respected
9. **Empty batch handling**: No emit when batch window expires with no events
10. **Concurrent matches**: Multiple matches batching independently

**Acceptance Criteria**:
- ✅ 8-10 deterministic tests passing
- ✅ utils.py coverage ≥65%
- ✅ Per-file coverage table with before/after/Δ
- ✅ Coverage artifact saved to `Artifacts/coverage/module_6_7/`

**Deliverables**:
- `tests/test_utils_batching_module_6_7.py`
- Coverage measurement and documentation

---

### Step 2: Match Consumer Lifecycle (~4-5 hours) 📅 PLANNED
**Target**: `apps/tournaments/realtime/match_consumer.py` from **19% → ≥55%** (+36% gap)

**Current State**:
- Coverage: 19% (132 statements, 107 missed)
- Uncovered: Lines 131-242, 274-288, 482-543 (match lifecycle state machine)

**Approach**: Integration tests with committed membership fixtures, test ASGI mounting

**Tests to Add (15-20)**:
1. **Valid connect**: Authenticated user with valid match membership
2. **Role-gated action success**: Organizer performs organizer-only action
3. **Role-gated action denial**: Participant attempts organizer-only → exact close code
4. **Malformed JSON**: Invalid JSON → schema error response
5. **Missing required fields**: Event missing 'type' → error response
6. **Unknown message type**: Unrecognized type → ignored/warning
7. **State transition**: Start → update → finalize (mock service layer)
8. **Reconnect with in-flight batch**: Ensure no duplicate emits
9. **Graceful disconnect**: Proper group leave and task cleanup
10. **Timeout disconnect**: Connection timeout handling
11. **Unauthorized room join**: Wrong tournament/match ID → rejection
12. **Invalid match ID**: Non-existent match → rejection
13. **Match state validation**: Action invalid for current state → error
14. **Concurrent organizers**: Multiple organizers, no race conditions
15. **Participant read-only**: Participant receives updates, can't modify

**Acceptance Criteria**:
- ✅ 15-20 integration tests passing
- ✅ match_consumer.py coverage ≥55%
- ✅ Per-file coverage table with before/after/Δ

**Deliverables**:
- `tests/test_match_consumer_lifecycle_module_6_7.py`
- Updated fixtures for committed membership

---

### Step 3: Rate-Limit Enforcement (~1-2 hours) 📅 PLANNED
**Target**: `apps/tournaments/realtime/middleware_ratelimit.py` from **41% → ≥65%** (+24% gap)

**Current State**:
- Coverage: 41% (126 statements, 74 missed)
- Uncovered: Lines 135-150, 154-174, 179-207 (enforcement logic)

**Approach**: Monkeypatch low limits, mock Redis eval responses, assert close codes (4008, 4009, 4010)

**Tests to Add (5-8)**:
1. **Per-user connection limit**: Under limit → accept; over limit → close 4008
2. **Message RPS under limit**: High-frequency messages within limit → pass
3. **Message RPS over limit**: Exceed rate → reject with close code 4009
4. **Payload cap boundary**: Exactly at MAX_PAYLOAD_BYTES → accept
5. **Payload cap boundary+1**: Over MAX_PAYLOAD_BYTES → reject with close code 4010
6. **Redis-down fallback**: Simulate Redis failure → in-memory fallback
7. **Cool-down recovery**: Burst → wait → recovery → accept
8. **Multiple users isolated**: Rate limits per-user, no cross-contamination

**Acceptance Criteria**:
- ✅ 5-8 tests passing with explicit close code validation
- ✅ middleware_ratelimit.py coverage ≥65%
- ✅ Per-file coverage table with before/after/Δ

**Deliverables**:
- `tests/test_websocket_middleware_ratelimit_module_6_7_extra.py`
- Close code validation documentation

---

## 🎨 Optional: API Fuzz Testing (~3-4 hours)
**Status**: ⏸️ Deferred (after Steps 1-3 complete)

**Scope**: Hypothesis-based property testing for WebSocket message handling
- Random message generation (invalid JSON, extreme values, type mismatches)
- Property: All invalid inputs handled gracefully without crashes
- Property: All responses conform to schema

---

## 📊 Coverage Targets Summary

| File | Baseline (Module 6.6) | Target (Module 6.7) | Gap | Priority |
|------|----------------------|---------------------|-----|----------|
| **utils.py** | 29% | **≥65%** | +36% | Step 1 (High ROI) |
| **match_consumer.py** | 19% | **≥55%** | +36% | Step 2 (Critical) |
| **middleware_ratelimit.py** | 41% | **≥65%** | +24% | Step 3 (High ROI) |
| **Overall Package** | 45% | **≥65%** | +20% | Combined Goal |

**Estimated Total Effort**: ~8-10 hours (2-3h + 4-5h + 1-2h)

---

## 🛡️ Guardrails

### Test-Only Scope (Maintained from Module 6.6)
- ✅ **No production code changes** unless undeniable bug found
- ✅ If bug found: Tiny, isolated diff + documentation in completion status
- ✅ Test infrastructure changes allowed (fixtures, test ASGI, test middleware)

### Commit Strategy
- ✅ **Single local commit per step** (Step 1 → commit, Step 2 → commit, Step 3 → commit)
- ✅ **No push** until explicit instruction
- ✅ Commit messages follow Module 6.6 format (concise, metrics-focused)

### Documentation
- ✅ Keep `MODULE_6.7_COMPLETION_STATUS.md` updated after each step
- ✅ Update `MAP.md` (mark Module 6.7 in-progress)
- ✅ Update `trace.yml` (add events for each step completion)
- ✅ Run `verify_trace.py` after trace.yml updates
- ✅ Save coverage artifacts to `Artifacts/coverage/module_6_7/`

### Coverage Measurement
- ✅ Run coverage after each step: `pytest <test_files> --cov=apps.tournaments.realtime --cov-report=html:htmlcov_module_6_7_step_X`
- ✅ Document per-file deltas in completion status
- ✅ Create before/after/Δ table for transparency

---

## 🔄 Parallel: Phase 5 Staging Checklist (Lightweight)

While working on coverage, measure p50/p95/p99 latency for:
- Winner determination finalize → WS broadcast
- Payout approve/reject (idempotent + duplicate handling)
- Certificate view/download & public verify
- Organizer analytics summary

**Flag** anything with p95 > 500ms and add one-line recommendation to `MODULE_6.7_COMPLETION_STATUS.md` ("Staging Observations" section).

---

## 📝 Dependencies

### Satisfied (from Module 6.6)
- ✅ Test ASGI stack with TestJWTAuthMiddleware
- ✅ Unique user fixture pattern (microsecond timestamp)
- ✅ Settings patching approach (`patch('django.conf.settings.WS_RATE_*')`)
- ✅ In-memory channel layer configuration for tests
- ✅ WebsocketCommunicator test patterns

### Required (for Module 6.7)
- ✅ Monkeypatch batch windows in utils.py
- ✅ Mock channel layer group_send for batch assertions
- ✅ Match fixtures with committed membership (Step 2)
- ✅ Low rate limit settings for enforcement tests (Step 3)

---

## 🚀 Success Criteria

### Step 1 Complete When:
- [ ] 8-10 utils batching tests passing
- [ ] utils.py coverage ≥65%
- [ ] Coverage artifact saved
- [ ] MODULE_6.7_COMPLETION_STATUS.md updated
- [ ] Single local commit created

### Step 2 Complete When:
- [ ] 15-20 match consumer tests passing
- [ ] match_consumer.py coverage ≥55%
- [ ] Coverage artifact saved
- [ ] MODULE_6.7_COMPLETION_STATUS.md updated
- [ ] Single local commit created

### Step 3 Complete When:
- [ ] 5-8 rate-limit enforcement tests passing
- [ ] middleware_ratelimit.py coverage ≥65%
- [ ] Explicit close codes validated (4008, 4009, 4010)
- [ ] Coverage artifact saved
- [ ] MODULE_6.7_COMPLETION_STATUS.md updated
- [ ] Single local commit created

### Module 6.7 Complete When:
- [ ] All 3 steps complete
- [ ] Overall realtime package coverage ≥65%
- [ ] MAP.md updated (mark Module 6.7 complete)
- [ ] trace.yml updated with completion event
- [ ] verify_trace.py runs clean
- [ ] No unexpected test failures or skips

---

## 📚 References

- **Module 6.6 Completion**: Documents/ExecutionPlan/MODULE_6.6_COMPLETION_STATUS.md
- **Module 6.6 Unblock Analysis**: Documents/ExecutionPlan/MODULE_6.6_INTEGRATION_UNBLOCK.md
- **Implementation Plan**: Documents/ExecutionPlan/PHASE_6_IMPLEMENTATION_PLAN.md#module-67
- **Project Roadmap**: Documents/ExecutionPlan/MAP.md
- **Trace Log**: Documents/ExecutionPlan/trace.yml

---

**Status**: ✅ Kickoff doc complete, ready for Step 1 implementation  
**Next**: Analyze `utils.py` batching logic (lines 153-261), create test plan, implement 8-10 tests
