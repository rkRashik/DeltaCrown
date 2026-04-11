# DeltaCrown — Full Platform Test Plan

**Created:** 2026-04-10  
**Last Reconciled:** 2026-04-11 (FINAL — code-verified)  
**Audit Report:** [FULL_PLATFORM_AUDIT_REPORT.md](FULL_PLATFORM_AUDIT_REPORT.md)  
**Implementation Tracker:** [FULL_PLATFORM_IMPLEMENTATION_TRACKER.md](FULL_PLATFORM_IMPLEMENTATION_TRACKER.md)  

---

## Current Test Status (2026-04-11 — verified)

| Metric | Value |
|--------|-------|
| **Tracked test files (SQLite smoke)** | 10 files — **297 passed, 3 skipped, 0 failed** |
| **Total test files** | 472 (126 top-level + 150 subdirs + 196 app tests) |
| **Total test methods** | ~6,859 |
| **E2E framework** | Playwright — conftest.py + smoke pages exist |

### Tracked 10 Files (all verified passing)

| File | Tests | Pass | Skip |
|------|:-----:|:----:|:----:|
| `tests/test_game_scoring_validation.py` | 32 | 32 | 0 |
| `tests/test_phase6_phase7.py` | 37 | 37 | 0 |
| `tests/test_bracket_seeding.py` | 18 | 18 | 0 |
| `tests/test_ws_consumers.py` | 15 | 13 | 2 |
| `tests/test_dispute_lifecycle.py` | 27 | 27 | 0 |
| `tests/test_admin_dashboard.py` | 20 | 20 | 0 |
| `tests/test_match_room_ws.py` | 22 | 22 | 0 |
| `tests/test_tournament_lifecycle.py` | 38 | 38 | 0 |
| `tests/test_ecommerce_models.py` | 59 | 59 | 0 |
| `tests/test_security_config.py` | 32 | 31 | 1 |
| **TOTAL** | **300** | **297** | **3** |

### Implementation Status of Planned Tests

| Planned Test | Status | File |
|-------------|--------|------|
| Security IDOR tests (7 endpoints) | ❌ NOT CREATED | `tests/test_security_idor.py` |
| Valorant/CS2 scoring | ✅ DONE | `tests/test_final_scoring.py` (39 tests) |
| eFootball/aggregate scoring | ✅ DONE | `tests/test_final_scoring.py` |
| Mobile Legends KDA scoring | ✅ DONE | `tests/test_final_scoring.py` |
| Bracket seeding (3,5,6,8 groups) | ✅ DONE | `tests/test_bracket_seeding.py` (18 tests) |
| WebSocket consumer tests | ✅ DONE | `tests/test_ws_consumers.py` (15 tests) |
| Celery task unit tests | ❌ NOT CREATED | `tests/test_celery_tasks.py` |
| Dispute lifecycle E2E | ✅ DONE | `tests/test_dispute_lifecycle.py` (27 tests) |
| Admin dashboard smoke | ✅ DONE | `tests/test_admin_dashboard.py` (20 tests) |
| Game scoring validation | ✅ DONE | `tests/test_game_scoring_validation.py` (32 tests) |
| Ecommerce payment flow | ❌ NOT CREATED | `apps/ecommerce/tests/` |
| Playwright E2E setup | ✅ DONE | `tests/e2e/conftest.py` + `test_smoke_pages.py` |
| nplusone query detection | ❌ NOT INSTALLED | `requirements.txt`, `conftest.py` |
| Signal knockout transition | ✅ DONE | `apps/tournaments/tests/test_signal_knockout_transition.py` |
| Lifecycle tasks | ✅ DONE | `apps/tournaments/tests/test_lifecycle_tasks.py` |
| Payment IDOR security | ✅ DONE | `apps/tournaments/tests/test_payment_idor_security.py` |

---

## 1. Test Strategy Overview

### Test Pyramid

```
        ┌──────────────┐
        │   E2E (5%)   │  Playwright — critical user journeys
        ├──────────────┤
        │ Integration  │  Django TestCase — API, signals, services
        │   (25%)      │
        ├──────────────┤
        │  Unit (70%)  │  pytest — models, validators, utils, tasks
        └──────────────┘
```

### Test Environments

