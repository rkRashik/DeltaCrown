# Tournament App Current Implementation Audit

**Date:** December 7, 2025  
**Auditor:** GitHub Copilot  
**Scope:** apps/tournaments (Full Tournament Application)  
**Purpose:** Deep structural audit of current tournament implementation before modernization

---

## Executive Summary

The tournaments app is a **comprehensive, feature-rich tournament management system** with 23 model files, 37+ service modules, 30+ view modules, and extensive API endpoints. It demonstrates **sophisticated architecture patterns** including service layer abstraction, soft deletes, JSONB flexibility, and real-time WebSocket support.

However, the app exhibits **dual architecture patterns** - mixing legacy hardcoded game logic with newer integration points to the Games app. This creates complexity and technical debt that must be addressed during modernization.

**Key Findings:**
- ✅ **Solid Foundation:** Well-structured models with proper constraints, indexes, and relationships
- ⚠️ **Mixed Architecture:** Simultaneous use of legacy Game model + new apps.games integration
- ⚠️ **Hardcoded Game Logic:** Game-specific conditionals scattered throughout views and services
- ✅ **Service Layer:** Comprehensive business logic abstraction following ADR-001
- ⚠️ **Integration Gaps:** Incomplete migration to apps.games, inconsistent use of GameService
- ✅ **Feature Complete:** Registration, brackets, matches, disputes, payments, certificates all implemented
- ⚠️ **Template Coupling:** Frontend assumes specific game slugs and legacy structures

---

## 1. High-Level Overview

### 1.1 Application Structure

The tournaments app is organized into **specialized modules**:

```
apps/tournaments/
├── models/          # 23 model files (Tournament, Match, Bracket, Registration, etc.)
├── services/        # 37+ service modules (business logic layer)
├── views/           # 30+ view modules (user-facing pages)
├── api/             # REST API endpoints (discovery, organizer, analytics, etc.)
├── admin*.py        # 8 admin modules (comprehensive Django admin)
├── forms/           # Form definitions
├── templatetags/    # Custom template tags
├── templates/       # Django templates (list, detail, registration, lobby, etc.)
├── games/           # Legacy game-specific logic (points.py for BR games)
├── signals/         # Event handlers
├── tasks/           # Celery tasks
├── realtime/        # WebSocket support
├── security/        # Permission and audit utilities
├── management/      # Management commands
└── tests/           # Test suites
```

### 1.2 Core Responsibilities

The tournaments app manages:

1. **Tournament Lifecycle:** Draft → Published → Registration → Live → Completed
2. **Participant Registration:** Solo and team registrations with payment processing
3. **Bracket Generation:** Single/double elimination, round robin, Swiss, group stage
4. **Match Management:** Scheduling, check-in, result submission, disputes
5. **Leaderboards & Standings:** Real-time standings calculation (game-specific logic)
6. **Prize Distribution:** Winner determination and payout processing
7. **Certificates:** Achievement proof generation
8. **Dynamic Forms:** Custom registration form builder
9. **Staff Management:** Tournament organizer roles and permissions
10. **Real-time Updates:** WebSocket integration for live bracket/match updates

### 1.3 Architecture Patterns

**Positive Patterns:**
- ✅ **Service Layer Pattern (ADR-001):** Business logic isolated in services/
- ✅ **Soft Delete Strategy (ADR-003):** Audit trail preservation
- ✅ **PostgreSQL JSONB (ADR-004):** Flexible data storage (game_config, registration_data)
- ✅ **Type Hints & Docstrings:** Google-style documentation throughout
- ✅ **Transaction Safety:** @transaction.atomic decorators on critical operations
- ✅ **Separation of Concerns:** Admin, views, API endpoints well-segregated

**Problematic Patterns:**
- ⚠️ **Dual Game Architecture:** Legacy Game model + apps.games integration coexist
- ⚠️ **Hardcoded Game Logic:** if game_slug == 'valorant' throughout codebase
- ⚠️ **Tight Coupling:** Views import and use service directly (acceptable but limits modularity)
- ⚠️ **Mixed Integration:** Some areas use GameService, others don't
- ⚠️ **IntegerField References:** team_id uses IntegerField to avoid circular dependency

---

## 2. Models & Data Structures

### 2.1 Core Models (Well-Designed)

#### **Tournament** (`models/tournament.py`)
**Purpose:** Central tournament entity with full lifecycle management

**Key Fields:**
- `organizer` → ForeignKey to accounts.User
- `game` → ForeignKey to **legacy Game model** (⚠️ This is the problem)
- `format` → Single/double elim, round robin, Swiss, group playoff
- `participation_type` → Team or Solo
- `status` → Full state machine (draft → archived)
- `prize_pool`, `prize_deltacoin` → Dual currency support
- `entry_fee_amount`, `payment_methods` → ArrayField for payment options
- `registration_data`, `game_config` → JSONB for flexibility
- Soft delete support via SoftDeleteModel

