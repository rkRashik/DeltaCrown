# Phase E Leaderboards - Master Navigation Index

**Version**: 1.0  
**Last Updated**: January 26, 2025  
**Status**: Production Ready (T+24h canary promoted to 25% traffic)  
**Scope**: Complete navigation for Phase E Leaderboards implementation  

---

## Quick Start: "Where Do I Start?"

**👨‍💻 Backend Engineers** (working on leaderboards logic):
- Start here: [LeaderboardService](../apps/tournaments/services/leaderboard_service.py) - Core service layer (450 lines)
- Then read: [Architecture README](../docs/leaderboards/README.md) - Design decisions, 5-step tie-breaker, caching strategy
- Key tests: [Service tests](../apps/tournaments/tests/test_leaderboard_service.py) - 550 lines covering aggregation, tie-breaking, caching

**🌐 API Consumers / Frontend Developers**:
- Start here: [Integration Examples](../docs/integration/leaderboards_examples.md) - cURL + JSON examples for all 9 endpoints
- Then read: [Public API README](../docs/leaderboards/api_readme.md) - Endpoint specs, pagination, error handling
- **IDs-Only Policy**: All responses contain participant_id, team_id, tournament_id only (no display names)
- **Name Resolution**: Clients resolve IDs via `/api/profiles/`, `/api/teams/`, `/api/tournaments/{id}/metadata/`
- Rate limits: 100 req/hour authenticated, responses update every 5 minutes

**🔧 Ops / SRE**:
- Start here: [Phase E Runbook](../docs/runbooks/phase_e_leaderboards.md) - 600 lines covering rollback, troubleshooting, monitoring
- Then check: [Observability Guide](../docs/leaderboards/observability_guide.md) - Prometheus metrics, query examples, alerting
- Feature flags: All 3 flags default `False` (instant rollback via environment config)

**🛡️ Admins / Support Staff**:
- Start here: [Admin Leaderboards API](../docs/admin/leaderboards.md) - 3 debug endpoints (inspect, cache status, invalidation)
- Then read: [Admin Tournament Ops API](../docs/admin/tournament_ops.md) - 3 tracking endpoints (payments, matches, disputes)
- Access: All admin endpoints require `IsAdminUser` permission

**📋 Project Managers / Stakeholders**:
- Start here: [MAP.md Phase E Section](../Documents/ExecutionPlan/PHASE_E_MAP_SECTION.md) - Module summary, SLOs, effort tracking
- Then check: [trace.yml Phase E Nodes](../Documents/ExecutionPlan/PHASE_E_TRACE_NODES.yml) - Traceability, checks, rollback plans
- Status: 4 modules complete, ~7,300 lines across 21 files, 85-90% test coverage, ~88 hours actual effort

---

## Complete File Inventory

### Production Code (10 files, ~2,750 lines)

| File | Purpose | Lines | Key Features |
|------|---------|-------|--------------|
| [apps/tournaments/services/leaderboard_service.py](../apps/tournaments/services/leaderboard_service.py) | Core service layer | 450 | DTOs, Redis caching (5min TTL), 5-step tie-breaker, flag gates |
| [apps/tournaments/api/leaderboards.py](../apps/tournaments/api/leaderboards.py) | Public API endpoints | 250 | 3 endpoints (tournament, participant history, scoped queries) |
| [apps/tournaments/api/admin_leaderboards.py](../apps/tournaments/api/admin_leaderboards.py) | Admin debug API | 350 | 3 endpoints (inspect, cache status, invalidate) |
| [apps/tournaments/api/admin_tournament_ops.py](../apps/tournaments/api/admin_tournament_ops.py) | Admin ops API | 350 | 3 endpoints (payments, matches, disputes tracking) |
| [apps/tournaments/utils/metrics.py](../apps/tournaments/utils/metrics.py) | Prometheus metrics | 200 | Counters (requests, cache hits/misses), histograms (latency) |
| [apps/tournaments/utils/observability.py](../apps/tournaments/utils/observability.py) | Logging & telemetry | 150 | Structured logging, trace IDs, correlation |
| [apps/common/models.py](../apps/common/models.py) | Feature flag models | 100 | FeatureFlag model (name, is_enabled, updated_at) |
| [apps/tournaments/urls.py](../apps/tournaments/urls.py) | URL routing | 50 | Public + admin API routes |
| [apps/tournaments/migrations/0023_leaderboard_flags.py](../apps/tournaments/migrations/0023_leaderboard_flags.py) | Feature flags migration | 100 | Creates 3 flags (compute, cache, API - all default False) |
| [deltacrown/settings.py](../deltacrown/settings.py) | Redis config | 50 | CACHES config for Redis, 5-minute TTL |

