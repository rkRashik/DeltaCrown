# 📋 Team & Organization System vNext — Master Plan

**Document Version:** 1.3 ⚠️ **CORRECTED ARCHITECTURE**  
**Effective Date:** January 31, 2026  
**Owner:** Product Architecture Team  
**Status:** Authoritative Specification  
**Related Documents:**  
- [TEAM_ORG_ENGINEERING_STANDARDS.md](./TEAM_ORG_ENGINEERING_STANDARDS.md) ⚠️ **MANDATORY**
- [TEAM_ORG_PERFORMANCE_CONTRACT.md](./TEAM_ORG_PERFORMANCE_CONTRACT.md) ⚠️ **BINDING REQUIREMENTS**
- [TEAM_ORG_VNEXT_TRACKER.md](../Execution/TEAM_ORG_VNEXT_TRACKER.md) ⚠️ **EXECUTION TRACKER**
- [PLANNING_REALIGNMENT_SUMMARY.md](./PLANNING_REALIGNMENT_SUMMARY.md) ⚠️ **PHASE 8 CORRECTION**

**Changelog:**
- v1.3 (Jan 31, 2026): **CRITICAL CORRECTION** - Removed org-mandatory assumptions, restored teams-first architecture (Phase 8 realignment)
- v1.2 (Jan 25, 2026): Added Database Strategy Hard Rules (SUPERSEDED by v1.3 corrections)
- v1.1 (Jan 25, 2026): Added Quality Gates section per phase, engineering standards compliance requirements
- v1.0 (Jan 24, 2026): Initial master plan

---

## Table of Contents

