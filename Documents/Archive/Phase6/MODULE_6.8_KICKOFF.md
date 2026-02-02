# Module 6.8 Kickoff: Redis-Backed Enforcement & E2E Rate Limiting

**Module**: 6.8 - Redis-Backed Enforcement & E2E Rate Limiting  
**Phase**: 6 (Testing & Polish)  
**Status**: 📋 **Planned** (awaiting green light)  
**Estimated Effort**: ~3-4 hours  
**Dependencies**: Module 6.7 complete (baseline test infrastructure in place)

---

## Executive Summary

**Goal**: Lift `middleware_ratelimit.py` coverage from **47% → ≥70-75%** by introducing Redis-backed integration tests that exercise core enforcement paths requiring stateful connection counters.

**Context**: Module 6.7 Step 3 achieved 47% coverage (up from 41%) but identified an 18% gap due to enforcement logic dependencies on Redis. Core paths (lines 135-288, 86% of file) require Redis connection counters to return non-zero values and enforce limits. Room capacity enforcement proven reachable via logs but test framework can't handle DenyConnection cleanly without Redis context.

**Approach**: Ephemeral Redis for tests (recommended) - spin up test-scoped Redis instance, configure test settings to use `localhost:6379`, exercise connection/room/message enforcement end-to-end with real counters.

---

## Problem Statement

### Module 6.7 Variance Analysis

**Achieved**: middleware_ratelimit.py 41% → 47% (+6%)  
**Target**: 65% (18% gap remaining)  
**Root Cause**: 108 uncovered lines (86% of file) require Redis infrastructure

**Uncovered Enforcement Paths**:
1. **Lines 135-150**: Per-user connection limit enforcement (15 lines)
   - Depends on `get_user_connections()` returning non-zero values
   - Requires `increment_user_connections()` / `decrement_user_connections()` state persistence
   
2. **Lines 154-174**: Per-IP connection limit enforcement (20 lines)
   - Depends on `get_ip_connections()` returning non-zero values  
   - Requires `increment_ip_connections()` / `decrement_ip_connections()` state persistence
   
3. **Lines 179-207**: Room capacity enforcement (28 lines)
   - ✅ **Proven reachable** (logs show "Tournament 123 room full: 100/2000")
   - DenyConnection exception propagates through test framework without Redis context
   
4. **Lines 240-263**: Payload size enforcement in receive wrapper (23 lines)
   - Requires actual oversized data through receive path with enforcement context
   
5. **Lines 267-288**: Message rate enforcement in receive wrapper (21 lines)
   - Requires `check_and_consume()` to return `(False, retry_ms)` with real Redis TTL

**Why Test-Only Approach Insufficient**:
- Connection counter functions (`get_user_connections`, `get_ip_connections`) return 0 without Redis
- Enforcement branches (`if current_conns >= limit`) never execute without non-zero counters
- DenyConnection exceptions require WebSocket connection context (not just mocks)
- Rate limit violations need time-based state (Redis TTL) for deterministic testing

---

## Proposed Solution: Ephemeral Redis for Tests (Approach A)

### Architecture

**Test Environment Setup**:
```yaml
# Redis test configuration (archived - no longer using Docker Compose)
services:
  redis-test:
    image: redis:7-alpine
    ports:
      - "6380:6379"  # Avoid conflict with local Redis
    command: redis-server --save "" --appendonly no
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 1s
      timeout: 3s
      retries: 30
```

**Test Settings**:
```python
# tests/conftest.py or test settings module
@pytest.fixture(scope="session", autouse=True)
def redis_test_setup():
    """Start ephemeral Redis for tests."""
    import subprocess
    import time
    import redis
    
    # Start Redis (archived approach - no longer using Docker Compose)
    # Redis should be available on localhost:6379
    
    # Wait for connection
    client = redis.Redis(host='localhost', port=6380, decode_responses=True)
    for _ in range(30):
        try:
            if client.ping():
                break
        except:
            time.sleep(0.1)
    
    yield
    
    # Teardown
    # No Docker cleanup needed

@pytest.fixture
def redis_test_client():
    """Redis client for test assertions."""
    import redis
    return redis.Redis(host='localhost', port=6380, decode_responses=True)

@pytest.fixture(autouse=True)
def clear_redis(redis_test_client):
    """Clear Redis before each test."""
    redis_test_client.flushdb()
```

**Configuration Override**:
```python
# Override settings for enforcement tests
@pytest.mark.django_db
class TestRedisBackedEnforcement:
    @pytest.fixture(autouse=True)
    def enforce_redis_limits(self, settings):
        settings.WS_RATE_ENABLED = True
        settings.WS_RATE_CONN_PER_USER = 2
        settings.WS_RATE_CONN_PER_IP = 5
        settings.WS_RATE_ROOM_MAX_MEMBERS = 100
        settings.REDIS_HOST = 'localhost'
        settings.REDIS_PORT = 6380  # Test Redis
        settings.REDIS_DB = 0
```

