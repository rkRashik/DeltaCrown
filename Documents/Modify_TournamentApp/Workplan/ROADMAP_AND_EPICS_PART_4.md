# Part 4: Development Roadmap & Epic Backlog

**Document Purpose**: High-level roadmap and epic definitions for transforming DeltaCrown into a modern, scalable esports platform.

**Created**: December 8, 2025  
**Scope**: 7-phase development plan with dependencies and stretch features

**Source Documents**:
- Part 1: ARCH_PLAN_PART_1.md (Architecture & Vision)
- Part 2: LIFECYCLE_GAPS_PART_2.md (Lifecycle Gaps Analysis)
- Part 3: SMART_REG_AND_RULES_PART_3.md (Smart Registration & Game Rules)

---

## Roadmap Overview

### Timeline Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: ARCHITECTURE FOUNDATIONS                       (Weeks 1-4)    │
│  Service boundaries, adapters, DTOs, event system foundation           │
└───────────────────────┬─────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────────────┐
│ PHASE 2: GAME RULES & CONFIGURATION SYSTEM              (Weeks 5-7)    │
│  Game config layer, rules engine, schema validation, scoring systems   │
└───────────────────────┬─────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────────────┐
│ PHASE 3: UNIVERSAL TOURNAMENT FORMAT ENGINE            (Weeks 8-12)    │
│  Bracket generators, group stage, Swiss, stage transitions, editors    │
└───────────────────────┬─────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────────────┐
│ PHASE 4: TOURNAMENTOPS CORE WORKFLOWS                  (Weeks 13-16)    │
│  Registration orchestration, result verification, match lifecycle       │
└───────────────────────┬─────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────────────┐
│ PHASE 5: SMART REGISTRATION SYSTEM                     (Weeks 17-21)    │
│  Draft persistence, auto-fill, game-aware questions, document uploads  │
└───────────────────────┬─────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────────────┐
│ PHASE 6: RESULT PIPELINE & DISPUTE RESOLUTION         (Weeks 22-25)    │
│  Manual result submission, opponent verification, organizer review      │
└───────────────────────┬─────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────────────┐
│ PHASE 7: ORGANIZER CONSOLE & MANUAL OPS               (Weeks 26-30)    │
│  Results inbox, dispute module, staff roles, visual dashboard, audit   │
└───────────────────────┬─────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────────────┐
│ PHASE 8: EVENT-DRIVEN STATS & HISTORY                 (Weeks 31-36)    │
│  User/team stats, match history, leaderboards, ranking system           │
└───────────────────────┬─────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────────────┐
│ PHASE 9: FRONTEND DEVELOPER SUPPORT & UI SPECS        (Weeks 37-40)    │
│  API docs, JSON schemas, component registry, UI/UX frameworks          │
└───────────────────────┬─────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────────────┐
│ PHASE 10: ADVANCED FEATURES & POLISH                  (Weeks 41-48)    │
│  Guided UI, notifications, Discord bot, achievements, mobile app        │
└─────────────────────────────────────────────────────────────────────────┘

Total Duration: 48 weeks (~12 months)
```

---

### Phase Dependencies

```
Phase 1 (Architecture Foundations)
    ↓ Required for all subsequent phases
    │
    ├──> Phase 2 (Game Rules & Configuration)
    │    └──> Phase 3 (Tournament Format Engine)
    │         ├──> Phase 4 (TournamentOps Workflows)
    │         │    ├──> Phase 5 (Smart Registration)
    │         │    ├──> Phase 6 (Result Pipeline)
    │         │    └──> Phase 7 (Organizer Console)
    │         │         └──> Phase 8 (Stats & History)
    │         │              └──> Phase 9 (Frontend Support)
    │         │                   └──> Phase 10 (Advanced Features)
    │         │
    │         └──> Can proceed in parallel after Phase 4:
    │              • Phase 5 (Smart Registration)
    │              • Phase 6 (Result Pipeline)
    │
    └──> Phase 9 (Frontend Support) - Can start after Phase 4

Critical Path:
1 → 2 → 3 → 4 → [5,6,7] → 8 → 9 → 10