| Environment | Settings | DB | Use Case |
|-------------|----------|-----|----------|
| `settings_smoke` | SQLite in-memory | None (mocked) | Unit tests, no DB |
| `settings_test` | PostgreSQL local | `deltacrown_test` | Integration tests |
| `settings_test_pg` | PostgreSQL local | `deltacrown_test` | Full DB tests |

### Running Tests

```powershell
# Unit tests (no DB required)
$env:DJANGO_SETTINGS_MODULE = "deltacrown.settings_smoke"
python -m pytest tests/ -v -m "not integration"

# Integration tests (requires local PostgreSQL)
$env:DJANGO_SETTINGS_MODULE = "deltacrown.settings_test"
python -m pytest tests/ -v -m "integration"

# Single test file
python -m pytest tests/test_security_idor.py -v

# With query counting (after nplusone installed)
python -m pytest tests/ -v --nplusone
```

---

## 2. Unit Tests

### 2.1 Security — IDOR Authorization Tests

**File:** `tests/test_security_idor.py`  
**Priority:** 🔴 Critical  
**Depends on:** Phase 1 security fixes

| # | Test Case | Validates |
|---|-----------|-----------|
| 1 | `test_organizer_A_cannot_process_payout_for_tournament_B` | SEC-IDOR-001: Payout endpoint ownership |
| 2 | `test_organizer_cannot_refund_other_tournament` | SEC-IDOR-001: Refund endpoint ownership |
| 3 | `test_analytics_returns_403_without_user_enumeration` | SEC-IDOR-002: Uniform 403 |
| 4 | `test_results_inbox_filtered_by_organizer` | SEC-IDOR-003: Results service filter |
| 5 | `test_cannot_submit_result_after_match_completed` | SEC-IDOR-004: State machine guard |
| 6 | `test_cannot_submit_result_after_match_cancelled` | SEC-IDOR-004: Additional state |
| 7 | `test_match_viewset_filters_by_organizer_tournament` | SEC-IDOR-005: Queryset filter |
| 8 | `test_payment_verification_cascades_ownership` | SEC-IDOR-006: Service ownership cascade |
| 9 | `test_csv_export_filtered_by_tournament_ownership` | SEC-IDOR-007: Export filter |
| 10 | `test_login_rate_limited_after_5_attempts` | Rate limiting |
| 11 | `test_password_reset_rate_limited` | Rate limiting |
| 12 | `test_concurrent_result_confirmation_uses_lock` | SEC-DATA-002: Select for update |

```python
# Example structure
class TestPayoutIDOR:
    """SEC-IDOR-001: Payout/refund endpoint ownership tests."""

    def test_organizer_A_cannot_process_payout_for_tournament_B(self, api_client):
        """Organizer of Tournament A gets 403 when hitting Tournament B payout."""
        org_a = UserFactory(is_organizer=True)
        tournament_b = TournamentFactory(organizer=UserFactory(is_organizer=True))
        api_client.force_authenticate(org_a)
        response = api_client.post(f'/api/tournaments/{tournament_b.id}/payouts/')
        assert response.status_code == 403

    def test_staff_can_process_any_payout(self, api_client):
        """Staff should bypass ownership check."""
        staff = UserFactory(is_staff=True)
        tournament = TournamentFactory()
        api_client.force_authenticate(staff)
        response = api_client.post(f'/api/tournaments/{tournament.id}/payouts/')
        assert response.status_code != 403
```

### 2.2 Game-Specific Scoring Tests

**File:** `tests/test_game_scoring.py`  
**Priority:** 🟠 High

#### Valorant / CS2 (ROUNDS)

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| 1 | Standard win | 13-7 | Winner: A, round_diff: +6 |
| 2 | Close match | 13-11 | Winner: A, round_diff: +2 |
| 3 | Overtime scenario | 15-13 | Winner: A, round_diff: +2 |
| 4 | Max rounds | 25-23 | Winner: A, rounds_won: 25 |
| 5 | Round-based tiebreaker | A=13-7, B=13-10, A vs B=7-13 | Tiebreak: head-to-head B wins |
| 6 | Round diff tiebreaker | A.round_diff=+6, B.round_diff=+4, no h2h | A advances |

