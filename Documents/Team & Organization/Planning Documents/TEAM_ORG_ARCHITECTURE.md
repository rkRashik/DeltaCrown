# 🏗️ Team & Organization System vNext — Architecture Specification

**Document Version:** 1.3 ⚠️ **CORRECTED ARCHITECTURE**  
**Effective Date:** January 31, 2026  
**Owner:** Engineering Architecture Team  
**Status:** Implementation Blueprint  
**Parent Documents:**  
- [TEAM_ORG_VNEXT_MASTER_PLAN.md](./TEAM_ORG_VNEXT_MASTER_PLAN.md) v1.3
- [PLANNING_REALIGNMENT_SUMMARY.md](./PLANNING_REALIGNMENT_SUMMARY.md) ⚠️ **PHASE 8 CORRECTION**
- [TEAM_ORG_COMPATIBILITY_CONTRACT.md](./TEAM_ORG_COMPATIBILITY_CONTRACT.md)  
- [TEAM_ORG_ENGINEERING_STANDARDS.md](./TEAM_ORG_ENGINEERING_STANDARDS.md) ⚠️ **MANDATORY COMPLIANCE**
- [TEAM_ORG_PERFORMANCE_CONTRACT.md](./TEAM_ORG_PERFORMANCE_CONTRACT.md) ⚠️ **BINDING REQUIREMENTS**