Parallel Opportunities:
- Phase 5, 6, 7 can be developed in parallel after Phase 4
- Phase 9 can start early (after Phase 4) to support frontend development
```

---

## Phase 1: Architecture Foundations (Weeks 1-4)

### Goal

Establish clean architectural boundaries, service adapter pattern, and event-driven communication infrastructure. Create the foundation for a scalable, maintainable codebase with proper separation of concerns.

**Success Criteria**:
- ✅ Zero direct model imports across domain boundaries
- ✅ Adapter pattern implemented for all cross-domain communication
- ✅ Event bus operational with basic event handlers
- ✅ DTO patterns established for data transfer
- ✅ Service boundaries documented and enforced

---

### Epics

#### Epic 1.1: Service Adapter Layer
**Description**: Create adapter pattern for cross-domain communication to eliminate tight coupling between apps.

**User Story**: As a developer, I want clean service boundaries so that I can modify one app without breaking others.

**Acceptance Criteria**:
- Adapters created for: Games, Teams, Users, Economy, Tournaments
- All cross-app communication goes through adapters
- No direct model imports (e.g., `from teams.models import Team`)
- Adapter interface contracts documented

**Technical Tasks**:
- [ ] Create `tournament_ops/adapters/` directory
- [ ] Implement `TeamAdapter` (get team data, validate membership)
- [ ] Implement `UserAdapter` (get user data, validate eligibility)
- [ ] Implement `GameAdapter` (get game configs, validate identity fields)
- [ ] Implement `EconomyAdapter` (charge fees, issue refunds)
- [ ] Write adapter documentation (usage examples)
- [ ] Add unit tests for all adapters

**Effort**: 2 weeks

**Legacy Cleanup**:
- Remove direct cross-domain model imports as adapters are implemented (see CLEANUP_AND_TESTING_PART_6.md §4.4)
- Mark legacy import patterns with deprecation warnings

**Testing & Acceptance**:
- Pass all adapter unit tests (see CLEANUP_AND_TESTING_PART_6.md §9.1)
- Verify zero direct imports in new code before closing phase

---

#### Epic 1.2: Event Bus Infrastructure
**Description**: Build event-driven architecture to decouple services and enable reactive programming.

**User Story**: As a developer, I want an event system so that services can react to changes without tight coupling.

**Acceptance Criteria**:
- Event bus supports publish/subscribe pattern
- Events are persisted for audit trail
- Event handlers can be registered dynamically
- Failed event processing is retried with exponential backoff
- Event payload includes metadata (timestamp, user, transaction ID)

**Technical Tasks**:
- [ ] Create `common/events/event_bus.py`
- [ ] Implement `Event` base class (payload, metadata, serialization)
- [ ] Implement `EventBus` (publish, subscribe, dispatch)
- [ ] Create `EventLog` model (audit trail, replay capability)
- [ ] Implement event handler registration decorator
- [ ] Add Celery integration for async event processing
- [ ] Write event system documentation
- [ ] Add integration tests for event flow

**Effort**: 1.5 weeks

**Legacy Cleanup**:
- Replace synchronous service calls with event-driven patterns (see CLEANUP_AND_TESTING_PART_6.md §3.1)

**Testing & Acceptance**:
- Pass event bus integration tests (see CLEANUP_AND_TESTING_PART_6.md §9.1)
- Verify events persist and handlers execute correctly

---

#### Epic 1.3: DTO (Data Transfer Object) Patterns
**Description**: Define DTO contracts for data exchange between services to prevent model coupling.

**User Story**: As a developer, I want DTOs so that I can change model structures without breaking API contracts.

**Acceptance Criteria**:
- DTO classes for all major entities (Tournament, Registration, Match, Team, User)
- DTOs use dataclasses or Pydantic for validation
- Conversion methods: `from_model()`, `to_dict()`
- DTO documentation with field descriptions

**Technical Tasks**:
- [ ] Create `tournament_ops/dtos/` directory
- [ ] Define `TournamentDTO`, `RegistrationDTO`, `MatchDTO`
- [ ] Define `TeamDTO`, `UserDTO`, `PaymentDTO`
- [ ] Implement validation rules (Pydantic schemas)
- [ ] Add serialization/deserialization methods
- [ ] Document DTO usage patterns
- [ ] Add unit tests for DTO validation

**Effort**: 0.5 weeks

**Testing & Acceptance**:
- Pass DTO serialization tests (see CLEANUP_AND_TESTING_PART_6.md §9.1)
- Verify all adapter methods use DTOs, not raw models

---

## Phase 2: Game Rules & Configuration System (Weeks 5-7)

### Goal

Build database-driven game configuration system to support all 11 games without code changes. Implement game rules engine for validation and scoring logic. Remove hardcoded game-specific if-else checks.

**Success Criteria**:
- ✅ All 11 games configurable via admin panel
- ✅ Game rules engine validates match results for any game
- ✅ Zero hardcoded game identity field checks
- ✅ Scoring rules configurable per game/format
- ✅ Match result JSON schema validation working

---

### Epics

#### Epic 2.1: Game Configuration Models
**Description**: Create database models for game-specific configuration (identity fields, formats, scoring).

**User Story**: As a platform admin, I want to configure games via admin panel so that I can add new games without code deployment.

**Acceptance Criteria**:
- `Game` model with basic metadata (name, slug, icon)
- `GamePlayerIdentityConfig` for identity fields (Riot ID, Steam ID, etc.)
- `GameTournamentConfig` for supported formats
- `GameScoringRule` for scoring logic
- Admin panel forms for all config models

**Technical Tasks**:
- [ ] Create `games/models.py` with configuration models
- [ ] Add migrations for game config tables
- [ ] Seed database with 11 game configurations
- [ ] Create admin panel forms (`games/admin.py`)
- [ ] Add validation rules for configs
- [ ] Document configuration schema
- [ ] Add unit tests for config models

**Effort**: 1 week

**Legacy Cleanup**:
- Migrate from tournaments.Game → apps.games.Game (see CLEANUP_AND_TESTING_PART_6.md §4.1)
- Begin dual-write pattern for Game data

**Testing & Acceptance**:
- Pass all game config model tests (see CLEANUP_AND_TESTING_PART_6.md §9.2)
- Verify all 11 games configurable via admin panel

---

#### Epic 2.2: Game Rules Engine
**Description**: Build pluggable rules engine that validates match results and calculates scores based on game configuration.

**User Story**: As a tournament organizer, I want match results validated automatically so that invalid scores are rejected.

**Acceptance Criteria**:
- `GameRulesEngine` with pluggable rules modules
- Default rules (config-driven, works for any game)
- Custom rules modules for complex games (Valorant, PUBG)
- Rules engine validates: winner, scores, match structure
- Rules engine calculates: standings, tiebreakers, advancement

**Technical Tasks**:
- [ ] Create `games/services/game_rules_engine.py`
- [ ] Implement `GameRulesInterface` (abstract base class)
- [ ] Implement `DefaultGameRules` (config-driven validation)
- [ ] Implement `ValorantRules` (best-of-3, overtime validation)
- [ ] Implement `PUBGRules` (placement + kills scoring)
- [ ] Add rules engine unit tests
- [ ] Document rules engine architecture

**Effort**: 1.5 weeks

**Legacy Cleanup**:
- Replace hardcoded scoring logic with GameRulesEngine (see CLEANUP_AND_TESTING_PART_6.md §4.2)
- Remove if-else chains for game-specific scoring

**Testing & Acceptance**:
- Pass GameRulesEngine tests for all 11 games (see CLEANUP_AND_TESTING_PART_6.md §9.2)
- Verify no hardcoded game slug checks remain

---

#### Epic 2.3: Match Result Schema Validation
**Description**: Implement JSON Schema validation for match results to ensure data consistency.

**User Story**: As a developer, I want schema validation so that match results always have correct structure.

**Acceptance Criteria**:
- `GameMatchResultSchema` model stores JSON schemas per game
- `SchemaValidationService` validates results against schemas
- Schemas support: single-match, best-of-N, group stage
- Validation errors include helpful messages
- Frontend can fetch schemas for dynamic form generation

**Technical Tasks**:
- [ ] Create `GameMatchResultSchema` model
- [ ] Implement `SchemaValidationService.validate_match_result()`
- [ ] Define schemas for all 11 games
- [ ] Add schema migration/seeding script
- [ ] Create API endpoint: `GET /api/v1/games/{id}/result-schema/`
- [ ] Add validation error formatting
- [ ] Write schema validation tests

**Effort**: 0.5 weeks

**Testing & Acceptance**:
- Pass schema validation tests (see CLEANUP_AND_TESTING_PART_6.md §9.2)
- Verify schemas validate all 11 game result types

---

## Phase 3: Universal Tournament Format Engine (Weeks 8-12)

### Goal

Build comprehensive bracket generation and management system supporting all major tournament formats: Single Elimination, Double Elimination, Round Robin, Swiss System, Group Stage→Playoffs. Enable organizers to edit brackets, swap participants, and handle stage transitions.

**Success Criteria**:
- ✅ All 5 formats generate correctly (SE, DE, RR, Swiss, Groups)
- ✅ Bracket editor with drag/drop, swap, repair functions
- ✅ Group stage editor with manual group assignment
- ✅ Stage transition system (Groups→Playoffs, Swiss→Top Cut)
- ✅ GameRules→MatchSchema→Scoring engine fully integrated
- ✅ Bracket state persisted (can pause/resume tournament)

---

### Epics

#### Epic 3.1: Pluggable Bracket Generators
**Description**: Create bracket generation system with pluggable generators for each tournament format.

**User Story**: As a tournament organizer, I want to select a format and generate brackets automatically so that I don't have to create matches manually.

**Acceptance Criteria**:
- `BracketGeneratorInterface` (abstract base class)
- `SingleEliminationGenerator` with seeding
- `DoubleEliminationGenerator` with winners/losers brackets
- `RoundRobinGenerator` with balanced scheduling
- `SwissSystemGenerator` with Dutch pairing algorithm
- Bracket generation is idempotent (can regenerate safely)

**Technical Tasks**:
- [ ] Create `tournament_ops/services/bracket_generators/` directory
- [ ] Implement `BracketGeneratorInterface`
- [ ] Implement `SingleEliminationGenerator`
  - [ ] Seeding algorithm (1v16, 2v15, etc.)
  - [ ] Bye handling for non-power-of-2
- [ ] Implement `DoubleEliminationGenerator`
  - [ ] Winners bracket + losers bracket
  - [ ] Grand finals (winner resets if loser wins)
- [ ] Implement `RoundRobinGenerator`
  - [ ] Full round robin (everyone plays everyone)
  - [ ] Balanced scheduling algorithm
- [ ] Implement `SwissSystemGenerator`
  - [ ] Dutch pairing (same record plays each other)
  - [ ] Rematch avoidance
  - [ ] Bye handling for odd participants
- [ ] Add bracket generator registry
- [ ] Write unit tests for all generators
- [ ] Document seeding and pairing algorithms

**Effort**: 2.5 weeks

**Legacy Cleanup**:
- Wrap legacy bracket code in adapter (see CLEANUP_AND_TESTING_PART_6.md §4.5)
- Add feature flag for new bracket engine (use_new_bracket_engine)

**Testing & Acceptance**:
- Pass all bracket generator tests (SE/DE/RR/Swiss) (see CLEANUP_AND_TESTING_PART_6.md §9.3)
- Verify seeding algorithms produce correct match count and round count

---

#### Epic 3.2: Group Stage Editor & Manager
**Description**: Build group stage creation, editing, and management tools for group-based tournaments.

**User Story**: As an organizer, I want to manually assign participants to groups so that I can balance skill levels or create regional groups.

**Acceptance Criteria**:
- Create groups with configurable size (4-8 teams per group)
- Manual drag/drop assignment of participants to groups
- Auto-balance groups (distribute by seed/skill)
- Generate round robin within each group
- Group standings calculation with tiebreakers
- Export group results to JSON

**Technical Tasks**:
- [ ] Create `GroupStage` model (tournament, num_groups, group_size)
- [ ] Create `Group` model (stage, name, participants)
- [ ] Implement `GroupStageService.create_groups()`
- [ ] Implement `GroupStageService.assign_participant()`
- [ ] Implement `GroupStageService.auto_balance_groups()`
- [ ] Implement `GroupStageService.generate_group_matches()`
- [ ] Add group standings calculation (with tiebreakers)
- [ ] Create group editor UI components (backend API)
- [ ] Write integration tests for group stage workflow
- [ ] Document group stage configuration

**Effort**: 1.5 weeks

**Testing & Acceptance**:
- Pass group stage integration tests (see CLEANUP_AND_TESTING_PART_6.md §9.3)
- Verify group standings calculated correctly with tiebreakers

---

#### Epic 3.3: Bracket Editor (Drag/Drop, Swaps, Repairs)
**Description**: Build visual bracket editor allowing organizers to manually adjust brackets, swap participants, and repair broken brackets.

**User Story**: As an organizer, I want to edit brackets visually so that I can fix errors or handle special situations (no-shows, DQs).

**Acceptance Criteria**:
- Swap participants between matches
- Move participant to different match (drag/drop)
- Remove participant (handle bye)
- Repair broken bracket (fix missing connections)
- Validate bracket integrity after edits
- Audit log of all bracket changes

**Technical Tasks**:
- [ ] Create `BracketEditor

**Deliverables**:
- `GameAdapter` (tournaments → games)
- `TeamAdapter` (tournaments → teams)
- `UserAdapter` (tournaments → user_profile)
- `EconomyAdapter` (tournaments → economy)
- Define DTOs for all adapter methods
- Remove all direct model imports from tournaments app

**Acceptance Criteria**:
- No `from apps.teams.models import Team` in tournaments app
- All cross-domain calls go through adapters
- 100% of adapter methods return DTOs, not model instances

---

#### Epic 1.2: Game Configuration Models
**Description**: Build database-driven game configuration system to replace hardcoded game logic.

