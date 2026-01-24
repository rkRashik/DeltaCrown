# Organizations App — Team & Organization vNext System

**Status:** Phase 1 - Foundation (Models, Tests, Migrations)  
**Version:** 0.1.0 (Pre-Production)  
**Created:** January 25, 2026

---

## What is This App?

The **organizations** app is the **vNext Team & Organization management system** for DeltaCrown platform, built in parallel to the legacy `apps/teams` system using the **Strangler Fig migration pattern**.

### Key Characteristics

- **Parallel System:** Runs alongside legacy `apps/teams` WITHOUT modifying legacy tables
- **New Tables Only:** All tables use `organizations_*` prefix (8 tables total)
- **Legacy Isolation:** Zero imports from `apps.teams.models` - systems are completely decoupled
- **Gradual Migration:** Phased cutover from legacy to vNext (Phases 1-8 over 14 weeks)
- **Service Layer Decoupling:** All external access through services (prevents tight coupling)

### Current Phase: Phase 1 (Foundation)

**Completed:**
- ✅ 8 models created (Organization, Team, Membership, Ranking, MigrationMap, ActivityLog)
- ✅ 147 tests written (80%+ coverage requirement)
- ✅ Initial migration generated and tested on staging
- ✅ All constraints verified (CheckConstraint, UniqueConstraints, Indexes)

**Not Yet Built:**
- ⏸️ Service layer (Phase 2)
- ⏸️ API endpoints (Phase 3)
- ⏸️ Frontend templates (Phase 4)
- ⏸️ Data migration from legacy (Phase 5-7)

---

## Critical Rules & Constraints

### Database Strategy (NON-NEGOTIABLE)

1. **COMPLETELY NEW TABLES:** Only `organizations_*` tables used (no legacy table modifications)
2. **LEGACY READ-ONLY:** Zero writes to `teams_*` tables after Phase 2
3. **NO LEGACY IMPORTS:** Forbidden to import from `apps.teams.models` in vNext code
4. **MIGRATION MAP ONLY:** `TeamMigrationMap` is sole bridge between systems (Phase 5-7)

**Violations result in immediate PR rejection and potential production rollback.**

### Performance Targets (BINDING)

| Operation | p95 Latency | Max Queries |
|-----------|------------|-------------|
| Service methods (simple reads) | <50ms | ≤3 queries |
| Service methods (complex reads) | <100ms | ≤5 queries |
| Team detail page | <200ms | ≤5 queries |
| Leaderboard page | <400ms | ≤10 queries |

**Enforcement:** CI pipeline FAILS if performance tests do not pass.

### Frontend Architecture (Future Phases)

- **Tailwind CSS 3.4+** for styling (no Bootstrap, no custom CSS frameworks)
- **Vanilla JavaScript** for interactivity (no jQuery, React, or Vue in this app)
- **Django templates** for server-side rendering (htmx for dynamic updates in later phases)

### Testing Standards

- **Minimum Coverage:** 80% (Models), 85% (Services), 75% (Views)
- **Test Runtime:** <30 seconds for full suite
- **Factory Boy:** REQUIRED for all test fixtures
- **Pytest Style:** Use `pytest` conventions, not Django's `TestCase`

---

## Folder Structure