**Changelog:**
- v1.3 (Jan 31, 2026): **CRITICAL CORRECTION** - Removed org-mandatory constraints, added dual ownership architecture (Phase 8 realignment)
- v1.2 (Jan 25, 2026): Added Database Strategy Hard Rules (SUPERSEDED by v1.3 corrections)
- v1.1 (Jan 25, 2026): Added Engineering Standards & Frontend Architecture section, updated module structure for Tailwind + Vanilla JS, added frontend directory conventions
- v1.0 (Jan 25, 2026): Initial architecture specification

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Database Strategy (Hard Rules)](#2-database-strategy-hard-rules)
3. [Engineering Standards & Frontend Architecture](#3-engineering-standards--frontend-architecture)
4. [App & Module Structure](#4-app--module-structure)
5. [Core Data Models](#5-core-data-models)
6. [Service Layer Design](#6-service-layer-design)
7. [Permissions & RBAC Enforcement](#7-permissions--rbac-enforcement)
8. [Signals & Events](#8-signals--events)
9. [Feature Flags & Configuration](#9-feature-flags--configuration)
10. [Error Handling & Logging](#10-error-handling--logging)

---

## 1. Architecture Overview

### 1.1 System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DELTACROWN PLATFORM                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌───────────────────┐         ┌──────────────────────────────────┐    │
│  │  Legacy System    │         │    vNext System (NEW)             │    │
│  │ apps/teams        │◄────────┤  apps/organizations               │    │
│  │                   │  Phase  │                                   │    │
│  │ - Team (legacy)   │  5-7    │ - Organization                    │    │
│  │ - TeamMembership  │  Dual   │ - Team (vNext)                    │    │
│  │ - TeamGameRanking │  Read   │ - TeamMembership (vNext)          │    │
│  │                   │         │ - TeamRanking                     │    │
│  │ Status: READ-ONLY │         │ - OrganizationRanking             │    │
│  │ (Phase 2+)        │         │ - TeamMigrationMap                │    │
│  └───────────────────┘         │ - TeamActivityLog                 │    │
│           │                     └──────────────────────────────────┘    │
│           │                                      │                       │
│           └──────────────────┬───────────────────┘                       │
│                              │                                           │
│                   ┌──────────▼──────────┐                               │
│                   │   Service Layer      │                               │
│                   │  TeamService         │◄───────────────┐              │
│                   │  OrganizationService │                │              │
│                   │  RankingService      │                │              │
│                   └──────────┬───────────┘                │              │
│                              │                            │              │
│         ┌────────────────────┼────────────────────┐       │              │
│         │                    │                    │       │              │
│    ┌────▼────┐          ┌───▼────┐         ┌────▼────┐  │              │
│    │Tournament│          │ User    │         │Leaderboard│              │
│    │  App     │          │ Profile │         │  App     │  │              │
│    │          │          │   App   │         │          │  │              │
│    │ - Register│         │ - History│        │ - Rank   │  │              │
│    │ - Validate│         │ - Display│        │ - Display │ │              │
│    └──────────┘          └─────────┘         └──────────┘  │              │
│         │                     │                    │        │              │
│    ┌────▼────┐          ┌────▼────┐         ┌─────▼─────┐ │              │
│    │Notification│        │Tournament│        │  Economy  │ │              │
│    │  App      │        │   Ops    │        │    App    │ │              │
│    │           │        │   App    │        │           │ │              │
│    │ - Invites │        │ - Dashboard│       │ - Payouts │ │              │
│    │ - Roster  │        │ - TOC    │        │ - Wallet  │ │              │
│    └───────────┘        └──────────┘        └───────────┘ │              │
│                                                             │              │
│                     DEPENDENT APPS                          │              │
│                     (DECOUPLED VIA SERVICE LAYER)           │              │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Architectural Principles

**Strangler Fig Migration Pattern:**
- Build `apps/organizations` alongside `apps/teams` (parallel systems).
- Service layer routes requests to correct system based on migration state.
- Gradual cutover: Phase 2 (service layer) → Phase 5 (data migration) → Phase 8 (legacy archive).

**Service-Oriented Decoupling:**
- Dependent apps (`tournaments`, `notifications`, etc.) NEVER import models directly.
- All access mediated through `TeamService`, `OrganizationService`, `RankingService`.
- Enables swapping underlying implementation without breaking consumers.

**Database Independence:**
- Legacy tables (`teams_team`, `teams_membership`) remain untouched until Phase 8.
- vNext tables (`organizations_organization`, `organizations_team`) use proper FK relationships.
- `TeamMigrationMap` bridges legacy and vNext IDs during transition (Phase 5-7).

**Zero-Downtime Deployment:**
- Feature flags control vNext feature visibility.
- Dual-write strategy (Phase 5-7) maintains data consistency across both systems.
- URL redirects preserve old notification links indefinitely.

### 1.3 Migration Phases & System State

| Phase | Weeks | Legacy State | vNext State | Service Layer Behavior |
|-------|-------|--------------|-------------|------------------------|
| **1** | 1-4   | READ-WRITE   | NOT DEPLOYED | N/A (Service Layer being built) |
| **2** | 5-6   | READ-WRITE   | NOT DEPLOYED | All calls route to legacy |
| **3** | 7-10  | READ-ONLY    | WRITE-PRIMARY (new teams) | New teams → vNext, Legacy teams → Legacy |
| **4** | 11-12 | READ-ONLY    | WRITE-PRIMARY | Same as Phase 3 |
| **5** | 13-14 | READ-ONLY (dual-write) | WRITE-PRIMARY (all teams) | Check `TeamMigrationMap` for routing |
| **6** | 15    | READ-ONLY (dual-write) | WRITE-PRIMARY | Same as Phase 5 + URL redirects active |
| **7** | 16+   | READ-ONLY (dual-write) | WRITE-PRIMARY | Same as Phase 6 + monitoring period |
| **8** | 17-20 | ARCHIVED     | SOLE SYSTEM | All calls route to vNext only |

### 1.4 Data Flow: Tournament Registration Example

**Phase 3+ Flow (New Team Registration):**
```
1. User clicks "Register Team" in tournament UI
      ↓
2. tournaments/views.py calls TeamService.validate_roster(team_id, tournament_id)
      ↓
3. TeamService checks TeamMigrationMap:
   - If mapping exists → Query organizations.Team
   - If no mapping → Query teams.Team (legacy)
      ↓
4. Service validates:
   - Roster size meets requirements
   - Game Passports valid
   - No overlapping tournament locks
      ↓
5. Returns ValidationResult(is_valid=True, errors=[], warnings=[])
      ↓
6. tournaments/views.py proceeds with registration
      ↓
7. On success, emit signal: tournament_registration_confirmed
      ↓
8. notifications/signals.py receives signal
      ↓
9. Calls TeamService.get_team_url(team_id) for notification link
      ↓
10. Sends email with correct URL (legacy or vNext format)
```

---

## 2. Database Strategy (Core Principles)

⚠️ **CORRECTED v1.3**: This section was updated to reflect **teams-first, organizations-optional** architecture per Phase 8 correction.

### 2.1 ARCHITECTURAL FOUNDATION: Dual Ownership Model

**THE REALITY:**

Teams can exist in **two modes**:

1. **Independent Teams** (90% of use cases):
   - **Database**: `Team.organization = NULL`
   - **Ownership**: User is Owner + Manager (`created_by` field)
   - **Constraints**: ONE per game per user (WHERE status=ACTIVE AND organization IS NULL)
   - **URL**: `/teams/<slug>/` (canonical)
   - **Wallet**: Personal (100% prize money)

2. **Organization Teams** (10% of use cases):
   - **Database**: `Team.organization = FK(Organization)`
   - **Ownership**: Organization is Owner, User is Manager (via TeamMembership)
   - **Constraints**: MULTIPLE per game allowed (Academy divisions)
   - **URL**: `/orgs/<org_slug>/teams/<team_slug>/` (canonical)
   - **Wallet**: Master Wallet (smart splits)

**Schema Implementation:**

```python
class Team(models.Model):
    """
    Competitive unit that participates in tournaments.
    Can be independent (user-owned) OR org-owned.
    """
    # Identity
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    game_id = models.IntegerField()  # FK to Game
    
    # CRITICAL: Dual ownership model
    organization = models.ForeignKey(
        'Organization',
        null=True,        # ← NULLABLE (independent teams have NULL)
        blank=True,
        on_delete=models.SET_NULL,
        related_name='teams'
    )
    created_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,  # Creator preserved
        related_name='created_teams'
    )
    
    # Status
    status = models.CharField(choices=Status.choices, default='ACTIVE')
    
    class Meta:
        constraints = [
            # Independent teams: ONE per game per user
            models.UniqueConstraint(
                fields=['created_by', 'game_id'],
                condition=models.Q(status='ACTIVE') & models.Q(organization__isnull=True),
                name='one_independent_team_per_game'
            ),
        ]
```

**Why This Architecture:**
- **Business Reality**: 90% of users are casual players (independent teams)
- **Platform Narrative**: "Grassroots to Glory" requires independent team support
- **Natural Progression**: Independent team → Build reputation → Get acquired by org
- **No Artificial Complexity**: Avoid fake "hidden orgs" for casual players

---

### 2.2 DATABASE SEPARATION: NEW TABLES REQUIRED

**MUST:**
- `apps/organizations` (vNext) uses **COMPLETELY NEW** database tables with `organizations_*` prefix
- All vNext models define `db_table = 'organizations_*'` in `Meta` class
- Zero dependencies on legacy `teams_*` table structure

**MUST NOT:**
- Import models from `apps/teams` into vNext code
- Reference legacy tables in vNext migrations
- Assume legacy table structure or column names

**Table Naming Convention:**

| vNext Model | Database Table Name | Legacy Equivalent |
|------------|---------------------|-------------------|
| `Organization` | `organizations_organization` | N/A (new concept) |
| `Team` | `organizations_team` | `teams_team` |
| `TeamMembership` | `organizations_membership` | `teams_membership` |
| `TeamRanking` | `organizations_ranking` | `teams_teamgameranking` |
| `OrganizationMembership` | `organizations_org_membership` | N/A (new concept) |
| `TeamMigrationMap` | `organizations_migration_map` | N/A (bridge table) |

**Why This Rule Exists:**
- Prevents accidental legacy table modification during development
- Enables independent schema evolution for vNext system
- Allows legacy system to remain frozen (READ-ONLY after Phase 2)
- Simplifies rollback (just drop `organizations_*` tables)

---

#### **HARD RULE 2: LEGACY TABLES MUST NOT BE ALTERED**

**MUST NOT during Phase 1-4:**
- Add new columns to `teams_team`, `teams_membership`, `teams_invite`, or `teams_teamgameranking`
- Modify existing column types or constraints on legacy tables
- Create new foreign keys pointing to legacy tables from vNext tables
- Drop or rename legacy columns (even if unused)

**EXCEPTION (Phase 5-7 ONLY):**
- Read-only data migration queries permitted (`SELECT` statements)
- `TeamMigrationMap` FK to legacy `teams_team.id` (bridge only)
- Dual-write inserts to legacy tables (Phase 5-7 compatibility shim)

**Enforcement:**
- Code review MUST reject any migration touching legacy tables
- CI pipeline runs `python manage.py check --deploy` to detect schema changes
- Database migration linter rejects migrations for `apps/teams`

**Why This Rule Exists:**
- Legacy system MUST remain stable (used by 100+ active tournaments)
- Any legacy table change requires testing 15+ dependent apps
- Phase 2+ makes legacy READ-ONLY (new columns would never be populated)
- Rollback impossible if legacy schema modified

---

#### **HARD RULE 3: LEGACY BECOMES READ-ONLY AFTER PHASE 2**

**Phase 2+ Behavior:**

**MUST:**
- All new team creations write to `organizations_team` (vNext)
- Legacy `teams_team` table receives **ZERO new inserts**
- Read queries to legacy permitted via service layer routing

**MUST NOT:**
- Insert new rows into `teams_team`, `teams_membership`, `teams_invite`
- Update existing legacy rows (except Phase 5-7 dual-write sync)
- Delete legacy rows before Phase 8

**Service Layer Routing (Phase 3-7):**

```python
# TeamService.create_team() - CORRECT
def create_team(name: str, game_id: int, owner_id: int) -> TeamDTO:
    """Create team in vNext system (Phase 3+)."""
    # MUST write to organizations_team (NEW)
    team = Team.objects.create(
        name=name,
        game_id=game_id,
        owner_id=owner_id
    )
    
    # MUST NOT write to legacy teams_team
    
    return TeamDTO.from_orm(team)
```

**Why This Rule Exists:**
- Prevents data fragmentation (some teams in legacy, some in vNext)
- Simplifies migration (all new data already in vNext)
- Reduces testing burden (legacy code frozen, no regression risk)

---

#### **HARD RULE 4: TEAMMIGRATIONMAP IS THE ONLY BRIDGE**

**Purpose:** Map legacy team IDs to vNext team IDs during Phase 5-7 dual-read period.

**Structure:**

```python
class TeamMigrationMap(models.Model):
    """Bridge table mapping legacy Team IDs to vNext Team IDs."""
    
    legacy_team_id = models.IntegerField(
        unique=True,
        help_text="Original teams_team.id"
    )
    vnext_team_id = models.ForeignKey(
        'Team',
        on_delete=models.CASCADE,
        help_text="New organizations_team.id"
    )
    migration_date = models.DateTimeField(auto_now_add=True)
    migrated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'organizations_migration_map'
```

**MUST:**
- Use `TeamMigrationMap` to route service layer calls during Phase 5-7
- Retain `TeamMigrationMap` **indefinitely** (minimum 12 months post-migration)
- Query this table to preserve URL redirects (legacy `/teams/{slug}/` → vNext URL)

**MUST NOT:**
- Create direct FKs between vNext models and legacy models
- Bypass `TeamMigrationMap` during dual-read phase (data corruption risk)
- Delete `TeamMigrationMap` rows (breaks old notification links)

**Service Layer Usage (Phase 5-7):**

```python
# CORRECT: Use migration map to route reads
def get_team_by_id(team_id: int) -> TeamDTO:
    """Get team from correct system (legacy or vNext)."""
    
    # Check if legacy team was migrated
    migration = TeamMigrationMap.objects.filter(
        legacy_team_id=team_id
    ).first()
    
    if migration:
        # Team migrated: Fetch from vNext
        team = Team.objects.get(id=migration.vnext_team_id)
    else:
        # Check if vNext-native team
        team = Team.objects.filter(id=team_id).first()
        if not team:
            # Fallback to legacy
            legacy_team = LegacyTeam.objects.get(id=team_id)
            team = adapt_legacy_team(legacy_team)
    
    return TeamDTO.from_orm(team)
```

**Why This Rule Exists:**
- Enables gradual migration without breaking existing tournament registrations
- Preserves referential integrity during dual-system phase
- Provides audit trail for migration debugging

---

### 2.2 Database Schema Separation Checklist

**Before writing ANY production code, verify:**

- [ ] All vNext models use `db_table = 'organizations_*'` naming
- [ ] No imports from `apps.teams.models` in vNext code
- [ ] No FKs from vNext models to legacy models (except `TeamMigrationMap`)
- [ ] No migrations created for `apps/teams` after Phase 2 start
- [ ] Service layer routes writes to vNext, reads to both (Phase 3+)
- [ ] `TeamMigrationMap` created and tested (Phase 5)
- [ ] Legacy tables have zero new inserts after Phase 2 deployment
- [ ] Code review checklist includes legacy table modification check

---

### 2.3 Violation Consequences

**If these database rules are violated:**

1. **Code Review:** Changes rejected immediately (no exceptions)
2. **CI Pipeline:** Build fails, cannot merge to main branch
3. **Production:** Rollback triggered, incident post-mortem required
4. **Technical Debt:** Emergency cleanup sprint to fix schema pollution

**Enforcement Authority:** Technical Lead has final say on schema changes (no exceptions).

---

## 3. Engineering Standards & Frontend Architecture

### 3.1 Mandatory Compliance

**⚠️ ALL code MUST comply with:**
- [TEAM_ORG_ENGINEERING_STANDARDS.md](./TEAM_ORG_ENGINEERING_STANDARDS.md) - Code quality & architecture
- [TEAM_ORG_PERFORMANCE_CONTRACT.md](./TEAM_ORG_PERFORMANCE_CONTRACT.md) - Performance requirements

This section summarizes key architectural constraints. For detailed rules, see the referenced documents.

### 3.2 Technology Stack (Non-Negotiable)

**Backend:**
- ✅ Python 3.10+
- ✅ Django 4.2+
- ✅ PostgreSQL (no SQLite in production)
- ✅ Service-oriented architecture (thin views, fat services)

**Frontend (MANDATORY):**
- ✅ **Tailwind CSS** for ALL styling (utility-first approach)
- ✅ **Vanilla JavaScript (ES6+)** for interactivity
- ✅ Django templates for server-side rendering
- ❌ **NO custom CSS** (except unavoidable edge cases with documentation)
- ❌ **NO jQuery, React, Vue, Angular**
- ❌ **NO Bootstrap, Bulma, Foundation**

### 3.3 Architecture Principles

**Clean, Modern, Future-Proof:**
- No messy shortcuts or technical debt.
- Prefer minimal, reusable patterns over verbose boilerplate.
- Every file MUST be well-commented (especially services, queries, migrations).

**Service Layer Boundaries:**
```
HTTP Layer (Views)  →  Service Layer (Business Logic)  →  Data Layer (Models)
      ↓                        ↓                                ↓
  Thin views           Stateless services              Simple model methods
  Handle I/O          Transaction management           Data validation only
  Render templates    Permission checks                No complex logic
```

**Performance-First:**
- All queries MUST use `select_related()`/`prefetch_related()` to prevent N+1.
- List views MUST be paginated (50 items max).
- Service methods MUST complete in <100ms (95th percentile).
- Detail pages MUST load in <200ms with ≤5 queries.

### 3.4 Frontend Architecture

**Component-Based Templates:**
```
templates/organizations_vnext/
  ├── base.html                    # Layout base with Tailwind CDN
  ├── team_detail.html             # Full page templates
  ├── organization_detail.html
  ├── components/                  # Reusable UI components
  │   ├── _team_card.html
  │   ├── _roster_table.html
  │   ├── _ranking_badge.html
  │   └── _tournament_card.html
  └── partials/                    # Partial includes
      ├── _header.html
      ├── _footer.html
      └── _navigation.html
```

**JavaScript Module Pattern:**
```
static/organizations_vnext/
  ├── js/
  │   ├── team-roster.js           # ES6 module for roster management
  │   ├── team-create.js           # Team creation flow
  │   ├── ranking-live-update.js   # Live ranking updates
  │   └── utils/
  │       ├── api-client.js        # Fetch wrapper with CSRF
  │       └── notifications.js     # Toast notifications
  └── css/
      └── organizations_vnext.css  # ONLY for unavoidable custom CSS (rare)
```

**Tailwind Build Process:**
```bash
# Development: Watch mode
npx tailwindcss -i ./static/css/tailwind_input.css -o ./static/css/tailwind_output.css --watch

# Production: Minified
npx tailwindcss -i ./static/css/tailwind_input.css -o ./static/css/tailwind_output.css --minify
```

**Page Rendering Flow:**
1. Django view calls service layer (e.g., `TeamService.get_team_identity()`).
2. Service returns dataclass/dict with data.
3. View passes data to template context.
4. Template uses Tailwind utilities for styling.
5. Vanilla JS modules add interactivity (drag-and-drop, live updates).
6. NO inline styles, NO jQuery, NO framework overhead.

### 3.5 Quality Gates

**Pre-Deployment Checklist:**
- [ ] Code passes Black formatter (120 char line length)
- [ ] No N+1 queries (verified with Django Debug Toolbar)
- [ ] Service methods have Google-style docstrings
- [ ] Test coverage meets phase target (see Engineering Standards)
- [ ] Mobile-responsive (tested on 320px width)
- [ ] Accessibility: ARIA labels, keyboard navigation, color contrast
- [ ] Performance: Page load <200ms, ≤5 queries for detail views

---

## 4. App & Module Structure

### 4.1 Directory Tree

```
apps/organizations/
├── __init__.py
├── apps.py                          # Django app config
├── admin.py                         # Django admin registration (see 2.5)
├── urls.py                          # URL routing (see 2.6)
├── views.py                         # HTTP views (reserved for future use)
│
├── models/                          # Data models (see Section 3)
│   ├── __init__.py                 # Export public models
│   ├── organization.py             # Organization model
│   ├── team.py                     # Team model
│   ├── membership.py               # TeamMembership model
│   ├── ranking.py                  # TeamRanking, OrganizationRanking
│   ├── migration.py                # TeamMigrationMap
│   ├── activity.py                 # TeamActivityLog
│   └── choices.py                  # Enum definitions (Status, Role, Tier)
│
├── services/                        # Business logic layer (see Section 4)
│   ├── __init__.py                 # Export public services
│   ├── team_service.py             # TeamService (primary interface)
│   ├── organization_service.py     # OrganizationService
│   ├── ranking_service.py          # RankingService
│   ├── migration_service.py        # MigrationService (Phase 5-7)
│   └── validators.py               # Shared validation logic
│
├── signals/                         # Event emitters (see Section 6)
│   ├── __init__.py
│   ├── handlers.py                 # Signal receivers
│   └── emitters.py                 # Signal dispatchers
│
├── api/                             # REST API (future)
│   ├── __init__.py
│   ├── serializers.py              # DRF serializers
│   ├── views.py                    # API views
│   └── permissions.py              # API permission classes
│
├── permissions/                     # RBAC enforcement (see Section 5)
│   ├── __init__.py
│   ├── decorators.py               # @require_team_permission
│   ├── checkers.py                 # Permission evaluation logic
│   └── rules.py                    # Permission matrix definitions
│
├── forms/                           # Django forms (MINIMAL use, prefer service layer)
│   ├── __init__.py
│   ├── organization.py             # Org create/edit (rendered with Tailwind)
│   ├── team.py                     # Team create/edit (rendered with Tailwind)
│   └── membership.py               # Roster invite (rendered with Tailwind)
│   # NOTE: Forms exist for validation only. UI built with Tailwind components.
│
├── templates/                       # HTML templates
│   └── organizations_vnext/        # vNext-specific templates
│       ├── base.html               # Base layout with Tailwind
│       ├── team_detail.html        # Team profile page
│       ├── team_create.html        # Team creation flow
│       ├── organization_detail.html # Org profile page
│       ├── components/             # Reusable Tailwind components
│       │   ├── _team_card.html
│       │   ├── _roster_table.html
│       │   ├── _ranking_badge.html
│       │   └── _tournament_card.html
│       └── partials/               # Partial includes
│           ├── _header.html
│           ├── _footer.html
│           └── _navigation.html
│
├── static/                          # Static assets
│   └── organizations_vnext/
│       ├── js/                     # Vanilla JS modules (ES6+)
│       │   ├── team-roster.js
│       │   ├── team-create.js
│       │   ├── ranking-live-update.js
│       │   └── utils/
│       │       ├── api-client.js   # Fetch wrapper
│       │       └── notifications.js # Toast system
│       └── css/
│           └── organizations_vnext.css  # Custom CSS (RARE, document why)
│
├── migrations/                      # Database migrations
│   └── 0001_initial.py             # Initial schema (generated)
│
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── test_models.py              # Model unit tests
│   ├── test_services.py            # Service layer tests
│   ├── test_signals.py             # Signal emission tests
│   ├── test_permissions.py         # RBAC tests
│   ├── test_migration.py           # Migration script tests
│   └── fixtures/                   # Test data
│       ├── teams.json
│       └── organizations.json
│
└── management/                      # Django management commands
    └── commands/
        ├── migrate_legacy_teams.py # Phase 5 migration script
        ├── reconcile_dual_write.py # Nightly consistency check
        └── backfill_rankings.py    # Initialize ranking data
```

### 4.2 Naming Conventions

**Model Classes:**
- Use singular nouns: `Organization`, `Team`, `TeamMembership`.
- Suffix model-specific enums: `Team.Status`, `TeamMembership.Role`.
- Use descriptive FK names: `organization` (not `org`), `captain_profile` (not `captain`).

**Service Classes:**
- Suffix with `Service`: `TeamService`, `OrganizationService`.
- Use verb-noun method names: `get_team_identity()`, `validate_roster()`, `create_organization()`.
- Prefix internal helpers with `_`: `_get_team_from_either_system()`, `_is_legacy_team()`.

**Signal Names:**
- Use past tense for events: `team_created`, `roster_updated`, `ranking_changed`.
- Prefix with entity: `team_created` (not `created_team`).
- Include context in payload: `team_invite_accepted` (not just `invite_accepted`).

**Database Tables:**
- Django auto-generated: `organizations_team`, `organizations_membership`.
- Migration map: `organizations_teammigrationmap` (explicitly named).
- Activity log: `organizations_teamactivitylog`.

**URL Patterns:**
- Organization teams: `/orgs/<org_slug>/teams/<team_slug>/`
- Independent teams: `/teams/<slug>/` (legacy-compatible redirect).
- API endpoints: `/api/v2/organizations/`, `/api/v2/teams/`.

### 4.3 Import Guidelines

**Public API (external apps):**
```python
# ALLOWED:
from apps.organizations.services import TeamService, OrganizationService, RankingService
from apps.organizations.permissions import require_team_permission

# FORBIDDEN (breaks encapsulation):
from apps.organizations.models import Team, Organization
```

**Internal API (within organizations app):**
```python
# ALLOWED:
from .models import Team, Organization, TeamMembership
from .services.team_service import TeamService
from .permissions.checkers import can_manage_team
```

### 4.4 Configuration Files

**apps/organizations/apps.py:**
```python
from django.apps import AppConfig

class OrganizationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.organizations'
    verbose_name = 'Team & Organization Management'
    
    def ready(self):
        """Import signal handlers when app is ready."""
        import apps.organizations.signals.handlers  # noqa: F401
```

**apps/organizations/__init__.py:**
```python
"""
Team & Organization Management vNext

This app replaces the legacy apps/teams system.
External apps should ONLY import from services/ module.
"""

default_app_config = 'apps.organizations.apps.OrganizationsConfig'

# Public API exports
from .services import TeamService, OrganizationService, RankingService
from .permissions import require_team_permission, require_org_permission

__all__ = [
    'TeamService',
    'OrganizationService',
    'RankingService',
    'require_team_permission',
    'require_org_permission',
]
```

### 4.5 Django Admin Registration

**apps/organizations/admin.py:**
```python
from django.contrib import admin
from django.utils.html import format_html
from .models import Organization, Team, TeamMembership, TeamRanking

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'ceo', 'is_verified', 'team_count', 'empire_score', 'created_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('name', 'slug', 'ceo__username')
    readonly_fields = ('slug', 'created_at', 'updated_at', 'empire_score_display')
    
    fieldsets = (
        ('Identity', {
            'fields': ('name', 'slug', 'logo', 'badge', 'description')
        }),
        ('Ownership', {
            'fields': ('ceo', 'is_verified', 'verification_date')
        }),
        ('Financial', {
            'fields': ('master_wallet', 'revenue_split_config')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def team_count(self, obj):
        return obj.teams.filter(status='ACTIVE').count()
    team_count.short_description = 'Active Teams'
    
    def empire_score_display(self, obj):
        ranking = obj.ranking if hasattr(obj, 'ranking') else None
        if ranking:
            return f"{ranking.empire_score:,} CP (Rank #{ranking.global_rank})"
        return "Not Ranked"
    empire_score_display.short_description = 'Empire Score'


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'game', 'organization_link', 'owner_link', 'status', 'region', 'cp_display', 'created_at')
    list_filter = ('status', 'game', 'region', 'organization__isnull')
    search_fields = ('name', 'slug', 'organization__name', 'owner__username')
    readonly_fields = ('slug', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Identity', {
            'fields': ('name', 'slug', 'logo', 'banner', 'game', 'region')
        }),
        ('Ownership', {
            'fields': ('organization', 'owner', 'status')
        }),
        ('Tournament Operations', {
            'fields': ('preferred_server', 'emergency_contact_discord', 'emergency_contact_phone'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('is_temporary', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def organization_link(self, obj):
        if obj.organization:
            url = f"/admin/organizations/organization/{obj.organization.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.organization.name)
        return "Independent"
    organization_link.short_description = 'Organization'
    
    def owner_link(self, obj):
        if obj.owner:
            url = f"/admin/auth/user/{obj.owner.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.owner.username)
        return "N/A (Org-owned)"
    owner_link.short_description = 'Owner'
    
    def cp_display(self, obj):
        ranking = obj.ranking if hasattr(obj, 'ranking') else None
        if ranking:
            return f"{ranking.current_cp:,} CP ({ranking.tier})"
        return "0 CP"
    cp_display.short_description = 'Ranking'


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ('profile', 'team', 'role', 'roster_slot', 'status', 'is_tournament_captain', 'joined_at')
    list_filter = ('status', 'role', 'roster_slot', 'is_tournament_captain')
    search_fields = ('profile__username', 'team__name')
    readonly_fields = ('joined_at', 'left_at')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('team', 'profile', 'status')
        }),
        ('Roles', {
            'fields': ('role', 'roster_slot', 'player_role', 'is_tournament_captain')
        }),
        ('Dates', {
            'fields': ('joined_at', 'left_at', 'left_reason'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TeamRanking)
class TeamRankingAdmin(admin.ModelAdmin):
    list_display = ('team', 'current_cp', 'tier', 'global_rank', 'regional_rank', 'hot_streak_display', 'last_activity')
    list_filter = ('tier', 'is_hot_streak')
    search_fields = ('team__name',)
    readonly_fields = ('global_rank', 'regional_rank', 'last_decay_applied')
    
    fieldsets = (
        ('Crown Points', {
            'fields': ('current_cp', 'season_cp', 'all_time_cp', 'tier')
        }),
        ('Rankings', {
            'fields': ('global_rank', 'regional_rank', 'rank_change_24h', 'rank_change_7d')
        }),
        ('Streaks', {
            'fields': ('is_hot_streak', 'streak_count')
        }),
        ('Maintenance', {
            'fields': ('last_activity_date', 'last_decay_applied'),
            'classes': ('collapse',)
        }),
    )
    
    def hot_streak_display(self, obj):
        if obj.is_hot_streak:
            return format_html('🔥 {} wins', obj.streak_count)
        return "—"
    hot_streak_display.short_description = 'Streak'
```

### 4.6 URL Routing

**apps/organizations/urls.py:**
```python
from django.urls import path, include
from . import views

app_name = 'organizations'

urlpatterns = [
    # Organization routes
    path('orgs/', views.organization_list, name='organization_list'),
    path('orgs/create/', views.organization_create, name='organization_create'),
    path('orgs/<slug:org_slug>/', views.organization_detail, name='organization_detail'),
    path('orgs/<slug:org_slug>/edit/', views.organization_edit, name='organization_edit'),
    
    # Organization team routes
    path('orgs/<slug:org_slug>/teams/', views.org_team_list, name='org_team_list'),
    path('orgs/<slug:org_slug>/teams/create/', views.org_team_create, name='org_team_create'),
    path('orgs/<slug:org_slug>/teams/<slug:team_slug>/', views.team_detail, name='org_team_detail'),
    path('orgs/<slug:org_slug>/teams/<slug:team_slug>/edit/', views.team_edit, name='org_team_edit'),
    path('orgs/<slug:org_slug>/teams/<slug:team_slug>/roster/', views.team_roster, name='org_team_roster'),
    
    # Independent team routes (legacy-compatible)
    path('teams/<slug:slug>/', views.team_detail, name='team_detail'),
    path('teams/<slug:slug>/edit/', views.team_edit, name='team_edit'),
    path('teams/<slug:slug>/roster/', views.team_roster, name='team_roster'),
    
    # API routes (future)
    path('api/v2/', include('apps.organizations.api.urls', namespace='api')),
]
```

**Root URL redirect shim (deltacrown/urls.py):**
```python
from django.urls import path
from apps.organizations.services import MigrationService

def legacy_team_redirect(request, slug):
    """Redirect legacy /teams/{slug}/ URLs to correct vNext URL."""
    team_url = MigrationService.resolve_legacy_url(slug)
    return redirect(team_url)

urlpatterns = [
    # vNext routes
    path('', include('apps.organizations.urls')),
    
    # Legacy redirect (Phase 6+)
    path('teams/<slug:slug>/', legacy_team_redirect, name='legacy_team_redirect'),
    
    # Other app routes...
]
```

---

## 5. Core Data Models

### 5.1 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA MODEL STRUCTURE                             │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐                    ┌──────────────────┐
    │   Organization   │                    │   User/Profile   │
    │                  │                    │                  │
    │ PK: id           │                    │ PK: id           │
    │     name         │                    │     username     │
    │     slug         │◄──┐                │     email        │
    │ FK: ceo ──────────┐  │                └────────┬─────────┘
    │     is_verified  │  │                         │
    │     logo         │  │                         │ owner (nullable)
    │     badge        │  │                         │
    └──────────────────┘  │                ┌────────▼─────────┐
            │             │                │      Team        │
            │ organization│                │                  │
            │ (nullable)  │                │ PK: id           │
            │             │                │     name         │
            │             └────────────────┤     slug         │
            │                              │ FK: organization │
            │                              │ FK: owner (null) │
            │                              │ FK: game         │
            │                              │     region       │
            │                              │     status       │
            │                              │     logo         │
            │                              └────────┬─────────┘
            │                                       │
            │                              ┌────────┴─────────┬──────────────┐
            │                              │                  │              │
    ┌───────▼──────────┐        ┌─────────▼──────────┐  ┌───▼──────────┐   │
    │OrganizationRanking│        │  TeamMembership    │  │ TeamRanking  │   │
    │                  │        │                    │  │              │   │
    │ PK: id           │        │ PK: id             │  │ PK: id       │   │
    │ FK: organization │        │ FK: team           │  │ FK: team     │   │
    │     empire_score │        │ FK: profile        │  │  current_cp  │   │
    │     global_rank  │        │     role           │  │  tier        │   │
    └──────────────────┘        │     roster_slot    │  │  global_rank │   │
                                │     player_role    │  │  streak_count│   │
                                │     status         │  └──────────────┘   │
                                │  is_tournament_captain│                  │
                                │  joined_at         │                     │
                                └────────────────────┘                     │
                                                                           │
                                ┌──────────────────────────────────────────┘
                                │
                        ┌───────▼────────────┐
                        │TeamMigrationMap    │  ◄── Phase 5-7 only
                        │                    │
                        │ PK: id             │
                        │    legacy_id  ─────┼──► links to legacy teams.Team.id
                        │    vnext_id   ─────┼──► links to organizations.Team.id
                        │    migration_date  │
                        └────────────────────┘

                        ┌────────────────────┐
                        │ TeamActivityLog    │  ◄── Audit trail
                        │                    │
                        │ PK: id             │
                        │ FK: team           │
                        │    action_type     │  (CREATE, UPDATE, DELETE, MIGRATE)
                        │    actor_id        │
                        │    description     │
                        │    metadata (JSON) │
                        │    timestamp       │
                        └────────────────────┘
```

### 5.2 Model: Organization

**Purpose:** Represents a verified business entity owning multiple teams.

**File:** `apps/organizations/models/organization.py`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `name` | CharField(100) | NOT NULL, Unique | Organization legal/brand name |
| `slug` | SlugField(100) | NOT NULL, Unique | URL-safe identifier |
| `ceo` | ForeignKey(User) | NOT NULL, on_delete=PROTECT | Organization owner |
| `is_verified` | BooleanField | Default: False | Verified Org Badge status |
| `verification_date` | DateTimeField | Nullable | Date verification granted |
| `logo` | ImageField | Nullable | Organization logo (brand inheritance) |
| `badge` | ImageField | Nullable | Verified badge overlay |
| `banner` | ImageField | Nullable | Profile page banner |
| `description` | TextField | Nullable | Organization bio |
| `website` | URLField | Nullable | Official website |
| `twitter` | CharField(50) | Nullable | Twitter handle |
| `master_wallet` | ForeignKey(Wallet) | NOT NULL, on_delete=PROTECT | Prize money destination |
| `revenue_split_config` | JSONField | Default: {} | Smart contract splits |
| `enforce_brand` | BooleanField | Default: False | Force teams to use org logo |
| `created_at` | DateTimeField | auto_now_add | Timestamp |
| `updated_at` | DateTimeField | auto_now | Timestamp |

**Relationships:**
- `teams` (Reverse FK) → `Team.organization`
- `ranking` (OneToOne) → `OrganizationRanking.organization`

**Indexes:**
```python
class Meta:
    indexes = [
        models.Index(fields=['slug']),  # URL lookups
        models.Index(fields=['ceo']),   # CEO dashboard queries
        models.Index(fields=['is_verified']),  # Verified org filter
    ]
    ordering = ['-created_at']
```

**Methods:**
```python
def get_absolute_url(self):
    """Return canonical URL for organization profile."""
    return reverse('organizations:organization_detail', kwargs={'org_slug': self.slug})

def get_active_teams(self):
    """Return queryset of active teams (excludes deleted/temporary)."""
    return self.teams.filter(status='ACTIVE', is_temporary=False)

def calculate_empire_score(self):
    """Recalculate Empire Score based on top 3 teams' CP."""
    from .ranking import OrganizationRanking
    top_teams = self.get_active_teams().select_related('ranking').order_by('-ranking__current_cp')[:3]
    weights = [1.0, 0.75, 0.5]
    score = sum(team.ranking.current_cp * weights[i] for i, team in enumerate(top_teams))
    ranking, _ = OrganizationRanking.objects.get_or_create(organization=self)
    ranking.empire_score = int(score)
    ranking.save()
    return score

def can_user_manage(self, user):
    """Check if user is CEO or has management permissions."""
    return user == self.ceo or user.is_staff
```

### 5.3 Model: Team

**Purpose:** Represents a competitive unit (roster) that plays tournaments.

**File:** `apps/organizations/models/team.py`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `name` | CharField(100) | NOT NULL | Team display name |
| `slug` | SlugField(100) | NOT NULL, Unique | URL-safe identifier |
| `organization` | ForeignKey(Organization) | Nullable, on_delete=CASCADE | Owning org (NULL if independent) |
| `owner` | ForeignKey(User) | Nullable, on_delete=PROTECT | Owner (NULL if org-owned) |
| `game` | ForeignKey(Game) | NOT NULL, on_delete=PROTECT | Game title |
| `region` | CharField(50) | NOT NULL | Home region (e.g., "Bangladesh") |
| `status` | CharField(20) | NOT NULL, choices=Status | ACTIVE, DELETED, SUSPENDED |
| `logo` | ImageField | Nullable | Team logo (or inherits from org) |
| `banner` | ImageField | Nullable | Profile page banner |
| `description` | TextField | Nullable | Team bio |
| `preferred_server` | CharField(50) | Nullable | TOC: Preferred game server |
| `emergency_contact_discord` | CharField(50) | Nullable | TOC: Discord handle |
| `emergency_contact_phone` | CharField(20) | Nullable | TOC: Phone number |
| `is_temporary` | BooleanField | Default: False | Created during tournament reg |
| `created_at` | DateTimeField | auto_now_add | Timestamp |
| `updated_at` | DateTimeField | auto_now | Timestamp |

**Relationships:**
- `memberships` (Reverse FK) → `TeamMembership.team`
- `ranking` (OneToOne) → `TeamRanking.team`

**Constraints:**
```python
class Meta:
    constraints = [
        # Independent teams: One owner per game
        models.UniqueConstraint(
            fields=['owner', 'game'],
            condition=Q(owner__isnull=False, status='ACTIVE'),
            name='one_independent_team_per_game'
        ),
        # Must have either organization OR owner (not both)
        models.CheckConstraint(
            check=(Q(organization__isnull=False, owner__isnull=True) | 
                   Q(organization__isnull=True, owner__isnull=False)),
            name='team_has_organization_or_owner'
        ),
    ]
    indexes = [
        models.Index(fields=['slug']),  # URL lookups
        models.Index(fields=['game', 'region']),  # Leaderboard filters
        models.Index(fields=['organization']),  # Org team queries
        models.Index(fields=['status']),  # Active team filter
    ]
    ordering = ['-created_at']
```

**Enums:**
```python
class Status(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    DELETED = 'DELETED', 'Deleted'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    DISBANDED = 'DISBANDED', 'Disbanded'
```

**Methods:**
```python
def get_absolute_url(self):
    """Return canonical URL (org-prefixed or independent)."""
    if self.organization:
        return reverse('organizations:org_team_detail', kwargs={
            'org_slug': self.organization.slug,
            'team_slug': self.slug
        })
    else:
        return reverse('organizations:team_detail', kwargs={'slug': self.slug})

def is_organization_team(self):
    """Check if team is owned by an organization."""
    return self.organization is not None

def get_effective_logo_url(self):
    """Return logo URL (team logo or inherited org logo)."""
    if self.organization and self.organization.enforce_brand:
        return self.organization.logo.url if self.organization.logo else None
    return self.logo.url if self.logo else '/static/default_team_logo.png'

def get_active_members(self):
    """Return queryset of active roster members."""
    return self.memberships.filter(status='ACTIVE').select_related('profile__user')

def get_tournament_captain(self):
    """Return the designated tournament captain (or None)."""
    captain_membership = self.memberships.filter(
        status='ACTIVE',
        is_tournament_captain=True
    ).select_related('profile__user').first()
    return captain_membership.profile.user if captain_membership else None

def can_user_manage(self, user):
    """Check if user has management permissions for this team."""
    if self.organization:
        # Org team: CEO or Manager
        if user == self.organization.ceo:
            return True
        return self.memberships.filter(
            profile__user=user,
            status='ACTIVE',
            role__in=['MANAGER', 'COACH']
        ).exists()
    else:
        # Independent team: Owner only
        return user == self.owner
```

### 5.4 Model: TeamMembership

**Purpose:** Represents a user's role on a team roster.

**File:** `apps/organizations/models/membership.py`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `team` | ForeignKey(Team) | NOT NULL, on_delete=CASCADE | Team |
| `profile` | ForeignKey(UserProfile) | NOT NULL, on_delete=CASCADE | User profile |
| `status` | CharField(20) | NOT NULL, choices=Status | ACTIVE, INACTIVE, INVITED, SUSPENDED |
| `role` | CharField(20) | NOT NULL, choices=Role | Organizational role (see below) |
| `roster_slot` | CharField(20) | Nullable, choices=RosterSlot | STARTER, SUBSTITUTE, COACH, ANALYST |
| `player_role` | CharField(20) | Nullable | Game-specific tactical role |
| `is_tournament_captain` | BooleanField | Default: False | Designated captain flag |
| `joined_at` | DateTimeField | auto_now_add | Timestamp |
| `left_at` | DateTimeField | Nullable | Timestamp (if left) |
| `left_reason` | CharField(100) | Nullable | Resignation, Kicked, Transfer |

**Relationships:**
- `team` (FK) → Team
- `profile` (FK) → UserProfile

**Enums:**
```python
class Status(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    INVITED = 'INVITED', 'Invited (Pending)'
    SUSPENDED = 'SUSPENDED', 'Suspended'

class Role(models.TextChoices):
    OWNER = 'OWNER', 'Owner'           # Independent teams only
    MANAGER = 'MANAGER', 'Manager'     # Day-to-day operations
    COACH = 'COACH', 'Coach'           # View-only, scrim scheduling
    PLAYER = 'PLAYER', 'Player'        # Active roster
    SUBSTITUTE = 'SUBSTITUTE', 'Substitute'  # Bench
    ANALYST = 'ANALYST', 'Analyst'     # Staff (non-playing)
    SCOUT = 'SCOUT', 'Scout'           # Org staff (view-only)

class RosterSlot(models.TextChoices):
    STARTER = 'STARTER', 'Starter'
    SUBSTITUTE = 'SUBSTITUTE', 'Substitute'
    COACH = 'COACH', 'Coach (Non-playing)'
    ANALYST = 'ANALYST', 'Analyst (Non-playing)'
```

**Constraints:**
```python
class Meta:
    constraints = [
        # One active membership per user per team
        models.UniqueConstraint(
            fields=['team', 'profile'],
            condition=Q(status='ACTIVE'),
            name='one_active_membership_per_user'
        ),
        # Only one tournament captain per team
        models.UniqueConstraint(
            fields=['team'],
            condition=Q(is_tournament_captain=True, status='ACTIVE'),
            name='one_tournament_captain_per_team'
        ),
    ]
    indexes = [
        models.Index(fields=['team', 'status']),  # Roster queries
        models.Index(fields=['profile', 'status']),  # User team history
        models.Index(fields=['role']),  # Permission checks
    ]
    ordering = ['-joined_at']
```

**Methods:**
```python
def get_permission_list(self):
    """Return list of permission strings for this membership."""
    permissions = {
        'OWNER': ['ALL'],
        'MANAGER': ['register_tournaments', 'edit_roster', 'edit_team', 'schedule_scrims'],
        'COACH': ['edit_toc', 'schedule_scrims', 'view_analytics'],
        'PLAYER': ['view_dashboard'],
        'SUBSTITUTE': ['view_dashboard'],
        'ANALYST': ['view_analytics'],
        'SCOUT': ['view_player_stats'],
    }
    return permissions.get(self.role, [])

def can_manage_roster(self):
    """Check if this member can invite/kick other members."""
    return self.role in ['OWNER', 'MANAGER'] and self.status == 'ACTIVE'

def requires_game_passport(self):
    """Check if this role requires a Game Passport."""
    return self.role in ['PLAYER', 'SUBSTITUTE'] and self.roster_slot in ['STARTER', 'SUBSTITUTE']
```

### 5.5 Model: TeamRanking

**Purpose:** Stores Crown Point rankings for teams.

**File:** `apps/organizations/models/ranking.py`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `team` | OneToOneField(Team) | NOT NULL, on_delete=CASCADE | Team |
| `current_cp` | IntegerField | Default: 0 | Current Crown Points |
| `season_cp` | IntegerField | Default: 0 | Season CP (resets every 4 months) |
| `all_time_cp` | IntegerField | Default: 0 | Lifetime maximum CP |
| `tier` | CharField(20) | NOT NULL, choices=Tier | UNRANKED, BRONZE, ..., CROWN |
| `global_rank` | IntegerField | Nullable | Global position (all games) |
| `regional_rank` | IntegerField | Nullable | Regional position |
| `rank_change_24h` | IntegerField | Default: 0 | Rank change in last 24 hours |
| `rank_change_7d` | IntegerField | Default: 0 | Rank change in last 7 days |
| `is_hot_streak` | BooleanField | Default: False | 3+ consecutive wins |
| `streak_count` | IntegerField | Default: 0 | Current win streak |
| `last_activity_date` | DateTimeField | auto_now | Last match played |
| `last_decay_applied` | DateTimeField | Nullable | Last decay timestamp |

**Enums:**
```python
class Tier(models.TextChoices):
    UNRANKED = 'UNRANKED', 'Unranked'
    BRONZE = 'BRONZE', 'Bronze'
    SILVER = 'SILVER', 'Silver'
    GOLD = 'GOLD', 'Gold'
    PLATINUM = 'PLATINUM', 'Platinum'
    DIAMOND = 'DIAMOND', 'Diamond'
    ASCENDANT = 'ASCENDANT', 'Ascendant'
    CROWN = 'CROWN', 'Crown'
```

**Indexes:**
```python
class Meta:
    indexes = [
        models.Index(fields=['-current_cp']),  # Leaderboard sorting
        models.Index(fields=['tier']),  # Tier filtering
        models.Index(fields=['team__game', '-current_cp']),  # Game-specific leaderboards
        models.Index(fields=['team__region', '-current_cp']),  # Regional leaderboards
    ]
```

**Methods:**
```python
def update_cp(self, points_delta, reason=""):
    """Add/subtract CP and recalculate tier."""
    from apps.organizations.services import RankingService
    self.current_cp += points_delta
    self.season_cp += points_delta
    self.all_time_cp = max(self.all_time_cp, self.current_cp)
    self.recalculate_tier()
    self.save()
    
    # Log activity
    TeamRankingHistory.objects.create(
        team=self.team,
        cp_change=points_delta,
        reason=reason,
        new_total=self.current_cp
    )

def recalculate_tier(self):
    """Determine tier based on current CP."""
    if self.current_cp >= 80000:
        self.tier = 'CROWN'  # Top 1% only
    elif self.current_cp >= 40000:
        self.tier = 'ASCENDANT'
    elif self.current_cp >= 15000:
        self.tier = 'DIAMOND'
    elif self.current_cp >= 5000:
        self.tier = 'PLATINUM'
    elif self.current_cp >= 1500:
        self.tier = 'GOLD'
    elif self.current_cp >= 500:
        self.tier = 'SILVER'
    elif self.current_cp >= 50:
        self.tier = 'BRONZE'
    else:
        self.tier = 'UNRANKED'

def apply_decay(self):
    """Apply 5% CP decay for inactivity (>7 days)."""
    from django.utils import timezone
    if self.last_activity_date < timezone.now() - timedelta(days=7):
        decay_amount = int(self.current_cp * 0.05)
        self.update_cp(-decay_amount, reason="Weekly inactivity decay")
        self.last_decay_applied = timezone.now()
        self.save()
```

### 5.6 Model: TeamMigrationMap

**Purpose:** Maps legacy team IDs to vNext team IDs during migration (Phase 5-7).

**File:** `apps/organizations/models/migration.py`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `legacy_id` | IntegerField | NOT NULL, Unique | apps/teams.Team.id |
| `vnext_id` | IntegerField | NOT NULL, Unique | apps/organizations.Team.id |
| `legacy_slug` | SlugField(100) | NOT NULL | Legacy team slug (for URL redirects) |
| `migration_date` | DateTimeField | auto_now_add | Timestamp |
| `migrated_by` | ForeignKey(User) | Nullable | Admin who ran migration |

**Indexes:**
```python
class Meta:
    indexes = [
        models.Index(fields=['legacy_id']),  # Service layer lookups
        models.Index(fields=['vnext_id']),   # Reverse lookups
        models.Index(fields=['legacy_slug']),  # URL redirects
    ]
    db_table = 'organizations_teammigrationmap'
```

**Methods:**
```python
@classmethod
def get_vnext_id(cls, legacy_id):
    """Return vNext ID for legacy team (or None if not migrated)."""
    mapping = cls.objects.filter(legacy_id=legacy_id).first()
    return mapping.vnext_id if mapping else None

@classmethod
def get_legacy_id(cls, vnext_id):
    """Return legacy ID for vNext team (or None if new team)."""
    mapping = cls.objects.filter(vnext_id=vnext_id).first()
    return mapping.legacy_id if mapping else None
```

### 5.7 Model: TeamActivityLog

**Purpose:** Audit trail for all team-related actions.

**File:** `apps/organizations/models/activity.py`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `team` | ForeignKey(Team) | NOT NULL, on_delete=CASCADE | Team |
| `action_type` | CharField(50) | NOT NULL, choices=ActionType | Action performed |
| `actor_id` | IntegerField | NOT NULL | User who performed action |
| `actor_username` | CharField(50) | NOT NULL | Cached username |
| `description` | TextField | NOT NULL | Human-readable description |
| `metadata` | JSONField | Default: {} | Additional context |
| `timestamp` | DateTimeField | auto_now_add | Timestamp |

**Enums:**
```python
class ActionType(models.TextChoices):
    CREATE = 'CREATE', 'Team Created'
    UPDATE = 'UPDATE', 'Team Updated'
    DELETE = 'DELETE', 'Team Deleted'
    ROSTER_ADD = 'ROSTER_ADD', 'Member Added'
    ROSTER_REMOVE = 'ROSTER_REMOVE', 'Member Removed'
    ROSTER_UPDATE = 'ROSTER_UPDATE', 'Member Role Changed'
    MIGRATE = 'MIGRATE', 'Migrated to vNext'
    ACQUIRE = 'ACQUIRE', 'Acquired by Organization'
    TOURNAMENT_REGISTER = 'TOURNAMENT_REGISTER', 'Registered for Tournament'
    RANKING_UPDATE = 'RANKING_UPDATE', 'Ranking Changed'
```

**Indexes:**
```python
class Meta:
    indexes = [
        models.Index(fields=['team', '-timestamp']),  # Team activity feed
        models.Index(fields=['action_type']),  # Filter by action
        models.Index(fields=['-timestamp']),  # Global activity feed
    ]
    ordering = ['-timestamp']
```

---

## 6. Service Layer Design

### 6.1 Service Architecture Principles

**Single Responsibility:**
- `TeamService`: Team identity, roster, validation.
- `OrganizationService`: Organization management, team acquisition.
- `RankingService`: Crown Points, tier calculation, leaderboards.
- `MigrationService`: Legacy/vNext routing, data migration (Phase 5-7).

**Stateless Operations:**
- Services have no instance variables (all methods are `@staticmethod` or `@classmethod`).
- No caching within services (use Django cache framework externally).

**Database Transaction Management:**
- Write operations use `@transaction.atomic` decorator.
- Bulk operations use `bulk_create()`, `bulk_update()` where possible.

**Error Handling:**
- Raise specific exceptions (not generic `Exception`).
- Return dataclasses for structured outputs (not raw dicts).

### 6.2 Service: TeamService

**Purpose:** Primary interface for all team-related operations.

**File:** `apps/organizations/services/team_service.py`

**Public Methods:**

```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from django.db import transaction

@dataclass
class TeamIdentity:
    """Display-ready team branding."""
    team_id: int
    name: str
    slug: str
    logo_url: str
    badge_url: Optional[str]
    game_name: str
    game_id: int
    region: str
    is_verified: bool
    is_org_team: bool
    organization_name: Optional[str]
    organization_slug: Optional[str]

@dataclass
class WalletInfo:
    """Wallet for prize distribution."""
    wallet_id: int
    owner_name: str
    wallet_type: str  # 'USER' or 'ORG'
    revenue_split: Optional[Dict[str, float]]

@dataclass
class ValidationResult:
    """Roster validation outcome."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    roster_data: Dict[str, Any]

@dataclass
class RosterMember:
    """Roster member info."""
    user_id: int
    username: str
    profile_id: int
    role: str
    roster_slot: str
    in_game_role: Optional[str]
    game_passport: Optional[str]
    passport_status: str  # 'VALID', 'EXPIRED', 'MISSING'
    joined_at: datetime
    is_tournament_captain: bool

@dataclass
class UserInfo:
    """User identity for permissions."""
    user_id: int
    username: str
    email: str
    role: str
    permissions: List[str]


class TeamService:
    """Service layer for team operations."""
    
    @staticmethod
    def get_team_identity(team_id: int) -> TeamIdentity:
        """
        Retrieve display-ready team branding and metadata.
        
        Args:
            team_id: Team primary key
            
        Returns:
            TeamIdentity dataclass
            
        Raises:
            Team.DoesNotExist: Team not found
        """
        team = TeamService._get_team(team_id)
        
        # Brand inheritance logic
        if team.organization and team.organization.enforce_brand:
            logo_url = team.organization.logo.url if team.organization.logo else None
            badge_url = team.organization.badge.url if team.organization.badge else None
        else:
            logo_url = team.get_effective_logo_url()
            badge_url = team.organization.badge.url if team.organization else None
        
        return TeamIdentity(
            team_id=team.id,
            name=team.name,
            slug=team.slug,
            logo_url=logo_url,
            badge_url=badge_url,
            game_name=team.game.name,
            game_id=team.game.id,
            region=team.region,
            is_verified=team.organization.is_verified if team.organization else False,
            is_org_team=team.is_organization_team(),
            organization_name=team.organization.name if team.organization else None,
            organization_slug=team.organization.slug if team.organization else None,
        )
    
    @staticmethod
    def get_team_wallet(team_id: int) -> WalletInfo:
        """
        Retrieve wallet for prize distribution.
        
        Args:
            team_id: Team primary key
            
        Returns:
            WalletInfo dataclass
            
        Raises:
            Team.DoesNotExist: Team not found
        """
        team = TeamService._get_team(team_id)
        
        if team.organization:
            # Organization team
            return WalletInfo(
                wallet_id=team.organization.master_wallet.id,
                owner_name=team.organization.name,
                wallet_type='ORG',
                revenue_split=team.organization.revenue_split_config,
            )
        else:
            # Independent team
            return WalletInfo(
                wallet_id=team.owner.wallet.id,
                owner_name=team.owner.username,
                wallet_type='USER',
                revenue_split=None,
            )
    
    @staticmethod
    def validate_roster(team_id: int, tournament_id: int) -> ValidationResult:
        """
        Validate team roster meets tournament requirements.
        
        Args:
            team_id: Team primary key
            tournament_id: Tournament primary key
            
        Returns:
            ValidationResult dataclass
        """
        from apps.tournaments.models import Tournament
        
        team = TeamService._get_team(team_id)
        tournament = Tournament.objects.get(id=tournament_id)
        errors = []
        warnings = []
        
        # Check 1: Game match
        if team.game_id != tournament.game_id:
            errors.append(f"Team game ({team.game.name}) does not match tournament game ({tournament.game.name})")
        
        # Check 2: Roster size
        active_members = team.memberships.filter(
            status='ACTIVE',
            role__in=['PLAYER', 'SUBSTITUTE']
        ).count()
        min_roster = tournament.min_roster_size or team.game.default_min_roster
        if active_members < min_roster:
            errors.append(f"Team has {active_members} players, minimum required: {min_roster}")
        
        # Check 3: Game Passports
        starters = team.memberships.filter(status='ACTIVE', roster_slot='STARTER')
        for member in starters:
            passport = member.profile.get_game_passport(team.game_id)
            if not passport or passport.is_expired():
                errors.append(f"Player {member.profile.username} missing valid {team.game.name} Game Passport")
        
        # Check 4: Ban status
        banned_players = [m for m in starters if m.profile.is_banned or m.profile.is_suspended]
        if banned_players:
            errors.append(f"{len(banned_players)} player(s) are banned or suspended")
        
        # Check 5: Roster lock conflicts
        locked_tournaments = team.get_active_tournament_locks()
        overlapping = [t for t in locked_tournaments if t.overlaps_with(tournament)]
        if overlapping:
            warnings.append(f"Team is locked in {len(overlapping)} overlapping tournament(s)")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            roster_data={'active_members': active_members, 'starters': len(starters)},
        )
    
    @staticmethod
    def get_authorized_managers(team_id: int) -> List[UserInfo]:
        """
        Retrieve all users authorized to manage team.
        
        Args:
            team_id: Team primary key
            
        Returns:
            List of UserInfo dataclasses
        """
        team = TeamService._get_team(team_id)
        managers = []
        
        if team.organization:
            # Organization team: CEO + Managers + Coaches
            ceo = team.organization.ceo
            managers.append(UserInfo(
                user_id=ceo.id,
                username=ceo.username,
                email=ceo.email,
                role='CEO',
                permissions=['ALL'],
            ))
            
            team_managers = team.memberships.filter(
                status='ACTIVE',
                role__in=['MANAGER', 'COACH'],
            ).select_related('profile__user')
            
            for membership in team_managers:
                managers.append(UserInfo(
                    user_id=membership.profile.user.id,
                    username=membership.profile.username,
                    email=membership.profile.user.email,
                    role=membership.role,
                    permissions=membership.get_permission_list(),
                ))
        else:
            # Independent team: Owner only
            if team.owner:
                managers.append(UserInfo(
                    user_id=team.owner.id,
                    username=team.owner.username,
                    email=team.owner.email,
                    role='OWNER',
                    permissions=['ALL'],
                ))
        
        return managers
    
    @staticmethod
    def get_team_url(team_id: int) -> str:
        """
        Generate correct URL for team profile (handles legacy/vNext routing).
        
        Args:
            team_id: Team primary key
            
        Returns:
            Absolute URL path (string)
        """
        team = TeamService._get_team(team_id)
        return team.get_absolute_url()
    
    @staticmethod
    def get_roster_members(team_id: int, filters: Optional[Dict[str, str]] = None) -> List[RosterMember]:
        """
        Retrieve team roster with optional filtering.
        
        Args:
            team_id: Team primary key
            filters: Optional dict with keys: status, role, roster_slot
            
        Returns:
            List of RosterMember dataclasses
        """
        team = TeamService._get_team(team_id)
        queryset = team.memberships.select_related('profile__user')
        
        if filters:
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            if 'role' in filters:
                queryset = queryset.filter(role=filters['role'])
            if 'roster_slot' in filters:
                queryset = queryset.filter(roster_slot=filters['roster_slot'])
        
        members = []
        for membership in queryset:
            passport = membership.profile.get_game_passport(team.game_id)
            passport_status = 'VALID' if passport and not passport.is_expired() else 'EXPIRED' if passport else 'MISSING'
            
            members.append(RosterMember(
                user_id=membership.profile.user.id,
                username=membership.profile.username,
                profile_id=membership.profile.id,
                role=membership.role,
                roster_slot=membership.roster_slot or '',
                in_game_role=membership.player_role,
                game_passport=passport.game_id if passport else None,
                passport_status=passport_status,
                joined_at=membership.joined_at,
                is_tournament_captain=membership.is_tournament_captain,
            ))
        
        return members
    
    @staticmethod
    @transaction.atomic
    def create_temporary_team(name: str, logo: str, game_id: int, creator_id: int) -> Dict[str, Any]:
        """
        Quick team creation during tournament registration.
        
        Args:
            name: Team name
            logo: Logo URL or path
            game_id: Game FK
            creator_id: User creating the team
            
        Returns:
            Dict with team_id, status='TEMPORARY'
        """
        from apps.organizations.models import Team, TeamMembership
        from django.contrib.auth import get_user_model
        from django.utils.text import slugify
        
        User = get_user_model()
        creator = User.objects.get(id=creator_id)
        
        team = Team.objects.create(
            name=name,
            slug=slugify(name),
            logo=logo,
            game_id=game_id,
            owner=creator,
            is_temporary=True,
            region=creator.profile.country or 'Unknown',
            status='ACTIVE',
        )
        
        # Create owner membership
        TeamMembership.objects.create(
            team=team,
            profile=creator.profile,
            role='OWNER',
            status='ACTIVE',
        )
        
        return {'team_id': team.id, 'status': 'TEMPORARY'}
    
    # --- Internal Helpers ---
    
    @staticmethod
    def _get_team(team_id: int):
        """
        Internal: Route to correct system (legacy or vNext).
        
        During Phase 5-7, checks TeamMigrationMap.
        After Phase 8, queries vNext only.
        """
        from apps.organizations.models import Team
        from apps.organizations.services import MigrationService
        
        # Phase 8+: vNext only
        if not MigrationService.is_dual_system_active():
            return Team.objects.select_related('organization', 'game').get(id=team_id)
        
        # Phase 5-7: Check migration map
        vnext_id = MigrationService.get_vnext_id(team_id)
        if vnext_id:
            return Team.objects.select_related('organization', 'game').get(id=vnext_id)
        else:
            # Still in legacy (should not happen after full migration)
            raise Team.DoesNotExist(f"Team {team_id} not found in vNext system")
```

### 6.3 Service: OrganizationService

**Purpose:** Organization management and team acquisition.

**File:** `apps/organizations/services/organization_service.py`

**Key Methods:**

```python
class OrganizationService:
    """Service layer for organization operations."""
    
    @staticmethod
    @transaction.atomic
    def create_organization(name: str, ceo_id: int, **kwargs) -> Organization:
        """
        Create new organization.
        
        Args:
            name: Organization name
            ceo_id: User ID of CEO
            **kwargs: Optional fields (logo, description, etc.)
            
        Returns:
            Organization instance
        """
        from apps.organizations.models import Organization, OrganizationRanking
        from django.utils.text import slugify
        
        org = Organization.objects.create(
            name=name,
            slug=slugify(name),
            ceo_id=ceo_id,
            **kwargs
        )
        
        # Initialize ranking
        OrganizationRanking.objects.create(
            organization=org,
            empire_score=0,
            global_rank=None
        )
        
        return org
    
    @staticmethod
    @transaction.atomic
    def acquire_team(organization_id: int, team_id: int, actor_id: int) -> Dict[str, Any]:
        """
        Transfer independent team to organization ownership.
        
        Args:
            organization_id: Acquiring organization
            team_id: Team being acquired
            actor_id: User initiating acquisition (must be team owner)
            
        Returns:
            Dict with acquisition details
            
        Raises:
            PermissionError: Actor is not team owner
            ValueError: Team already owned by organization
        """
        from apps.organizations.models import Organization, Team, TeamMembership, TeamActivityLog
        
        org = Organization.objects.get(id=organization_id)
        team = Team.objects.get(id=team_id)
        
        # Validation
        if team.organization:
            raise ValueError("Team is already owned by an organization")
        if team.owner_id != actor_id:
            raise PermissionError("Only team owner can accept acquisition")
        
        # Transfer ownership
        previous_owner = team.owner
        team.organization = org
        team.owner = None
        team.save()
        
        # Convert owner to manager
        owner_membership = TeamMembership.objects.filter(
            team=team,
            profile__user=previous_owner,
            role='OWNER',
            status='ACTIVE'
        ).first()
        if owner_membership:
            owner_membership.role = 'MANAGER'
            owner_membership.save()
        
        # Log activity
        TeamActivityLog.objects.create(
            team=team,
            action_type='ACQUIRE',
            actor_id=actor_id,
            actor_username=previous_owner.username,
            description=f"Team acquired by {org.name}",
            metadata={'organization_id': org.id, 'previous_owner_id': previous_owner.id}
        )
        
        # Recalculate org empire score
        org.calculate_empire_score()
        
        return {
            'success': True,
            'organization_name': org.name,
            'team_name': team.name,
            'previous_owner': previous_owner.username
        }
```

### 6.4 Service: RankingService

**Purpose:** Crown Points calculation and leaderboard generation.

**File:** `apps/organizations/services/ranking_service.py`

**Key Methods:**

```python
class RankingService:
    """Service layer for ranking operations."""
    
    @staticmethod
    @transaction.atomic
    def award_tournament_cp(team_id: int, placement: int, tier: str, tournament_name: str):
        """
        Award Crown Points based on tournament placement.
        
        Args:
            team_id: Team primary key
            placement: 1 (1st), 2 (2nd), 4 (Top 4), 8 (Top 8), 0 (Participation)
            tier: Tournament tier (S, A, B, C)
            tournament_name: Tournament name for audit log
        """
        from apps.organizations.models import TeamRanking
        
        # Base points
        base_points = {
            1: 100,   # 1st place
            2: 75,    # 2nd place
            4: 50,    # Top 4
            8: 25,    # Top 8
            0: 5,     # Participation
        }.get(placement, 5)
        
        # Tier multipliers
        tier_multiplier = {
            'S': 100,
            'A': 50,
            'B': 20,
            'C': 5,
        }.get(tier, 5)
        
        total_cp = base_points * tier_multiplier
        
        # Apply hot streak bonus (1.2x)
        ranking = TeamRanking.objects.get(team_id=team_id)
        if ranking.is_hot_streak:
            total_cp = int(total_cp * 1.2)
        
        # Update CP
        ranking.update_cp(
            points_delta=total_cp,
            reason=f"Tournament: {tournament_name} (Placement: {placement}, Tier: {tier})"
        )
        
        # Update streak
        if placement <= 4:  # Top 4 counts as "win"
            ranking.streak_count += 1
            if ranking.streak_count >= 3:
                ranking.is_hot_streak = True
        else:
            ranking.streak_count = 0
            ranking.is_hot_streak = False
        
        ranking.save()
    
    @staticmethod
    def get_leaderboard(game_id: Optional[int] = None, region: Optional[str] = None, limit: int = 100):
        """
        Retrieve leaderboard rankings.
        
        Args:
            game_id: Filter by game (None = all games)
            region: Filter by region (None = global)
            limit: Number of teams to return
            
        Returns:
            List of TeamRanking instances
        """
        from apps.organizations.models import TeamRanking
        
        queryset = TeamRanking.objects.select_related('team__game', 'team__organization')
        
        if game_id:
            queryset = queryset.filter(team__game_id=game_id)
        if region:
            queryset = queryset.filter(team__region=region)
        
        return queryset.order_by('-current_cp')[:limit]
```

### 6.5 Service: MigrationService (Phase 5-7 Only)

**Purpose:** Handle legacy/vNext routing during migration.

**File:** `apps/organizations/services/migration_service.py`

**Key Methods:**

```python
class MigrationService:
    """Service layer for migration-period routing."""
    
    @staticmethod
    def is_dual_system_active() -> bool:
        """Check if currently in dual-system period (Phase 5-7)."""
        from django.conf import settings
        return getattr(settings, 'TEAM_MIGRATION_DUAL_SYSTEM', False)
    
    @staticmethod
    def get_vnext_id(legacy_id: int) -> Optional[int]:
        """Return vNext ID for legacy team (or None if not migrated)."""
        from apps.organizations.models import TeamMigrationMap
        return TeamMigrationMap.get_vnext_id(legacy_id)
    
    @staticmethod
    def resolve_legacy_url(slug: str) -> str:
        """Resolve legacy /teams/{slug}/ URL to correct vNext URL."""
        from apps.organizations.models import TeamMigrationMap, Team
        
        mapping = TeamMigrationMap.objects.filter(legacy_slug=slug).first()
        if mapping:
            team = Team.objects.select_related('organization').get(id=mapping.vnext_id)
            return team.get_absolute_url()
        else:
            # Team not yet migrated (shouldn't happen after Phase 7)
            return f"/teams/{slug}/"
```

---

## 7. Permissions & RBAC Enforcement

### 7.1 Permission Matrix

| Action | CEO | Manager | Coach | Player | Public |
|--------|-----|---------|-------|--------|--------|
| View team profile | ✅ | ✅ | ✅ | ✅ | ✅ |
| Edit team name/logo | ✅ | ✅ | ❌ | ❌ | ❌ |
| Delete team | ✅ | ❌ | ❌ | ❌ | ❌ |
| Invite/kick members | ✅ | ✅ | ❌ | ❌ | ❌ |
| Register for tournament | ✅ | ✅ | ❌ | ❌ | ❌ |
| Edit TOC settings | ✅ | ✅ | ✅ | ❌ | ❌ |
| Withdraw prize money | ✅ | ❌ | ❌ | ❌ | ❌ |
| Schedule scrims | ✅ | ✅ | ✅ | ❌ | ❌ |
| Leave team | ✅ | ✅ | ✅ | ✅ | ❌ |

### 7.2 Permission Decorators

**File:** `apps/organizations/permissions/decorators.py`

```python
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from apps.organizations.models import Team, Organization

def require_team_permission(permission_name):
    """
    Decorator to check team-level permissions.
    
    Usage:
        @require_team_permission('edit_roster')
        def add_player_view(request, team_id):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            team_id = kwargs.get('team_id') or kwargs.get('pk')
            team = get_object_or_404(Team, id=team_id)
            
            if not team.can_user_manage(request.user):
                return HttpResponseForbidden("You do not have permission to perform this action.")
            
            # Check specific permission
            from apps.organizations.permissions.checkers import has_team_permission
            if not has_team_permission(request.user, team, permission_name):
                return HttpResponseForbidden(f"You do not have '{permission_name}' permission.")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_org_permission(permission_name):
    """
    Decorator to check organization-level permissions.
    
    Usage:
        @require_org_permission('create_team')
        def create_org_team_view(request, org_id):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            org_id = kwargs.get('org_id') or kwargs.get('pk')
            org = get_object_or_404(Organization, id=org_id)
            
            if not org.can_user_manage(request.user):
                return HttpResponseForbidden("You do not have permission to manage this organization.")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

### 7.3 Permission Checkers

**File:** `apps/organizations/permissions/checkers.py`

```python
def has_team_permission(user, team, permission: str) -> bool:
    """
    Check if user has specific permission for team.
    
    Args:
        user: Django User instance
        team: Team instance
        permission: Permission string (e.g., 'edit_roster', 'register_tournaments')
        
    Returns:
        Boolean
    """
    # Staff always have permission
    if user.is_staff:
        return True
    
    if team.organization:
        # Organization team: Check CEO or membership role
        if user == team.organization.ceo:
            return True
        
        membership = team.memberships.filter(
            profile__user=user,
            status='ACTIVE'
        ).first()
        
        if not membership:
            return False
        
        # Permission mapping
        permissions_map = {
            'edit_team': ['MANAGER'],
            'edit_roster': ['MANAGER'],
            'register_tournaments': ['MANAGER'],
            'edit_toc': ['MANAGER', 'COACH'],
            'schedule_scrims': ['MANAGER', 'COACH'],
            'view_dashboard': ['MANAGER', 'COACH', 'PLAYER', 'SUBSTITUTE'],
        }
        
        allowed_roles = permissions_map.get(permission, [])
        return membership.role in allowed_roles
    else:
        # Independent team: Owner has all permissions
        return user == team.owner
```

### 7.4 Ownership Resolution

**Logic for determining team control:**

```python
def get_team_controller(team) -> User:
    """
    Return the User who controls team decisions.
    
    Returns:
        User instance (CEO for org teams, owner for independent teams)
    """
    if team.organization:
        return team.organization.ceo
    else:
        return team.owner
```

---

## 8. Signals & Events

### 8.1 Signal Naming & Structure

**Convention:** Use past tense verbs, prefix with entity name.

**Examples:**
- `team_created`
- `team_updated`
- `team_deleted`
- `roster_member_added`
- `roster_member_removed`
- `roster_member_updated`
- `team_invite_sent`
- `team_invite_accepted`
- `ranking_updated`

### 8.2 Signal Emitters

**File:** `apps/organizations/signals/emitters.py`

```python
from django.dispatch import Signal

# Team lifecycle signals
team_created = Signal()  # providing_args=['team', 'creator']
team_updated = Signal()  # providing_args=['team', 'changed_fields']
team_deleted = Signal()  # providing_args=['team', 'actor']

# Roster signals
roster_member_added = Signal()  # providing_args=['team', 'membership', 'invited_by']
roster_member_removed = Signal()  # providing_args=['team', 'membership', 'removed_by', 'reason']
roster_member_updated = Signal()  # providing_args=['team', 'membership', 'changed_fields']

# Invite signals
team_invite_sent = Signal()  # providing_args=['invite', 'team', 'invitee', 'inviter']
team_invite_accepted = Signal()  # providing_args=['invite', 'team', 'membership']
team_invite_declined = Signal()  # providing_args=['invite', 'team', 'invitee']

# Ranking signals
ranking_updated = Signal()  # providing_args=['team', 'old_cp', 'new_cp', 'reason']
```

### 8.3 Signal Handlers

**File:** `apps/organizations/signals/handlers.py`

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.organizations.models import Team, TeamMembership, Organization
from apps.organizations.signals.emitters import team_created, roster_member_added

@receiver(post_save, sender=Team)
def initialize_team_ranking(sender, instance, created, **kwargs):
    """Create TeamRanking record for new teams."""
    if created:
        from apps.organizations.models import TeamRanking
        TeamRanking.objects.create(
            team=instance,
            current_cp=0,
            tier='UNRANKED'
        )
        
        # Emit custom signal
        team_created.send(sender=Team, team=instance, creator=instance.owner)


@receiver(post_save, sender=TeamMembership)
def handle_membership_save(sender, instance, created, **kwargs):
    """Handle roster changes."""
    if created and instance.status == 'ACTIVE':
        # New active member added
        roster_member_added.send(
            sender=TeamMembership,
            team=instance.team,
            membership=instance,
            invited_by=None  # TODO: Track inviter
        )
        
        # Update user profile team count
        instance.profile.recalculate_team_count()


@receiver(post_save, sender=Organization)
def initialize_organization_ranking(sender, instance, created, **kwargs):
    """Create OrganizationRanking record for new organizations."""
    if created:
        from apps.organizations.models import OrganizationRanking
        OrganizationRanking.objects.create(
            organization=instance,
            empire_score=0,
            global_rank=None
        )
```

### 8.4 Notification Integration

**Pattern:** Dependent apps listen to vNext signals and call NotificationService.

**Example (in apps/notifications/signals/team_signals.py):**

```python
from django.dispatch import receiver
from apps.organizations.signals.emitters import roster_member_added, team_invite_sent
from apps.notifications.services import NotificationService

@receiver(roster_member_added)
def notify_roster_change(sender, team, membership, invited_by, **kwargs):
    """Send notification to all team members when roster changes."""
    NotificationService.send_roster_change_notification(
        team_id=team.id,
        team_name=team.name,
        added_username=membership.profile.username,
        team_url=team.get_absolute_url()
    )

@receiver(team_invite_sent)
def notify_team_invite(sender, invite, team, invitee, inviter, **kwargs):
    """Send invitation notification to invitee."""
    NotificationService.send_team_invite_notification(
        invitee_email=invitee.email,
        team_name=team.name,
        inviter_username=inviter.username,
        accept_url=f"/teams/invites/{invite.id}/accept/"
    )
```

### 8.5 Legacy Signal Compatibility

**Requirement:** vNext signals must be equivalent to legacy signals during Phase 5-7.

**Strategy:**
- vNext emits same signal names as legacy (e.g., `post_save` on `Team`).
- Dependent apps register handlers for both legacy and vNext models.
- After Phase 8, legacy signal handlers are removed.

---

## 9. Feature Flags & Configuration

### 9.1 Feature Flag Definitions

**Purpose:** Control phased rollout of vNext features.

**Storage:** Django settings + Database (django-waffle or similar).

**Flags:**

| Flag Name | Scope | Purpose | Default (Phase) |
|-----------|-------|---------|-----------------|
| `TEAM_VNEXT_ENABLED` | Global | Enable vNext team system | False (Phase 1-2), True (Phase 3+) |
| `ORG_FEATURES_ENABLED` | Global | Enable organization features | False (Phase 1-3), True (Phase 4+) |
| `TEAM_MIGRATION_DUAL_SYSTEM` | Global | Enable dual-system routing | False (Phase 1-4), True (Phase 5-7), False (Phase 8+) |
| `TEAM_VNEXT_USER_ROLLOUT` | Per-User | Gradual user rollout | 0% (Phase 3), 10% (Phase 4), 100% (Phase 5+) |
| `SHOW_EMPIRE_SCORE` | Global | Display org rankings | False (Phase 1-4), True (Phase 5+) |
| `DCRS_ENABLED` | Global | Enable ranking system | False (Phase 1-3), True (Phase 4+) |
| `LEGACY_TEAM_CREATE_DISABLED` | Global | Disable legacy team creation | False (Phase 1-2), True (Phase 3+) |

### 9.2 Flag Evaluation

**Configuration (deltacrown/settings.py):**

```python
# Feature flags
TEAM_VNEXT_ENABLED = env.bool('TEAM_VNEXT_ENABLED', default=False)
ORG_FEATURES_ENABLED = env.bool('ORG_FEATURES_ENABLED', default=False)
TEAM_MIGRATION_DUAL_SYSTEM = env.bool('TEAM_MIGRATION_DUAL_SYSTEM', default=False)
DCRS_ENABLED = env.bool('DCRS_ENABLED', default=False)
LEGACY_TEAM_CREATE_DISABLED = env.bool('LEGACY_TEAM_CREATE_DISABLED', default=False)

# Gradual rollout percentage (0-100)
TEAM_VNEXT_USER_ROLLOUT = env.int('TEAM_VNEXT_USER_ROLLOUT', default=0)
```

**Usage in Code:**

```python
from django.conf import settings

def team_create_view(request):
    """Team creation view."""
    if not settings.TEAM_VNEXT_ENABLED:
        return HttpResponse("Team creation is temporarily unavailable.", status=503)
    
    # Check per-user rollout
    if not user_in_rollout(request.user, settings.TEAM_VNEXT_USER_ROLLOUT):
        return render(request, 'teams/legacy_create.html')
    
    # vNext flow
    return render(request, 'organizations/team_create.html')

def user_in_rollout(user, percentage):
    """Check if user is in gradual rollout cohort."""
    if percentage >= 100:
        return True
    if percentage <= 0:
        return False
    return (user.id % 100) < percentage
```

### 9.3 Rollback Strategy

**Trigger Conditions:**
- P0 incident: >5% error rate, data corruption, critical functionality broken.
- P1 incident: >10% performance degradation, 10%+ support ticket increase.

**Rollback Procedure:**

1. **Immediate Actions (0-5 minutes):**
   ```bash
   # Disable vNext features
   heroku config:set TEAM_VNEXT_ENABLED=false --app deltacrown-prod
   heroku config:set ORG_FEATURES_ENABLED=false --app deltacrown-prod
   ```

2. **Service Layer Revert (5-15 minutes):**
   ```bash
   # Revert TeamService to legacy-only mode
   git revert <commit-hash>
   git push origin main
   # Deploy previous version
   ```

3. **Monitoring (15-60 minutes):**
   - Verify error rate drops below 1%.
   - Check tournament registration success rate.
   - Monitor notification delivery.

4. **Post-Mortem (24-48 hours):**
   - Document root cause.
   - Add regression tests.
   - Update compatibility contract if design flaw found.

---

## 10. Error Handling & Logging

### 10.1 Error Categories

**Application Errors:**
- `TeamNotFoundError`: Team ID does not exist.
- `PermissionDeniedError`: User lacks required permission.
- `RosterValidationError`: Roster fails tournament requirements.
- `MigrationError`: Data migration failed (Phase 5-7).
- `WalletNotFoundError`: Team wallet missing or inaccessible.

**Custom Exception Definitions:**

**File:** `apps/organizations/exceptions.py`

```python
class OrganizationsError(Exception):
    """Base exception for organizations app."""
    pass

class TeamNotFoundError(OrganizationsError):
    """Team does not exist."""
    pass

class PermissionDeniedError(OrganizationsError):
    """User lacks required permission."""
    pass

class RosterValidationError(OrganizationsError):
    """Roster fails validation checks."""
    def __init__(self, errors, warnings=None):
        self.errors = errors
        self.warnings = warnings or []
        super().__init__(f"Roster validation failed: {', '.join(errors)}")

class MigrationError(OrganizationsError):
    """Migration-related error."""
    pass

class WalletNotFoundError(OrganizationsError):
    """Wallet does not exist or is inaccessible."""
    pass
```

### 10.2 Logging Strategy

**Log Levels:**
- `DEBUG`: Service layer method entry/exit.
- `INFO`: Successful operations (team created, CP awarded).
- `WARNING`: Non-critical issues (missing optional fields, deprecated API usage).
- `ERROR`: Recoverable errors (validation failures, permission denied).
- `CRITICAL`: Data corruption, migration failures, system-wide issues.

**Logging Configuration:**

**File:** `apps/organizations/services/team_service.py` (example)

```python
import logging

logger = logging.getLogger('organizations.team_service')

class TeamService:
    @staticmethod
    def get_team_identity(team_id: int) -> TeamIdentity:
        logger.debug(f"get_team_identity called for team_id={team_id}")
        
        try:
            team = TeamService._get_team(team_id)
            logger.info(f"Retrieved team identity: {team.name} (id={team_id})")
            # ... rest of logic
        except Team.DoesNotExist:
            logger.error(f"Team not found: team_id={team_id}")
            raise TeamNotFoundError(f"Team with ID {team_id} does not exist")
        except Exception as e:
            logger.critical(f"Unexpected error in get_team_identity: {e}", exc_info=True)
            raise
```

**Logging Format (deltacrown/settings.py):**

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/organizations.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'organizations': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'organizations.team_service': {
            'handlers': ['file'],
            'level': 'INFO',
        },
        'organizations.migration_service': {
            'handlers': ['file'],
            'level': 'WARNING',  # Phase 5-7 only
        },
    },
}
```

### 10.3 Audit Logging

**Purpose:** Track all permission-sensitive actions for compliance and debugging.

**Implementation:** `TeamActivityLog` model (see Section 3.7).

**Logged Actions:**
- Team creation/deletion.
- Roster changes (invite, kick, role change).
- Organization acquisitions.
- Prize money withdrawals.
- Tournament registrations.
- Migration events (Phase 5-7).

**Usage Example:**

```python
from apps.organizations.models import TeamActivityLog

def kick_player(team, membership, actor):
    """Remove player from roster."""
    membership.status = 'INACTIVE'
    membership.left_at = timezone.now()
    membership.left_reason = "Kicked by management"
    membership.save()
    
    # Audit log
    TeamActivityLog.objects.create(
        team=team,
        action_type='ROSTER_REMOVE',
        actor_id=actor.id,
        actor_username=actor.username,
        description=f"Removed {membership.profile.username} from roster",
        metadata={
            'removed_user_id': membership.profile.user.id,
            'reason': 'management_decision'
        }
    )
```

### 10.4 Monitoring & Alerting

**Metrics to Track:**
- Team creation rate (per hour).
- Tournament registration success rate.
- Service layer response time (95th percentile).
- Database query count per service call.
- Error rate by exception type.
- Migration progress (Phase 5-7): Teams migrated per day.

**Alert Thresholds:**
- Error rate >2%: Page on-call engineer.
- Service response time >500ms: Warning.
- Tournament registration failure rate >5%: Critical alert.
- Dual-write divergence detected (Phase 5-7): Critical alert.

**Tools:**
- Sentry for exception tracking.
- Prometheus + Grafana for metrics.
- Django Debug Toolbar for local profiling.

---

## Appendix A: Migration Checklist

**Phase 2 (Week 5-6): Service Layer Deployment**

- [ ] Deploy `TeamService`, `OrganizationService`, `RankingService` to production
- [ ] Enable `TEAM_VNEXT_ENABLED=true` flag
- [ ] Update `tournaments` app to use `TeamService`
- [ ] Update `notifications` app to use `TeamService.get_team_url()`
- [ ] Run integration tests (100% pass rate required)
- [ ] Performance benchmarks: <200ms service response time
- [ ] Monitor error rate for 48 hours (<1% required)

**Phase 5 (Week 13-14): Data Migration**

- [ ] Run `migrate_legacy_teams` management command on staging
- [ ] Validate: All legacy teams mapped to vNext (zero unmapped teams)
- [ ] Enable `TEAM_MIGRATION_DUAL_SYSTEM=true` flag
- [ ] Run `reconcile_dual_write` nightly for 7 days (zero divergence)
- [ ] Stakeholder approval for production migration
- [ ] Run production migration during maintenance window
- [ ] Verify: All tournament registrations point to correct team IDs

**Phase 6 (Week 15): URL Redirects**

- [ ] Deploy URL redirect middleware
- [ ] Test: Click 20+ pre-migration notification links (zero 404s)
- [ ] Update email templates to use dynamic URLs
- [ ] Monitor redirect logs for 7 days

**Phase 8 (Week 17-20): Legacy Archive**

- [ ] 30 days of stable operation (no P0/P1 incidents)
- [ ] Disable `LEGACY_TEAM_CREATE_DISABLED=true`
- [ ] Rename legacy tables: `teams_team` → `_archived_teams_team`
- [ ] Remove legacy admin panels
- [ ] Update documentation to reference vNext only
- [ ] Stakeholder approval for permanent legacy deletion (6+ months later)

---

## Appendix B: API Reference

**Service Layer Public Methods (Summary):**

```python
# TeamService
TeamService.get_team_identity(team_id: int) -> TeamIdentity
TeamService.get_team_wallet(team_id: int) -> WalletInfo
TeamService.validate_roster(team_id: int, tournament_id: int) -> ValidationResult
TeamService.get_authorized_managers(team_id: int) -> List[UserInfo]
TeamService.get_team_url(team_id: int) -> str
TeamService.get_roster_members(team_id: int, filters: dict) -> List[RosterMember]
TeamService.create_temporary_team(...) -> dict

# OrganizationService
OrganizationService.create_organization(name: str, ceo_id: int) -> Organization
OrganizationService.acquire_team(org_id: int, team_id: int, actor_id: int) -> dict

# RankingService
RankingService.award_tournament_cp(team_id: int, placement: int, tier: str, tournament_name: str) -> None
RankingService.get_leaderboard(game_id: int, region: str, limit: int) -> List[TeamRanking]

# MigrationService (Phase 5-7 only)
MigrationService.is_dual_system_active() -> bool
MigrationService.get_vnext_id(legacy_id: int) -> Optional[int]
MigrationService.resolve_legacy_url(slug: str) -> str
```

---

## Document Maintenance

**Review Cadence:** Weekly during development (Phase 1-7), monthly post-launch.  
**Amendment Process:** Requires approval from Tech Lead + Senior Engineer.  
**Version History:**
- v1.0 (Jan 25, 2026): Initial architecture specification.

---

**END OF ARCHITECTURE SPECIFICATION**