**Status Workflow:**
```
DRAFT → PENDING_APPROVAL → PUBLISHED → REGISTRATION_OPEN → 
REGISTRATION_CLOSED → LIVE → COMPLETED → (CANCELLED/ARCHIVED)
```

**Integration Points:**
- ✅ Uses `organizer` from accounts.User
- ⚠️ Uses legacy `Game` model (NOT apps.games.Game)
- ⚠️ Uses `team_id` IntegerField (NOT ForeignKey to apps.teams.Team)

**Assessment:** Well-structured with proper constraints, but tied to **legacy Game model**.

---

#### **Game** (`models/tournament.py`)
**Purpose:** Game definitions for supported tournament games

**⚠️ CRITICAL ISSUE:** This is a **legacy Game model** that duplicates functionality from `apps.games.Game`.

**Key Fields:**
- `name`, `slug` → Game identification
- `default_team_size` → 1v1, 2v2, 5v5, etc.
- `profile_id_field` → Field name in UserProfile (e.g., 'riot_id', 'steam_id')
- `default_result_type` → Map score, best of X, point based
- `game_config` → JSONB for game-specific settings
- `banner`, `card_image`, `logo` → Media fields
- `min_team_size`, `max_team_size`, `roster_rules` → Team structure
- `result_logic` → JSONB for result calculation

**Assessment:** This model **duplicates** the newer `apps.games.Game` model. The tournaments app should migrate to use `apps.games.Game` exclusively.

---

#### **Registration** (`models/registration.py`)
**Purpose:** Participant registration tracking

**Key Fields:**
- `tournament` → ForeignKey to Tournament
- `user` → ForeignKey to accounts.User (for solo or team captain)
- `team_id` → IntegerField (⚠️ should be ForeignKey to apps.teams.Team)
- `registration_data` → JSONB (game IDs, contact info, custom fields)
- `status` → pending → payment_submitted → confirmed/rejected/cancelled
- `completion_percentage`, `current_step`, `time_spent_seconds` → UX tracking
- `checked_in`, `checked_in_at`, `checked_in_by` → Check-in workflow
- `slot_number`, `seed` → Bracket seeding
- `waitlist_position` → Waitlist management

**Constraints:**
- XOR constraint: Either user OR team_id must be set (not both)
- Unique slot per tournament
- Unique team per tournament

**Assessment:** Excellent design with proper constraints. **IntegerField for team_id is a compromise** to avoid circular dependency with apps.teams.

---

#### **Bracket** & **BracketNode** (`models/bracket.py`)
**Purpose:** Tournament bracket structure

**Bracket:**
- `tournament` → OneToOneField
- `format` → Single/double elim, round robin, Swiss, group stage
- `seeding_method` → slot-order, random, ranked, manual
- `bracket_structure` → JSONB metadata for visualization
- `is_finalized` → Lock bracket after generation

**BracketNode:**
- Tree structure with `parent_node`, `child1_node`, `child2_node`
- `participant_id`, `participant_name` → IntegerField + denormalized name
- `round_number`, `position_in_round`
- `is_bye` → Handle power-of-2 bracket gaps

**Seeding Methods:**
- `slot-order`: First-come-first-served (registration order)
- `random`: Random seeding
- `ranked`: Based on team rankings from apps.teams ⚠️ (assumes apps.teams integration)
- `manual`: Organizer assigns seeds

**Assessment:** Solid bracket implementation. **Ranked seeding assumes apps.teams integration** which may not be fully implemented.

---

#### **Match** (`models/match.py`)
**Purpose:** Match lifecycle with state machine

**State Machine:**
```
SCHEDULED → CHECK_IN → READY → LIVE → PENDING_RESULT → COMPLETED
                │                          │
                └──> FORFEIT               └──> DISPUTED
```

**Key Fields:**
- `tournament`, `bracket` → ForeignKeys
- `round_number`, `match_number` → Match identification
- `participant1_id`, `participant2_id` → IntegerField (team or user)
- `participant1_name`, `participant2_name` → Denormalized for display
- `state` → Full state machine
- `participant1_score`, `participant2_score` → Match scores
- `winner_id`, `loser_id` → Result tracking
- `lobby_info` → JSONB (map, server, lobby code, password)
- `scheduled_at`, `started_at`, `completed_at` → Timestamps
- Soft delete support

**Assessment:** Comprehensive match management with proper state machine. **IntegerField for participants** again due to team/user duality.

---

#### **Group** & **GroupStanding** (`models/group.py`)
**Purpose:** Group stage support for 9 games