### Tests (6 files, ~1,550 lines, 85-90% coverage)

| File | Purpose | Lines | Coverage | Tests Passing |
|------|---------|-------|----------|---------------|
| [apps/tournaments/tests/test_leaderboard_service.py](../apps/tournaments/tests/test_leaderboard_service.py) | Service layer tests | 550 | 90% | 65 |
| [apps/tournaments/tests/test_leaderboard_api.py](../apps/tournaments/tests/test_leaderboard_api.py) | Public API tests | 450 | 88% | 48 |
| [apps/tournaments/tests/test_admin_leaderboards.py](../apps/tournaments/tests/test_admin_leaderboards.py) | Admin debug API tests | 200 | 85% | 24 |
| [apps/tournaments/tests/test_admin_tournament_ops.py](../apps/tournaments/tests/test_admin_tournament_ops.py) | Admin ops API tests | 200 | 85% | 27 |
| [apps/tournaments/tests/test_metrics.py](../apps/tournaments/tests/test_metrics.py) | Metrics instrumentation tests | 100 | 90% | 15 |
| [apps/tournaments/tests/test_observability.py](../apps/tournaments/tests/test_observability.py) | Logging tests | 50 | 88% | 8 |

### Documentation (5 files, ~3,000 lines)

| File | Purpose | Lines | Audience |
|------|---------|-------|----------|
| [docs/integration/leaderboards_examples.md](../docs/integration/leaderboards_examples.md) | Integration guide | 750 | Frontend developers, API consumers |
| [docs/runbooks/phase_e_leaderboards.md](../docs/runbooks/phase_e_leaderboards.md) | Operational runbook | 600 | SRE, ops engineers |
| [docs/leaderboards/README.md](../docs/leaderboards/README.md) | Architecture docs | 700 | Backend engineers, architects |
| [docs/leaderboards/api_readme.md](../docs/leaderboards/api_readme.md) | API reference | 400 | Backend engineers, API consumers |
| [docs/leaderboards/observability_guide.md](../docs/leaderboards/observability_guide.md) | Monitoring guide | 550 | SRE, ops engineers, admins |

### Traceability & Planning (2 files, ~450 lines)

| File | Purpose | Lines | Audience |
|------|---------|-------|----------|
| [Documents/ExecutionPlan/PHASE_E_MAP_SECTION.md](../Documents/ExecutionPlan/PHASE_E_MAP_SECTION.md) | MAP.md Phase E section | 200 | Project managers, stakeholders |
| [Documents/ExecutionPlan/PHASE_E_TRACE_NODES.yml](../Documents/ExecutionPlan/PHASE_E_TRACE_NODES.yml) | trace.yml Phase E nodes | 250 | Compliance, auditors, architects |

---

## Phase E Module Breakdown

### Module E.1: Leaderboards Service & Public API
**Status**: ✅ Complete (2025-01-26)  
**Canary Status**: T+24h promoted to 25% traffic (98.2% success)  
**Scope**: Core service layer, 3 authenticated public endpoints, Redis caching, metrics instrumentation  

**Key Files**:
- Service: [leaderboard_service.py](../apps/tournaments/services/leaderboard_service.py) (450 lines)
- API: [leaderboards.py](../apps/tournaments/api/leaderboards.py) (250 lines)
- Metrics: [metrics.py](../apps/tournaments/utils/metrics.py) (200 lines)
- Tests: [test_leaderboard_service.py](../apps/tournaments/tests/test_leaderboard_service.py) (550 lines), [test_leaderboard_api.py](../apps/tournaments/tests/test_leaderboard_api.py) (450 lines)

