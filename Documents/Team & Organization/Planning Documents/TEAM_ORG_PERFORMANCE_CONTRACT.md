# Team & Organization vNext: Performance Contract

**Document Status:** BINDING REQUIREMENTS  
**Version:** 1.0  
**Last Updated:** 2026-01-25  
**Owner:** Engineering Team  
**Review Cycle:** Before each phase deployment

---

## Document Purpose

This document defines **NON-NEGOTIABLE** performance requirements for the Team & Organization vNext system. All code changes MUST meet these criteria or will be rejected during code review.

**Enforcement:**
- CI pipeline enforces query limits and response times
- Pre-deployment performance tests MUST pass
- Production monitoring triggers alerts on violations

**Related Documents:**
- [TEAM_ORG_ENGINEERING_STANDARDS.md](TEAM_ORG_ENGINEERING_STANDARDS.md) - Code quality standards
- [TEAM_ORG_ARCHITECTURE.md](TEAM_ORG_ARCHITECTURE.md) - System architecture
- [TEAM_ORG_VNEXT_MASTER_PLAN.md](TEAM_ORG_VNEXT_MASTER_PLAN.md) - Implementation plan

---

## Table of Contents

1. [Performance Targets (Hard Limits)](#1-performance-targets-hard-limits)
2. [Query Rules](#2-query-rules)
3. [Caching Strategy](#3-caching-strategy)
4. [Read vs Write Paths](#4-read-vs-write-paths)
5. [Async Rules](#5-async-rules)
6. [Monitoring & Enforcement](#6-monitoring--enforcement)

---

## 1. Performance Targets (Hard Limits)

### 1.1 Service Layer Response Times

**MUST comply with p95 latency limits:**

| Service Method Category | p95 Latency Limit | Rationale |
|------------------------|------------------|-----------|
| Simple reads (single object) | <50ms | Direct PK lookup with minimal joins |
| Complex reads (list views) | <100ms | Limited joins, pagination enforced |
| Write operations (create/update) | <100ms | Database transaction with validation |
| Calculations (CP, rankings) | <200ms | Precomputed data, minimal runtime calc |
| Bulk operations (migration) | <500ms | Batch processing, background preferred |

**Testing Requirements:**
- All service methods MUST have performance tests
- Use Django Debug Toolbar in development to measure query time
- Use `django.test.utils.override_settings(DEBUG=True)` to count queries
- Use `pytest-benchmark` for automated performance regression tests

**Example Test:**
```python
def test_team_detail_performance(benchmark):
    """TeamService.get_team_by_id() must complete in <50ms."""
    team = TeamFactory.create()
    
    result = benchmark(TeamService.get_team_by_id, team.id)
    
    assert result is not None
    assert benchmark.stats['mean'] < 0.05  # 50ms
```

---

### 1.2 Page Load Times

**MUST comply with user-facing latency limits:**

| Page Type | p95 Load Time | Max Queries | Rationale |
|-----------|--------------|-------------|-----------|
| Team detail page | <200ms | ≤5 queries | Most common page, single object |
| Team list (search) | <300ms | ≤7 queries | Paginated, simple filters |
| Leaderboard (DCRS) | <400ms | ≤10 queries | Cached rankings, background updates |
| Tournament registration | <500ms | ≤12 queries | Multi-step form, validation |
| Organization dashboard | <300ms | ≤8 queries | Aggregated stats, cached data |

**Testing Requirements:**
- Use `django-silk` or Django Debug Toolbar to profile page loads
- Automated tests MUST assert query count limits
- Load test with 100 concurrent users (no performance degradation >10%)

**Example Test:**
```python
from django.test import override_settings
from django.db import connection

@override_settings(DEBUG=True)
def test_team_detail_query_count(client):
    """Team detail page must use ≤5 queries."""
    team = TeamFactory.create()
    
    with connection.queries as queries:
        response = client.get(f'/organizations/teams/{team.slug}/')
    
    assert response.status_code == 200
    assert len(queries) <= 5, f"Used {len(queries)} queries (limit: 5)"
```

---

### 1.3 Background Job Latency

**MUST comply with job execution limits:**

| Job Type | Execution Time | Frequency | Failure Threshold |
|----------|---------------|-----------|------------------|
| Leaderboard update (per game) | <5 minutes | Every 5 minutes | Error rate <1% |
| CP decay (inactive teams) | <30 minutes | Daily (1 AM) | Error rate <0.1% |
| Notification delivery | <10 seconds | Real-time | Error rate <2% |
| Migration batch (1000 teams) | <15 minutes | One-time | Zero data loss |

**Monitoring:**
- Celery task metrics logged (execution time, error rate, retry count)
- Failed tasks trigger alerts (PagerDuty or equivalent)
- Timeout enforcement: Task killed if exceeds 2x expected time

---

## 2. Query Rules

### 2.1 Query Count Limits

**MUST NOT exceed maximum query count per operation:**

| Operation Type | Max Queries | Enforcement |
|---------------|-------------|-------------|
| Single object detail | 5 queries | CI test fails if exceeded |
| List view (paginated) | 7 queries | CI test fails if exceeded |
| Dashboard aggregates | 10 queries | CI test fails if exceeded |
| Multi-step form | 12 queries | CI test fails if exceeded |
| Background job (per item) | 3 queries | Warning logged if exceeded |

**N+1 Query Prevention:**
- MUST use `select_related()` for forward ForeignKey relationships
- MUST use `prefetch_related()` for reverse ForeignKey and ManyToMany relationships
- MUST use `Prefetch()` objects for filtered prefetches

**Example (CORRECT):**
```python
# TeamService - CORRECT N+1 prevention
def get_team_with_roster(team_id: int) -> TeamDetailDTO:
    """Fetch team with roster in 3 queries max."""
    team = (
        Team.objects
        .select_related('owner', 'game', 'organization')  # 1 query
        .prefetch_related(
            Prefetch(
                'roster',
                queryset=TeamMembership.objects.select_related('user')
            )
        )  # 2 queries total
        .get(id=team_id)
    )
    return TeamDetailDTO.from_orm(team)
```

**Example (FORBIDDEN):**
```python
# FORBIDDEN: N+1 query anti-pattern
def get_team_with_roster(team_id: int):
    team = Team.objects.get(id=team_id)  # 1 query
    roster = []
    for member in team.roster.all():  # N+1 queries (BAD!)
        roster.append({
            'user': member.user.username,  # Another N+1 (VERY BAD!)
            'role': member.role
        })
    return team, roster
```

---

### 2.2 Mandatory Database Indexes

**MUST create indexes for all performance-critical columns:**

| Model | Column(s) | Index Type | Rationale |
|-------|-----------|------------|-----------|
| `Team` | `slug` | Unique B-tree | URL lookup (most common query) |
| `Team` | `organization, game` | Composite | Organization dashboard filtering |
| `Team` | `created_at` | B-tree | Recency sorting |
| `TeamRanking` | `game, tier` | Composite | Leaderboard queries |
| `TeamRanking` | `game, current_cp` | Composite | Top 100 leaderboard |
| `TeamMembership` | `team, user` | Composite Unique | Permission checks |
| `TeamMembership` | `user, role` | Composite | User's teams query |
| `Organization` | `slug` | Unique B-tree | URL lookup |
| `OrganizationMembership` | `organization, user` | Composite Unique | Permission checks |

**Index Verification:**
- Run `python manage.py check --tag performance` to verify indexes exist
- Use `EXPLAIN ANALYZE` in PostgreSQL to verify index usage
- CI pipeline MUST fail if missing indexes detected

**Example Migration:**
```python
class Migration(migrations.Migration):
    operations = [
        migrations.AddIndex(
            model_name='team',
            index=models.Index(
                fields=['organization', 'game'],
                name='team_org_game_idx'
            ),
        ),
    ]
```

---

### 2.3 Forbidden Query Patterns

**MUST NOT use these anti-patterns:**

| Anti-Pattern | Why Forbidden | Alternative |
|-------------|--------------|-------------|
| `.count()` on large querysets | Full table scan | Cache counts, use aggregates |
| `.exists()` in loops | N+1 queries | Prefetch and check in Python |
| `ORDER BY` without index | Slow sort | Add index on sort column |
| `LIKE '%value%'` | No index usage | Full-text search (PostgreSQL) |
| `IN` query with 1000+ items | Memory overflow | Batch into chunks of 500 |
| `filter()` after `prefetch_related()` | Re-queries database | Use `Prefetch(queryset=...)` |
| Raw SQL without parameterization | SQL injection risk | Always use params |

**Example (FORBIDDEN):**
```python
# FORBIDDEN: .count() on large queryset
teams = Team.objects.filter(game=game)
if teams.count() > 100:  # BAD: Full table scan
    ...

# CORRECT: Use cached aggregate
game_team_counts = cache.get(f'game_{game.id}_team_count')
if game_team_counts is None:
    game_team_counts = Team.objects.filter(game=game).count()
    cache.set(f'game_{game.id}_team_count', game_team_counts, 300)  # 5 min TTL
```

---

## 3. Caching Strategy

### 3.1 What MUST Be Cached

**High-frequency reads with low change rate:**

| Data Type | Cache Key Pattern | TTL | Invalidation Trigger |
|-----------|------------------|-----|---------------------|
| Leaderboard (top 100) | `leaderboard:{game_id}` | 5 minutes | Celery job updates |
| Game metadata | `game:{game_id}` | 1 hour | Admin edit (rare) |
| Organization profile | `org:{org_id}` | 15 minutes | Org settings change |
| User's teams list | `user:{user_id}:teams` | 5 minutes | Team join/leave |
| Team member count | `team:{team_id}:count` | 10 minutes | Roster change |

**Implementation:**
- Use Redis for caching (not database-backed cache)
- Use `django.core.cache` API with versioned keys
- MUST implement cache warming for critical paths (leaderboards)

**Example:**
```python
from django.core.cache import cache

def get_leaderboard_cached(game_id: int) -> List[TeamRankingDTO]:
    """Cached leaderboard with 5-minute TTL."""
    cache_key = f'leaderboard:{game_id}:v1'
    
    leaderboard = cache.get(cache_key)
    if leaderboard is None:
        leaderboard = RankingService.get_leaderboard(game_id, limit=100)
        cache.set(cache_key, leaderboard, 300)  # 5 minutes
    
    return leaderboard
```

---

### 3.2 What MUST NOT Be Cached

**Data that MUST always be fresh:**

| Data Type | Reason | Alternative |
|-----------|--------|-------------|
| Permission checks | Security risk (stale permissions) | Always query in real-time |
| CSRF tokens | Security risk | Session-backed |
| Active session data | Consistency risk | Database session store |
| Payment state | Legal/compliance risk | Real-time query |
| Audit logs | Compliance requirement | Write-through only |
| Migration state | Race condition risk | Database lock |

**CRITICAL:** Never cache user permissions or roles. Always query in real-time:

```python
# CORRECT: Always query permissions (never cached)
def has_team_permission(user_id: int, team_id: int, permission: str) -> bool:
    """Check team permission in real-time (never cached)."""
    return TeamMembership.objects.filter(
        user_id=user_id,
        team_id=team_id,
        role__in=get_roles_with_permission(permission)
    ).exists()
```

---

### 3.3 Cache Invalidation Rules

**MUST invalidate cache on data changes:**

| Event | Cache Keys to Invalidate | Implementation |
|-------|-------------------------|----------------|
| Team roster change | `team:{team_id}:count`, `user:{user_id}:teams` | Signal handler |
| CP award | `leaderboard:{game_id}`, `team:{team_id}:ranking` | Signal handler |
| Tier change | `leaderboard:{game_id}`, `game:{game_id}:tier_counts` | Signal handler |
| Organization settings change | `org:{org_id}` | Signal handler |
| Game metadata change | `game:{game_id}` | Admin action |

**Example Signal Handler:**
```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache

@receiver(post_save, sender=TeamMembership)
def invalidate_team_cache(sender, instance, **kwargs):
    """Invalidate team roster cache on membership change."""
    cache.delete(f'team:{instance.team_id}:count')
    cache.delete(f'user:{instance.user_id}:teams')
```

---

### 3.4 Cache Warming Strategy

**MUST pre-populate cache for critical paths:**

| Cache Warming Job | Frequency | Purpose |
|------------------|-----------|---------|
| Leaderboard pre-compute | Every 5 minutes | Avoid cold cache on user request |
| Popular teams pre-fetch | Every 15 minutes | Top 100 teams by views |
| Game metadata refresh | Every 1 hour | Ensure latest game config |

**Implementation:**
- Celery periodic task runs cache warming
- Warming MUST complete before cache expiration (no gaps)

---

## 4. Read vs Write Paths

### 4.1 Hot Paths (Frequent Reads)

**Optimize for read performance:**

| Path | Expected Load | Optimization Strategy |
|------|--------------|----------------------|
| Team detail page | 10,000 req/min | Cached rankings, prefetch roster |
| Leaderboard view | 5,000 req/min | Redis cache, 5-min TTL |
| User's teams list | 3,000 req/min | Cached list, 5-min TTL |
| Tournament team search | 2,000 req/min | Indexed columns, paginated |

**Implementation:**
- MUST use read replicas for hot read paths (if available)
- MUST paginate all list views (50 items max)
- MUST use `select_related()` / `prefetch_related()`

---

### 4.2 Cold Paths (Admin/Migration)

**Acceptable slower performance:**

| Path | Expected Load | Optimization Strategy |
|------|--------------|----------------------|
| Admin panel edits | 10 req/hour | Real-time, no caching |
| Migration batch job | 1 req/day | Bulk operations, batched |
| Audit log queries | 5 req/hour | Indexed date range, paginated |
| Organization settings | 50 req/hour | Cached 15 min, low priority |

**Implementation:**
- No caching required (low volume)
- Use database transactions with `select_for_update()` to prevent race conditions
- Background jobs acceptable for admin bulk operations

---

### 4.3 Precomputation vs Runtime Calculation

**MUST precompute expensive operations:**

| Operation | Precompute? | Storage | Update Trigger |
|-----------|------------|---------|---------------|
| Team CP (ranking points) | YES | `TeamRanking.current_cp` | Match result post-save |
| Team tier (rank bracket) | YES | `TeamRanking.tier` | CP recalculation job |
| Hot streak count | YES | `TeamRanking.hot_streak` | Match result post-save |
| Leaderboard rankings | YES | Redis cache | Celery job every 5 min |
| Team member count | YES | Cached | Signal invalidation |
| Organization team count | YES | Cached | Signal invalidation |

**MUST NOT compute at runtime:**
- Leaderboard rankings (MUST be precomputed)
- Tier distributions (MUST be cached)
- Complex aggregates (MUST be cached or precomputed)

**Example (CORRECT):**
```python
# CORRECT: Precompute CP on match result
@receiver(post_save, sender=MatchResult)
def update_team_cp(sender, instance, **kwargs):
    """Award CP immediately on match result save."""
    cp_awarded = calculate_cp_award(instance.placement, instance.tier)
    
    ranking, created = TeamRanking.objects.get_or_create(
        team=instance.team,
        game=instance.tournament.game
    )
    ranking.current_cp += cp_awarded
    ranking.save()  # Precomputed, no runtime calculation
```

---

## 5. Async Rules

### 5.1 What MUST Be Synchronous

**User-facing operations requiring immediate feedback:**

| Operation | Reason | Max Latency |
|-----------|--------|------------|
| Team creation | User expects instant confirmation | <500ms |
| Roster invite | User expects immediate UI update | <300ms |
| Tournament registration | User expects instant feedback | <500ms |
| Permission checks | Security-critical | <50ms |

**Implementation:**
- Inline database writes
- Synchronous service method calls
- Return response before sending notifications (notifications async)

---

### 5.2 What MUST Be Async

**Operations that can be eventually consistent:**

| Operation | Reason | Implementation |
|-----------|--------|---------------|
| Email notifications | Slow SMTP, can fail | Celery task |
| Push notifications | External API, can retry | Celery task |
| Leaderboard updates | Not real-time critical | Celery periodic task |
| CP decay (inactive teams) | Batch operation | Celery daily task |
| Audit log writes | Not user-blocking | Celery task |
| Migration batch processing | Long-running | Celery task |

**Example:**
```python
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def send_roster_invite_email(self, team_id: int, user_email: str):
    """Send roster invite email asynchronously."""
    try:
        team = Team.objects.get(id=team_id)
        send_mail(
            subject=f'You've been invited to {team.name}',
            message='...',
            recipient_list=[user_email]
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)  # Retry after 1 min
```

---

### 5.3 Signal vs Direct Call

**When to use Django signals:**

| Use Signals For | Reason |
|----------------|--------|
| Cache invalidation | Decoupled, reusable |
| Audit logging | Decoupled, non-blocking |
| Notification triggers | Decoupled, async |

**When NOT to use signals:**

| Avoid Signals For | Reason | Alternative |
|------------------|--------|-------------|
| Business logic | Hidden dependencies | Explicit service method calls |
| Validation | Hard to test | Model `clean()` method |
| Critical workflows | Race conditions | Transaction-wrapped service methods |

---

## 6. Monitoring & Enforcement

### 6.1 Metrics to Log

**MUST log these metrics for all service methods:**

| Metric | Format | Purpose |
|--------|--------|---------|
| Execution time | `service.{method_name}.duration` (ms) | Performance tracking |
| Query count | `service.{method_name}.queries` (count) | N+1 detection |
| Error rate | `service.{method_name}.errors` (count) | Reliability tracking |
| Cache hit rate | `cache.{key_pattern}.hit_rate` (%) | Cache effectiveness |

**Implementation:**
- Use Django middleware or decorators to auto-log metrics
- Export to Prometheus or equivalent
- Grafana dashboards for visualization

**Example Decorator:**
```python
import time
from functools import wraps
from django.db import connection
import logging

logger = logging.getLogger(__name__)

def log_performance(func):
    """Log service method performance metrics."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        query_count_start = len(connection.queries)
        
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            query_count = len(connection.queries) - query_count_start
            
            logger.info(
                f'{func.__name__} completed',
                extra={
                    'duration_ms': duration_ms,
                    'query_count': query_count,
                    'status': 'success'
                }
            )
            return result
        except Exception as exc:
            logger.error(
                f'{func.__name__} failed',
                extra={'status': 'error', 'error': str(exc)}
            )
            raise
    
    return wrapper
```

---

### 6.2 CI Pipeline Enforcement

**MUST fail CI pipeline if:**

| Violation | Detection Method | Failure Threshold |
|-----------|-----------------|------------------|
| Service method >100ms | Performance test | p95 > 100ms |
| Page view >5 queries | Query count test | Any view exceeds limit |
| Test coverage <70% | `pytest-cov` | Coverage below phase target |
| Missing database indexes | `python manage.py check` | Any missing index |
| N+1 queries detected | Django Debug Toolbar | Any N+1 in tests |

**Example CI Config (.github/workflows/ci.yml):**
```yaml
- name: Run performance tests
  run: |
    pytest tests/performance/ --benchmark-only --benchmark-max-time=0.1
    if [ $? -ne 0 ]; then
      echo "Performance tests failed: Service methods exceed 100ms limit"
      exit 1
    fi

- name: Check query counts
  run: |
    pytest tests/ --count-queries --max-queries=5
    if [ $? -ne 0 ]; then
      echo "Query count limit exceeded"
      exit 1
    fi
```

---

### 6.3 Production Alerts

**MUST trigger alerts on these conditions:**

| Alert Condition | Threshold | Action |
|----------------|-----------|--------|
| Page load time spike | p95 > 500ms for 5 min | Page on-call engineer |
| Error rate spike | >5% for 5 min | Page on-call engineer |
| Cache miss rate high | <50% hit rate for 10 min | Warning, investigate |
| Celery queue backlog | >1000 tasks pending | Warning, scale workers |
| Database connection pool exhausted | >90% utilization | Page DBA team |

**Implementation:**
- Use Grafana + Prometheus alerting
- PagerDuty integration for critical alerts
- Slack notifications for warnings

---

### 6.4 Pre-Deployment Performance Checklist

**MUST complete before production deployment:**

- [ ] All service methods pass performance tests (<100ms p95)
- [ ] All page views pass query count tests (≤5 queries)
- [ ] Load test completed (100 concurrent users, no degradation >10%)
- [ ] Cache warming jobs running (leaderboards pre-populated)
- [ ] Database indexes verified (`python manage.py check --tag performance`)
- [ ] Monitoring dashboards configured (Grafana)
- [ ] Alerts configured (PagerDuty or equivalent)
- [ ] Rollback procedure tested (can revert within 5 minutes)

---

## Performance Contract Violations

**What happens if these rules are violated:**

1. **Code Review:** Changes rejected immediately (no exceptions)
2. **CI Pipeline:** Build fails, cannot merge to main branch
3. **Production:** Alerts trigger, on-call engineer investigates
4. **Post-Incident:** Performance post-mortem required, preventive measures documented

**Enforcement Authority:**
- Technical Lead has final say on performance exceptions
- Exceptions require written justification + plan to remediate

---

## Document Maintenance

**Update this document when:**
- New performance bottlenecks identified
- New caching strategies implemented
- Infrastructure changes (database upgrades, Redis cluster)
- Load test results reveal new limits

**Review Cycle:** Before each phase deployment (Phase 1-8).

---

**END OF PERFORMANCE CONTRACT**
