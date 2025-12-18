# Tournament System Legacy Documentation Audit

**Audit Date:** December 19, 2025  
**Audit Type:** Read-Only Documentation Analysis  
**Purpose:** Understand the previous developer's architectural intent for the Tournament system before building Django Templates dashboard

---

## Executive Summary

The previous developer planned a comprehensive **Service-Oriented Architecture (SOA)** transformation of DeltaCrown's tournament system, introducing a dedicated **`apps/tournament_ops`** orchestration layer to coordinate workflows across multiple domain apps. The documentation reveals a 10-phase, 48-week modernization plan with extensive emphasis on:

- **Eliminating tight coupling** via adapter pattern (zero direct cross-app model imports)
- **Event-driven architecture** for reactive stat updates and cross-domain coordination
- **Configuration-over-code** for game-specific logic (support 11 games without code changes)
- **Headless service layer** with no views/templates/URLs in `tournament_ops`
- **API-first design** preparing for future React/Next.js frontend (though explicitly rejected now)

**Current Reality:** Implementation is **~75% complete** through Phase 9, with core service layers, adapters, DTOs, and bracket generators operational. However, the system remains **headless** — no Django templates or traditional views exist to expose the service layer to users.

---

## 1. Documentation Analysis by File

### 1.1 `TOURNAMENT_OPS_DESIGN.md` (2,586 lines)

**Purpose:**  
Master specification defining the conceptual domain model, service contracts, and cross-app integration patterns for the `tournament_ops` orchestration layer.