**Key SLOs**:
- Cache hit ratio ≥90% (actual: 92% at T+24h)
- P95 latency <100ms cached, <500ms uncached (actual: 78ms / 320ms)
- **PII discipline**: IDs-only responses (participant_id, team_id, tournament_id; no display names, emails, usernames)
- **Name resolution**: Clients use `/api/profiles/`, `/api/teams/`, `/api/tournaments/{id}/metadata/` to resolve IDs

**Actual Effort**: 40 hours

---

### Module E.2: Admin Leaderboards Debug API
**Status**: ✅ Complete (2025-01-26)  
**Scope**: 3 staff-only endpoints for cache inspection, raw aggregation debugging, manual invalidation  

**Key Files**:
- API: [admin_leaderboards.py](../apps/tournaments/api/admin_leaderboards.py) (350 lines)
- Tests: [test_admin_leaderboards.py](../apps/tournaments/tests/test_admin_leaderboards.py) (200 lines)
- Docs: [leaderboards.md](../docs/admin/leaderboards.md) (350 lines)

**Key SLOs**:
- **PII discipline**: IDs-only responses (participant_id, team_id, tournament_id, payment_id, match_id, dispute_id; no display names, emails, usernames, payment proof URLs)
- **Name resolution**: Full details available in Django Admin interface (not exposed via API)
- Audit logging: All cache invalidations logged with staff user_id

**Actual Effort**: 16 hours

---

### Module E.3: Admin Tournament Ops API
**Status**: ✅ Complete (2025-01-26)  
**Scope**: 3 read-only staff endpoints for payment/match/dispute tracking (bulk monitoring, not detailed investigation)  

**Key Files**:
- API: [admin_tournament_ops.py](../apps/tournaments/api/admin_tournament_ops.py) (350 lines)
- Tests: [test_admin_tournament_ops.py](../apps/tournaments/tests/test_admin_tournament_ops.py) (200 lines)
- Docs: [tournament_ops.md](../docs/admin/tournament_ops.md) (350 lines)

**Key SLOs**:
- PII discipline: IDs-only responses (payment_id, participant_id, match_id, dispute_id)
- Full details via Django admin interface (not exposed via API)

**Actual Effort**: 16 hours

---

### Module E.4: Runbook & Observability
**Status**: ✅ Complete (2025-01-26)  
**Scope**: 600-line operational runbook, Prometheus metrics instrumentation, observability guide  

**Key Files**:
- Runbook: [phase_e_leaderboards.md](../docs/runbooks/phase_e_leaderboards.md) (600 lines)
- Observability: [observability.py](../apps/tournaments/utils/observability.py) (150 lines), [observability_guide.md](../docs/leaderboards/observability_guide.md) (550 lines)
- Tests: [test_metrics.py](../apps/tournaments/tests/test_metrics.py) (100 lines), [test_observability.py](../apps/tournaments/tests/test_observability.py) (50 lines)

**Key SLOs**:
- Rollback time <5 minutes (feature flag toggle, no code deployment)
- Alert resolution time <15 minutes (runbook-driven)

**Actual Effort**: 16 hours

---

## Canary Deployment Timeline

| Checkpoint | Time | Status | Success Rate | Cache Hit Ratio | P95 Latency (Cached/Uncached) | Action |
|------------|------|--------|--------------|-----------------|-------------------------------|--------|
| **T+30m** | 2025-01-26 10:30 | ✅ Green | 99.1% | 88% | 82ms / 345ms | Promoted 5% → 10% |
| **T+2h** | 2025-01-26 12:00 | ✅ Green | 98.8% | 91% | 79ms / 325ms | Promoted 10% → 25% |
| **T+24h** | 2025-01-27 10:00 | ✅ Green | 98.2% | 92% | 78ms / 320ms | Promoted 25% → 50% (next step) |

**Current Traffic Split**: 25% leaderboards compute enabled, 75% legacy placeholder  
**Rollback Plan**: Set all 3 feature flags to `False` → instant traffic drain to 0%

---

## Feature Flags

All Phase E functionality is controlled by 3 feature flags (default: **OFF**):