1. [Context & Rebuild Decision](#1-context--rebuild-decision)
2. [Database Strategy & Constraints (Hard Rules)](#2-database-strategy--constraints-hard-rules)
3. [Core Vision & Philosophy](#3-core-vision--philosophy)
4. [Domain Definitions](#4-domain-definitions)
5. [Ownership, Roles & Permissions](#5-ownership-roles--permissions)
6. [Team Lifecycle](#6-team-lifecycle)
7. [Roster & Transfer System](#7-roster--transfer-system)
8. [Tournament Operations Center](#8-tournament-operations-center)
9. [Ranking System (DCRS)](#9-ranking-system-dcrs)
10. [Service Layer & Compatibility Contracts](#10-service-layer--compatibility-contracts)
11. [Migration Strategy (Parallel Build)](#11-migration-strategy-parallel-build)
12. [Development Phases & Milestones](#12-development-phases--milestones)
13. [Quality Gates by Phase](#13-quality-gates-by-phase)

---

## 1. Context & Rebuild Decision

### 1.1 Current State Assessment

The existing `apps/teams` application suffers from critical architectural issues identified in comprehensive audits:

**Technical Debt:**
- Dual model system (Legacy Team + Game-Specific Teams) with competing responsibilities
- Captain/Owner semantic confusion causing N+1 query problems
- Duplicate field definitions (e.g., `is_captain` defined twice in same model)
- Broken notification ORM queries using `select_related()` on non-FK fields
- Tournament integration using `IntegerField` instead of proper `ForeignKey` relationships
- 620 lines of "deprecated" code still actively used across 15+ files
- Missing referential integrity constraints leading to data consistency risks

**Business Logic Gaps:**
- No support for professional Organizations owning multiple teams
- Game Passport required for all roles (blocks non-playing team owners)
- No transfer/acquisition system for team ownership changes
- No revenue splitting mechanisms for organizational prize money
- Inadequate support for 1v1 games (eFootball, Fighting Games)

### 1.2 Strategic Decision: Parallel Build ("Strangler Fig" Pattern)

**Chosen Approach:** Build new `apps/organizations` alongside existing `apps/teams`.

**Rationale:**
- **Avoid catastrophic breakage:** Deleting `apps/teams` would cascade failures across `tournaments`, `user_profile`, `notifications`, `leaderboards`, and `tournament_ops`.
- **Clean slate architecture:** Build modern, debt-free code without legacy constraints.
- **Gradual migration:** Switch integration points one at a time after thorough testing.
- **Backward compatibility:** Maintain platform stability during transition.

**NOT Chosen:** Complete deletion and rebuild (would require 2+ weeks of error fighting before writing new features).

---

## 2. Database Strategy & Constraints (Core Principles)

### 2.1 ARCHITECTURAL REALITY: Dual Ownership Model

⚠️ **CRITICAL CORRECTION (v1.3)**: This section was updated to reflect **teams-first, organizations-optional** architecture per Phase 8 correction.

#### **CORE PRINCIPLE 1: Teams Can Be Independent OR Org-Owned**

**THE REALITY:**
- **Independent Teams**: Created by users, stand-alone competitive units (organization=NULL)
  - **Constraint**: ONE per game per user (if status=ACTIVE)
  - **Ownership**: User is Owner/Manager
  - **URL**: `/teams/<slug>/` (canonical)
  - **Wallet**: Personal (100% prize money)

- **Organization Teams**: Created under orgs, professional divisions (organization=FK)
  - **Constraint**: MULTIPLE per game allowed (Academy teams, etc.)
  - **Ownership**: Organization is Owner, User is Manager
  - **URL**: `/orgs/<org_slug>/teams/<team_slug>/` (canonical)
  - **Wallet**: Master Wallet (smart splits)

**Database Implementation:**
```python
class Team(models.Model):
    # Identity
    name = CharField(max_length=100)
    slug = SlugField(unique=True)
    game_id = IntegerField()  # FK to Game
    
    # CRITICAL: Dual ownership model
    organization = ForeignKey(
        Organization,
        null=True,        # ← NULLABLE (independent teams have NULL)
        blank=True,
        on_delete=SET_NULL,
        related_name="teams"
    )
    created_by = ForeignKey(User, on_delete=PROTECT)  # Creator/founder
    
    # Constraint: ONE independent team per game per user
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['created_by', 'game_id'],
                condition=Q(status='ACTIVE') & Q(organization__isnull=True),
                name='one_independent_team_per_game'
            ),
        ]
```

**Why This Architecture:**
1. **90% of users** are casual players (independent teams)
2. **10% are professional** orgs (multi-team management)
3. **Natural upgrade path**: Independent team → Acquired by org later
4. **Platform narrative**: "Grassroots to Glory" requires independent team support

#### **CORE PRINCIPLE 2: COMPLETELY NEW TABLES REQUIRED**

**MUST:**
- `apps/organizations` (vNext) uses **COMPLETELY NEW** database tables
- Table naming: `organizations_*` prefix mandatory
- Models define `db_table` explicitly in `Meta` class
- Zero dependencies on legacy `teams_*` schema

**MUST NOT:**
- Add columns to `teams_team`, `teams_membership`, `teams_invite`, `teams_teamgameranking`
- Modify legacy table types, constraints, or indexes
- Create FKs from vNext models to legacy models (except `TeamMigrationMap`)
- Import from `apps.teams.models` in vNext code

**Table Mapping:**

| vNext Model | Database Table | Legacy Table (DO NOT MODIFY) |
|------------|----------------|------------------------------|
| `Organization` | `organizations_organization` | N/A (new concept) |
| `Team` | `organizations_team` | `teams_team` |
| `TeamMembership` | `organizations_membership` | `teams_membership` |
| `TeamRanking` | `organizations_ranking` | `teams_teamgameranking` |
| `OrganizationMembership` | `organizations_org_membership` | N/A (new concept) |
| `TeamMigrationMap` | `organizations_migration_map` | N/A (bridge table) |

---

#### **CONSTRAINT 2: LEGACY READ-ONLY FROM PHASE 2**

**Timeline:**

| Phase | Legacy Write Behavior | vNext Write Behavior |
|-------|----------------------|---------------------|
| Phase 1 | READ-WRITE (frozen after Phase 2) | NOT DEPLOYED |
| Phase 2 | READ-WRITE (last writes) | NOT DEPLOYED |
| Phase 3+ | READ-ONLY (zero new inserts) | WRITE-PRIMARY (all new teams) |
| Phase 5-7 | READ-ONLY (dual-write sync only) | WRITE-PRIMARY (+ migration) |
| Phase 8 | ARCHIVED (legacy code deleted) | SOLE SYSTEM |

**Enforcement:**

**MUST:**
- Route all new team creations to `organizations_team` (Phase 3+)
- Preserve legacy data in frozen state (no deletes until Phase 8)
- Query both systems via service layer (Phase 5-7)

**MUST NOT:**
- Insert into `teams_team` after Phase 2 deployment
- Update legacy rows outside of Phase 5-7 dual-write sync
- Delete legacy data before Phase 8 cleanup

---

#### **CONSTRAINT 3: TEAMMIGRATIONMAP IS SOLE BRIDGE**

**Purpose:** Map legacy team IDs to vNext team IDs during Phase 5-7 parallel operation.

**Bridge Table Schema:**

```python
class TeamMigrationMap(models.Model):
    """
    Bridge between legacy teams_team and organizations_team.
    
    Retention Policy: Indefinite (minimum 12 months post-Phase 8).
    """
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
        indexes = [
            models.Index(fields=['legacy_team_id']),
            models.Index(fields=['vnext_team_id']),
        ]
```

**MUST:**
- Query `TeamMigrationMap` for all cross-system ID lookups
- Retain indefinitely (supports old notification links)
- Use for URL redirect middleware (Phase 6)

**MUST NOT:**
- Create direct FKs between vNext and legacy models
- Bypass migration map during dual-read phase (data corruption risk)
- Delete rows (breaks audit trail + old URLs)

---

### 2.2 Enforcement & Violation Handling

**Code Review Checklist:**
- [ ] No imports from `apps.teams.models` in vNext code
- [ ] All vNext models use `db_table = 'organizations_*'`
- [ ] No migrations touching `apps/teams` after Phase 2
- [ ] Service layer routes writes to vNext (Phase 3+)

**CI Pipeline Checks:**
- Fail build if legacy migrations detected
- Lint: Reject `from apps.teams.models import` in vNext
- Schema diff: Alert on any `teams_*` table changes

**Violation Consequences:**
1. **Development:** PR rejected, code review fails
2. **Production:** Immediate rollback, incident post-mortem
3. **Post-Incident:** Emergency cleanup sprint, update linter rules

**Authority:** Technical Lead has final say on database changes (no exceptions).

---

## 3. Core Vision & Philosophy

### 3.1 Design Principles

1. **Teams-First, Organizations-Optional** ⚠️ **CORRECTED v1.3**
   - **Independent Teams**: Standalone competitive units (90% of use cases)
   - **Organization Teams**: Professional divisions under business entities (10% of use cases)
   - **Natural Progression**: Independent team → Compete → Build reputation → Get acquired by org

2. **Managers Manage, Players Play**  
   - Non-combat roles (Owner, CEO, Manager, Coach) do NOT require Game Passports.
   - Only Players occupying active roster slots need verified Game IDs.

3. **Frictionless Creation**  
   - Team creation in under 30 seconds.
   - Minimal mandatory fields (Name + Game).
   - Progressive disclosure: Show simple options first, advanced features later.
   - **Organization linking is OPTIONAL** (toggle switch during creation).

4. **Professional Ecosystem Support**  
   - Organizations as first-class citizens, not afterthoughts.
   - Sub-brand strategy: Teams keep unique identities while inheriting Org benefits.
   - Real esports workflows: Acquisitions, contracts, revenue splits.

5. **Play-to-Earn-Access Model**  
   - Rankings are currency: High rank = Free tournament entry + Direct Invites.
   - Replace "pay-to-play" with "play-to-earn-status."

6. **Multi-Game Flexibility**  
   - Support both team games (5v5 Valorant) and solo games (1v1 eFootball).
   - Per-game roster management (one person can be in Valorant team AND eFootball team).

### 3.2 Success Metrics

- **Onboarding:** 90% of new teams complete creation flow without support tickets.
- **Casual Accessibility:** 80%+ of teams are independent (serving grassroots players).
- **Professional Adoption:** 50+ verified Organizations within 6 months.
- **Tournament Integration:** Zero registration failures due to team schema issues.
- **Performance:** All team list pages load in <200ms (no N+1 queries).
- **Data Integrity:** Zero orphaned records after tournament deletions.

---

## 4. Domain Definitions

### 4.1 Core Entities

#### **Independent Team (The Grassroots Unit)** ⚠️ **ADDED v1.3**

**Definition:** A standalone competitive team created and owned by a single user (typically casual players or friends).

**Examples:**
- Dhaka Killers (friends playing for fun)
- Null Boyz (semi-pro squad)
- Solo Pro (1v1 eFootball player)

**Properties:**
- **Ownership**: User is Owner + Manager
- **Wallet**: Personal (100% prize money to creator)
- **Constraints**: ONE per game per user (prevents farming)
- **URL**: `/teams/<slug>/`
- **Database**: `Team.organization = NULL`

**Lifecycle**:
1. User creates independent team (30 seconds)
2. Competes in tournaments, builds reputation
3. May receive acquisition offer from org
4. If accepted, becomes Organization Team

#### **Organization (The Brand)**

**Definition:** A verified business entity that owns multiple teams across different games.

**Examples:**
- SYNTAX (owns Protocol V for Valorant + Syntax FC for eFootball)
- Cloud9 Bangladesh
- GamerHub Esports

**Properties:**
- Legal name and brand identity (logo, colors, sponsors)
- Master Wallet for consolidated prize money
- Verification status (Verified Org Badge)
- CEO/Owner (single User)
- Multiple Staff roles (Managers, Scouts, Analysts)

**Lifecycle:**
- Created by Users who want to manage professional esports operations
- Can acquire existing Independent Teams
- Cannot be deleted while owning active teams
- Maintains historical trophy room aggregating all team achievements

#### **Team (The Squad)**

**Definition:** The competitive unit that registers for tournaments and plays matches.

**Types:**
1. **Organization Team:** Owned by an Organization, managed by appointed Manager.
2. **Independent Team:** Owned by a single User (Captain/Owner).

**Properties:**
- Unique name and logo (sub-brand identity)
- Game specification (e.g., Valorant, eFootball)
- Region/Country base (identity, not server)
- Roster (Players + Substitutes)
- Tournament Operations Center settings
- Ranking data (Crown Points, Tier)

**Constraints:**
- One User can own max 1 Independent Team per game title.
- One Organization can own unlimited Teams per game (e.g., Main + Academy).
- Team names must be unique within game context.

#### **TeamMembership (The Role Assignment)**

**Definition:** Links a User to a Team with specific roles and permissions.

**Role Categories (4 Orthogonal Systems):**

1. **Organizational Role** (Leadership/Management):
   - `OWNER`: Full control (Independent Teams only)
   - `MANAGER`: Operational control (roster, registration)
   - `COACH`: View-only, scrim scheduling
   - `PLAYER`: Combat role only
   - `SUBSTITUTE`: Bench player

2. **Tournament Captain Flag**:
   - `is_tournament_captain` (Boolean): Designated captain for admin duties (Ban/Pick, check-in)
   - One per team maximum

3. **Roster Slot** (Availability):
   - `STARTER`: Active lineup
   - `SUBSTITUTE`: Bench/reserve
   - `COACH`: Staff (non-playing)
   - `ANALYST`: Staff (non-playing)

4. **In-Game Tactical Role** (Game-Specific):
   - Valorant: Duelist, IGL, Sentinel, Controller, Initiator
   - CS2: AWPer, IGL, Entry Fragger, Support, Lurker
   - eFootball: Solo Athlete (no sub-roles)

**Status:**
- `ACTIVE`: Currently on roster
- `INACTIVE`: Left team (historical record)
- `SUSPENDED`: Temporarily removed
- `INVITED`: Pending acceptance

### 4.2 Domain Rules
**Exception:** Non-playing roles (Manager, Coach) have no game restrictions.

#### **The Game Passport Requirement**

**Required:**
- Users occupying PLAYER or SUBSTITUTE slots in STARTER/ACTIVE status.
- Passport must match team's game (Riot ID for Valorant, Steam ID for CS2, etc.).

**Not Required:**
- Owners, Managers, Coaches, Analysts.
- Players in INVITED status (required upon acceptance).

**Validation Timing:**
- Checked when: Joining team, moving to STARTER slot, tournament registration.
- Enforcement: System blocks action and prompts user to link Game ID.

#### **Region vs. Server**

**Region (Team Identity):**
- Set during team creation (e.g., "Bangladesh," "India").
- Represents team's home/origin for display and rankings.
- Immutable after creation (requires admin intervention to change).

**Server (Operational Preference):**
- Set in Tournament Operations Center (e.g., "Singapore," "Mumbai").
- Used for matchmaking and tournament server selection.
- Can be changed anytime by Manager.

---

## 5. Ownership, Roles & Permissions

### 5.1 Permission Matrix

| Action | Owner/CEO | Manager | Coach | Player |
|--------|-----------|---------|-------|--------|
| Delete Team/Org | ✅ | ❌ | ❌ | ❌ |
| Edit Team Name/Logo | ✅ | ✅ | ❌ | ❌ |
| Invite/Kick Members | ✅ | ✅ | ❌ | ❌ |
| Register for Tournament | ✅ | ✅ | ❌ | ❌ |
| Edit TOC Settings | ✅ | ✅ | ✅ | ❌ |
| Withdraw Prize Money | ✅ | ❌ | ❌ | ❌ |
| Schedule Scrims | ✅ | ✅ | ✅ | ❌ |
| View Team Dashboard | ✅ | ✅ | ✅ | ✅ |
| Leave Team Voluntarily | ✅ | ✅ | ✅ | ✅ |

### 5.2 Organization-Specific Permissions

**CEO (Organization Owner):**
- Create/delete teams under Organization
- Assign Managers to teams
- Access Master Wallet (all withdrawals)
- Set Smart Contract rules (revenue splits)
- Initiate team acquisitions
- Upload global sponsor logos

**Manager (Team-Level):**
- Day-to-day team operations
- Roster management
- Tournament registration
- **Cannot access** Master Wallet
- **Cannot transfer** team ownership
- May have allocated "Petty Cash" budget from CEO

**Scout (Organization Staff):**
- View-only access to player stats across platform
- Create shortlists for recruitment
- **Cannot** edit rosters or access financials
- **Cannot** register teams for tournaments

### 5.3 Permission Enforcement

**Implementation:**
- Role-Based Access Control (RBAC) decorators on all views/APIs.
- Database-level constraints for critical actions (one OWNER per Independent Team).
- Audit logging for all permission-sensitive actions.

**Security Rules:**
- All ownership changes require OTP verification.
- Wallet withdrawals >5,000 BDT require KYC verification.
- Manager assignments require acceptance notification.

---

## 6. Team Lifecycle

### 6.1 Creation Flow (Fast-Track: <30 Seconds)

⚠️ **UPDATED v1.3**: Clarified independent vs organization team creation paths.

#### **Step 1: Identity (Mandatory)**

**Fields:**
- **Team Name** (unique within game context)
- **Game Selection** (grid view: Valorant, CS2, Dota 2, MLBB, PUBG, Free Fire, eFootball, FC26, CODM)
- **Organization Link** (toggle switch - **OPTIONAL**):
  - **OFF** (default): Creates **Independent Team** (organization=NULL)
  - **ON**: Dropdown to select User's owned Organizations

**Validation Logic**:

**If Independent Team (Toggle OFF)**:
- Check: Does User already own an **independent** team for selected game?
  - Query: `Team.objects.filter(created_by=user, game_id=game, organization__isnull=True, status=ACTIVE)`
  - **If EXISTS**: BLOCK creation. Error: *"You already have an independent team for this game. Join an Organization to create additional teams."*
  - **If NOT EXISTS**: ALLOW creation.

**If Organization Team (Toggle ON)**:
- Check: Does selected Org already have a team for this game?
  - Query: `Team.objects.filter(organization=org, game_id=game, status=ACTIVE)`
  - **If EXISTS**: WARN (but allow): *"This organization already has a Valorant team. Consider naming this 'Academy' or 'Black' division."*
  - **If NOT EXISTS**: ALLOW creation.

**System Action:**
- Generate unique slug from team name.
- Auto-detect User's country from IP for Region field.

#### **Step 2: Base (Mandatory with Smart Default)**

**Field:**
- **Region/Country Base** (dropdown: Bangladesh, India, Pakistan, Nepal, etc.)

**Smart Default:**
- Pre-filled with IP-detected country.
- User clicks "Next" (90% case) or manually changes.

#### **Step 3: Setup (Skippable)**

**Fields:**
- **Logo/Banner Upload** (or skip → system generates initials placeholder)
- **Manager Assignment**:
  - Radio A: "I will manage this team" (default)
  - Radio B: "Assign a Manager" (email input)
- **Org Branding** (only if Organization linked):
  - Checkbox: `[ ] Use Organization Logo instead of custom logo?` (default: unchecked)

**Visual Design:**
- Large "Skip for Later" button.
- Completion progress bar: "Profile Strength: 30%" after creation.

#### **Step 4: Launch**

**Action:** User clicks **"Create Team"**.

**System Operations**:

**For Independent Teams (organization=NULL)**:
1. Create `Team` record:
   - `organization` = NULL
   - `created_by` = User
   - `status` = ACTIVE
2. Create `TeamMembership` record:
   - User as OWNER (role=OWNER, status=ACTIVE)
   - No separate Manager needed (Owner IS Manager for independent teams)
3. Initialize `TeamGameRanking` (CP: 0, Tier: UNRANKED)
4. **Wallet**: Link to User's personal wallet
5. **URL**: `/teams/<slug>/` (canonical)

**For Organization Teams (organization=FK)**:
1. Create `Team` record:
   - `organization` = FK to selected Org
   - `created_by` = User (historical record)
   - `status` = ACTIVE
2. Create `TeamMembership` records:
   - User as MANAGER (role=MANAGER, status=ACTIVE)
   - Org CEO automatically added as OWNER
3. Initialize `TeamGameRanking` (CP: 0, Tier: UNRANKED)
4. **Inherit verification status** from Organization
5. **Wallet**: Link to Organization Master Wallet
6. **URL**: `/orgs/<org_slug>/teams/<team_slug>/` (canonical)

**Common Post-Creation**:
- Send notification to Manager (if different from creator).
- Initialize empty Tournament Operations Center settings.
- Redirect to Team Dashboard with empty state prompts:
  - "Profile Strength: 30% Complete"
  - Primary CTA: "Your Roster is Empty. Start Scouting!"
  - Secondary prompts: Upload logo, fill TOC settings.

### 6.2 Acquisition Protocol (Org Acquires Independent Team)

**Scenario:** Organization CEO wants to sign an existing Independent Team.

#### **Initiation Phase**

**Actor:** Organization CEO  
**Steps:**
1. Navigate to Org Dashboard → "Acquisitions" tab.
2. Search for team by name or ID (e.g., "Null Boyz").
3. Click "Send Acquisition Request."
4. System validates:
   - Target is Independent Team (not already owned by Org).
   - Org doesn't have ownership conflicts.
   - Target team not locked in active tournament.

#### **Negotiation Phase**

**Actor:** Independent Team Owner  
**Notification:** Email + in-app notification:
- *"SYNTAX has requested to acquire your team, Null Boyz."*

**Terms Screen:**
```
🔄 Acquisition Offer from SYNTAX

📋 Terms:
• Ownership will transfer to: SYNTAX
• Your new role will be: Team Manager
• Current roster: Preserved (all players remain)
• All future prize money: Goes to SYNTAX Master Wallet
• Team name & logo: Preserved
• Ranking & history: Preserved

⚠️ This action cannot be undone without CEO approval.

[Accept & Transfer]  [Decline Offer]
```

#### **Execution Phase**

**If Accepted:**
1. `Team.organization` → Set to SYNTAX.
2. `Team.owner` → Removed (NULL or archived).
3. Previous Owner → Added as `TeamMembership` with role=MANAGER.
4. Team inherits Org verification badge.
5. Wallet redirect: Future prizes → Org Master Wallet.
6. Audit log entry: "Team acquired by SYNTAX on [timestamp]."
7. Notifications sent to:
   - Org CEO: "Acquisition successful."
   - All team members: "Your team is now part of SYNTAX."

**If Declined:**
- Acquisition request archived.
- Notification to Org CEO: "Acquisition declined by Null Boyz owner."

### 6.3 Team Deletion

#### **Independent Team Deletion**

**Actor:** Team Owner  
**Preconditions:**
- No active tournament registrations.
- No pending financial transactions.

**Action:** Owner clicks "Delete Team" → Confirmation modal with password re-entry.

**System Operations:**
1. Soft-delete `Team` record (status: DELETED, archived).
2. Set all `TeamMembership` records to INACTIVE.
3. Archive ranking data (preserve historical leaderboard entries).
4. Notify all members: "Team has been disbanded."
5. Maintain tournament participation history (cannot be erased).

#### **Organization Team Deletion**

**Actor:** Organization CEO  
**Additional Validation:**
- Cannot delete if team has <30 days history (prevent impulsive decisions).
- Requires second confirmation step.

**System Operations:** Same as Independent, plus:
- Aggregate trophy count recalculated for Org.
- Team's historical achievements remain in Org Trophy Room (marked as "Disbanded Division").

---

## 7. Roster & Transfer System

### 7.1 Player Status Types

Every User has a "Competitive Status" per game, visible on their profile:

1. **Free Agent:** Not on any roster for that game. Eligible to join immediately.
2. **Contracted (Active):** On an active roster. Cannot join another team unless released.
3. **Restricted:** Banned or suspended. Cannot join any team.

### 7.2 Movement Workflows

#### **Scenario 1: Voluntary Departure (Resignation)**

**Actor:** Player  
**Action:** Clicks "Leave Team" in dashboard.

**Validation:**
- **Check:** Is team currently in active tournament (roster locked)?
  - **YES** → Block action. Error: *"You cannot leave while the team is in an active tournament run."*
  - **NO** → Proceed.

**System Operations:**
1. Set `TeamMembership.status` → INACTIVE.
2. Set `TeamMembership.left_at` → Current timestamp.
3. Update `TeamMembership.left_reason` → "Voluntary Resignation."
4. Notify Manager: *"[Player] has left the team."*
5. Create `TransferLog` entry.
6. Update team roster count.

#### **Scenario 2: The Kick (Release)**

**Actor:** Manager/Owner  
**Action:** Clicks "Remove from Roster" for specific player.

**Validation:** Same roster lock check as resignation.

**System Operations:**
1. Set `TeamMembership.status` → INACTIVE.
2. Set `TeamMembership.left_at` → Current timestamp.
3. Set `TeamMembership.left_reason` → "Released by Management."
4. Notify Player: *"You have been released from Protocol V."*
5. Create `TransferLog` entry.

#### **Scenario 3: The Transfer (Poaching)**

**Scenario:** Protocol V wants a player currently in Null Boyz.

**Actor:** Protocol V Manager  
**Steps:**
1. Navigate to player's profile.
2. Click "Send Transfer Offer."
3. Input optional message: *"We'd love to have you for our Major push."*

**Validation:**
- Target player is in ACTIVE status on another team.
- Receiving team has roster capacity.
- Target player not locked in tournament.

**Notification to Player:**
```
🔄 Transfer Offer from Protocol V

Current Team: Null Boyz
Offered By: Protocol V
Message: "We'd love to have you for our Major push."

⚠️ Accepting will automatically remove you from Null Boyz.

[View Offer Details]  [Accept Transfer]  [Decline]
```

**If Player Accepts:**
1. Auto-remove from Null Boyz (set membership INACTIVE).
2. Auto-add to Protocol V (create new ACTIVE membership).
3. Create `TransferLog` entries for both teams.
4. Notify:
   - Null Boyz Manager: *"[Player] has transferred to Protocol V."*
   - Protocol V Manager: *"[Player] accepted your transfer offer."*

**Future Enhancement (Post-MVP):**
- Add "Manager Approval Required" flag for contracted players.
- Support buyout fees (transfer from Org wallet to releasing team's wallet).

### 7.3 The "Solo-Squad" Architecture (1v1 Games)

**Challenge:** Represent 1v1 games (eFootball, FC26, Fighting Games) where individuals play solo but represent a team/organization.

#### **Solution: The Stable Model**

**Concept:**
- Even for 1v1 games, create a `Team` entity.
- Roster contains multiple solo players (e.g., "Syntax FC" has Player A, Player B, Player C).
- These players do NOT play together; they play parallel matches wearing the team's brand.

**Example:**
- **Organization:** SYNTAX
- **Team:** Syntax FC (Game: eFootball)
- **Roster:**
  - Player A (Rank: Diamond, Win Rate: 75%)
  - Player B (Rank: Platinum, Win Rate: 68%)
  - Player C (Rank: Gold, Win Rate: 62%)

#### **Display Changes (UI)**

**Team Profile for 5v5 Game (Valorant):**
- Shows "Active Lineup" with roles (IGL, Duelist, Sentinel, etc.).
- Layout: Grid/card format with tactical positions.

**Team Profile for 1v1 Game (eFootball):**
- Shows "Athletes List."
- Layout: Table format with columns: Player Name | Rank | Win Rate | Matches Played.
- Visual: Like a Tennis or MMA Gym roster.

#### **Tournament Registration for Solos**

**Process:**
1. Manager selects "Syntax FC" for tournament.
2. System detects game format: 1v1_SOLO.
3. System prompts: *"Which athlete is entering this slot?"*
4. Manager selects "Player A."
5. Bracket entry displays:
   - Name: "Syntax FC (Player A)" OR "Player A [SYN]"
   - Team affiliation visible for branding.

**Ranking Points Calculation:**
- Crown Points (CP) earned by **Syntax FC** (the Team entity).
- Player A's individual stats updated.
- Organization's "Empire Score" aggregates all team CP.

**Multi-Entry Rule:**
- Tournament Organizer sets: "Max Entries Per Org."
- Scenario A (Strict): Limit = 1 → Manager picks best athlete.
- Scenario B (Open): Limit = Unlimited → Manager registers Player A, B, and C.
- Bracket handles "Team Kill" scenarios (two athletes from same team facing off).

### 7.4 Free Agent Market (LFT/LFP)

#### **For Players: "Open to Work"**

**Feature:** Profile setting toggle: `[ ] Looking for Team`

**Inputs:**
- **Role:** (e.g., Duelist, IGL, Support, Solo Athlete)
- **Region:** (e.g., Dhaka, Chittagong, Rajshahi)
- **Language:** (e.g., Bangla, English)
- **Availability:** (e.g., Weekdays 8pm-12am)

**Visibility:**
- Player appears in public "Scouting Grounds" list.
- Searchable/filterable by game, role, region.
- Shows player stats: Rank, Win Rate, Games Played.

#### **For Teams: "Recruitment Post"**

**Feature:** Manager creates "Help Wanted" ad.

**Inputs:**
- **Headline:** "Looking for Aggressive Duelist for Tier B Tournament"
- **Requirements:** "Must be Diamond 3+, available weekends, fluent Bangla"
- **Expiration:** 7 days (auto-renewed or archived)

**Application Flow:**
1. Free Agent sees recruitment post.
2. Clicks "Apply" → Optional cover message.
3. Manager sees list of applicants with profiles.
4. Manager clicks "Invite" → Standard invitation flow.

---

## 8. Tournament Operations Center (TOC)

**Purpose:** Pre-configured settings allowing one-click tournament registration (eliminates repetitive forms).

**Location:** Dedicated tab in Team Dashboard.

### 8.1 TOC Modules

#### **Module A: Roster Snapshot (Active Lineup)**

**Feature:** Drag-and-drop interface for setting primary roster.

**5v5 Games:**
- Select 5 players from member list → Assign to "Active Lineup."
- Assign in-game roles (IGL, Duelist, etc.).
- Validation: All 5 must have valid Game Passports → Visual feedback (Green checkmark / Red warning).

**1v1 Games:**
- Select primary athlete → Mark as "Tournament Ready."
- Optional: Set secondary athlete as backup.

**Substitute Management:**
- Designate up to 2 substitute players.
- Substitutes also require Game Passports (validated on save).

**Benefit:**
- Tournament registration pulls this pre-validated roster automatically.
- No scrambling to collect Game IDs during registration window.

#### **Module B: Logistics & Settings**

**Fields:**

1. **Preferred Server** (not identity):
   - Dropdown: Singapore, Mumbai, Tokyo, Seoul.
   - Used for: Matchmaking and tournament seeding preferences.
   - Can differ from Team Region.

2. **Emergency Contact**:
   - Discord ID (e.g., `captain#1234`)
   - Phone Number (with country code)
   - For: Tournament admins to reach team urgently.

3. **Communication Language**:
   - Primary: Bangla, English, Hindi, etc.
   - For: Tournament broadcast/admin communication preferences.

4. **Payout Preference** (read-only for Org teams):
   - **Independent Team:** User Wallet (editable).
   - **Organization Team:** Org Master Wallet (locked, managed by CEO).

**Validation:**
- All fields optional EXCEPT Active Lineup (required for tournament eligibility).
- Settings auto-save on change (no manual "Save" button).

#### **Module C: Tournament History Integration** (Future)

**Planned Features:**
- Display past tournament participations and results.
- Show upcoming registered tournaments with countdown timers.
- Quick links to tournament dashboards.

### 8.2 Registration Flow Using TOC

**Scenario:** Manager registers team for "Winter Major 2026."

**Standard Flow (with TOC):**
1. Click "Register" on tournament page.
2. System auto-fills:
   - Team name, logo.
   - Active lineup from TOC (5 players with roles).
   - Emergency contact.
   - Preferred server.
3. Manager reviews → Clicks "Confirm Registration" → Done in 10 seconds.

**Without TOC (Legacy Flow):**
1. Fill team name, logo.
2. Manually input 5 Game IDs.
3. Manually assign roles.
4. Input Discord ID, phone number.
5. Takes 3-5 minutes, error-prone.

---

## 9. Ranking System (DCRS)

**Full Name:** DeltaCrown Ranking System  
**Core Metric:** Crown Points (CP)  
**Philosophy:** Rankings are currency—high rank = savings (free entry) + prestige (direct invites).

### 9.1 The Point Calculation System

**Formula:** Base Points × Tier Multiplier = Total CP

#### **A. Tournament Tiers (The Multipliers)**

| Tier | Criteria | Example | Multiplier |
|------|----------|---------|------------|
| **Tier S (Crown)** | Official DeltaCrown Majors, >50k BDT Prize, LAN Finals | *Delta Winter Championship* | **100x** |
| **Tier A (Elite)** | Verified Org tournaments, >10k BDT Prize | *GamerHub Monthly Cup* | **50x** |
| **Tier B (Challenger)** | Community cups, weekly events | *Weekend Skirmish* | **20x** |
| **Tier C (Grassroots)** | Daily scrims, small user-hosted events | *Daily Scrim #45* | **5x** |

**Tier Assignment:** Determined by Tournament Organizer during event creation (subject to admin approval for Tier S/A).

#### **B. Placement Points (The Base)**

| Placement | Base Points |
|-----------|-------------|
| 1st Place | 100 |
| 2nd Place | 75 |
| Top 4 | 50 |
| Top 8 | 25 |
| Participation | 5 (must play ≥1 match) |

**Example Calculation:**
- **Protocol V** wins **Tier A** tournament.
- Calculation: 100 (1st) × 50 (Tier A) = **5,000 CP**.

### 9.2 The Visual Hierarchy (Tiers & Badges)

| Tier | CP Range | Badge Visual | Perks |
|------|----------|--------------|-------|
| **Unranked** | 0-50 | Grey Circle | None |
| **Bronze** | 50-500 | Rusty Shield | — |
| **Silver** | 501-1,500 | Polished Metal | — |
| **Gold** | 1,501-5,000 | Shining Gold | Verified Team Application |
| **Platinum** | 5,001-15,000 | Teal Gem | Scrim Priority Queue |
| **Diamond** | 15,001-40,000 | Blue Refractive | **Direct Invites (Tier B)** |
| **Ascendant** | 40,001-80,000 | Red/Crimson | **Direct Invites (Tier A)** |
| **CROWN** | Top 1% (Regional) | **Animated Purple Crown** | **Direct Invites (Tier S) + Homepage Feature** |

**Badge Display:**
- Appears on Team Profile header.
- Shown in tournament lobbies and brackets.
- Animated glow effect for Diamond+ tiers.

### 9.3 The "Direct Invite" Ecosystem

**Killer Feature:** Replace "pay-to-play" with "play-to-earn-access."

#### **How It Works**

**Eligibility:**
- Teams in **Top 5% of their region/game** (Diamond tier or above).

**Benefits:**
1. **Skip Qualifiers:** Directly advance to Main Event/Group Stage.
2. **Fee Waiver:** $0 entry fee (organizer-subsidized or platform-credited).

**Organizer Incentive:**
- Having "Protocol V" (Rank #1) in tournament brings viewers and prestige.
- Platform compensates organizer via credits or revenue share boost.

#### **User Journey**

**New Team:**
- Pays entry fees for grassroots tournaments.
- Plays Open Qualifiers (6+ rounds).

**Mid-Tier Team:**
- Grinds Tier B/C tournaments to earn CP.
- Slowly climbs Silver → Gold → Platinum.

**Top-Tier Team:**
- Receives email: *"You have been Directly Invited to the Winter Major. Accept Invitation?"*
- No fee, no qualifiers, straight to main stage.

### 9.4 Advanced Mechanics

#### **A. Giant Slayer Bonus ⚔️**

**Trigger:** Lower-ranked team defeats higher-ranked team.

**Calculation:**
- Tier difference ≥2 (e.g., Silver beats Diamond).
- **Winner Bonus:** +500 CP.
- **Loser Penalty:** -200 CP.

**Effect:**
- Creates viral moments and storylines.
- Prevents rank camping (top teams must defend status).

#### **B. Hot Streak 🔥**

**Trigger:** Win 3 official matches in a row.

**Benefits:**
- 🔥 icon displayed next to team name.
- **1.2x CP multiplier** while streak active.
- Breaks on loss or 7-day inactivity.

**Effect:**
- Encourages continuous play.
- Rewards consistency over isolated wins.

#### **C. Regional Leaderboards**

**Categories:**
- "Top 10 in Dhaka"
- "Top 10 in Chittagong"
- "Top 10 in Bangladesh"
- "South Asia Rankings"

**Effect:**
- Casual teams gain local fame even if not #1 globally.
- Sponsorship opportunities for regional dominance.

### 9.5 The Organization Power Ranking

**Metric:** "Empire Score"

**Calculation:** Sum of **Top 3 Performing Teams'** CP (weighted).

**Formula:**
```
Empire Score = (Best Team CP × 1.0) + (2nd Best Team CP × 0.75) + (3rd Best Team CP × 0.5)
```

**Example:**
- **SYNTAX:**
  - Protocol V (Valorant): 50,000 CP
  - Syntax FC (eFootball): 30,000 CP
  - Syntax Academy (Valorant): 15,000 CP
- **Empire Score:** (50,000 × 1.0) + (30,000 × 0.75) + (15,000 × 0.5) = **80,000**

**Visual:**
- Leaderboard: "Top Esports Organizations in Bangladesh"
- Organization Profile displays Empire Score with breakdown.
- High Empire Score → Golden Border on profile.

**Benefit:**
- Incentivizes Orgs to expand into multiple games.
- Orgs with diverse portfolios rank higher than single-game specialists.

### 9.6 Seasonal Resets (The Loop)

**Season Duration:** 4 months (Winter, Summer, Autumn).

**Soft Reset Mechanics:**
- At season end: All teams lose **50% of CP**.
- Example: Team with 10,000 CP → 5,000 CP at season start.

**Purpose:**
- Allows new teams to catch up.
- Prevents permanent dominance by early adopters.
- Maintains competitive hierarchy (top teams still start higher).

**Hall of Fame:**
- Season #1 Champion permanently listed in "History" tab.
- Example: *"Season 1 Champion: Protocol V (50,000 CP)"*

### 9.7 Decay Rule (Anti-Camping)

**Mechanism:**
- Teams lose **5% of CP** every 7 days of inactivity.
- **Activity Definition:** Playing ≥1 official match.

**Example:**
- Team with 20,000 CP inactive for 2 weeks:
  - Week 1: 20,000 → 19,000 (-5%)
  - Week 2: 19,000 → 18,050 (-5%)

**Purpose:**
- Forces top teams to play regularly.
- Prevents "camping" the #1 spot.
- Keeps leaderboard dynamic.

### 9.8 Technical Implementation

#### **TeamRanking Model**

```python
class TeamRanking(models.Model):
    team = models.OneToOneField(Team, related_name='ranking')
    current_cp = models.IntegerField(default=0)
    season_cp = models.IntegerField(default=0)  # Resets every season
    all_time_cp = models.IntegerField(default=0)  # Never resets
    tier = models.CharField(choices=TIERS, default='UNRANKED')
    global_rank = models.IntegerField(null=True)
    regional_rank = models.IntegerField(null=True)
    
    # Trend Tracking
    rank_change_24h = models.IntegerField(default=0)  # e.g., +2 (moved up 2 spots)
    rank_change_7d = models.IntegerField(default=0)
    is_hot_streak = models.BooleanField(default=False)
    streak_count = models.IntegerField(default=0)
    
    last_activity_date = models.DateTimeField(auto_now=True)
    last_decay_applied = models.DateTimeField(null=True, blank=True)
    
    def update_cp(self, points, reason=""):
        """Add/subtract CP and recalculate tier."""
        self.current_cp += points
        self.season_cp += points
        self.all_time_cp = max(self.all_time_cp, self.current_cp)
        self.recalculate_tier()
        self.save()
        
        # Log for history tracking
        TeamRankingHistory.objects.create(
            team=self.team,
            cp_change=points,
            reason=reason,
            new_total=self.current_cp
        )
    
    def recalculate_tier(self):
        """Determine tier based on current CP."""
        if self.current_cp >= 80000:
            self.tier = 'CROWN' if self.is_top_percentile(1) else 'ASCENDANT'
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
```

#### **OrganizationRanking Model**

```python
class OrganizationRanking(models.Model):
    organization = models.OneToOneField(Organization, related_name='ranking')
    empire_score = models.IntegerField(default=0)
    global_rank = models.IntegerField(null=True)
    
    def recalculate_empire_score(self):
        """Aggregate top 3 teams' CP with weighting."""
        top_teams = self.organization.teams.all().select_related('ranking').order_by('-ranking__current_cp')[:3]
        
        weights = [1.0, 0.75, 0.5]
        score = sum(team.ranking.current_cp * weights[i] for i, team in enumerate(top_teams))
        
        self.empire_score = int(score)
        self.save()
```

---

## 10. Service Layer & Compatibility Contracts

**Purpose:** Decouple new `apps/organizations` from dependent apps (tournaments, user_profile, notifications) using stable interfaces.

### 10.1 The Problem: Direct Model Access

**Current Anti-Pattern (Legacy):**
```python
# In tournaments app:
from apps.teams.models import Team

# Direct database access:
team = Team.objects.get(id=team_id)
captain = team.captain  # Triggers N+1 query
wallet = team.owner.wallet  # Assumes owner field exists
```

**Issues:**
- Tight coupling: Changing Team schema breaks tournaments app.
- No abstraction: Business logic leaked across apps.
- Migration blockers: Cannot swap Team model without rewriting consumers.

### 10.2 The Solution: TeamService Interface

**New Pattern:**
```python
# In tournaments app:
from apps.organizations.services import TeamService

# Service layer handles complexity:
team_info = TeamService.get_team_info(team_id)
# Returns: { 'name': ..., 'captain': ..., 'wallet_id': ..., 'members': [...] }
```

**Benefits:**
- **Decoupling:** Tournaments doesn't know if Team is legacy or new model.
- **Flexibility:** Service can query legacy Team OR new Organization/Team.
- **Testability:** Mock TeamService without database.

### 10.3 Standard Service Methods

#### **Method 1: `get_team_wallet(team_id)`**

**Purpose:** Retrieve wallet for prize payout.

**Logic:**
- **Independent Team:** Return `team.owner.wallet`.
- **Organization Team:** Return `team.organization.master_wallet`.

**Signature:**
```python
def get_team_wallet(team_id: int) -> WalletInfo:
    """
    Returns wallet for prize distribution.
    
    Returns:
        WalletInfo(wallet_id, owner_name, type=['USER', 'ORG'])
    """
```

**Benefit:** Economy app doesn't care who owns the wallet.

#### **Method 2: `validate_roster(team_id, tournament_id)`**

**Purpose:** Check if team meets tournament requirements.

**Validation Checks:**
1. Team has minimum required players (e.g., 5 for Valorant).
2. All active lineup players have valid Game Passports.
3. No players are suspended/banned.
4. No roster lock conflicts (team not in overlapping tournament).
5. Game-specific checks (e.g., 1v1 games need 1 athlete).

**Signature:**
```python
def validate_roster(team_id: int, tournament_id: int) -> ValidationResult:
    """
    Validates team roster eligibility for tournament.
    
    Returns:
        ValidationResult(is_valid: bool, errors: List[str])
    """
```

**Benefit:** Centralizes complex eligibility logic.

#### **Method 3: `get_team_identity(team_id)`**

**Purpose:** Retrieve branding assets for display.

**Logic:**
- Check "Brand Inheritance" setting.
- **If Org-enforced:** Return `org.logo`.
- **If Custom:** Return `team.logo`.

**Signature:**
```python
def get_team_identity(team_id: int) -> TeamIdentity:
    """
    Returns display-ready team branding.
    
    Returns:
        TeamIdentity(name, slug, logo_url, badge_url, verification_status)
    """
```

**Benefit:** Templates always display correct logo without `if/else` logic.

#### **Method 4: `get_authorized_managers(team_id)`**

**Purpose:** Retrieve users authorized to manage team.

**Logic:**
- **Independent Team:** Return `[owner]`.
- **Organization Team:** Return `[org_ceo, team_manager, team_coach]` (filtered by permissions).

**Signature:**
```python
def get_authorized_managers(team_id: int) -> List[UserInfo]:
    """
    Returns all users authorized to perform management actions.
    
    Returns:
        List of UserInfo(user_id, username, role)
    """
```

**Benefit:** Solves permission matrix for tournament registration.

#### **Method 5: `create_temporary_team(name, logo, game_id)`**

**Purpose:** Quick team creation during tournament registration (for one-time participants).

**Logic:**
- Create Team with `is_temporary=True` flag.
- Skip full setup (no TOC, no ranking initialization).
- Post-tournament upsell: "Make this team permanent?"

**Signature:**
```python
def create_temporary_team(name: str, logo: str, game_id: int, creator_id: int) -> TemporaryTeam:
    """
    Creates lightweight team for tournament registration.
    
    Returns:
        TemporaryTeam(team_id, status='TEMPORARY')
    """
```

**Benefit:** Reduces friction for casual participants.

### 10.4 Compatibility Layer for Legacy Apps

**Bridge Strategy:** During migration, TeamService queries BOTH legacy `apps/teams` and new `apps/organizations` models.

**Implementation:**
```python
class TeamService:
    @staticmethod
    def get_team_wallet(team_id):
        # Check if team_id belongs to legacy or new system
        if LegacyTeam.objects.filter(id=team_id).exists():
            team = LegacyTeam.objects.get(id=team_id)
            return WalletInfo(team.owner.wallet.id, team.owner.username, 'USER')
        else:
            team = NewTeam.objects.select_related('organization').get(id=team_id)
            if team.organization:
                return WalletInfo(team.organization.master_wallet.id, team.organization.name, 'ORG')
            else:
                return WalletInfo(team.owner.wallet.id, team.owner.username, 'USER')
```

**Phased Rollout:**
1. **Phase 1:** Deploy TeamService with legacy support.
2. **Phase 2:** Update all consumers (tournaments, notifications) to use TeamService.
3. **Phase 3:** Migrate legacy teams to new system.
4. **Phase 4:** Remove legacy model handling from TeamService.

---

## 11. Migration Strategy (Parallel Build)

### 11.1 High-Level Approach

**Pattern:** "Strangler Fig" (grow new system around old, gradually replace).

**Timeline:** 12-16 weeks (see Development Phases).

### 11.2 Three Critical Migration Plans

#### **Plan A: Data Migration Strategy**

**Challenge:** Existing teams (e.g., "Protocol V") owned by Users must fit new Organization/Team model.

**Solution:**

**Script 1: Convert Independent Teams**
```python
# For each existing Team without Organization:
for team in LegacyTeam.objects.filter(organization__isnull=True):
    # Create in new system
    new_team = NewIndependentTeam.objects.create(
        name=team.name,
        slug=team.slug,
        game=team.game,
        region=team.region or detect_region_from_user(team.owner),
        owner=team.owner,  # User FK
        created_at=team.created_at
    )
    
    # Migrate memberships
    for membership in team.memberships.filter(status='ACTIVE'):
        NewTeamMembership.objects.create(
            team=new_team,
            profile=membership.profile,
            role=map_legacy_role(membership.role),
            status='ACTIVE',
            joined_at=membership.joined_at
        )
    
    # Migrate ranking
    new_team.ranking.current_cp = team.ranking.current_cp
    new_team.ranking.save()
    
    # Create mapping for lookups
    TeamMigrationMap.objects.create(
        legacy_id=team.id,
        new_id=new_team.id
    )
```

**Script 2: Handle Tournament References**
```python
# Update tournament registrations to point to new team IDs
for registration in TournamentRegistration.objects.filter(team_id__isnull=False):
    mapping = TeamMigrationMap.objects.filter(legacy_id=registration.team_id).first()
    if mapping:
        registration.team_id = mapping.new_id
        registration.save()
```

**Rollback Strategy:**
- Maintain `TeamMigrationMap` table indefinitely.
- Keep legacy tables in read-only mode for 6 months post-migration.

#### **Plan B: URL Redirect Strategy**

**Challenge:** 50+ hardcoded links to `/teams/{slug}/` will 404 if legacy app removed.

**Solution: Routing Shim**

```python
# In urls.py (root):
urlpatterns = [
    # New org URLs
    path('orgs/<slug:org_slug>/teams/<slug:team_slug>/', new_team_view),
    
    # Legacy redirect
    path('teams/<slug:team_slug>/', legacy_team_redirect),
]

# Redirect logic:
def legacy_team_redirect(request, team_slug):
    # Check if team is legacy or new
    mapping = TeamMigrationMap.objects.filter(legacy_slug=team_slug).first()
    if mapping:
        team = NewTeam.objects.get(id=mapping.new_id)
        if team.organization:
            # Redirect to org-prefixed URL
            return redirect(f'/orgs/{team.organization.slug}/teams/{team.slug}/')
        else:
            # Redirect to standalone team URL (new structure)
            return redirect(f'/teams-v2/{team.slug}/')
    else:
        # Still in legacy system
        return legacy_team_view(request, team_slug)
```

**Notification Fix:**
- Update NotificationService to use `TeamService.get_team_url(team_id)` instead of hardcoded URLs.

#### **Plan C: Service Layer Abstraction**

**See Section 9 above.** Implement TeamService before new app launch.

**Deployment Order:**
1. Deploy TeamService (week 4).
2. Update tournaments app to use TeamService (week 5-6).
3. Update notifications app to use TeamService (week 7).
4. Deploy new `apps/organizations` (week 8).
5. Run data migration scripts (week 9).
6. Enable URL redirects (week 10).
7. Monitor & fix edge cases (week 11-12).
8. Archive legacy app (week 16).

### 11.3 Rollback Procedures

**Trigger Conditions:**
- >5% error rate in tournament registrations.
- >10% performance degradation.
- Critical data loss detected.

**Rollback Steps:**
1. Re-enable legacy `apps/teams` routes.
2. Revert TeamService to legacy-only queries.
3. Disable new Organization features in UI.
4. Investigate root cause, patch, re-deploy.

**Data Safety:**
- No destructive migrations until 30 days post-launch.
- Dual-write to legacy + new databases during transition.

---

## 12. Development Phases & Milestones

### Phase 1: Foundation (Weeks 1-4)

**Objectives:**
- Set up `apps/organizations` skeleton.
- Define models (Organization, Team, TeamMembership).
- Implement TeamService interface.

**Deliverables:**
- [ ] Django app structure created.
- [ ] Models written and peer-reviewed.
- [ ] Initial migrations generated (not applied to prod).
- [ ] TeamService interface defined with method signatures.
- [ ] Unit tests for core models (>80% coverage).

**Dependencies:** None.

### Phase 2: Service Layer Integration (Weeks 5-6)

**Objectives:**
- Deploy TeamService to production (legacy-backed).
- Update tournaments app to use TeamService.

**Deliverables:**
- [ ] TeamService deployed (queries legacy models only).
- [ ] `apps/tournaments` refactored to call TeamService.
- [ ] Integration tests for tournament-team workflows.
- [ ] Performance benchmarking (ensure no regressions).

**Dependencies:** Phase 1 complete.

### Phase 3: Core Features Build (Weeks 7-10)

**Objectives:**
- Build Organization and Team creation flows.
- Implement TOC (Tournament Operations Center).
- Build roster management UI.

**Deliverables:**
- [ ] Organization creation form + dashboard.
- [ ] Team creation fast-track flow (<30 sec).
- [ ] TOC module with active lineup management.
- [ ] Roster invitation/transfer workflows.
- [ ] Free Agent Market (LFT/LFP) basic version.

**Dependencies:** Phase 2 complete.

### Phase 4: Ranking System (DCRS) (Weeks 11-12)

**Objectives:**
- Implement CP calculation engine.
- Build leaderboards (team + organization).
- Implement decay and seasonal reset logic.

**Deliverables:**
- [ ] TeamRanking and OrganizationRanking models.
- [ ] CP calculation service.
- [ ] Leaderboard views (global, regional, game-specific).
- [ ] Cron jobs for decay and seasonal resets.
- [ ] Direct Invite eligibility checks.

**Dependencies:** Phase 3 complete.

### Phase 5: Data Migration (Weeks 13-14)

**Objectives:**
- Migrate legacy teams to new system.
- Update tournament registrations to new team IDs.

**Deliverables:**
- [ ] Migration scripts written and tested on staging.
- [ ] TeamMigrationMap populated.
- [ ] Tournament registration team_id updated.
- [ ] Validation: All legacy teams mapped, zero data loss.
- [ ] Rollback script tested.

**Dependencies:** Phase 4 complete + stakeholder approval.

### Phase 6: URL & Notification Fixes (Week 15)

**Objectives:**
- Deploy URL redirect shim.
- Update NotificationService to use dynamic URLs.

**Deliverables:**
- [ ] URL redirect middleware deployed.
- [ ] All email notifications use `TeamService.get_team_url()`.
- [ ] Manual QA: Click 20+ notification links, verify no 404s.

**Dependencies:** Phase 5 complete.

### Phase 7: Launch & Monitor (Week 16+)

**Objectives:**
- Full production launch.
- Monitor error rates, performance, user feedback.

**Deliverables:**
- [ ] Feature flag enabled for 100% of users.
- [ ] Dashboard for monitoring (CP changes, registrations, errors).
- [ ] Support documentation updated.
- [ ] Retrospective meeting conducted.

**Success Criteria:**
- <2% error rate in tournament registrations.
- <5% support ticket increase.
- >70% of new teams use fast-track creation flow.

### Phase 8: Cleanup & Archive (Weeks 17-20)

**Objectives:**
- Archive legacy `apps/teams` code.
- Remove deprecated models and migrations.

**Deliverables:**
- [ ] Legacy models marked as deprecated in code.
- [ ] Legacy admin panels disabled.
- [ ] Documentation updated to reference new system only.
- [ ] Legacy database tables backed up and dropped from prod.

**Dependencies:** 30 days of stable operation post-launch.

---

## 13. Quality Gates by Phase

**Purpose:** Define mandatory criteria that MUST be met before advancing to the next phase. Prevents accumulating technical debt and ensures production readiness.

### Phase 1 Quality Gates (Foundation)

**Before Proceeding to Phase 2:**

**Code Quality:**
- [ ] All models have docstrings and type hints
- [ ] Code passes Black formatter (120 char line length)
- [ ] No pylint/flake8 errors (warnings reviewed)
- [ ] All service method signatures defined with dataclass returns

**Testing:**
- [ ] Model tests: 80%+ coverage
- [ ] All model methods tested (happy path + error cases)
- [ ] Migration scripts tested on staging database
- [ ] No breaking changes to existing `apps/teams` (verified)

**Documentation:**
- [ ] README.md created for `apps/organizations`
- [ ] Architecture Decision Records (ADRs) created for key decisions
- [ ] Model relationship diagram documented

**Performance:**
- [ ] No N+1 queries in model methods (verified with Django Debug Toolbar)
- [ ] Database indexes defined for all FK columns and common filters

**Security:**
- [ ] No sensitive data in migrations or fixtures
- [ ] Database constraints enforce business rules (e.g., one owner per game)

**Rollback Readiness:**
- [ ] Migration rollback script tested
- [ ] Database backup procedure documented

---

### Phase 2 Quality Gates (Service Layer Integration)

**Before Proceeding to Phase 3:**

**Code Quality:**
- [ ] All service methods have Google-style docstrings
- [ ] Type hints on all service method signatures
- [ ] Service methods use `@staticmethod` or `@classmethod` (no instance state)
- [ ] Error handling uses custom exceptions (not generic `Exception`)

**Testing:**
- [ ] Service layer tests: 75%+ coverage
- [ ] All 7+ TeamService methods tested (happy path + error cases)
- [ ] Integration tests: Service → Model interactions
- [ ] Performance tests: Service methods <100ms (95th percentile)

**Integration:**
- [ ] `tournaments` app successfully refactored to use TeamService
- [ ] `notifications` app uses `TeamService.get_team_url()`
- [ ] No direct `Team` model imports in dependent apps (linter enforced)
- [ ] All hardcoded URLs replaced with service calls

**Performance:**
- [ ] Query count benchmarks met (≤5 queries for detail views)
- [ ] Page load times <200ms (verified on staging)
- [ ] No performance regressions (before/after comparison)

**Monitoring:**
- [ ] Logging configured for all service methods
- [ ] Error tracking enabled (Sentry or equivalent)
- [ ] Service method metrics dashboard created (response time, error rate)

**Rollback Readiness:**
- [ ] Feature flag `TEAM_VNEXT_ENABLED` tested (can disable without errors)
- [ ] Rollback procedure documented and tested
- [ ] 48-hour monitoring period after deployment (error rate <1%)

---

### Phase 3 Quality Gates (Core Features Build)

**Before Proceeding to Phase 4:**

**Code Quality:**
- [ ] All views are thin (delegate to services)
- [ ] Forms use Django Forms with Tailwind-rendered templates
- [ ] No custom CSS except documented edge cases
- [ ] Vanilla JS modules follow ES6+ standards (no jQuery)

**Testing:**
- [ ] Feature tests: 70%+ coverage
- [ ] Complete user workflows tested (team creation → roster invite → tournament reg)
- [ ] Permission boundary tests (unauthorized access blocked)
- [ ] Mobile responsiveness tested on 320px width

**Frontend:**
- [ ] All templates use Tailwind CSS only (no Bootstrap/custom CSS)
- [ ] Component-based partials created (`_team_card.html`, `_roster_table.html`)
- [ ] Vanilla JS modules for interactivity (no jQuery, React, Vue)
- [ ] Accessibility checklist completed (ARIA labels, keyboard nav, contrast)
- [ ] Page speed: <2s initial load, <200ms subsequent nav

**UX:**
- [ ] Team creation flow completes in <30 seconds
- [ ] Progressive disclosure implemented (simple options first)
- [ ] Error messages user-friendly (no technical jargon)
- [ ] Mobile-first design verified on real devices

**Performance:**
- [ ] No N+1 queries (Django Debug Toolbar checks pass)
- [ ] List views paginated (50 items max)
- [ ] Images lazy-loaded, CSS/JS minified

**Security:**
- [ ] CSRF protection on all forms
- [ ] Permission decorators on all management views
- [ ] Input validation server-side (not just client-side)
- [ ] Audit logging for team creation/deletion

**Rollback Readiness:**
- [ ] Can disable new features with `ORG_FEATURES_ENABLED=false`
- [ ] Legacy team creation still functional (fallback)
- [ ] User data preserved if rollback occurs

---

### Phase 4 Quality Gates (Ranking System)

**Before Proceeding to Phase 5:**

**Code Quality:**
- [ ] CP calculation logic well-documented (formula explained in docstrings)
- [ ] Tier recalculation tested with edge cases (boundary values)
- [ ] Decay logic tested (inactive teams lose 5% CP per week)

**Testing:**
- [ ] RankingService tests: 80%+ coverage (critical path)
- [ ] CP award calculations tested (all placement + tier combinations)
- [ ] Hot streak logic tested (3+ wins, breaks on loss)
- [ ] Seasonal reset tested (50% CP reduction)
- [ ] Performance: Leaderboard query <400ms for 100 teams

**Data Integrity:**
- [ ] CP values cannot go negative (database constraint)
- [ ] Tier transitions logged (audit trail)
- [ ] Concurrent CP updates handled safely (`select_for_update()`)

**Monitoring:**
- [ ] Leaderboard update job runs every 5 minutes (Celery task)
- [ ] Decay job runs nightly (Celery task)
- [ ] Metrics dashboard: CP distribution, tier counts, hot streaks

**Rollback Readiness:**
- [ ] Can disable DCRS with `DCRS_ENABLED=false`
- [ ] Legacy ranking system still functional (fallback)
- [ ] CP data backed up before each update

---

### Phase 5 Quality Gates (Data Migration)

**Before Proceeding to Phase 6:**

**Migration Safety:**
- [ ] Migration scripts tested on staging with full data copy
- [ ] Data validation script confirms zero data loss
- [ ] `TeamMigrationMap` table populated for all legacy teams
- [ ] Dual-write enabled: All writes go to BOTH legacy + vNext
- [ ] Reconciliation script detects divergence (runs nightly)

**Testing:**
- [ ] MigrationService tests: 90%+ coverage (critical path)
- [ ] All 10,000+ teams migrated successfully (staging)
- [ ] Tournament registrations point to correct team IDs (verified)
- [ ] User profiles show correct team history (verified)
- [ ] Notifications contain valid team links (verified)

**Data Integrity:**
- [ ] Foreign key relationships preserved
- [ ] Ranking data transferred correctly (CP, tier, streak)
- [ ] Audit logs transferred (team activity history)
- [ ] No orphaned records (referential integrity check)

**Performance:**
- [ ] Migration completes in <30 minutes for 10,000 teams
- [ ] Service layer routing overhead <10ms per call
- [ ] No performance degradation vs pre-migration

**Rollback Readiness:**
- [ ] Rollback script tested (restores legacy tables)
- [ ] Database backup taken immediately before migration
- [ ] Can revert to legacy-only mode with `TEAM_MIGRATION_DUAL_SYSTEM=false`
- [ ] Rollback procedure documented (step-by-step)
- [ ] 7-day monitoring period (zero divergence detected)

**Stakeholder Approval:**
- [ ] Technical Lead sign-off
- [ ] Product Lead sign-off
- [ ] Support team trained on migration issues

---

### Phase 6 Quality Gates (URL & Notification Fixes)

**Before Proceeding to Phase 7:**

**URL Stability:**
- [ ] URL redirect middleware deployed and tested
- [ ] 20+ pre-migration notification links clicked (zero 404s)
- [ ] Email templates use dynamic URLs (`TeamService.get_team_url()`)
- [ ] Redirect logs monitored for 7 days (no errors)

**Testing:**
- [ ] All notification types tested (invite, roster change, tournament reg)
- [ ] Legacy URLs redirect correctly (org vs independent teams)
- [ ] SEO: 301 redirects (not 302) for permanent moves

**Monitoring:**
- [ ] 404 error rate <0.1% (vs 5%+ baseline before redirects)
- [ ] Notification delivery rate unchanged (no regressions)
- [ ] User complaints <5 per 10,000 users

**Rollback Readiness:**
- [ ] Can disable redirects without breaking legacy URLs
- [ ] Old email templates preserved as fallback

---

### Phase 7 Quality Gates (Launch & Monitor)

**Before Proceeding to Phase 8:**

**Production Stability:**
- [ ] Feature flag `TEAM_VNEXT_USER_ROLLOUT` at 100%
- [ ] Error rate <2% (vs <5% threshold)
- [ ] Support ticket increase <5% (vs <10% threshold)
- [ ] Page load times meet benchmarks (<200ms detail pages)

**User Adoption:**
- [ ] 70%+ of new teams use fast-track creation flow
- [ ] User feedback survey: 80%+ satisfaction
- [ ] Zero P0 incidents in 30 days
- [ ] Zero data loss incidents

**Monitoring:**
- [ ] Dashboard tracks: CP changes, registrations, errors, response times
- [ ] Alerts configured: Error rate >2%, response time >500ms
- [ ] On-call rotation established

**Documentation:**
- [ ] User-facing documentation updated (help center)
- [ ] Support team trained on new features
- [ ] Runbook created for common issues

**Rollback Readiness:**
- [ ] 30-day observation period (stable operation)
- [ ] Rollback procedure tested monthly (drill)

---

### Phase 8 Quality Gates (Cleanup & Archive)

**Before Legacy Deletion:**

**Verification:**
- [ ] 30 days of stable operation (zero P0/P1 incidents)
- [ ] Zero active usage of legacy `apps/teams` (analytics confirm)
- [ ] All dependent apps use vNext service layer (code audit)
- [ ] Legal/compliance review: Data retention requirements met

**Backup:**
- [ ] Legacy database tables backed up (long-term retention)
- [ ] Migration map retained indefinitely (forensic/audit)
- [ ] Legacy code archived in git (tagged release)

**Documentation:**
- [ ] "Deprecated" warnings added to legacy code
- [ ] Migration post-mortem completed
- [ ] Lessons learned documented (ADRs updated)
- [ ] README.md updated to reference vNext only

**Final Approval:**
- [ ] Technical Lead sign-off
- [ ] Product Lead sign-off
- [ ] Security team sign-off (no compliance issues)
- [ ] Stakeholder approval for permanent deletion (6+ months later)

---

### Quality Gate Enforcement

**Review Process:**
- Each gate reviewed in Phase Exit Meeting.
- Technical Lead + Senior Engineer approval required.
- Failed gates block phase advancement (no exceptions).

**Documentation:**
- Checklist results logged in project management tool.
- Failed gates documented with remediation plan.
- Stakeholder sign-offs archived.

---

## Appendix A: Open Questions & Decisions Required

### Decisions Needed Before Implementation

1. **Organization Verification Process:**
   - Who approves verification requests? (Manual review by admin / Automated via document upload?)
   - Verification criteria checklist needed.

2. **Prize Money Taxation:**
   - Are Smart Contract splits pre-tax or post-tax?
   - Who handles tax reporting (Platform / User / Org)?

3. **Data Retention:**
   - How long to keep disbanded team records?
   - GDPR/data privacy compliance for player histories?

4. **Tournament Tier Assignment:**
   - Who assigns Tier S/A/B/C to tournaments? (Self-reported + admin approval / Automated based on prize pool?)

5. **Global vs. Regional CP:**
   - Should CP be game-specific and region-specific, or truly global?
   - Example: Top Valorant team in Bangladesh vs. Top Valorant team globally?

### Technical Stack Decisions

- **Database:** Continue with PostgreSQL + proper FK relationships (no more IntegerField hacks).
- **Caching:** Redis for leaderboard rankings (updated every 5 minutes).
- **Background Tasks:** Celery for CP decay, seasonal resets, notification dispatching.
- **Frontend:** Vue.js components for TOC drag-and-drop (if not already in use).

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **CP (Crown Points)** | Ranking currency earned through tournament performance. |
| **DCRS** | DeltaCrown Ranking System. |
| **Empire Score** | Aggregate ranking for Organizations based on top 3 teams. |
| **Game Passport** | Verified Game ID (Riot ID, Steam ID, etc.) required for players. |
| **Hot Streak** | 3+ consecutive official match wins, grants CP multiplier. |
| **IGL** | In-Game Leader (tactical role in team games). |
| **LFT** | Looking for Team (player seeking roster spot). |
| **LFP** | Looking for Player (team seeking member). |
| **Roster Lock** | Tournament-imposed restriction preventing roster changes. |
| **Solo-Squad** | Team structure for 1v1 games where individual athletes represent a team brand. |
| **Strangler Fig** | Migration pattern: Build new system alongside old, gradually replace. |
| **TOC** | Tournament Operations Center (pre-configured team settings). |
| **Transfer** | Player movement from one team to another. |
| **Soft FK** | IntegerField used instead of ForeignKey (anti-pattern to be eliminated). |

---

## Document Maintenance

**Review Cadence:** Quarterly or after major feature releases.  
**Amendment Process:** Changes require Product Lead + Tech Lead approval.  
**Version History:**
- v1.0 (Jan 24, 2026): Initial consolidated master plan.

**Contact:**
- Product Questions: Product Architecture Team
- Technical Questions: Engineering Lead
- Implementation Coordination: Project Manager

---

**END OF MASTER PLAN**