#### eFootball / EA FC26 (GOALS)

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| 7 | Standard win | 3-1 | Winner: A, goal_diff: +2 |
| 8 | Draw | 2-2 | Draw, points: 1 each |
| 9 | Goal difference tiebreaker | A.gd=+4, B.gd=+2, same points | A advances |
| 10 | Goals scored tiebreaker | A.gd=+4, B.gd=+4, A.gf=10, B.gf=8 | A advances |
| 11 | Head-to-head tiebreaker | Same points, same gd, A beat B | A advances |

#### PUBG / Free Fire (PLACEMENT)

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| 12 | 1st place with 10 kills | placement=1, kills=10 | score = 12 + 10 = 22 |
| 13 | 2nd place with 0 kills | placement=2, kills=0 | score = 9 |
| 14 | 16th place with 5 kills | placement=16, kills=5 | score = 0 + 5 = 5 |
| 15 | Kill tiebreaker | Same total_points, A.kills=15, B.kills=12 | A advances |
| 16 | Average placement tiebreaker | Same points+kills, A.avg=3.2, B.avg=5.1 | A (lower) |

#### Mobile Legends (WIN_LOSS)

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| 17 | Win gives 3 points | A wins | A.points += 3 |
| 18 | Loss gives 0 points | A loses | A.points += 0 |
| 19 | Draw gives 1 point | Draw | Both += 1 |
| 20 | H2H tiebreaker | Same points, A beat B | A advances |

### 2.3 Bracket Seeding Tests

**File:** `tests/test_bracket_seeding.py`  
**Priority:** 🟠 High

| # | Test Case | Validates |
|---|-----------|-----------|
| 1 | 4 groups → 8-team bracket (standard cross-match) | Happy path |
| 2 | 3 groups → 6-team bracket + 2 byes | Odd group handling |
| 3 | 5 groups → 10-team bracket + 6 byes | Large odd groups |
| 4 | 8 groups → 16-team bracket | Power of 2 |
| 5 | 2 groups → 4-team bracket | Minimum viable |
| 6 | Cross-matching: 1A vs 2B, 1B vs 2A | Seeding correctness |
| 7 | Ranked seeding preserves standings order | Sorted by points |
| 8 | Random seeding yields different orders per run | Randomness |
| 9 | Manual seeding uses admin-provided order | Admin override |

### 2.4 Upload Validator Tests

**File:** `tests/test_upload_validators.py` (extend existing)  
**Priority:** 🟡 Medium

| # | Test Case | Validates |
|---|-----------|-----------|
| 1 | Valid JPEG accepted | Magic bytes check |
| 2 | Valid PNG accepted | Magic bytes check |
| 3 | EXE renamed to .jpg rejected | MIME sniffing |
| 4 | SVG rejected (not in allowed types) | Type whitelist |
| 5 | File > 5 MB rejected | Size limit |
| 6 | Valid PDF accepted (document validator) | PDF magic bytes |
| 7 | HTML file renamed to .pdf rejected | MIME sniffing |
| 8 | File exactly at size limit accepted | Edge case |

### 2.5 Celery Task Unit Tests

**File:** `tests/test_celery_tasks.py`  
**Priority:** 🟠 High

| # | Test Case | Validates |
|---|-----------|-----------|
| 1 | `auto_advance_tournaments` transitions REGISTRATION_OPEN → CLOSED | Status transition |
| 2 | `check_tournament_wrapup` completes when all matches terminal (incl. forfeit) | Terminal state set |
| 3 | `reconcile_stuck_tournaments` fixes stuck GROUP_PLAYOFF | Recovery path |
| 4 | `reconcile_stuck_tournaments` skips healthy tournaments | No false positives |
| 5 | `send_daily_digest` processes users in batches of 100 | Memory optimization |
| 6 | `send_daily_digest` handles empty user set gracefully | Edge case |
| 7 | Task retry on transient DB error | Retry policy |
| 8 | Task respects soft time limit | Timeout behavior |

---

## 3. Integration Tests

### 3.1 Tournament Lifecycle Integration

**File:** `tests/integration/test_lifecycle_e2e.py`  
**Priority:** 🔴 Critical  
**Requires:** Local PostgreSQL (`settings_test`)  
**Marker:** `@pytest.mark.integration`