**Group:**
- `tournament` → ForeignKey
- `name` → "Group A", "Group B", etc.
- `max_participants`, `advancement_count`
- `config` → JSONB (points_system, tiebreaker_rules, match_format)

**GroupStanding:**
- `group` → ForeignKey
- `participant_id`, `participant_name` → IntegerField + denormalized
- Points tracking: `wins`, `losses`, `draws`, `points`
- Game-specific stats: `kills`, `deaths`, `assists`, `goals_for`, `goals_against`

**Assessment:** Supports diverse game types (football, FPS, MOBA, BR). **JSONB config** provides flexibility.

---

### 2.2 Supporting Models

#### **Payment** (`models/registration.py`)
- Payment proof submission and verification
- `payment_method` → bkash, nagad, rocket, bank_transfer, deltacoin
- `verification_status` → pending → verified/rejected
- `payment_proof` → File upload

#### **Dispute** (`models/match.py`)
- Match result disputes
- `status` → open → under_review → resolved/escalated
- `submitted_by`, `reviewed_by`, `resolution`

#### **Certificate** (`models/certificate.py`)
- Achievement proof generation
- `certificate_type` → winner, runner_up, participation, mvp
- `issued_at`, `revoked_at` → Lifecycle tracking

#### **TournamentResult** (`models/result.py`)
- Final placement and winner determination
- `final_placement` → 1st, 2nd, 3rd, etc.
- `prize_amount`, `prize_deltacoin`

#### **PrizeTransaction** (`models/prize.py`)
- Prize payout tracking
- `transaction_status` → pending → processed/failed
- Integration with apps.economy

#### **Dynamic Forms** (`models/form_template.py`, `form_configuration.py`)
- `RegistrationFormTemplate` → Reusable form templates
- `TournamentRegistrationForm` → Per-tournament form config
- `FormResponse` → Registration submissions
- `FormWebhook`, `WebhookDelivery` → Webhook integration

#### **Staff Management** (`models/staff.py`)
- `TournamentStaffRole` → Role definitions with permissions
- `TournamentStaff` → Staff assignments to tournaments

**Assessment:** All supporting models are **feature-complete and well-designed**.

---

### 2.3 Legacy/Deprecated Models

- ✅ `TemplateRating` → Removed (deprecated marketplace feature per `__init__.py`)

---

## 3. Services & Business Logic

### 3.1 Service Architecture Overview

**37+ service modules** implement tournament business logic following **ADR-001 (Service Layer Pattern)**.

**Core Services:**
- `tournament_service.py` → Tournament CRUD and lifecycle
- `registration_service.py` → Registration and payment processing (1,710 lines!)
- `bracket_service.py` → Bracket generation and seeding (1,250 lines)
- `match_service.py` → Match state transitions and result submission
- `leaderboard.py` → Standings calculation (game-specific logic)
- `payment_service.py` → DeltaCoin integration
- `certificate_service.py` → Certificate generation
- `notification_service.py` → Notification dispatching

**Specialized Services:**
- `game_config_service.py` → Game config management
- `group_stage_service.py` → Group stage logic
- `lobby_service.py` → Tournament lobby and check-in
- `ranking_service.py` → Ranking calculations
- `eligibility_service.py` → Registration eligibility checks
- `analytics_service.py` → Tournament analytics
- `payout_service.py` → Prize distribution
- `winner_service.py` → Winner determination
- And 20+ more...

**Assessment:** **Excellent service layer separation**. Business logic is properly abstracted from views.

---

### 3.2 Game-Specific Logic (⚠️ Technical Debt)

**Problem Areas:**

#### **Hardcoded Game Conditionals**

**In `registration_wizard.py` (lines 479-491):**
```python
if game_slug == 'valorant':
    auto_filled['game_id'] = profile.riot_id or ''
elif game_slug == 'pubg-mobile':
    auto_filled['game_id'] = profile.pubg_mobile_id or ''
elif game_slug == 'mobile-legends':
    auto_filled['game_id'] = profile.mlbb_id or ''
elif game_slug == 'free-fire':
    auto_filled['game_id'] = profile.free_fire_id or ''
elif game_slug == 'cod-mobile':
    auto_filled['game_id'] = profile.codm_uid or ''
elif game_slug == 'dota-2' or game_slug == 'cs2':
    auto_filled['game_id'] = profile.steam_id or ''
elif game_slug == 'efootball' or game_slug == 'ea-fc':
    auto_filled['game_id'] = profile.efootball_id or profile.ea_id or ''
```

**In `leaderboard.py` (lines 107-111):**
```python
from apps.games.services import game_service
game_slug = game_service.normalize_slug(tournament.game.slug)
if game_slug == 'free-fire':
    points = calc_ff_points(kills, placement)
elif game_slug == 'pubg-mobile':
    points = calc_pubgm_points(kills, placement)
```

