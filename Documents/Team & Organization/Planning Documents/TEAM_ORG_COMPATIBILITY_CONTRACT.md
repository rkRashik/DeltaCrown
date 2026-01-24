# 🔗 Team & Organization System Compatibility Contract

**Document Version:** 1.2  
**Effective Date:** January 25, 2026  
**Owner:** Platform Architecture Team  
**Status:** Binding Technical Contract  
**Parent Documents:**  
- [TEAM_ORG_VNEXT_MASTER_PLAN.md](./TEAM_ORG_VNEXT_MASTER_PLAN.md)  
- [TEAM_ORG_ENGINEERING_STANDARDS.md](./TEAM_ORG_ENGINEERING_STANDARDS.md)
- [TEAM_ORG_PERFORMANCE_CONTRACT.md](./TEAM_ORG_PERFORMANCE_CONTRACT.md)

**Changelog:**
- v1.2 (Jan 25, 2026): Added Database Strategy Hard Rules, explicit legacy table modification prohibition, performance contract reference
- v1.1 (Jan 25, 2026): Added Frontend & URL Stability Rules section, engineering standards compliance requirements
- v1.0 (Jan 25, 2026): Initial compatibility contract

---

## Table of Contents

1. [Overview](#1-overview)
2. [Database Strategy (Hard Rules)](#2-database-strategy-hard-rules)
3. [Guaranteed Identity Contracts](#3-guaranteed-identity-contracts)
4. [Service-Level Contracts](#4-service-level-contracts)
5. [Data Field Assumptions](#5-data-field-assumptions)
6. [URL & Routing Contracts](#6-url--routing-contracts)
7. [Event / Signal / Notification Contracts](#7-event--signal--notification-contracts)
8. [Frontend & URL Stability Rules](#8-frontend--url-stability-rules)
9. [Adapter Strategy](#9-adapter-strategy)
10. [Hard Rules (Non-Negotiable)](#10-hard-rules-non-negotiable)

---

## 1. Overview

### 1.1 Purpose of This Contract

This document defines **the exact interface** that dependent applications (`tournaments`, `user_profile`, `notifications`, `leaderboards`, `tournament_ops`, `economy`) expect from the Team system. It ensures:

1. **Zero-breakage migration:** New `apps/organizations` can be built in parallel without breaking existing functionality.
2. **Clear boundaries:** Developers know what can/cannot change during migration.
3. **Adapter requirements:** Specifies where compatibility shims are needed.
4. **Safe deprecation:** Defines what legacy code must continue to work and for how long.

**This is NOT a feature specification.** This is a **platform integration contract** that prevents production failures during the parallel build migration.

### 1.2 Relationship to Master Plan

This contract implements Section 9 ("Service Layer & Compatibility Contracts") and Section 10 ("Migration Strategy") of the [TEAM_ORG_VNEXT_MASTER_PLAN.md](./TEAM_ORG_VNEXT_MASTER_PLAN.md).

**Key Principles:**
- Legacy `apps/teams` remains **read-only** after Phase 2.
- New `apps/organizations` becomes **write-primary** from Phase 3 onward.
- Service layer (TeamService) provides **unified interface** to both systems.
- Migration timeline: 12-16 weeks with gradual cutover.

### 1.3 Definitions

**Legacy System:**
- `apps/teams` Django app (existing codebase).
- Models: `Team`, `TeamMembership`, `TeamInvite`, `TeamGameRanking`.
- Database tables: `teams_team`, `teams_membership`, `teams_invite`.
- Status: **Read-only after Phase 2, archived after Phase 8.**

**vNext System:**
- `apps/organizations` Django app (new codebase).
- Models: `Organization`, `Team`, `TeamMembership`, `TeamRanking`, `OrganizationRanking`.
- Database tables: `organizations_organization`, `organizations_team`, `organizations_membership`.
- Status: **Write-primary from Phase 3, sole system from Phase 8.**

**Dependent Apps:**
- `tournaments`: Tournament registration, eligibility, bracket generation.
- `user_profile`: Team history, profile display, activity feeds.
- `notifications`: Invites, roster changes, tournament notifications.
- `leaderboards`: Ranking displays, leaderboard entries.
- `tournament_ops`: Operations dashboard, team management.
- `economy`: Prize distribution, wallet access.

---

## 2. Database Strategy (Hard Rules)

### 2.1 NON-NEGOTIABLE DATABASE SEPARATION

**CRITICAL:** Legacy tables MUST NOT be modified during vNext development. This prevents catastrophic breakage of existing tournament integrations.

#### **HARD RULE 1: COMPLETELY NEW TABLES REQUIRED**

**MUST:**
- `apps/organizations` uses **COMPLETELY NEW** database tables
- All tables prefixed with `organizations_*`
- Zero structural dependencies on legacy `teams_*` tables

**MUST NOT:**
- Add columns to `teams_team`, `teams_membership`, `teams_invite`, `teams_teamgameranking`
- Modify legacy table constraints or column types
- Create FKs from vNext to legacy tables (except `TeamMigrationMap`)
- Assume legacy table schema will remain unchanged

**Table Separation:**

| System | Table Prefix | Examples | Status |
|--------|-------------|----------|--------|
| Legacy | `teams_*` | `teams_team`, `teams_membership` | READ-ONLY (Phase 2+) |
| vNext | `organizations_*` | `organizations_team`, `organizations_membership` | WRITE-PRIMARY (Phase 3+) |

---

#### **HARD RULE 2: LEGACY READ-ONLY AFTER PHASE 2**

**Phase 2+ Behavior:**

**MUST:**
- All new team creations write ONLY to `organizations_team`
- Service layer routes reads to correct system
- Legacy tables frozen (zero new inserts)

**MUST NOT:**
- Insert into `teams_team` after Phase 2 deployment
- Update legacy rows (except Phase 5-7 dual-write sync)
- Delete legacy data before Phase 8

**Why This Exists:**
- Prevents data fragmentation (some teams in legacy, some in vNext)
- Simplifies rollback (legacy system unmodified)
- Reduces regression testing burden

---

#### **HARD RULE 3: TEAMMIGRATIONMAP IS SOLE BRIDGE**

**Purpose:** Connect legacy team IDs to vNext team IDs during Phase 5-7.

**Structure:**
```python
class TeamMigrationMap(models.Model):
    legacy_team_id = models.IntegerField(unique=True)  # teams_team.id
    vnext_team_id = models.ForeignKey('Team', on_delete=models.CASCADE)
    migration_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'organizations_migration_map'
```

**MUST:**
- Query `TeamMigrationMap` for all cross-system lookups
- Retain indefinitely (minimum 12 months post-migration)
- Use for URL redirect preservation

**MUST NOT:**
- Create direct FKs between legacy and vNext models
- Bypass migration map during dual-read phase
- Delete rows (breaks old notification links)

---

### 2.2 Enforcement Mechanisms

**Code Review:**
- Reject any PR touching legacy tables (Phase 1-4)
- Verify `db_table = 'organizations_*'` on all vNext models
- Check for `from apps.teams.models import` (forbidden)

**CI Pipeline:**
- Fail build if legacy migrations detected
- Lint check: No legacy model imports in vNext code
- Schema diff: Verify zero legacy table changes

**Violation Consequences:**
- Immediate PR rejection (no exceptions)
- Rollback if deployed to production
- Post-mortem required

---

## 3. Guaranteed Identity Contracts

These identifiers **MUST exist and remain stable** during and after migration. Changing these breaks platform stability.

### 3.1 Team Primary Identifier

**Field:** `team.id` (Integer Primary Key)

**Contract:**
- ✅ **Preserved:** Team IDs remain stable across migration.
- **Type:** Integer (no UUID migration during vNext transition).
- **Uniqueness:** Global unique constraint across legacy + vNext systems.

**Migration Mapping:**
- `TeamMigrationMap` table created in Phase 5.
- Structure: `(legacy_id, vnext_id, migration_date)`.
- Maintained **indefinitely** (minimum 12 months post-migration).

**Dependent Apps Assumption:**
- `tournaments`: Uses `team_id` (IntegerField) in Registration model.
- `leaderboards`: Uses FK to `teams.Team` model.
- `economy`: Prize distribution queries by `team_id`.

**Break Risk:** **P0 - CRITICAL**  
Changing team ID type or reusing IDs will cause data corruption across 100+ locations.

---

### 3.2 Team Slug Identifier

**Field:** `team.slug` (SlugField, Unique)

**Contract:**
- ✅ **Preserved:** Slugs remain stable for SEO and URL persistence.
- **Format:** Lowercase, hyphenated, alphanumeric (e.g., `protocol-v`, `syntax-fc`).
- **Uniqueness:** Global unique constraint (not scoped to game).

**URL Usage:**
- Legacy: `/teams/{slug}/`
- vNext Independent: `/teams/{slug}/` (redirect from legacy)
- vNext Organization: `/orgs/{org_slug}/teams/{team_slug}/`

**Dependent Apps Assumption:**
- `notifications`: Uses `reverse('teams:team_detail', kwargs={'slug': team.slug})`.
- `user_profile`: Generates team profile links via slug.
- `tournaments`: Email notifications contain `/teams/{slug}/` links.

**Migration Strategy:**
- Phase 6 deploys URL redirect shim.
- `TeamService.get_team_url(team_id)` returns correct URL (legacy or vNext).
- Notifications updated to use dynamic URL generation, not hardcoded paths.

**Break Risk:** **P0 - CRITICAL**  
Changing slugs breaks 50+ notification links, SEO, and external referrals.

---

### 3.3 Team Display Name

**Field:** `team.name` (CharField, Max 100)

**Contract:**
- ✅ **Preserved:** Team names remain editable but field name unchanged.
- **Validation:** Non-empty, max 100 characters, no special characters except hyphen/space.

**Dependent Apps Assumption:**
- `tournaments`: Bracket display uses `team.name`.
- `notifications`: All notification messages reference `team.name`.
- `user_profile`: Activity feeds display `team.name`.
- `leaderboards`: Ranking tables show `team.name`.

**Break Risk:** **P0 - CRITICAL**  
Renaming this field breaks 200+ display locations across 7 apps.

---

### 3.4 Organization Identifier (New in vNext)

**Field:** `organization.id` (Integer Primary Key)

**Contract:**
- 🔁 **Adapted:** New field introduced in vNext, NULL in legacy teams.
- **Access Pattern:** `team.organization_id` (ForeignKey, nullable).

**Backward Compatibility:**
- Legacy teams: `team.organization_id = NULL` (Independent Team).
- vNext teams: `team.organization_id = <org_id>` (Organization Team).

**Service Layer Handling:**
```python
# TeamService.get_team_identity() returns:
{
    'is_org_team': team.organization_id is not None,
    'organization_name': team.organization.name if team.organization else None,
    'organization_slug': team.organization.slug if team.organization else None,
}
```

**Break Risk:** **P1 - HIGH**  
Direct database queries assuming `organization` field exists will fail on legacy teams.

---

### 3.5 Game Association

**Field:** `team.game_id` (ForeignKey to `games.Game`)

**Contract:**
- ✅ **Preserved:** Field name and type unchanged.
- **Nullability:** NOT NULL (every team must have a game).

**Dependent Apps Assumption:**
- `tournaments`: Eligibility checks filter by `team.game`.
- `leaderboards`: Rankings scoped by `game`.
- `user_profile`: Team history grouped by `game`.

**Break Risk:** **P0 - CRITICAL**  
Removing game FK or allowing NULL breaks tournament eligibility logic.

---

### 3.6 Region / Base Identity

**Field:** `team.region` (CharField, nullable in legacy)

**Contract:**
- 🔁 **Adapted:** Legacy teams may have NULL region, vNext teams MUST have region.
- **Migration:** Phase 5 script backfills NULL regions using IP detection.

**Service Layer Handling:**
```python
# TeamService.get_team_identity() returns:
{
    'region': team.region or 'Unknown',  # Safe default
}
```

**Dependent Apps Assumption:**
- `leaderboards`: Regional rankings require non-NULL region.
- `tournaments`: Region used for seeding and matchmaking preferences.

**Break Risk:** **P2 - MEDIUM**  
NULL regions cause leaderboard filtering issues but don't break core functionality.

---

## 4. Service-Level Contracts

**MANDATORY:** All dependent apps MUST use these service methods instead of direct model access after Phase 2 deployment.

### 4.1 TeamService.get_team_identity(team_id)

**Purpose:** Retrieve display-ready team branding and metadata.

**Input:**
- `team_id` (int): Team primary key.

**Output:** `TeamIdentity` dataclass
```python
@dataclass
class TeamIdentity:
    team_id: int
    name: str
    slug: str
    logo_url: str
    badge_url: Optional[str]  # Org badge if applicable
    game_name: str
    game_id: int
    region: str
    is_verified: bool
    is_org_team: bool
    organization_name: Optional[str]
    organization_slug: Optional[str]
```

**Source of Truth:**
- **Phase 2-4:** Queries legacy `apps/teams.Team`.
- **Phase 5-7:** Checks `TeamMigrationMap`, queries legacy OR vNext.
- **Phase 8+:** Queries vNext `apps/organizations.Team` only.

**Logic:**
```python
def get_team_identity(team_id: int) -> TeamIdentity:
    # Phase 5-7: Check migration status
    if mapping := TeamMigrationMap.objects.filter(legacy_id=team_id).first():
        team = VNextTeam.objects.select_related('organization', 'game').get(id=mapping.vnext_id)
    else:
        team = LegacyTeam.objects.select_related('game').get(id=team_id)
    
    # Brand inheritance logic
    if team.organization and team.organization.enforce_brand:
        logo_url = team.organization.logo.url
        badge_url = team.organization.badge.url
    else:
        logo_url = team.logo.url if team.logo else '/static/default_team_logo.png'
        badge_url = team.organization.badge.url if team.organization else None
    
    return TeamIdentity(
        team_id=team.id,
        name=team.name,
        slug=team.slug,
        logo_url=logo_url,
        badge_url=badge_url,
        game_name=team.game.name,
        game_id=team.game.id,
        region=team.region or 'Unknown',
        is_verified=team.organization.is_verified if team.organization else False,
        is_org_team=team.organization is not None,
        organization_name=team.organization.name if team.organization else None,
        organization_slug=team.organization.slug if team.organization else None,
    )
```

**Consumers:**
- `tournaments`: Bracket display, tournament lobbies.
- `notifications`: Team name in notification messages.
- `user_profile`: Team profile cards.
- `leaderboards`: Ranking table display.

**Break Risk:** **P0 - CRITICAL**  
If consumers directly access `team.name` or `team.logo` instead of service, they bypass brand inheritance logic.

---

### 4.2 TeamService.get_team_wallet(team_id)

**Purpose:** Retrieve wallet for prize distribution.

**Input:**
- `team_id` (int): Team primary key.

**Output:** `WalletInfo` dataclass
```python
@dataclass
class WalletInfo:
    wallet_id: int
    owner_name: str
    wallet_type: Literal['USER', 'ORG']
    revenue_split: Optional[Dict[str, float]]  # e.g., {'players': 0.8, 'org': 0.2}
```

**Source of Truth:**
- **Legacy:** `team.owner.wallet` (User's personal wallet).
- **vNext Independent:** `team.owner.wallet` (same as legacy).
- **vNext Organization:** `team.organization.master_wallet` (Org's master wallet).

**Logic:**
```python
def get_team_wallet(team_id: int) -> WalletInfo:
    team = _get_team_from_either_system(team_id)
    
    if team.organization:
        # Organization team
        return WalletInfo(
            wallet_id=team.organization.master_wallet.id,
            owner_name=team.organization.name,
            wallet_type='ORG',
            revenue_split=team.organization.get_revenue_split_for_team(team.id),
        )
    else:
        # Independent team
        return WalletInfo(
            wallet_id=team.owner.wallet.id,
            owner_name=team.owner.username,
            wallet_type='USER',
            revenue_split=None,  # No split for independent teams
        )
```

**Consumers:**
- `economy`: Prize distribution after tournament completion.
- `tournaments`: Display payout destination in registration confirmation.

**Break Risk:** **P0 - CRITICAL**  
Direct access to `team.owner.wallet` fails for Organization teams (owner is NULL).

---

### 4.3 TeamService.validate_roster(team_id, tournament_id)

**Purpose:** Validate team roster meets tournament requirements.

**Input:**
- `team_id` (int): Team primary key.
- `tournament_id` (int): Tournament primary key.

**Output:** `ValidationResult` dataclass
```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    roster_data: Dict[str, Any]  # Debug info
```

**Validation Checks:**
1. **Roster Size:** Team has minimum required players (game-specific: 5 for Valorant, 1 for eFootball).
2. **Game Passports:** All active lineup players have valid, non-expired Game IDs.
3. **Ban Status:** No players are suspended or banned platform-wide.
4. **Roster Lock Conflicts:** Team not locked in overlapping tournament.
5. **Game Match:** `team.game == tournament.game`.
6. **Active Lineup Set:** Team has configured TOC with active lineup (vNext only).

**Logic:**
```python
def validate_roster(team_id: int, tournament_id: int) -> ValidationResult:
    team = _get_team_from_either_system(team_id)
    tournament = Tournament.objects.get(id=tournament_id)
    errors = []
    warnings = []
    
    # Check 1: Game match
    if team.game_id != tournament.game_id:
        errors.append(f"Team game ({team.game.name}) does not match tournament game ({tournament.game.name})")
    
    # Check 2: Roster size
    active_members = team.memberships.filter(status='ACTIVE', role__in=['PLAYER', 'SUBSTITUTE']).count()
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
```

**Consumers:**
- `tournaments`: Registration eligibility check.
- `tournament_ops`: Pre-tournament validation dashboard.

**Break Risk:** **P0 - CRITICAL**  
Tournaments cannot validate eligibility without this centralized logic.

---

### 4.4 TeamService.get_authorized_managers(team_id)

**Purpose:** Retrieve all users authorized to manage team (register tournaments, edit roster, etc.).

**Input:**
- `team_id` (int): Team primary key.

**Output:** `List[UserInfo]`
```python
@dataclass
class UserInfo:
    user_id: int
    username: str
    email: str
    role: str  # OWNER, MANAGER, COACH
    permissions: List[str]  # ['register_tournaments', 'edit_roster', ...]
```

**Logic:**
```python
def get_authorized_managers(team_id: int) -> List[UserInfo]:
    team = _get_team_from_either_system(team_id)
    managers = []
    
    if team.organization:
        # Organization team: CEO + assigned Manager + Coaches with permissions
        ceo = team.organization.ceo
        managers.append(UserInfo(
            user_id=ceo.id,
            username=ceo.username,
            email=ceo.email,
            role='CEO',
            permissions=['ALL'],  # CEO has all permissions
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
        owner_membership = team.memberships.filter(status='ACTIVE', role='OWNER').first()
        if owner_membership:
            managers.append(UserInfo(
                user_id=owner_membership.profile.user.id,
                username=owner_membership.profile.username,
                email=owner_membership.profile.user.email,
                role='OWNER',
                permissions=['ALL'],
            ))
    
    return managers
```

**Consumers:**
- `tournaments`: Permission check before allowing registration.
- `notifications`: Determine who receives management-related notifications.

**Break Risk:** **P1 - HIGH**  
Incorrect permission checks could allow unauthorized tournament registrations.

---

### 4.5 TeamService.get_team_url(team_id)

**Purpose:** Generate correct URL for team profile (handles legacy/vNext routing).

**Input:**
- `team_id` (int): Team primary key.

**Output:** `str` (Absolute URL path)

**Logic:**
```python
def get_team_url(team_id: int) -> str:
    team = _get_team_from_either_system(team_id)
    
    if team.organization:
        # Organization team: /orgs/{org_slug}/teams/{team_slug}/
        return f"/orgs/{team.organization.slug}/teams/{team.slug}/"
    else:
        # Independent team: /teams/{slug}/
        return f"/teams/{team.slug}/"
```

**Consumers:**
- `notifications`: All notification links.
- `user_profile`: Team profile cards, activity feeds.
- `tournaments`: Bracket team links.

**Break Risk:** **P0 - CRITICAL**  
Hardcoded URLs (`/teams/{slug}/`) break for Organization teams.

---

### 4.6 TeamService.get_roster_members(team_id, filters=None)

**Purpose:** Retrieve team roster with filtering options.

**Input:**
- `team_id` (int): Team primary key.
- `filters` (dict, optional): Filter criteria.
  - `status` (str): 'ACTIVE', 'INACTIVE', 'SUSPENDED'.
  - `role` (str): 'PLAYER', 'SUBSTITUTE', 'COACH', 'MANAGER'.
  - `roster_slot` (str): 'STARTER', 'SUBSTITUTE'.

**Output:** `List[RosterMember]`
```python
@dataclass
class RosterMember:
    user_id: int
    username: str
    profile_id: int
    role: str  # Organizational role
    roster_slot: str  # STARTER, SUBSTITUTE, COACH, ANALYST
    in_game_role: Optional[str]  # Duelist, IGL, etc. (game-specific)
    game_passport: Optional[str]  # Game ID (Riot ID, Steam ID)
    passport_status: str  # VALID, EXPIRED, MISSING
    joined_at: datetime
    is_tournament_captain: bool
```

**Logic:**
```python
def get_roster_members(team_id: int, filters: dict = None) -> List[RosterMember]:
    team = _get_team_from_either_system(team_id)
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
        members.append(RosterMember(
            user_id=membership.profile.user.id,
            username=membership.profile.username,
            profile_id=membership.profile.id,
            role=membership.role,
            roster_slot=membership.roster_slot,
            in_game_role=membership.player_role,
            game_passport=passport.game_id if passport else None,
            passport_status='VALID' if passport and not passport.is_expired() else 'EXPIRED' if passport else 'MISSING',
            joined_at=membership.joined_at,
            is_tournament_captain=membership.is_tournament_captain,
        ))
    
    return members
```

**Consumers:**
- `tournaments`: Roster display in registration flow.
- `user_profile`: Team roster tab on profile pages.
- `tournament_ops`: Operations dashboard roster view.

**Break Risk:** **P1 - HIGH**  
Direct ORM queries on `team.memberships` bypass business logic filters.

---

### 4.7 TeamService.create_temporary_team(name, logo, game_id, creator_id)

**Purpose:** Quick team creation during tournament registration (for one-time participants).

**Input:**
- `name` (str): Team name.
- `logo` (str): Logo URL or uploaded file path.
- `game_id` (int): Game FK.
- `creator_id` (int): User creating the team.

**Output:** `TemporaryTeam` dataclass
```python
@dataclass
class TemporaryTeam:
    team_id: int
    status: str  # 'TEMPORARY'
    upsell_sent: bool  # Post-tournament conversion prompt
```

**Logic:**
```python
def create_temporary_team(name: str, logo: str, game_id: int, creator_id: int) -> TemporaryTeam:
    # vNext only (not available in legacy system)
    team = VNextTeam.objects.create(
        name=name,
        slug=slugify(name),
        logo=logo,
        game_id=game_id,
        owner_id=creator_id,
        is_temporary=True,  # Flag for post-tournament cleanup
        region=detect_region_from_user(creator_id),
    )
    
    # Create owner membership
    VNextTeamMembership.objects.create(
        team=team,
        profile_id=creator_id,
        role='OWNER',
        status='ACTIVE',
    )
    
    # Skip TOC initialization, ranking initialization (lightweight)
    
    return TemporaryTeam(
        team_id=team.id,
        status='TEMPORARY',
        upsell_sent=False,
    )
```

**Consumers:**
- `tournaments`: Tournament registration flow for unregistered users.

**Break Risk:** **P2 - MEDIUM**  
Feature not available until vNext deployment (Phase 3).

---

## 5. Data Field Assumptions

These fields are directly accessed by dependent apps. Changes require careful migration.

### 5.1 Team Model Fields

| Field Name | Type | Nullable | Legacy | vNext | Consumer Apps | Break Risk |
|------------|------|----------|--------|-------|---------------|------------|
| `id` | Integer PK | No | ✅ | ✅ | All apps | **P0** |
| `name` | CharField(100) | No | ✅ | ✅ | tournaments, notifications, user_profile, leaderboards | **P0** |
| `slug` | SlugField(100) | No | ✅ | ✅ | notifications, tournaments (URL generation) | **P0** |
| `game` | FK(Game) | No | ✅ | ✅ | tournaments (eligibility), leaderboards | **P0** |
| `logo` | ImageField | Yes | ✅ | ✅ | All apps (display) | **P1** |
| `region` | CharField(50) | **Yes (Legacy)** / **No (vNext)** | 🔁 | ✅ | leaderboards, tournaments | **P2** |
| `organization` | FK(Organization) | Yes | ❌ | ✅ | vNext only (new field) | **P1** |
| `owner` | FK(UserProfile) | **No (Legacy)** / **Yes (vNext Org)** | ✅ | 🔁 | economy (wallet access) | **P0** |
| `created_at` | DateTimeField | No | ✅ | ✅ | user_profile (history sorting) | **P2** |
| `status` | CharField | No | ✅ | ✅ | tournaments (eligibility) | **P1** |

**Critical Notes:**

1. **`captain` field does NOT exist as FK:**
   - Legacy: Computed via `@property` querying TeamMembership with `role='OWNER'`.
   - vNext: Same pattern (no FK).
   - **Break Risk:** P0 - Code assuming `team.captain` is an FK will fail.
   - **Mitigation:** All apps MUST use `TeamService.get_authorized_managers()` instead.

2. **`owner` field nullability change:**
   - Legacy: NOT NULL (Independent teams always have owner).
   - vNext Org: NULL (Organization owns team, not individual user).
   - **Break Risk:** P0 - Direct access to `team.owner.wallet` crashes for Org teams.
   - **Mitigation:** Use `TeamService.get_team_wallet()`.

3. **`organization` field:**
   - New field in vNext, does NOT exist in legacy.
   - **Break Risk:** P1 - Queries filtering by `organization` fail on legacy tables.
   - **Mitigation:** Service layer checks system type before querying.

---

### 5.2 TeamMembership Model Fields

| Field Name | Type | Nullable | Legacy | vNext | Consumer Apps | Break Risk |
|------------|------|----------|--------|-------|---------------|------------|
| `team` | FK(Team) | No | ✅ | ✅ | All apps (roster queries) | **P0** |
| `profile` | FK(UserProfile) | No | ✅ | ✅ | tournaments (eligibility), user_profile | **P0** |
| `status` | CharField | No | ✅ | ✅ | All apps (ACTIVE filtering) | **P0** |
| `role` | CharField | No | ✅ | ✅ | tournaments (permission checks) | **P1** |
| `roster_slot` | CharField | Yes | ✅ | ✅ | tournaments (starter vs sub) | **P1** |
| `player_role` | CharField | Yes | ✅ | ✅ | tournaments (display), user_profile | **P2** |
| `is_tournament_captain` | BooleanField | No | ✅ | ✅ | tournaments (captain designation) | **P1** |
| `joined_at` | DateTimeField | No | ✅ | ✅ | user_profile (history sorting) | **P2** |
| `left_at` | DateTimeField | Yes | ✅ | ✅ | user_profile (history) | **P2** |

**Critical Notes:**

1. **`status` enum values MUST remain unchanged:**
   - Required values: `ACTIVE`, `INACTIVE`, `SUSPENDED`, `INVITED`.
   - **Break Risk:** P0 - Tournaments filter by `status='ACTIVE'` in 50+ locations.
   - **Mitigation:** vNext uses identical enum values.

2. **`role` enum expansion:**
   - Legacy: `OWNER`, `CAPTAIN`, `PLAYER`, `SUBSTITUTE`, `COACH`.
   - vNext: Adds `MANAGER`, `ANALYST`, `SCOUT`.
   - **Break Risk:** P2 - Legacy code ignores new roles (safe fallback).
   - **Mitigation:** Service layer maps vNext roles to legacy-compatible equivalents.

3. **`is_tournament_captain` NOT to be confused with `role='CAPTAIN'`:**
   - `is_tournament_captain`: Boolean flag for tournament admin duties (one per team).
   - `role='CAPTAIN'`: Deprecated organizational role (legacy artifact).
   - **Break Risk:** P1 - Code conflating these two causes permission errors.
   - **Mitigation:** Service layer provides `get_tournament_captain(team_id)` method.

---

### 5.3 Computed Properties (Not Database Fields)

These are **@property** methods, not database columns. Direct attribute access triggers database queries.

**`team.captain` (Property, NOT FK):**
```python
@property
def captain(self):
    """Returns UserProfile of team owner/captain."""
    owner_membership = self.memberships.filter(status='ACTIVE', role='OWNER').first()
    return owner_membership.profile if owner_membership else None
```

**Problem:**
- **N+1 Query:** Every `team.captain` access executes a database query.
- **Null Returns:** If no OWNER membership exists, returns `None` (crashes on `.user` access).

**Dependent App Usage:**
- `tournaments`: `team.captain.user` (assumes FK chain).
- `notifications`: `team.captain.email` (assumes FK chain).

**Break Risk:** **P0 - CRITICAL**  
Code using `select_related('team__captain')` will fail (cannot select_related on property).

**Mitigation:**
```python
# WRONG (Legacy pattern):
team = Team.objects.get(id=team_id)
captain_email = team.captain.user.email  # ❌ N+1 query + potential crash

# CORRECT (Service pattern):
managers = TeamService.get_authorized_managers(team_id)
captain = next((m for m in managers if m.role in ['OWNER', 'CEO']), None)
captain_email = captain.email if captain else None  # ✅ Safe, no N+1
```

---

### 5.4 Related Managers

**`team.memberships` (Reverse FK relation):**
- Provides: `team.memberships.all()`, `team.memberships.filter(...)`.
- **Break Risk:** P0 - Removing FK from TeamMembership breaks this relation.
- **Usage:** 100+ locations across all apps.

**`team.ranking` (OneToOne relation):**
- Legacy: `TeamGameRanking` model.
- vNext: `TeamRanking` model.
- **Break Risk:** P1 - Different table names, same relation name.
- **Mitigation:** Service layer abstracts ranking access.

**`team.invites` (Reverse FK relation):**
- Provides: `team.invites.filter(status='PENDING')`.
- **Break Risk:** P2 - Used for invite capacity checks.
- **Usage:** Team creation flow, roster management.

---

## 6. URL & Routing Contracts

### 6.1 Named URL Routes

These Django URL names **MUST continue to work** during migration (hardcoded in 50+ locations).

**`teams:team_detail`:**
- Pattern: `/teams/<slug:slug>/`
- Used by: `notifications`, `user_profile`, `tournaments`.
- **Status:** ✅ Preserved (redirects to vNext URL if team migrated).

**`teams:team_roster`:**
- Pattern: `/teams/<slug:slug>/roster/`
- Used by: `user_profile`, `tournaments`.
- **Status:** ✅ Preserved.

**`teams:team_edit`:**
- Pattern: `/teams/<slug:slug>/edit/`
- Used by: `tournaments` (manager links).
- **Status:** ✅ Preserved.

**`teams:invite_accept`:**
- Pattern: `/teams/<slug:slug>/invite/<int:invite_id>/accept/`
- Used by: `notifications` (email links).
- **Status:** ✅ Preserved.

### 6.2 URL Redirect Strategy

**Phase 6 Deployment (Week 15):**

1. **Legacy URL Shim:**
```python
# deltacrown/urls.py
urlpatterns = [
    # vNext Organization URLs
    path('orgs/<slug:org_slug>/teams/<slug:team_slug>/', include('organizations.urls', namespace='org_teams')),
    
    # Legacy redirect shim
    path('teams/<slug:slug>/', legacy_team_redirect, name='legacy_team_redirect'),
    
    # Other legacy routes...
]

def legacy_team_redirect(request, slug):
    """Redirect legacy team URLs to vNext URLs if team migrated."""
    mapping = TeamMigrationMap.objects.filter(legacy_slug=slug).first()
    if mapping:
        team = VNextTeam.objects.select_related('organization').get(id=mapping.vnext_id)
        if team.organization:
            return redirect('org_teams:team_detail', org_slug=team.organization.slug, team_slug=team.slug)
        else:
            return redirect('teams:team_detail', slug=team.slug)  # Independent team (new structure)
    else:
        # Still in legacy system
        return legacy_team_detail_view(request, slug)
```

2. **Notification Service Update:**
```python
# Before (hardcoded):
url = f"/teams/{team.slug}/"

# After (service-based):
url = TeamService.get_team_url(team.id)
```

**Break Risk:** **P0 - CRITICAL**  
Not implementing redirects breaks ALL notification links sent before migration.

---

### 6.3 URL Preservation Requirements

**Forbidden Changes:**
- ❌ Cannot change `/teams/{slug}/` path structure.
- ❌ Cannot rename `teams:team_detail` URL name.
- ❌ Cannot remove legacy URL routes until Phase 8 (6+ months post-launch).

**Allowed Changes:**
- ✅ Add new `/orgs/{org_slug}/teams/{team_slug}/` routes.
- ✅ Redirect legacy URLs to new structure.
- ✅ Add query parameters to URLs (backward compatible).

---

## 7. Event / Signal / Notification Contracts

### 7.1 Django Signals

These signals are expected by dependent apps. vNext MUST emit equivalent signals.

**`post_save` on `Team` model:**
- **Listener:** `apps/teams/signals.py` → `initialize_team_ranking()`.
- **Payload:** `sender`, `instance`, `created`, `**kwargs`.
- **Action:** Creates `TeamGameRanking` record for new teams.
- **vNext Equivalent:** Must emit `post_save` on `organizations.Team` with same payload structure.

**`post_save` on `TeamMembership` model:**
- **Listener:** `apps/user_profile/signals/legacy_signals.py` → `handle_team_membership_save()`.
- **Payload:** `sender`, `instance`, `created`, `**kwargs`.
- **Action:** Updates user profile's team count, activity feed.
- **vNext Equivalent:** Must emit `post_save` on `organizations.TeamMembership`.

**`post_save` on `TeamInvite` model:**
- **Listener:** `apps/teams/signals.py` → `handle_team_invite_notification()`.
- **Payload:** `sender`, `instance`, `created`, `**kwargs`.
- **Action:** Sends notification to invitee.
- **vNext Equivalent:** Must emit equivalent signal or call NotificationService directly.

**Break Risk:** **P1 - HIGH**  
If vNext models don't emit signals, user profiles won't update, notifications won't send.

**Mitigation:**
```python
# vNext Team model:
class Team(models.Model):
    # ... fields ...
    
    class Meta:
        # Ensure signals are emitted
        pass

# In vNext app signals.py:
@receiver(post_save, sender='organizations.Team')
def initialize_team_ranking_vnext(sender, instance, created, **kwargs):
    """Mirror of legacy signal for vNext teams."""
    if created:
        TeamRanking.objects.create(team=instance, current_cp=0, tier='UNRANKED')
```

---

### 7.2 Notification Events

These notification types are hardcoded in dependent apps.

**`team_invite_sent`:**
- **Trigger:** TeamInvite created with status='PENDING'.
- **Recipients:** Invitee.
- **Payload:** `team_name`, `inviter_username`, `team_url`.
- **Status:** ✅ Must continue to work.

**`team_invite_accepted`:**
- **Trigger:** TeamInvite status changed to 'ACCEPTED'.
- **Recipients:** Team captain/owner.
- **Payload:** `team_name`, `invitee_username`, `team_url`.
- **Status:** ✅ Must continue to work.

**`roster_changed`:**
- **Trigger:** TeamMembership created/deleted.
- **Recipients:** All team members.
- **Payload:** `team_name`, `change_type`, `affected_user`, `team_url`.
- **Status:** ✅ Must continue to work.

**`tournament_registration_confirmed`:**
- **Trigger:** Tournament registration created.
- **Recipients:** Team managers.
- **Payload:** `team_name`, `tournament_name`, `tournament_url`, `team_url`.
- **Status:** ✅ Must continue to work.

**Break Risk:** **P0 - CRITICAL**  
Changing notification payload structure breaks email templates.

**Mitigation:**
- vNext NotificationService must use identical payload keys.
- Add new keys (e.g., `organization_name`) as optional, not required.

---

### 7.3 Webhook Events (Future)

**Status:** Not implemented in legacy, planned for vNext.

**Planned Events:**
- `team.created`
- `team.updated`
- `team.deleted`
- `roster.member_added`
- `roster.member_removed`

**Contract:** These are NEW features, no backward compatibility required.

---

## 9. Adapter Strategy

### 9.1 Read Routing Logic

**Phase 2-4:** All reads go to legacy `apps/teams`.

**Phase 5-7:** Dual-system reads (check migration status):
```python
def _get_team_from_either_system(team_id: int):
    """Internal helper: Route read to correct system."""
    if mapping := TeamMigrationMap.objects.filter(legacy_id=team_id).first():
        # Team has been migrated to vNext
        return VNextTeam.objects.select_related('organization', 'game').get(id=mapping.vnext_id)
    else:
        # Team still in legacy system
        return LegacyTeam.objects.select_related('game').get(id=team_id)
```

**Phase 8+:** All reads go to vNext `apps/organizations`.

**Break Risk:** **P1 - HIGH**  
Incorrect routing returns wrong data or crashes.

**Mitigation:**
- Comprehensive integration tests for dual-system period.
- Monitoring: Log every read with system source (legacy vs vNext).

---

### 9.2 Write Routing Logic

**Phase 2-4:** All writes go to legacy `apps/teams`.

**Phase 5-7:** Dual-write (write to BOTH systems):
```python
def update_team_name(team_id: int, new_name: str):
    """Update team name in both systems during migration."""
    if mapping := TeamMigrationMap.objects.filter(legacy_id=team_id).first():
        # Update vNext
        vnext_team = VNextTeam.objects.get(id=mapping.vnext_id)
        vnext_team.name = new_name
        vnext_team.save()
        
        # Also update legacy (read-only after Phase 5, but keep in sync)
        legacy_team = LegacyTeam.objects.get(id=team_id)
        legacy_team.name = new_name
        legacy_team.save()
    else:
        # Only in legacy system
        legacy_team = LegacyTeam.objects.get(id=team_id)
        legacy_team.name = new_name
        legacy_team.save()
```

**Phase 8+:** All writes go to vNext only (legacy tables archived).

**Break Risk:** **P0 - CRITICAL**  
Missing dual-write causes data divergence.

**Mitigation:**
- Database triggers to enforce dual-write at DB level (Phase 5).
- Nightly reconciliation script to detect divergence.

---

### 9.3 Forbidden Direct Access

**Starting Phase 2 (Week 5), the following is FORBIDDEN:**

❌ **Direct ORM imports in dependent apps:**
```python
# FORBIDDEN:
from apps.teams.models import Team, TeamMembership

# CORRECT:
from apps.organizations.services import TeamService
```

❌ **Direct property access on computed fields:**
```python
# FORBIDDEN:
captain = team.captain  # N+1 query, nullable
captain_email = team.captain.user.email  # Crashes if captain is None

# CORRECT:
managers = TeamService.get_authorized_managers(team_id)
captain = managers[0] if managers else None
captain_email = captain.email if captain else None
```

❌ **Hardcoded URLs:**
```python
# FORBIDDEN:
url = f"/teams/{team.slug}/"

# CORRECT:
url = TeamService.get_team_url(team.id)
```

❌ **Hardcoded status enum strings:**
```python
# FORBIDDEN:
active_members = team.memberships.filter(status='ACTIVE')  # Fragile

# CORRECT:
from apps.organizations.models import TeamMembership
active_members = team.memberships.filter(status=TeamMembership.Status.ACTIVE)
```

**Enforcement:**
- Code review checklist includes "No direct Team imports in non-team apps."
- CI pipeline linter flags forbidden imports.
- Phase 2 deployment includes deprecation warnings in legacy models.

---

### 9.4 Adapter Lifespan

**Dual-System Period:** Phase 5-7 (Weeks 13-16) = **4 weeks**.

**Legacy Table Retention:** Phase 8+ (Week 17 onward):
- Legacy tables marked as `_archived_` (renamed, not dropped).
- Read-only views maintained for forensic/audit purposes.
- Minimum retention: **6 months** post-migration.
- Permanent deletion: Requires stakeholder approval + legal review.

---

## 10. Hard Rules (Non-Negotiable)

### 10.1 Rules for Legacy Code (DO NOT CHANGE)

These legacy components **MUST NOT be modified** after Phase 2:

❌ **Cannot change `apps/teams/models/_legacy.py` schema:**
- No field additions, removals, or type changes.
- No changing enum values (e.g., `TeamMembership.Status.ACTIVE`).
- No changing FK relationships.
- **Rationale:** Would break in-flight transactions during migration.

❌ **Cannot delete legacy URL routes before Phase 8:**
- `/teams/{slug}/` routes must exist and redirect.
- Named routes (`teams:team_detail`) must resolve.
- **Rationale:** Old notification emails contain these links.

❌ **Cannot stop emitting legacy signals before Phase 8:**
- `post_save` on `Team`, `TeamMembership`, `TeamInvite` must continue.
- **Rationale:** Dependent apps rely on these for data sync.

❌ **Cannot change legacy database table names:**
- `teams_team`, `teams_membership`, `teams_invite` must remain.
- **Rationale:** External analytics tools query these tables directly.

**Violation Consequences:**
- Immediate rollback to previous deployment.
- Post-mortem required before re-deployment.

---

### 10.2 Rules for vNext Code (MUST IMPLEMENT)

These vNext requirements are **MANDATORY** for migration success:

✅ **Must implement all Service Layer methods (Section 3):**
- All 7 service methods must be implemented before Phase 2 deployment.
- **Rationale:** Dependent apps will immediately start using these.

✅ **Must emit equivalent Django signals:**
- `post_save` on vNext `Team`, `TeamMembership` models.
- **Rationale:** Maintains data sync with user_profile, notifications.

✅ **Must populate TeamMigrationMap during Phase 5:**
- Every migrated team must have `(legacy_id, vnext_id)` mapping.
- **Rationale:** Service layer routing depends on this.

✅ **Must maintain identical enum values:**
- `TeamMembership.Status`: `ACTIVE`, `INACTIVE`, `SUSPENDED`, `INVITED`.
- `TeamMembership.Role`: `OWNER`, `MANAGER`, `PLAYER`, `SUBSTITUTE`, `COACH`.
- **Rationale:** Dependent apps filter by these exact strings.

✅ **Must support dual-write during Phase 5-7:**
- All vNext writes must also update legacy tables.
- **Rationale:** Prevents data divergence during migration.

**Violation Consequences:**
- Migration blocked until compliance achieved.
- Phase advancement requires explicit technical lead approval.

---

### 10.3 Rules for Dependent Apps (MUST COMPLY)

These requirements apply to `tournaments`, `notifications`, `user_profile`, etc.:

✅ **Must refactor to use TeamService by Phase 2:**
- All direct `Team` imports must be removed.
- All queries must go through service layer.
- **Deadline:** Phase 2 deployment (Week 6).

✅ **Must use dynamic URL generation:**
- Replace hardcoded `/teams/{slug}/` with `TeamService.get_team_url()`.
- **Deadline:** Phase 6 deployment (Week 15).

✅ **Must handle nullable `team.organization`:**
- All code accessing `team.organization` must check for NULL.
- **Deadline:** Phase 3 deployment (Week 10).

✅ **Must not cache team data longer than 5 minutes:**
- TeamService responses may change during migration.
- **Rationale:** Prevents stale data display during dual-system period.

**Violation Detection:**
- Automated tests run in CI for every dependent app.
- Tests include "Service Layer Compliance Check."
- Failures block deployment.

---

### 10.4 Break-Glass Procedures

**If migration causes P0 incident:**

1. **Immediate Actions (0-15 minutes):**
   - Revert TeamService to legacy-only mode (disable vNext queries).
   - Disable new Organization features in UI (feature flag OFF).
   - Alert on-call engineer + technical lead.

2. **Investigation (15-60 minutes):**
   - Identify root cause (dual-write failure, routing bug, signal missing).
   - Assess data integrity (any lost/corrupted records).

3. **Rollback Decision (60-90 minutes):**
   - If data corruption detected: Full rollback to Phase N-1.
   - If isolated bug: Hotfix + re-deploy.
   - If design flaw: Halt migration, revise contract.

4. **Post-Mortem (24-48 hours):**
   - Document what broke, why, and how detected.
   - Update compatibility contract with new rules.
   - Add regression tests.

**Rollback Safety:**
- `TeamMigrationMap` table never deleted (permanent).
- Legacy tables maintained in read-write mode until Phase 8.
- Nightly backups of both legacy and vNext databases.

---

## Appendix A: Service Layer API Reference

**Complete method signatures for TeamService:**

```python
# Identity & Branding
def get_team_identity(team_id: int) -> TeamIdentity
def get_team_url(team_id: int) -> str

# Financial & Wallet
def get_team_wallet(team_id: int) -> WalletInfo

# Roster & Membership
def get_roster_members(team_id: int, filters: dict = None) -> List[RosterMember]
def get_authorized_managers(team_id: int) -> List[UserInfo]
def get_tournament_captain(team_id: int) -> Optional[UserInfo]

# Validation & Eligibility
def validate_roster(team_id: int, tournament_id: int) -> ValidationResult
def check_roster_lock(team_id: int) -> RosterLockStatus

# Team Creation
def create_independent_team(...) -> Team
def create_organization_team(...) -> Team
def create_temporary_team(...) -> TemporaryTeam

# Ranking & Stats
def get_team_ranking(team_id: int) -> TeamRankingInfo
def update_team_cp(team_id: int, cp_delta: int, reason: str) -> None

# Internal Helpers (not public API)
def _get_team_from_either_system(team_id: int) -> Team
def _is_legacy_team(team_id: int) -> bool
def _get_migration_mapping(team_id: int) -> Optional[TeamMigrationMap]
```

---

## Appendix B: Migration Checklist

**Phase 2 Deployment Checklist (Week 5-6):**

- [ ] TeamService implemented with all 7+ public methods.
- [ ] `tournaments` app refactored to use TeamService (no direct imports).
- [ ] Integration tests pass (100% coverage of service methods).
- [ ] Performance benchmarks show <10ms overhead per service call.
- [ ] Deprecation warnings added to legacy `Team` model imports.

**Phase 5 Deployment Checklist (Week 13-14):**

- [ ] Data migration scripts tested on staging (zero data loss).
- [ ] `TeamMigrationMap` table populated for all legacy teams.
- [ ] Dual-write enabled (writes go to both legacy + vNext).
- [ ] Reconciliation script running nightly (detects divergence).
- [ ] Rollback script tested (can revert to legacy-only mode).

**Phase 6 Deployment Checklist (Week 15):**

- [ ] URL redirect middleware deployed.
- [ ] All notification emails use `TeamService.get_team_url()`.
- [ ] Manual QA: Click 20+ notification links from pre-migration emails.
- [ ] Zero 404 errors in production logs.

**Phase 8 Deployment Checklist (Week 17-20):**

- [ ] Legacy tables renamed to `_archived_teams_team`, etc.
- [ ] Legacy admin panels hidden (not deleted).
- [ ] Documentation updated to reference vNext only.
- [ ] 30 days of stable operation (no P0/P1 incidents).
- [ ] Stakeholder approval for legacy table deletion (6+ months later).

---

## Appendix C: Contact & Escalation

**Questions about this contract:**
- Technical Lead: platform-architecture@deltacrown.com
- Slack: #team-migration-vnext

**Report contract violations:**
- Engineering Manager: eng-lead@deltacrown.com
- Incident Channel: #platform-incidents

**Request contract amendments:**
- Submit PR to this document with justification.
- Requires approval from: Tech Lead + Product Lead + 1 Senior Engineer.

---

## Document Maintenance

**Review Cadence:** Weekly during migration (Phase 2-8), monthly post-migration.  
**Amendment Process:** All changes require 2+ engineer sign-off.  
**Version History:**
- v1.0 (Jan 25, 2026): Initial compatibility contract.

---

**END OF COMPATIBILITY CONTRACT**