| Flag | Default | Django Admin Toggle | Environment Variable | Effect When OFF |
|------|---------|---------------------|----------------------|-----------------|
| `LEADERBOARDS_COMPUTE_ENABLED` | `False` | ✅ Yes | `LEADERBOARDS_COMPUTE_ENABLED=true` | Service layer returns empty results |
| `LEADERBOARDS_CACHE_ENABLED` | `False` | ✅ Yes | `LEADERBOARDS_CACHE_ENABLED=true` | No Redis caching (live queries only) |
| `LEADERBOARDS_API_ENABLED` | `False` | ✅ Yes | `LEADERBOARDS_API_ENABLED=true` | Public API endpoints return 503 |

**Rollback Procedure** (instant, no code deployment):
1. Django Admin: Go to `/admin/common/featureflag/`, set all 3 flags to **OFF**
2. Or: Set environment variables to `false`, restart application
3. Result: All leaderboard endpoints return 503 (graceful degradation)

---

## Key Metrics & Observability

### Prometheus Metrics (Available in Grafana)

**Request Counters**:
- `leaderboard_requests_total{endpoint, status_code}` - Total API requests
- `leaderboard_cache_hits_total` - Cache hit count
- `leaderboard_cache_misses_total` - Cache miss count

**Latency Histograms**:
- `leaderboard_service_latency_seconds{scope}` - Service layer latency (P50/P95/P99)
- `leaderboard_api_latency_seconds{endpoint}` - API endpoint latency (P50/P95/P99)

**Cache Metrics**:
- `leaderboard_cache_evictions_total` - Total cache evictions

**Query Examples** (Prometheus):
```promql
# Cache hit ratio (last 1 hour)
sum(rate(leaderboard_cache_hits_total[1h])) / 
  (sum(rate(leaderboard_cache_hits_total[1h])) + sum(rate(leaderboard_cache_misses_total[1h])))

# P95 latency (cached requests, last 5 minutes)
histogram_quantile(0.95, rate(leaderboard_service_latency_seconds_bucket{cached="true"}[5m]))

# Request error rate (last 15 minutes)
sum(rate(leaderboard_requests_total{status_code=~"5.."}[15m])) / 
  sum(rate(leaderboard_requests_total[15m]))
```

See [observability_guide.md](../docs/leaderboards/observability_guide.md) for full query examples and alerting rules.

---

## API Endpoint Summary

### Public Endpoints (Authenticated, `IsAuthenticated` permission)

| Endpoint | Method | Purpose | Rate Limit |
|----------|--------|---------|------------|
| `/api/tournaments/{id}/leaderboard/` | GET | Fetch tournament leaderboard | 100/hour per user |
| `/api/tournaments/leaderboards/participant/{id}/history/` | GET | Player history across tournaments | 100/hour per user |
| `/api/tournaments/leaderboards/scoped/` | GET | Scoped queries (tournament/season/all-time) | 100/hour per user |

### Admin Endpoints (Staff-only, `IsAdminUser` permission)

| Endpoint | Method | Purpose | Rate Limit |
|----------|--------|---------|------------|
| `/api/admin/leaderboards/inspect/{id}/` | GET | Raw aggregation debug | 100/hour per user |
| `/api/admin/leaderboards/cache/status/` | GET | Cache health inspection | 100/hour per user |
| `/api/admin/leaderboards/cache/invalidate/` | POST | Manual cache invalidation | 10/hour per user |
| `/api/admin/tournaments/{id}/payments/` | GET | Payment verification tracking | 100/hour per user |
| `/api/admin/tournaments/{id}/matches/` | GET | Match state tracking | 100/hour per user |
| `/api/admin/tournaments/{id}/disputes/` | GET | Dispute resolution tracking | 100/hour per user |

---

## Testing Summary

**Total Tests**: ~187 passing (across 6 test files)  
**Coverage**: 85-90% (service layer 90%, API endpoints 85-88%)  
**Test Execution Time**: ~45 seconds (full suite)

