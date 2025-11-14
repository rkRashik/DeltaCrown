# Module 9.1 — Performance Audit Report

**Date**: January 2025  
**Auditor**: GitHub Copilot (Claude Sonnet 4.5)  
**Planning Reference**: PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (Section 4.4, lines 465-517)

---

## Executive Summary

This audit analyzes the DeltaCrown backend for performance optimization opportunities focusing on:
- Query patterns and N+1 issues
- Missing database indexes
- Caching opportunities
- Pagination enforcement
- Current performance baseline

**Key Findings**:
- ✅ **Good**: Many endpoints already use `select_related` (13 instances found)
- ⚠️ **N+1 Risk**: Registration ViewSet lacks query optimization
- ⚠️ **Missing Indexes**: No composite indexes for common filter patterns
- ⚠️ **Cache Gap**: Redis configured but underutilized (only LocMemCache in use)
- ⚠️ **Pagination**: Default PAGE_SIZE=20 configured, but no max enforcement

---

## 1. Query Analysis

### 1.1 Endpoints with Query Optimization ✅

**Already Optimized (13 instances)**:
- `apps/tournaments/api/bracket_views.py` (line 58): `Bracket.objects.all().select_related('tournament')`
- `apps/tournaments/api/matches.py` (line 55): `Match.objects.select_related('tournament').all()`
- `apps/tournaments/api/match_views.py` (line 109): `Match.objects.filter().select_related(...)`
- `apps/tournaments/api/payments.py` (line 43): `PaymentVerification.objects.select_related("registration")`
- `apps/tournaments/api/result_views.py` (line 64): `Match.objects.select_related('tournament', 'bracket')`
- `apps/tournaments/api/tournament_views.py` (line 88): `qs.select_related('game', 'organizer')`
- `apps/tournaments/api/views.py` (lines 76, 82, 140): Payment/Registration with `select_related`
- `apps/tournaments/api/certificate_views.py` (line 93): Certificate with `select_related`
- `apps/leaderboards/services.py` (line 485): LeaderboardEntry with `select_related`

### 1.2 Endpoints Missing Optimization ⚠️

**High-Priority Targets**:

1. **Registration ViewSet** (`apps/tournaments/api/registrations.py`):
   ```python
   # Line 199: queryset = Registration.objects.all()
   # ISSUE: No select_related for tournament, user, team, payment_verification
   # IMPACT: N+1 queries when listing registrations
   # FIX: Add .select_related('tournament', 'user', 'team', 'payment_verification')
   ```

2. **Tournament Discovery** (`apps/tournaments/api/leaderboard_views.py`):
   ```python
   # Line 369: queryset = Tournament.objects.filter(is_deleted=False)
   # ISSUE: Missing select_related for game, organizer
   # IMPACT: Extra queries when listing tournaments
   # FIX: Add .select_related('game', 'organizer')
   ```

3. **Custom Field Views** (`apps/tournaments/api/custom_field_views.py`):
   ```python
   # Line 56: CustomField.objects.filter(tournament_id=...).order_by(...)
   # ISSUE: Missing select_related for tournament
   # IMPACT: Minor - custom fields are tournament-scoped
   # FIX: Add .select_related('tournament') if tournament data is accessed
   ```

4. **Leaderboard Engine** (`apps/leaderboards/engine.py`):
   ```python
   # Lines 792, 881, 888: Match.objects.filter(...)
   # ISSUE: Missing select_related for tournament, participants
   # IMPACT: N+1 queries during leaderboard calculations
   # FIX: Add .select_related('tournament').prefetch_related('participants')
   ```

5. **Leaderboard Tasks** (`apps/leaderboards/tasks.py`):
   ```python
   # Line 178: Tournament.objects.filter(...)
   # ISSUE: Missing optimization for active tournament queries
   # IMPACT: Background tasks slower than needed
   # FIX: Add .select_related('game', 'organizer')
   ```

### 1.3 Prefetch Opportunities

**Reverse ForeignKey / ManyToMany**:
- `Tournament.registrations` - should use `prefetch_related('registrations')`
- `Tournament.sponsors` - should use `prefetch_related('sponsors')`
- `Match.participants` - should use `prefetch_related('participants')`
- `Bracket.nodes` - should use `prefetch_related('nodes')`