**Key Architectural Ideas:**
- **TournamentOps as Pure Orchestrator:** Does NOT own tournament data (that's `apps/tournaments`), only operational state (registrations-in-flight, match operations, disputes, audit logs)
- **Domain Entities Defined:**
  - `TournamentOperationalState` — tracks tournament phase, operator locks, health metrics
  - `TournamentPhase` — discrete lifecycle stages (Registration → Check-In → Bracket Seeding → Live → Completion)
  - `RegistrationEntity` — polymorphic participant (solo player or team), with eligibility check results
  - `MatchOperation` — match operational state machine (Scheduled → Check-In → Ready → In Progress → Verified → Completed)
  - `DisputeTicket` — formal dispute workflow with evidence, SLA tracking, moderator assignment
  - `ResultSubmission` — multiple result claims per match, consensus-based auto-verification
  - `OpsActionLog` — audit trail for all operator/admin actions with rollback capability
  - `RewardDistribution` — prize allocation workflow (DeltaCoin + physical prizes)
  - `CertificateRecord` — cryptographically-signed achievement certificates

**Promised Behaviors:**
- **Registration Workflow:** Eligibility checks → Registration submission → Payment processing → Confirmation (coordinating `GameService`, `TeamService`, `EconomyService`)
- **Match Operations:** Scheduling → Check-in tracking → Lobby creation (via external game APIs) → State transitions → Result verification
- **Result Verification:** Multi-party submissions → Consensus detection → Auto-verify or flag for admin review
- **Dispute Resolution:** Ticket creation → Moderator assignment → Evidence collection → Ruling → Result propagation
- **Standings Calculation:** Real-time standings based on game-specific scoring rules from `GameTournamentConfig`
- **Completion Cascade:** Winner determination → Certificate generation → Prize distribution → Global ranking sync

**Mentioned Apps/Modules:**
- **Owned by tournament_ops:** No models yet mentioned (service layer only)
- **Consumed Services:**
  - `apps.games.GameService` — game config, identity validation, lobby creation
  - `apps.teams.TeamService` — roster validation, captain checks
  - `apps.economy.services.PaymentService` — wallet operations (credit/debit/transfer)
  - `apps.accounts.UserService` — profile data, ban checks
  - `apps.notifications.NotificationService` — status updates
  - `apps.moderation.ModerationService` — ban enforcement, fraud investigation

**Explicit TODOs/Gaps/Risks:**
- ❌ **GameService API incomplete:** Expected methods like `check_player_eligibility()`, `create_tournament_lobby()` not yet implemented in `apps.games`
- ❌ **TeamRankingService broken:** Audit notes show import errors, tournament results don't update team rankings
- ❌ **EconomyService missing reservation API:** Needs `reserve_funds()`, `release_reservation()`, `capture_reservation()` for pending registrations
- ⚠️ **NotificationService undefined:** Expected API for check-in reminders, dispute updates not found in audit
- ⚠️ **ModerationService undefined:** Ban checking not integrated into eligibility checks

---

### 1.2 `Workplan/ARCH_PLAN_PART_1.md` (4,017 lines)

**Purpose:**  
High-level architectural vision defining domain boundaries, responsibilities, and service APIs for all 7 core platform apps.

**Key Architectural Ideas:**
- **Domain-Driven Design (DDD):** Each app owns specific entities and exposes service APIs
- **Zero Cross-Domain Model Imports:** All cross-app communication via service adapters
- **Event-Driven Stat Updates:** Match completion → cascading events → Team stats / User stats / Leaderboards / Achievements (all via event handlers)
- **Service API Contracts:** Each app defines expected methods other apps can call

**Architecture by Domain:**

1. **`apps/games/`** — Game Configuration Hub
   - **Owns:** Game catalog, roster configs, tournament configs, player identity configs, scoring rules
   - **API:** `GameService.get_game()`, `list_active_games()`, `normalize_slug()`, `get_roster_config()`, `get_identity_validation_rules()`

2. **`apps/teams/`** — Team Management
   - **Owns:** Team records, rosters, memberships, rankings, analytics
   - **API:** `TeamService.validate_roster()`, `check_tournament_eligibility()`, `TeamRankingService.update_ranking()`, `TeamStatsService` (event handlers)

3. **`apps/tournaments/`** — Tournament Data Layer
   - **Owns:** Tournament records, registrations, brackets, matches, results, prizes, certificates
   - **API:** `TournamentService`, `RegistrationService`, `MatchService`, `BracketService`

4. **`apps/tournament_ops/`** — Orchestration Layer
   - **Owns:** Workflow state, cross-domain coordination
   - **API:** `TournamentOpsService.process_registration_workflow()`, `finalize_tournament()`, `verify_manual_payment()`

5. **`apps/economy/`** — Virtual Currency
   - **Owns:** DeltaCoin wallets, transactions
   - **API:** `WalletService.deduct_funds()`, `add_funds()`, `validate_balance()`

6. **`apps/accounts/` + `apps/user_profile/`** — User Identity
   - **Owns:** Authentication, profiles, game account links, user stats
   - **API:** `ProfileService.get_profile()`, `UserStatsService` (event handlers)

7. **`apps/leaderboards/`** — Rankings (Planned)
   - **Owns:** Global leaderboards, seasonal rankings
   - **API:** Event-driven updates from tournament completions

**Promised Behaviors:**
- **Event-Driven Cascade:** One match completion → 5+ event handlers fire (bracket progression, team stats, match history, rankings, rewards, notifications)
- **Service Boundaries Enforced:** Architecture guard tests prevent direct model imports
- **Adapters as Integration Layer:** `tournament_ops/adapters/` directory contains all cross-domain communication logic

**What tournament_ops Should Do (per this doc):**
- Orchestrate multi-service workflows (e.g., registration = eligibility check + payment + notification)
- Coordinate complex operations spanning multiple domains
- Publish domain events for async updates
- Serve as "glue code" without owning core entities

**What tournament_ops Should NOT Do:**
- Own tournament/match/registration models (those stay in `apps/tournaments`)
- Contain views/templates/URLs (headless service layer)
- Implement game-specific logic (delegated to `GameService`)
- Directly manipulate team/user data (use adapters)

**Risks Identified:**
- ⚠️ **Architectural Drift Risk:** Document warns "Legacy patterns still exist, cleanup will take 12+ months"
- ⚠️ **Event Bus Not Production-Ready:** EventLog persistence mentioned but Celery integration incomplete
- ⚠️ **Feature Flag Management:** Multiple parallel code paths create complexity

---

### 1.3 `Workplan/LIFECYCLE_GAPS_PART_2.md` (3,418 lines)

**Purpose:**  
Gap analysis comparing ideal tournament lifecycle capabilities vs. DeltaCrown's current implementation across 6 stages.

**Key Findings per Stage:**

**Stage 1: Discovery & Browsing**
- ✅ Exists: Tournament list, filters, detail pages
- ❌ Missing: Countdown timers (JS), "Featured" tournament flag, email notifications, Discord integration

**Stage 2: Registration & Payment**
- ✅ Exists: Eligibility checks, auto-fill (7 games), DeltaCoin payment, manual proof upload, wizard steps
- ❌ Missing: Unique registration numbers (`VCT-2025-001234`), field locking (verified fields), draft persistence (UUID-based), email confirmation, real-time API validation, calendar invites (`.ics`)

**Stage 3: Bracket & Seeding**
- ✅ Exists: Single elimination bracket generation, bracket visualization, match status badges
- ❌ Missing: Auto-schedule first-round matches, ranking-based seeding, bracket preview/edit UI, Swiss format, winner path highlighting

**Stage 4: Match Operations**
- ✅ Exists: Match state machine, check-in tracking, result submission, WebSocket broadcasts
- ❌ Missing: Lobby creation integration (external game APIs), automated check-in reminders, dispute resolution UI

**Stage 5: Tournament Completion**
- ✅ Exists: Winner determination logic, `TournamentResult` model, idempotency checks
- ❌ Missing: Auto-certificate generation, auto-prize payout, team stats updates

**Stage 6: Post-Tournament**
- ✅ Exists: Certificate generation service, payout service
- ❌ Missing: Automatic stat propagation (team/user stats), ranking updates, match history population

**Manual Operations Needed (4A subsection):**
- ❌ **Manual Bracket Editing:** No drag-and-drop UI, no swap participants, no undo/redo
- ❌ **Manual Group Assignment:** Group stage models exist but no assignment UI, no auto-balance
- ❌ **Manual Scheduling:** No calendar view, no conflict detection, no bulk scheduling
- ❌ **Manual Rescheduling:** No timezone conversion, no participant notification integration

**Architectural Gaps Identified:**
- **Three Parallel Registration Systems:** Classic Wizard, Form Builder (dynamic fields), Legacy — needs consolidation
- **Session-Based Wizard Data:** Lost on session expiration, no cross-device resume
- **No Event-Driven Stats:** Manual admin updates required for team wins/losses

---

### 1.4 `SMART_REGISTRATION_AND_ARCH_PLAN_PART_6.md` (1,056 lines)

**Purpose:**  
Design recommendations for smart registration (dynamic auto-fill, field locking, eligibility rules) and event-driven architecture.

**Key Recommendations:**

**A. Dynamic Field Resolution via Game Config:**
```python
# Replace hardcoded:
if game_slug == 'valorant':
    auto_filled['game_id'] = profile.riot_id

# With configuration-driven:
identity_configs = game_service.get_identity_validation_rules(tournament.game)
for config in identity_configs:
    field_value = getattr(user_profile, config.field_name, None)
    if field_value:
        auto_filled[config.display_name] = AutoFillField(
            value=field_value,
            locked=config.is_immutable,  # Lock verified fields
            validation_pattern=config.validation_pattern
        )
```

**B. Field Locking Strategy:**
- **Critical Fields (Lock After Verification):** Riot ID, Steam ID, email, phone
- **Editable Fields:** Display name, Discord username, preferred contact method
- **Implementation:** `AutoFillField` DTO with `locked` boolean, template renders read-only inputs

**C. Unique Registration Number System:**
```python
class RegistrationDraft(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    registration_number = models.CharField(unique=True)  # "VCT-2025-001234"
    user = models.ForeignKey('accounts.User')
    tournament = models.ForeignKey('tournaments.Tournament')
    form_data = models.JSONField()
    submitted = models.BooleanField(default=False)
    
    class Meta:
        unique_together = [('user', 'tournament')]
```

**D. Eligibility Validation via Configuration:**
```python
class EligibilityRule(models.Model):
    tournament = models.ForeignKey('tournaments.Tournament')
    rule_type = models.CharField(choices=[
        ('MIN_AGE', 'Minimum Age'),
        ('MIN_RANK', 'Minimum Rank'),
        ('SERVER_LOCK', 'Server/Region Lock'),
        ('VERIFIED_ACCOUNT', 'Verified Account Required'),
    ])
    config = models.JSONField()  # {"min_rank": "Diamond"}
    error_message = models.TextField()
```

**E. Event-Driven Architecture:**
```python
# Match completion triggers cascading updates:
@transaction.atomic
def confirm_match_result(match_id: int):
    match.state = Match.COMPLETED
    match.save()
    
    events.publish(MatchCompletedEvent(...))
    
    # All downstream updates via event handlers:
    # - BracketService.advance_winner_to_next_round()
    # - TeamStatsService.record_match_result()
    # - MatchHistoryService.create_history_entry()
    # - RankingService.update_elo_ratings()
    # - EconomyService.award_match_rewards()
    # - NotificationService.notify_match_result()
```

**Gaps Addressed:**
- ❌ **Draft Persistence:** Currently session-only, needs database-backed with UUID resume
- ❌ **Cross-Device Resume:** No mechanism for `/register?draft=abc123-def456`
- ❌ **Real-Time Validation:** No field-level API endpoints
- ❌ **Atomic Submission:** Registration + Payment + Wallet deduction not in single transaction

---

### 1.5 `TOURNAMENT_LIFECYCLE_AND_PROPAGATION_PART_5.md` (617 lines)

**Purpose:**  
Document tournament lifecycle state machine, stage-by-stage breakdown, and auto-update status for stats/rankings.

**Tournament Status State Machine:**
```
DRAFT
  ↓
PENDING_APPROVAL (if approval required)
  ↓
PUBLISHED
  ↓
REGISTRATION_OPEN
  ↓
REGISTRATION_CLOSED
  ↓
LIVE (matches in progress)
  ↓
COMPLETED (all matches finished)
  ↓
ARCHIVED (optional)
```

**Auto-Updates per Stage:**

| Stage | What Happens | Auto-Updated? | Evidence |
|-------|--------------|---------------|----------|
| **Registration Closed** | Bracket generation | ❌ Manual trigger | `BracketService.generate_bracket()` must be called explicitly |
| **Match Completed** | Bracket progression | ✅ Yes | `BracketService.update_bracket_after_match()` |
| **Match Completed** | WebSocket broadcast | ✅ Yes | `match_completed` event fired |
| **Match Completed** | Player stats | ❌ No | TODO comment in code: "Update player stats - Module 2.x" |
| **Match Completed** | DeltaCoin rewards | ❌ No | TODO comment: "Award DeltaCoin for win - Module 2.x" |
| **Tournament Completed** | `TournamentResult` created | ✅ Yes | Idempotent winner determination |
| **Tournament Completed** | Team stats | ❌ No | No service hooks found |
| **Tournament Completed** | Certificates | ❌ Manual trigger | Organizer must click "Generate Certificates" |
| **Tournament Completed** | Prize payouts | ❌ Manual trigger | `PayoutService.process_payouts()` called explicitly |
| **Tournament Completed** | Team rankings | ❌ No | `TeamRankingService` import broken, no integration |

**Critical Findings:**
- ✅ **Core Progression Works:** Match winner advances to next bracket round automatically
- ✅ **Idempotency Guaranteed:** Re-running completion doesn't duplicate results
- ❌ **Stats Not Auto-Updated:** `TeamAnalytics` model exists but never populated
- ❌ **No User Stats Model:** No `UserStats` or `PlayerStats` model found in codebase
- ❌ **Rankings Broken:** `TeamRankingService.update_ranking()` expected but not implemented
- ❌ **Match History Not Populated:** `TeamMatchHistory` model exists, never written to

---

### 1.6 `REGISTRATION_BACKEND_MODELS_PART_1.md` (394 lines)

**Purpose:**  
Audit of registration data models, constraints, and validation layers.

**Core Models:**

**1. Tournament:**
- **Dual Game Problem:** Uses legacy `tournaments.Game` (FK) instead of modern `apps.games.Game`
- **Key Fields:** `status` (state machine), `participation_type` (SOLO/TEAM), `max_participants`, `entry_fee`, `payment_methods` (ArrayField)

**2. Registration:**
- **XOR Constraint:** `(user IS NOT NULL AND team_id IS NULL) OR (user IS NULL AND team_id IS NOT NULL)`
- **Loose Coupling:** `team_id = IntegerField` (not ForeignKey) to avoid circular dependency with `apps.teams`
- **Flexible Storage:** `registration_data = JSONField` for game-specific fields
- **Status Workflow:** `DRAFT → SUBMITTED → PENDING → CONFIRMED / REJECTED / CANCELLED`

**3. Payment:**
- **Proof Upload:** Manual payment requires `payment_proof` (ImageField)
- **Admin Verification:** `verified_by` (FK to User), `verified_at` (DateTime)
- **Status:** `pending → verified / rejected`

**Auto-fill Mechanism:**
- ✅ **Exists:** `RegistrationAutoFillService.get_autofill_data()`
- ❌ **Hardcoded:** 7 if-else checks for game slugs instead of `GamePlayerIdentityConfig`
- ✅ **Completion Tracking:** Calculates % complete based on filled fields

**Validation Layers:**
1. **Database Constraints:** XOR, unique registrations, unique slots
2. **Service Layer:** `RegistrationService.check_eligibility()`
3. **Model Level:** `Registration.clean()` method

**Risk Areas:**
- ⚠️ **No Referential Integrity:** `team_id` as IntegerField means orphaned registrations possible if team deleted
- ⚠️ **Direct Model Imports:** `from apps.teams.models import Team, TeamMembership` throughout services

---

### 1.7 `CROSS_APP_INTEGRATION_AUDIT.md` (1,356 lines)

**Purpose:**  
Map cross-app dependencies to inform `tournament_ops` adapter design.

**Critical Findings:**

**A. Dual Game Architecture Confusion:**
- ❌ `Tournament.game` → `tournaments.Game` (legacy model)
- ✅ `apps.games.Game` — modern model with full config
- ⚠️ **50+ references** to `game_service` in tournaments code (partial migration underway)

**B. Hardcoded Game Logic (Legacy Patterns):**
```python
# registration_wizard.py lines 479-491
if game_slug == 'valorant':
    auto_filled['game_id'] = profile.riot_id
elif game_slug == 'pubg-mobile':
    auto_filled['game_id'] = profile.pubg_mobile_id
# ... 7 total games
```

**C. Tight Team Coupling:**
- ❌ **50+ direct imports** of `apps.teams.models.Team`, `TeamMembership`
- ✅ **IntegerField pattern** (`Registration.team_id`) avoids circular dependency
- ⚠️ **No TeamService abstraction** — tournaments directly query `TeamMembership`

**D. Economy Integration (Excellent):**
- ✅ **Well-designed:** `economy.services.credit()`, `debit()`, `transfer()` with idempotency
- ✅ **Properly used:** `PaymentService` calls `economy_services.debit()` for entry fees
- ❌ **Missing:** Reservation API (`reserve_funds()`, `capture_reservation()`) for pending registrations

**E. Broken Ranking Integration:**
```python
# result.py line 270
from apps.teams.services.game_ranking_service import game_ranking_service
# ❌ File does not exist — broken import
```

**Integration Patterns Summary:**

| Target App | Current Pattern | Desired Pattern | Status |
|------------|-----------------|-----------------|--------|
| **Games** | Mixed (direct model + GameService) | 100% GameService | ⚠️ In Progress |
| **Teams** | Direct model imports | TeamAdapter | ❌ Not Started |
| **Economy** | Clean service API | EconomyAdapter | ✅ Working Well |
| **Users** | Mixed (ForeignKey + direct Profile access) | UserAdapter | ⚠️ Partial |
| **Rankings** | Broken import | TeamRankingAdapter | ❌ Not Implemented |

---

### 1.8 Additional Workplan Files (Brief Scan)

**`Workplan/DEV_PROGRESS_TRACKER.md` (3,758 lines):**
- **Phase Status:** Phases 1-9 marked COMPLETED (December 11, 2025)
- **Epic 1.1:** Service Adapter Layer ✅ (43 tests passing)
- **Epic 1.2:** Event Bus Infrastructure ✅ (with Celery integration)
- **Epic 1.3:** DTO Patterns ✅ (all DTOs have `from_model()` + `validate()`)
- **Epic 1.4:** TournamentOps Service Layer ✅ (71/71 tests passing)
- **Epic 3.1:** Bracket Generators ✅ (30+ tests, feature flag enabled)
- **Epic 4.1-4.3:** Registration/Lifecycle/Match services ✅ (54/54 tests passing)
- **Epic 5.x:** Smart Registration (partially done, UI missing)
- **Epic 6.x:** Result Pipeline & Disputes ✅ (backend complete)
- **Epic 7.x:** Organizer Console ✅ (services complete, UI missing)
- **Epic 8.x:** Event-Driven Stats ✅ (EventBus hardening, UserStats/TeamStats services, MatchHistory, Analytics)
- **Epic 9.x:** Frontend Developer Support ✅ (API Docs, TypeScript SDK, UI/UX Framework, Boilerplate, Dev Guides)
- **Phase 10:** Advanced Features (NOT STARTED) — Notifications, Discord bot, achievements, mobile app

**`Workplan/ROADMAP_AND_EPICS_PART_4.md` (2,025 lines):**
- **Total Timeline:** 48 weeks (~12 months), Phases 1-9 completed in ~3 months (ahead of schedule)
- **Dependencies:** Phase 1 → 2 → 3 → 4 → [5, 6, 7] (parallel) → 8 → 9 → 10
- **Epic Structure:** Each phase has 3-6 epics with detailed acceptance criteria
- **Testing Strategy:** Unit tests + integration tests + E2E tests per epic
- **Legacy Cleanup:** Planned for Phase 10+ (feature flags in place now)

**`Workplan/SMART_REG_AND_RULES_PART_3.md` (4,463 lines):**
- **Game Rules Layer:** `GameRulesEngine` with pluggable rules modules (Valorant, CSGO, default)
- **Match Result Schema:** JSON Schema validation for game-specific result structures
- **Smart Registration:** Configurable eligibility rules, auto-approval logic
- **Configuration Models:** `GamePlayerIdentityConfig`, `GameTournamentConfig`, `GameScoringRule`, `GameMatchResultSchema`

**`Workplan/CLEANUP_AND_TESTING_PART_6.md` (2,909 lines):**
- **Cleanup Categories:**
  1. **Refactor & Keep:** Core functionality with outdated patterns → refactor to services
  2. **Migrate Then Remove:** Completely replaced systems (e.g., `tournaments.Game` → `apps.games.Game`)
  3. **Delete (Dead/Obsolete):** `views_old_backup.py`, ad-hoc test files, commented code
- **Migration Strategy:** Feature flags → dual-write → switch reads → stop dual-write → remove old
- **Testing Philosophy:** Maintain ≥ current 213 test files, add adapter tests, service layer tests, E2E tests
- **Rollback Plan:** Keep old code paths active for 2-4 weeks during migration

---

## 2. Overall Intended Architecture Summary

### 2.1 The Vision (What the Developer Planned)

**Architecture Pattern:** Service-Oriented Architecture (SOA) with Event-Driven Domain Services

**Core Principles:**
1. **Domain Boundaries:** Each app owns specific entities, never share models directly
2. **Service APIs:** All cross-app communication via well-defined service methods
3. **Adapter Pattern:** `tournament_ops/adapters/` wraps external service calls
4. **DTO Pattern:** Data Transfer Objects decouple service interfaces from model structures
5. **Event-Driven Updates:** Domain events (e.g., `MatchCompletedEvent`) trigger cascading updates
6. **Configuration Over Code:** Game-specific logic driven by database config, not if-else chains
7. **Feature Flags:** Old and new code paths coexist during migration
8. **Headless Services:** `tournament_ops` provides orchestration logic, NOT UI

**Layered Architecture:**

```
┌───────────────────────────────────────────────────────────────┐
│  LAYER 1: PRESENTATION (NOT PART OF tournament_ops)          │
│  - Django Templates (to be built)                            │
│  - Django Views (to be built)                                │
│  - Forms & Context Builders (to be built)                    │
│  - AJAX/HTMX Progressive Enhancement (to be built)           │
└──────────────────────┬────────────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────────┐
│  LAYER 2: ORCHESTRATION (apps/tournament_ops)                │
│  - TournamentOpsService (facade)                             │
│  - RegistrationService (workflow coordination)               │
│  - TournamentLifecycleService (state machine)                │
│  - MatchOpsService (match operations)                        │
│  - ResultVerificationService (result pipeline)               │
│  - DisputeService (dispute resolution)                       │
│  - CompletionService (post-tournament cascade)               │
└──────────────────────┬────────────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────────┐
│  LAYER 3: ADAPTERS (tournament_ops/adapters)                 │
│  - GameAdapter → apps.games.GameService                      │
│  - TeamAdapter → apps.teams.TeamService                      │
│  - UserAdapter → apps.accounts / apps.user_profile           │
│  - EconomyAdapter → apps.economy.services                    │
│  - NotificationAdapter → apps.notifications                  │
│  - AnalyticsAdapter → Event-driven stats services            │
└──────────────────────┬────────────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────────┐
│  LAYER 4: DOMAIN SERVICES (per app)                          │
│  - apps.games.GameService (game config, validation)          │
│  - apps.teams.TeamService (roster, permissions)              │
│  - apps.tournaments (models + CRUD services)                 │
│  - apps.economy.services (wallet operations)                 │
│  - Event Handlers (TeamStatsService, UserStatsService)       │
└──────────────────────┬────────────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────────┐
│  LAYER 5: DATA LAYER (Django ORM Models)                     │
│  - tournaments.Tournament, Registration, Match, Bracket      │
│  - games.Game, GamePlayerIdentityConfig                      │
│  - teams.Team, TeamMembership, TeamAnalytics                 │
│  - economy.DeltaCrownWallet, DeltaCrownTransaction           │
└───────────────────────────────────────────────────────────────┘
```

**Data Flow Example (Registration):**
```
1. User submits registration form (LAYER 1 - to be built)
   ↓
2. Django View calls TournamentOpsService.register_participant() (LAYER 2)
   ↓
3. TournamentOpsService delegates:
   - GameAdapter.check_eligibility() → GameService (LAYER 3)
   - TeamAdapter.validate_roster() → TeamService (LAYER 3)
   - EconomyAdapter.charge_fee() → economy.services (LAYER 3)
   ↓
4. Domain services perform operations (LAYER 4)
   ↓
5. ORM models persist data (LAYER 5)
   ↓
6. Event published: RegistrationConfirmedEvent
   ↓
7. Event handlers fire (LAYER 4):
   - TeamStatsService.increment_tournaments_entered()
   - UserStatsService.record_registration()
   - NotificationService.send_confirmation()
```

---

### 2.2 What tournament_ops Was Intended to Be

**Responsibilities:**

1. **Workflow Orchestration:**
   - Coordinate multi-step processes spanning multiple apps
   - Example: Registration = eligibility check (games) + payment (economy) + notification (notifications)
   - Example: Tournament completion = winner determination + certificates + prizes + stats updates

2. **Cross-Domain Coordination:**
   - Call services from multiple apps in correct order
   - Maintain transactional consistency across domains
   - Handle failures gracefully (rollback, retry, compensating transactions)

3. **Business Process Implementation:**
   - Registration workflow (draft → eligibility → payment → confirmation)
   - Match operations workflow (schedule → check-in → play → submit → verify → complete)
   - Dispute resolution workflow (open → assign → evidence → ruling → propagate)
   - Completion workflow (finalize → certificates → prizes → rankings)

4. **Event Publishing:**
   - Emit domain events at workflow milestones
   - Allow other apps to react asynchronously
   - Maintain event log for audit trail

5. **Operational State Management:**
   - Track workflow-specific state not owned by core domains
   - Example: `MatchOperationalState` (check-in status, lobby info, operator notes)
   - Example: `DisputeTicket` (dispute workflow state, evidence, SLA tracking)

6. **Adapter Abstraction:**
   - Provide adapters that wrap external service calls
   - Isolate tournament logic from changes in other apps
   - Enable testing via mocked adapters

**What It Should NOT Do:**

1. ❌ **Own Core Domain Models:**
   - Tournaments, Matches, Registrations → owned by `apps/tournaments`
   - Teams → owned by `apps/teams`
   - Users → owned by `apps/accounts` / `apps/user_profile`

2. ❌ **Contain Views/Templates/URLs:**
   - `tournament_ops` should be 100% headless
   - Views/templates live in `apps/tournaments/views/` and `apps/tournaments/templates/`
   - Forms live in `apps/tournaments/forms/`

3. ❌ **Implement Game-Specific Logic:**
   - Point calculations, scoring rules → `GameRulesEngine` in `apps/games`
   - Identity validation (Riot ID format) → `GamePlayerIdentityConfig`

4. ❌ **Directly Access Other App Models:**
   - Never `from apps.teams.models import Team`
   - Always `team = TeamAdapter().get_team(team_id)`

5. ❌ **Perform Low-Level CRUD:**
   - Creating a Match → `MatchService.create_match()` in `apps/tournaments`
   - TournamentOps only orchestrates, doesn't CRUD

**In Summary:**  
`tournament_ops` is the **conductor of an orchestra** — it coordinates the musicians (domain services) but doesn't play any instruments (own models) or perform for the audience (no views).

---

### 2.3 Key Assumptions Made by Previous Developer

**About the Frontend:**
1. ✅ **API-First Design:** Services return DTOs, easily serializable to JSON
2. ✅ **Headless Backend:** Frontend could be React/Next.js (now rejected) or Django Templates
3. ⚠️ **WebSocket Support:** Real-time updates mentioned (match_completed events) but implementation unclear
4. ⚠️ **AJAX/Progressive Enhancement:** Assumed but not detailed

**About Data Migration:**
1. ✅ **Feature Flags Everywhere:** Old and new code paths coexist (see `BRACKETS_USE_UNIVERSAL_ENGINE` setting)
2. ✅ **Dual-Write Pattern:** Write to both old and new systems during migration
3. ⚠️ **Long Migration Timeline:** 12+ months expected for full legacy cleanup
4. ⚠️ **Backward Compatibility:** Old tournaments must continue working during migration

**About Testing:**
1. ✅ **Test-Driven:** Every epic has acceptance criteria and test requirements
2. ✅ **Adapter Mocking:** Services tested with mocked adapters (71/71 tests passing)
3. ✅ **E2E Pipeline Tests:** Stage transitions, bracket generation tested end-to-end
4. ⚠️ **Frontend Tests Undefined:** No mention of template rendering tests, form tests, view tests

**About Deployment:**
1. ⚠️ **Gradual Rollout:** New code behind feature flags, enabled per tournament
2. ⚠️ **Rollback Capability:** Keep old code paths for 2-4 weeks
3. ⚠️ **Zero Downtime:** Migrations designed to run alongside live system
4. ❌ **Monitoring Strategy:** Event logging mentioned but no observability plan

**About the Team:**
1. ⚠️ **Solo Developer Assumption:** Documentation assumes future developers will read this (no handoff process defined)
2. ⚠️ **12-Month Timeline:** Phase 10 planned but never started (work stopped at Phase 9)
3. ⚠️ **Frontend Developer Support:** Phase 9 deliverables (API docs, SDK, UI specs) suggest separate frontend team
4. ❌ **Organizer Training:** No mention of user documentation, training materials, or change management

---

## 3. Critical Gaps & Risks for Django Templates Dashboard

### 3.1 What Exists (Green Light)

✅ **Service Layer Complete:**
- `TournamentOpsService`, `RegistrationService`, `TournamentLifecycleService`, `MatchOpsService` (71+ tests passing)
- All return DTOs, can be called from Django views
- Transactional guarantees in place

✅ **Adapters Implemented:**
- `GameAdapter`, `TeamAdapter`, `UserAdapter`, `EconomyAdapter` (43 adapter tests passing)
- Clean API to call cross-domain services

✅ **Event Bus Operational:**
- EventLog model persists events
- Event handlers registered and tested
- Celery integration for async processing

✅ **Bracket Generators:**
- Single/Double Elimination, Round Robin, Swiss generators (30+ tests)
- `BracketEngineService` orchestrator with format registry

✅ **Result Verification:**
- `ResultVerificationService`, `DisputeService` implemented
- Dispute models (`DisputeRecord`, `DisputeEvidence`) exist

✅ **Economy Integration:**
- `economy.services` well-designed (credit/debit/transfer)
- Idempotency keys supported
- `PaymentService` properly calls `economy_services.debit()`

### 3.2 What's Missing (Red Flags)

❌ **NO VIEWS/TEMPLATES/URLS in tournament_ops:**
- `tournament_ops` is 100% headless (no user-facing layer)
- All 20+ views live in `apps/tournaments/views/`
- Dashboard building must happen in `apps/tournaments/`, NOT `tournament_ops/`

❌ **Incomplete Service Methods:**
- `GameService.check_player_eligibility()` — expected but not found
- `GameService.create_tournament_lobby()` — expected but not found
- `TeamService` — doesn't exist (direct model imports everywhere)
- `NotificationService` — undefined API (expected but missing)
- `ModerationService.check_active_bans()` — expected but not found

❌ **Broken Integrations:**
- `TeamRankingService` import broken (`game_ranking_service.py` doesn't exist)
- Tournament completion doesn't update team rankings
- Match completion doesn't update team/user stats (TODO comments in code)

❌ **Missing Auto-Updates:**
- Team stats (`tournaments_participated`, `tournaments_won`) never incremented
- User stats model doesn't exist (`UserStats`, `PlayerStats` models missing)
- Match history (`TeamMatchHistory`) model exists but never populated
- Rankings/leaderboards not updated on tournament completion

❌ **Draft Persistence Not Implemented:**
- Registration drafts are session-only (no database backing)
- No UUID-based cross-device resume
- No registration numbers (`VCT-2025-001234` format)

❌ **Field Locking Not Implemented:**
- All auto-filled fields editable (should lock verified email, Riot ID, etc.)
- `AutoFillField.locked` concept defined in docs but not in code

❌ **Manual Operations UI Missing:**
- Bracket editor (drag-and-drop, swap participants) — no UI
- Group assignment (create groups, assign teams) — no UI
- Manual scheduling (calendar view, set match times) — no UI
- Results inbox (review pending results) — backend service exists, no frontend

### 3.3 Blockers for Building Dashboard

**High Priority (Must Fix):**

1. **Service Method Gaps:**
   - Implement `GameService.check_player_eligibility()`
   - Implement `TeamService` (replace direct model imports)
   - Define `NotificationService` API
   - Fix broken `TeamRankingService` import

2. **Stat Propagation:**
   - Create `UserStats` / `PlayerStats` model
   - Add event handlers to update team/user stats on match completion
   - Implement `TeamRankingService.update_ranking()`
   - Populate `TeamMatchHistory` on match completion

3. **Registration Enhancements:**
   - Implement `RegistrationDraft` model with UUID
   - Add registration number generation
   - Implement field locking logic
   - Add API endpoints for draft save/resume

**Medium Priority (Nice to Have):**

4. **Manual Operations:**
   - Build bracket editor UI (drag-and-drop)
   - Build group assignment UI
   - Build scheduling calendar UI
   - Build results inbox dashboard

5. **Notifications:**
   - Implement email confirmation (registration, match results)
   - Add check-in reminders
   - Add dispute status updates

**Low Priority (Deferred):**

6. **Advanced Features:**
   - Discord bot integration
   - Mobile app support
   - Achievement/badge system
   - Advanced analytics

---

## 4. Recommended Integration Strategy for Django Templates

### 4.1 Phased Approach

**Phase 1: Service Layer Integration (2-3 weeks)**
- Build Django views that call existing `TournamentOpsService` methods
- Create context builders that convert DTOs → template context
- Build forms that call service methods on POST
- Keep existing templates, enhance with service-layer data

**Phase 2: Manual Operations UI (3-4 weeks)**
- Build results inbox (list pending results, approve/reject)
- Build simple bracket editor (no drag-and-drop, just manual overrides)
- Build scheduling UI (basic time picker, no calendar)

**Phase 3: Smart Registration (2-3 weeks)**
- Implement draft persistence (RegistrationDraft model)
- Add field locking in templates
- Build real-time validation API endpoints

**Phase 4: Stats & Notifications (2-3 weeks)**
- Create UserStats model
- Add event handlers for stat updates
- Implement email notifications

**Phase 5: Polish & Advanced Features (3-4 weeks)**
- Build advanced bracket editor (drag-and-drop)
- Add calendar view for scheduling
- Implement Discord integration

### 4.2 Integration Patterns

**Pattern 1: View → Service → Template**
```python
# apps/tournaments/views/registration.py
from apps.tournament_ops.services import TournamentOpsService

class TournamentRegistrationView(LoginRequiredMixin, FormView):
    template_name = 'tournaments/registration/wizard.html'
    form_class = RegistrationForm
    
    def form_valid(self, form):
        # Call service layer
        result = TournamentOpsService().register_participant(
            tournament_id=self.tournament.id,
            user_id=self.request.user.id,
            registration_data=form.cleaned_data,
            payment_method='deltacoin'
        )
        
        # Convert DTO to context
        context = {
            'registration': result.to_dict(),
            'payment_status': result.payment_result.status
        }
        
        return render(self.request, 'tournaments/registration/success.html', context)
```

**Pattern 2: Context Builder**
```python
# apps/tournaments/context_builders.py
from apps.tournament_ops.adapters import GameAdapter, TeamAdapter

class TournamentDetailContextBuilder:
    def __init__(self, tournament):
        self.tournament = tournament
        self.game_adapter = GameAdapter()
        self.team_adapter = TeamAdapter()
    
    def build(self):
        # Get game config via adapter
        game_config = self.game_adapter.get_game_config(self.tournament.game_id)
        
        # Get registrations via service
        registrations = RegistrationService.get_tournament_registrations(
            tournament_id=self.tournament.id,
            status_filter='confirmed'
        )
        
        return {
            'tournament': self.tournament,
            'game_config': game_config,
            'registrations': [r.to_dict() for r in registrations],
            'slots_filled': len(registrations),
            'slots_total': self.tournament.max_participants,
        }
```

**Pattern 3: Form with Service Validation**
```python
# apps/tournaments/forms/registration.py
from apps.tournament_ops.services import RegistrationService

class RegistrationForm(forms.Form):
    def clean(self):
        cleaned_data = super().clean()
        
        # Call service layer for eligibility check
        eligibility = RegistrationService.validate_registration(
            tournament_id=self.tournament.id,
            user_id=self.user.id,
            team_id=cleaned_data.get('team_id')
        )
        
        if not eligibility.is_eligible:
            raise ValidationError(eligibility.reasons)
        
        return cleaned_data
```

**Pattern 4: AJAX API for Progressive Enhancement**
```python
# apps/tournaments/views/registration_api.py
from django.http import JsonResponse
from apps.tournament_ops.services import RegistrationService

class SaveDraftAPIView(LoginRequiredMixin, View):
    def post(self, request, tournament_slug):
        draft_data = json.loads(request.body)
        
        # Call service to save draft
        draft = RegistrationService.save_draft(
            tournament_id=self.tournament.id,
            user_id=request.user.id,
            form_data=draft_data
        )
        
        return JsonResponse({
            'draft_uuid': str(draft.uuid),
            'registration_number': draft.registration_number,
            'resume_url': f'/tournaments/{tournament_slug}/register/?draft={draft.uuid}'
        })
```

### 4.3 What NOT to Do

❌ **Don't Create Views in tournament_ops:**
- `tournament_ops` should remain headless
- All views/templates go in `apps/tournaments/`

❌ **Don't Bypass Services:**
- Don't call `Registration.objects.create()` directly in views
- Always use `RegistrationService.create_registration()`

❌ **Don't Import Adapters in Views:**
- Views should only call orchestration services (`TournamentOpsService`)
- Adapters are internal to `tournament_ops`, not exposed to views

❌ **Don't Break Existing Tournaments:**
- Use feature flags for new features
- Keep old code paths working until migration complete

❌ **Don't Assume Services Are Complete:**
- Check if service method exists before calling
- Some methods in docs aren't implemented yet (e.g., `GameService.create_tournament_lobby()`)

---

## 5. Final Assessment

### 5.1 Architecture Quality: 9/10

**Strengths:**
- ✅ Clean service boundaries with adapter pattern
- ✅ Event-driven architecture for reactive updates
- ✅ DTO pattern decouples services from models
- ✅ Feature flags enable safe migration
- ✅ Comprehensive test coverage (71 service tests, 43 adapter tests, 30+ bracket tests)
- ✅ Configuration-over-code for game rules

**Weaknesses:**
- ⚠️ Some documented services not implemented (`GameService.check_player_eligibility()`, `TeamService`)
- ⚠️ Event handlers defined but stat models incomplete (`UserStats` missing)
- ⚠️ Broken imports (`TeamRankingService`)

### 5.2 Documentation Quality: 10/10

**Strengths:**
- ✅ Extremely detailed (15,000+ lines across 7 docs)
- ✅ Clear separation of concerns
- ✅ Explicit about what's missing vs. implemented
- ✅ Practical examples (code snippets, diagrams)
- ✅ Gap analysis with current state assessment

**Weaknesses:**
- ⚠️ Some docs assume React/Next.js frontend (now rejected)
- ⚠️ No explicit template/view layer documentation

### 5.3 Implementation Status: 75% Complete

**Completed:**
- ✅ Service layer (RegistrationService, TournamentLifecycleService, MatchOpsService)
- ✅ Adapters (GameAdapter, TeamAdapter, UserAdapter, EconomyAdapter)
- ✅ DTOs (TournamentDTO, RegistrationDTO, MatchDTO, etc.)
- ✅ Event bus (EventLog model, event handlers, Celery integration)
- ✅ Bracket generators (Single/Double Elim, Round Robin, Swiss)
- ✅ Result verification (ResultVerificationService, DisputeService)

**Incomplete:**
- ❌ Frontend layer (0% — no Django templates for service layer)
- ❌ Stat propagation (TeamStats/UserStats event handlers exist but models incomplete)
- ❌ Manual operations UI (bracket editor, group assignment, scheduling)
- ❌ Notification system (NotificationService undefined)
- ❌ Moderation integration (ModerationService undefined)

### 5.4 Readiness for Django Templates Dashboard: 7/10

**Ready:**
- ✅ Service layer can be called from views
- ✅ DTOs easily convert to template context
- ✅ Economy integration works (entry fees, payouts)
- ✅ Bracket generation works

**Blockers:**
- ❌ No example views/templates to follow
- ❌ Some service methods documented but not implemented
- ❌ Stat updates don't happen automatically (manual intervention required)
- ❌ No registration draft persistence (would need to build)

**Recommendation:**  
**Proceed with caution.** Service layer is solid, but frontend integration layer is 0% complete. Expect 4-6 weeks to build:
1. View layer calling services (2 weeks)
2. Context builders & forms (1 week)
3. Missing service methods (1 week)
4. Stat propagation fixes (1 week)
5. Manual operations UI (2 weeks)

---

## 6. Appendix: Critical File/Module Locations

### Services (Implemented)
- `apps/tournament_ops/services/registration_service.py` — Registration workflow
- `apps/tournament_ops/services/tournament_lifecycle_service.py` — Tournament state machine
- `apps/tournament_ops/services/match_ops_service.py` — Match operations
- `apps/tournament_ops/services/result_verification_service.py` — Result pipeline
- `apps/tournament_ops/services/dispute_service.py` — Dispute resolution
- `apps/tournament_ops/services/bracket_engine_service.py` — Bracket orchestrator
- `apps/tournament_ops/services/tournament_ops_service.py` — Main facade

### Adapters (Implemented)
- `apps/tournament_ops/adapters/game_adapter.py` — Games app integration
- `apps/tournament_ops/adapters/team_adapter.py` — Teams app integration
- `apps/tournament_ops/adapters/user_adapter.py` — Users app integration
- `apps/tournament_ops/adapters/economy_adapter.py` — Economy app integration
- `apps/tournament_ops/adapters/notification_adapter.py` — Notifications (placeholder)

### Models (Core Domain — apps/tournaments)
- `apps/tournaments/models/tournament.py` — Tournament, Game (legacy)
- `apps/tournaments/models/registration.py` — Registration, Payment
- `apps/tournaments/models/match.py` — Match, Dispute
- `apps/tournaments/models/bracket.py` — Bracket, BracketNode
- `apps/tournaments/models/result.py` — TournamentResult
- `apps/tournaments/models/dispute.py` — DisputeRecord, DisputeEvidence

### Services (Domain — apps/tournaments)
- `apps/tournaments/services/tournament_service.py` — Tournament CRUD
- `apps/tournaments/services/registration_service.py` — Registration logic (old)
- `apps/tournaments/services/match_service.py` — Match CRUD
- `apps/tournaments/services/bracket_service.py` — Bracket progression
- `apps/tournaments/services/bracket_generator.py` — Legacy bracket generation

### Views (User-Facing — apps/tournaments)
- `apps/tournaments/views/main.py` — Tournament list/detail
- `apps/tournaments/views/registration.py` — Old registration flow
- `apps/tournaments/views/registration_wizard.py` — Registration wizard
- `apps/tournaments/views/live.py` — Bracket view, match detail
- `apps/tournaments/views/lobby.py` — Check-in, lobby
- `apps/tournaments/views/organizer.py` — Organizer dashboard

### URLs
- `apps/tournaments/urls.py` — 382 lines, ~50 URL patterns
- **NOTE:** `apps/tournament_ops/` has NO urls.py (headless by design)

---

**End of Audit Report**

**Next Steps:**
1. Verify service method implementations (test if they exist)
2. Identify which views need to be built vs. refactored
3. Build context builders to bridge services → templates
4. Implement missing stat propagation
5. Create integration test suite for view → service → template flow