```
apps/organizations/
├── __init__.py                    # App configuration
├── README.md                      # This file
├── apps.py                        # Django app config
├── admin.py                       # (Future) Django admin integration
│
├── models/                        # Django models (Phase 1 ✅)
│   ├── __init__.py                # Model exports
│   ├── organization.py            # Organization + OrganizationMembership
│   ├── team.py                    # Team model (org XOR owner)
│   ├── membership.py              # TeamMembership (roster management)
│   ├── ranking.py                 # TeamRanking + OrganizationRanking (Crown Points)
│   ├── migration.py               # TeamMigrationMap (legacy bridge)
│   └── activity.py                # TeamActivityLog (audit trail)
│
├── choices.py                     # Enum choices (TeamStatus, MembershipRole, RankingTier, etc.)
├── signals.py                     # Signal handlers (auto-create TeamRanking)
│
├── tests/                         # Test suite (Phase 1 ✅)
│   ├── __init__.py                # Test module documentation
│   ├── factories.py               # Factory Boy fixtures (8 factories)
│   ├── test_organization.py       # Organization + OrganizationMembership tests
│   ├── test_team.py               # Team model tests (28 tests)
│   ├── test_membership.py         # TeamMembership tests (31 tests)
│   ├── test_ranking.py            # Ranking tests (32 tests)
│   ├── test_migration.py          # MigrationMap tests (19 tests)
│   └── test_activity.py           # ActivityLog tests (17 tests)
│
├── migrations/                    # Database migrations (Phase 1 ✅)
│   ├── __init__.py                # Migration directory documentation
│   └── 0001_initial.py            # Initial migration (8 models, 28 indexes, 8 constraints)
│
├── services/                      # Service layer (Phase 2 - NOT YET BUILT)
│   ├── __init__.py
│   ├── team_service.py            # Team CRUD + business logic
│   ├── organization_service.py    # Organization CRUD + business logic
│   └── ranking_service.py         # Crown Point calculations
│
├── api/                           # REST API (Phase 3 - NOT YET BUILT)
│   ├── __init__.py
│   ├── serializers.py             # DRF serializers
│   ├── views.py                   # API viewsets
│   └── urls.py                    # API routes
│
├── templates/                     # Django templates (Phase 4 - NOT YET BUILT)
│   └── organizations/
│       ├── team_detail.html
│       ├── team_list.html
│       └── organization_detail.html
│
└── static/                        # Static assets (Phase 4 - NOT YET BUILT)
    └── organizations/
        ├── css/
        └── js/
```

---

## Developer Workflow: Working Safely

### Running Code Quality Checks

```bash
# Django system check (MUST pass before any commit)
python manage.py check

# Run organizations app tests only
pytest apps/organizations/tests/ -v

# Run tests with coverage report
pytest apps/organizations/tests/ --cov=apps.organizations --cov-report=html

# Open coverage report
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS/Linux
```

**Requirement:** All tests MUST pass, coverage MUST be ≥80% before PR approval.

### Running Migrations (STAGING/TEST ONLY)

**⚠️ CRITICAL: DO NOT run migrations on production database during Phase 1-2.**

```bash
# Check migration status
python manage.py showmigrations organizations

# Apply migrations to TEST database (settings_test.py)
python manage.py migrate organizations --settings=deltacrown.settings_test

# Apply migrations to STAGING database (when available)
python manage.py migrate organizations --database=staging

# Generate SQL for review (NO database changes)
python manage.py sqlmigrate organizations 0001

# Check migration plan (shows what will be applied)
python manage.py migrate --plan
```

### Rolling Back Migrations (Emergency)

```bash
# Rollback organizations app to zero (removes all tables)
python manage.py migrate organizations zero --settings=deltacrown.settings_test

# Rollback to specific migration
python manage.py migrate organizations 0001 --settings=deltacrown.settings_test

# Verify rollback
python manage.py showmigrations organizations
```

**⚠️ Production Rollback:** Contact DevOps lead before rolling back production migrations.

### Creating New Migrations

```bash
# Generate migration after model changes
python manage.py makemigrations organizations

# Review generated migration file
cat apps/organizations/migrations/0002_*.py  # Linux/macOS
type apps\organizations\migrations\0002_*.py  # Windows

# MANDATORY: Review SQL before applying
python manage.py sqlmigrate organizations 0002
```

**Pre-Merge Checklist:**
- [ ] Migration includes only `organizations_*` tables (no legacy table changes)
- [ ] All constraints defined (CheckConstraint, UniqueConstraints)
- [ ] All indexes defined (especially for FK fields and slug lookups)
- [ ] SQL reviewed for performance (no N+1 index patterns)