**Deliverables**:
- `GamePlayerIdentityConfig` model (Riot ID, Steam ID, etc.)
- `GameTournamentConfig` model (formats, scoring, result schemas)
- `GameScoringRule` model (points calculation rules)
- Migration scripts to populate configs for 11 games
- Admin UI for managing game configs

**Acceptance Criteria**:
- All 11 games configured with identity fields
- Each game has at least 1 tournament format configured
- Game configs drive registration form field rendering
- Admin can add new game without developer involvement

---

#### Epic 1.3: Game Rules Engine
**Description**: Implement flexible rules engine that validates match results and calculates points based on game type.

**Deliverables**:
- `GameRulesEngine` service with pluggable rules modules
- `DefaultGameRules` (config-driven fallback)
- Custom rules modules for 3 games (Valorant, PUBG, CS2)
- Match result validation using rules engine
- Tournament points calculation using rules engine

**Acceptance Criteria**:
- Rules engine validates Valorant results (13-25 rounds, no draws)
- Rules engine validates PUBG results (placement 1-16, kills >= 0)
- Points calculated correctly for Swiss/Round Robin formats
- Can add new game by creating config (no custom module required)

---

#### Epic 1.4: Refactor Existing Registration to Use Adapters
**Description**: Update current registration workflow to use new adapter layer (prepare for Phase 2).

**Deliverables**:
- Refactor `registration_wizard.py` to use `GameAdapter`
- Refactor team registration to use `TeamAdapter`
- Refactor payment logic to use `EconomyAdapter`
- Remove hardcoded game checks (7 if-else statements → 0)

**Acceptance Criteria**:
- Registration still works (no broken functionality)
- All game-specific logic pulled from `GameAdapter.get_identity_configs()`
- Auto-fill uses adapter methods, not direct model queries
- Unit tests pass with mocked adapters

---

#### Epic 1.5: Data Transfer Objects (DTOs)
**Description**: Define DTOs for all cross-domain data transfer to decouple service boundaries.

**Deliverables**:
- `GamePlayerIdentityConfigDTO`
- `TeamDTO`
- `UserProfileDTO`
- `ValidationResult` DTO
- Type hints on all adapter methods

**Acceptance Criteria**:
- All adapter methods typed with DTOs (input/output)
**Technical Tasks**:
- [ ] Create `BracketEditorService` class
- [ ] Implement `swap_participants(match1_id, match2_id)`
- [ ] Implement `move_participant(participant_id, from_match_id, to_match_id)`
- [ ] Implement `remove_participant(match_id, participant_id)`
- [ ] Implement `repair_bracket()` (fix orphaned matches)
- [ ] Add bracket validation logic
- [ ] Create audit log entries for all edits
- [ ] Add API endpoints for bracket editing
- [ ] Write integration tests
- [ ] Document bracket editor usage

**Effort**: 1 week

**Testing & Acceptance**:
- Pass bracket editor tests (see CLEANUP_AND_TESTING_PART_6.md §9.3)
- Verify swap/move/remove operations maintain bracket integrity

---

#### Epic 3.4: Stage Transitions System (Groups→Playoffs, Swiss→Top Cut)
**Description**: Build system to transition between tournament stages, advancing participants based on standings.

**User Story**: As an organizer, I want to automatically advance top teams from group stage to playoffs so that I don't have to manually create the next bracket.

**Acceptance Criteria**:
- Define stage transition rules (top N from each group)
- Auto-generate next stage bracket from previous stage results
- Handle different advancement scenarios (top 2, top 4, wildcard)
- Preserve seeding from previous stage
- Support multi-stage tournaments (Groups→Ro16→Ro8→Ro4→Finals)

**Technical Tasks**:
- [ ] Create `TournamentStage` model (type, order, advancement_rules)
- [ ] Create `StageTransitionService`
- [ ] Implement `calculate_advancement(stage_id)` (determine who advances)
- [ ] Implement `generate_next_stage(current_stage_id)`
- [ ] Add advancement rule validation
- [ ] Support seeding carryover (group winner seeds higher)
- [ ] Handle tiebreakers for advancement (head-to-head, round diff)
- [ ] Add stage transition API endpoints
- [ ] Write integration tests for multi-stage tournaments
- [ ] Document stage transition configuration

**Effort**: 1 week

**Testing & Acceptance**:
- Pass stage transition tests (see CLEANUP_AND_TESTING_PART_6.md §9.3)
- Verify groups→playoffs advancement works for top 2/4/8 scenarios

---

#### Epic 3.5: GameRules→MatchSchema→Scoring Integration
**Description**: Integrate game rules engine, match schema validation, and scoring systems for end-to-end result processing.

**User Story**: As a platform, I want match results validated and scored automatically so that standings are always accurate.

**Acceptance Criteria**:
- Match results validated against game schema before saving
- Game rules engine calculates scores based on game type
- Standings auto-update when match completes
- Tiebreakers applied automatically
- Scoring errors logged and reported

**Technical Tasks**:
- [ ] Connect `MatchResultService` to `SchemaValidationService`
- [ ] Connect `MatchResultService` to `GameRulesEngine`
- [ ] Implement scoring pipeline: validate → score → update standings
- [ ] Add scoring error handling and logging
- [ ] Create scoring audit trail
- [ ] Add real-time standings calculation
- [ ] Implement tiebreaker logic (head-to-head, rounds, Buchholz)
- [ ] Write integration tests for scoring pipeline
- [ ] Document scoring workflow

**Effort**: 1 week

**Testing & Acceptance**:
- Pass GameRules→Schema→Scoring integration tests (see CLEANUP_AND_TESTING_PART_6.md §9.3)
- Verify standings auto-update when matches complete

---

## Phase 4: TournamentOps Core Workflows (Weeks 13-16)

### Goal

Build TournamentOps orchestration layer to coordinate tournament lifecycle: registration workflow, participant verification, tournament finalization, and cross-domain coordination.

**Success Criteria**:
- ✅ Registration workflow fully orchestrated (draft→submit→payment→verify)
- ✅ Tournament finalization process automated
- ✅ Participant verification integrated
- ✅ Event publishing working for all major actions
- ✅ Adapter pattern used for all cross-domain calls

---

### Epics

#### Epic 4.1: Registration Orchestration Service
**Description**: Build service to orchestrate registration workflow across multiple domains (users, teams, payments, tournaments).

**User Story**: As the platform, I want registration coordinated automatically so that all systems stay in sync.

**Acceptance Criteria**:
- Registration draft creation
- Auto-fill from user/team profiles
- Payment processing coordination
- Registration confirmation and finalization
- Event publishing at each step

**Technical Tasks**:
- [ ] Create `RegistrationOrchestrationService`
- [ ] Implement `create_draft(user_id, tournament_id)`
- [ ] Implement `auto_fill_draft(draft_id)` (call adapters)
- [ ] Implement `submit_registration(draft_id)`
- [ ] Implement `process_payment(registration_id)`
- [ ] Implement `finalize_registration(registration_id)`
- [ ] Add event publishing (RegistrationSubmittedEvent, etc.)
- [ ] Add rollback/compensation logic for failures
- [ ] Write integration tests
- [ ] Document registration workflow

**Effort**: 2 weeks

**Legacy Cleanup**:
- Migrate from old registration logic → TournamentOps orchestration (see CLEANUP_AND_TESTING_PART_6.md §4.3)
- Add feature flag for new registration flow (use_new_registration_flow)

**Testing & Acceptance**:
- Pass registration orchestration integration tests (see CLEANUP_AND_TESTING_PART_6.md §9.4)
- Verify full workflow: draft→submit→payment→verify→confirm

---

#### Epic 4.2: Tournament Lifecycle Orchestration
**Description**: Coordinate tournament lifecycle from creation to completion, managing state transitions and validations.

**User Story**: As an organizer, I want tournaments to progress automatically so that I don't have to manually trigger each step.

**Acceptance Criteria**:
- Tournament state machine (Draft→Open→Live→Completed)
- Automatic state transitions based on conditions
- Validation at each state transition
- Bracket generation triggered automatically
- Tournament completion finalized with stats

**Technical Tasks**:
- [ ] Create `TournamentLifecycleService`
- [ ] Implement state machine (FSM pattern)
- [ ] Implement `open_registration(tournament_id)`
- [ ] Implement `close_registration(tournament_id)`
- [ ] Implement `start_tournament(tournament_id)` (generate brackets)
- [ ] Implement `complete_tournament(tournament_id)`
- [ ] Add validation for state transitions
- [ ] Publish lifecycle events
- [ ] Write state machine tests
- [ ] Document tournament lifecycle

**Effort**: 1.5 weeks

**Testing & Acceptance**:
- Pass tournament lifecycle state machine tests (see CLEANUP_AND_TESTING_PART_6.md §9.4)
- Verify all state transitions work correctly (Draft→Open→Live→Completed)

---

#### Epic 4.3: Match Lifecycle Management
**Description**: Manage match lifecycle from creation to completion, including scheduling, result validation, and advancement.