**In `games/points.py`:**
- Hardcoded BR point calculation for Free Fire and PUBG Mobile
- Should be data-driven from apps.games

**Assessment:** **This is the core technical debt**. Game-specific logic should be:
1. Defined in `apps.games.Game.game_config` JSONB
2. Retrieved via `GameService.get_game_config()`
3. Applied generically using configurable rules

---

#### **Mixed Use of GameService**

**Partial Integration:**
- ✅ `leaderboard.py` imports and uses `game_service.normalize_slug()`
- ✅ `registration_wizard.py` has fallback to legacy hardcoded logic
- ❌ Most services do NOT use GameService
- ❌ Tournament model still references legacy Game model

**Assessment:** **Inconsistent migration** to apps.games architecture.

---

### 3.3 Registration Service Analysis (`registration_service.py`)

**Size:** 1,710 lines (largest service)

**Responsibilities:**
- Participant registration with eligibility validation
- Auto-fill from UserProfile
- Payment submission and verification
- DeltaCoin integration (auto-verification)
- Registration cancellation with refunds
- Slot and seed assignment
- Waitlist management

**Key Methods:**
- `register_participant()` → Main registration flow
- `submit_payment()` → Payment proof submission
- `verify_payment()` → Admin verification
- `process_deltacoin_payment()` → DeltaCoin deduction
- `cancel_registration()` → Cancellation with refund
- `_auto_fill_registration_data()` → UserProfile integration

**Integration Points:**
- ✅ `apps.user_profile` → Auto-fill game IDs, phone, etc.
- ✅ `apps.economy` → DeltaCoin wallet operations
- ⚠️ Hardcoded game slug checks (see above)

**Assessment:** **Comprehensive but needs refactoring** to use GameService for profile field mapping.

---

### 3.4 Bracket Service Analysis (`bracket_service.py`)

**Size:** 1,250 lines

**Algorithms:**
- Single Elimination → Standard knockout with byes
- Double Elimination → Winners + Losers brackets
- Round Robin → All participants play each other
- Swiss → (implementation unclear from excerpt)

**Seeding:**
- `slot-order` → Registration order
- `random` → Random seeding
- `ranked` → **Assumes apps.teams integration** for team rankings
- `manual` → Organizer-defined

**Real-time Support:**
- ✅ WebSocket broadcasting via `broadcast_bracket_updated()`

**Assessment:** Solid algorithms. **Ranked seeding dependency on apps.teams** may be incomplete.

---

### 3.5 Integration Services

#### **PaymentService** (`payment_service.py`)
- ✅ Integrates with `apps.economy` for DeltaCoin operations
- ✅ Wallet balance checks
- ✅ Automatic deduction and verification
- ✅ Refund processing
- ✅ Idempotency keys to prevent duplicate charges

#### **NotificationService** (`notification_service.py`)
- ✅ Integrates with `apps.notifications`
- Sends notifications for registration, payment, match results, etc.

#### **PayoutService** (`payout_service.py`)
- ✅ Integrates with `apps.economy.services.award`
- ✅ Prize distribution to winners
- ✅ Transaction tracking

**Assessment:** **Integration with economy and notifications is well-implemented**.

---

## 4. Views, URLs & User Flows

### 4.1 View Architecture

**30+ view modules** organized by feature area:

**Main Views:**
- `main.py` → Tournament list, detail pages
- `registration.py`, `registration_wizard.py`, `dynamic_registration.py` → Registration flows
- `player.py` → Player dashboard, my tournaments
- `organizer.py` → Organizer dashboard and management
- `live.py` → Live brackets, match detail, results
- `leaderboard.py` → Tournament leaderboards
- `lobby.py` → Tournament lobby and check-in
- `spectator.py` → Public spectator view

**Specialized Views:**
- `group_stage.py` → Group configuration and standings
- `result_submission.py` → Match result submission
- `dispute_resolution.py`, `disputes_management.py` → Dispute handling
- `permission_requests.py` → Team registration permissions
- `withdrawal.py` → Registration cancellation
- `payment_status.py` → Payment tracking
- `form_analytics_view.py` → Registration analytics
- `response_export_view.py` → Export registration data
- `bulk_operations_view.py` → Bulk admin actions
- `webhook_views.py` → Webhook management
- `health_metrics.py` → Tournament health monitoring

**Assessment:** **Comprehensive coverage of all user flows**. Views are properly segregated by feature.

---

### 4.2 URL Structure (`urls.py`)

**382 lines** of URL patterns covering:

**Public Pages:**
- `/tournaments/` → Tournament list (FE-T-001)
- `/tournaments/<slug>/` → Tournament detail (FE-T-002)
- `/tournaments/<slug>/register/` → Registration wizard (FE-T-004)
- `/tournaments/<slug>/bracket/` → Live bracket (FE-T-008)
- `/tournaments/<slug>/matches/<id>/` → Match detail (FE-T-009)
- `/tournaments/<slug>/leaderboard/` → Leaderboard (FE-T-010)
- `/tournaments/<slug>/lobby/` → Tournament lobby (FE-T-007)
- `/tournaments/<slug>/results/` → Results page (FE-T-018)

**Player Pages:**
- `/tournaments/my/` → My tournaments dashboard (FE-T-005)
- `/tournaments/my/matches/` → My matches view

**Organizer Pages:**
- `/tournaments/organizer/dashboard/` → Organizer dashboard
- `/tournaments/organizer/hub/` → Organizer hub
- Various management endpoints (participants, payments, matches, disputes)

**API Endpoints:**
- `/api/tournaments/` → REST API (handled by api/ module)

**Assessment:** **Well-organized URL structure** following frontend sprint plan. Clear separation of public/player/organizer concerns.

---

### 4.3 Key User Flows

#### **Registration Flow (Solo)**
1. User navigates to `/tournaments/<slug>/`
2. Clicks "Register Now" (eligibility check in template)
3. Redirected to `/tournaments/<slug>/register/` (RegistrationWizardView)
4. **Step 1:** Game ID entry (auto-filled from UserProfile)
   - ⚠️ Hardcoded game slug logic for auto-fill
5. **Step 2:** Contact info (phone, Discord, etc.)
6. **Step 3:** Payment submission (if entry fee required)
   - DeltaCoin: Auto-verification
   - bKash/Nagad: Manual proof upload
7. Success page with confirmation

**Issues:**
- ⚠️ Hardcoded game slug checks in `_auto_fill_registration_data()`
- ⚠️ Should use GameService to get profile field mapping

---

#### **Registration Flow (Team)**
1. Team captain navigates to tournament detail
2. Team eligibility check (team must exist in apps.teams)
3. Permission request workflow (if required)
4. Registration wizard (similar to solo)
5. **Step 3 Enhancement:** Roster verification
   - ⚠️ Imports `apps.teams.models.Team` and `TeamMembership`
   - ⚠️ Assumes apps.teams integration

**Issues:**
- ⚠️ Team registration heavily depends on apps.teams architecture
- ✅ Uses IntegerField team_id to avoid circular dependency

---

#### **Bracket Generation Flow**
1. Organizer navigates to tournament hub
2. Clicks "Generate Bracket"
3. BracketService.generate_bracket() called
   - Fetches confirmed registrations
   - Applies seeding method
   - Creates BracketNodes
   - Creates Matches
4. Real-time WebSocket broadcast to participants
5. Bracket displayed at `/tournaments/<slug>/bracket/`

**Issues:**
- ⚠️ Ranked seeding assumes apps.teams has ranking data
- ✅ Other seeding methods work independently

---

#### **Match Result Submission**
1. Participant navigates to match detail
2. Submits result with scores
3. MatchService.submit_result() validates and saves
4. State transition: LIVE → PENDING_RESULT
5. Organizer reviews and confirms/rejects
6. If confirmed: Winner advances in bracket, loser eliminated
7. BracketService.advance_winner() updates bracket
8. Real-time updates via WebSocket

**Issues:**
- ✅ Well-implemented state machine
- ⚠️ Game-specific result types not fully leveraged

---

### 4.4 View Layer Issues

**Hardcoded Game Logic in Views:**
- `registration_wizard.py` → Game slug conditionals (lines 479-491)
- `registration.py` → Similar auto-fill logic
- `group_stage.py` → Imports `game_service` (partial integration)
- `spectator.py` → Uses `game_service.normalize_slug()`

**Direct Team Model Imports:**
- Multiple views import `apps.teams.models.Team` and `TeamMembership`
- Creates tight coupling to teams architecture
- IntegerField team_id is a workaround, not a solution

**Assessment:** **Views are feature-complete but tightly coupled** to legacy game logic and teams app internals.

---

## 5. Templates & Frontend Behavior

### 5.1 Template Organization

**Template Structure:**
```
templates/tournaments/
├── list.html, list_redesigned.html → Tournament listing
├── detailPages/
│   ├── detail.html → Tournament detail (764 lines!)
│   └── partials/ → Hero, tabs, CTA, etc.
├── registration/ → Registration wizard templates
├── lobby/ → Tournament lobby and check-in
├── organizer/ → Organizer hub (participants, payments, matches, disputes)
├── spectator/ → Public spectator view
├── groups/ → Group stage templates
├── form_builder/ → Dynamic form builder
├── analytics/ → Registration analytics
├── responses/ → Response export
└── components/ → Reusable components
```