---

## Database Schema Overview

### Tables (8 total)

| Table Name | Purpose | Key Constraints |
|------------|---------|-----------------|
| `organizations_organization` | Esports organization entity | Unique: name, slug |
| `organizations_org_membership` | Org roster (CEO, scouts, staff) | Unique: (organization, user) |
| `organizations_team` | Team entity (org-owned or independent) | CheckConstraint: org XOR owner |
| `organizations_membership` | Team roster (players, coaches) | Unique: (team, user, status=ACTIVE), (team, is_captain=True) |
| `organizations_ranking` | Team Crown Point rankings | OneToOne with Team |
| `organizations_org_ranking` | Organization Empire Score | OneToOne with Organization |
| `organizations_migration_map` | Legacy→vNext team ID mapping | Unique: legacy_team_id, vnext_team_id |
| `organizations_activity_log` | Team audit trail | Composite index: (team, timestamp) |

### Critical Constraints

1. **Team Ownership (XOR Constraint):**
   - Team MUST have `organization` XOR `owner` (not both, not neither)
   - Enforced by CheckConstraint: `(organization_id IS NOT NULL AND owner_id IS NULL) OR (organization_id IS NULL AND owner_id IS NOT NULL)`

2. **Unique Tournament Captain:**
   - Only one ACTIVE membership can have `is_tournament_captain=True` per team

3. **Unique Active Membership:**
   - User can only have one ACTIVE membership per team (allows multiple INACTIVE/SUSPENDED)

4. **Independent Team Uniqueness:**
   - Partial unique index: (owner, game_id) WHERE owner IS NOT NULL AND status='ACTIVE'
   - Prevents user from owning multiple active teams for same game

---

## Contracts & Planning Documents

**MANDATORY READING before contributing:**

1. **[TEAM_ORG_VNEXT_MASTER_PLAN.md](../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_VNEXT_MASTER_PLAN.md)**
   - 8-phase implementation roadmap (14 weeks)
   - Phase objectives, timelines, deliverables
   - Risk mitigation strategies

2. **[TEAM_ORG_ARCHITECTURE.md](../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ARCHITECTURE.md)**
   - Strangler Fig pattern details
   - Database strategy (hard rules)
   - Service layer architecture
   - URL routing strategy

3. **[TEAM_ORG_COMPATIBILITY_CONTRACT.md](../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_COMPATIBILITY_CONTRACT.md)**
   - Legacy system interfaces
   - Migration map usage
   - URL redirect strategy
   - Rollback procedures

4. **[TEAM_ORG_ENGINEERING_STANDARDS.md](../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ENGINEERING_STANDARDS.md)**
   - Code style rules (PEP 8, type hints, docstrings)
   - Service layer patterns
   - Query performance standards (N+1 prevention)
   - Testing requirements

5. **[TEAM_ORG_PERFORMANCE_CONTRACT.md](../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_PERFORMANCE_CONTRACT.md)** ⚠️ **BINDING**
   - Hard latency limits (p95 targets)
   - Query limits per operation type
   - Caching strategy (TTLs, invalidation)
   - Monitoring & enforcement

6. **[TEAM_ORG_VNEXT_TRACKER.md](../../../Documents/Team%20&%20Organization/Execution/TEAM_ORG_VNEXT_TRACKER.md)**
   - Task execution tracker (single source of truth)
   - Current progress (Phase 1: 4/7 tasks complete)
   - Next planned tasks
   - Task history & timestamps

---

## Testing Strategy

### Test Categories

1. **Model Tests** (`test_*.py`)
   - Field validation (max_length, choices, defaults)
   - Constraint enforcement (unique, check constraints)
   - Signal behavior (auto-create ranking)
   - String representations (`__str__`)
   - Model methods (permissions, CP calculations)