**User Story**: As the platform, I want matches to progress automatically from scheduled→live→completed so that tournaments flow smoothly.

**Acceptance Criteria**:
- Match state machine (Pending→Scheduled→Live→Completed)
- Automatic match scheduling (if times configured)
- Result submission and validation
- Winner advancement to next match
- Match completion events published

**Technical Tasks**:
- [ ] Create `MatchLifecycleService`
- [ ] Implement match state machine
- [ ] Implement `schedule_match(match_id, datetime)`
- [ ] Implement `start_match(match_id)`
- [ ] Implement `submit_result(match_id, result_data)`
- [ ] Implement `complete_match(match_id)`
- [ ] Implement `advance_winner(match_id)` (update next match)
- [ ] Add match validation logic
- [ ] Publish match events
- [ ] Write integration tests
- [ ] Document match lifecycle

**Effort**: 0.5 weeks

**Legacy Cleanup**:
- Finalize migration: switch FK from tournaments.Game → apps.games.Game (see CLEANUP_AND_TESTING_PART_6.md §3.2)
- Remove old Game model after data migration complete

**Testing & Acceptance**:
- Pass match lifecycle tests (see CLEANUP_AND_TESTING_PART_6.md §9.4)
- Verify winner advancement to next match works correctly

---

## Phase 5: Smart Registration System (Weeks 17-21)

### Goal

Build comprehensive smart registration system with draft persistence, auto-fill from profiles, game-aware questions, conditional field display, document uploads, and organizer verification.

**Success Criteria**:
- ✅ Registration drafts persist across sessions
- ✅ Auto-fill from UserProfile, Team, GameAccounts
- ✅ Game-specific questions render dynamically
- ✅ Conditional fields show/hide based on selections
- ✅ Document uploads (rank screenshots, ID, consent forms)
- ✅ Organizer verification checklist operational
- ✅ Draft recovery via email

---

### Epics

#### Epic 5.1: Registration Draft System
**Description**: Build persistent draft system allowing users to save progress and resume registration across devices/sessions.

**User Story**: As a user, I want to save my registration progress so that I can complete it later on any device.

**Acceptance Criteria**:
- Draft auto-saves every 30 seconds
- UUID-based draft recovery
- Draft expiration (7 days)
- Cross-device resume
- Progress percentage tracking

**Technical Tasks**:
- [ ] Create `RegistrationDraft` model
- [ ] Implement auto-save mechanism (frontend + backend)
- [ ] Add UUID generation and indexing
- [ ] Implement draft expiration cleanup task
- [ ] Create resume endpoint `GET /api/v1/drafts/{uuid}/resume/`
- [ ] Add progress calculation logic
- [ ] Implement draft recovery email service
- [ ] Write unit tests
- [ ] Document draft system

**Effort**: 1.5 weeks

**Testing & Acceptance**:
- Pass registration draft auto-save tests (see CLEANUP_AND_TESTING_PART_6.md §9.5)
- Verify drafts persist across sessions and devices

---

#### Epic 5.2: Auto-Fill Intelligence
**Description**: Automatically pre-populate registration fields from user profile, team data, and game account configurations.

**User Story**: As a user, I want fields filled automatically so that I don't have to re-enter information I've already provided.

**Acceptance Criteria**:
- Auto-fill from UserProfile (name, email, phone, DOB)
- Auto-fill from Team (team name, logo, roster)
- Auto-fill from GameAccount (Riot ID, Steam ID, etc.)
- Field locking for verified data (prevent tampering)
- Visual indicators showing auto-filled fields

**Technical Tasks**:
- [ ] Create `RegistrationAutoFillService`
- [ ] Implement `auto_fill_from_profile(user_id, draft_id)`
- [ ] Implement `auto_fill_from_team(team_id, draft_id)`
- [ ] Implement `auto_fill_from_game_account(user_id, game_id, draft_id)`
- [ ] Add field locking mechanism
- [ ] Track auto-filled fields in draft metadata
- [ ] Add verification status to fields
- [ ] Write unit tests
- [ ] Document auto-fill sources

**Effort**: 1 week

**Testing & Acceptance**:
- Pass auto-fill tests (see CLEANUP_AND_TESTING_PART_6.md §9.5)
- Verify verified Riot ID/Steam ID auto-filled correctly

---

#### Epic 5.3: Game-Aware Registration Questions
**Description**: Dynamic registration form fields based on game and tournament format.

**User Story**: As an organizer, I want to ask game-specific questions so that I collect relevant data for each game.

**Acceptance Criteria**:
- `GameRegistrationQuestionConfig` model
- Questions per game (Valorant: rank, role; PUBG: server, tier)
- Field types: text, select, multi-select, file upload
- Validation rules per field
- Questions render dynamically based on tournament game

**Technical Tasks**:
- [ ] Create `GameRegistrationQuestionConfig` model
- [ ] Seed game-specific questions for all 11 games
- [ ] Add API endpoint `GET /api/v1/games/{id}/registration-questions/`
- [ ] Implement dynamic field rendering (backend)
- [ ] Add field validation service
- [ ] Write question configuration documentation
- [ ] Add unit tests

**Effort**: 1 week

**Testing & Acceptance**:
- Pass game-aware question rendering tests (see CLEANUP_AND_TESTING_PART_6.md §9.5)
- Verify all 11 games have correct registration questions configured

---

#### Epic 5.4: Conditional Field Display
**Description**: Show/hide registration fields based on user selections (tournament type, format, age, etc.).

**User Story**: As a user, I want to see only relevant fields so that I'm not confused by irrelevant questions.

**Acceptance Criteria**:
- Conditional logic: `show_if: {tournament_type: 'team'}`
- Frontend evaluates conditions in real-time
- Backend validates only visible fields
- Conditional rules documented

**Technical Tasks**:
- [ ] Add `show_if` field to `GameRegistrationQuestionConfig`
- [ ] Implement frontend condition evaluation logic
- [ ] Add backend validation (only validate visible fields)
- [ ] Document conditional logic syntax
- [ ] Add test cases for conditional scenarios
- [ ] Create example configurations

**Effort**: 0.5 weeks

**Testing & Acceptance**:
- Pass conditional field display tests (see CLEANUP_AND_TESTING_PART_6.md §9.5)
- Verify fields show/hide based on selections (e.g., parent consent if age < 18)

---

#### Epic 5.5: Document Upload Requirements
**Description**: Support for required document uploads (rank screenshots, ID verification, parent consent forms).

**User Story**: As an organizer, I want to require proof documents so that I can verify participant eligibility.

**Acceptance Criteria**:
- `TournamentDocumentRequirement` model
- Document types: rank_screenshot, ID, parent_consent, payment_proof
- File upload with size/format validation
- Document verification by organizers
- Conditional requirements (parent consent if age < 18)

**Technical Tasks**:
- [ ] Create `TournamentDocumentRequirement` model
- [ ] Create `RegistrationDocumentUpload` model
- [ ] Implement file upload endpoint with validation
- [ ] Add conditional requirement logic
- [ ] Create document verification UI (backend API)
- [ ] Add file storage (S3 integration)
- [ ] Write upload tests
- [ ] Document requirement configuration

**Effort**: 1 week

**Testing & Acceptance**:
- Pass document upload tests (see CLEANUP_AND_TESTING_PART_6.md §9.5)
- Verify file uploads work with size/format validation

---

#### Epic 5.6: Organizer Verification Checklist
**Description**: Admin checklist for verifying registration completeness and accuracy.

**User Story**: As an organizer, I want a verification checklist so that I can systematically verify each registration.

**Acceptance Criteria**:
- `RegistrationVerificationChecklist` model
- Checklist items: email_verified, game_id_verified, payment_verified, documents_verified
- Progress tracking (% complete)
- Bulk verification operations
- Verification notes/comments

**Technical Tasks**:
- [ ] Create `RegistrationVerificationChecklist` model
- [ ] Auto-create checklist when registration submitted
- [ ] Implement verification progress calculation
- [ ] Add bulk verification API endpoints
- [ ] Create verification dashboard backend
- [ ] Add verification audit log
- [ ] Write verification workflow tests
- [ ] Document checklist usage

**Effort**: 0.5 weeks

**Legacy Cleanup**:
- Remove legacy registration views completely (see CLEANUP_AND_TESTING_PART_6.md §3.4)
- Delete old registration_legacy.py files

**Testing & Acceptance**:
- Pass organizer verification checklist tests (see CLEANUP_AND_TESTING_PART_6.md §9.5)
- Complete E2E test: full registration wizard journey

---

## Phase 6: Result Pipeline & Dispute Resolution (Weeks 22-25)

### Goal

Build manual result submission pipeline with opponent verification, dispute mechanism, and organizer review. Enable multi-checkpoint verification to ensure result accuracy without game API integration.

**Success Criteria**:
- ✅ 6-step result pipeline operational (submit→confirm→review→validate→propagate→update)
- ✅ Opponent confirmation/dispute mechanism working
- ✅ Organizer results inbox functional
- ✅ Dispute resolution workflow complete
- ✅ Proof screenshot uploads required
- ✅ Event-driven stats updates triggered