**Test Coverage by Component**:
- Service layer (`leaderboard_service.py`): 90% (65 tests)
- Public API (`leaderboards.py`): 88% (48 tests)
- Admin debug API (`admin_leaderboards.py`): 85% (24 tests)
- Admin ops API (`admin_tournament_ops.py`): 85% (27 tests)
- Metrics instrumentation (`metrics.py`): 90% (15 tests)
- Observability (`observability.py`): 88% (8 tests)

**Run Tests**:
```bash
# Full Phase E test suite
pytest apps/tournaments/tests/test_leaderboard* apps/tournaments/tests/test_admin_* apps/tournaments/tests/test_metrics.py apps/tournaments/tests/test_observability.py -v

# Service layer only
pytest apps/tournaments/tests/test_leaderboard_service.py -v

# API endpoints only
pytest apps/tournaments/tests/test_leaderboard_api.py apps/tournaments/tests/test_admin_leaderboards.py apps/tournaments/tests/test_admin_tournament_ops.py -v
```

---

## Implementation Standards Compliance

Phase E adheres to all DeltaCrown implementation standards:

### PII Discipline ✅
- **IDs-only responses**: All leaderboard responses use participant_id, team_id, tournament_id (no display names, usernames, emails)
- **Name resolution**: Clients resolve IDs via `/api/profiles/`, `/api/teams/`, `/api/tournaments/{id}/metadata/`
- **Zero PII leaks validated**: 100% test coverage on serializers, audit confirmed no display names in JSON
- **Admin API IDs-only**: Admin endpoints return participant_id, team_id, payment_id, match_id, dispute_id only (no payment proof URLs, no rejection reasons)
- **Full details in Django admin**: Use `/admin/` interface for payment proof images, match lobby info, dispute evidence

### Feature Flag Control ✅
- **3 flags**: `LEADERBOARDS_COMPUTE_ENABLED`, `LEADERBOARDS_CACHE_ENABLED`, `LEADERBOARDS_API_ENABLED` (all default `False`)
- **Instant rollback**: Toggle flags in Django admin or environment config → no code deployment needed
- **Graceful degradation**: Public endpoints return 503 when flags OFF (error code `FEATURE_DISABLED`, retry_after_seconds: 300)

### Canary Deployment ✅
- **3 checkpoints**: T+30m (5%), T+2h (10%), T+24h (25%)
- **All SLOs met**: 98.2% success rate, 92% cache hit ratio, 78ms P95 latency (cached)
- **Rollback plan tested**: Instant flag toggle drains traffic to 0% within 30 seconds

### Observability ✅
- **Prometheus metrics**: 7 metrics (3 counters, 2 histograms, 2 cache metrics)
- **Structured logging**: Trace IDs, correlation, log levels (INFO/WARN/ERROR)
- **600-line runbook**: Troubleshooting scenarios, rollback procedures, alert response playbooks

### Test Coverage ✅
- **85-90% coverage**: All components covered (service layer 90%, API endpoints 85-88%)
- **187 tests passing**: Regression-safe (no test failures on promotion to 25% traffic)

---

## Project Effort Summary

**Total Effort**: ~88 hours (across 4 modules)  
**Total Lines**: ~7,300 lines (10 code files + 6 test files + 5 doc files)  
**Timeline**: January 20-26, 2025 (7 days)  

**Effort Breakdown by Module**:
- Module E.1 (Service + Public API): 40 hours (~1,200 lines code + tests)
- Module E.2 (Admin Debug API): 16 hours (~550 lines code + tests + docs)
- Module E.3 (Admin Ops API): 16 hours (~550 lines code + tests + docs)
- Module E.4 (Runbook + Observability): 16 hours (~1,100 lines docs + observability code)

**Variance from Estimate**: +8 hours (80 hours estimated, 88 actual)  
**Primary drivers**:
- Redis caching integration more complex than estimated (race conditions, TTL tuning)
- 5-step tie-breaker logic required additional edge case testing
- Runbook expanded from 400 to 600 lines (added canary procedures, alert response playbooks)

---

## Integration with Existing Systems

Phase E integrates with:

### Upstream Dependencies
- **Phase 1 (Models)**: `Tournament`, `Registration`, `Match` models (read-only queries)
- **Phase 3 (Registration)**: `Registration` model for participant data (team_id, participant_id)
- **Phase 5 (Post-Game)**: `Match` model for aggregation (points, wins, losses)
- **Phase 7 (Economy)**: `Payment` model for payment verification tracking (admin API only)
- **Phase 0 (Guardrails)**: Feature flag system (`FeatureFlag` model in `apps/common/`)

### Downstream Consumers
- **Frontend**: Leaderboard UI component (fetches from public API every 2 minutes)
- **Mobile App**: Tournament standings screen (cURL examples in integration guide)
- **Admin Dashboard**: Ops monitoring widgets (payment/match/dispute tracking endpoints)
- **Prometheus/Grafana**: Metrics scraping (7 metrics exported at `/metrics` endpoint)

---

## Future Enhancements (Post-V1)

Potential Phase E V2 improvements (not scheduled):

1. **Dedicated Leaderboard Tables**:
   - Current: Real-time aggregation from `Match` model (V1 simplicity)
   - Future: Materialized `Leaderboard` model (batch-refreshed, 1-minute staleness acceptable)
   - Benefit: 10x latency reduction (P95 <10ms vs <100ms), lower database load

2. **WebSocket Live Updates**:
   - Current: Frontend polls API every 2 minutes
   - Future: WebSocket push notifications on score changes
   - Benefit: Real-time leaderboard updates (sub-second latency)

3. **Advanced Filtering**:
   - Current: Scope-based queries (tournament/season/all-time)
   - Future: Filter by game type, region, skill tier, date range
   - Benefit: Enhanced analytics for admins, player insights

4. **Historical Snapshots**:
   - Current: Live leaderboards only (no historical data)
   - Future: Daily snapshots stored in `LeaderboardSnapshot` model
   - Benefit: Time-series analysis, trend graphs, "replay" past leaderboards

5. **Caching Strategy Upgrade**:
   - Current: Simple TTL-based Redis cache (5-minute expiry)
   - Future: Event-driven cache invalidation (invalidate on match result submission)
   - Benefit: Near-instant leaderboard updates + high cache hit ratio

---

## Contact & Support

**Questions or Issues?**

- **Technical Support**: support@deltacrown.com
- **API Issues**: File ticket in [DeltaCrown Support Portal](https://support.deltacrown.com)
- **Runbook Issues**: Update [phase_e_leaderboards.md](../docs/runbooks/phase_e_leaderboards.md) via PR
- **Code Contributions**: Follow [CONTRIBUTING.md](../CONTRIBUTING.md) guidelines

**Phase E Maintainers**:
- Backend: backend-team@deltacrown.com
- Ops/SRE: sre-team@deltacrown.com
- API/Docs: api-team@deltacrown.com

---

## Related Planning Documents

Phase E implements requirements from:

- `Documents/Planning/V1_PROJECT_GOALS.md` - Overall V1 scope (leaderboards listed as priority 2 feature)
- `Documents/Planning/ARENA_TOURNAMENT_LOGIC.md` - Tournament lifecycle, match state machine
- `Documents/Planning/MONETIZATION_PAYMENT_FLOWS.md` - Payment verification tracking (admin API)
- `Documents/Planning/PII_PRIVACY_GUIDELINES.md` - Display-name-only discipline
- `Documents/Planning/TOURNAMENT_LIFECYCLE_FLOWS.md` - Leaderboard computation timing (post-match, pre-payout)

**ADRs (Architecture Decision Records)**:
- `Documents/ExecutionPlan/ADR_LEADERBOARDS_REALTIME_V1.md` - Real-time aggregation vs materialized tables
- `Documents/ExecutionPlan/ADR_LEADERBOARDS_CACHING.md` - Redis caching strategy (5-minute TTL)
- `Documents/ExecutionPlan/ADR_LEADERBOARDS_TIEBREAKER.md` - 5-step tie-breaker cascade logic
- `Documents/ExecutionPlan/ADR_LEADERBOARDS_PII_DISCIPLINE.md` - Display names only, no email/username exposure

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-26 | Initial release (Phase E complete, T+24h canary promoted to 25%) |

---

**End of Phase E Master Navigation Index**