2. **Service Tests** (Phase 2 - NOT YET BUILT)
   - Business logic correctness
   - Query count limits (N+1 prevention)
   - Performance benchmarks (<100ms p95)
   - Error handling (Team.DoesNotExist, validation errors)

3. **API Tests** (Phase 3 - NOT YET BUILT)
   - Endpoint response codes (200, 400, 404)
   - Serialization correctness
   - Pagination behavior
   - Permission enforcement

### Running Specific Test Categories

```bash
# Run all model tests
pytest apps/organizations/tests/test_*.py -v

# Run specific model tests
pytest apps/organizations/tests/test_team.py -v
pytest apps/organizations/tests/test_ranking.py -v

# Run tests matching keyword
pytest apps/organizations/tests/ -k "xor" -v  # Find XOR constraint tests
pytest apps/organizations/tests/ -k "ranking" -v  # All ranking tests

# Run with coverage and fail if <80%
pytest apps/organizations/tests/ --cov=apps.organizations --cov-fail-under=80

# Run tests in parallel (faster)
pytest apps/organizations/tests/ -n auto
```

---

## Deployment Checklist (Phase 2+)

**Not applicable yet - Phase 1 is models/tests/migrations only.**

When deploying services/views in later phases:

- [ ] All tests passing (coverage ≥80%)
- [ ] Performance tests passing (<100ms p95 for services)
- [ ] Migration tested on staging database
- [ ] No imports from `apps.teams.models`
- [ ] Feature flags configured (vNext features disabled by default)
- [ ] Rollback plan documented
- [ ] Monitoring dashboards configured
- [ ] Runbook updated (troubleshooting steps)

---

## Troubleshooting

### "Can't run tests - Database error"

**Cause:** organizations migrations not applied to test database.

**Solution:**
```bash
python manage.py migrate organizations --settings=deltacrown.settings_test
```

### "IntegrityError: team_has_organization_xor_owner"

**Cause:** Attempting to create Team with BOTH organization AND owner set (or neither).

**Solution:** Team must have exactly one:
```python
# Organization-owned team
team = Team.objects.create(organization=org, owner=None, ...)

# Independent team
team = Team.objects.create(organization=None, owner=user, ...)
```

### "UniqueConstraint: one_tournament_captain_per_team"

**Cause:** Attempting to create second tournament captain for team.

**Solution:** Only one ACTIVE membership can have `is_tournament_captain=True`:
```python
# Remove old captain flag first
TeamMembership.objects.filter(team=team, is_tournament_captain=True).update(is_tournament_captain=False)

# Then set new captain
new_captain = TeamMembership.objects.create(team=team, user=user, is_tournament_captain=True, ...)
```

### "ImportError: cannot import name 'Team' from 'apps.teams.models'"

**Cause:** Accidentally importing legacy Team model in vNext code.

**Solution:** Use `apps.organizations.models.Team` instead:
```python
# ❌ WRONG
from apps.teams.models import Team

# ✅ CORRECT
from apps.organizations.models import Team
```

---

## Contributing

**This app is under active development (Phase 1 complete, Phase 2+ upcoming).**

Before contributing:
1. Read all planning documents (linked above)
2. Check [TEAM_ORG_VNEXT_TRACKER.md](../../../Documents/Team%20&%20Organization/Execution/TEAM_ORG_VNEXT_TRACKER.md) for current task
3. Ensure your work aligns with current phase objectives
4. Do NOT implement Phase 2+ features (services, views, API) during Phase 1

**Current Phase:** Phase 1 (Foundation - Models, Tests, Migrations)  
**Next Phase:** Phase 2 (Service Layer - Starting Week 5)

---

## License & Ownership

**Proprietary Software** — DeltaCrown Platform  
**Copyright:** 2026 DeltaCrown Esports Platform  
**Internal Use Only** — Not for public distribution

---

**Last Updated:** January 25, 2026  
**Document Owner:** Engineering Team  
**Review Cycle:** After each phase completion