### Test Targets

**1. Connection Limit Enforcement** (Lines 135-150, 154-174)
```python
async def test_user_connection_limit_enforced_with_redis():
    """
    Open 3 connections for same user → 3rd rejected with close code 4008.
    Verify Redis counters: user:<user_id>:ws_connections = 2 after rejection.
    """
    # Establish 2 connections (at limit)
    comm1 = await connect_as_user(user_id=1)
    comm2 = await connect_as_user(user_id=1)
    
    # Verify Redis counter
    assert redis_client.get(f"user:{1}:ws_connections") == "2"
    
    # Try 3rd connection → rejected
    comm3 = WebsocketCommunicator(app, f"/ws/match/123/?token={jwt_token}")
    connected, _ = await comm3.connect()
    assert not connected  # DenyConnection raised
    
    # Verify error message sent before close
    output = await comm3.receive_output()
    assert output['type'] == 'websocket.send'
    error_data = json.loads(output['text'])
    assert error_data['code'] == 'connection_limit_exceeded'
    assert error_data['retry_after_ms'] == 5000
    
    # Verify close code
    close_output = await comm3.receive_output()
    assert close_output['type'] == 'websocket.close'
    assert close_output['code'] == 4008  # Policy Violation
    
    # Cleanup
    await comm1.disconnect()
    await comm2.disconnect()
    
    # Verify Redis counter decremented
    assert redis_client.get(f"user:{1}:ws_connections") == "0"
```

**2. Room Capacity Enforcement** (Lines 179-207)
```python
async def test_room_capacity_enforced_with_redis():
    """
    Fill tournament room to capacity → next connection rejected.
    Verify Redis set: room:tournament_123:members size = max.
    """
    # Fill room to capacity (max = 100)
    connections = []
    for i in range(100):
        comm = await connect_as_user(user_id=i, path="/ws/match/123/")
        connections.append(comm)
    
    # Verify Redis room set
    room_size = redis_client.scard("room:tournament_123:members")
    assert room_size == 100
    
    # Try 101st connection → rejected
    comm_overflow = await connect_as_user(user_id=101, path="/ws/match/123/")
    
    # Should receive room_full error
    output = await comm_overflow.receive_output()
    error_data = json.loads(output['text'])
    assert error_data['code'] == 'room_full'
    assert 'room at capacity' in error_data['message'].lower()
    
    # Verify close code
    close_output = await comm_overflow.receive_output()
    assert close_output['code'] == 4008
    
    # Cleanup one connection → room available
    await connections[0].disconnect()
    
    # Verify Redis room set updated
    room_size = redis_client.scard("room:tournament_123:members")
    assert room_size == 99
    
    # New connection should succeed
    comm_new = await connect_as_user(user_id=101, path="/ws/match/123/")
    assert comm_new.connected
```

**3. Message Rate Limit Enforcement** (Lines 267-288)
```python
async def test_message_rate_limit_enforced_with_redis():
    """
    Burst beyond RPS → messages rejected with rate_limit error.
    Verify Redis token bucket: user:<user_id>:msg_tokens key with TTL.
    """
    # Configure low rate limit (2 RPS, burst 3)
    settings.WS_RATE_MSG_RPS = 2.0
    settings.WS_RATE_MSG_BURST = 3
    
    comm = await connect_as_user(user_id=1)
    
    # Send 3 messages (at burst limit) → all succeed
    for i in range(3):
        await comm.send_json_to({"type": "ping", "seq": i})
        response = await comm.receive_json_from()
        assert response['type'] == 'pong'
    
    # Verify Redis token bucket
    tokens_key = "user:1:msg_tokens"
    assert redis_client.exists(tokens_key)
    assert int(redis_client.get(tokens_key)) < 3  # Tokens consumed
    
    # Send 4th message → rate limited
    await comm.send_json_to({"type": "ping", "seq": 3})
    
    # Should receive rate_limit error
    response = await comm.receive_json_from()
    assert response['type'] == 'error'
    assert response['code'] == 'rate_limit_exceeded'
    assert 'retry_after_ms' in response
    
    # Wait for cooldown
    await asyncio.sleep(response['retry_after_ms'] / 1000)
    
    # Message should succeed after cooldown
    await comm.send_json_to({"type": "ping", "seq": 4})
    response = await comm.receive_json_from()
    assert response['type'] == 'pong'
    
    await comm.disconnect()
```