---

## 2. Database Index Analysis

### 2.1 Existing Indexes ✅

**Found (via db_index=True)**:
- `Tournament.slug` (unique index)
- `Tournament.organizer` (ForeignKey auto-indexed)
- `Game.slug` (unique index)
- `Certificate.issued_to` (db_index=True)
- Various timestamps (created_at, updated_at via default behavior)

**Found (via Meta.indexes)**:
- `Tournament` model has composite indexes (line 112)
- `Certificate` model has composite indexes (line 151)
- `Result` model has indexes (line 189)

### 2.2 Missing Indexes ⚠️

**High-Priority Composite Indexes Needed**:

1. **Tournament Filtering**:
   ```python
   # Common query: Tournament.objects.filter(game_id=X, status=Y, is_deleted=False)
   # MISSING: Index on (game_id, status, is_deleted)
   # IMPACT: Slow tournament discovery/filtering
   ```

2. **Registration Lookup**:
   ```python
   # Common query: Registration.objects.filter(tournament_id=X, user_id=Y)
   # MISSING: Index on (tournament_id, user_id)
   # IMPACT: Duplicate registration checks are slower
   ```

3. **Match Queries**:
   ```python
   # Common query: Match.objects.filter(tournament_id=X, status=Y)
   # MISSING: Index on (tournament_id, status)
   # IMPACT: Slow match listings/bracket generation
   ```

4. **Leaderboard Queries**:
   ```python
   # Common query: LeaderboardEntry.objects.filter(game_id=X, is_active=True)
   # MISSING: Index on (game_id, is_active)
   # IMPACT: Slow leaderboard reads
   ```

5. **Payment Verification**:
   ```python
   # Common query: PaymentVerification.objects.filter(registration_id=X, status=Y)
   # MISSING: Index on (registration_id, status)
   # IMPACT: Slow payment lookup/verification
   ```

---

## 3. Caching Analysis

### 3.1 Current State

**Configuration** (`deltacrown/settings.py` line 192-194):
```python
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}
```

**Issues**:
- ⚠️ Using `LocMemCache` (in-memory, not distributed)
- ⚠️ Redis is available (Celery uses `redis://localhost:6379/0`) but not used for Django cache
- ⚠️ No caching strategy implemented for high-read endpoints

### 3.2 Redis Infrastructure Status ✅

**Already Configured**:
- Celery broker: `redis://localhost:6379/0` (line 489)
- Celery results: `redis://localhost:6379/0` (line 490)
- Django Channels: `RedisChannelLayer` (line 445, conditionally)

**Conclusion**: Redis is production-ready, can be used for Django cache.

### 3.3 Caching Opportunities

**High-Value Targets**:

1. **Leaderboard Reads** (HIGH):
   - Endpoint: `GET /api/leaderboards/`
   - TTL: 5-10 minutes
   - Cache key: `leaderboard:{game_id}:{page}`
   - Impact: Leaderboards are read-heavy, recalculated infrequently

2. **Tournament Discovery** (HIGH):
   - Endpoint: `GET /api/tournaments/` (public list)
   - TTL: 10-15 minutes
   - Cache key: `tournaments:list:{game}:{status}:{page}`
   - Impact: Discovery is heavily accessed, changes slowly

3. **Organizer Stats** (MEDIUM):
   - Endpoint: `GET /api/organizer/dashboard/stats/`
   - TTL: 5 minutes
   - Cache key: `organizer_stats:{user_id}`
   - Impact: Dashboard is accessed frequently, stats change slowly

4. **Tournament Health** (MEDIUM):
   - Endpoint: `GET /api/organizer/tournaments/{id}/health/`
   - TTL: 2-5 minutes
   - Cache key: `tournament_health:{tournament_id}`
   - Impact: Health metrics are read-heavy

5. **Game Config Schema** (LOW):
   - Endpoint: `GET /api/games/{id}/config-schema/`
   - TTL: 60 minutes
   - Cache key: `game_config_schema:{game_id}`
   - Impact: Schema rarely changes, read frequently

**Invalidation Strategy**:
- Use Django signals (`post_save`, `post_delete`) to invalidate related caches
- Prefix all cache keys with `v1:` for easy version-based invalidation

