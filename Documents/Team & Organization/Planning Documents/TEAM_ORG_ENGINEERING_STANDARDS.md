# 🛠️ Team & Organization System — Engineering Standards

**Document Version:** 1.1  
**Effective Date:** January 25, 2026  
**Owner:** Engineering Team  
**Status:** Mandatory Compliance Document  
**Enforcement:** All code must pass standards review before merge

**Related Documents:**
- [TEAM_ORG_PERFORMANCE_CONTRACT.md](./TEAM_ORG_PERFORMANCE_CONTRACT.md) ⚠️ **BINDING PERFORMANCE REQUIREMENTS**
- [TEAM_ORG_ARCHITECTURE.md](./TEAM_ORG_ARCHITECTURE.md) - System architecture
- [TEAM_ORG_VNEXT_MASTER_PLAN.md](./TEAM_ORG_VNEXT_MASTER_PLAN.md) - Implementation plan

**Changelog:**
- v1.1 (Jan 25, 2026): Added performance contract reference, database strategy cross-reference
- v1.0 (Jan 24, 2026): Initial engineering standards

---

## Table of Contents

1. [Code Style & Conventions](#1-code-style--conventions)
2. [Service Layer Architecture](#2-service-layer-architecture)
3. [Query Performance Standards](#3-query-performance-standards)
4. [Error Handling & Logging](#4-error-handling--logging)
5. [Testing Requirements](#5-testing-requirements)
6. [Security Standards](#6-security-standards)
7. [Frontend Architecture](#7-frontend-architecture)
8. [Documentation Requirements](#8-documentation-requirements)

---

## ⚠️ CRITICAL: Database Strategy Compliance

**Before writing any code, read:**
- [TEAM_ORG_ARCHITECTURE.md - Section 2: Database Strategy](./TEAM_ORG_ARCHITECTURE.md#2-database-strategy-hard-rules)

**NON-NEGOTIABLE RULES:**
1. **COMPLETELY NEW TABLES:** vNext uses `organizations_*` tables ONLY (no legacy table modifications)
2. **LEGACY READ-ONLY:** Zero writes to `teams_*` tables after Phase 2
3. **NO LEGACY IMPORTS:** Forbidden to import from `apps.teams.models` in vNext code
4. **MIGRATION MAP ONLY:** `TeamMigrationMap` is sole bridge between systems (Phase 5-7)

**Violations result in immediate PR rejection and potential production rollback.**

---

## ⚠️ CRITICAL: Performance Requirements Compliance

**Before writing any code, read:**
- [TEAM_ORG_PERFORMANCE_CONTRACT.md](./TEAM_ORG_PERFORMANCE_CONTRACT.md) ⚠️ **BINDING REQUIREMENTS**

**Key Performance Targets (Hard Limits):**
- **Service methods:** <100ms (p95 latency)
- **Page loads:** <200ms (team detail), <400ms (leaderboards)
- **Max queries:** ≤5 queries per detail view, ≤7 per list view
- **N+1 prevention:** MANDATORY `select_related()` / `prefetch_related()`
- **Caching:** Leaderboards (5 min TTL), team data (10-15 min TTL)
- **Async jobs:** Notifications, CP decay, leaderboard updates

**CI pipeline will FAIL if performance tests do not pass.**

---

## 1. Code Style & Conventions

### 1.1 Python Style Rules

**Mandatory:**
- ✅ **MUST** follow PEP 8 (enforced by Black formatter, line length: 120 chars).
- ✅ **MUST** use type hints for all function signatures in services, models, and utilities.
- ✅ **MUST** use f-strings for string formatting (no `.format()` or `%` formatting).
- ✅ **MUST** use pathlib for file path operations (not `os.path`).

**Forbidden:**
- ❌ **MUST NOT** use wildcard imports (`from module import *`).
- ❌ **MUST NOT** use bare `except:` clauses (always specify exception types).
- ❌ **MUST NOT** use mutable default arguments (e.g., `def func(items=[])`).

**Example (Correct):**
```python
from typing import List, Optional
from pathlib import Path

def get_team_members(team_id: int, active_only: bool = True) -> List[dict]:
    """
    Retrieve team members with optional filtering.
    
    Args:
        team_id: Team primary key
        active_only: If True, return only ACTIVE members
        
    Returns:
        List of member dictionaries
        
    Raises:
        Team.DoesNotExist: If team_id is invalid
    """
    queryset = TeamMembership.objects.filter(team_id=team_id)
    
    if active_only:
        queryset = queryset.filter(status='ACTIVE')
    
    return list(queryset.values('profile__username', 'role', 'joined_at'))
```

### 1.2 Naming Conventions

**Models:**
- Singular nouns: `Organization`, `Team`, `TeamMembership` (not `Teams`, `Memberships`).
- Enum classes as nested classes: `Team.Status`, `TeamMembership.Role`.

**Services:**
- Suffix with `Service`: `TeamService`, `RankingService`.
- Method names: `verb_noun` pattern: `get_team_identity()`, `validate_roster()`, `create_organization()`.
- Private helpers: Prefix with `_`: `_get_team()`, `_check_migration_status()`.

**Views:**
- Function-based views: `noun_verb`: `team_detail()`, `organization_create()`.
- Class-based views: `NounVerbView`: `TeamDetailView`, `OrganizationCreateView`.

**Templates:**
- Snake_case: `team_detail.html`, `organization_roster.html`.
- Partials: Prefix with `_`: `_roster_card.html`, `_team_header.html`.

**URLs:**
- Kebab-case: `/orgs/syntax-gaming/teams/protocol-v/`.
- Named routes: `app_name:resource_action`: `organizations:team_detail`, `organizations:org_team_create`.

**Database:**
- Table names: Django auto-generated (`organizations_team`, `organizations_membership`).
- Column names: Snake_case: `is_verified`, `created_at`, `empire_score`.
- Indexes: Descriptive suffix: `idx_team_game_region`, `idx_membership_status`.

### 1.3 Docstring Standards

**MUST use Google-style docstrings for all:**
- Public functions and methods.
- Service layer methods (mandatory).
- Model methods (mandatory).
- Complex view functions.

**Format:**
```python
def method_name(arg1: Type1, arg2: Type2) -> ReturnType:
    """
    One-line summary ending with period.
    
    Detailed description if needed. Explain business logic, assumptions,
    and any non-obvious behavior.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When this exception occurs
        
    Example:
        >>> result = method_name(1, 2)
        >>> print(result)
        3
    """
```

**Forbidden:**
- ❌ No docstrings (service methods without docstrings fail code review).
- ❌ Vague docstrings: `"""Does stuff."""` (must explain what, why, and edge cases).

### 1.4 Commenting Rules

**When to Comment:**
- ✅ Complex business logic: Explain *why*, not *what*.
- ✅ Workarounds for platform bugs: Cite issue number and date.
- ✅ Performance optimizations: Explain trade-offs.
- ✅ Database queries: Explain join strategy and expected result size.
- ✅ Migration scripts: Explain data transformation logic.

**Example (Good Comments):**
```python
# Phase 5-7: Check migration map to route between legacy and vNext systems.
# After Phase 8, this conditional is removed and all queries go to vNext.
if MigrationService.is_dual_system_active():
    vnext_id = TeamMigrationMap.get_vnext_id(team_id)
    if vnext_id:
        return VNextTeam.objects.get(id=vnext_id)

# Performance: Prefetch memberships to avoid N+1 queries when displaying roster.
# Expected: 1 team query + 1 membership query (not 1 + N per member).
teams = Team.objects.prefetch_related('memberships__profile__user').filter(status='ACTIVE')

# Workaround: Django 4.2 doesn't support JSONField array indexing in SQLite.
# Remove this .extra() call after upgrading to PostgreSQL in Phase 3.
# See: https://code.djangoproject.com/ticket/32717
queryset = queryset.extra(where=["json_extract(metadata, '$.verified') = 1"])
```

**Forbidden:**
- ❌ Obvious comments: `i += 1  # Increment i` (noise).
- ❌ Commented-out code: Delete it (use git history if needed).
- ❌ TODO without context: `# TODO: Fix this` (must include who, when, why).

---

## 2. Service Layer Architecture

### 2.1 Service-Oriented Design Principles

**Architecture Pattern:**
```
Views (HTTP layer) → Services (Business logic) → Models (Data layer)
```

**Rules:**
- ✅ **Views MUST be thin:** Handle HTTP request/response only, delegate to services.
- ✅ **Services MUST be stateless:** All methods are `@staticmethod` or `@classmethod`.
- ✅ **Services MUST NOT import views:** One-way dependency only.
- ✅ **Models MUST NOT contain complex business logic:** Keep model methods to basic helpers.

**Example (Correct Architecture):**

**View (Thin):**
```python
from django.shortcuts import render, redirect
from apps.organizations.services import TeamService
from apps.organizations.exceptions import RosterValidationError

def tournament_registration(request, tournament_id):
    """Register team for tournament."""
    team_id = request.POST.get('team_id')
    
    try:
        # Delegate validation to service
        result = TeamService.validate_roster(team_id, tournament_id)
        
        if result.is_valid:
            # Delegate registration to tournament service
            TournamentService.register_team(tournament_id, team_id, request.user)
            return redirect('tournaments:registration_success')
        else:
            return render(request, 'tournaments/register.html', {
                'errors': result.errors,
                'warnings': result.warnings
            })
    except RosterValidationError as e:
        return render(request, 'tournaments/register.html', {'error': str(e)})
```

**Service (Fat):**
```python
class TeamService:
    @staticmethod
    def validate_roster(team_id: int, tournament_id: int) -> ValidationResult:
        """
        Validate team roster meets tournament requirements.
        
        Business rules:
        1. Roster size >= tournament minimum
        2. All starters have valid Game Passports
        3. No banned/suspended players
        4. No overlapping roster locks
        
        Args:
            team_id: Team primary key
            tournament_id: Tournament primary key
            
        Returns:
            ValidationResult with is_valid flag and error/warning lists
        """
        team = Team.objects.select_related('game').get(id=team_id)
        tournament = Tournament.objects.select_related('game').get(id=tournament_id)
        
        errors = []
        warnings = []
        
        # Rule 1: Game match
        if team.game_id != tournament.game_id:
            errors.append(f"Team game ({team.game.name}) ≠ tournament game ({tournament.game.name})")
        
        # Rule 2: Roster size
        active_count = team.memberships.filter(status='ACTIVE', role__in=['PLAYER', 'SUBSTITUTE']).count()
        if active_count < tournament.min_roster_size:
            errors.append(f"Roster has {active_count} players, need {tournament.min_roster_size}")
        
        # Rule 3: Game Passports
        starters = team.memberships.filter(status='ACTIVE', roster_slot='STARTER').select_related('profile')
        for member in starters:
            if not member.profile.has_valid_passport(team.game_id):
                errors.append(f"{member.profile.username} missing valid Game Passport")
        
        # Rule 4: Roster locks
        overlapping = team.get_overlapping_tournaments(tournament)
        if overlapping:
            warnings.append(f"Team locked in {len(overlapping)} overlapping tournament(s)")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            roster_data={'active_count': active_count, 'starter_count': len(starters)}
        )
```

### 2.2 Service Boundaries

**Separation of Concerns:**

| Service | Responsibility | Must NOT Handle |
|---------|----------------|-----------------|
| `TeamService` | Team identity, roster, validation | Organization management, ranking calculations |
| `OrganizationService` | Org management, acquisitions | Team roster operations, tournament registration |
| `RankingService` | CP calculation, leaderboards | Team creation, roster validation |
| `MigrationService` | Legacy/vNext routing (Phase 5-7) | Business logic (readonly helper only) |

**Cross-Service Communication:**
- ✅ **MUST** call other services via public methods: `RankingService.award_cp(team_id, ...)`.
- ❌ **MUST NOT** access other service's private methods: `_internal_helper()`.
- ❌ **MUST NOT** import models from other apps: Use service layer only.

### 2.3 Transaction Management

**Rules:**
- ✅ **MUST** use `@transaction.atomic` for all write operations that modify multiple tables.
- ✅ **MUST** use `select_for_update()` for operations requiring locking (e.g., prize withdrawals).
- ❌ **MUST NOT** nest transactions unless absolutely necessary (prefer single outer transaction).

**Example:**
```python
from django.db import transaction

class OrganizationService:
    @staticmethod
    @transaction.atomic
    def acquire_team(org_id: int, team_id: int, actor_id: int) -> dict:
        """
        Transfer team ownership from user to organization.
        
        This operation modifies:
        1. Team.organization (set to org)
        2. Team.owner (set to NULL)
        3. TeamMembership (convert OWNER to MANAGER)
        4. TeamActivityLog (audit entry)
        5. OrganizationRanking (recalculate Empire Score)
        
        All changes must succeed or rollback together.
        """
        # Lock team to prevent concurrent modifications
        team = Team.objects.select_for_update().get(id=team_id)
        org = Organization.objects.select_for_update().get(id=org_id)
        
        if team.organization:
            raise ValueError("Team already owned by organization")
        
        previous_owner = team.owner
        
        # Step 1: Transfer ownership
        team.organization = org
        team.owner = None
        team.save()
        
        # Step 2: Update membership roles
        TeamMembership.objects.filter(
            team=team,
            profile__user=previous_owner,
            role='OWNER'
        ).update(role='MANAGER')
        
        # Step 3: Log activity
        TeamActivityLog.objects.create(
            team=team,
            action_type='ACQUIRE',
            actor_id=actor_id,
            actor_username=previous_owner.username,
            description=f"Acquired by {org.name}",
            metadata={'org_id': org.id, 'prev_owner_id': previous_owner.id}
        )
        
        # Step 4: Recalculate rankings
        org.calculate_empire_score()
        
        return {'success': True, 'team_id': team.id, 'org_id': org.id}
```

---

## 3. Query Performance Standards

### 3.1 N+1 Query Prevention

**Mandatory Patterns:**

**Rule 1: Always use `select_related()` for FK traversals:**
```python
# ❌ WRONG (N+1 queries)
teams = Team.objects.filter(status='ACTIVE')
for team in teams:
    print(team.game.name)  # Queries game table N times

# ✅ CORRECT (2 queries)
teams = Team.objects.filter(status='ACTIVE').select_related('game')
for team in teams:
    print(team.game.name)  # No additional query
```

**Rule 2: Always use `prefetch_related()` for reverse FKs and M2M:**
```python
# ❌ WRONG (1 + N queries)
teams = Team.objects.filter(status='ACTIVE')
for team in teams:
    members = team.memberships.all()  # N queries

# ✅ CORRECT (2 queries: 1 for teams, 1 for all memberships)
teams = Team.objects.filter(status='ACTIVE').prefetch_related('memberships')
for team in teams:
    members = team.memberships.all()  # No additional query
```

**Rule 3: Chain related lookups:**
```python
# ✅ CORRECT (3 queries: teams, memberships, profiles)
teams = Team.objects.prefetch_related(
    'memberships__profile__user'
).filter(status='ACTIVE')

for team in teams:
    for membership in team.memberships.all():
        print(membership.profile.user.username)  # No additional queries
```

### 3.2 Query Optimization Checklist

**Before Writing a Query:**
- ✅ **MUST** use `only()` or `defer()` if fetching large text fields not needed immediately.
- ✅ **MUST** use `values()` or `values_list()` for simple data extraction (no model instances needed).
- ✅ **MUST** use `exists()` instead of `count() > 0` for existence checks.
- ✅ **MUST** use `iterator()` for processing large querysets (>1000 records).

**Examples:**
```python
# Existence check
if Team.objects.filter(owner=user, game_id=game_id).exists():  # ✅ CORRECT
    raise ValueError("User already owns team for this game")

if Team.objects.filter(owner=user, game_id=game_id).count() > 0:  # ❌ WRONG (slower)
    raise ValueError("User already owns team for this game")

# Large dataset processing
for team in Team.objects.all().iterator(chunk_size=500):  # ✅ CORRECT (memory-efficient)
    process_team(team)

# Defer large fields
teams = Team.objects.defer('description', 'banner').filter(status='ACTIVE')  # ✅ CORRECT
```

### 3.3 Pagination Policy

**Mandatory:**
- ✅ **MUST** paginate all list views displaying >50 records.
- ✅ **MUST** use Django Paginator (not custom slicing).
- ✅ **MUST** include pagination metadata in API responses.

**Example:**
```python
from django.core.paginator import Paginator

def team_list(request):
    """Display paginated team list."""
    teams = Team.objects.select_related('game', 'organization').filter(status='ACTIVE')
    
    paginator = Paginator(teams, 50)  # 50 teams per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'organizations/team_list.html', {
        'page_obj': page_obj,
        'total_count': paginator.count
    })
```

### 3.4 Database Index Requirements

**MUST create indexes for:**
- All FK columns (auto-created by Django).
- Columns used in `filter()` with high frequency (e.g., `status`, `game_id`).
- Columns used in `order_by()` (e.g., `-created_at`, `-current_cp`).
- Composite indexes for common filter combinations (e.g., `['game', 'region']`).

**Example (in models):**
```python
class Team(models.Model):
    # ... fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['slug']),  # URL lookups
            models.Index(fields=['status']),  # Active team filter
            models.Index(fields=['game', 'region']),  # Leaderboard queries
            models.Index(fields=['-created_at']),  # Recent teams sorting
        ]
```

### 3.5 Performance Benchmarks

**Required Targets:**

| Operation | Max Response Time | Max Query Count | Notes |
|-----------|-------------------|-----------------|-------|
| Team detail page | 200ms | 5 queries | With `select_related`, `prefetch_related` |
| Team list page (50 items) | 300ms | 3 queries | Paginated, with game/org data |
| Tournament registration | 500ms | 10 queries | Includes roster validation |
| Leaderboard (100 teams) | 400ms | 2 queries | Single query for teams + rankings |
| Service method call | 100ms | 3 queries | Average across all service methods |

**Enforcement:**
- Django Debug Toolbar in development (shows query count and time).
- Automated performance tests in CI (fail if benchmarks exceeded).

---

## 4. Error Handling & Logging

### 4.1 Custom Exception Hierarchy

**Mandatory Structure:**
```python
# apps/organizations/exceptions.py

class OrganizationsError(Exception):
    """Base exception for organizations app."""
    
    def __init__(self, message: str, user_message: str = None, context: dict = None):
        """
        Initialize exception with internal and user-facing messages.
        
        Args:
            message: Technical message for logging
            user_message: Safe message to display to user (optional)
            context: Additional context for debugging (optional)
        """
        self.message = message
        self.user_message = user_message or "An error occurred. Please try again."
        self.context = context or {}
        super().__init__(message)


class TeamNotFoundError(OrganizationsError):
    """Team does not exist."""
    pass


class PermissionDeniedError(OrganizationsError):
    """User lacks required permission."""
    pass


class RosterValidationError(OrganizationsError):
    """Roster fails validation checks."""
    
    def __init__(self, errors: list, warnings: list = None):
        self.errors = errors
        self.warnings = warnings or []
        message = f"Roster validation failed: {', '.join(errors)}"
        user_message = "Your roster does not meet tournament requirements. Please check the errors below."
        super().__init__(message, user_message, context={'errors': errors, 'warnings': warnings})
```

### 4.2 Exception Handling in Views

**Pattern:**
```python
def team_detail(request, slug):
    """Display team profile."""
    try:
        team_identity = TeamService.get_team_identity_by_slug(slug)
        roster = TeamService.get_roster_members(team_identity.team_id)
        
        return render(request, 'organizations/Demo_detailTeam.html', {
            'team': team_identity,
            'roster': roster
        })
        
    except TeamNotFoundError as e:
        logger.warning(f"Team not found: {slug}", extra={'user': request.user.id})
        return render(request, '404.html', {'message': e.user_message}, status=404)
        
    except PermissionDeniedError as e:
        logger.warning(f"Permission denied: {slug}", extra={'user': request.user.id})
        return render(request, '403.html', {'message': e.user_message}, status=403)
        
    except Exception as e:
        logger.error(f"Unexpected error in team_detail: {e}", exc_info=True)
        return render(request, '500.html', {'message': 'An unexpected error occurred.'}, status=500)
```

### 4.3 User-Safe Error Messages

**Rules:**
- ✅ **MUST** show user-friendly messages in UI (no stack traces, no technical jargon).
- ✅ **MUST** log technical details server-side for debugging.
- ❌ **MUST NOT** expose internal system details to users (e.g., table names, query errors).

**Examples:**

| Technical Error | User Message |
|-----------------|--------------|
| `Team.DoesNotExist: Team matching query does not exist` | `"Team not found. It may have been deleted or the link is incorrect."` |
| `IntegrityError: duplicate key value violates unique constraint` | `"A team with this name already exists. Please choose a different name."` |
| `ValidationError: Roster size must be >= 5` | `"Your roster needs at least 5 players to register for this tournament."` |

### 4.4 Logging Standards

**Log Levels:**

| Level | Use Case | Example |
|-------|----------|---------|
| `DEBUG` | Service method entry/exit, query details | `"TeamService.get_team_identity called with team_id=123"` |
| `INFO` | Successful operations, state changes | `"Team 'Protocol V' created by user 456"` |
| `WARNING` | Recoverable errors, deprecated API usage | `"Deprecated field accessed: team.captain (use TeamService.get_managers())"` |
| `ERROR` | Operation failures, validation errors | `"Roster validation failed for team 123: missing Game Passports"` |
| `CRITICAL` | Data corruption, system-wide failures | `"Migration script failed: TeamMigrationMap data loss detected"` |

**Structured Logging:**
```python
import logging

logger = logging.getLogger('organizations.team_service')

class TeamService:
    @staticmethod
    def get_team_identity(team_id: int) -> TeamIdentity:
        logger.debug(f"get_team_identity called", extra={
            'team_id': team_id,
            'service': 'TeamService',
            'method': 'get_team_identity'
        })
        
        try:
            team = Team.objects.select_related('game', 'organization').get(id=team_id)
            logger.info(f"Team identity retrieved", extra={
                'team_id': team_id,
                'team_name': team.name,
                'org_owned': team.organization is not None
            })
            # ... rest of logic
        except Team.DoesNotExist:
            logger.error(f"Team not found", extra={
                'team_id': team_id,
                'requested_by': 'unknown'  # Add user context if available
            })
            raise TeamNotFoundError(f"Team {team_id} does not exist")
```

### 4.5 Audit Logging Policy

**MUST log to `TeamActivityLog` for:**
- Team creation/deletion.
- Roster changes (invite, kick, role change).
- Organization acquisitions.
- Tournament registrations.
- Prize withdrawals.
- Permission changes.

**Format:**
```python
TeamActivityLog.objects.create(
    team=team,
    action_type='ROSTER_ADD',  # Enum value
    actor_id=request.user.id,
    actor_username=request.user.username,
    description=f"Invited {invitee.username} as {role}",
    metadata={
        'invitee_id': invitee.id,
        'role': role,
        'invited_at': timezone.now().isoformat()
    }
)
```

---

## 5. Testing Requirements

### 5.1 Coverage Targets by Phase

| Phase | Minimum Coverage | Focus Areas |
|-------|------------------|-------------|
| **Phase 1** (Foundation) | 80% | Models, service layer |
| **Phase 2** (Integration) | 75% | Service layer + signal handlers |
| **Phase 3** (Core Features) | 70% | Views, forms, service layer |
| **Phase 4** (Ranking) | 80% | RankingService, CP calculations |
| **Phase 5** (Migration) | 90% | MigrationService, data scripts |
| **Phase 6+** (Launch) | 75% overall | Critical paths at 95%+ |

**Critical Paths Requiring 95%+ Coverage:**
- Prize withdrawal flows.
- Tournament registration validation.
- Migration scripts (Phase 5-7).
- Permission checks (all RBAC logic).

### 5.2 Required Test Types

**Unit Tests (Per File):**
- ✅ **MUST** test all service methods with happy path + error cases.
- ✅ **MUST** test all model methods (e.g., `get_absolute_url()`, `can_user_manage()`).
- ✅ **MUST** test all custom validators and form validation logic.

**Integration Tests:**
- ✅ **MUST** test service-to-service interactions (e.g., `RankingService` + `TeamService`).
- ✅ **MUST** test signal emission and handling.
- ✅ **MUST** test database transactions and rollback behavior.

**Functional Tests:**
- ✅ **MUST** test complete user workflows (e.g., team creation → roster invite → tournament registration).
- ✅ **MUST** test permission boundaries (unauthorized access blocked).

**Performance Tests:**
- ✅ **MUST** test query count for key views (fail if >5 queries for detail pages).
- ✅ **MUST** test response time benchmarks (see Section 3.5).

### 5.3 Test Naming & Structure

**Convention:**
```python
# tests/test_services/test_team_service.py

from django.test import TestCase
from apps.organizations.services import TeamService
from apps.organizations.exceptions import TeamNotFoundError


class TeamServiceTestCase(TestCase):
    """Tests for TeamService."""
    
    def setUp(self):
        """Create test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team", game_id=1, owner_id=1)
        self.user = User.objects.create(username="testuser")
    
    def test_get_team_identity_success(self):
        """get_team_identity returns correct identity for valid team."""
        identity = TeamService.get_team_identity(self.team.id)
        
        self.assertEqual(identity.team_id, self.team.id)
        self.assertEqual(identity.name, "Test Team")
        self.assertEqual(identity.slug, "test-team")
        self.assertFalse(identity.is_org_team)
    
    def test_get_team_identity_not_found(self):
        """get_team_identity raises TeamNotFoundError for invalid ID."""
        with self.assertRaises(TeamNotFoundError):
            TeamService.get_team_identity(999999)
    
    def test_get_team_identity_query_count(self):
        """get_team_identity executes at most 3 queries."""
        with self.assertNumQueries(3):
            TeamService.get_team_identity(self.team.id)
```

### 5.4 Fixture Management

**Rules:**
- ✅ **MUST** use Django fixtures or factory_boy for test data.
- ✅ **MUST** keep fixtures minimal (only data needed for test).
- ❌ **MUST NOT** rely on production data dumps (too brittle).

**Example (factory_boy):**
```python
# tests/factories.py
import factory
from apps.organizations.models import Team, Organization

class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization
    
    name = factory.Sequence(lambda n: f"Organization {n}")
    slug = factory.Sequence(lambda n: f"org-{n}")
    ceo = factory.SubFactory('tests.factories.UserFactory')
    is_verified = False


class TeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Team
    
    name = factory.Sequence(lambda n: f"Team {n}")
    slug = factory.Sequence(lambda n: f"team-{n}")
    game = factory.SubFactory('tests.factories.GameFactory')
    owner = factory.SubFactory('tests.factories.UserFactory')
    status = 'ACTIVE'
```

---

## 6. Security Standards

### 6.1 Permission Enforcement

**Mandatory Checks:**
- ✅ **MUST** verify permissions in views BEFORE performing any action.
- ✅ **MUST** use decorators for permission checks (not manual if/else in view body).
- ✅ **MUST** perform object-level permission checks (not just model-level).

**Example:**
```python
from apps.organizations.permissions import require_team_permission

@require_team_permission('edit_roster')
def invite_player(request, team_id):
    """Invite player to team (requires edit_roster permission)."""
    # Permission already verified by decorator
    # View logic here
    pass
```

### 6.2 Object-Level Access Control

**Pattern:**
```python
def team_edit(request, team_id):
    """Edit team details."""
    team = get_object_or_404(Team, id=team_id)
    
    # Object-level check
    if not team.can_user_manage(request.user):
        raise PermissionDenied("You do not have permission to edit this team.")
    
    # Proceed with edit logic
```

### 6.3 CSRF Protection

**Rules:**
- ✅ **MUST** include `{% csrf_token %}` in all forms.
- ✅ **MUST** use `@csrf_protect` decorator for AJAX endpoints accepting POST.
- ❌ **MUST NOT** disable CSRF without security team approval.

### 6.4 Input Validation

**Mandatory:**
- ✅ **MUST** validate all user inputs (never trust client-side validation alone).
- ✅ **MUST** sanitize HTML inputs (use Django's `escape()` or template auto-escaping).
- ✅ **MUST** validate file uploads (type, size, content).

**Example:**
```python
from django.utils.html import escape

def create_team(request):
    """Create new team."""
    name = request.POST.get('name', '').strip()
    
    # Validate length
    if not name or len(name) > 100:
        return JsonResponse({'error': 'Team name must be 1-100 characters'}, status=400)
    
    # Validate characters (alphanumeric + spaces/hyphens only)
    if not re.match(r'^[a-zA-Z0-9 -]+$', name):
        return JsonResponse({'error': 'Team name contains invalid characters'}, status=400)
    
    # Sanitize for storage
    safe_name = escape(name)
    
    # Create team via service
    team = TeamService.create_team(safe_name, ...)
```

### 6.5 Sensitive Data Handling

**Rules:**
- ✅ **MUST** redact sensitive data in logs (emails, tokens, passwords).
- ✅ **MUST** use `select_for_update()` for financial operations (prize withdrawals).
- ❌ **MUST NOT** log plaintext passwords or API keys.

**Example:**
```python
logger.info(f"User login attempt", extra={
    'username': user.username,
    'email': user.email[:3] + '***',  # Redacted
    'ip': request.META.get('REMOTE_ADDR')
})
```

---

## 7. Frontend Architecture

### 7.1 Technology Stack (Non-Negotiable)

**MANDATORY:**
- ✅ **Tailwind CSS** for all styling (utility-first approach).
- ✅ **Vanilla JavaScript** (ES6+) for interactivity.
- ✅ **Django Templates** for server-side rendering.

**FORBIDDEN:**
- ❌ **Custom CSS** (except unavoidable edge cases, must be documented).
- ❌ **jQuery** (use native DOM APIs).
- ❌ **React/Vue/Angular** (not permitted).
- ❌ **Bootstrap/Bulma/Foundation** (Tailwind only).

### 7.2 Tailwind CSS Standards

**Configuration:**
```javascript
// tailwind.config.js
module.exports = {
  content: [
    './templates/**/*.html',
    './static/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        'brand-primary': '#6366f1',  // Indigo
        'brand-secondary': '#8b5cf6', // Purple
        'brand-accent': '#ec4899',   // Pink
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
```

**Usage Rules:**
- ✅ **MUST** use Tailwind utility classes (e.g., `bg-blue-500`, `text-lg`, `rounded-md`).
- ✅ **MUST** extract repeated patterns into components (see Section 7.4).
- ❌ **MUST NOT** write inline styles (`style="..."`) unless absolutely unavoidable.
- ❌ **MUST NOT** create custom CSS classes unless Tailwind cannot express the pattern.

**Acceptable Custom CSS (Rare Cases):**
```css
/* static/css/organizations_vnext.css */

/* Justification: Complex animation not possible with Tailwind utilities */
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 5px rgba(99, 102, 241, 0.5); }
  50% { box-shadow: 0 0 20px rgba(99, 102, 241, 0.8); }
}

.animate-pulse-glow {
  animation: pulse-glow 2s ease-in-out infinite;
}
```

### 7.3 JavaScript Standards

**Module Pattern:**
```javascript
// static/organizations_vnext/js/team-roster.js

/**
 * Team roster management module.
 * Handles drag-and-drop reordering and inline editing.
 */
export class TeamRoster {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.init();
  }
  
  init() {
    if (!this.container) {
      console.warn('TeamRoster container not found');
      return;
    }
    
    this.attachEventListeners();
    this.initDragAndDrop();
  }
  
  attachEventListeners() {
    this.container.addEventListener('click', (e) => {
      if (e.target.matches('.btn-remove-member')) {
        this.handleRemoveMember(e.target.dataset.memberId);
      }
    });
  }
  
  initDragAndDrop() {
    // Drag-and-drop logic using native HTML5 APIs
    const items = this.container.querySelectorAll('.roster-item');
    items.forEach(item => {
      item.draggable = true;
      item.addEventListener('dragstart', this.handleDragStart.bind(this));
      item.addEventListener('dragover', this.handleDragOver.bind(this));
      item.addEventListener('drop', this.handleDrop.bind(this));
    });
  }
  
  handleRemoveMember(memberId) {
    if (!confirm('Remove this member from the roster?')) return;
    
    fetch(`/api/v2/teams/members/${memberId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': this.getCSRFToken(),
        'Content-Type': 'application/json'
      }
    })
    .then(response => {
      if (response.ok) {
        document.querySelector(`[data-member-id="${memberId}"]`).remove();
        this.showNotification('Member removed successfully', 'success');
      } else {
        this.showNotification('Failed to remove member', 'error');
      }
    })
    .catch(error => {
      console.error('Remove member error:', error);
      this.showNotification('An error occurred', 'error');
    });
  }
  
  getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
  }
  
  showNotification(message, type) {
    // Notification logic
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg ${
      type === 'success' ? 'bg-green-500' : 'bg-red-500'
    } text-white`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.remove(), 3000);
  }
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('team-roster-container')) {
    new TeamRoster('team-roster-container');
  }
});
```

**Rules:**
- ✅ **MUST** use ES6 modules (`export`, `import`).
- ✅ **MUST** use modern APIs (`fetch`, `async/await`, `querySelector`).
- ✅ **MUST** handle errors gracefully (show user-friendly messages).
- ❌ **MUST NOT** use jQuery (use native DOM instead).

### 7.4 Component-Based Templates

**Directory Structure:**
```
templates/
├── organizations_vnext/
│   ├── base.html                    # Layout base
│   ├── team_detail.html             # Full page templates
│   ├── organization_detail.html
│   ├── components/                  # Reusable components
│   │   ├── _team_card.html
│   │   ├── _roster_table.html
│   │   ├── _ranking_badge.html
│   │   └── _tournament_card.html
│   └── partials/                    # Partial includes
│       ├── _header.html
│       ├── _footer.html
│       └── _navigation.html
└── layouts/
    └── app.html                     # Global layout
```

**Component Pattern:**
```django
{# templates/organizations_vnext/components/_team_card.html #}
{% comment %}
Reusable team card component.

Required context:
  - team: TeamIdentity dataclass from TeamService.get_team_identity()
  
Optional context:
  - show_roster_count: Boolean (default: False)
  - link_to_profile: Boolean (default: True)
{% endcomment %}

<div class="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6">
  <div class="flex items-center space-x-4">
    {# Team Logo #}
    <img src="{{ team.logo_url }}" 
         alt="{{ team.name }} logo" 
         class="w-16 h-16 rounded-full object-cover">
    
    {# Team Info #}
    <div class="flex-1">
      <h3 class="text-xl font-bold text-gray-900">
        {% if link_to_profile %}
          <a href="{{ team.get_absolute_url }}" class="hover:text-brand-primary">
            {{ team.name }}
          </a>
        {% else %}
          {{ team.name }}
        {% endif %}
      </h3>
      
      <p class="text-sm text-gray-600">
        {{ team.game_name }} • {{ team.region }}
        {% if team.is_verified %}
          <span class="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">
            ✓ Verified
          </span>
        {% endif %}
      </p>
      
      {% if show_roster_count %}
        <p class="text-xs text-gray-500 mt-1">
          {{ team.roster_count }} members
        </p>
      {% endif %}
    </div>
    
    {# Ranking Badge #}
    {% if team.ranking %}
      {% include 'organizations_vnext/components/_ranking_badge.html' with ranking=team.ranking %}
    {% endif %}
  </div>
</div>
```

**Usage:**
```django
{# templates/organizations_vnext/team_list.html #}
{% extends "organizations_vnext/base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
  <h1 class="text-3xl font-bold mb-8">Teams</h1>
  
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    {% for team in teams %}
      {% include 'organizations_vnext/components/_team_card.html' with team=team show_roster_count=True %}
    {% endfor %}
  </div>
</div>
{% endblock %}
```

### 7.5 Responsive Design Standards

**Mobile-First Approach:**
- ✅ **MUST** design for mobile (320px width) first, then scale up.
- ✅ **MUST** test on real devices (not just browser dev tools).
- ✅ **MUST** use Tailwind responsive prefixes (`sm:`, `md:`, `lg:`, `xl:`).

**Breakpoints:**
```
sm: 640px   (Tablet portrait)
md: 768px   (Tablet landscape)
lg: 1024px  (Desktop)
xl: 1280px  (Large desktop)
```

**Example:**
```html
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
  <!-- 1 column on mobile, 2 on tablet, 3 on desktop -->
</div>

<button class="w-full sm:w-auto px-6 py-3">
  <!-- Full width on mobile, auto width on tablet+ -->
</button>
```

### 7.6 Accessibility Checklist

**MUST include:**
- ✅ Semantic HTML (`<header>`, `<nav>`, `<main>`, `<article>`).
- ✅ ARIA labels for icons and interactive elements.
- ✅ Keyboard navigation support (focus styles, tab order).
- ✅ Alt text for images.
- ✅ Sufficient color contrast (WCAG AA minimum: 4.5:1 for text).

**Example:**
```html
<button 
  aria-label="Remove member from roster" 
  class="text-red-600 hover:text-red-800 focus:outline-none focus:ring-2 focus:ring-red-500">
  <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
    <path d="..."/>
  </svg>
</button>
```

### 7.7 Performance Optimization

**Rules:**
- ✅ **MUST** minify and bundle JavaScript in production.
- ✅ **MUST** use lazy loading for images below the fold.
- ✅ **MUST** defer non-critical JavaScript.
- ❌ **MUST NOT** load external libraries (except Tailwind CDN in dev only).

**Example:**
```html
<script type="module" src="{% static 'organizations_vnext/js/team-roster.js' %}" defer></script>

<img src="{{ team.logo_url }}" 
     alt="{{ team.name }}" 
     loading="lazy" 
     class="w-16 h-16">
```

---

## 8. Documentation Requirements

### 8.1 Code Documentation

**Required:**
- ✅ Module-level docstrings explaining purpose.
- ✅ Class-level docstrings explaining responsibility.
- ✅ Method-level docstrings (Google style, see Section 1.3).
- ✅ Inline comments for complex logic (see Section 1.4).

### 8.2 Migration Documentation

**Every migration script MUST include:**
```python
# migrations/0005_migrate_legacy_teams.py

"""
Migration: Transfer legacy teams to vNext system.

Phase: 5 (Week 13-14)
Author: Engineering Team
Date: 2026-01-25

Purpose:
  Migrate all teams from apps/teams to apps/organizations.
  Preserves all data: team identity, roster, rankings, activity history.

Pre-conditions:
  - TeamMigrationMap table exists
  - Service layer deployed (Phase 2)
  - Dependent apps use TeamService (Phase 2)

Post-conditions:
  - All legacy teams have vNext counterparts
  - TeamMigrationMap populated
  - No data loss (verified by validation script)

Rollback:
  - Use management command: python manage.py rollback_team_migration
  - Restores legacy tables to pre-migration state
  - Requires database backup from before migration

Estimated Duration: 30 minutes for 10,000 teams
"""
```

### 8.3 Architecture Decision Records (ADRs)

**Template:**
```markdown
# ADR-XXX: [Decision Title]

**Status:** Accepted | Rejected | Superseded  
**Date:** YYYY-MM-DD  
**Deciders:** [Names]

## Context
[Describe the problem or decision to be made]

## Decision
[Describe the chosen solution]

## Rationale
[Explain why this decision was made]

## Consequences
[Positive and negative impacts]

## Alternatives Considered
[Other options and why they were rejected]
```

### 8.4 README Requirements

**Every app folder MUST have a README.md:**
```markdown
# apps/organizations

Team & Organization Management vNext

## Purpose
Replaces legacy apps/teams with modern architecture supporting Organizations, Teams, and DeltaCrown Ranking System (DCRS).

## Key Features
- Organizations as first-class entities
- Team creation in <30 seconds
- Crown Points ranking system
- Tournament Operations Center

## Service Layer API
See [TEAM_ORG_ARCHITECTURE.md](../../Documents/Team & Organization/Planning Documents/TEAM_ORG_ARCHITECTURE.md)

## Migration Status
- Phase 2: Service layer deployed ✅
- Phase 3: Core features (in progress)
- Phase 5: Data migration (not started)

## Running Tests
```bash
python manage.py test apps.organizations
```

## Dependencies
- apps.games (Game model)
- apps.user_profile (UserProfile model)
- apps.economy (Wallet model)
```

---

## Enforcement & Code Review Checklist

### Pre-Merge Checklist

**Code Quality:**
- [ ] Code follows PEP 8 (Black formatted)
- [ ] All functions have type hints
- [ ] All service methods have docstrings
- [ ] Complex logic has inline comments

**Performance:**
- [ ] No N+1 queries (checked with Django Debug Toolbar)
- [ ] Query count meets benchmarks (see Section 3.5)
- [ ] Large querysets use pagination or `iterator()`

**Testing:**
- [ ] New code has tests (meets phase coverage target)
- [ ] All tests pass
- [ ] Performance tests pass

**Security:**
- [ ] Permission checks in place
- [ ] User inputs validated
- [ ] CSRF protection enabled
- [ ] Audit logging added for sensitive actions

**Frontend:**
- [ ] Uses Tailwind CSS only (no custom CSS unless justified)
- [ ] Uses Vanilla JS (no jQuery)
- [ ] Mobile-responsive
- [ ] Accessibility checklist completed

**Documentation:**
- [ ] README updated if new app/module
- [ ] Migration script documented if applicable
- [ ] ADR created for significant decisions

---

## Appendix: Tool Configuration

### Black (Code Formatter)
```toml
# pyproject.toml
[tool.black]
line-length = 120
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
/(
  migrations
  | \.git
  | \.venv
)/
'''
```

### Flake8 (Linter)
```ini
# .flake8
[flake8]
max-line-length = 120
exclude = .git,__pycache__,migrations,venv
ignore = E203,W503
per-file-ignores =
    __init__.py:F401
```

### Pylint (Advanced Linter)
```ini
# .pylintrc
[MASTER]
ignore=migrations,venv

[FORMAT]
max-line-length=120

[MESSAGES CONTROL]
disable=C0111,R0903
```

---

**END OF ENGINEERING STANDARDS**