---

### Epics

#### Epic 6.1: Match Result Submission Service
**Description**: Allow participants to submit match results with proof screenshots.

**User Story**: As a player, I want to submit match results so that the tournament can progress.

**Acceptance Criteria**:
- Result submission form with scores, winner, proof screenshot
- Schema validation against game's expected result structure
- Proof screenshot required (enforced)
- Submission stored in queue (pending opponent confirmation)
- Opponent notified automatically

**Technical Tasks**:
- [ ] Create `MatchResultSubmission` model
- [ ] Implement `ResultSubmissionService.submit_result()`
- [ ] Add schema validation integration
- [ ] Add proof screenshot upload with validation
- [ ] Create submission queue
- [ ] Implement opponent notification
- [ ] Add submission API endpoint
- [ ] Write submission tests
- [ ] Document submission workflow

**Effort**: 1 week

**Testing & Acceptance**:
- Pass result submission tests (see CLEANUP_AND_TESTING_PART_6.md §9.6)
- Verify schema validation rejects invalid scores

---

#### Epic 6.2: Opponent Verification & Dispute System
**Description**: Enable opponents to confirm or dispute submitted results.

**User Story**: As a participant, I want to verify my opponent's result submission so that incorrect results don't get finalized.

**Acceptance Criteria**:
- Opponent can confirm/dispute submission
- Dispute requires reason + explanation (min 50 chars)
- Counter-proof screenshot optional
- Auto-confirm after 24 hours if no response
- Disputed results routed to organizer review

**Technical Tasks**:
- [ ] Create `DisputeRecord` model
- [ ] Implement `ResultConfirmationService.confirm_result()`
- [ ] Implement `ResultConfirmationService.dispute_result()`
- [ ] Add auto-confirm background task (Celery)
- [ ] Create dispute form validation
- [ ] Route disputed results to organizer queue
- [ ] Add API endpoints for confirm/dispute
- [ ] Write dispute workflow tests
- [ ] Document dispute process

**Effort**: 1 week

**Testing & Acceptance**:
- Pass opponent confirmation and dispute workflow tests (see CLEANUP_AND_TESTING_PART_6.md §9.6)
- Verify dispute escalates to organizer inbox correctly

---

#### Epic 6.3: Organizer Results Inbox
**Description**: Admin interface for reviewing pending/disputed/conflicted result submissions.

**User Story**: As an organizer, I want a results inbox so that I can review and approve submissions efficiently.

**Acceptance Criteria**:
- Results inbox with tabs: Pending, Disputed, Conflicted
- View submission details (proof, scores, notes)
- View dispute details (reason, counter-proof)
- Actions: Approve, Reject, Order Rematch, Request More Info
- Resolution notes required

**Technical Tasks**:
- [ ] Create results inbox API endpoints
- [ ] Implement result categorization logic
- [ ] Add submission detail view API
- [ ] Create organizer actions API
- [ ] Implement resolution notes storage
- [ ] Add filtering/sorting
- [ ] Write inbox workflow tests
- [ ] Document inbox usage

**Effort**: 1 week

**Testing & Acceptance**:
- Pass organizer results inbox tests (see CLEANUP_AND_TESTING_PART_6.md §9.6)
- Verify disputed results appear in inbox with evidence

---

#### Epic 6.4: Result Verification & Finalization Service
**Description**: TournamentOps service to validate, finalize, and propagate match results.

**User Story**: As the platform, I want results validated and finalized automatically so that stats are always accurate.

**Acceptance Criteria**:
- Schema validation + game rules validation
- Result applied to Match model (winner, scores, state)
- Conflicting submissions rejected
- MatchCompletedEvent published
- Winner advanced to next match
- Stats update triggered via event

**Technical Tasks**:
- [ ] Create `ResultVerificationService`
- [ ] Implement `finalize_result(submission_id)`
- [ ] Add multi-level validation (schema + rules)
- [ ] Implement result application to Match
- [ ] Add conflicting submission rejection
- [ ] Publish MatchCompletedEvent
- [ ] Trigger winner advancement
- [ ] Write finalization tests
- [ ] Document finalization workflow

**Effort**: 0.5 weeks

**Testing & Acceptance**:
- Pass result finalization tests (see CLEANUP_AND_TESTING_PART_6.md §9.6)
- Verify MatchCompletedEvent published and stats updated

---

#### Epic 6.5: Dispute Resolution Module
**Description**: Workflow for organizers to resolve disputed results with multiple resolution options.

**User Story**: As an organizer, I want resolution options so that I can handle different dispute scenarios appropriately.

**Acceptance Criteria**:
- Resolution options: Approve Original, Approve Dispute, Order Rematch
- Resolution notes required (explain decision)
- Both parties notified of resolution
- Audit trail of all resolutions

**Technical Tasks**:
- [ ] Implement `resolve_dispute(dispute_id, decision, notes)`
- [ ] Add resolution logic for each decision type
- [ ] Create notification service for resolutions
- [ ] Add resolution audit logging
- [ ] Create resolution API endpoints
- [ ] Write resolution tests
- [ ] Document resolution options

**Effort**: 0.5 weeks

**Testing & Acceptance**:
- Pass dispute resolution tests (see CLEANUP_AND_TESTING_PART_6.md §9.6)
- Complete manual QA: opponent confirm/dispute flow (see CLEANUP_AND_TESTING_PART_6.md §10.3)

---

## Phase 7: Organizer Console & Manual Ops (Weeks 26-30)

### Goal

Build comprehensive organizer tools for tournament management including results inbox, dispute queue, manual scheduling, staff/referee roles, visual dashboard with alerts, audit log system, and contextual help.

**Success Criteria**:
- ✅ Results inbox with pending/disputed queues operational
- ✅ Dispute resolution interface complete
- ✅ Manual scheduling tools working
- ✅ Staff/referee role system implemented
- ✅ Visual dashboard with warnings/alerts
- ✅ Comprehensive audit log system
- ✅ Contextual help overlays for organizers

---

### Epics

#### Epic 7.1: Results Inbox & Queue Management
**Description**: Centralized inbox for managing all result submissions across all tournaments.

**User Story**: As an organizer, I want a centralized results inbox so that I can efficiently process all submissions.

**Acceptance Criteria**:
- Multi-tournament results queue
- Filters: tournament, status, date range
- Bulk actions (approve multiple, export)
- Submission age indicators (overdue in red)
- Quick actions (approve/reject with one click)

**Technical Tasks**:
- [ ] Create multi-tournament inbox view API
- [ ] Implement filtering and sorting
- [ ] Add bulk action endpoints
- [ ] Create age calculation logic
- [ ] Add quick action endpoints
- [ ] Implement inbox caching (performance)
- [ ] Write inbox tests
- [ ] Document inbox features

**Effort**: 1 week

**Testing & Acceptance**:
- Pass results inbox queue management tests (see CLEANUP_AND_TESTING_PART_6.md §9.7)
- Verify bulk actions work correctly

---

#### Epic 7.2: Manual Scheduling Tools
**Description**: Tools for organizers to manually schedule matches, set times, and manage calendar.

**User Story**: As an organizer, I want to schedule matches manually so that I can coordinate with players' availability.

**Acceptance Criteria**:
- Calendar view of all matches
- Drag/drop to reschedule matches
- Bulk scheduling (schedule entire round)
- Conflict detection (same team in two matches at same time)
- Schedule notifications to participants

**Technical Tasks**:
- [ ] Create match calendar API
- [ ] Implement manual scheduling endpoint
- [ ] Add bulk scheduling logic
- [ ] Implement conflict detection
- [ ] Create schedule notification service
- [ ] Add time zone handling
- [ ] Write scheduling tests
- [ ] Document scheduling tools

**Effort**: 1.5 weeks

**Testing & Acceptance**:
- Pass manual scheduling tests (see CLEANUP_AND_TESTING_PART_6.md §9.7)
- Verify conflict detection works (same team, overlapping times)

---

#### Epic 7.3: Staff & Referee Role System
**Description**: Role-based permissions for tournament staff and referees.

**User Story**: As an organizer, I want to assign staff roles so that I can delegate responsibilities.

**Acceptance Criteria**:
- Roles: Organizer, Referee, Moderator, Staff
- Permissions: manage_registrations, verify_results, edit_brackets, moderate_chat
- Staff assignment per tournament
- Activity tracking for staff actions

**Technical Tasks**:
- [ ] Create `TournamentStaff` model (role, permissions)
- [ ] Implement role-based permission checks
- [ ] Add staff assignment API
- [ ] Create permission decorators
- [ ] Add staff activity logging
- [ ] Implement staff dashboard
- [ ] Write permission tests
- [ ] Document role system

**Effort**: 1 week

**Testing & Acceptance**:
- Pass role-based permission tests (see CLEANUP_AND_TESTING_PART_6.md §9.7)
- Verify staff can only perform authorized actions

---

#### Epic 7.4: Visual Dashboard with Alerts
**Description**: Real-time dashboard showing tournament health, warnings, and action items.