**Assessment:** **Well-organized template hierarchy** with proper component separation.

---

### 5.2 Frontend Assumptions (⚠️ Legacy Coupling)

#### **Hardcoded Game Slugs in Templates**

**In `detail.html` (lines 14-67):**
```django
{% if game_spec.slug == 'valorant' %}
    <div class="... from-red-950/40 ..."></div>
{% elif game_spec.slug == 'cs2' or game_spec.slug == 'csgo' %}
    <div class="... from-orange-950/40 ..."></div>
{% elif game_spec.slug == 'mlbb' or game_spec.slug == 'mobile_legends' %}
    <div class="... from-blue-950/40 ..."></div>
...
{% endif %}
```

**Problem:** Template assumes specific game slugs and hardcodes visual styles per game.

**Solution:** Game-specific branding should come from:
- `apps.games.Game.primary_color`, `secondary_color` fields
- Or JSONB `game_config.branding` section

---

#### **GAMES Dictionary Assumption**

**In `list_redesigned.html`:**
- Template expects `games` context variable (list of games)
- Uses `{{ games|length }}` for stats

**Current Implementation:**
- Views pass `games` from legacy Game model
- Should migrate to `apps.games.Game.objects.filter(is_active=True)`

---

### 5.3 Template Tag Dependencies

**Custom Template Tags:**
- `{% load tournament_filters %}` → Tournament-specific filters
- `{% load tournament_tags %}` → Custom tags

**Assessment:** Template tags likely contain legacy logic that needs audit.

---

## 6. Integration with Other Apps

### 6.1 Integration with apps.games (⚠️ Incomplete)

**Current State:**
- ❌ Tournament model uses **legacy Game model**, NOT apps.games.Game
- ⚠️ Partial GameService usage in some views (leaderboard, spectator)
- ❌ Hardcoded game slug logic throughout views and services
- ⚠️ Game-specific point calculations in tournaments/games/points.py

**Expected Integration:**
- ✅ Tournament.game → ForeignKey to apps.games.Game
- ✅ GameService.get_game_config() for all game-specific logic
- ✅ Profile field mapping from apps.games.IdentityField
- ✅ Point calculation rules from apps.games.Game.scoring_config

**Migration Path:**
1. Add migration to change Tournament.game ForeignKey to apps.games.Game
2. Migrate Game data to apps.games.Game
3. Refactor all hardcoded game slug checks to use GameService
4. Move point calculation logic to apps.games scoring config

---

### 6.2 Integration with apps.teams (⚠️ Tight Coupling)

**Current State:**
- ✅ Registration.team_id → IntegerField (workaround for circular dependency)
- ✅ Views import Team and TeamMembership for team registration
- ⚠️ BracketService ranked seeding assumes Team.ranking field exists
- ✅ Permission request workflow for team registration

**Issues:**
- IntegerField team_id prevents proper foreign key constraints
- Direct model imports create tight coupling
- Assumes apps.teams architecture (may not be fully implemented)

**Recommendation:**
- Keep IntegerField approach until teams app is stable
- Use TeamService abstraction layer instead of direct imports
- Define clear API contract between tournaments and teams

---

### 6.3 Integration with apps.economy (✅ Good)

**Current State:**
- ✅ PaymentService integrates with economy services
- ✅ DeltaCoin balance checks and deductions
- ✅ Automatic verification for DeltaCoin payments
- ✅ Refund processing on cancellation
- ✅ PayoutService integrates with economy.services.award
- ✅ Transaction tracking with idempotency

**Models Used:**
- `DeltaCrownWallet` → User wallet
- `DeltaCrownTransaction` → Transaction history

**Assessment:** **Excellent integration**. Economy integration is well-designed.

---

### 6.4 Integration with apps.notifications (✅ Good)

**Current State:**
- ✅ NotificationService integrates with notifications app
- ✅ Sends notifications for:
  - Registration confirmation
  - Payment verification
  - Match results
  - Tournament updates
  - Dispute resolution

**Assessment:** **Solid integration**. Notification dispatching is properly abstracted.

---

### 6.5 Integration with apps.user_profile (⚠️ Hardcoded)

**Current State:**
- ✅ Auto-fill registration data from UserProfile
- ⚠️ Hardcoded field mapping by game slug
- ❌ Does NOT use apps.games.IdentityField

**Hardcoded Logic:**
```python
if game_slug == 'valorant':
    auto_filled['game_id'] = profile.riot_id
elif game_slug == 'pubg-mobile':
    auto_filled['game_id'] = profile.pubg_mobile_id
...
```

**Expected Behavior:**
- ✅ Query `apps.games.IdentityField` for game's profile field
- ✅ Use GameService.get_identity_field_name(game)
- ✅ Generically retrieve profile value

**Assessment:** **Needs refactoring** to use apps.games architecture.