| # | Test Case | Scope |
|---|-----------|-------|
| 1 | Full GROUP_PLAYOFF lifecycle (create → groups → matches → knockout → complete) | Happy path |
| 2 | Same lifecycle for SINGLE_ELIMINATION format | Format variation |
| 3 | Same lifecycle for DOUBLE_ELIMINATION format | Format variation |
| 4 | Tournament with 16 participants across 4 groups (eFootball config) | Game-specific |
| 5 | Tournament with 64 participants (PUBG, placement scoring) | Scale test |
| 6 | Group→Knockout via signal path (not direct service call) | Signal integration |
| 7 | Group→Knockout via Celery reconciliation task | Recovery path |
| 8 | Tournament cancellation mid-group stage | Cancellation |
| 9 | Tournament with forfeited matches completes properly | BUG-005 verify |

### 3.2 Payment & Registration Integration

**File:** `tests/integration/test_payment_registration.py`  
**Priority:** 🟠 High

| # | Test Case | Scope |
|---|-----------|-------|
| 1 | Full registration flow (register → pay → confirm → check-in) | Happy path |
| 2 | Registration with waitlist (capacity full → waitlist → slot opens) | Waitlist |
| 3 | Payment proof upload → staff verify → confirmed | Payment flow |
| 4 | Payment rejection → resubmit → approve | Rejection recovery |
| 5 | Refund request → process → payout | Refund flow |
| 6 | Duplicate registration attempt rejected | Guard |
| 7 | Registration after close date rejected | Time guard |

### 3.3 Dispute Resolution Integration

**File:** `tests/integration/test_dispute_lifecycle.py`  
**Priority:** 🟠 High

| # | Test Case | Scope |
|---|-----------|-------|
| 1 | Create dispute with evidence → admin reviews → resolved (winner) | Happy path |
| 2 | Create dispute → timeout → auto-resolved by system | Timeout |
| 3 | Multiple disputes on same match → merged or sequential | Multi-dispute |
| 4 | Dispute on completed match → result revision | Post-complete |
| 5 | Evidence file upload → size/type validation | Upload guard |

### 3.4 API Permission Integration

**File:** `tests/integration/test_api_permissions.py`  
**Priority:** 🟠 High

| # | Test Case | Validates |
|---|-----------|-----------|
| 1 | Unauthenticated user → 401 on all protected endpoints | Auth check |
| 2 | Player → 403 on organizer-only endpoints | Role check |
| 3 | Organizer → 200 on own tournament endpoints | Ownership |
| 4 | Organizer → 403 on other's tournament endpoints | Cross-access |
| 5 | Staff → 200 on any tournament endpoint | Admin override |
| 6 | Co-organizer → appropriate access level | Delegation |

### 3.5 WebSocket Consumer Integration

**File:** `tests/integration/test_ws_consumers.py`  
**Priority:** 🟡 Medium  
**Requires:** `channels[daphne]` test utilities

| # | Test Case | Validates |
|---|-----------|-----------|
| 1 | Match room connect → auth validated → joined | Connection |
| 2 | Match room message → broadcast to participants | Messaging |
| 3 | Match room disconnect → presence updated | Cleanup |
| 4 | Lobby consumer → ready check → all ready → start | Ready flow |
| 5 | Bracket update → push to spectators | Real-time update |
| 6 | Invalid auth token → connection rejected | Auth guard |
| 7 | Connection drop → reconnect → state restored | Recovery |

---

## 4. E2E Tests (Browser Automation)

### 4.1 Setup

**Framework:** Playwright (Python)  
**Install:** `pip install playwright && playwright install chromium`  
**Directory:** `e2e/`

```python
# e2e/conftest.py
import pytest
from playwright.sync_api import Page

@pytest.fixture
def authenticated_page(page: Page, live_server):
    """Log in as test user and return authenticated page."""
    page.goto(f"{live_server.url}/accounts/login/")
    page.fill("#id_username", "testuser")
    page.fill("#id_password", "testpass123")
    page.click("button[type=submit]")
    page.wait_for_url("**/dashboard/**")
    return page
```

### 4.2 Critical User Journeys

**File:** `e2e/test_critical_journeys.py`  
**Priority:** 🟠 High