**4. Payload Size Enforcement** (Lines 240-263)
```python
async def test_payload_size_enforced_with_redis():
    """
    Send oversized payload → connection closed with code 4009.
    """
    settings.WS_MAX_PAYLOAD_BYTES = 1024
    
    comm = await connect_as_user(user_id=1)
    
    # Send oversized payload (2KB)
    large_payload = {"type": "subscribe", "data": "x" * 2048}
    await comm.send_json_to(large_payload)
    
    # Should receive error
    output = await comm.receive_output()
    error_data = json.loads(output['text'])
    assert error_data['code'] == 'payload_too_large'
    
    # Verify close code
    close_output = await comm.receive_output()
    assert close_output['code'] == 4009  # Message Too Big
```

### Acceptance Criteria

1. **Coverage Target**: `middleware_ratelimit.py` ≥ **70-75%**
   - Lines 135-150 covered (per-user connection enforcement)
   - Lines 154-174 covered (per-IP connection enforcement)
   - Lines 179-207 covered (room capacity enforcement)
   - Lines 240-263 covered (payload size enforcement)
   - Lines 267-288 covered (message rate enforcement)

2. **Test Quality**:
   - All tests pass with ephemeral Redis running
   - Tests verify Redis state (counters, sets, TTL)
   - Exact close codes validated (4008, 4009, 4010)
   - Cleanup verified (counters decremented on disconnect)

3. **Production Safety**:
   - **Zero production code changes** (except optional test-only DI hooks)
   - Test settings isolated (port 6380, separate DB)
   - Docker Compose test profile (no interference with dev/prod Redis)

4. **Documentation**:
   - Test README with Redis setup instructions
   - CI integration guide (GitHub Actions with Redis service)
   - Troubleshooting section (Redis not running, port conflicts)

---

## Alternative Approach: Pluggable Backend (Approach B)

**Concept**: Introduce interface for rate limiter backend, test path uses in-memory backend emulating Redis semantics.

**Pros**:
- No external service dependency in tests
- Faster test execution (no Docker startup)
- Portable (works on any platform)

**Cons**:
- Requires small production refactor (DI hooks)
- In-memory backend must emulate Lua token-bucket semantics accurately
- More complex implementation (~5-6 hours vs 3-4 hours)
- May not catch Redis-specific edge cases

**Recommendation**: **Defer to future** if Approach A works well. Revisit if CI environment constrains Redis usage.

---

## Test File Structure

```
tests/
  test_middleware_ratelimit_redis_module_6_8.py     (~600 lines, 12-15 tests)
    - TestConnectionLimitRedis (4 tests)
      - test_user_connection_limit_enforced_with_redis
      - test_ip_connection_limit_enforced_with_redis
      - test_connection_limit_cleanup_on_disconnect
      - test_concurrent_connection_attempts_serialized
    
    - TestRoomCapacityRedis (3 tests)
      - test_room_capacity_enforced_with_redis
      - test_room_join_leave_cycle
      - test_multiple_rooms_independent_capacity
    
    - TestMessageRateLimitRedis (4 tests)
      - test_message_rate_limit_enforced_with_redis
      - test_cooldown_recovery_after_burst
      - test_per_user_rate_limit_independence
      - test_anonymous_ip_based_rate_limit
    
    - TestPayloadSizeRedis (2 tests)
      - test_payload_size_enforced_with_redis
      - test_boundary_payload_edge_cases
    
    - TestRedisFailover (2 tests)
      - test_redis_down_graceful_degradation
      - test_redis_recovery_after_outage

tests/conftest.py                                     (Redis fixtures + setup/teardown)
Documents/ExecutionPlan/MODULE_6.8_COMPLETION_STATUS.md
```

---

## Implementation Plan

### Phase 1: Infrastructure Setup (~1 hour)

**Tasks**:
1. Set up Redis test infrastructure
2. Add `redis_test_setup` fixture in `tests/conftest.py`
3. Add `redis_test_client` fixture for assertions
4. Add `clear_redis` autouse fixture for test isolation
5. Configure test settings override (`WS_RATE_ENABLED=True`, Redis port 6380)

**Validation**:
- Docker Compose starts Redis successfully
- Pytest fixtures connect to Redis
- Health check confirms Redis ready before tests run

### Phase 2: Connection Limit Tests (~1 hour)

**Tasks**:
1. Implement `test_user_connection_limit_enforced_with_redis`
2. Implement `test_ip_connection_limit_enforced_with_redis`
3. Implement `test_connection_limit_cleanup_on_disconnect`
4. Implement `test_concurrent_connection_attempts_serialized`

**Validation**:
- All 4 tests pass
- Redis counters verified (`user:<id>:ws_connections`, `ip:<ip>:ws_connections`)
- Close code 4008 confirmed
- Cleanup verified (counters = 0 after disconnect)

### Phase 3: Room Capacity & Message Rate Tests (~1 hour)