---

### 6.6 No Integration Found

- ❌ `apps.ecommerce` → No direct integration
- ❌ `apps.shop` → No direct integration
- ❌ `apps.moderation` → No content moderation integration

**Note:** These may not be needed for tournaments app.

---

## 7. Technical Debt & Legacy Patterns

### 7.1 Major Technical Debt Items

#### **1. Dual Game Architecture (Critical)**

**Problem:**
- Tournament model references **legacy Game model**
- apps.games.Game exists as modern replacement
- Two sources of truth for game data
- Inconsistent usage throughout codebase

**Impact:**
- Confusion about which Game model to use
- Duplicated game configuration
- Impossible to fully leverage apps.games features

**Effort:** High (requires migration, refactoring)

---

#### **2. Hardcoded Game Logic (High Priority)**

**Locations:**
- `registration_wizard.py` → Profile field mapping
- `leaderboard.py` → Point calculations
- `games/points.py` → BR game scoring
- Templates → Visual styling by game slug

**Impact:**
- Non-scalable (adding new game requires code changes)
- Violates Open/Closed Principle
- Makes testing difficult

**Effort:** Medium (refactor to data-driven config)

---

#### **3. IntegerField Team References (Medium Priority)**

**Problem:**
- `Registration.team_id` is IntegerField, not ForeignKey
- `Match.participant1_id`, `participant2_id` are IntegerField
- Prevents database-level referential integrity
- No cascade delete behavior

**Reason:** Circular dependency avoidance

**Impact:**
- Orphaned references possible if team deleted
- Manual integrity checks required
- More complex queries

**Effort:** Low-Medium (architecture decision needed)

---

#### **4. Incomplete apps.games Migration (High Priority)**

**Problem:**
- Partial GameService usage
- Legacy Game model still in use
- Inconsistent integration patterns

**Impact:**
- Can't leverage new game features
- Duplicated game logic
- Confusion for developers

**Effort:** High (systematic refactoring)

---

### 7.2 Missing Features for Production

#### **1. Dispute Resolution Workflow**

**Current State:**
- ✅ Dispute model exists
- ✅ Admin can review and resolve
- ❌ No automated evidence collection
- ❌ No participant communication thread
- ❌ No SLA tracking for dispute resolution

**Recommendation:** Enhance dispute system with:
- Evidence upload (screenshots, videos)
- Comment thread for back-and-forth
- Escalation workflow
- Auto-resolution after timeout

---

#### **2. Automated Scheduling**

**Current State:**
- ❌ No automatic match scheduling
- ❌ Organizer must manually set match times
- ❌ No conflict detection (participants in multiple matches)

**Recommendation:** Build scheduling service:
- Auto-schedule based on tournament start time
- Detect and prevent conflicts
- Send reminders before matches

---

#### **3. Prize Distribution Automation**

**Current State:**
- ✅ PayoutService exists
- ⚠️ Requires manual trigger by organizer
- ❌ No bulk payout workflow
- ❌ No payout verification/confirmation

**Recommendation:**
- Auto-trigger payouts on tournament completion
- Bulk payout UI for organizers
- Participant confirmation workflow

---

#### **4. Comprehensive Testing**

**Current State:**
- ⚠️ tests/ directory exists but coverage unknown
- ❌ No visible integration tests for critical flows
- ❌ No end-to-end tests for registration → bracket → match → payout

**Recommendation:**
- Write integration tests for all user flows
- Add E2E tests with Selenium/Playwright
- Target 80%+ code coverage

---

#### **5. Real-time Updates for All States**

**Current State:**
- ✅ WebSocket support for brackets and matches
- ⚠️ Not all state changes broadcast in real-time
- ❌ No real-time registration count updates
- ❌ No real-time leaderboard updates

**Recommendation:**
- Broadcast all tournament state changes
- Real-time participant count on tournament list
- Live leaderboard updates during matches

---

### 7.3 Code Quality Issues

#### **1. Massive Service Files**

- `registration_service.py` → 1,710 lines
- `bracket_service.py` → 1,250 lines

**Problem:** Hard to navigate and maintain

**Recommendation:** Split into smaller modules:
- `registration_service/core.py`, `registration_service/payment.py`, etc.

---

#### **2. Inconsistent Error Handling**

- Some services raise ValidationError
- Others raise custom exceptions
- No standardized error response format

**Recommendation:**
- Define tournament-specific exceptions
- Standardize error handling across services
- Use consistent error response format for API

---

#### **3. Weak Type Safety**

- ✅ Type hints present in many places
- ⚠️ Not comprehensive
- ❌ No mypy enforcement

**Recommendation:**
- Add type hints to all public methods
- Run mypy in CI/CD pipeline
- Enforce strict mode

---