| # | Test Case | Journey |
|---|-----------|---------|
| 1 | **Tournament Creation** | Login → Dashboard → Create Tournament → Configure → Publish |
| 2 | **Player Registration** | Browse → Tournament Detail → Register → Pay → Confirmation |
| 3 | **Bracket Generation** | Login as Organizer → TOC → Groups → Close Group Stage → Generate Bracket |
| 4 | **Match Result Submission** | Join Match Room → Submit Score → Opponent Confirms → Match Complete |
| 5 | **Dispute Filing** | Match Complete → File Dispute → Upload Evidence → Submit |

### 4.3 Responsive Tests

**File:** `e2e/test_responsive.py`  
**Priority:** 🟡 Medium

| # | Test Case | Viewport | Validates |
|---|-----------|:--------:|-----------|
| 1 | Registration form on mobile | 375×667 | Labels visible, inputs not zoomed |
| 2 | Hub date tape on small screen | 375×667 | Scroll indicator present |
| 3 | TOC sidebar on tablet | 768×1024 | Sidebar collapsed, content full-width |
| 4 | Match room on mobile | 375×667 | Chat input above keyboard |
| 5 | Bracket visualization on mobile | 375×667 | Horizontal scroll enabled |

---

## 5. Performance Tests

### 5.1 Query Count Tests

**File:** `tests/performance/test_query_counts.py`  
**Requires:** `django.test.utils.override_settings`, `django.test.TestCase`

| # | Test Case | Max Queries |
|---|-----------|:-----------:|
| 1 | Tournament hub page load (100 participants) | ≤ 30 |
| 2 | Admin dashboard load | ≤ 10 |
| 3 | Cart checkout with 5 items | ≤ 5 |
| 4 | Match detail page | ≤ 20 |
| 5 | Group standings calculation (4 groups, 16 teams) | ≤ 15 |
| 6 | Bracket generation (16 teams) | ≤ 25 |
| 7 | Notification send to 10-person team | ≤ 5 |

```python
# Example
class TestQueryCounts(TestCase):
    def test_hub_page_query_count(self):
        tournament = TournamentFactory(participant_count=100)
        with self.assertNumQueries(30):
            response = self.client.get(f'/tournaments/{tournament.slug}/hub/')
        assert response.status_code == 200
```

### 5.2 Memory Usage Tests

**File:** `tests/performance/test_memory.py`  
**Priority:** 🟡 Medium

| # | Test Case | Max Memory |
|---|-----------|:----------:|
| 1 | `send_daily_digest` with 1000 users | ≤ 10 MB |
| 2 | `snapshot_active_tournaments` with 50 tournaments | ≤ 5 MB |
| 3 | Bracket generation for 128 teams | ≤ 20 MB |

---

## 6. Regression Test Matrix

### 6.1 Game × Format Coverage

| Format | Valorant | eFootball | PUBG | Dota 2 | MLBB | Free Fire |
|--------|:--------:|:---------:|:----:|:------:|:----:|:---------:|
| Single Elim | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Double Elim | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Round Robin | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Group → Knockout | NEEDS | NEEDS | NEEDS | NEEDS | NEEDS | NEEDS |

**Goal:** Fill every NEEDS cell with a dedicated test.

### 6.2 Tiebreaker Matrix

| Scoring Type | H2H | Score Diff | Total Score | Kills | Placement |
|:-------------|:---:|:----------:|:-----------:|:-----:|:---------:|
| ROUNDS | NEEDS | NEEDS | NEEDS | — | — |
| GOALS | NEEDS | NEEDS | NEEDS | — | — |
| WIN_LOSS | NEEDS | — | — | — | — |
| PLACEMENT | — | — | NEEDS | NEEDS | NEEDS |

**Goal:** 20+ tiebreaker combination tests.

---

## 7. CI Integration