**Tasks**:
1. Implement `test_room_capacity_enforced_with_redis`
2. Implement `test_room_join_leave_cycle`
3. Implement `test_message_rate_limit_enforced_with_redis`
4. Implement `test_cooldown_recovery_after_burst`

**Validation**:
- Redis room sets verified (`room:tournament_<id>:members`)
- Redis token buckets verified (`user:<id>:msg_tokens` with TTL)
- Rate limit errors include `retry_after_ms`
- Cooldown recovery works (messages pass after wait)

### Phase 4: Payload & Failover Tests (~30 min)

**Tasks**:
1. Implement `test_payload_size_enforced_with_redis`
2. Implement `test_redis_down_graceful_degradation`
3. Measure coverage, document gaps

**Validation**:
- Payload enforcement with close code 4009
- Redis down → in-memory fallback (no crash)
- Coverage ≥70% target achieved

### Phase 5: Documentation & CI (~30 min)

**Tasks**:
1. Create `tests/README_REDIS_TESTS.md` with setup instructions
2. Update `MODULE_6.8_COMPLETION_STATUS.md`
3. Add GitHub Actions Redis service configuration
4. Commit with detailed message

**Validation**:
- CI runs tests with Redis service
- Documentation clear for new contributors
- Coverage artifacts saved

---

## Estimated Effort Breakdown

| Phase | Task | Effort |
|-------|------|--------|
| 1 | Infrastructure setup (Docker, fixtures) | ~1 hour |
| 2 | Connection limit tests (4 tests) | ~1 hour |
| 3 | Room capacity & message rate tests (4 tests) | ~1 hour |
| 4 | Payload & failover tests (3 tests) | ~30 min |
| 5 | Documentation & CI | ~30 min |
| **Total** | **12-15 tests, Redis integration** | **~4 hours** |

**Contingency**: +1 hour for Redis setup troubleshooting or CI integration issues

---

## Success Metrics

**Coverage**:
- `middleware_ratelimit.py`: 47% → **≥70-75%** (+23-28%)
- Realtime package overall: ≥70%

**Test Quality**:
- 12-15 passing tests with Redis integration
- All enforcement paths (135-288) covered
- Exact close codes validated (4008, 4009, 4010)
- Redis state verification (counters, sets, TTL)

**Production Safety**:
- Zero production code changes (test-only scope)
- No interference with dev/prod Redis (port isolation)
- Graceful degradation if Redis unavailable

**Documentation**:
- Clear setup instructions for contributors
- CI integration guide
- Troubleshooting section

---

## Risks & Mitigations

### Risk 1: Docker Not Available in CI
**Mitigation**: Use GitHub Actions Redis service (built-in support)
```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - 6379:6379
    options: >-
      --health-cmd "redis-cli ping"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

### Risk 2: Port Conflicts on Developer Machines
**Mitigation**: Use non-standard port (6380) for test Redis, document in setup guide

### Risk 3: Flaky Tests Due to Redis Timing
**Mitigation**: Health check with retries before running tests, generous timeouts in assertions

### Risk 4: Coverage Still Below Target After Redis Integration
**Mitigation**: Identify remaining uncovered lines, add targeted tests or document as low-priority edge cases

---

## Dependencies

- **Completed**: Module 6.7 (baseline test infrastructure, test ASGI, fixtures)
- **Required**: Docker or Docker Compose for local dev
- **Optional**: GitHub Actions Redis service for CI

---

## Acceptance & Sign-Off

**Definition of Done**:
- [ ] Docker Compose test Redis configuration created
- [ ] 12-15 tests passing with Redis-backed enforcement
- [ ] `middleware_ratelimit.py` coverage ≥70%
- [ ] Redis state verification in assertions (counters, sets, TTL)
- [ ] Exact close codes validated (4008, 4009, 4010)
- [ ] Documentation complete (setup, CI, troubleshooting)
- [ ] CI integration verified (GitHub Actions with Redis service)
- [ ] MODULE_6.8_COMPLETION_STATUS.md documented
- [ ] MAP.md and trace.yml updated
- [ ] Committed locally (single commit, no push)

**Sign-Off**: Awaiting green light to proceed with Approach A (ephemeral Redis)

---

## Next Steps After Module 6.8

**Module 6.9**: End-to-End Realtime Flow Testing (~4-5 hours)
- Full tournament lifecycle with realtime events
- Multi-user concurrency scenarios
- Error recovery and reconnection flows

**Module 6.10**: API Fuzz Testing (~3-4 hours)
- Hypothesis-based property testing for WebSocket messages
- Random message generation (invalid JSON, extreme values, type mismatches)
- Chaos engineering for realtime layer

---

**Ready to Start**: Awaiting confirmation to create Docker Compose config and begin Phase 1 (Infrastructure Setup)