**User Story**: As an organizer, I want a visual dashboard so that I can see problems at a glance.

**Acceptance Criteria**:
- Widgets: Pending Results, Overdue Matches, Disputed Results, Registration Status
- Alerts: Match conflicts, Payment issues, No-shows
- Color coding: Green (healthy), Yellow (warning), Red (critical)
- Real-time updates (WebSocket or polling)

**Technical Tasks**:
- [ ] Create dashboard API endpoints
- [ ] Implement widget data calculation
- [ ] Add alert generation logic
- [ ] Create real-time update mechanism
- [ ] Add color coding rules
- [ ] Implement dashboard caching
- [ ] Write dashboard tests
- [ ] Document dashboard widgets

**Effort**: 1 week

**Testing & Acceptance**:
- Pass visual dashboard tests (see CLEANUP_AND_TESTING_PART_6.md §9.7)
- Verify alerts appear correctly based on tournament state

---

#### Epic 7.5: Audit Log System
**Description**: Comprehensive audit trail of all administrative actions for accountability and debugging.

**User Story**: As a platform admin, I want audit logs so that I can track who did what and when.

**Acceptance Criteria**:
- Log all admin actions (registrations, results, brackets, disputes)
- Track: user, action, timestamp, before/after state
- Searchable and filterable
- Immutable log entries
- Export to CSV

**Technical Tasks**:
- [ ] Create `AuditLog` model
- [ ] Implement audit logging decorators
- [ ] Add automatic before/after state capture
- [ ] Create audit log search API
- [ ] Implement CSV export
- [ ] Add retention policy (archive after 1 year)
- [ ] Write audit log tests
- [ ] Document audit log usage

**Effort**: 0.5 weeks

**Testing & Acceptance**:
- Pass audit log tests (see CLEANUP_AND_TESTING_PART_6.md §9.7)
- Verify all admin actions logged with before/after state

---

#### Epic 7.6: Guidance & Help Overlays
**Description**: Contextual help and onboarding for organizers using the console for the first time.

**User Story**: As a new organizer, I want guided help so that I learn how to use the tools effectively.

**Acceptance Criteria**:
- Onboarding wizard for first-time organizers
- Contextual tooltips on all features
- Help overlay system (press ? for help)
- Video tutorials embedded in UI
- "Tips & Tricks" sidebar

**Technical Tasks**:
- [ ] Create onboarding wizard flow
- [ ] Implement tooltip system
- [ ] Add help overlay trigger (keyboard shortcut)
- [ ] Create help content database
- [ ] Embed video tutorial players
- [ ] Add tips/tricks content
- [ ] Write help content
- [ ] Document help system

**Effort**: 0.5 weeks

**Legacy Cleanup**:
- Remove Django admin customizations for tournaments (see CLEANUP_AND_TESTING_PART_6.md §3.3)
- Delete admin_bracket.py, admin_match.py (replaced by custom console)

**Testing & Acceptance**:
- Complete manual QA: organizer console workflow (see CLEANUP_AND_TESTING_PART_6.md §10.1, §10.4)
- Verify all organizer features work end-to-end

---

## Phase 8: Event-Driven Stats & History (Weeks 31-36)

### Goal

Build event-driven statistics and history tracking system. Automatically update user stats, team stats, match history, and leaderboards when matches complete. Implement ranking/ELO system driven by events.

**Success Criteria**:
- ✅ User stats auto-update on match completion
- ✅ Team stats auto-update on match completion
- ✅ Match history persisted for all participants
- ✅ Leaderboards calculate correctly
- ✅ Ranking/ELO system operational
- ✅ Event handlers tested and reliable

---

### Epics

#### Epic 8.1: Event System Architecture
**Description**: Build robust event system with event bus, event handlers, and failure recovery.

**User Story**: As the platform, I want reliable event processing so that stats are always consistent.

**Acceptance Criteria**:
- Event bus with publish/subscribe
- Event persistence (replay capability)
- Failed event retry with exponential backoff
- Dead letter queue for permanently failed events
- Event processing metrics

**Technical Tasks**:
- [ ] Create `Event` base class with serialization
- [ ] Implement `EventBus` (publish, subscribe, dispatch)
- [ ] Create `EventLog` model for persistence
- [ ] Add Celery integration for async processing
- [ ] Implement retry logic with exponential backoff
- [ ] Create dead letter queue
- [ ] Add event metrics (Prometheus)
- [ ] Write event system tests
- [ ] Document event architecture

**Effort**: 2 weeks

**Legacy Cleanup**:
- Migrate from synchronous stats updates → event-driven (see CLEANUP_AND_TESTING_PART_6.md §3.5)
- Remove direct stats calculation in views/services

**Testing & Acceptance**:
- Pass event bus architecture tests (see CLEANUP_AND_TESTING_PART_6.md §9.8)
- Verify events persist and retry on failure

---

#### Epic 8.2: User Stats Service
**Description**: Track user statistics across all tournaments and matches.

**User Story**: As a user, I want to see my stats so that I can track my competitive progress.

**Acceptance Criteria**:
- Stats: matches_played, matches_won, win_rate, total_kills, total_deaths, K/D ratio
- Stats per game (Valorant stats separate from PUBG stats)
- Stats updated automatically on match completion
- Historical stats tracking (monthly, yearly)

**Technical Tasks**:
- [ ] Create `UserStats` model (per game aggregation)
- [ ] Create `UserStatsService`
- [ ] Implement `record_match_result(user_id, match_result)`
- [ ] Add event handler for MatchCompletedEvent
- [ ] Implement stat calculation logic
- [ ] Add historical stats models
- [ ] Create stats API endpoints
- [ ] Write stats calculation tests
- [ ] Document stats tracking

**Effort**: 1.5 weeks

**Testing & Acceptance**:
- Pass user stats calculation tests (see CLEANUP_AND_TESTING_PART_6.md §9.8)
- Verify stats update automatically on MatchCompletedEvent

---

#### Epic 8.3: Team Stats & Ranking System
**Description**: Track team statistics and maintain team rankings based on tournament performance.

**User Story**: As a team, I want to see our ranking so that we know how we compare to other teams.

**Acceptance Criteria**:
- Team stats: matches_played, matches_won, tournaments_won, win_rate
- Team ranking/ELO system
- Rankings per game
- Rank history tracking

**Technical Tasks**:
- [ ] Create `TeamStats` model
- [ ] Create `TeamRanking` model (ELO system)
- [ ] Create `TeamStatsService`
- [ ] Implement ELO calculation algorithm
- [ ] Add event handler for team match completion
- [ ] Implement rank history tracking
- [ ] Create team stats/ranking API
- [ ] Write ELO tests
- [ ] Document ranking system

**Effort**: 1.5 weeks

**Testing & Acceptance**:
- Pass team stats and ELO calculation tests (see CLEANUP_AND_TESTING_PART_6.md §9.8)
- Verify rankings update correctly after matches

---

#### Epic 8.4: Match History Engine
**Description**: Persist complete match history for users and teams with detailed stats.

**User Story**: As a user, I want to view my match history so that I can review past performances.

**Acceptance Criteria**:
- Complete match records (opponent, result, stats, tournament)
- Filterable history (by game, tournament, date)
- Detailed match stats (kills, deaths, rounds won, etc.)
- Export to CSV

**Technical Tasks**:
- [ ] Create `UserMatchHistory` model
- [ ] Create `TeamMatchHistory` model
- [ ] Create `MatchHistoryService`
- [ ] Add event handler to create history entries
- [ ] Implement history filtering/search
- [ ] Add CSV export
- [ ] Create history API endpoints
- [ ] Write history tests
- [ ] Document history tracking

**Effort**: 1 week

**Testing & Acceptance**:
- Pass match history persistence tests (see CLEANUP_AND_TESTING_PART_6.md §9.8)
- Verify history includes all match details and stats

---

#### Epic 8.5: Leaderboards System
**Description**: Global and per-tournament leaderboards showing top players and teams.

**User Story**: As a user, I want to see leaderboards so that I know who the top players are.

**Acceptance Criteria**:
- Global leaderboards (all-time stats)
- Per-game leaderboards
- Per-tournament leaderboards
- Leaderboard categories: Most Wins, Highest Win Rate, Most Kills, Highest ELO
- Real-time leaderboard updates

**Technical Tasks**:
- [ ] Create `Leaderboard` model
- [ ] Create `LeaderboardService`
- [ ] Implement leaderboard calculation logic
- [ ] Add event handler to update leaderboards
- [ ] Implement leaderboard caching (Redis)
- [ ] Create leaderboard API endpoints
- [ ] Write leaderboard tests
- [ ] Document leaderboard system

**Effort**: 1 week

**Testing & Acceptance**:
- Pass leaderboard calculation tests (see CLEANUP_AND_TESTING_PART_6.md §9.8)
- Verify leaderboards update in real-time
- Complete manual QA: tournament completion flow (see CLEANUP_AND_TESTING_PART_6.md §10.5)

---

## Phase 9: Frontend Developer Support & UI Specification System (Weeks 37-40)