---

## 4. Pagination Analysis

### 4.1 Current Configuration ✅

**REST Framework Settings** (`deltacrown/settings.py` line 277-278):
```python
"DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
"PAGE_SIZE": 20,
```

**Status**: Default pagination is configured correctly.

### 4.2 Issues Found ⚠️

1. **No Max Page Size Enforcement**:
   - Current: Clients can potentially request unlimited page_size via `?page_size=999999`
   - Risk: DoS vulnerability, performance degradation
   - Fix: Add `max_page_size=100` to pagination class

2. **High-Volume Endpoints Need Cursor Pagination**:
   - Leaderboard listings (thousands of entries)
   - Match history (large tournaments)
   - Issue: Offset pagination is slow for deep pages (e.g., page 100)
   - Fix: Add cursor pagination option for large datasets

### 4.3 Pagination Patterns Found

**Endpoints Using Pagination**:
- Tournament ViewSet (line 85): Uses default pagination
- Registration ViewSet (line 199): Uses default pagination
- Match ViewSet (line 109): Uses default pagination
- Leaderboard ViewSet: Uses default pagination

**No Issues Found**: All endpoints respect DRF pagination defaults.

---

## 5. Performance Baseline (Estimated)

### 5.1 Current Query Counts (Estimated)

**Without Optimization**:
- `/api/tournaments/` (list 20 items): ~42 queries (1 + 20 organizer + 20 game + 1 count)
- `/api/registrations/` (list 20 items): ~62 queries (1 + 20 tournament + 20 user + 20 payment + 1 count)
- `/api/leaderboards/` (list 20 items): ~22 queries (1 + 20 user + 1 count)

**With Optimization** (Expected):
- `/api/tournaments/` (list 20 items): ~2 queries (1 + 1 count)
- `/api/registrations/` (list 20 items): ~2 queries (1 + 1 count)
- `/api/leaderboards/` (list 20 items): ~2 queries (1 + 1 count)

### 5.2 Expected Performance Gains

- **Query Reduction**: 70-95% fewer queries per request
- **Response Time**: 50-70% faster API responses
- **Cache Hit Rate**: 60-80% for leaderboards/discovery (after warmup)
- **Database Load**: 60-80% reduction in SELECT queries

---

## 6. Recommendations (Priority Order)

### Immediate (Step 2)
1. Add `select_related` to Registration ViewSet
2. Add `select_related` to Tournament discovery endpoints
3. Add `prefetch_related` for reverse ForeignKey patterns

### High Priority (Step 3)
4. Create migration with composite indexes
5. Add indexes: (game_id, status), (tournament_id, user_id), (tournament_id, status)

### Medium Priority (Step 4)
6. Switch Django cache from LocMemCache to Redis
7. Implement caching for leaderboards (5-10 min TTL)
8. Implement caching for tournament discovery (10-15 min TTL)

### Standard Priority (Step 5)
9. Enforce `max_page_size=100` in pagination
10. Document pagination limits in API docs

### Optional (Step 6)
11. Add cursor pagination for leaderboards
12. Add simple query count tests in `tests/performance/test_benchmarks.py`

---

## 7. Risk Assessment

**Low Risk**:
- Adding `select_related`/`prefetch_related` (only affects query efficiency)
- Adding database indexes (improves read performance, minimal write overhead)
- Enforcing pagination limits (protects against abuse)

**Medium Risk**:
- Switching to Redis cache (requires Redis running, but already used by Celery)
- Cache invalidation logic (must be tested to avoid stale data)

**No Risk**:
- Performance testing/benchmarking
- Documentation

---

## 8. Success Metrics

**Before Module 9.1**:
- Avg queries per request: 20-60
- API response time (p95): ~300-500ms (estimated)
- Cache hit rate: 0% (no caching)
- Deep pagination: O(n) offset cost

**After Module 9.1** (Targets):
- Avg queries per request: 2-5 (90% reduction)
- API response time (p95): <200ms (40-60% improvement)
- Cache hit rate: 60-80% for cached endpoints
- Max page size enforced: 100 items
- SLO documented: API <200ms, DB queries <50ms, WebSocket <100ms

---

**End of Performance Audit Report**