### 7.1 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    env:
      DJANGO_SETTINGS_MODULE: deltacrown.settings_smoke
      DATABASE_URL: sqlite:////:memory:
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -v -m "not integration" --tb=short

  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: dcadmin
          POSTGRES_PASSWORD: dcpass123
          POSTGRES_DB: deltacrown_test
        ports: ['5433:5432']
    env:
      DJANGO_SETTINGS_MODULE: deltacrown.settings_test
      DATABASE_URL: postgresql://dcadmin:dcpass123@localhost:5433/deltacrown_test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: python manage.py migrate --no-input
      - run: python -m pytest tests/ -v -m "integration" --tb=short

  e2e:
    runs-on: ubuntu-latest
    needs: [unit, integration]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt playwright
      - run: playwright install chromium
      - run: python -m pytest e2e/ -v --tb=short
```

### 7.2 Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: unit-tests
        name: Quick unit tests
        entry: python -m pytest tests/ -x -q -m "not integration" --no-header
        language: system
        pass_filenames: false
        always_run: true
```

---

## 8. Test Priority & Effort Estimates

| Phase | Test Category | # Tests | Effort | Priority |
|:-----:|---------------|:-------:|--------|----------|
| 1 | Security IDOR tests | 12 | 1 day | 🔴 Critical |
| 2 | Game scoring tests (4 types) | 20 | 2 days | 🟠 High |
| 3 | Bracket seeding tests | 9 | 1 day | 🟠 High |
| 4 | Celery task tests | 8 | 1 day | 🟠 High |
| 5 | Lifecycle integration | 9 | 2 days | 🔴 Critical |
| 6 | Payment/Registration integration | 7 | 1 day | 🟠 High |
| 7 | Dispute lifecycle | 5 | 1 day | 🟡 Medium |
| 8 | API permission tests | 6 | 1 day | 🟠 High |
| 9 | WebSocket consumer tests | 7 | 2 days | 🟡 Medium |
| 10 | Query count tests | 7 | 1 day | 🟡 Medium |
| 11 | E2E browser tests | 5 | 2 days | 🟡 Medium |
| 12 | Responsive E2E | 5 | 1 day | 🟢 Low |
| **Total** | | **100** | **~16 days** | |

---

## 9. Coverage Targets

| Metric | Current | Target (Sprint 1) | Target (Sprint 3) |
|--------|:-------:|:------------------:|:------------------:|
| Overall test count | 62 | 120+ | 200+ |
| Apps with tests | ~16/29 | 20/29 | 25/29 |
| Critical path coverage | 50% | 80% | 95% |
| Game scoring coverage | 40% | 75% | 95% |
| API permission coverage | 75% | 90% | 98% |
| WebSocket coverage | 30% | 50% | 80% |
| E2E journey coverage | 10% | 30% | 60% |

---

## 10. Appendix: Test File Locations

| Category | File | Status |
|----------|------|--------|
| Lifecycle (Phase 2) | `apps/tournaments/tests/test_signal_knockout_transition.py` | ✅ 7 tests |
| Lifecycle (Phase 2) | `apps/tournaments/tests/test_lifecycle_tasks.py` | ✅ 7 tests |
| Payment IDOR (Phase 2) | `apps/tournaments/tests/test_payment_idor_security.py` | ✅ 5 tests |
| Lifecycle (Phase 3) | `tests/test_tournament_lifecycle_full.py` | ✅ 43 tests |
| BR Points | `apps/tournaments/tests/test_points_br.py` (estimated) | ✅ 15+ tests |
| Security IDOR (NEW) | `tests/test_security_idor.py` | TODO |
| Game Scoring (NEW) | `tests/test_game_scoring.py` | TODO |
| Bracket Seeding (NEW) | `tests/test_bracket_seeding.py` | TODO |
| Celery Tasks (NEW) | `tests/test_celery_tasks.py` | TODO |
| Lifecycle Integration (NEW) | `tests/integration/test_lifecycle_e2e.py` | TODO |
| Payment Integration (NEW) | `tests/integration/test_payment_registration.py` | TODO |
| Dispute Integration (NEW) | `tests/integration/test_dispute_lifecycle.py` | TODO |
| API Permissions (NEW) | `tests/integration/test_api_permissions.py` | TODO |
| WebSocket (NEW) | `tests/integration/test_ws_consumers.py` | TODO |
| Query Counts (NEW) | `tests/performance/test_query_counts.py` | TODO |
| E2E Journeys (NEW) | `e2e/test_critical_journeys.py` | TODO |
| E2E Responsive (NEW) | `e2e/test_responsive.py` | TODO |