### Goal

Build comprehensive frontend developer support system including auto-generated API documentation, JSON schemas for components, UI/UX frameworks, component specification registry, and developer onboarding documentation.

**Success Criteria**:
- ✅ API documentation auto-generated from code
- ✅ JSON schemas for all major components
- ✅ UI/UX design tokens and rules documented
- ✅ Component spec registry operational
- ✅ Developer onboarding docs complete

---

### Epics

#### Epic 9.1: API Documentation Generator
**Description**: Auto-generate comprehensive API documentation from Django REST Framework serializers and views.

**User Story**: As a frontend developer, I want API docs so that I know how to integrate with the backend.

**Acceptance Criteria**:
- OpenAPI 3.0 schema generated automatically
- Interactive API browser (Swagger UI or ReDoc)
- Request/response examples for all endpoints
- Authentication documentation
- Error code reference

**Technical Tasks**:
- [ ] Install and configure drf-spectacular
- [ ] Add docstrings to all API views
- [ ] Generate OpenAPI schema
- [ ] Set up Swagger UI at `/api/docs/`
- [ ] Add request/response examples
- [ ] Document authentication flows
- [ ] Create error code reference
- [ ] Write API documentation guide

**Effort**: 1 week

**Testing & Acceptance**:
- Verify API documentation complete and accurate (see CLEANUP_AND_TESTING_PART_6.md §9.9)
- All endpoints documented with examples

---

#### Epic 9.2: JSON Schemas for Frontend Components
**Description**: Provide JSON schemas for all major UI components to enable type-safe frontend development.

**User Story**: As a frontend developer, I want JSON schemas so that I can validate data and generate TypeScript types.

**Acceptance Criteria**:
- JSON Schema for: Tournament, Registration, Match, Bracket, Group, User, Team
- Schemas include validation rules
- Schemas hosted at `/api/schemas/{model}/`
- TypeScript type generation supported

**Technical Tasks**:
- [ ] Create JSON Schema definitions for all models
- [ ] Add schema validation rules
- [ ] Create schema API endpoints
- [ ] Add schema versioning
- [ ] Generate TypeScript definitions
- [ ] Create schema documentation
- [ ] Write schema tests

**Effort**: 1 week

**Testing & Acceptance**:
- Verify JSON schemas validate correctly (see CLEANUP_AND_TESTING_PART_6.md §9.9)
- TypeScript types generated successfully

---

#### Epic 9.3: UI/UX Framework & Design Tokens
**Description**: Document UI/UX patterns, design tokens (colors, spacing, typography), and component usage guidelines.

**User Story**: As a frontend developer, I want design guidelines so that I build consistent UIs.

**Acceptance Criteria**:
- Design tokens JSON (colors, fonts, spacing)
- Component library documentation
- UI pattern library (forms, cards, modals)
- Accessibility guidelines
- Responsive design rules

**Technical Tasks**:
- [ ] Create design tokens JSON file
- [ ] Document color palette and usage
- [ ] Document typography scale
- [ ] Document spacing system
- [ ] Create component usage guides
- [ ] Document accessibility requirements
- [ ] Create responsive design guide
- [ ] Write UI/UX documentation

**Effort**: 1 week

**Testing & Acceptance**:
- Verify design tokens and UI guidelines complete (see CLEANUP_AND_TESTING_PART_6.md §9.9)
- Accessibility guidelines documented

---

#### Epic 9.4: Component Specification Registry
**Description**: Centralized registry of all UI components with props, events, and usage examples.

**User Story**: As a frontend developer, I want component specs so that I know how to use each component.

**Acceptance Criteria**:
- Component registry database
- Specs include: props, events, slots, examples
- Interactive component playground
- Component search and filtering

**Technical Tasks**:
- [ ] Create `ComponentSpec` model
- [ ] Define spec format (props, events, examples)
- [ ] Seed component specs
- [ ] Create component registry API
- [ ] Build component search
- [ ] Add code examples
- [ ] Create component playground
- [ ] Document registry usage

**Effort**: 0.5 weeks

**Testing & Acceptance**:
- Verify component registry complete (see CLEANUP_AND_TESTING_PART_6.md §9.9)
- All major components documented with examples

---

#### Epic 9.5: Developer Onboarding Documentation
**Description**: Complete developer onboarding guide for new frontend/backend developers.

**User Story**: As a new developer, I want onboarding docs so that I can start contributing quickly.

**Acceptance Criteria**:
- Project setup guide (environment, dependencies)
- Architecture overview
- Code style guide
- Testing guide
- Deployment guide
- Contribution workflow

**Technical Tasks**:
- [ ] Write project setup guide
- [ ] Document architecture patterns
- [ ] Create code style guide (Black, ESLint configs)
- [ ] Write testing guide (pytest, Jest)
- [ ] Document deployment process
- [ ] Create contribution guide (git workflow, PR template)
- [ ] Add FAQ section
- [ ] Record video tutorials

**Effort**: 0.5 weeks

**Testing & Acceptance**:
- Verify developer onboarding docs complete (see CLEANUP_AND_TESTING_PART_6.md §9.9)
- New developer can set up project in < 30 minutes

---

## Phase 10: Advanced Features & Polish (Weeks 41-48)

### Goal

Add advanced user-facing features, notifications, integrations, and mobile support to enhance user experience and engagement.

**Success Criteria**:
- ✅ Guided UI for players/teams operational
- ✅ Email notifications working
- ✅ Discord bot integrated
- ✅ Achievement system complete
- ✅ Mobile app (optional) released
- ✅ Internationalization (optional) working

---

### Epics

#### Epic 10.1: Guided UI for Players/Teams
**Description**: Onboarding wizard and guided workflows for new players and teams.

**User Story**: As a new user, I want guided help so that I understand how to use the platform.

**Acceptance Criteria**:
- Player onboarding wizard (complete profile, link game accounts)
- Team creation wizard (invite members, set roles)
- Tournament discovery help (find tournaments, understand formats)
- Interactive tooltips throughout platform

**Technical Tasks**:
- [ ] Create player onboarding wizard
- [ ] Create team creation wizard
- [ ] Add tournament discovery guide
- [ ] Implement tooltip system
- [ ] Add progress tracking
- [ ] Create onboarding API endpoints
- [ ] Write onboarding tests
- [ ] Document guided UI

**Effort**: 2 weeks

**Testing & Acceptance**:
- Pass onboarding wizard tests (see CLEANUP_AND_TESTING_PART_6.md §9.10)
- Verify tooltips and help overlays work correctly

---

#### Epic 10.2: User Stats & History Dashboard
**Description**: Comprehensive user dashboard showing stats, match history, achievements, and rankings.

**User Story**: As a user, I want a stats dashboard so that I can see my competitive progress.

**Acceptance Criteria**:
- Stats overview (win rate, K/D, matches played)
- Match history timeline
- Achievement showcase
- Ranking trends graph
- Per-game breakdowns

**Technical Tasks**:
- [ ] Create dashboard API endpoints
- [ ] Implement stats aggregation
- [ ] Add match history filtering
- [ ] Create ranking trend calculation
- [ ] Build dashboard frontend (backend API)
- [ ] Add caching for performance
- [ ] Write dashboard tests
- [ ] Document dashboard features

**Effort**: 1.5 weeks

**Testing & Acceptance**:
- Pass user dashboard tests (see CLEANUP_AND_TESTING_PART_6.md §9.10)
- Verify stats dashboard displays correctly

---

#### Epic 10.3: Email Notification System
**Description**: Comprehensive email notification system for all major events.

**User Story**: As a user, I want email notifications so that I stay informed about my tournaments.

**Acceptance Criteria**:
- Notification types: Match scheduled, Result submitted, Dispute, Tournament start, Achievement unlocked
- Email templates (responsive HTML)
- Unsubscribe mechanism
- Notification preferences
- Email delivery tracking

**Technical Tasks**:
- [ ] Set up email backend (SendGrid/SES)
- [ ] Create email templates
- [ ] Implement notification service
- [ ] Add event handlers for notifications
- [ ] Create unsubscribe mechanism
- [ ] Add notification preferences UI
- [ ] Implement delivery tracking
- [ ] Write notification tests
- [ ] Document notification system

**Effort**: 1.5 weeks

**Testing & Acceptance**:
- Pass email notification tests (see CLEANUP_AND_TESTING_PART_6.md §9.10)
- Verify email delivery rate > 95%

---

#### Epic 10.4: Discord Bot Integration
**Description**: Discord bot for tournament updates, match reminders, and community engagement.

**User Story**: As a user, I want Discord notifications so that I get updates where I already spend time.

**Acceptance Criteria**:
- Discord bot with commands: /tournaments, /register, /mystats
- Automatic notifications in Discord channels
- Match reminders via DM
- Tournament announcements
- Leaderboard updates

**Technical Tasks**:
- [ ] Create Discord bot application
- [ ] Implement bot commands
- [ ] Add webhook integration for notifications
- [ ] Create match reminder scheduler
- [ ] Implement announcement system
- [ ] Add leaderboard update posting
- [ ] Write bot tests
- [ ] Document bot setup and usage