## 8. Summary: What's Solid vs Fragile

### 8.1 Solid Foundations ✅

**Models:**
- ✅ Well-structured with proper constraints and indexes
- ✅ Soft delete support where needed
- ✅ JSONB flexibility for game-specific data
- ✅ Comprehensive coverage of tournament lifecycle

**Service Layer:**
- ✅ Business logic properly abstracted from views
- ✅ Transaction safety with @transaction.atomic
- ✅ Good separation of concerns
- ✅ Comprehensive feature coverage

**Integration:**
- ✅ Economy integration is excellent
- ✅ Notification integration is solid
- ✅ Payment processing is well-designed

**Admin:**
- ✅ Comprehensive Django admin with 8 specialized modules
- ✅ Inline editors for related models
- ✅ Proper filtering and search

**Frontend:**
- ✅ Well-organized templates
- ✅ Comprehensive URL coverage
- ✅ All major user flows implemented

---

### 8.2 Fragile Areas ⚠️

**Architecture:**
- ⚠️ Dual Game model architecture (legacy + apps.games)
- ⚠️ Hardcoded game logic throughout codebase
- ⚠️ Incomplete migration to apps.games
- ⚠️ IntegerField team references (workaround, not solution)

**Game Integration:**
- ⚠️ Inconsistent use of GameService
- ⚠️ Hardcoded game slug conditionals
- ⚠️ Profile field mapping not using IdentityField
- ⚠️ Point calculations hardcoded, not data-driven

**Teams Integration:**
- ⚠️ Tight coupling to apps.teams models
- ⚠️ Direct imports instead of service abstraction
- ⚠️ Ranked seeding assumes team rankings exist

**Templates:**
- ⚠️ Hardcoded game slugs for styling
- ⚠️ Assumes legacy Game model in context
- ⚠️ No dynamic branding from game config

**Missing Features:**
- ⚠️ Dispute resolution workflow incomplete
- ⚠️ No automated scheduling
- ⚠️ Prize distribution requires manual trigger
- ⚠️ Incomplete real-time updates
- ⚠️ Testing coverage unknown

---

## 9. Recommendations for Modernization

### 9.1 Immediate Priorities (Pre-TournamentOps)

1. **Migrate to apps.games.Game**
   - Change Tournament.game ForeignKey target
   - Migrate data from legacy Game to apps.games.Game
   - Remove legacy Game model

2. **Refactor Hardcoded Game Logic**
   - Replace all `if game_slug ==` with GameService calls
   - Use IdentityField for profile mapping
   - Move point calculations to game config

3. **Standardize Team Integration**
   - Create TeamService abstraction
   - Replace direct Team imports with service calls
   - Document IntegerField team_id pattern

4. **Enhance Dispute System**
   - Add evidence upload
   - Build comment thread
   - Implement SLA tracking

5. **Add Automated Tests**
   - Integration tests for critical flows
   - E2E tests for registration → payout
   - Target 80% coverage

### 9.2 Long-Term Goals (TournamentOps App)

When building the new TournamentOps/TournamentManagement app:

1. **Use This as Reference, Not Truth**
   - Learn from the solid patterns (service layer, soft deletes)
   - Avoid the fragile patterns (hardcoded logic, dual architecture)

2. **Design for Scalability**
   - Game logic should be 100% data-driven
   - No hardcoded game slugs anywhere
   - Use GameService for all game-specific behavior

3. **Proper Foreign Keys**
   - Tournament → ForeignKey to apps.games.Game
   - Participant → Polymorphic or GenericForeignKey to Team/User
   - Avoid IntegerField workarounds

4. **Comprehensive Testing**
   - Write tests alongside features
   - Integration tests for all flows
   - E2E tests for critical paths

5. **Real-time by Default**
   - All state changes broadcast via WebSocket
   - Live updates for all participants
   - Real-time leaderboards

---

## 10. Conclusion

The tournaments app is a **feature-rich, well-architected system** with excellent service layer design, comprehensive admin tools, and solid integrations with economy and notifications.

However, it suffers from **dual architecture syndrome** with legacy Game model and hardcoded game logic coexisting alongside modern apps.games integration. This creates technical debt that must be addressed.

**For the new TournamentOps app:**
- ✅ **Adopt:** Service layer pattern, soft deletes, JSONB flexibility, transaction safety
- ❌ **Avoid:** Hardcoded game logic, dual model architecture, tight coupling to other apps
- 🎯 **Goal:** 100% data-driven, game-agnostic tournament system

**Key Takeaway:** The tournaments app is **production-ready but needs refactoring** before it can serve as the foundation for a truly scalable, multi-game tournament platform.

---

**End of Audit**  
**Next Step:** Use this audit to inform the design of the new TournamentOps app in the upcoming modernization sprint.