**Effort**: 1.5 weeks

**Testing & Acceptance**:
- Pass Discord bot integration tests (see CLEANUP_AND_TESTING_PART_6.md §9.10)
- Verify bot commands work correctly

---

#### Epic 10.5: Achievement System
**Description**: Gamification system with achievements, badges, and rewards.

**User Story**: As a user, I want achievements so that I have goals to work toward.

**Acceptance Criteria**:
- Achievement types: First Win, 10 Wins, Tournament Winner, Undefeated, etc.
- Badge display on profiles
- Achievement notifications
- Achievement progress tracking
- Rewards (DeltaCoin bonuses)

**Technical Tasks**:
- [ ] Create `Achievement` model
- [ ] Create `UserAchievement` model
- [ ] Define achievement criteria
- [ ] Implement achievement checking service
- [ ] Add event handlers for achievements
- [ ] Create badge display system
- [ ] Implement reward distribution
- [ ] Write achievement tests
- [ ] Document achievement system

**Effort**: 1 week

**Legacy Cleanup**:
- Remove all legacy code and feature flags (see CLEANUP_AND_TESTING_PART_6.md §3.5)
- Delete all *_legacy.py files
- Squash migrations (optional)

**Testing & Acceptance**:
- Pass achievement system tests (see CLEANUP_AND_TESTING_PART_6.md §9.10)
- Verify achievements unlock correctly

---

#### Epic 10.6: Internationalization (i18n)
**Description**: Multi-language support for global reach (English, Spanish, Portuguese, Chinese).

**User Story**: As a non-English user, I want the platform in my language so that I can use it comfortably.

**Acceptance Criteria**:
- Django i18n framework configured
- UI strings translatable
- Language selector in header
- 4 languages supported
- Content translations (tournament descriptions)

**Technical Tasks**:
- [ ] Configure Django i18n
- [ ] Mark all strings for translation
- [ ] Generate translation files (.po)
- [ ] Translate to 4 languages
- [ ] Add language selector
- [ ] Implement content translation
- [ ] Write i18n tests
- [ ] Document translation workflow

**Effort**: 2 weeks (optional)

**Testing & Acceptance**:
- Pass i18n tests if implemented (see CLEANUP_AND_TESTING_PART_6.md §9.10)
- Verify all 4 languages display correctly

---

#### Epic 10.7: Mobile App (React Native)
**Description**: Mobile app for iOS/Android with core platform features.

**User Story**: As a mobile user, I want a native app so that I have a better mobile experience.

**Acceptance Criteria**:
- Registration flow
- Tournament browsing
- Match tracking (live updates)
- Push notifications
- Profile management

**Technical Tasks**:
- [ ] Set up React Native project
- [ ] Implement authentication
- [ ] Build registration screens
- [ ] Build tournament browser
- [ ] Add match tracking
- [ ] Implement push notifications
- [ ] Add profile screens
- [ ] Test on iOS and Android
- [ ] Submit to app stores
- [ ] Document mobile app

**Effort**: 6 weeks (optional, can be separate project)

**Testing & Acceptance**:
- Pass mobile app tests if implemented (see CLEANUP_AND_TESTING_PART_6.md §9.10)
- Verify core features work on iOS and Android

**Final Cleanup & Testing**:
- Complete full regression test suite (see CLEANUP_AND_TESTING_PART_6.md §11.4)
- Achieve 80%+ test coverage across all modules (see CLEANUP_AND_TESTING_PART_6.md §11.5)
- Zero legacy code patterns remaining (see CLEANUP_AND_TESTING_PART_6.md §2)
- All manual QA checklists passed (see CLEANUP_AND_TESTING_PART_6.md §10)

---

## Phase Dependencies Summary

### Critical Path
The minimum path to a functional platform:

```
Phase 1 (Foundations) → 4 weeks
  ↓
Phase 2 (Game Rules) → 3 weeks
  ↓
Phase 3 (Bracket Engine) → 5 weeks
  ↓
Phase 4 (TournamentOps) → 4 weeks
  ↓
Phase 5 (Smart Registration) → 5 weeks
  ↓
Phase 6 (Result Pipeline) → 4 weeks
  ↓
Phase 7 (Organizer Console) → 5 weeks
  ↓
Phase 8 (Stats & History) → 6 weeks

Total Critical Path: 36 weeks
```

### Parallel Opportunities

After Phase 4 completes, these can run in parallel:
- **Phase 5** (Smart Registration) - Team A
- **Phase 6** (Result Pipeline) - Team B
- **Phase 9** (Frontend Support) - Team C (docs can start early)

After Phase 7 completes:
- **Phase 8** (Stats) - Team A
- **Phase 10** (Advanced Features) - Team B

### Recommended Sequencing

**Sprint 1-4 (Weeks 1-16)**: Foundation + Core Systems
- Phase 1: Architecture Foundations
- Phase 2: Game Rules & Configuration
- Phase 3: Universal Tournament Format Engine
- Phase 4: TournamentOps Core Workflows

**Sprint 5-8 (Weeks 17-30)**: Registration + Results + Organizer Tools
- Phase 5: Smart Registration System
- Phase 6: Result Pipeline & Dispute Resolution (parallel with Phase 5)
- Phase 7: Organizer Console & Manual Ops

**Sprint 9-10 (Weeks 31-40)**: Stats + Developer Support
- Phase 8: Event-Driven Stats & History
- Phase 9: Frontend Developer Support (parallel with Phase 8)

**Sprint 11-12 (Weeks 41-48)**: Polish + Advanced Features
- Phase 10: Advanced Features & Polish

---

## Success Metrics (KPIs)

### Technical Excellence (Phases 1-4)
- **Code Coverage**: > 80% unit test coverage
- **API Response Time**: < 200ms (p95)
- **Event Processing Latency**: < 30 seconds (match complete → stats updated)
- **Zero Direct Imports**: No cross-domain model imports

### User Experience (Phases 5-7)
- **Registration Completion Rate**: > 85% (draft started → submitted)
- **Registration Time**: < 5 minutes (avg time to complete)
- **Result Dispute Rate**: < 5% (disputed / total submissions)
- **Organizer Approval Time**: < 6 hours (submission → approval)

### Platform Health (Phases 8-10)
- **Stats Accuracy**: 100% (verified via manual audit)
- **Email Delivery Rate**: > 95%
- **API Uptime**: > 99.5%
- **Mobile Registration Success**: > 90%

### Business Metrics (Post-Launch)
- **30-Day Retention**: > 40%
- **Tournament Completion Rate**: > 90%
- **User Growth**: 20% MoM
- **Revenue per User**: > $5/month

---

## Recommended Prioritization

### Must-Have (MVP - Phases 1-8)
Essential for production launch:
- ✅ Clean architecture with proper boundaries
- ✅ Game configuration system (support all 11 games)
- ✅ Universal tournament format engine
- ✅ Smart registration with auto-fill
- ✅ Result pipeline with verification
- ✅ Organizer console with tools
- ✅ Event-driven stats and rankings

### High-Priority (Launch+ - Phase 9-10 Core)
Add immediately after MVP:
1. **Frontend Developer Support** (API docs, schemas)
2. **Guided UI** (player/team onboarding)
3. **Email Notifications** (critical for communication)
4. **Discord Integration** (meet users where they are)

### Medium-Priority (3-6 Months Post-Launch)
Add after platform stabilizes:
1. **Achievement System** (gamification, retention)
2. **User Stats Dashboard** (enhanced UX)
3. **Advanced Organizer Tools** (bulk operations, analytics)

### Low-Priority (6-12 Months Post-Launch)
Nice-to-have features:
1. **Mobile App** (significant investment, wait for demand)
2. **Internationalization** (target when expanding globally)
3. **Advanced Analytics** (requires data accumulation)

---

## Conclusion

This comprehensive roadmap provides a **structured, 48-week development plan** to transform DeltaCrown into a **world-class esports tournament platform** that supports:

- ✅ **11 games** with zero hardcoded logic
- ✅ **5 tournament formats** (SE, DE, RR, Swiss, Groups→Playoffs)
- ✅ **Manual result verification** with multi-checkpoint validation
- ✅ **Smart registration** with auto-fill and game-aware questions
- ✅ **Comprehensive organizer tools** for efficient tournament management
- ✅ **Event-driven architecture** for automatic stats updates
- ✅ **Frontend developer support** with API docs and component specs

**Total Development Timeline**: 48 weeks (12 months)

**Key Milestones**:
- **Month 3**: Architecture + Game Rules + Bracket Engine complete
- **Month 4**: TournamentOps workflows operational
- **Month 6**: Smart Registration + Result Pipeline live
- **Month 8**: Organizer Console + Stats System complete
- **Month 10**: Frontend Support + Developer Docs ready
- **Month 12**: Advanced Features + Platform ready for public launch

**Post-Launch Focus**: Community building, mobile app, international expansion, advanced analytics, third-party integrations.

---

**End of Development Roadmap & Epic Backlog**
